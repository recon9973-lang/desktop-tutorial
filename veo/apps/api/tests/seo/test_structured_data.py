"""구조화 데이터 — five checks, all of which are 해당 없음 on a page that declares none.

The rule this file exists to protect: **N/A is not zero.** A brochure site with no
JSON-LD has nothing to get wrong, so it loses nothing.
"""

from __future__ import annotations

import dataclasses

from tests.seo.support import build_context, by_id, issues_for, status_of

from veo.scoring import CheckStatus
from veo.seo.collectors import StructuredDataCollector

COLLECTOR = StructuredDataCollector()

SD_CHECKS = (
    "seo.sd.jsonld_parses",
    "seo.sd.required_properties_present",
    "seo.sd.matches_visible_content",
    "seo.sd.google_supported_type",
    "seo.sd.naver_supported_type",
)


def run(fixture: str, **overrides: object):
    return COLLECTOR.collect(build_context(fixture, **overrides))  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# N/A is not zero
# --------------------------------------------------------------------------- #


def test_a_site_with_no_structured_data_is_not_applicable_on_all_five_checks() -> None:
    result = run("brochure_na")
    for check_id in SD_CHECKS:
        outcome = by_id(result)[check_id]
        assert outcome.status is CheckStatus.NOT_APPLICABLE, check_id
        assert outcome.note


def test_a_site_with_no_structured_data_raises_no_issue() -> None:
    assert run("brochure_na").issues == ()


# --------------------------------------------------------------------------- #
# Present and correct
# --------------------------------------------------------------------------- #


def test_valid_json_ld_parses() -> None:
    assert status_of(run("healthy"), "seo.sd.jsonld_parses") is CheckStatus.PASS


def test_required_properties_are_present_on_a_healthy_site() -> None:
    assert status_of(run("healthy"), "seo.sd.required_properties_present") is CheckStatus.PASS


def test_structured_data_matching_the_visible_page_passes() -> None:
    assert status_of(run("healthy"), "seo.sd.matches_visible_content") is CheckStatus.PASS


def test_a_google_supported_type_passes() -> None:
    assert status_of(run("healthy"), "seo.sd.google_supported_type") is CheckStatus.PASS


def test_naver_requirements_are_met_when_json_ld_and_open_graph_are_both_present() -> None:
    assert status_of(run("healthy"), "seo.sd.naver_supported_type") is CheckStatus.PASS


# --------------------------------------------------------------------------- #
# Present and broken
# --------------------------------------------------------------------------- #


def test_a_trailing_comma_in_json_ld_fails_the_parse_check() -> None:
    result = run("broken_jsonld")
    outcome = by_id(result)["seo.sd.jsonld_parses"]
    assert outcome.status is CheckStatus.FAIL
    issue = issues_for(result, "seo.sd.jsonld_parses")[0]
    assert "https://jsonld.example.kr/" in issue.affected_urls
    assert issue.evidence_ids


def test_a_product_without_a_name_fails_the_required_property_check() -> None:
    result = run("broken_jsonld")
    assert status_of(result, "seo.sd.required_properties_present") is CheckStatus.FAIL
    issue = issues_for(result, "seo.sd.required_properties_present")[0]
    assert "https://jsonld.example.kr/menu/" in issue.affected_urls


def test_a_name_that_appears_nowhere_on_the_page_does_not_pass() -> None:
    result = run("broken_jsonld")
    assert status_of(result, "seo.sd.matches_visible_content") in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


def test_a_type_google_does_not_support_does_not_pass() -> None:
    result = run("broken_jsonld")
    assert status_of(result, "seo.sd.google_supported_type") in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


def test_structured_data_without_open_graph_does_not_meet_the_naver_requirement() -> None:
    assert status_of(run("broken_jsonld"), "seo.sd.naver_supported_type") in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


def test_a_site_outside_the_korean_market_skips_the_naver_check() -> None:
    context = dataclasses.replace(build_context("healthy"), locale="en-US")
    outcome = by_id(COLLECTOR.collect(context))["seo.sd.naver_supported_type"]
    assert outcome.status is CheckStatus.NOT_APPLICABLE


def test_an_unrecognised_type_is_unknown_rather_than_failed_for_required_properties() -> None:
    """VEO does not know every schema.org type, and pretending otherwise invents a finding."""
    context = build_context("healthy")
    replaced = {
        url: dataclasses.replace(
            document,
            body=document.body.replace(b'"MedicalClinic"', b'"AmusementPark"').replace(
                b'"BreadcrumbList"', b'"AmusementPark"'
            ),
        )
        for url, document in context.documents.items()
    }
    context = dataclasses.replace(context, documents=replaced, primary_document=None)
    outcome = by_id(COLLECTOR.collect(context))["seo.sd.required_properties_present"]
    assert outcome.status is CheckStatus.UNKNOWN


def test_structured_data_checks_are_unknown_without_documents() -> None:
    context = dataclasses.replace(
        build_context("healthy"), documents={}, primary_document=None, url_importance={}
    )
    result = COLLECTOR.collect(context)
    assert all(outcome.status is CheckStatus.UNKNOWN for outcome in result.outcomes)
