"""Entity clarity: who this is, said the same way everywhere."""

from __future__ import annotations

from tests.geo.support import load_case

from veo.geo.collectors.entity_clarity import EntityClarityCollector
from veo.scoring import CheckStatus


def run(name: str) -> dict[str, CheckStatus]:
    result = EntityClarityCollector().collect(load_case(name).context)
    return {o.check_id: o.status for o in result.outcomes}


def test_a_complete_entity_graph_passes() -> None:
    statuses = run("hospital_local")
    assert statuses["geo.entity.organization_identified"] is CheckStatus.PASS
    assert statuses["geo.entity.stable_id_graph"] is CheckStatus.PASS
    assert statuses["geo.entity.sameas_profiles_present"] is CheckStatus.PASS
    assert statuses["geo.entity.name_consistent_across_pages"] is CheckStatus.PASS
    assert statuses["geo.entity.nap_consistent"] is CheckStatus.PASS
    assert statuses["geo.entity.disambiguation_signals"] is CheckStatus.PASS


def test_a_page_with_no_organization_signal_fails_identification() -> None:
    assert run("no_schema")["geo.entity.organization_identified"] is CheckStatus.FAIL


def test_structured_data_without_identifiers_fails_the_graph_check() -> None:
    assert run("generic_service")["geo.entity.stable_id_graph"] is CheckStatus.FAIL


def test_no_structured_data_means_the_graph_check_does_not_apply() -> None:
    assert run("no_schema")["geo.entity.stable_id_graph"] is CheckStatus.NOT_APPLICABLE


def test_missing_official_profiles_fail_the_sameas_check() -> None:
    assert run("generic_service")["geo.entity.sameas_profiles_present"] is CheckStatus.FAIL


def test_a_brand_named_three_ways_fails_the_consistency_check() -> None:
    assert run("generic_service")["geo.entity.name_consistent_across_pages"] is CheckStatus.FAIL


def test_a_business_without_premises_is_not_asked_for_an_address() -> None:
    assert run("no_schema")["geo.entity.nap_consistent"] is CheckStatus.NOT_APPLICABLE


def test_an_address_that_contradicts_the_official_record_fails() -> None:
    assert run("contradictory_schema")["geo.entity.nap_consistent"] is CheckStatus.FAIL


def test_a_page_with_no_distinguishing_detail_fails_disambiguation() -> None:
    assert run("generic_service")["geo.entity.disambiguation_signals"] is CheckStatus.FAIL


def test_entity_checks_cite_the_document_they_read() -> None:
    result = EntityClarityCollector().collect(load_case("hospital_local").context)
    assert result.evidence
    for outcome in result.outcomes:
        if outcome.status in {CheckStatus.PASS, CheckStatus.FAIL, CheckStatus.WARNING}:
            assert outcome.evidence_ids, outcome.check_id
