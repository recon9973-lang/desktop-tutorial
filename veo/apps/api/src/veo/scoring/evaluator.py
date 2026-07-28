"""The single deterministic scoring evaluator used everywhere in VEO.

Every SEO and GEO readiness score in the product goes through :func:`evaluate`.
No checker, API handler or report template may compute a score of its own, and no
language model is allowed to produce or adjust one.

Arithmetic (VEO-LAB methodology):

    coverage_i     = affected_importance_weight / evaluated_importance_weight
    penalty_i      = severity_coefficient x status_multiplier x coverage_i x confidence_i
    category_budget= sum of severity_coefficient over checks that were actually scored
    category_score = 100 x max(0, 1 - sum(penalty_i) / category_budget)
    overall_score  = sum(category_score x weight) / sum(weight of scoreable categories)

    caps           = overall_score is then bounded from above; a cap never raises a score.
    gates          = reported beside the score; a gate never changes the number.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

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
    by_id = _index_outcomes(spec, outcomes)
    ordered = [by_id[check_id] for check_id in spec.check_ids]

    check_rows: list[dict[str, Any]] = []
    category_scores: list[CategoryScore] = []
    category_rows: list[dict[str, Any]] = []

    for category in spec.categories:
        score, row, traces = _score_category(spec, category, by_id)
        category_scores.append(score)
        category_rows.append(row)
        check_rows.extend(traces)

    scoreable = [c for c in category_scores if c.status == "SCORED"]
    effective_weight_total = sum(c.weight for c in scoreable)
    declared_weight_total = sum(c.weight for c in spec.categories)

    if scoreable:
        weighted_sum = sum((c.score or 0.0) * c.weight for c in scoreable)
        score_before_caps: float | None = weighted_sum / effective_weight_total
        result_status: CategoryStatus = "SCORED"
    else:
        weighted_sum = 0.0
        score_before_caps = None
        result_status = (
            "NOT_APPLICABLE"
            if all(c.status == "NOT_APPLICABLE" for c in category_scores)
            else "UNKNOWN"
        )

    applied_caps = _apply_caps(spec, by_id)
    if score_before_caps is None:
        overall_score: float | None = None
    else:
        overall_score = score_before_caps
        for cap in applied_caps:
            overall_score = min(overall_score, cap.max_overall_score)
        overall_score = round(max(0.0, min(100.0, overall_score)), 6)

    gates = _raise_gates(spec, by_id)

    measurable = [c for c in category_scores if c.status != "NOT_APPLICABLE"]
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
            "formula": (
                "overall = sum(category_score x weight)"
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

    for check in category.checks:
        outcome = by_id[check.id]
        coefficient = spec.severity_coefficient(check.severity)
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
        penalty = coefficient * multiplier * outcome.coverage_ratio * confidence
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
                "formula": (
                    f"penalty = {coefficient} x {multiplier} x "
                    f"{round(outcome.coverage_ratio, 6)} x {confidence} = {round(penalty, 6)}"
                ),
            }
        )
        rows.append(row)

    if not applicable:
        status: CategoryStatus = "NOT_APPLICABLE"
        score: float | None = None
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
