"""Structured data and meta.

Absence is not a fault. A declaration that contradicts the page is the serious finding.
"""

from __future__ import annotations

from tests.geo.support import load_case

from veo.geo.collectors.structured_data_meta import StructuredDataMetaCollector
from veo.scoring import CheckStatus

SD_CHECKS = (
    "geo.sd.valid_syntax",
    "geo.sd.matches_visible_content",
    "geo.sd.page_type_appropriate",
)


def run(name: str) -> dict[str, CheckStatus]:
    result = StructuredDataMetaCollector().collect(load_case(name).context)
    return {o.check_id: o.status for o in result.outcomes}


def test_valid_matching_structured_data_passes() -> None:
    statuses = run("hospital_local")
    assert statuses["geo.sd.valid_syntax"] is CheckStatus.PASS
    assert statuses["geo.sd.matches_visible_content"] is CheckStatus.PASS
    assert statuses["geo.sd.page_type_appropriate"] is CheckStatus.PASS
    assert statuses["geo.meta.title_description_descriptive"] is CheckStatus.PASS
    assert statuses["geo.meta.opengraph_present"] is CheckStatus.PASS


def test_no_structured_data_is_never_a_fault() -> None:
    statuses = run("no_schema")
    for check_id in SD_CHECKS:
        assert statuses[check_id] is CheckStatus.NOT_APPLICABLE, check_id


def test_meta_checks_still_apply_without_structured_data() -> None:
    statuses = run("no_schema")
    assert statuses["geo.meta.title_description_descriptive"] is CheckStatus.PASS
    assert statuses["geo.meta.opengraph_present"] is CheckStatus.FAIL


def test_unparseable_structured_data_fails_the_syntax_check() -> None:
    assert run("generic_service")["geo.sd.valid_syntax"] is CheckStatus.FAIL


def test_a_declared_type_that_does_not_suit_the_page_fails() -> None:
    assert run("generic_service")["geo.sd.page_type_appropriate"] is CheckStatus.FAIL


def test_a_product_page_declaring_product_passes_the_type_check() -> None:
    assert run("ecommerce_product")["geo.sd.page_type_appropriate"] is CheckStatus.PASS


def test_a_name_price_and_telephone_that_contradict_the_page_fail() -> None:
    statuses = run("contradictory_schema")
    assert statuses["geo.sd.matches_visible_content"] is CheckStatus.FAIL
    assert statuses["geo.sd.valid_syntax"] is CheckStatus.PASS


def test_the_mismatch_finding_names_the_fields_that_disagree() -> None:
    result = StructuredDataMetaCollector().collect(load_case("contradictory_schema").context)
    outcome = next(o for o in result.outcomes if o.check_id == "geo.sd.matches_visible_content")
    assert isinstance(outcome.observed_value, dict)
    disagreeing = set(outcome.observed_value.get("disagreeing_fields", []))
    assert {"name", "telephone"} <= disagreeing


def test_a_generic_title_without_a_description_fails() -> None:
    assert run("generic_service")["geo.meta.title_description_descriptive"] is CheckStatus.FAIL


def test_sharing_metadata_is_information_only_but_still_reported() -> None:
    assert run("generic_service")["geo.meta.opengraph_present"] is CheckStatus.FAIL
    assert run("publisher_article")["geo.meta.opengraph_present"] is CheckStatus.PASS
