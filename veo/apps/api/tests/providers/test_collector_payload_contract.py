"""The adapters' output, fed to the real SEO collectors.

The payload shape is not restated here. It is *executed*: this suite builds the same
``CollectionContext`` the SEO suite builds, fills it with payloads produced by the
adapters under test, and runs the collectors themselves. If a key is renamed on either
side, a check that should read PASS goes UNKNOWN and these tests fail — which is the only
kind of contract test worth having between two modules owned by different people.

``tests.seo.support`` is imported rather than copied for the same reason.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, date, datetime
from typing import Any

import httpx
from google_fixtures import (
    SITE_URL,
    gsc_search_analytics_response,
    gsc_site_response,
    gsc_sitemaps_response,
    gsc_url_inspection_response,
    oauth_token_response,
    runpagespeed_response,
    service_account_json,
)
from pydantic import SecretStr
from tests.seo.support import ALL_PROVIDERS_DISABLED, build_context, by_id

from veo.collect.contract import CollectionContext
from veo.contracts.enums import ProviderState
from veo.providers.google.credentials import (
    PageSpeedCredentials,
    parse_search_console_credentials,
)
from veo.providers.google.crux import field_payload
from veo.providers.google.pagespeed import PageSpeedClient, Strategy, lab_payload
from veo.providers.google.search_console import SearchConsoleClient, search_console_payload
from veo.providers.searchadvisor.client import IndexNowKey, indexnow_payload
from veo.scoring import CheckStatus
from veo.seo.collectors import (
    ObservabilityOutcomesCollector,
    PerformanceUxCollector,
    SearchEngineIntegrationCollector,
)
from veo.seo.collectors.performance_ux import PROVIDER_CRUX, PROVIDER_PAGESPEED
from veo.seo.collectors.search_engine_integration import (
    PROVIDER_INDEXNOW,
    PROVIDER_SEARCH_CONSOLE,
)

COLLECTED_AT = datetime(2026, 7, 28, 3, 5, tzinfo=UTC)
PAGESPEED_CREDENTIALS = PageSpeedCredentials(api_key=SecretStr("synthetic-pagespeed-key"))
GSC_CREDENTIALS = parse_search_console_credentials(SecretStr(service_account_json()))


def gsc_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/token"):
        return httpx.Response(200, json=oauth_token_response())
    if path.endswith("/sitemaps"):
        return httpx.Response(200, json=gsc_sitemaps_response())
    if path.endswith("/searchAnalytics/query"):
        return httpx.Response(200, json=gsc_search_analytics_response())
    if "urlInspection" in path:
        return httpx.Response(200, json=gsc_url_inspection_response())
    return httpx.Response(200, json=gsc_site_response())


def measured_payloads(urls: tuple[str, ...]) -> dict[str, Any]:
    """Run every adapter against a synthetic transport and collect what they produce."""

    def pagespeed_handler(request: httpx.Request) -> httpx.Response:
        measured_url = request.url.params["url"]
        return httpx.Response(200, json=runpagespeed_response(url=measured_url))

    pagespeed = PageSpeedClient(
        credentials=PAGESPEED_CREDENTIALS,
        transport=httpx.MockTransport(pagespeed_handler),
        clock=lambda: COLLECTED_AT,
    )
    results = [pagespeed.measure(url, strategy=Strategy.MOBILE).value for url in urls]

    console = SearchConsoleClient(
        credentials=GSC_CREDENTIALS,
        transport=httpx.MockTransport(gsc_handler),
        clock=lambda: COLLECTED_AT,
    )
    coverage = console.index_coverage(SITE_URL, urls=list(urls)).value
    # The previous figure comes from VEO's own history, never from Google.
    coverage = dataclasses.replace(coverage, previous_indexed=len(urls))

    return {
        PROVIDER_PAGESPEED: lab_payload(result.lab for result in results),
        PROVIDER_CRUX: field_payload(result.field for result in results),
        PROVIDER_SEARCH_CONSOLE: search_console_payload(
            site=console.site(SITE_URL).value,
            sitemaps=console.sitemaps(SITE_URL).value,
            performance=console.performance(
                SITE_URL, start_date=date(2026, 7, 24), end_date=date(2026, 7, 26)
            ).value,
            coverage=coverage,
        ),
        PROVIDER_INDEXNOW: indexnow_payload(
            key=IndexNowKey(
                key=SecretStr("synthetic0indexnow0key0000000000"),
                key_location="https://healthy.example.kr/veo-indexnow-synthetic.txt",
            )
        ),
    }


def context_with_measurements() -> CollectionContext:
    base = build_context("healthy")
    payloads = measured_payloads(tuple(base.documents))
    states = dict(ALL_PROVIDERS_DISABLED)
    for provider in payloads:
        states[provider] = ProviderState.ENABLED
    return dataclasses.replace(
        base,
        provider_states=states,
        provider_payloads=payloads,
        collected_at=datetime(2026, 7, 28, 3, 5, tzinfo=UTC),
    )


def outcomes() -> dict[str, Any]:
    context = context_with_measurements()
    merged: dict[str, Any] = {}
    for collector in (
        PerformanceUxCollector(),
        SearchEngineIntegrationCollector(),
        ObservabilityOutcomesCollector(),
    ):
        merged.update(by_id(collector.collect(context)))
    return merged


# --------------------------------------------------------------------------- #
# The lab payload is read as lab data
# --------------------------------------------------------------------------- #


def test_the_lab_payload_is_understood_by_the_lab_checks() -> None:
    produced = outcomes()
    for check_id in ("seo.perf.lcp_lab", "seo.perf.cls_lab", "seo.perf.tbt_lab"):
        assert produced[check_id].status is CheckStatus.PASS, check_id


def test_the_field_payload_is_understood_by_the_field_check() -> None:
    assert outcomes()["seo.perf.inp_field"].status is CheckStatus.PASS


def test_a_url_with_no_field_sample_is_not_applicable_end_to_end() -> None:
    """No CrUX sample must reach the collector as NOT_APPLICABLE, never as a failure."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=runpagespeed_response(url=request.url.params["url"], with_field_data=False)
        )

    base = build_context("healthy")
    client = PageSpeedClient(
        credentials=PAGESPEED_CREDENTIALS,
        transport=httpx.MockTransport(handler),
        clock=lambda: COLLECTED_AT,
    )
    results = [client.measure(url).value for url in base.documents]
    states = dict(ALL_PROVIDERS_DISABLED)
    states[PROVIDER_PAGESPEED] = ProviderState.ENABLED
    states[PROVIDER_CRUX] = ProviderState.ENABLED

    context = dataclasses.replace(
        base,
        provider_states=states,
        provider_payloads={
            PROVIDER_PAGESPEED: lab_payload(result.lab for result in results),
            PROVIDER_CRUX: field_payload(result.field for result in results),
        },
    )
    produced = by_id(PerformanceUxCollector().collect(context))
    assert produced["seo.perf.inp_field"].status is CheckStatus.NOT_APPLICABLE
    assert produced["seo.perf.lcp_lab"].status is CheckStatus.PASS

    # 상태만으로는 부족하다. 사장님이 이 줄을 **"CrUX 실패"** 로 읽으셨다(2026-08-09).
    # 앞의 문구가 "…측정하지 못했습니다" 로 끝나서, 우리가 뭔가 못 한 것처럼 읽혔다.
    # 실제로 일어난 일은 **구글이 아직 이 사이트의 값을 공개하지 않는 것**이고, 우리가
    # 할 수 있는 일이 하나도 없다. 고장으로 읽히면 사람은 없는 원인을 찾으러 간다.
    note = produced["seo.perf.inp_field"].note or ""
    assert "구글" in note and "공개" in note, note
    assert "결함이 아니" in note and "점수도 깎지 않" in note, note
    assert "측정하지 못했습니다" not in note, note


def test_a_slow_field_category_reaches_the_field_check_and_not_the_lab_ones() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=runpagespeed_response(url=request.url.params["url"], inp_category="SLOW"),
        )

    base = build_context("healthy")
    client = PageSpeedClient(
        credentials=PAGESPEED_CREDENTIALS,
        transport=httpx.MockTransport(handler),
        clock=lambda: COLLECTED_AT,
    )
    results = [client.measure(url).value for url in base.documents]
    states = dict(ALL_PROVIDERS_DISABLED)
    states[PROVIDER_PAGESPEED] = ProviderState.ENABLED
    states[PROVIDER_CRUX] = ProviderState.ENABLED
    context = dataclasses.replace(
        base,
        provider_states=states,
        provider_payloads={
            PROVIDER_PAGESPEED: lab_payload(result.lab for result in results),
            PROVIDER_CRUX: field_payload(result.field for result in results),
        },
    )
    produced = by_id(PerformanceUxCollector().collect(context))
    assert produced["seo.perf.inp_field"].status is CheckStatus.FAIL
    assert produced["seo.perf.lcp_lab"].status is CheckStatus.PASS


# --------------------------------------------------------------------------- #
# Search Console
# --------------------------------------------------------------------------- #


def test_the_search_console_payload_answers_ownership_and_sitemaps() -> None:
    produced = outcomes()
    assert produced["seo.integration.gsc_verified"].status is CheckStatus.PASS
    assert produced["seo.integration.sitemap_submitted"].status is CheckStatus.PASS


def test_the_search_console_payload_answers_the_outcome_checks() -> None:
    produced = outcomes()
    assert produced["seo.outcome.impressions_available"].status is CheckStatus.PASS
    assert produced["seo.outcome.index_coverage_healthy"].status is CheckStatus.PASS
    assert produced["seo.outcome.data_freshness"].status is CheckStatus.PASS


def test_the_indexnow_payload_answers_its_check() -> None:
    assert outcomes()["seo.integration.indexnow_configured"].status is CheckStatus.PASS


def test_search_advisor_stays_unknown_because_there_is_no_api_to_call() -> None:
    outcome = outcomes()["seo.integration.naver_swa_registered"]
    assert outcome.status is CheckStatus.UNKNOWN
    assert outcome.note
