"""Assembling the SEO scan: observations in, one specification-derived score out.

This is the only module in the package that imports :func:`veo.scoring.evaluate`. The
collectors report what they saw; the evaluator alone turns that into a number, using the
published VEO-LAB specification and nothing else. If a weight ever needs changing it
changes in ``packages/scoring-specs`` and nothing here moves.

The site is parsed once and the same observation is handed to all eight collectors, so
every finding in a report refers to the same normalised URLs.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    Collector,
    EvidenceRecord,
    IssueDraft,
    run_collectors,
)
from veo.scoring import (
    CheckOutcome,
    CheckStatus,
    ScoreResult,
    ScoringSpec,
    evaluate,
    latest_published,
)
from veo.seo.collectors import CATEGORY_COLLECTORS
from veo.seo.observation import build_observation
from veo.seo.parsing.sitemap import parse_sitemap

SPEC_ID = "veo.seo.readiness"


@dataclass(frozen=True, slots=True)
class UnknownCheck:
    """A check that applied but could not be measured, and the Korean reason why."""

    check_id: str
    category_id: str
    title_ko: str
    reason_ko: str


@dataclass(frozen=True, slots=True)
class SeoScanResult:
    """Everything one scan produced: the score, the findings and the evidence behind them."""

    score: ScoreResult
    issues: tuple[IssueDraft, ...]
    evidence: tuple[EvidenceRecord, ...]
    notes_ko: tuple[str, ...]
    summary_ko: str
    unknown_checks: tuple[UnknownCheck, ...]

    @property
    def spec_id(self) -> str:
        return self.score.spec_id


def seo_collectors(context: CollectionContext | None = None) -> tuple[Collector, ...]:
    """One collector per specification category, in the specification's own order.

    When a context is supplied the crawl is parsed once and shared, so the eight
    collectors agree on URL normalisation, the link graph and the click depths.
    """
    observation = build_observation(context) if context is not None else None
    return tuple(factory(observation) for factory in CATEGORY_COLLECTORS.values())  # type: ignore[call-arg]


def load_seo_spec() -> ScoringSpec:
    return latest_published(SPEC_ID)


def run_seo_scan(context: CollectionContext) -> SeoScanResult:
    """Run every collector against ``context`` and score the result."""
    collected = run_collectors(list(seo_collectors(context)), context)
    return score_collection(context, collected)


def score_collection(context: CollectionContext, collected: CollectionResult) -> SeoScanResult:
    """Hand a completed collection to the evaluator and package what comes back."""
    result = evaluate(context.spec, collected.outcomes)

    return SeoScanResult(
        score=result,
        issues=collected.issues,
        evidence=_deduplicate(collected.evidence),
        notes_ko=_scope_notice(context) + collected.notes_ko,
        summary_ko=summarise(context.spec, result),
        unknown_checks=_unknown_checks(context.spec, result.outcomes),
    )


def _scope_notice(context: CollectionContext) -> tuple[str, ...]:
    """측정 범위가 사이트 전체가 아니면 그 사실을 결과 맨 앞에 적는다.

    범위 밖 페이지는 이번 점수에 존재하지 않는다 — 그 사실을 숨기면 "이 점수가
    사이트 전체" 로 읽히고, 그것이 우리가 타사에서 잡아낸 그럴듯한 완결성이다.
    사이트맵이 선언한 주소 수를 함께 적어, 사이트가 대략 얼마나 더 큰지 읽는 사람이
    가늠할 수 있게 한다. 배점은 건드리지 않는다 — 범위 밖이라고 분모에서 빼면
    큰 사이트일수록 덜 재서 유리해진다.
    """
    if context.crawl_is_exhaustive:
        # 표본을 썼다면 전체 선언이 불가능하므로(크롤러가 보장) 이 갈래에서 표본
        # 고지가 사라질 일은 없다 — 그래도 방어적으로 함께 내보낸다.
        return context.sampling_notes_ko
    measured = len(context.documents)
    declared = 0
    for body in context.sitemap_documents.values():
        declared += len(parse_sitemap(body).locations)
    size_hint = (
        f" 사이트맵은 약 {declared:,}개 주소를 선언하고 있습니다."
        if declared > measured
        else ""
    )
    return (
        f"이번 진단은 {measured}장을 측정했으며, 사이트 전체를 본 것으로 확인되지 "
        f"않았습니다.{size_hint} 측정하지 못한 페이지는 이번 점수의 범위 밖입니다. "
        "페이지 간 비교 검사(중복·고아 페이지·깨진 링크)는 전체를 재야 판정됩니다.",
        *context.sampling_notes_ko,
    )


def _deduplicate(records: Sequence[EvidenceRecord]) -> tuple[EvidenceRecord, ...]:
    """Two collectors quoting the same page produce the same content hash, and therefore
    the same evidence id. Keep one copy so a report does not show the page twice."""
    unique: dict[str, EvidenceRecord] = {}
    for record in records:
        unique.setdefault(record.evidence_id, record)
    return tuple(unique.values())


def _unknown_checks(
    spec: ScoringSpec, outcomes: Sequence[CheckOutcome]
) -> tuple[UnknownCheck, ...]:
    unknown: list[UnknownCheck] = []
    for item in outcomes:
        if item.status is not CheckStatus.UNKNOWN:
            continue
        check = spec.check(item.check_id)
        unknown.append(
            UnknownCheck(
                check_id=item.check_id,
                category_id=spec.category_of(item.check_id).id,
                title_ko=check.title_ko,
                reason_ko=item.note or "측정하지 못한 이유가 기록되지 않았습니다.",
            )
        )
    return tuple(unknown)


def summarise(spec: ScoringSpec, result: ScoreResult) -> str:
    """A Korean sentence stating what the number means and what it does not.

    It says outright that the score is not a rank prediction, because that is the single
    misreading that causes the most damage when a report reaches a customer.
    """
    counts = _status_counts(result.outcomes)
    measured = counts[CheckStatus.PASS] + counts[CheckStatus.WARNING] + counts[CheckStatus.FAIL]

    if result.overall_score is None:
        return (
            f"점수를 산출할 수 있는 검사 항목이 없습니다. 전체 {len(result.outcomes)}개 항목 중 "
            f"{counts[CheckStatus.UNKNOWN]}개를 측정하지 못했고 "
            f"{counts[CheckStatus.NOT_APPLICABLE]}개는 해당 없음입니다. "
            "수집 실패는 사이트의 결함이 아니므로 감점하지 않았습니다."
        )

    band = spec.band_for(result.overall_score)
    band_label = band.label_ko if band else "구간 미지정"
    sentences = [
        f"기술 준비도 {result.overall_score:.1f}점({band_label}), "
        f"측정 범위 {result.coverage * 100:.0f}%입니다.",
        f"전체 {len(result.outcomes)}개 항목 가운데 {measured}개를 채점했고, "
        f"{counts[CheckStatus.NOT_APPLICABLE]}개는 해당 없음으로 분모에서 제외했으며, "
        f"{counts[CheckStatus.UNKNOWN]}개는 측정하지 못해 점수에 반영하지 않았습니다.",
    ]

    failing = counts[CheckStatus.FAIL]
    if failing:
        sentences.append(f"조치가 필요한 실패 항목은 {failing}개입니다.")

    if result.applied_caps:
        reasons = " ".join(cap.reason_ko for cap in result.applied_caps)
        sentences.append(f"상한이 적용되었습니다: {reasons}")

    sentences.append(
        "이 점수는 검색 순위 예측이 아니라 검색엔진이 사이트를 발견·해석할 수 있는 상태인지에 "
        "대한 값입니다."
    )
    return " ".join(sentences)


def _status_counts(outcomes: Sequence[CheckOutcome]) -> dict[CheckStatus, int]:
    counts = dict.fromkeys(CheckStatus, 0)
    for item in outcomes:
        counts[item.status] += 1
    return counts


__all__ = [
    "SPEC_ID",
    "SeoScanResult",
    "UnknownCheck",
    "load_seo_spec",
    "run_seo_scan",
    "score_collection",
    "seo_collectors",
    "summarise",
]
