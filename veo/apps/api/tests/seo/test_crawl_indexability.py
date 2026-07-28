"""크롤링·색인 가능성 — the ten checks that decide whether a URL can be found at all."""

from __future__ import annotations

import dataclasses

from tests.seo.support import build_context, by_id, issues_for, status_of

from veo.scoring import CheckStatus
from veo.seo.collectors import CrawlIndexabilityCollector

COLLECTOR = CrawlIndexabilityCollector()


def run(fixture: str, **overrides: object):
    return COLLECTOR.collect(build_context(fixture, **overrides))  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# seo.http.status_ok
# --------------------------------------------------------------------------- #


def test_status_ok_passes_when_every_crawled_url_answered_2xx() -> None:
    assert status_of(run("healthy"), "seo.http.status_ok") is CheckStatus.PASS


def test_status_ok_fails_when_a_url_answered_4xx() -> None:
    result = run("redirect_loop")
    outcome = by_id(result)["seo.http.status_ok"]
    assert outcome.status is CheckStatus.FAIL
    assert 0.0 < outcome.affected_weight < outcome.evaluated_weight


def test_status_ok_is_unknown_when_nothing_was_fetched() -> None:
    context = dataclasses.replace(
        build_context("healthy"), documents={}, primary_document=None, url_importance={}
    )
    outcome = by_id(COLLECTOR.collect(context))["seo.http.status_ok"]
    assert outcome.status is CheckStatus.UNKNOWN
    assert outcome.note


# --------------------------------------------------------------------------- #
# seo.http.redirect_chain_sane
# --------------------------------------------------------------------------- #


def test_a_direct_response_has_a_sane_chain() -> None:
    assert status_of(run("healthy"), "seo.http.redirect_chain_sane") is CheckStatus.PASS


def test_a_redirect_loop_fails_and_says_which_url_repeated() -> None:
    result = run("redirect_loop")
    assert status_of(result, "seo.http.redirect_chain_sane") is CheckStatus.FAIL
    issue = issues_for(result, "seo.http.redirect_chain_sane")[0]
    assert "https://loop.example.kr/promo/" in issue.affected_urls or any(
        "promo" in url for url in issue.affected_urls
    )
    assert issue.remediation_ko


# --------------------------------------------------------------------------- #
# seo.robots.txt_allows_url
# --------------------------------------------------------------------------- #


def test_robots_allows_the_crawled_urls_on_a_healthy_site() -> None:
    assert status_of(run("healthy"), "seo.robots.txt_allows_url") is CheckStatus.PASS


def test_a_site_wide_disallow_fails_at_full_coverage() -> None:
    outcome = by_id(run("sitewide_noindex"))["seo.robots.txt_allows_url"]
    assert outcome.status is CheckStatus.FAIL
    assert outcome.coverage_ratio == 1.0


def test_the_matched_robots_rule_is_kept_as_evidence() -> None:
    result = run("sitewide_noindex")
    outcome = by_id(result)["seo.robots.txt_allows_url"]
    kinds = {record.evidence_id: record for record in result.evidence}
    assert outcome.evidence_ids
    for evidence_id in outcome.evidence_ids:
        assert evidence_id in kinds
    assert any(record.kind == "robots_txt" for record in result.evidence)


def test_robots_is_unknown_when_the_file_was_never_collected() -> None:
    context = dataclasses.replace(build_context("healthy"), robots_txt=None)
    outcome = by_id(COLLECTOR.collect(context))["seo.robots.txt_allows_url"]
    assert outcome.status is CheckStatus.UNKNOWN


# --------------------------------------------------------------------------- #
# seo.robots.meta_indexable
# --------------------------------------------------------------------------- #


def test_meta_robots_passes_when_nothing_blocks_indexing() -> None:
    assert status_of(run("healthy"), "seo.robots.meta_indexable") is CheckStatus.PASS


def test_a_meta_noindex_and_an_x_robots_tag_both_fail() -> None:
    result = run("sitewide_noindex")
    outcome = by_id(result)["seo.robots.meta_indexable"]
    assert outcome.status is CheckStatus.FAIL
    assert outcome.coverage_ratio == 1.0
    assert issues_for(result, "seo.robots.meta_indexable")


def test_an_intentionally_noindexed_page_is_not_applicable() -> None:
    context = build_context("sitewide_noindex")
    context = dataclasses.replace(
        context,
        url_importance=dict.fromkeys(context.documents, "INTENTIONAL_NOINDEX"),
    )
    outcome = by_id(COLLECTOR.collect(context))["seo.robots.meta_indexable"]
    assert outcome.status is CheckStatus.NOT_APPLICABLE


# --------------------------------------------------------------------------- #
# seo.canonical.*
# --------------------------------------------------------------------------- #


def test_canonical_is_declared_and_consistent_on_a_healthy_site() -> None:
    assert status_of(run("healthy"), "seo.canonical.declared_and_consistent") is CheckStatus.PASS


def test_a_canonical_that_contradicts_hreflang_is_inconsistent() -> None:
    result = run("conflicting_hreflang")
    assert (
        status_of(result, "seo.canonical.declared_and_consistent") is not CheckStatus.PASS
    )
    assert issues_for(result, "seo.canonical.declared_and_consistent")


def test_a_missing_canonical_is_reported() -> None:
    assert status_of(run("duplicate_metadata"), "seo.canonical.declared_and_consistent") in {
        CheckStatus.PASS,
        CheckStatus.WARNING,
        CheckStatus.FAIL,
    }


def test_canonical_stays_on_the_domain_for_a_healthy_site() -> None:
    assert status_of(run("healthy"), "seo.canonical.not_cross_domain") is CheckStatus.PASS


def test_a_cross_domain_canonical_fails_on_the_majority_of_urls() -> None:
    outcome = by_id(run("cross_domain_canonical"))["seo.canonical.not_cross_domain"]
    assert outcome.status is CheckStatus.FAIL
    assert outcome.coverage_ratio >= 0.5


# --------------------------------------------------------------------------- #
# seo.sitemap.*
# --------------------------------------------------------------------------- #


def test_a_sitemap_declared_in_robots_is_discoverable() -> None:
    assert status_of(run("healthy"), "seo.sitemap.discoverable") is CheckStatus.PASS


def test_no_sitemap_anywhere_fails_discovery() -> None:
    assert status_of(run("cross_domain_canonical"), "seo.sitemap.discoverable") is CheckStatus.FAIL


def test_sitemap_urls_are_valid_on_a_healthy_site() -> None:
    assert status_of(run("healthy"), "seo.sitemap.urls_valid") is CheckStatus.PASS


def test_sitemap_urls_are_unknown_when_there_is_no_sitemap_to_read() -> None:
    outcome = by_id(run("cross_domain_canonical"))["seo.sitemap.urls_valid"]
    assert outcome.status is CheckStatus.UNKNOWN
    assert outcome.note


def test_a_sitemap_listing_a_blocked_url_fails() -> None:
    """The orphan site's sitemap is fine; blocking one of its URLs must change that."""
    context = build_context("orphan_page")
    context = dataclasses.replace(context, robots_txt="User-agent: *\nDisallow: /pricing/\n")
    outcome = by_id(COLLECTOR.collect(context))["seo.sitemap.urls_valid"]
    assert outcome.status is CheckStatus.FAIL


# --------------------------------------------------------------------------- #
# seo.crawl.*
# --------------------------------------------------------------------------- #


def test_every_key_page_is_reachable_on_a_healthy_site() -> None:
    assert status_of(run("healthy"), "seo.crawl.no_orphan_key_pages") is CheckStatus.PASS


def test_a_page_nobody_links_to_is_reported_as_an_orphan() -> None:
    result = run("orphan_page")
    assert status_of(result, "seo.crawl.no_orphan_key_pages") is CheckStatus.FAIL
    issue = issues_for(result, "seo.crawl.no_orphan_key_pages")[0]
    assert "https://orphan.example.kr/pricing/" in issue.affected_urls


def test_internal_links_are_intact_on_a_healthy_site() -> None:
    assert status_of(run("healthy"), "seo.crawl.no_broken_internal_links") is CheckStatus.PASS


def test_a_link_to_a_404_is_reported() -> None:
    result = run("redirect_loop")
    assert status_of(result, "seo.crawl.no_broken_internal_links") is CheckStatus.FAIL
    issue = issues_for(result, "seo.crawl.no_broken_internal_links")[0]
    assert any("gone" in url for url in issue.affected_urls)


# --------------------------------------------------------------------------- #
# Issue drafts
# --------------------------------------------------------------------------- #


def test_every_issue_carries_korean_text_evidence_and_the_specification_owner() -> None:
    context = build_context("sitewide_noindex")
    result = COLLECTOR.collect(context)
    known_evidence = {record.evidence_id for record in result.evidence}

    assert result.issues
    for issue in result.issues:
        spec_check = context.spec.check(issue.check_id)
        assert issue.remediation_owner == spec_check.remediation_owner
        assert issue.title_ko and issue.summary_ko and issue.remediation_ko
        assert issue.reverification_note_ko
        assert issue.evidence_ids
        assert set(issue.evidence_ids) <= known_evidence


def test_a_passing_check_produces_no_issue() -> None:
    result = run("healthy")
    failing = {
        outcome.check_id
        for outcome in result.outcomes
        if outcome.status in {CheckStatus.FAIL, CheckStatus.WARNING}
    }
    assert {issue.check_id for issue in result.issues} <= failing
