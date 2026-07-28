"""The GEO collectors must cover the published specification exactly.

This is the test that fails the day VEO-LAB adds a 38th check: a new check id in the
specification has no collector, so it can never be reported, and an unreported check is
silently missing from the evaluator's denominator. Failing here is how that stays loud.
"""

from __future__ import annotations

import pytest
from tests.geo.support import GeoCase, load_case

from veo.collect.contract import CollectionResult, run_collectors
from veo.geo.service import declared_check_ids, geo_collectors, run_geo_readiness
from veo.scoring import ScoringSpec

EXPECTED_CHECK_COUNT = 37

EXPECTED_CATEGORY_COLLECTORS = {
    "access_eligibility",
    "answer_extractability",
    "evidence_transparency",
    "entity_clarity",
    "structured_data_meta",
    "freshness_signals",
    "external_verifiability",
}


def test_the_specification_still_declares_thirty_seven_checks(spec: ScoringSpec) -> None:
    assert len(spec.check_ids) == EXPECTED_CHECK_COUNT


def test_there_is_one_collector_per_category(spec: ScoringSpec) -> None:
    assert {c.category_id for c in geo_collectors()} == EXPECTED_CATEGORY_COLLECTORS
    assert {c.id for c in spec.categories} == EXPECTED_CATEGORY_COLLECTORS


def test_collectors_cover_every_check_in_the_specification(spec: ScoringSpec) -> None:
    covered = declared_check_ids()
    missing = set(spec.check_ids) - covered
    assert not missing, f"no collector owns: {sorted(missing)}"


def test_collectors_never_claim_a_check_the_specification_does_not_define(
    spec: ScoringSpec,
) -> None:
    extra = declared_check_ids() - set(spec.check_ids)
    assert not extra, f"collectors claim checks absent from the spec: {sorted(extra)}"


def test_no_two_collectors_own_the_same_check() -> None:
    seen: dict[str, str] = {}
    for collector in geo_collectors():
        for check_id in collector.check_ids:
            assert check_id not in seen, (
                f"{check_id} is owned by both {seen.get(check_id)} and {collector.category_id}"
            )
            seen[check_id] = collector.category_id


def test_each_collector_owns_exactly_its_category_checks(spec: ScoringSpec) -> None:
    by_category = {c.id: {check.id for check in c.checks} for c in spec.categories}
    for collector in geo_collectors():
        assert collector.check_ids == frozenset(by_category[collector.category_id])


@pytest.mark.parametrize(
    "case_fixture", ["hospital_local", "generic_service", "no_schema", "http_error"]
)
def test_every_collector_reports_on_every_check_it_owns(case_fixture: str) -> None:
    """``run_collectors`` refuses silence — this proves it has nothing to refuse."""
    case: GeoCase = load_case(case_fixture)
    result: CollectionResult = run_collectors(list(geo_collectors()), case.context)
    assert result.outcome_ids() == declared_check_ids()


def test_a_full_run_produces_an_outcome_for_every_check(case_name: str) -> None:
    case = load_case(case_name)
    report = run_geo_readiness(case.context)
    assert {o.check_id for o in report.score.outcomes} == set(case.context.spec.check_ids)


def test_every_outcome_states_a_confidence_level_from_the_specification(
    case_name: str, spec: ScoringSpec
) -> None:
    """Confidence comes from the spec's vocabulary, never from a number in our code."""
    report = run_geo_readiness(load_case(case_name).context)
    for outcome in report.score.outcomes:
        if outcome.confidence_level is None:
            continue
        assert outcome.confidence_level in spec.confidence_levels, outcome.check_id


def test_judged_checks_never_claim_direct_observation(case_name: str) -> None:
    """Anything reasoned about rather than measured must say so."""
    judged = {
        "geo.extract.direct_answer_present",
        "geo.extract.passage_self_contained",
        "geo.extract.low_boilerplate_ratio",
        "geo.evidence.claims_have_sources",
        "geo.evidence.method_disclosed",
        "geo.evidence.primary_source_linked",
        "geo.entity.disambiguation_signals",
        "geo.entity.name_consistent_across_pages",
        "geo.fresh.no_stale_claims",
        "geo.sd.page_type_appropriate",
        "geo.meta.title_description_descriptive",
    }
    report = run_geo_readiness(load_case(case_name).context)
    for outcome in report.score.outcomes:
        if outcome.check_id in judged:
            assert outcome.confidence_level != "DIRECT_OBSERVATION", outcome.check_id


def test_non_trivial_outcomes_point_at_evidence(case_name: str) -> None:
    report = run_geo_readiness(load_case(case_name).context)
    known = {record.evidence_id for record in report.evidence}
    for outcome in report.score.outcomes:
        for evidence_id in outcome.evidence_ids:
            assert evidence_id in known, f"{outcome.check_id} cites unknown {evidence_id}"
