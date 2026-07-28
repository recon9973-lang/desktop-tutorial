"""네이버 서치어드바이저 — what exists, and an honest gap where nothing does.

Naver publishes no public API for site registration state, crawl statistics or sitemap
processing. Those are read from a browser session by a human, and no amount of wanting
turns that into an endpoint. This suite therefore checks two opposite things:

* the one surface that **is** documented — IndexNow submission — behaves like every other
  VEO adapter: typed errors, fixed Korean messages, no key means no connection;
* every surface that is **not** documented returns ``NOT_AVAILABLE`` with a Korean reason
  and, crucially, **never opens a socket**. A client that plausibly pretends is worse than
  no client, because the fake one gets believed.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from pydantic import SecretStr

from veo.contracts.enums import DataSource, ProviderState
from veo.providers.naver.errors import UNKNOWN
from veo.providers.searchadvisor.client import (
    INDEXNOW_ENDPOINT,
    NOT_AVAILABLE_CAPABILITIES,
    SEARCH_ADVISOR_UNAVAILABLE_KO,
    CapabilityState,
    IndexNowKey,
    SearchAdvisorClient,
    indexnow_payload,
    search_advisor_capability,
)

COLLECTED_AT = datetime(2026, 7, 28, 3, 5, tzinfo=UTC)
HOST = "healthy.example.kr"
URLS = ("https://healthy.example.kr/", "https://healthy.example.kr/services/")
#: A deliberately mismatched key and location: the IndexNow spec allows any path on the
#: host, and keeping them different is what lets the tests below prove the key value
#: itself never leaks into a repr or a customer-visible message.
KEY = IndexNowKey(
    key=SecretStr("synthetic0indexnow0key0000000000"),
    key_location="https://healthy.example.kr/veo-indexnow-synthetic.txt",
)


def build_client(handler: object, **kwargs: object) -> SearchAdvisorClient:
    return SearchAdvisorClient(
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        clock=lambda: COLLECTED_AT,
        **kwargs,  # type: ignore[arg-type]
    )


# --------------------------------------------------------------------------- #
# The gap, stated rather than filled
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("capability", ["site_registration", "crawl_stats", "sitemap_status"])
def test_an_undocumented_capability_is_not_available_with_a_korean_reason(
    capability: str,
) -> None:
    gap = search_advisor_capability(capability)
    assert gap.state is CapabilityState.NOT_AVAILABLE
    assert gap.reason_ko
    assert gap.manual_alternative_ko


def test_the_unavailable_capabilities_are_enumerated_not_discovered_at_runtime() -> None:
    assert "site_registration" in NOT_AVAILABLE_CAPABILITIES
    assert SEARCH_ADVISOR_UNAVAILABLE_KO


def test_asking_for_an_unavailable_capability_opens_no_connection() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    client = build_client(handler)
    for capability in NOT_AVAILABLE_CAPABILITIES:
        assert client.capability(capability).state is CapabilityState.NOT_AVAILABLE
    assert calls == 0


def test_no_search_advisor_payload_is_produced_for_the_collector() -> None:
    """The collector must stay UNKNOWN rather than receive a fabricated registration."""
    client = build_client(lambda request: httpx.Response(200))
    assert client.search_advisor_payload() is None


# --------------------------------------------------------------------------- #
# IndexNow — the part that genuinely exists
# --------------------------------------------------------------------------- #


def test_a_submission_posts_the_documented_body_to_the_naver_endpoint() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["body"] = request.content.decode()
        seen["content_type"] = request.headers.get("content-type", "")
        return httpx.Response(200)

    outcome = build_client(handler).submit_indexnow(host=HOST, urls=URLS, key=KEY)
    assert outcome.value is not UNKNOWN
    assert seen["method"] == "POST"
    assert str(seen["url"]).startswith(INDEXNOW_ENDPOINT)
    body = str(seen["body"])
    assert HOST in body
    assert "urlList" in body
    assert "keyLocation" in body
    assert "application/json" in str(seen["content_type"])


def test_an_accepted_submission_records_what_was_sent_and_when() -> None:
    outcome = build_client(lambda request: httpx.Response(202)).submit_indexnow(
        host=HOST, urls=URLS, key=KEY
    )
    submission = outcome.value
    assert submission.accepted is True
    assert submission.status_code == 202
    assert submission.submitted_urls == URLS
    assert submission.submitted_at == COLLECTED_AT
    assert submission.source is DataSource.VEO_INTERNAL


def test_a_submission_never_happens_without_a_key() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    outcome = build_client(handler).submit_indexnow(host=HOST, urls=URLS, key=None)
    assert calls == 0
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None
    assert outcome.failure.provider_state is ProviderState.DISABLED_NO_CREDENTIAL


def test_urls_that_do_not_belong_to_the_host_are_refused_before_the_call() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    with pytest.raises(ValueError, match="host"):
        build_client(handler).submit_indexnow(
            host=HOST, urls=("https://another.example.kr/",), key=KEY
        )
    assert calls == 0


@pytest.mark.parametrize("status", [400, 403, 422, 429, 500])
def test_each_rejection_maps_to_a_typed_error_with_a_fixed_korean_message(
    status: int,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text="key not found at synthetic0indexnow0key.txt")

    outcome = build_client(handler, sleep=lambda seconds: None).submit_indexnow(
        host=HOST, urls=URLS, key=KEY
    )
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None
    assert outcome.failure.reason_ko
    assert "synthetic0indexnow0key" not in outcome.failure.reason_ko


def test_the_key_itself_never_reaches_a_failure_message_or_a_repr() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="forbidden")

    client = build_client(handler, sleep=lambda seconds: None)
    outcome = client.submit_indexnow(host=HOST, urls=URLS, key=KEY)
    assert outcome.failure is not None
    assert "synthetic0indexnow0key0000000000" not in outcome.failure.reason_ko
    assert "synthetic0indexnow0key0000000000" not in repr(client)
    assert "synthetic0indexnow0key0000000000" not in repr(KEY)


def test_a_timeout_degrades_to_unknown_rather_than_raising() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    outcome = build_client(handler, sleep=lambda seconds: None).submit_indexnow(
        host=HOST, urls=URLS, key=KEY
    )
    assert outcome.value is UNKNOWN


# --------------------------------------------------------------------------- #
# The IndexNow collector payload
# --------------------------------------------------------------------------- #


def test_the_indexnow_payload_reports_configuration_and_the_key_location() -> None:
    payload = indexnow_payload(key=KEY)
    assert payload["configured"] is True
    assert payload["key_location"] == KEY.key_location
    # An IndexNow key is published on the site by design, so the *location* is reportable
    # — but the value stays in its SecretStr and never becomes a field of its own.
    assert "key" not in payload


def test_no_key_means_no_payload_rather_than_a_configured_false() -> None:
    """VEO does not know a site is unconfigured just because VEO was not told the key."""
    assert indexnow_payload(key=None) is None
