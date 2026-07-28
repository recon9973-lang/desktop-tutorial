"""콘텐츠·정보구조 — seven checks, one of which is the raw-versus-rendered comparison."""

from __future__ import annotations

import dataclasses

from tests.seo.support import build_context, by_id, issues_for, status_of

from veo.scoring import CheckStatus
from veo.seo.collectors import ContentArchitectureCollector

COLLECTOR = ContentArchitectureCollector()


def run(fixture: str, **overrides: object):
    return COLLECTOR.collect(build_context(fixture, **overrides))  # type: ignore[arg-type]


def test_substantive_pages_pass_the_thin_content_check() -> None:
    assert status_of(run("healthy"), "seo.content.no_thin_signal") is CheckStatus.PASS


def test_a_page_of_two_sentences_does_not_pass() -> None:
    result = run("duplicate_metadata")
    assert status_of(result, "seo.content.no_thin_signal") in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }
    assert issues_for(result, "seo.content.no_thin_signal")


def test_distinct_bodies_pass_the_duplication_check() -> None:
    assert status_of(run("healthy"), "seo.content.no_duplicate_bodies") is CheckStatus.PASS


def test_two_near_identical_bodies_do_not_pass() -> None:
    assert status_of(run("duplicate_metadata"), "seo.content.no_duplicate_bodies") in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


def test_click_depth_is_reasonable_on_a_healthy_site() -> None:
    assert status_of(run("healthy"), "seo.content.click_depth_reasonable") is CheckStatus.PASS


def test_a_page_four_clicks_from_the_entry_does_not_pass() -> None:
    assert status_of(run("duplicate_metadata"), "seo.content.click_depth_reasonable") in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


def test_internal_link_density_passes_on_a_healthy_site() -> None:
    assert status_of(run("healthy"), "seo.content.internal_link_density") is CheckStatus.PASS


def test_a_page_with_a_single_internal_link_does_not_pass() -> None:
    assert status_of(run("duplicate_metadata"), "seo.content.internal_link_density") in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


def test_a_site_without_pagination_is_not_applicable() -> None:
    assert (
        status_of(run("brochure_na"), "seo.content.pagination_signals")
        is CheckStatus.NOT_APPLICABLE
    )


def test_a_paginated_page_canonicalising_to_page_one_does_not_pass() -> None:
    result = run("duplicate_metadata")
    assert status_of(result, "seo.content.pagination_signals") in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }
    assert issues_for(result, "seo.content.pagination_signals")


def test_a_flat_site_needs_no_breadcrumb() -> None:
    assert (
        status_of(run("brochure_na"), "seo.content.breadcrumb_present")
        is CheckStatus.NOT_APPLICABLE
    )


def test_a_deep_site_with_breadcrumbs_passes() -> None:
    assert status_of(run("healthy"), "seo.content.breadcrumb_present") is CheckStatus.PASS


def test_a_deep_site_without_breadcrumbs_does_not_pass() -> None:
    assert status_of(run("duplicate_metadata"), "seo.content.breadcrumb_present") in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


# --------------------------------------------------------------------------- #
# seo.content.js_render_parity — raw HTML against rendered DOM
# --------------------------------------------------------------------------- #


def test_render_parity_is_unknown_when_no_renderer_ran() -> None:
    """Never PASS. 'We did not look' and 'we looked and it matched' are different facts."""
    outcome = by_id(run("healthy", with_rendered=False))["seo.content.js_render_parity"]
    assert outcome.status is CheckStatus.UNKNOWN
    assert outcome.note


def test_render_parity_passes_when_the_rendered_dom_matches_the_raw_html() -> None:
    assert status_of(run("healthy"), "seo.content.js_render_parity") is CheckStatus.PASS


def test_an_empty_shell_that_hydrates_into_a_full_page_fails() -> None:
    result = run("render_gap")
    outcome = by_id(result)["seo.content.js_render_parity"]
    assert outcome.status is CheckStatus.FAIL
    issue = issues_for(result, "seo.content.js_render_parity")[0]
    assert "https://render.example.kr/" in issue.affected_urls


def test_render_parity_only_evaluates_urls_a_renderer_actually_visited() -> None:
    context = build_context("render_gap")
    only_home = {"https://render.example.kr/": context.rendered_dom["https://render.example.kr/"]}
    context = dataclasses.replace(context, rendered_dom=only_home)
    outcome = by_id(COLLECTOR.collect(context))["seo.content.js_render_parity"]
    assert outcome.evaluated_weight > 0
    assert outcome.affected_weight == outcome.evaluated_weight


def test_content_checks_are_unknown_without_documents() -> None:
    context = dataclasses.replace(
        build_context("healthy"),
        documents={},
        primary_document=None,
        rendered_dom={},
        url_importance={},
    )
    result = COLLECTOR.collect(context)
    assert all(outcome.status is CheckStatus.UNKNOWN for outcome in result.outcomes)
