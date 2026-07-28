"""Freshness — and the trust problem of a date that moves on its own."""

from __future__ import annotations

from dataclasses import replace

from tests.geo.support import load_case

from veo.geo.collectors.freshness_signals import FreshnessSignalsCollector
from veo.scoring import CheckStatus


def run(name: str) -> dict[str, CheckStatus]:
    result = FreshnessSignalsCollector().collect(load_case(name).context)
    return {o.check_id: o.status for o in result.outcomes}


def test_published_and_modified_dates_are_found() -> None:
    assert run("publisher_article")["geo.fresh.dates_present"] is CheckStatus.PASS


def test_a_page_type_that_does_not_carry_dates_is_not_applicable() -> None:
    assert run("corporate_site")["geo.fresh.dates_present"] is CheckStatus.NOT_APPLICABLE


def test_an_article_with_no_dates_at_all_fails() -> None:
    assert run("no_schema")["geo.fresh.dates_present"] is CheckStatus.FAIL


def test_a_modified_date_that_moved_while_the_bytes_stayed_identical_fails() -> None:
    statuses = run("untruthful_dates")
    assert statuses["geo.fresh.dates_truthful"] is CheckStatus.FAIL


def test_the_untruthful_date_finding_shows_both_observations() -> None:
    result = FreshnessSignalsCollector().collect(load_case("untruthful_dates").context)
    outcome = next(o for o in result.outcomes if o.check_id == "geo.fresh.dates_truthful")
    assert isinstance(outcome.observed_value, dict)
    assert outcome.observed_value["content_changed"] is False
    assert outcome.observed_value["declared_modified_changed"] is True


def test_a_date_that_moved_with_the_content_passes() -> None:
    assert run("hospital_local")["geo.fresh.dates_truthful"] is CheckStatus.PASS


def test_without_history_truthfulness_is_unknown_not_assumed() -> None:
    case = load_case("hospital_local")
    context = replace(case.context, provider_states={}, provider_payloads={})
    result = FreshnessSignalsCollector().collect(context)
    statuses = {o.check_id: o.status for o in result.outcomes}
    assert statuses["geo.fresh.dates_truthful"] is CheckStatus.UNKNOWN


def test_a_page_without_dates_cannot_have_untruthful_ones() -> None:
    assert run("no_schema")["geo.fresh.dates_truthful"] is CheckStatus.NOT_APPLICABLE


def test_a_trustworthy_sitemap_lastmod_passes() -> None:
    assert run("hospital_local")["geo.fresh.sitemap_lastmod_reliable"] is CheckStatus.PASS


def test_a_sitemap_stamped_in_the_future_fails() -> None:
    assert run("generic_service")["geo.fresh.sitemap_lastmod_reliable"] is CheckStatus.FAIL


def test_no_sitemap_means_the_check_does_not_apply() -> None:
    assert run("no_schema")["geo.fresh.sitemap_lastmod_reliable"] is CheckStatus.NOT_APPLICABLE


def test_a_claim_anchored_to_an_old_year_fails() -> None:
    assert run("generic_service")["geo.fresh.no_stale_claims"] is CheckStatus.FAIL


def test_current_time_sensitive_information_passes() -> None:
    assert run("hospital_local")["geo.fresh.no_stale_claims"] is CheckStatus.PASS
