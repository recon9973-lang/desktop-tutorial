"""Evidence transparency, and corroboration from outside the site.

The external checks need an outside source. Without one they say UNKNOWN — which lowers
coverage and leaves the gap on screen — rather than guessing in either direction.
"""

from __future__ import annotations

from dataclasses import replace

from tests.geo.support import load_case

from veo.geo.collectors.evidence_transparency import EvidenceTransparencyCollector
from veo.geo.collectors.external_verifiability import ExternalVerifiabilityCollector
from veo.scoring import CheckStatus


def evidence(name: str) -> dict[str, CheckStatus]:
    result = EvidenceTransparencyCollector().collect(load_case(name).context)
    return {o.check_id: o.status for o in result.outcomes}


def external(name: str) -> dict[str, CheckStatus]:
    result = ExternalVerifiabilityCollector().collect(load_case(name).context)
    return {o.check_id: o.status for o in result.outcomes}


# --------------------------------------------------------------------------- #
# Evidence transparency
# --------------------------------------------------------------------------- #


def test_an_article_that_links_its_sources_passes() -> None:
    statuses = evidence("publisher_article")
    assert statuses["geo.evidence.claims_have_sources"] is CheckStatus.PASS
    assert statuses["geo.evidence.author_identified"] is CheckStatus.PASS
    assert statuses["geo.evidence.publisher_identified"] is CheckStatus.PASS
    assert statuses["geo.evidence.method_disclosed"] is CheckStatus.PASS
    assert statuses["geo.evidence.primary_source_linked"] is CheckStatus.PASS


def test_numbers_asserted_without_a_source_fail() -> None:
    assert evidence("generic_service")["geo.evidence.claims_have_sources"] is CheckStatus.FAIL


def test_a_product_page_is_not_asked_for_a_byline() -> None:
    statuses = evidence("ecommerce_product")
    assert statuses["geo.evidence.author_identified"] is CheckStatus.NOT_APPLICABLE


def test_an_article_without_a_byline_fails() -> None:
    assert evidence("no_schema")["geo.evidence.author_identified"] is CheckStatus.FAIL


def test_a_reviewer_counts_as_an_identified_author() -> None:
    assert evidence("hospital_local")["geo.evidence.author_identified"] is CheckStatus.PASS


def test_a_footer_with_no_contact_path_does_not_identify_a_publisher() -> None:
    assert evidence("generic_service")["geo.evidence.publisher_identified"] in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


def test_a_page_with_no_figures_of_its_own_is_not_asked_for_a_method() -> None:
    assert evidence("corporate_site")["geo.evidence.method_disclosed"] is CheckStatus.NOT_APPLICABLE


def test_a_claim_of_being_first_without_a_method_fails() -> None:
    assert evidence("generic_service")["geo.evidence.method_disclosed"] is CheckStatus.FAIL


def test_a_page_citing_nothing_external_is_not_asked_for_primary_sources() -> None:
    assert (
        evidence("corporate_site")["geo.evidence.primary_source_linked"]
        is CheckStatus.NOT_APPLICABLE
    )


def test_links_only_to_aggregators_do_not_pass_as_primary_sources() -> None:
    assert evidence("generic_service")["geo.evidence.primary_source_linked"] in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


def test_evidence_checks_are_labelled_as_heuristics() -> None:
    result = EvidenceTransparencyCollector().collect(load_case("publisher_article").context)
    for outcome in result.outcomes:
        assert outcome.confidence_level != "DIRECT_OBSERVATION", outcome.check_id


# --------------------------------------------------------------------------- #
# External verifiability
# --------------------------------------------------------------------------- #


def test_a_well_corroborated_entity_passes_every_external_check() -> None:
    statuses = external("hospital_local")
    assert statuses["geo.external.independent_sources_exist"] is CheckStatus.PASS
    assert statuses["geo.external.official_profiles_claimed"] is CheckStatus.PASS
    assert statuses["geo.external.source_type_diversity"] is CheckStatus.PASS
    assert statuses["geo.external.facts_agree_across_sources"] is CheckStatus.PASS


def test_one_dependent_source_fails_every_external_check() -> None:
    statuses = external("generic_service")
    assert statuses["geo.external.independent_sources_exist"] is CheckStatus.FAIL
    assert statuses["geo.external.source_type_diversity"] is CheckStatus.FAIL
    assert statuses["geo.external.official_profiles_claimed"] is CheckStatus.FAIL


def test_an_outside_source_that_disagrees_about_the_name_fails() -> None:
    statuses = external("generic_service")
    assert statuses["geo.external.facts_agree_across_sources"] is CheckStatus.FAIL


def test_with_no_provider_every_external_check_is_unknown() -> None:
    statuses = external("no_schema")
    assert set(statuses.values()) == {CheckStatus.UNKNOWN}


def test_a_disabled_provider_is_unknown_rather_than_a_failure() -> None:
    from veo.contracts.enums import ProviderState

    case = load_case("hospital_local")
    context = replace(
        case.context, provider_states={"geo_external": ProviderState.DISABLED_NO_CREDENTIAL}
    )
    result = ExternalVerifiabilityCollector().collect(context)
    assert {o.status for o in result.outcomes} == {CheckStatus.UNKNOWN}


def test_external_findings_are_labelled_as_outside_estimates() -> None:
    result = ExternalVerifiabilityCollector().collect(load_case("hospital_local").context)
    for outcome in result.outcomes:
        assert outcome.confidence_level == "EXTERNAL_ESTIMATE", outcome.check_id
