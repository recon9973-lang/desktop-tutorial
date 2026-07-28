"""Behavioural contract of the VEO scoring evaluator.

Rules under test (from VEO-LAB methodology):
  * N/A is not zero — it leaves the denominator entirely.
  * UNKNOWN is not a failure — it reduces coverage and confidence, never the score.
  * Weights, severities and caps come only from the versioned spec.
  * Every score carries its raw inputs, denominator, calculation trace and confidence.
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from veo.scoring import (
    CheckOutcome,
    CheckStatus,
    ScoringSpecError,
    build_spec,
    evaluate,
)

pytestmark = pytest.mark.filterwarnings("error")


def outcome(
    check_id: str,
    status: CheckStatus,
    *,
    confidence: float = 1.0,
    affected: float = 1.0,
    evaluated: float = 1.0,
) -> CheckOutcome:
    return CheckOutcome(
        check_id=check_id,
        status=status,
        confidence=confidence,
        affected_weight=affected,
        evaluated_weight=evaluated,
        evidence_ids=[f"ev::{check_id}"],
    )


ALL_CHECKS = (
    "test.a.blocker",
    "test.a.major",
    "test.a.info",
    "test.b.critical",
    "test.b.minor",
)


def outcomes(**overrides: CheckOutcome) -> list[CheckOutcome]:
    """All checks PASS unless overridden by ``check_id.replace('.', '_')``."""
    result = []
    for check_id in ALL_CHECKS:
        key = check_id.replace(".", "_")
        result.append(overrides.get(key, outcome(check_id, CheckStatus.PASS)))
    return result


# --------------------------------------------------------------------------- #
# Baseline
# --------------------------------------------------------------------------- #


def test_all_pass_scores_100(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(spec, outcomes())

    assert result.overall_score == 100.0
    assert result.overall_score_before_caps == 100.0
    assert result.coverage == 1.0
    assert result.confidence == 1.0
    assert result.applied_caps == []
    assert result.gates == []
    assert result.band_id == "ready"


def test_score_carries_spec_identity(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(spec, outcomes())

    assert result.spec_id == "veo.test.tiny"
    assert result.spec_version == "1.0.0"
    assert result.spec_checksum == spec.checksum
    assert len(result.spec_checksum) == 64


# --------------------------------------------------------------------------- #
# Penalty arithmetic
# --------------------------------------------------------------------------- #


def test_single_fail_uses_severity_over_category_budget(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(
        spec, outcomes(test_a_major=outcome("test.a.major", CheckStatus.FAIL))
    )

    # cat_a budget = 1.00 + 0.30 + 0.00 = 1.30 ; penalty = 0.30
    cat_a = result.category("cat_a")
    assert cat_a.budget == pytest.approx(1.30)
    assert cat_a.penalty_total == pytest.approx(0.30)
    assert cat_a.score == pytest.approx(100 * (1 - 0.30 / 1.30))

    expected_overall = (cat_a.score * 70 + 100.0 * 30) / 100
    assert result.overall_score == pytest.approx(expected_overall)


def test_warning_costs_half_of_a_failure(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    warned = evaluate(
        spec, outcomes(test_a_major=outcome("test.a.major", CheckStatus.WARNING))
    )
    failed = evaluate(
        spec, outcomes(test_a_major=outcome("test.a.major", CheckStatus.FAIL))
    )

    assert warned.category("cat_a").penalty_total == pytest.approx(0.15)
    assert failed.category("cat_a").penalty_total == pytest.approx(0.30)


def test_coverage_ratio_scales_the_penalty(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(
        spec,
        outcomes(
            test_a_major=outcome(
                "test.a.major", CheckStatus.FAIL, affected=3.0, evaluated=12.0
            )
        ),
    )
    # coverage_i = 3/12 = 0.25 -> penalty = 0.30 * 0.25 = 0.075
    assert result.category("cat_a").penalty_total == pytest.approx(0.075)


def test_confidence_scales_the_penalty(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(
        spec, outcomes(test_a_major=outcome("test.a.major", CheckStatus.FAIL, confidence=0.5))
    )
    assert result.category("cat_a").penalty_total == pytest.approx(0.15)


def test_info_severity_cannot_reduce_the_score(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(spec, outcomes(test_a_info=outcome("test.a.info", CheckStatus.FAIL)))

    assert result.category("cat_a").penalty_total == pytest.approx(0.0)
    assert result.category("cat_a").score == pytest.approx(100.0)


def test_score_is_clamped_at_zero(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(
        spec,
        outcomes(
            test_b_critical=outcome("test.b.critical", CheckStatus.FAIL),
            test_b_minor=outcome("test.b.minor", CheckStatus.FAIL),
        ),
    )
    assert result.category("cat_b").score == pytest.approx(0.0)
    assert result.overall_score >= 0.0


# --------------------------------------------------------------------------- #
# N/A — must leave the denominator, must never read as zero
# --------------------------------------------------------------------------- #


def test_not_applicable_leaves_the_category_denominator(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(
        spec,
        outcomes(
            test_a_major=outcome("test.a.major", CheckStatus.NOT_APPLICABLE),
            test_a_blocker=outcome("test.a.blocker", CheckStatus.FAIL),
        ),
    )
    cat_a = result.category("cat_a")
    # budget drops from 1.30 to 1.00 because the MAJOR check is not applicable
    assert cat_a.budget == pytest.approx(1.00)
    assert cat_a.not_applicable_check_ids == ["test.a.major"]
    assert cat_a.score == pytest.approx(0.0)


def test_not_applicable_is_not_scored_as_failure(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(
        spec, outcomes(test_a_major=outcome("test.a.major", CheckStatus.NOT_APPLICABLE))
    )
    assert result.category("cat_a").score == pytest.approx(100.0)
    assert result.overall_score == pytest.approx(100.0)


def test_fully_not_applicable_category_is_excluded_and_weight_redistributed(
    tiny_spec_dict: dict[str, Any],
) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(
        spec,
        outcomes(
            test_b_critical=outcome("test.b.critical", CheckStatus.NOT_APPLICABLE),
            test_b_minor=outcome("test.b.minor", CheckStatus.NOT_APPLICABLE),
            test_a_major=outcome("test.a.major", CheckStatus.FAIL),
        ),
    )
    cat_b = result.category("cat_b")
    assert cat_b.status == "NOT_APPLICABLE"
    assert cat_b.score is None
    # cat_a now carries the whole weight
    assert result.effective_weight_total == pytest.approx(70.0)
    assert result.overall_score == pytest.approx(result.category("cat_a").score)


def test_all_categories_not_applicable_yields_unscoreable(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(
        spec,
        [outcome(cid, CheckStatus.NOT_APPLICABLE) for cid in ALL_CHECKS],
    )
    assert result.overall_score is None
    assert result.status == "NOT_APPLICABLE"


# --------------------------------------------------------------------------- #
# UNKNOWN — never a failure, always visible in coverage and confidence
# --------------------------------------------------------------------------- #


def test_unknown_adds_no_penalty(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(
        spec, outcomes(test_a_blocker=outcome("test.a.blocker", CheckStatus.UNKNOWN))
    )
    cat_a = result.category("cat_a")
    assert cat_a.penalty_total == pytest.approx(0.0)
    assert cat_a.score == pytest.approx(100.0)


def test_unknown_lowers_coverage_and_confidence(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(
        spec, outcomes(test_a_blocker=outcome("test.a.blocker", CheckStatus.UNKNOWN))
    )
    cat_a = result.category("cat_a")

    assert cat_a.unknown_check_ids == ["test.a.blocker"]
    assert cat_a.coverage == pytest.approx(2 / 3)
    assert cat_a.confidence < 1.0
    assert result.coverage < 1.0
    assert result.confidence < 1.0


def test_unknown_is_excluded_from_the_budget(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(
        spec,
        outcomes(
            test_a_blocker=outcome("test.a.blocker", CheckStatus.UNKNOWN),
            test_a_major=outcome("test.a.major", CheckStatus.FAIL),
        ),
    )
    # budget = MAJOR only (0.30); INFO contributes 0 -> score collapses to 0
    cat_a = result.category("cat_a")
    assert cat_a.budget == pytest.approx(0.30)
    assert cat_a.score == pytest.approx(0.0)


def test_unknown_does_not_count_as_not_applicable(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(spec, outcomes(test_b_minor=outcome("test.b.minor", CheckStatus.UNKNOWN)))
    cat_b = result.category("cat_b")
    assert cat_b.status == "SCORED"
    assert cat_b.not_applicable_check_ids == []
    assert cat_b.unknown_check_ids == ["test.b.minor"]


# --------------------------------------------------------------------------- #
# Caps — bounded overall score, with reason and release condition
# --------------------------------------------------------------------------- #


def test_cap_bounds_the_overall_score(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(
        spec,
        outcomes(test_a_blocker=outcome("test.a.blocker", CheckStatus.FAIL)),
    )
    assert result.overall_score_before_caps > 25.0
    assert result.overall_score == pytest.approx(25.0)

    assert len(result.applied_caps) == 1
    cap = result.applied_caps[0]
    assert cap.cap_id == "hard_block"
    assert cap.max_overall_score == 25.0
    assert cap.reason_ko
    assert cap.release_condition_ko


def test_cap_respects_min_coverage(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(
        spec,
        outcomes(
            test_a_blocker=outcome(
                "test.a.blocker", CheckStatus.FAIL, affected=1.0, evaluated=10.0
            )
        ),
    )
    # coverage 0.1 < min_coverage 0.9 -> no cap
    assert result.applied_caps == []
    assert result.overall_score == result.overall_score_before_caps


def test_cap_never_raises_a_lower_score(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(
        spec,
        outcomes(
            test_a_blocker=outcome("test.a.blocker", CheckStatus.FAIL),
            test_a_major=outcome("test.a.major", CheckStatus.FAIL),
            test_b_critical=outcome("test.b.critical", CheckStatus.FAIL),
            test_b_minor=outcome("test.b.minor", CheckStatus.FAIL),
        ),
    )
    assert result.overall_score == pytest.approx(0.0)
    assert result.overall_score <= result.overall_score_before_caps


# --------------------------------------------------------------------------- #
# Gates — separate status, never folded into the number
# --------------------------------------------------------------------------- #


def test_gate_is_reported_without_changing_the_score(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    with_gate = evaluate(
        spec, outcomes(test_b_critical=outcome("test.b.critical", CheckStatus.FAIL))
    )

    assert [g.status_code for g in with_gate.gates] == ["EXPOSURE_BLOCKED"]
    # the number is exactly what the penalty arithmetic produced — the gate adds nothing
    cat_b_score = 100 * (1 - 0.60 / 0.70)
    assert with_gate.overall_score == pytest.approx((100.0 * 70 + cat_b_score * 30) / 100)


# --------------------------------------------------------------------------- #
# Input integrity
# --------------------------------------------------------------------------- #


def test_unknown_check_id_is_rejected(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    with pytest.raises(ScoringSpecError, match="not defined"):
        evaluate(spec, [*outcomes(), outcome("test.a.ghost", CheckStatus.PASS)])


def test_missing_outcome_is_rejected(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    partial = [o for o in outcomes() if o.check_id != "test.b.minor"]
    with pytest.raises(ScoringSpecError, match="missing"):
        evaluate(spec, partial)


def test_duplicate_outcome_is_rejected(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    with pytest.raises(ScoringSpecError, match=r"[Dd]uplicate"):
        evaluate(spec, [*outcomes(), outcome("test.b.minor", CheckStatus.PASS)])


def test_category_weights_must_be_positive(tiny_spec_dict: dict[str, Any]) -> None:
    tiny_spec_dict["categories"][0]["weight"] = 0
    with pytest.raises(ScoringSpecError):
        build_spec(tiny_spec_dict)


def test_duplicate_check_id_across_categories_is_rejected(
    tiny_spec_dict: dict[str, Any],
) -> None:
    tiny_spec_dict["categories"][1]["checks"].append(
        {
            "id": "test.a.major",
            "title_ko": "x",
            "title_en": "x",
            "severity": "MAJOR",
            "scope": "URL",
            "remediation_owner": "DEVELOPER",
        }
    )
    with pytest.raises(ScoringSpecError, match=r"[Dd]uplicate"):
        build_spec(tiny_spec_dict)


def test_cap_referencing_unknown_check_is_rejected(tiny_spec_dict: dict[str, Any]) -> None:
    tiny_spec_dict["caps"][0]["trigger"]["any_of"][0]["check_id"] = "test.a.ghost"
    with pytest.raises(ScoringSpecError, match="not defined"):
        build_spec(tiny_spec_dict)


def test_confidence_outside_unit_interval_is_rejected(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    with pytest.raises(ValueError):
        evaluate(
            spec,
            outcomes(
                test_a_major=outcome("test.a.major", CheckStatus.FAIL, confidence=1.4)
            ),
        )


def test_affected_weight_above_evaluated_weight_is_rejected(
    tiny_spec_dict: dict[str, Any],
) -> None:
    spec = build_spec(tiny_spec_dict)
    with pytest.raises(ValueError):
        evaluate(
            spec,
            outcomes(
                test_a_major=outcome(
                    "test.a.major", CheckStatus.FAIL, affected=5.0, evaluated=2.0
                )
            ),
        )


# --------------------------------------------------------------------------- #
# Traceability & determinism
# --------------------------------------------------------------------------- #


def test_trace_records_every_check_and_the_denominators(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(
        spec,
        outcomes(
            test_a_major=outcome("test.a.major", CheckStatus.FAIL, affected=2.0, evaluated=4.0),
            test_b_minor=outcome("test.b.minor", CheckStatus.UNKNOWN),
        ),
    )
    trace = result.trace

    assert trace["spec"]["checksum"] == spec.checksum
    traced_ids = {row["check_id"] for row in trace["checks"]}
    assert traced_ids == set(ALL_CHECKS)

    failed_row = next(r for r in trace["checks"] if r["check_id"] == "test.a.major")
    assert failed_row["severity_coefficient"] == pytest.approx(0.30)
    assert failed_row["status_multiplier"] == pytest.approx(1.0)
    assert failed_row["coverage_ratio"] == pytest.approx(0.5)
    assert failed_row["confidence"] == pytest.approx(1.0)
    assert failed_row["penalty"] == pytest.approx(0.15)
    assert failed_row["formula"]

    cat_a_row = next(r for r in trace["categories"] if r["category_id"] == "cat_a")
    assert cat_a_row["budget"] == pytest.approx(1.30)
    assert cat_a_row["penalty_total"] == pytest.approx(0.15)

    assert trace["overall"]["effective_weight_total"] == pytest.approx(100.0)
    assert "renormalised" in trace["overall"]


def test_trace_is_json_serialisable(tiny_spec_dict: dict[str, Any]) -> None:
    import json

    spec = build_spec(tiny_spec_dict)
    result = evaluate(spec, outcomes(test_a_blocker=outcome("test.a.blocker", CheckStatus.FAIL)))
    encoded = json.dumps(result.trace, ensure_ascii=False, sort_keys=True)
    assert json.loads(encoded) == result.trace


def test_evaluation_is_deterministic(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    given = outcomes(
        test_a_major=outcome("test.a.major", CheckStatus.FAIL, affected=1.0, evaluated=3.0),
        test_b_minor=outcome("test.b.minor", CheckStatus.WARNING, confidence=0.9),
    )
    first = evaluate(spec, given)
    second = evaluate(spec, list(reversed(given)))

    assert first.overall_score == second.overall_score
    assert first.trace["categories"] == second.trace["categories"]


def test_checksum_changes_when_a_weight_changes(tiny_spec_dict: dict[str, Any]) -> None:
    original = build_spec(tiny_spec_dict).checksum
    tiny_spec_dict["categories"][0]["weight"] = 60
    assert build_spec(tiny_spec_dict).checksum != original


def test_no_nan_or_infinity_leaks_into_results(tiny_spec_dict: dict[str, Any]) -> None:
    spec = build_spec(tiny_spec_dict)
    result = evaluate(
        spec,
        outcomes(
            test_a_major=outcome("test.a.major", CheckStatus.FAIL, affected=0.0, evaluated=0.0)
        ),
    )
    for value in (result.overall_score, result.coverage, result.confidence):
        assert value is None or math.isfinite(value)
