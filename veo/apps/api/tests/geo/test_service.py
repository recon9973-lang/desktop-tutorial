"""End-to-end GEO readiness behaviour, fixture by fixture.

The assertions here are the methodology, not the implementation: a gate never moves the
number, blocking a training crawler is free, and an absent schema is not a fault.
"""

from __future__ import annotations

import re

import pytest
from tests.geo.support import load_case, replace_robots

from veo.geo.service import GEO_SPEC_ID, run_geo_readiness
from veo.scoring import CheckStatus, ScoringSpec

PLAIN_ROBOTS = "User-agent: *\nAllow: /\nSitemap: https://best.example.com/sitemap.xml\n"


def status_of(report: object, check_id: str) -> CheckStatus:
    outcomes = {o.check_id: o for o in report.score.outcomes}  # type: ignore[attr-defined]
    return outcomes[check_id].status


# --------------------------------------------------------------------------- #
# The score is always a readiness score, and it is always traceable
# --------------------------------------------------------------------------- #


def test_a_report_names_the_specification_that_produced_it(case_name: str) -> None:
    report = run_geo_readiness(load_case(case_name).context)
    assert report.score.spec_id == GEO_SPEC_ID
    assert report.score.spec_version
    assert report.score.spec_checksum


def test_the_engine_refuses_a_specification_from_another_domain() -> None:
    from veo.scoring import latest_published

    case = load_case("hospital_local")
    seo = latest_published("veo.seo.readiness")
    with pytest.raises(ValueError, match=re.escape("veo.geo.readiness")):
        run_geo_readiness(case.context, spec=seo)


# --------------------------------------------------------------------------- #
# Gates sit beside the number; they never change it
# --------------------------------------------------------------------------- #


def test_a_noindex_page_raises_exposure_blocked() -> None:
    report = run_geo_readiness(load_case("noindex_page").context)
    assert "EXPOSURE_BLOCKED" in report.gate_status_codes
    assert status_of(report, "geo.access.indexable") is CheckStatus.FAIL


def test_a_noindex_page_keeps_the_score_the_arithmetic_produced() -> None:
    """The same outcomes, scored by a specification with no gates at all, must tie."""
    case = load_case("noindex_page")
    report = run_geo_readiness(case.context)

    ungated: ScoringSpec = case.context.spec.model_copy(update={"gates": ()})
    without_gates = run_geo_readiness(case.context, spec=ungated)

    assert without_gates.gate_status_codes == ()
    assert report.score.overall_score == without_gates.score.overall_score
    assert report.score.overall_score == report.score.overall_score_before_caps
    assert report.score.applied_caps == []


def test_a_blocked_page_can_still_score_well() -> None:
    """A page may be structurally excellent and still be invisible. Both must show."""
    report = run_geo_readiness(load_case("noindex_page").context)
    assert report.score.overall_score is not None
    assert report.score.overall_score > 60.0
    assert report.score.band_id not in {"blocked", "poor"}
    assert "EXPOSURE_BLOCKED" in report.gate_status_codes


def test_an_http_error_raises_exposure_blocked() -> None:
    report = run_geo_readiness(load_case("http_error").context)
    assert "EXPOSURE_BLOCKED" in report.gate_status_codes
    assert status_of(report, "geo.access.http_status_ok") is CheckStatus.FAIL


def test_authentication_raises_exposure_blocked() -> None:
    report = run_geo_readiness(load_case("auth_required").context)
    assert "EXPOSURE_BLOCKED" in report.gate_status_codes
    assert status_of(report, "geo.access.no_auth_required") is CheckStatus.FAIL


def test_blocking_search_crawlers_raises_its_own_gate() -> None:
    report = run_geo_readiness(load_case("search_crawler_blocked").context)
    assert "SEARCH_CRAWLER_BLOCKED" in report.gate_status_codes
    assert status_of(report, "geo.access.search_bots_allowed") is CheckStatus.FAIL


def test_contradictory_structured_data_raises_the_mismatch_gate() -> None:
    report = run_geo_readiness(load_case("contradictory_schema").context)
    assert "STRUCTURED_DATA_MISMATCH" in report.gate_status_codes
    assert status_of(report, "geo.sd.matches_visible_content") is CheckStatus.FAIL


def test_a_healthy_page_raises_no_gate() -> None:
    report = run_geo_readiness(load_case("hospital_local").context)
    assert report.gate_status_codes == ()


# --------------------------------------------------------------------------- #
# Blocking training crawlers is a business choice, not a fault
# --------------------------------------------------------------------------- #


def test_blocking_only_training_crawlers_costs_exactly_nothing() -> None:
    blocked = run_geo_readiness(load_case("training_bot_blocked").context)
    plain = run_geo_readiness(load_case("generic_service").context)

    assert blocked.score.overall_score == plain.score.overall_score
    assert blocked.score.band_id == plain.score.band_id
    assert blocked.gate_status_codes == plain.gate_status_codes
    assert "SEARCH_CRAWLER_BLOCKED" not in blocked.gate_status_codes


def test_search_crawlers_stay_allowed_when_only_training_crawlers_are_disallowed() -> None:
    report = run_geo_readiness(load_case("training_bot_blocked").context)
    assert status_of(report, "geo.access.search_bots_allowed") is CheckStatus.PASS


def test_declaring_a_training_policy_is_information_only() -> None:
    declared = run_geo_readiness(load_case("training_bot_blocked").context)
    silent = run_geo_readiness(
        replace_robots(load_case("training_bot_blocked"), PLAIN_ROBOTS).context
    )
    assert status_of(declared, "geo.access.training_bot_policy_declared") is CheckStatus.PASS
    assert status_of(silent, "geo.access.training_bot_policy_declared") is not CheckStatus.PASS
    assert declared.score.overall_score == silent.score.overall_score


def test_a_hospital_blocking_training_crawlers_is_still_ready() -> None:
    report = run_geo_readiness(load_case("hospital_local").context)
    assert status_of(report, "geo.access.training_bot_policy_declared") is CheckStatus.PASS
    assert status_of(report, "geo.access.search_bots_allowed") is CheckStatus.PASS
    assert report.score.overall_score is not None
    assert report.score.overall_score >= 85.0


# --------------------------------------------------------------------------- #
# Missing schema is not a fault
# --------------------------------------------------------------------------- #


def test_a_page_without_structured_data_is_not_penalised() -> None:
    report = run_geo_readiness(load_case("no_schema").context)
    for check_id in (
        "geo.sd.valid_syntax",
        "geo.sd.matches_visible_content",
        "geo.sd.page_type_appropriate",
    ):
        assert status_of(report, check_id) is CheckStatus.NOT_APPLICABLE, check_id

    category = report.score.category("structured_data_meta")
    assert set(category.not_applicable_check_ids) >= {
        "geo.sd.valid_syntax",
        "geo.sd.matches_visible_content",
        "geo.sd.page_type_appropriate",
    }
    assert not set(category.failing_check_ids) & {
        "geo.sd.valid_syntax",
        "geo.sd.matches_visible_content",
        "geo.sd.page_type_appropriate",
    }
    assert "STRUCTURED_DATA_MISMATCH" not in report.gate_status_codes


def test_absent_structured_data_leaves_the_entity_graph_check_out_of_the_denominator() -> None:
    report = run_geo_readiness(load_case("no_schema").context)
    assert status_of(report, "geo.entity.stable_id_graph") is CheckStatus.NOT_APPLICABLE


# --------------------------------------------------------------------------- #
# A business with no premises is not failing its address check
# --------------------------------------------------------------------------- #


def test_an_online_only_business_is_not_failed_for_having_no_address() -> None:
    report = run_geo_readiness(load_case("no_schema").context)
    assert status_of(report, "geo.entity.nap_consistent") is CheckStatus.NOT_APPLICABLE


def test_a_business_with_premises_is_checked_against_the_official_record() -> None:
    with_premises = run_geo_readiness(load_case("hospital_local").context)
    contradicting = run_geo_readiness(load_case("contradictory_schema").context)

    assert status_of(with_premises, "geo.entity.nap_consistent") is CheckStatus.PASS
    assert status_of(contradicting, "geo.entity.nap_consistent") is CheckStatus.FAIL


# --------------------------------------------------------------------------- #
# Dates
# --------------------------------------------------------------------------- #


def test_a_date_that_moved_without_the_content_moving_fails() -> None:
    report = run_geo_readiness(load_case("untruthful_dates").context)
    assert status_of(report, "geo.fresh.dates_truthful") is CheckStatus.FAIL


def test_date_truthfulness_is_unknown_without_history() -> None:
    report = run_geo_readiness(load_case("ecommerce_product").context)
    assert status_of(report, "geo.fresh.dates_truthful") in {
        CheckStatus.UNKNOWN,
        CheckStatus.NOT_APPLICABLE,
    }


def test_areas_we_cannot_reach_are_declared_outside_the_score() -> None:
    """외부 출처는 수집 경로가 없다. 그러면 **애초에 점수의 일부가 아니라고 적는다.**

    1.0.0 은 이 영역을 점수 안에 두고, 못 재면 분모에서 빼는 방식이었다. 그러면 잴 수
    없다는 사실이 조용히 분모를 줄여 점수를 올린다 — 1.1.0 에서 선언으로 옮겼다.

    영역이 사라지는 것은 아니다. "이 진단의 배점 밖" 으로 사유와 함께 계속 보고된다.
    """
    report = run_geo_readiness(load_case("no_schema").context)
    external = report.score.category("external_verifiability")

    assert external is not None, "점수 밖이어도 보고에서 빠지면 안 된다"
    assert external.not_applicable_check_ids, "수집 경로가 없는 항목은 해당 없음으로 남는다"
    assert external.unknown_check_ids == []


def test_the_denominator_does_not_shrink_when_we_cannot_measure() -> None:
    """분모가 움직이는 것이 이 제품에서 가장 비싸게 배운 결함이다.

    못 잰 항목이 배점을 들고 나가면 **적게 잴수록 점수가 오른다.** 그래서 점수를 이루는
    영역의 배점 합은 무엇을 쟀든 늘 100 이어야 한다.
    """
    report = run_geo_readiness(load_case("no_schema").context)
    spec = report.spec

    scored = sum(
        category.weight for category in spec.categories if category.contributes_to_score
    )

    assert scored == pytest.approx(100.0)
    assert spec.status_policy.unknown == "SCORE_AS_ZERO_KEEP_IN_DENOMINATOR"
    assert report.score.overall_score is not None


# --------------------------------------------------------------------------- #
# Evidence and issues
# --------------------------------------------------------------------------- #


def test_failures_are_turned_into_actionable_korean_issues() -> None:
    report = run_geo_readiness(load_case("generic_service").context)
    assert report.issues
    for issue in report.issues:
        assert issue.title_ko
        assert issue.summary_ko
        assert issue.remediation_ko
        assert issue.remediation_owner in {
            "DEVELOPER",
            "MARKETER",
            "BUSINESS_OWNER",
            "OPERATIONS",
        }


def test_every_issue_matches_a_failing_or_warning_outcome() -> None:
    report = run_geo_readiness(load_case("generic_service").context)
    troubled = {
        o.check_id
        for o in report.score.outcomes
        if o.status in {CheckStatus.FAIL, CheckStatus.WARNING}
    }
    assert {issue.check_id for issue in report.issues} <= troubled


def test_evidence_records_carry_a_content_hash(case_name: str) -> None:
    report = run_geo_readiness(load_case(case_name).context)
    for record in report.evidence:
        assert len(record.content_hash) == 64
        assert record.kind
