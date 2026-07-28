"""The comparison engine.

One rule shapes every line of this module: **a comparison that was not measured alike is
not a comparison.** Every pairing goes through :func:`veo.compare.assert_comparable`, and
when that guard says no, this module produces a refusal with a Korean explanation instead
of a number. It does not fall back to a "rough" comparison, it does not compute a partial
delta, and it does not keep the headline score gap while dropping the details.

Three design decisions worth stating outright.

**A refusal is per competitor, not per report.** Four competitors where one was crawled on
desktop should not cost the other three their comparison. The refused pair carries zero
deltas — not a hidden zero, an absent one — and says which field blocked it.

**The useful output is the check diff, not the score gap.** "We are 8.5 points behind" is
a feeling. "We fail ``seo.robots.txt_allows_url`` and they pass it" is a task. The
category deltas are here because people expect them, and each one states the denominator
it was computed over, plus a warning when the two sides did not score the same checks.

**Confidence follows the weakest side.** A 0.4-coverage measurement against a 0.9-coverage
one is barely a comparison, and the number says so: the coverage gap itself reduces
confidence, so a lopsided pair cannot present itself as a firm result.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any

from veo.compare import (
    DEFAULT_MAX_AGE_GAP_DAYS,
    DEFAULT_MAX_PAGE_RATIO,
    ComparabilityError,
    ConditionDifference,
    MeasurementConditions,
    assert_comparable,
    describe_differences,
)
from veo.scoring import CheckStatus, ScoreResult, ScoringSpec

#: Statuses that put a check in the denominator. ``UNKNOWN`` and ``NOT_APPLICABLE`` do not:
#: one is "we could not look", the other is "it does not apply here". Neither is a result,
#: and comparing either against a real result invents a gap that was never measured.
SCORED_STATUSES = frozenset({CheckStatus.PASS, CheckStatus.WARNING, CheckStatus.FAIL})

_STATUS_RANK = {CheckStatus.FAIL: 0, CheckStatus.WARNING: 1, CheckStatus.PASS: 2}

_CONFIDENCE_BANDS_KO = ((0.8, "높음"), (0.5, "보통"), (0.25, "낮음"))


class CheckVerdict(StrEnum):
    """How one check stands between the two sites."""

    WE_FAIL_THEY_PASS = "WE_FAIL_THEY_PASS"  # noqa: S105 - a verdict, not a credential
    THEY_FAIL_WE_PASS = "THEY_FAIL_WE_PASS"  # noqa: S105 - a verdict, not a credential
    WE_ARE_BEHIND = "WE_ARE_BEHIND"
    WE_ARE_AHEAD = "WE_ARE_AHEAD"
    LEVEL = "LEVEL"
    NOT_COMPARABLE = "NOT_COMPARABLE"


# --------------------------------------------------------------------------- #
# Input
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class CategoryMeasurement:
    """One category of one site's score, in the vocabulary this engine needs."""

    category_id: str
    name_ko: str
    weight: float
    score: float | None
    coverage: float
    scored_check_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Measurement:
    """One site, measured once, with the conditions that measurement was taken under.

    Deliberately narrower than :class:`~veo.scoring.ScoreResult`: this engine has no
    business with penalties, caps or traces, and taking only what it needs keeps it from
    quietly acquiring the ability to recompute a score.
    """

    key: str
    label_ko: str
    conditions: MeasurementConditions
    overall_score: float | None
    coverage: float
    confidence: float
    categories: tuple[CategoryMeasurement, ...] = ()
    check_statuses: Mapping[str, CheckStatus] = field(default_factory=dict)

    @classmethod
    def from_score_result(
        cls,
        *,
        key: str,
        label_ko: str,
        conditions: MeasurementConditions,
        score: ScoreResult,
    ) -> Measurement:
        return cls(
            key=key,
            label_ko=label_ko,
            conditions=conditions,
            overall_score=score.overall_score,
            coverage=score.coverage,
            confidence=score.confidence,
            categories=tuple(
                CategoryMeasurement(
                    category_id=category.category_id,
                    name_ko=category.name_ko,
                    weight=category.weight,
                    score=category.score,
                    coverage=category.coverage,
                    scored_check_ids=tuple(category.scored_check_ids),
                )
                for category in score.categories
            ),
            check_statuses={item.check_id: item.status for item in score.outcomes},
        )

    def with_key(self, key: str, label_ko: str | None = None) -> Measurement:
        return replace(self, key=key, label_ko=label_ko or self.label_ko)

    def category(self, category_id: str) -> CategoryMeasurement | None:
        for category in self.categories:
            if category.category_id == category_id:
                return category
        return None


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class SetMember:
    """One participant in the comparison set, named wherever a number is shown."""

    key: str
    label_ko: str

    def as_dict(self) -> dict[str, str]:
        return {"key": self.key, "label_ko": self.label_ko}


@dataclass(frozen=True, slots=True)
class CheckDelta:
    """One check, on both sites."""

    check_id: str
    title_ko: str
    category_id: str | None
    severity: str | None
    our_status: CheckStatus | None
    their_status: CheckStatus | None
    comparable: bool
    verdict: CheckVerdict

    def as_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "title_ko": self.title_ko,
            "category_id": self.category_id,
            "severity": self.severity,
            "our_status": str(self.our_status) if self.our_status else None,
            "their_status": str(self.their_status) if self.their_status else None,
            "comparable": self.comparable,
            "verdict": str(self.verdict),
        }


@dataclass(frozen=True, slots=True)
class CategoryDelta:
    """One category, on both sites, with the denominator the difference rests on."""

    category_id: str
    name_ko: str
    weight: float
    our_score: float | None
    their_score: float | None
    delta: float | None
    our_coverage: float | None
    their_coverage: float | None
    shared_check_ids: tuple[str, ...]
    our_only_scored_check_ids: tuple[str, ...]
    their_only_scored_check_ids: tuple[str, ...]
    denominators_match: bool
    note_ko: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "category_id": self.category_id,
            "name_ko": self.name_ko,
            "weight": self.weight,
            "our_score": self.our_score,
            "their_score": self.their_score,
            "delta": self.delta,
            "our_coverage": self.our_coverage,
            "their_coverage": self.their_coverage,
            "shared_check_ids": list(self.shared_check_ids),
            "our_only_scored_check_ids": list(self.our_only_scored_check_ids),
            "their_only_scored_check_ids": list(self.their_only_scored_check_ids),
            "denominators_match": self.denominators_match,
            "note_ko": self.note_ko,
        }


@dataclass(frozen=True, slots=True)
class PairComparison:
    """Our site against exactly one competitor — or the reason there is no comparison."""

    competitor_key: str
    competitor_label_ko: str
    competitor_conditions: MeasurementConditions
    comparable: bool
    refusal_ko: str | None
    blocking_differences: tuple[dict[str, Any], ...]
    waived_differences: tuple[dict[str, Any], ...]
    tolerated_differences: tuple[dict[str, Any], ...]
    waived_scope_variance: bool
    overall_delta: float | None
    categories: tuple[CategoryDelta, ...]
    check_deltas: tuple[CheckDelta, ...]
    confidence: float | None
    confidence_level_ko: str | None
    confidence_basis_ko: str
    summary_ko: str

    def we_fail_they_pass(self) -> tuple[CheckDelta, ...]:
        """The list worth acting on: they solved it, we have not."""
        return tuple(d for d in self.check_deltas if d.verdict is CheckVerdict.WE_FAIL_THEY_PASS)

    def they_fail_we_pass(self) -> tuple[CheckDelta, ...]:
        """The reverse — worth knowing before a report claims we are behind everywhere."""
        return tuple(d for d in self.check_deltas if d.verdict is CheckVerdict.THEY_FAIL_WE_PASS)

    def not_comparable_checks(self) -> tuple[CheckDelta, ...]:
        """Checks one side could not measure. A gap here is unknown, not zero."""
        return tuple(d for d in self.check_deltas if not d.comparable)

    def as_dict(self) -> dict[str, Any]:
        return {
            "competitor_key": self.competitor_key,
            "competitor_label_ko": self.competitor_label_ko,
            "competitor_conditions": self.competitor_conditions.as_dict(),
            "comparable": self.comparable,
            "refusal_ko": self.refusal_ko,
            "blocking_differences": [dict(d) for d in self.blocking_differences],
            "waived_differences": [dict(d) for d in self.waived_differences],
            "tolerated_differences": [dict(d) for d in self.tolerated_differences],
            "waived_scope_variance": self.waived_scope_variance,
            "overall_delta": self.overall_delta,
            "categories": [category.as_dict() for category in self.categories],
            "check_deltas": [delta.as_dict() for delta in self.check_deltas],
            "we_fail_they_pass": [delta.check_id for delta in self.we_fail_they_pass()],
            "they_fail_we_pass": [delta.check_id for delta in self.they_fail_we_pass()],
            "not_comparable_check_ids": [
                delta.check_id for delta in self.not_comparable_checks()
            ],
            "confidence": self.confidence,
            "confidence_level_ko": self.confidence_level_ko,
            "confidence_basis_ko": self.confidence_basis_ko,
            "summary_ko": self.summary_ko,
        }


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """Our site against a named set of competitors."""

    baseline_key: str
    baseline_label_ko: str
    baseline_conditions: MeasurementConditions
    comparison_set: tuple[SetMember, ...]
    pairs: tuple[PairComparison, ...]
    allow_scope_variance: bool
    confidence: float | None
    confidence_level_ko: str | None
    confidence_basis_ko: str
    summary_ko: str

    @property
    def comparable_count(self) -> int:
        return sum(1 for pair in self.pairs if pair.comparable)

    @property
    def refused_count(self) -> int:
        return sum(1 for pair in self.pairs if not pair.comparable)

    def as_dict(self) -> dict[str, Any]:
        return {
            "baseline": {
                "key": self.baseline_key,
                "label_ko": self.baseline_label_ko,
                "conditions": self.baseline_conditions.as_dict(),
            },
            "comparison_set": [member.as_dict() for member in self.comparison_set],
            "pairs": [pair.as_dict() for pair in self.pairs],
            "allow_scope_variance": self.allow_scope_variance,
            "comparable_count": self.comparable_count,
            "refused_count": self.refused_count,
            "confidence": self.confidence,
            "confidence_level_ko": self.confidence_level_ko,
            "confidence_basis_ko": self.confidence_basis_ko,
            "summary_ko": self.summary_ko,
        }


# --------------------------------------------------------------------------- #
# The engine
# --------------------------------------------------------------------------- #


def compare(
    baseline: Measurement,
    competitors: Sequence[Measurement],
    *,
    spec: ScoringSpec | None = None,
    allow_scope_variance: bool = False,
    max_page_ratio: float = DEFAULT_MAX_PAGE_RATIO,
    max_age_gap_days: int = DEFAULT_MAX_AGE_GAP_DAYS,
) -> ComparisonResult:
    """Compare one site against one or more competitors, refusing what cannot be compared.

    ``spec`` is only used to name checks in Korean and to attach their severity; the
    comparison is identical without it. ``allow_scope_variance`` waives an uneven page
    count and nothing else — it must be an explicit request, it is never a default, and
    the waived difference stays in the output.
    """
    _reject_empty(competitors)
    _reject_duplicate_keys(baseline, competitors)

    pairs = tuple(
        _compare_one(
            baseline,
            competitor,
            spec=spec,
            allow_scope_variance=allow_scope_variance,
            max_page_ratio=max_page_ratio,
            max_age_gap_days=max_age_gap_days,
        )
        for competitor in competitors
    )

    weakest = _weakest(pairs)
    confidence = weakest.confidence if weakest is not None else None

    return ComparisonResult(
        baseline_key=baseline.key,
        baseline_label_ko=baseline.label_ko,
        baseline_conditions=baseline.conditions,
        comparison_set=tuple(
            SetMember(key=c.key, label_ko=c.label_ko) for c in competitors
        ),
        pairs=pairs,
        allow_scope_variance=allow_scope_variance,
        confidence=confidence,
        confidence_level_ko=_level_ko(confidence),
        confidence_basis_ko=_overall_confidence_basis_ko(weakest, pairs),
        summary_ko=_overall_summary_ko(pairs, confidence),
    )


def _compare_one(
    baseline: Measurement,
    competitor: Measurement,
    *,
    spec: ScoringSpec | None,
    allow_scope_variance: bool,
    max_page_ratio: float,
    max_age_gap_days: int,
) -> PairComparison:
    differences = describe_differences(
        baseline.conditions,
        competitor.conditions,
        max_page_ratio=max_page_ratio,
        max_age_gap_days=max_age_gap_days,
    )
    tolerated = tuple(d.as_dict() for d in differences if not d.blocking)

    try:
        assert_comparable(
            baseline.conditions,
            competitor.conditions,
            allow_scope_variance=allow_scope_variance,
            max_page_ratio=max_page_ratio,
            max_age_gap_days=max_age_gap_days,
        )
    except ComparabilityError as refused:
        # No deltas at all. A partial comparison past a blocking difference is exactly the
        # confident lie this package exists to prevent.
        return PairComparison(
            competitor_key=competitor.key,
            competitor_label_ko=competitor.label_ko,
            competitor_conditions=competitor.conditions,
            comparable=False,
            refusal_ko=str(refused),
            blocking_differences=tuple(d.as_dict() for d in refused.differences),
            waived_differences=_scope_waivers(differences, allow_scope_variance),
            tolerated_differences=tolerated,
            waived_scope_variance=bool(_scope_waivers(differences, allow_scope_variance)),
            overall_delta=None,
            categories=(),
            check_deltas=(),
            confidence=None,
            confidence_level_ko=None,
            confidence_basis_ko=(
                "측정 조건이 달라 비교하지 않았으므로 신뢰도를 계산하지 않았습니다."
            ),
            summary_ko=str(refused),
        )

    waived = _scope_waivers(differences, allow_scope_variance)
    categories = _category_deltas(baseline, competitor)
    checks = _check_deltas(baseline, competitor, spec)
    confidence = _pair_confidence(baseline.coverage, competitor.coverage)
    overall_delta = _delta(baseline.overall_score, competitor.overall_score)

    return PairComparison(
        competitor_key=competitor.key,
        competitor_label_ko=competitor.label_ko,
        competitor_conditions=competitor.conditions,
        comparable=True,
        refusal_ko=None,
        blocking_differences=(),
        waived_differences=waived,
        tolerated_differences=tolerated,
        waived_scope_variance=bool(waived),
        overall_delta=overall_delta,
        categories=categories,
        check_deltas=checks,
        confidence=confidence,
        confidence_level_ko=_level_ko(confidence),
        confidence_basis_ko=_pair_confidence_basis_ko(
            baseline.coverage, competitor.coverage, competitor.label_ko, confidence
        ),
        summary_ko=_pair_summary_ko(
            competitor.label_ko, overall_delta, checks, confidence, bool(waived)
        ),
    )


# --------------------------------------------------------------------------- #
# Deltas
# --------------------------------------------------------------------------- #


def _category_deltas(
    baseline: Measurement, competitor: Measurement
) -> tuple[CategoryDelta, ...]:
    ordered = [category.category_id for category in baseline.categories]
    ordered.extend(
        category.category_id
        for category in competitor.categories
        if category.category_id not in ordered
    )

    deltas: list[CategoryDelta] = []
    for category_id in ordered:
        ours = baseline.category(category_id)
        theirs = competitor.category(category_id)

        our_scored = frozenset(ours.scored_check_ids if ours else ())
        their_scored = frozenset(theirs.scored_check_ids if theirs else ())
        shared = tuple(sorted(our_scored & their_scored))
        our_only = tuple(sorted(our_scored - their_scored))
        their_only = tuple(sorted(their_scored - our_scored))

        described = ours if ours is not None else theirs
        deltas.append(
            CategoryDelta(
                category_id=category_id,
                name_ko=described.name_ko if described is not None else category_id,
                weight=described.weight if described is not None else 0.0,
                our_score=ours.score if ours else None,
                their_score=theirs.score if theirs else None,
                delta=_delta(
                    ours.score if ours else None, theirs.score if theirs else None
                ),
                our_coverage=ours.coverage if ours else None,
                their_coverage=theirs.coverage if theirs else None,
                shared_check_ids=shared,
                our_only_scored_check_ids=our_only,
                their_only_scored_check_ids=their_only,
                denominators_match=our_scored == their_scored,
                note_ko=_denominator_note_ko(shared, our_only, their_only),
            )
        )
    return tuple(deltas)


def _denominator_note_ko(
    shared: tuple[str, ...], our_only: tuple[str, ...], their_only: tuple[str, ...]
) -> str:
    if our_only or their_only:
        return (
            f"두 측정의 채점 분모가 다릅니다 — 공통 {len(shared)}개, 우리만 채점 "
            f"{len(our_only)}개, 경쟁사만 채점 {len(their_only)}개입니다. 한쪽에서 측정하지 "
            "못한 항목은 분모에서 빠져 있으므로, 점수 차이를 그대로 사이트의 차이로 읽으면 "
            "안 됩니다."
        )
    if not shared:
        return (
            "두 측정 모두 이 카테고리에서 채점된 항목이 없습니다. 점수 차이를 해석할 근거가 "
            "없습니다."
        )
    return f"두 측정이 같은 {len(shared)}개 항목을 채점했습니다. 분모가 일치합니다."


def _check_deltas(
    baseline: Measurement, competitor: Measurement, spec: ScoringSpec | None
) -> tuple[CheckDelta, ...]:
    ordered = list(baseline.check_statuses)
    ordered.extend(
        check_id for check_id in competitor.check_statuses if check_id not in ordered
    )

    deltas: list[CheckDelta] = []
    for check_id in ordered:
        ours = baseline.check_statuses.get(check_id)
        theirs = competitor.check_statuses.get(check_id)
        comparable = ours in SCORED_STATUSES and theirs in SCORED_STATUSES
        deltas.append(
            CheckDelta(
                check_id=check_id,
                title_ko=_title_ko(spec, check_id),
                category_id=_category_id(spec, check_id),
                severity=_severity(spec, check_id),
                our_status=ours,
                their_status=theirs,
                comparable=comparable,
                verdict=_verdict(ours, theirs, comparable=comparable),
            )
        )
    return tuple(deltas)


def _verdict(
    ours: CheckStatus | None, theirs: CheckStatus | None, *, comparable: bool
) -> CheckVerdict:
    if not comparable or ours is None or theirs is None:
        return CheckVerdict.NOT_COMPARABLE
    if ours is CheckStatus.FAIL and theirs is CheckStatus.PASS:
        return CheckVerdict.WE_FAIL_THEY_PASS
    if theirs is CheckStatus.FAIL and ours is CheckStatus.PASS:
        return CheckVerdict.THEY_FAIL_WE_PASS
    our_rank, their_rank = _STATUS_RANK[ours], _STATUS_RANK[theirs]
    if our_rank < their_rank:
        return CheckVerdict.WE_ARE_BEHIND
    if our_rank > their_rank:
        return CheckVerdict.WE_ARE_AHEAD
    return CheckVerdict.LEVEL


# --------------------------------------------------------------------------- #
# Confidence
# --------------------------------------------------------------------------- #


def _pair_confidence(our_coverage: float, their_coverage: float) -> float:
    """The weakest side, penalised by how uneven the two sides are.

    ``min(a, b) * (1 - |a - b|)``. Two 0.9 measurements give 0.9. A 0.4 against a 0.9
    gives 0.2 — because it is not a 0.4-quality comparison either, it is two measurements
    of different thoroughness placed side by side, and half of what one side looked at the
    other never did.
    """
    weakest = min(our_coverage, their_coverage)
    gap = abs(our_coverage - their_coverage)
    return max(0.0, min(1.0, weakest * (1.0 - gap)))


def _pair_confidence_basis_ko(
    our_coverage: float, their_coverage: float, label_ko: str, confidence: float
) -> str:
    gap = abs(our_coverage - their_coverage)
    return (
        f"우리 측정 범위 {our_coverage:.0%}, {label_ko} 측정 범위 {their_coverage:.0%}"
        f"(차이 {gap:.0%})입니다. 비교 신뢰도는 낮은 쪽을 따르고 격차만큼 더 내려가므로 "
        f"{confidence:.0%}({_level_ko(confidence)})입니다."
    )


def _overall_confidence_basis_ko(
    weakest: PairComparison | None, pairs: tuple[PairComparison, ...]
) -> str:
    if weakest is None:
        return (
            f"비교할 수 있는 경쟁사가 없어 신뢰도를 계산하지 않았습니다. "
            f"{len(pairs)}곳 모두 측정 조건이 달랐습니다."
        )
    return (
        f"전체 신뢰도는 가장 약한 비교를 따릅니다 — {weakest.competitor_label_ko}. "
        f"{weakest.confidence_basis_ko}"
    )


def _weakest(pairs: tuple[PairComparison, ...]) -> PairComparison | None:
    comparable = [pair for pair in pairs if pair.comparable and pair.confidence is not None]
    if not comparable:
        return None
    return min(comparable, key=lambda pair: pair.confidence or 0.0)


def _level_ko(confidence: float | None) -> str | None:
    if confidence is None:
        return None
    for threshold, label in _CONFIDENCE_BANDS_KO:
        if confidence >= threshold:
            return label
    return "매우 낮음"


# --------------------------------------------------------------------------- #
# Korean summaries
# --------------------------------------------------------------------------- #


def _pair_summary_ko(
    label_ko: str,
    overall_delta: float | None,
    checks: tuple[CheckDelta, ...],
    confidence: float,
    waived: bool,
) -> str:
    behind = sum(1 for d in checks if d.verdict is CheckVerdict.WE_FAIL_THEY_PASS)
    ahead = sum(1 for d in checks if d.verdict is CheckVerdict.THEY_FAIL_WE_PASS)
    unmeasured = sum(1 for d in checks if not d.comparable)

    if overall_delta is None:
        headline = f"{label_ko}와(과) 같은 조건에서 비교했으나 한쪽의 종합 점수가 없습니다."
    elif overall_delta < 0:
        headline = f"{label_ko} 대비 종합 점수가 {abs(overall_delta):.1f}점 낮습니다."
    elif overall_delta > 0:
        headline = f"{label_ko} 대비 종합 점수가 {overall_delta:.1f}점 높습니다."
    else:
        headline = f"{label_ko}와(과) 종합 점수가 같습니다."

    sentences = [
        headline,
        f"우리만 실패한 항목 {behind}개, 경쟁사만 실패한 항목 {ahead}개입니다.",
    ]
    if unmeasured:
        sentences.append(
            f"한쪽에서 측정하지 못해 비교에서 제외한 항목이 {unmeasured}개 있습니다. "
            "제외는 0점이 아니라 '모름'입니다."
        )
    if waived:
        sentences.append(
            "검사 페이지 수 차이는 요청에 따라 예외로 허용하고 비교했습니다. 표본 크기가 "
            "다르다는 점을 감안해서 읽어야 합니다."
        )
    sentences.append(f"비교 신뢰도 {confidence:.0%}({_level_ko(confidence)})입니다.")
    return " ".join(sentences)


def _overall_summary_ko(
    pairs: tuple[PairComparison, ...], confidence: float | None
) -> str:
    comparable = [pair for pair in pairs if pair.comparable]
    if not comparable:
        return (
            f"비교할 수 있는 경쟁사가 없습니다. 대상 {len(pairs)}곳 모두 측정 조건이 달라 "
            "비교를 거부했습니다. 각 경쟁사의 거부 사유를 확인해 같은 조건으로 다시 "
            "측정하십시오."
        )

    behind = sum(len(pair.we_fail_they_pass()) for pair in comparable)
    sentences = [
        f"경쟁사 {len(pairs)}곳 가운데 {len(comparable)}곳과 같은 조건에서 비교했습니다.",
        f"우리는 실패했고 경쟁사는 통과한 검사 항목이 누적 {behind}건입니다.",
    ]
    if len(comparable) != len(pairs):
        sentences.append(
            f"{len(pairs) - len(comparable)}곳은 측정 조건이 달라 비교하지 않았습니다."
        )
    if confidence is not None:
        sentences.append(f"전체 비교 신뢰도 {confidence:.0%}({_level_ko(confidence)})입니다.")
    sentences.append(
        "이 값은 검색 순위 예측이 아니라 같은 조건에서 측정한 준비도의 차이입니다."
    )
    return " ".join(sentences)


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _scope_waivers(
    differences: Sequence[ConditionDifference], allow_scope_variance: bool
) -> tuple[dict[str, Any], ...]:
    """The scope differences the caller asked to accept — kept in the output on purpose."""
    if not allow_scope_variance:
        return ()
    return tuple(
        difference.as_dict()
        for difference in differences
        if difference.field == "pages_examined" and difference.blocking
    )


def _delta(ours: float | None, theirs: float | None) -> float | None:
    if ours is None or theirs is None:
        return None
    return ours - theirs


def _title_ko(spec: ScoringSpec | None, check_id: str) -> str:
    check = _spec_check(spec, check_id)
    return check.title_ko if check is not None else check_id


def _severity(spec: ScoringSpec | None, check_id: str) -> str | None:
    check = _spec_check(spec, check_id)
    return str(check.severity) if check is not None else None


def _category_id(spec: ScoringSpec | None, check_id: str) -> str | None:
    if spec is None:
        return None
    try:
        return spec.category_of(check_id).id
    except KeyError:
        return None


def _spec_check(spec: ScoringSpec | None, check_id: str) -> Any:
    if spec is None:
        return None
    try:
        return spec.check(check_id)
    except KeyError:
        return None


def _reject_empty(competitors: Sequence[Measurement]) -> None:
    if not competitors:
        raise ValueError(
            "비교 대상 경쟁사가 최소 한 곳은 있어야 합니다. 비교 집합이 비어 있으면 "
            "'비교 결과'라고 부를 수 있는 것이 없습니다."
        )


def _reject_duplicate_keys(
    baseline: Measurement, competitors: Sequence[Measurement]
) -> None:
    seen = {baseline.key}
    for competitor in competitors:
        if competitor.key in seen:
            raise ValueError(
                f"비교 대상 키가 중복되었습니다: {competitor.key}. 같은 대상을 두 번 세면 "
                "점유율과 집계가 조용히 어긋납니다."
            )
        seen.add(competitor.key)


__all__ = [
    "SCORED_STATUSES",
    "CategoryDelta",
    "CategoryMeasurement",
    "CheckDelta",
    "CheckVerdict",
    "ComparisonResult",
    "Measurement",
    "PairComparison",
    "SetMember",
    "compare",
]
