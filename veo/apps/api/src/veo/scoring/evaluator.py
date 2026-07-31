"""The single deterministic scoring evaluator used everywhere in VEO.

Every SEO and GEO readiness score in the product goes through :func:`evaluate`.
No checker, API handler or report template may compute a score of its own, and no
language model is allowed to produce or adjust one.

Arithmetic (VEO-LAB methodology):

    coverage_i     = affected_importance_weight / evaluated_importance_weight
    penalty_i      = severity_coefficient x status_multiplier x coverage_i x confidence_i
    category_budget= sum of severity_coefficient over checks that were actually scored
    category_score = 100 x max(0, 1 - sum(penalty_i) / category_budget)
    reach          = product over gate categories of (1 - status x coverage)
    overall_score  = reach x sum(category_score x weight) / sum(weight of scoreable)

    caps           = overall_score is then bounded from above; a cap never raises a score.
    gates          = reported beside the score; a gate never changes the number.

**Two different things are called a gate here, and they must not be confused.**

``SpecGate`` / :func:`_raise_gates` is a *label*: "this site is blocked from indexing",
reported next to the score, changing no number. It has been here from the start.

``SpecCategory.is_gate`` is *arithmetic*: a category whose failures multiply the score
instead of subtracting from it. It exists because the additive form gave a **fully
noindexed site 74 points** — a site absent from search scored "ready". Only the blocking
checks' own weights were lost.

``reach`` is 1.0 for every specification that does not declare a gate category, so
published specifications keep scoring exactly as they did (ADR 0012).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, Final

from veo.scoring.errors import ScoringSpecError
from veo.scoring.models import (
    AppliedCap,
    CategoryScore,
    CategoryStatus,
    CheckOutcome,
    CheckStatus,
    RaisedGate,
    ScoreResult,
    ScoringSpec,
    SpecCap,
    SpecCategory,
    SpecGate,
    Trigger,
)

_SCORED_STATUSES = frozenset({CheckStatus.PASS, CheckStatus.WARNING, CheckStatus.FAIL})


def evaluate(spec: ScoringSpec, outcomes: Iterable[CheckOutcome]) -> ScoreResult:
    """Score a set of check outcomes against a published specification."""
    by_id = _gate_unopened_integrations(spec, _index_outcomes(spec, outcomes))
    ordered = [by_id[check_id] for check_id in spec.check_ids]

    check_rows: list[dict[str, Any]] = []
    category_scores: list[CategoryScore] = []
    category_rows: list[dict[str, Any]] = []

    for category in spec.categories:
        score, row, traces = _score_category(spec, category, by_id)
        category_scores.append(score)
        category_rows.append(row)
        check_rows.extend(traces)

    reach, gate_unverified = _reach(spec, by_id)

    # 연동이 있어야만 잴 수 있는 영역은 점수를 이루지 않는다. 판정과 보고는 그대로
    # 하되 분모에서 빠지므로, 고객이 서치콘솔을 연결하든 안 하든 100점의 뜻이 같다.
    # 관문 영역도 여기서 빠진다 — 관문은 가중 평균에 참여하지 않고 결과에 곱해진다.
    in_score = {
        c.id for c in spec.categories if c.contributes_to_score and not c.is_gate
    }
    scoring_categories = [c for c in category_scores if c.category_id in in_score]

    # 아무것도 재지 못했다면 0점이 아니라 **측정 불가**다. 사이트를 가져오지 못한 것과
    # 사이트가 나쁜 것은 다른 사실이고, 0점으로 보고하면 없는 실패를 지어내게 된다.
    # 절대 평가는 "잰 것이 있는데 일부를 못 잰" 경우의 규칙이지, 한 번도 못 본 대상을
    # 0점으로 만드는 규칙이 아니다.
    nothing_measured = not any(c.scored_check_ids for c in scoring_categories)
    if _is_absolute(spec) and nothing_measured:
        category_scores = [
            c.model_copy(update={"status": "UNKNOWN", "score": None})
            if c.status == "SCORED" and c.category_id in in_score
            else c
            for c in category_scores
        ]
        scoring_categories = [c for c in category_scores if c.category_id in in_score]

    scoreable = [c for c in scoring_categories if c.status == "SCORED"]
    effective_weight_total = sum(c.weight for c in scoreable)
    declared_weight_total = sum(c.weight for c in spec.categories if c.id in in_score)

    if scoreable:
        weighted_sum = sum((c.score or 0.0) * c.weight for c in scoreable)
        score_before_caps: float | None = weighted_sum / effective_weight_total
        result_status: CategoryStatus = "SCORED"
    else:
        weighted_sum = 0.0
        score_before_caps = None
        result_status = (
            "NOT_APPLICABLE"
            if all(c.status == "NOT_APPLICABLE" for c in scoring_categories)
            else "UNKNOWN"
        )

    applied_caps = _apply_caps(spec, by_id)
    if score_before_caps is None:
        overall_score: float | None = None
    else:
        # 관문을 먼저 곱하고 상한을 적용한다. 순서가 뒤바뀌면 상한이 이미 0 에 가까운
        # 점수를 다시 깎는 시늉만 하게 되고, 어떤 상한이 실제로 걸렸는지 기록이
        # 뒤엉킨다. 상한은 "이 결함이 있으면 아무리 잘해도 여기까지" 라는 뜻이므로
        # 도달률을 반영한 실제 점수에 걸려야 한다.
        overall_score = score_before_caps * reach
        for cap in applied_caps:
            overall_score = min(overall_score, cap.max_overall_score)
        overall_score = round(max(0.0, min(100.0, overall_score)), 6)

    gates = _raise_gates(spec, by_id)

    # 측정 범위도 점수를 이루는 영역에 대해서만 말한다. 연동 지표를 섞으면 "측정 범위
    # 62%" 가 우리가 못 한 것인지 고객이 아직 권한을 안 준 것인지 구분되지 않는다.
    measurable = [c for c in scoring_categories if c.status != "NOT_APPLICABLE"]
    measurable_weight = sum(c.weight for c in measurable)
    if measurable_weight > 0:
        coverage = sum(c.coverage * c.weight for c in measurable) / measurable_weight
        confidence = sum(c.confidence * c.weight for c in measurable) / measurable_weight
    else:
        coverage = 0.0
        confidence = 0.0

    band = spec.band_for(overall_score) if overall_score is not None else None

    trace: dict[str, Any] = {
        "spec": {
            "spec_id": spec.spec_id,
            "version": spec.version,
            "checksum": spec.checksum,
            "domain": str(spec.domain),
            "status": str(spec.status),
            "effective_at": spec.effective_at,
            "methodology_owner": spec.methodology_owner,
            "implementation_owner": spec.implementation_owner,
        },
        "policy": {
            "severity_coefficients": {str(k): v for k, v in spec.severity_coefficients.items()},
            "fail_penalty_multiplier": spec.status_policy.fail_penalty_multiplier,
            "warning_penalty_multiplier": spec.status_policy.warning_penalty_multiplier,
            "pass_penalty_multiplier": spec.status_policy.pass_penalty_multiplier,
            "not_applicable": spec.status_policy.not_applicable,
            "unknown": spec.status_policy.unknown,
        },
        "checks": check_rows,
        "categories": category_rows,
        "overall": {
            "declared_weight_total": round(declared_weight_total, 6),
            "effective_weight_total": round(effective_weight_total, 6),
            "renormalised": abs(effective_weight_total - declared_weight_total) > 1e-9,
            "weighted_sum": round(weighted_sum, 6),
            "score_before_caps": None if score_before_caps is None else round(score_before_caps, 6),
            "score": overall_score,
            "coverage": round(coverage, 6),
            "confidence": round(confidence, 6),
            "status": result_status,
            "band_id": band.id if band else None,
            # 도달률은 관문 영역이 있는 명세에서만 1.0 이 아니다. 그래도 항상 적는다 —
            # 어떤 명세로 매긴 점수인지 나중에 이 기록만 보고 알 수 있어야 한다.
            "reach": round(reach, 6),
            "gate_unverified": gate_unverified,
            "formula": (
                "overall = reach x sum(category_score x weight)"
                " / sum(weight of scoreable categories)"
            ),
        },
        "caps": [
            {
                "cap_id": cap.cap_id,
                "max_overall_score": cap.max_overall_score,
                "reason_ko": cap.reason_ko,
                "release_condition_ko": cap.release_condition_ko,
                "triggered_by": list(cap.triggered_by),
            }
            for cap in applied_caps
        ],
        "gates": [
            {
                "gate_id": gate.gate_id,
                "status_code": gate.status_code,
                "label_ko": gate.label_ko,
                "triggered_by": list(gate.triggered_by),
            }
            for gate in gates
        ],
    }

    return ScoreResult(
        spec_id=spec.spec_id,
        spec_version=spec.version,
        spec_checksum=spec.checksum,
        domain=spec.domain,
        status=result_status,
        overall_score=overall_score,
        overall_score_before_caps=(
            None if score_before_caps is None else round(score_before_caps, 6)
        ),
        band_id=band.id if band else None,
        coverage=round(coverage, 6),
        confidence=round(confidence, 6),
        effective_weight_total=round(effective_weight_total, 6),
        categories=category_scores,
        applied_caps=applied_caps,
        gates=gates,
        outcomes=ordered,
        trace=trace,
    )


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _index_outcomes(
    spec: ScoringSpec, outcomes: Iterable[CheckOutcome]
) -> dict[str, CheckOutcome]:
    known = set(spec.check_ids)
    by_id: dict[str, CheckOutcome] = {}

    for item in outcomes:
        if item.check_id not in known:
            raise ScoringSpecError(
                f"check '{item.check_id}' is not defined in specification "
                f"{spec.spec_id}@{spec.version}"
            )
        if item.check_id in by_id:
            raise ScoringSpecError(f"duplicate outcome supplied for check '{item.check_id}'")
        by_id[item.check_id] = item

    missing = [check_id for check_id in spec.check_ids if check_id not in by_id]
    if missing:
        raise ScoringSpecError(
            "missing outcomes for "
            f"{len(missing)} check(s) in {spec.spec_id}@{spec.version}: {', '.join(missing)}. "
            "Every check needs an explicit outcome — use NOT_APPLICABLE or UNKNOWN rather "
            "than omitting it."
        )
    return by_id


#: 연동이 열리기 전까지 잴 수 없는 항목에 남기는 사유.
#:
#: 상태만 바꾸고 이유를 비우면 화면에서 "해당 없음" 으로만 읽혀, **연결하면 잴 수 있다**
#: 는 사실이 사라진다. 사용자의 요구는 배점에서 빼되 알려는 주라는 것이었다.
_UNOPENED_REASONS_KO: Final[dict[str, str]] = {
    "CUSTOMER_GRANTED": (
        "사이트 소유자가 권한을 연결해야 측정됩니다. 연결 전까지는 배점에서 제외하며, "
        "점수를 깎지 않습니다."
    ),
    "PAID_PROVIDER": (
        "유료 데이터 연동이 있어야 측정됩니다. 연동 전까지는 배점에서 제외하며, "
        "점수를 깎지 않습니다."
    ),
    "REFERENCE_ONLY": (
        "참고 항목입니다. 조회는 되지만 보이는 범위가 일부이고 이름이 비슷한 다른 업체가 "
        "섞일 수 있어, 점수로 확정하지 않고 **별도 확인**을 부탁드립니다. 배점에서 "
        "제외하며 점수를 깎지 않습니다."
    ),
}


def _gate_unopened_integrations(
    spec: ScoringSpec, by_id: dict[str, CheckOutcome]
) -> dict[str, CheckOutcome]:
    """아직 열리지 않은 연동 때문에 고객의 점수가 깎이지 않게 한다.

    권한이나 유료 계약이 있어야 재는 항목은, 그것이 마련되기 전까지 **진단 범위 밖**이지
    사이트의 결함이 아니다. 측정 불가로 두면 절대 평가에서 0점이 되어, 아직 요청하지도
    않은 권한 때문에 점수가 내려간다.

    연동이 살아 있어 실제로 판정이 나온 항목은 건드리지 않는다. 그때는 잰 것이므로 잰
    대로 채점한다.
    """
    for check_id, outcome in list(by_id.items()):
        check = spec.check(check_id)
        reason = _UNOPENED_REASONS_KO.get(check.availability)
        if reason is None or outcome.status is not CheckStatus.UNKNOWN:
            continue
        # 수집기가 남긴 사유(자격증명 없음 등)를 지우지 않고 뒤에 붙인다. 정책과 관측을
        # 둘 다 남겨야 나중에 왜 빠졌는지 되짚을 수 있다.
        detail = (outcome.note or "").strip()
        by_id[check_id] = outcome.model_copy(
            update={
                "status": CheckStatus.NOT_APPLICABLE,
                "note": f"{reason} ({detail})" if detail else reason,
            }
        )
    return by_id


def _resolve_confidence(spec: ScoringSpec, outcome: CheckOutcome) -> float:
    if outcome.confidence is not None:
        return outcome.confidence
    level = outcome.confidence_level
    assert level is not None  # guaranteed by CheckOutcome validation
    if level not in spec.confidence_levels:
        raise ScoringSpecError(
            f"check '{outcome.check_id}' uses confidence level '{level}' which is not "
            f"defined in {spec.spec_id}@{spec.version}"
        )
    return spec.confidence_levels[level]


def _status_multiplier(spec: ScoringSpec, status: CheckStatus) -> float:
    policy = spec.status_policy
    if status is CheckStatus.FAIL:
        return policy.fail_penalty_multiplier
    if status is CheckStatus.WARNING:
        return policy.warning_penalty_multiplier
    return policy.pass_penalty_multiplier


#: 절대 평가 정책. 재지 못한 항목이 배점을 유지한 채 0점이 된다.
ABSOLUTE_UNKNOWN_POLICY: Final = "SCORE_AS_ZERO_KEEP_IN_DENOMINATOR"


def _breadth(spec: ScoringSpec, coverage_ratio: float) -> float:
    """결함이 퍼진 범위를 감점에 얼마나 반영할지.

    지수가 1.0(기본값)이면 선형이고 지금까지의 계산과 한 글자도 다르지 않다.
    1보다 작은 지수를 선언한 명세에서만 값이 올라간다 — 웹사이트의 결함은 대개
    템플릿 단위로 생기므로, 100장 중 40장이 깨졌다는 것은 40개의 개별 실수가 아니라
    템플릿 하나의 문제이고 나머지 60장도 같은 위험 위에 있다는 뜻이다.
    """
    ratio = min(1.0, max(0.0, coverage_ratio))
    exponent = spec.status_policy.breadth_exponent
    if exponent == 1.0:
        return ratio
    return float(ratio**exponent)


def _check_weights(
    spec: ScoringSpec, category: SpecCategory, by_id: dict[str, CheckOutcome]
) -> dict[str, float]:
    """이 영역에서 각 검사가 실제로 갖는 배점.

    영역이 `raw_budget` 을 선언하지 않았으면 지금까지처럼 심각도 계수를 그대로 쓴다.
    그 경우 분모는 "채점된 검사들의 계수 합" 이 되고, **검사를 더할 때마다 자란다.**
    발행된 명세들이 그 방식이고, 발행본은 불변이므로 그대로 둔다(ADR 0012).

    선언했으면 분모는 그 상수다. 해당 없음(N/A) 검사의 배점만 형제들에게 비례 배분
    된다 — 그것은 "이 사이트에 그 항목이 없다" 는 사실을 반영하는 것이고(ADR 0002),
    "명세에 검사가 하나 늘었다" 와는 전혀 다른 일이다. 후자는 배점표를 다시 짜야 하는
    일이고, 모델이 그것을 강제한다.
    """
    if category.raw_budget is None:
        return {
            check.id: spec.severity_coefficient(check.severity) for check in category.checks
        }

    live = [
        check
        for check in category.checks
        if by_id[check.id].status is not CheckStatus.NOT_APPLICABLE
    ]
    declared = sum(check.points or 0.0 for check in live)
    if declared <= 0.0:
        return {check.id: 0.0 for check in category.checks}

    scale = category.raw_budget / declared
    return {check.id: (check.points or 0.0) * scale for check in category.checks}


def _reach(
    spec: ScoringSpec, by_id: dict[str, CheckOutcome]
) -> tuple[float, list[str]]:
    """검색에 들어갈 수 있는 비율. 관문 영역이 없는 명세에서는 항상 1.0 이다.

    ## 왜 곱셈인가

    가산 방식에서는 **색인이 전면 차단된 사이트가 74점을 받았다**(실측). 검색에
    존재하지 않는 사이트가 "양호" 등급을 받은 것이다. 차단 검사들의 배점만큼만
    잃기 때문이다.

    실제로는 앞 단계가 막히면 뒤 단계가 통째로 무의미하다. noindex 페이지의 완벽한
    구조화 데이터는 아무 일도 하지 않는다. 그래서 차단은 배점이 아니라 곱셈이다.

    관문끼리도 곱한다. 페이지는 **모든** 관문을 통과해야 하기 때문이다 — robots 가
    절반을 막고 상태 코드가 20% 실패면 (1-0.5)(1-0.2) = 0.4 다.

    ## 못 잰 관문은 곱하지 않는다

    관측하지 않은 차단을 있다고 하면 **없는 결함을 지어내는 것**이다(0-A). 오늘
    robots.txt 를 못 가져왔다는 이유로 멀쩡한 병원 홈페이지가 0점이 되어서는 안 된다 —
    구글 Lighthouse 가 정확히 그 실수를 한다(2026-08-01 실측: fetch 타임아웃이 0점
    실패로 기록되고, 화면에서 '크롤러를 막고 있음' 과 구분되지 않았다).

    대신 확인하지 못한 관문의 이름을 함께 돌려주어, 화면이 "색인 가능 여부를 확인하지
    못했다" 고 말할 수 있게 한다. **품질 점수에서는 다르다** — 거기서는 못 잰 항목이
    배점을 잃는다(ADR 0016). 관문은 "있다고 단정하면 사이트를 죽이는" 자리이고,
    품질은 "없다고 단정하면 만점을 주는" 자리라서 안전한 방향이 서로 반대다.
    """
    reach = 1.0
    unverified: list[str] = []

    for category in spec.categories:
        if not category.is_gate:
            continue
        for check in category.checks:
            outcome = by_id[check.id]
            if outcome.status is CheckStatus.NOT_APPLICABLE:
                continue
            if outcome.status is CheckStatus.UNKNOWN:
                unverified.append(check.id)
                continue
            blocked = _status_multiplier(spec, outcome.status) * min(
                1.0, outcome.coverage_ratio
            )
            if blocked > 0:
                reach *= 1.0 - blocked

    return max(0.0, reach), unverified


def _is_absolute(spec: ScoringSpec) -> bool:
    """이 명세가 절대 평가인가.

    명세로 갈라 두는 이유: 규칙이 바뀌어도 그 규칙으로 매긴 과거 점수는 그대로여야 한다.
    1.1.0 이하로 채점된 결과는 앞으로도 1.1.0 의 규칙으로 설명된다.
    """
    return spec.status_policy.unknown == ABSOLUTE_UNKNOWN_POLICY


def _score_category(
    spec: ScoringSpec,
    category: SpecCategory,
    by_id: dict[str, CheckOutcome],
) -> tuple[CategoryScore, dict[str, Any], list[dict[str, Any]]]:
    applicable: list[str] = []
    scored: list[str] = []
    not_applicable: list[str] = []
    unknown: list[str] = []
    failing: list[str] = []

    budget = 0.0
    penalty_total = 0.0
    confidence_weight = 0.0
    confidence_accum = 0.0
    plain_confidences: list[float] = []
    rows: list[dict[str, Any]] = []

    absolute = _is_absolute(spec)
    weight_of = _check_weights(spec, category, by_id)

    for check in category.checks:
        outcome = by_id[check.id]
        coefficient = weight_of[check.id]
        confidence = _resolve_confidence(spec, outcome)

        row: dict[str, Any] = {
            "check_id": check.id,
            "category_id": category.id,
            "status": str(outcome.status),
            "severity": str(check.severity),
            "severity_coefficient": coefficient,
            "affected_weight": outcome.affected_weight,
            "evaluated_weight": outcome.evaluated_weight,
            "coverage_ratio": round(outcome.coverage_ratio, 6),
            "confidence": confidence,
            "evidence_ids": list(outcome.evidence_ids),
        }

        if outcome.status is CheckStatus.NOT_APPLICABLE:
            not_applicable.append(check.id)
            row.update(
                {
                    "status_multiplier": None,
                    "penalty": 0.0,
                    "counted_in_budget": False,
                    "formula": "N/A — excluded from both the numerator and the denominator",
                }
            )
            rows.append(row)
            continue

        applicable.append(check.id)

        if outcome.status is CheckStatus.UNKNOWN:
            unknown.append(check.id)
            if absolute:
                # 절대 평가: 재지 못한 항목은 점수를 얻지 못하고, 그 배점은 분모에 남는다.
                # 빼 버리면 남은 항목의 몫이 부풀려져 "4개 중 1개만 보고 100점" 이 된다.
                # 실패로 보고하지는 않는다 — 사이트의 결함이 아니라 우리가 못 잰 것이다.
                budget += coefficient
                penalty_total += coefficient
                row.update(
                    {
                        "status_multiplier": None,
                        "penalty": round(coefficient, 6),
                        "counted_in_budget": True,
                        "formula": (
                            f"UNKNOWN — earns nothing; {coefficient} stays in the denominator"
                        ),
                    }
                )
            else:
                row.update(
                    {
                        "status_multiplier": None,
                        "penalty": 0.0,
                        "counted_in_budget": False,
                        "formula": (
                            "UNKNOWN — no penalty; lowers category coverage and confidence"
                        ),
                    }
                )
            rows.append(row)
            continue

        scored.append(check.id)
        budget += coefficient
        multiplier = _status_multiplier(spec, outcome.status)
        breadth = _breadth(spec, outcome.coverage_ratio)
        penalty = coefficient * multiplier * breadth * confidence
        penalty_total += penalty

        if outcome.status is CheckStatus.FAIL:
            failing.append(check.id)

        confidence_accum += confidence * coefficient
        confidence_weight += coefficient
        plain_confidences.append(confidence)

        row.update(
            {
                "status_multiplier": multiplier,
                "penalty": round(penalty, 6),
                "counted_in_budget": True,
                "breadth": round(breadth, 6),
                "formula": (
                    f"penalty = {round(coefficient, 6)} x {multiplier} x "
                    f"{round(breadth, 6)} x {confidence} = {round(penalty, 6)}"
                ),
            }
        )
        rows.append(row)

    if not applicable:
        status: CategoryStatus = "NOT_APPLICABLE"
        score: float | None = None
        coverage = 0.0
        mean_confidence = 0.0
    elif not scored and absolute:
        # 한 항목도 재지 못한 영역. 사라지지 않고 0점으로 남는다 — 자격증명이 없어
        # 못 잰 10점어치가 조용히 분모에서 빠지면 전체 점수가 그만큼 부풀려진다.
        status = "SCORED"
        score = 0.0
        coverage = 0.0
        mean_confidence = 0.0
    elif not scored:
        status = "UNKNOWN"
        score = None
        coverage = 0.0
        mean_confidence = 0.0
    else:
        status = "SCORED"
        coverage = len(scored) / len(applicable)
        # A zero budget means only zero-coefficient (INFO) checks were scored:
        # there is nothing that could have been lost, so the category is intact.
        score = (
            round(100.0 * max(0.0, 1.0 - penalty_total / budget), 6) if budget > 0 else 100.0
        )
        if confidence_weight > 0:
            mean_confidence = confidence_accum / confidence_weight
        else:
            mean_confidence = sum(plain_confidences) / len(plain_confidences)

    confidence_value = round(coverage * mean_confidence, 6)

    category_score = CategoryScore(
        category_id=category.id,
        name_ko=category.name_ko,
        name_en=category.name_en,
        weight=category.weight,
        status=status,
        score=score,
        budget=round(budget, 6),
        penalty_total=round(penalty_total, 6),
        coverage=round(coverage, 6),
        confidence=confidence_value,
        applicable_check_ids=applicable,
        scored_check_ids=scored,
        not_applicable_check_ids=not_applicable,
        unknown_check_ids=unknown,
        failing_check_ids=failing,
    )

    category_row: dict[str, Any] = {
        "category_id": category.id,
        "name_ko": category.name_ko,
        "weight": category.weight,
        "status": status,
        "budget": round(budget, 6),
        "penalty_total": round(penalty_total, 6),
        "score": score,
        "coverage": round(coverage, 6),
        "confidence": confidence_value,
        "applicable_check_ids": applicable,
        "scored_check_ids": scored,
        "not_applicable_check_ids": not_applicable,
        "unknown_check_ids": unknown,
        "formula": "category_score = 100 x max(0, 1 - penalty_total / budget)",
    }

    return category_score, category_row, rows


def _trigger_matches(trigger: Trigger, by_id: dict[str, CheckOutcome]) -> list[str]:
    matched: list[str] = []
    for condition in trigger.any_of:
        outcome = by_id.get(condition.check_id)
        if outcome is None or outcome.status is not condition.status:
            continue
        if condition.min_coverage is not None and outcome.coverage_ratio < condition.min_coverage:
            continue
        matched.append(condition.check_id)
    return matched


def _apply_caps(spec: ScoringSpec, by_id: dict[str, CheckOutcome]) -> list[AppliedCap]:
    applied: list[AppliedCap] = []
    for cap in _sorted_caps(spec.caps):
        matched = _trigger_matches(cap.trigger, by_id)
        if matched:
            applied.append(
                AppliedCap(
                    cap_id=cap.id,
                    max_overall_score=cap.max_overall_score,
                    reason_ko=cap.reason_ko,
                    release_condition_ko=cap.release_condition_ko,
                    triggered_by=matched,
                )
            )
    return applied


def _sorted_caps(caps: Sequence[SpecCap]) -> list[SpecCap]:
    return sorted(caps, key=lambda cap: (cap.max_overall_score, cap.id))


def _raise_gates(spec: ScoringSpec, by_id: dict[str, CheckOutcome]) -> list[RaisedGate]:
    raised: list[RaisedGate] = []
    for gate in _sorted_gates(spec.gates):
        matched = _trigger_matches(gate.trigger, by_id)
        if matched:
            raised.append(
                RaisedGate(
                    gate_id=gate.id,
                    status_code=gate.status_code,
                    label_ko=gate.label_ko,
                    label_en=gate.label_en,
                    description_ko=gate.description_ko,
                    triggered_by=matched,
                )
            )
    return raised


def _sorted_gates(gates: Sequence[SpecGate]) -> list[SpecGate]:
    return sorted(gates, key=lambda gate: gate.id)
