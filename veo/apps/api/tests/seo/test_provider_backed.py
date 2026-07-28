"""검색엔진 연동, 관측·성과, 오프페이지 — ten checks that live or die by a credential.

Without one every single one of them is UNKNOWN with a Korean reason. That is the
product working correctly: coverage drops, the gap is named, and no number is invented.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from tests.seo.support import (
    ALL_PROVIDERS_ENABLED,
    build_context,
    by_id,
    healthy_provider_payloads,
    issues_for,
)

from veo.scoring import CheckStatus
from veo.seo.collectors import (
    ObservabilityOutcomesCollector,
    OffpageEntityCollector,
    SearchEngineIntegrationCollector,
)

COLLECTORS = (
    SearchEngineIntegrationCollector(),
    ObservabilityOutcomesCollector(),
    OffpageEntityCollector(),
)

PROVIDER_CHECKS = (
    "seo.integration.gsc_verified",
    "seo.integration.naver_swa_registered",
    "seo.integration.sitemap_submitted",
    "seo.integration.indexnow_configured",
    "seo.outcome.impressions_available",
    "seo.outcome.index_coverage_healthy",
    "seo.outcome.data_freshness",
    "seo.offpage.referring_domains_present",
    "seo.offpage.brand_name_consistency",
    "seo.offpage.no_spam_signal",
)


def collect(context: Any) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for collector in COLLECTORS:
        merged.update(by_id(collector.collect(context)))
    return merged


def disabled_context() -> Any:
    return build_context("healthy")


def enabled_context(**payload_overrides: object) -> Any:
    context = build_context("healthy")
    payloads = healthy_provider_payloads(tuple(context.documents))
    payloads.update(payload_overrides)
    return dataclasses.replace(
        context,
        provider_states=dict(ALL_PROVIDERS_ENABLED),
        provider_payloads=payloads,
    )


# --------------------------------------------------------------------------- #
# No credential
# --------------------------------------------------------------------------- #


def test_every_provider_backed_check_is_unknown_without_a_credential() -> None:
    outcomes = collect(disabled_context())
    for check_id in PROVIDER_CHECKS:
        outcome = outcomes[check_id]
        assert outcome.status is CheckStatus.UNKNOWN, check_id
        assert outcome.note, check_id


def test_a_missing_credential_never_produces_a_failure_or_an_issue() -> None:
    context = disabled_context()
    for collector in COLLECTORS:
        result = collector.collect(context)
        assert all(o.status is not CheckStatus.FAIL for o in result.outcomes)
        assert result.issues == ()


def test_an_unknown_outcome_carries_no_confidence() -> None:
    outcomes = collect(disabled_context())
    for check_id in PROVIDER_CHECKS:
        assert outcomes[check_id].confidence == 0.0


# --------------------------------------------------------------------------- #
# Credential present, everything healthy
# --------------------------------------------------------------------------- #


def test_every_provider_backed_check_passes_on_a_healthy_account() -> None:
    outcomes = collect(enabled_context())
    for check_id in PROVIDER_CHECKS:
        assert outcomes[check_id].status is CheckStatus.PASS, check_id


def test_a_provider_answer_is_recorded_as_evidence() -> None:
    context = enabled_context()
    for collector in COLLECTORS:
        result = collector.collect(context)
        known = {record.evidence_id for record in result.evidence}
        for outcome in result.outcomes:
            assert set(outcome.evidence_ids) <= known


# --------------------------------------------------------------------------- #
# Credential present, something wrong
# --------------------------------------------------------------------------- #


def test_an_unverified_property_fails_the_search_console_check() -> None:
    context = enabled_context(
        GOOGLE_SEARCH_CONSOLE={
            "site": {"verified": False, "permission_level": "siteUnverifiedUser"},
            "sitemaps": [],
            "performance": {"rows": 0, "impressions": 0},
            "index_coverage": {},
        }
    )
    outcomes = collect(context)
    assert outcomes["seo.integration.gsc_verified"].status is CheckStatus.FAIL
    assert outcomes["seo.integration.sitemap_submitted"].status is CheckStatus.FAIL


def test_an_unregistered_naver_site_fails() -> None:
    context = enabled_context(
        NAVER_SEARCH_ADVISOR={"site_registered": False, "ownership_verified": False}
    )
    result = SearchEngineIntegrationCollector().collect(context)
    assert by_id(result)["seo.integration.naver_swa_registered"].status is CheckStatus.FAIL
    assert issues_for(result, "seo.integration.naver_swa_registered")


def test_indexnow_not_configured_fails() -> None:
    context = enabled_context(INDEXNOW={"configured": False})
    outcomes = collect(context)
    assert outcomes["seo.integration.indexnow_configured"].status is CheckStatus.FAIL


def test_no_impression_rows_fails_the_observability_check() -> None:
    context = enabled_context(
        GOOGLE_SEARCH_CONSOLE={
            "site": {"verified": True},
            "sitemaps": [{"path": "s.xml", "is_pending": False, "errors": 0}],
            "performance": {"rows": 0, "impressions": 0, "date_range_end": "2026-07-26"},
            "index_coverage": {"indexed": 100, "previous_indexed": 100},
        }
    )
    outcomes = collect(context)
    assert outcomes["seo.outcome.impressions_available"].status is CheckStatus.FAIL


def test_a_collapse_in_index_coverage_fails() -> None:
    context = enabled_context(
        GOOGLE_SEARCH_CONSOLE={
            "site": {"verified": True},
            "sitemaps": [{"path": "s.xml", "is_pending": False, "errors": 0}],
            "performance": {"rows": 10, "impressions": 500, "date_range_end": "2026-07-26"},
            "index_coverage": {"indexed": 12, "previous_indexed": 120},
        }
    )
    result = ObservabilityOutcomesCollector().collect(context)
    assert by_id(result)["seo.outcome.index_coverage_healthy"].status is CheckStatus.FAIL
    assert issues_for(result, "seo.outcome.index_coverage_healthy")


def test_stale_performance_data_does_not_pass_the_freshness_check() -> None:
    context = enabled_context(
        GOOGLE_SEARCH_CONSOLE={
            "site": {"verified": True},
            "sitemaps": [{"path": "s.xml", "is_pending": False, "errors": 0}],
            "performance": {"rows": 10, "impressions": 500, "date_range_end": "2025-01-01"},
            "index_coverage": {"indexed": 100, "previous_indexed": 100},
        }
    )
    outcomes = collect(context)
    assert outcomes["seo.outcome.data_freshness"].status in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


def test_no_referring_domains_fails() -> None:
    context = enabled_context(
        BACKLINK_INDEX={"referring_domains": 0, "spam_flagged_domains": 0, "sampled_domains": 0}
    )
    outcomes = collect(context)
    assert outcomes["seo.offpage.referring_domains_present"].status is CheckStatus.FAIL


def test_a_spam_heavy_backlink_profile_fails() -> None:
    context = enabled_context(
        BACKLINK_INDEX={
            "referring_domains": 80,
            "spam_flagged_domains": 61,
            "sampled_domains": 80,
        }
    )
    result = OffpageEntityCollector().collect(context)
    assert by_id(result)["seo.offpage.no_spam_signal"].status is CheckStatus.FAIL


def test_inconsistent_brand_naming_does_not_pass() -> None:
    context = enabled_context(
        BRAND_MENTIONS={
            "canonical_name": "온담의원",
            "observed_names": ["온담의원", "온담 클리닉", "ONDAM CLINIC"],
            "sources_checked": 3,
        }
    )
    outcomes = collect(context)
    assert outcomes["seo.offpage.brand_name_consistency"].status in {
        CheckStatus.FAIL,
        CheckStatus.WARNING,
    }


def test_an_enabled_provider_that_sent_nothing_is_unknown_not_failed() -> None:
    context = build_context("healthy")
    context = dataclasses.replace(
        context, provider_states=dict(ALL_PROVIDERS_ENABLED), provider_payloads={}
    )
    outcomes = collect(context)
    for check_id in PROVIDER_CHECKS:
        assert outcomes[check_id].status is CheckStatus.UNKNOWN, check_id
