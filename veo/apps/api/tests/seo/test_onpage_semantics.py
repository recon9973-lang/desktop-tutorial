"""온페이지 시맨틱 — the eight checks about what a page says about itself."""

from __future__ import annotations

import dataclasses

from tests.seo.support import build_context, by_id, issues_for, status_of

from veo.scoring import CheckStatus
from veo.seo.collectors import OnpageSemanticsCollector

COLLECTOR = OnpageSemanticsCollector()


def run(fixture: str):
    return COLLECTOR.collect(build_context(fixture))


def test_titles_are_present_and_unique_on_a_healthy_site() -> None:
    assert status_of(run("healthy"), "seo.onpage.title_present_and_unique") is CheckStatus.PASS


def test_a_repeated_title_fails() -> None:
    result = run("duplicate_metadata")
    assert status_of(result, "seo.onpage.title_present_and_unique") is CheckStatus.FAIL
    assert issues_for(result, "seo.onpage.title_present_and_unique")


def test_a_missing_title_fails() -> None:
    context = build_context("healthy")
    stripped = {
        url: dataclasses.replace(document, body=b"<html lang='ko'><body></body></html>")
        for url, document in context.documents.items()
    }
    context = dataclasses.replace(context, documents=stripped, primary_document=None)
    assert (
        by_id(COLLECTOR.collect(context))["seo.onpage.title_present_and_unique"].status
        is CheckStatus.FAIL
    )


def test_meta_description_quality_passes_on_a_healthy_site() -> None:
    assert status_of(run("healthy"), "seo.onpage.meta_description_quality") is CheckStatus.PASS


def test_a_seven_character_description_repeated_everywhere_does_not_pass() -> None:
    assert status_of(run("duplicate_metadata"), "seo.onpage.meta_description_quality") in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


def test_one_meaningful_h1_passes() -> None:
    assert status_of(run("healthy"), "seo.onpage.single_meaningful_h1") is CheckStatus.PASS


def test_two_h1_elements_on_one_page_fails() -> None:
    result = run("duplicate_metadata")
    assert status_of(result, "seo.onpage.single_meaningful_h1") is CheckStatus.FAIL
    issue = issues_for(result, "seo.onpage.single_meaningful_h1")[0]
    assert "https://dup.example.kr/list/" in issue.affected_urls


def test_a_logical_heading_hierarchy_passes() -> None:
    assert status_of(run("healthy"), "seo.onpage.heading_hierarchy") is CheckStatus.PASS


def test_skipping_from_h1_to_h3_does_not_pass() -> None:
    assert status_of(run("duplicate_metadata"), "seo.onpage.heading_hierarchy") in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


def test_html_lang_is_declared_on_a_healthy_site() -> None:
    assert status_of(run("healthy"), "seo.onpage.html_lang_declared") is CheckStatus.PASS


def test_a_missing_html_lang_fails() -> None:
    assert status_of(run("duplicate_metadata"), "seo.onpage.html_lang_declared") is CheckStatus.FAIL


def test_image_alt_coverage_passes_when_every_image_carries_alt() -> None:
    assert status_of(run("healthy"), "seo.onpage.image_alt_coverage") is CheckStatus.PASS


def test_a_page_with_no_images_at_all_is_not_applicable() -> None:
    assert (
        status_of(run("brochure_na"), "seo.onpage.image_alt_coverage")
        is CheckStatus.NOT_APPLICABLE
    )


def test_an_image_without_an_alt_attribute_does_not_pass() -> None:
    assert status_of(run("duplicate_metadata"), "seo.onpage.image_alt_coverage") in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


def test_descriptive_anchor_text_passes_on_a_healthy_site() -> None:
    assert status_of(run("healthy"), "seo.onpage.descriptive_anchor_text") is CheckStatus.PASS


def test_click_here_anchors_do_not_pass() -> None:
    result = run("duplicate_metadata")
    assert status_of(result, "seo.onpage.descriptive_anchor_text") in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }
    assert issues_for(result, "seo.onpage.descriptive_anchor_text")


def test_metadata_is_not_duplicated_on_a_healthy_site() -> None:
    assert status_of(run("healthy"), "seo.onpage.no_duplicate_metadata") is CheckStatus.PASS


def test_three_pages_sharing_one_title_and_description_fails() -> None:
    result = run("duplicate_metadata")
    outcome = by_id(result)["seo.onpage.no_duplicate_metadata"]
    assert outcome.status is CheckStatus.FAIL
    assert outcome.affected_weight > 0
    issue = issues_for(result, "seo.onpage.no_duplicate_metadata")[0]
    assert len(issue.affected_urls) >= 2


def test_on_page_checks_are_unknown_without_a_single_html_document() -> None:
    context = dataclasses.replace(
        build_context("healthy"), documents={}, primary_document=None, url_importance={}
    )
    result = COLLECTOR.collect(context)
    assert all(outcome.status is CheckStatus.UNKNOWN for outcome in result.outcomes)
    assert all(outcome.note for outcome in result.outcomes)


# --------------------------------------------------------------------------- #
# seo.sd.naver_supported_type — 명세 1.1.0 에서 이 영역으로 옮겨 온 검사
# --------------------------------------------------------------------------- #

def test_naver_requirements_are_met_when_json_ld_and_open_graph_are_both_present() -> None:
    assert status_of(run("healthy"), "seo.sd.naver_supported_type") is CheckStatus.PASS


# --------------------------------------------------------------------------- #
# Present and broken
# --------------------------------------------------------------------------- #


def test_structured_data_without_open_graph_does_not_meet_the_naver_requirement() -> None:
    assert status_of(run("broken_jsonld"), "seo.sd.naver_supported_type") in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


def test_a_site_outside_the_korean_market_skips_the_naver_check() -> None:
    context = dataclasses.replace(build_context("healthy"), locale="en-US")
    outcome = by_id(COLLECTOR.collect(context))["seo.sd.naver_supported_type"]
    assert outcome.status is CheckStatus.NOT_APPLICABLE
