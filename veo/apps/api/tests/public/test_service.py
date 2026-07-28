"""The public scan: the paid engine, a smaller scope, and nothing else in the answer.

The first test here is the one that matters most. A free scan that disagrees with the
paid scan about the same URL means the product has lied to somebody, so the assertion is
made against :func:`veo.seo.service.run_seo_scan` itself rather than against a recorded
number.
"""

from __future__ import annotations

from datetime import UTC, timedelta

import httpx
import pytest
from public_support import (
    CLINIC_HTML,
    FIXED_NOW,
    PUBLIC_IP,
    ROBOTS_TXT,
    Page,
    RequestLog,
    ServiceClock,
    clinic_site,
    make_fetcher,
    payload_strings,
    public_guard,
    site_transport,
)

from veo.contracts.enums import ErrorCode
from veo.core.settings import get_settings
from veo.geo.service import run_geo_readiness
from veo.providers.naver.searchad import NaverSearchAdClient
from veo.public.limits import InMemoryRateLimiter
from veo.public.service import (
    PUBLIC_PROVIDER_STATES,
    InMemoryPublicResultStore,
    PublicRefusal,
    PublicScanService,
    build_public_context,
)
from veo.scoring import latest_published
from veo.seo.service import run_seo_scan


def build_service(
    *,
    pages: dict[str, Page] | None = None,
    resolves_to: str = PUBLIC_IP,
    clock: ServiceClock | None = None,
    limiter: InMemoryRateLimiter | None = None,
    store: InMemoryPublicResultStore | None = None,
    log: RequestLog | None = None,
    serve_unknown_hosts: bool = False,
) -> PublicScanService:
    """The service under test.

    Note what is *not* passed: a fetcher. The service assembles its own around the
    target-host budget guard, so no test can accidentally exercise a version of the code
    with the amplification control switched off.
    """
    site = pages if pages is not None else clinic_site()
    return PublicScanService(
        guard=public_guard(resolves_to),
        transport=site_transport(site, log=log, serve_unknown_hosts=serve_unknown_hosts),
        limiter=limiter or InMemoryRateLimiter(),
        results=store or InMemoryPublicResultStore(),
        clock=clock or ServiceClock(),
        # Explicitly credential-less: a test must not depend on whatever happens to sit
        # in the deployment's .env, and a client with no credential opens no connection.
        searchad=NaverSearchAdClient(credentials=None),
    )


# --------------------------------------------------------------------------- #
# One engine
# --------------------------------------------------------------------------- #


def test_a_public_seo_scan_scores_exactly_what_the_internal_engine_scores() -> None:
    service = build_service()
    payload = service.run_seo_scan(
        urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
    )

    spec = latest_published("veo.seo.readiness")
    document = make_fetcher(clinic_site()).fetch("https://clinic.example/")
    context = build_public_context(
        target_url="https://clinic.example/",
        spec=spec,
        documents=(document,),
        robots_txt=ROBOTS_TXT,
        collected_at=FIXED_NOW,
    )
    internal = run_seo_scan(context)

    assert payload.score.score == internal.score.overall_score
    assert payload.score.coverage == internal.score.coverage
    assert payload.score.confidence == internal.score.confidence
    assert payload.score.band_id == internal.score.band_id
    assert payload.score.spec_checksum == internal.score.spec_checksum
    assert payload.score.is_rank_prediction is False


def test_a_public_geo_scan_scores_exactly_what_the_internal_engine_scores() -> None:
    service = build_service()
    payload = service.run_geo_readiness(
        urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
    )

    spec = latest_published("veo.geo.readiness")
    document = make_fetcher(clinic_site()).fetch("https://clinic.example/")
    context = build_public_context(
        target_url="https://clinic.example/",
        spec=spec,
        documents=(document,),
        robots_txt=ROBOTS_TXT,
        collected_at=FIXED_NOW,
    )
    internal = run_geo_readiness(context, spec=spec)

    assert payload.readiness.score == internal.score.overall_score
    assert payload.readiness.coverage == internal.score.coverage
    assert payload.readiness.spec_checksum == internal.score.spec_checksum
    assert payload.exposure.is_blocked == internal.is_exposure_blocked


def test_the_public_scan_runs_with_every_provider_disabled_and_says_so() -> None:
    """No credential is spent on an anonymous scan, so provider-backed checks are UNKNOWN."""
    assert PUBLIC_PROVIDER_STATES
    assert all(state.value.startswith("DISABLED") for state in PUBLIC_PROVIDER_STATES.values())

    payload = build_service().run_seo_scan(
        urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
    )
    assert payload.score.coverage < 1.0
    assert payload.unmeasured_check_count > 0


# --------------------------------------------------------------------------- #
# Scope
# --------------------------------------------------------------------------- #


def test_more_urls_than_the_configured_maximum_are_refused_in_korean() -> None:
    maximum = get_settings().public_max_urls_per_scan
    service = build_service()
    with pytest.raises(PublicRefusal) as caught:
        service.run_seo_scan(
            urls=["https://clinic.example/"] * (maximum + 1),
            client_ip="203.0.113.9",
            session_id="s-1",
        )
    assert caught.value.error.code is ErrorCode.VALIDATION_FAILED
    assert str(maximum) in caught.value.error.message
    assert any("가" <= ch <= "힣" for ch in caught.value.error.message)


def test_an_empty_url_list_is_refused() -> None:
    with pytest.raises(PublicRefusal):
        build_service().run_seo_scan(urls=[], client_ip="203.0.113.9", session_id="s-1")


# --------------------------------------------------------------------------- #
# The front door is the SSRF surface
# --------------------------------------------------------------------------- #


def test_a_private_address_target_is_refused_with_a_korean_reason() -> None:
    service = build_service(resolves_to="127.0.0.1")
    with pytest.raises(PublicRefusal) as caught:
        service.run_seo_scan(
            urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
        )

    error = caught.value.error
    assert error.code is ErrorCode.TARGET_URL_REJECTED
    assert any("가" <= ch <= "힣" for ch in error.message)
    assert "127.0.0.1" not in error.message


def test_the_cloud_metadata_address_is_refused_without_echoing_it() -> None:
    service = build_service(resolves_to="169.254.169.254")
    with pytest.raises(PublicRefusal) as caught:
        service.run_seo_scan(
            urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
        )
    assert "169.254" not in caught.value.error.message


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "gopher://clinic.example/",
        "http://user:pass@clinic.example/",
        "http://clinic.example:22/",
        "http://localhost/",
        "http://2130706433/",
    ],
)
def test_targets_the_guard_forbids_never_reach_the_network(url: str) -> None:
    service = build_service()
    with pytest.raises(PublicRefusal) as caught:
        service.run_seo_scan(urls=[url], client_ip="203.0.113.9", session_id="s-1")
    assert caught.value.error.code is ErrorCode.TARGET_URL_REJECTED


# --------------------------------------------------------------------------- #
# What a public answer may contain
# --------------------------------------------------------------------------- #


def test_a_public_payload_carries_no_evidence_excerpt_and_no_page_urls() -> None:
    payload = build_service().run_seo_scan(
        urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
    )
    body = payload.model_dump(mode="json")
    strings = payload_strings(body)

    for banned in ("excerpt", "evidence", "evidence_ids", "content_hash", "storage_key"):
        assert banned not in strings, f"public payload exposes {banned}"

    # No fragment of the fetched page comes back out.
    for line in CLINIC_HTML.splitlines():
        stripped = line.strip()
        if len(stripped) > 25:
            assert stripped not in strings

    # The only URL a public answer may repeat is the one the caller typed.
    urls = [text for text in strings if text.startswith(("http://", "https://"))]
    assert set(urls) <= {"https://clinic.example/"}


def test_a_public_payload_carries_the_methodology_version() -> None:
    payload = build_service().run_seo_scan(
        urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
    )
    assert payload.score.spec_id == "veo.seo.readiness"
    assert payload.score.spec_version
    assert len(payload.score.spec_checksum) == 64


def test_findings_name_the_check_but_never_a_page() -> None:
    payload = build_service().run_seo_scan(
        urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
    )
    assert payload.total_finding_count >= len(payload.top_findings)
    for finding in payload.top_findings:
        assert finding.check_id
        assert finding.title_ko
        assert finding.severity
        assert "http" not in finding.title_ko


# --------------------------------------------------------------------------- #
# Limits
# --------------------------------------------------------------------------- #


def test_the_rate_limit_refusal_names_a_wait() -> None:
    """One caller, a different host every time: only the caller's own buckets can bind."""
    service = build_service(serve_unknown_hosts=True)
    allowed = get_settings().public_rate_limit_per_hour
    for index in range(allowed):
        service.run_seo_scan(
            urls=[f"https://h{index}.example/"], client_ip="203.0.113.9", session_id="s-1"
        )

    with pytest.raises(PublicRefusal) as caught:
        service.run_seo_scan(
            urls=["https://h99.example/"], client_ip="203.0.113.9", session_id="s-1"
        )
    assert caught.value.error.code is ErrorCode.RATE_LIMITED
    assert caught.value.status_code == 429
    assert (caught.value.error.retry_after_seconds or 0) > 0


def test_the_target_host_budget_is_shared_across_callers() -> None:
    """Rotating source addresses must not buy more requests against one victim.

    Asserted on requests **delivered**, not on scans refused. The unit the bucket counts
    is one outbound request, and a scan makes two of them — the page and its robots.txt
    — so the number of scans that fit is an implementation detail while the traffic
    ceiling is the actual promise.
    """
    log = RequestLog()
    service = build_service(limiter=InMemoryRateLimiter(), log=log)
    # The host bucket has its own setting, in its own unit: requests, not scans.
    limit = get_settings().public_target_host_limit_per_hour

    refused = False
    for index in range(limit * 2):
        try:
            service.run_seo_scan(
                urls=["https://clinic.example/"],
                client_ip=f"203.0.113.{index}",
                session_id=f"s-{index}",
            )
        except PublicRefusal as exc:
            assert exc.error.code is ErrorCode.RATE_LIMITED
            refused = True
            break

    assert refused, "the host budget never bound"
    assert log.count("clinic.example") <= limit


# --------------------------------------------------------------------------- #
# Shared results
# --------------------------------------------------------------------------- #


def test_a_result_can_be_read_back_with_its_token() -> None:
    store = InMemoryPublicResultStore()
    service = build_service(store=store)
    payload = service.run_seo_scan(
        urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
    )

    assert payload.result_token
    read_back = service.read_result(payload.result_token)
    assert read_back.score.score == payload.score.score


def test_the_store_never_holds_the_token_itself() -> None:
    store = InMemoryPublicResultStore()
    service = build_service(store=store)
    payload = service.run_seo_scan(
        urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
    )
    assert payload.result_token not in store.stored_keys()


def test_an_expired_token_is_refused() -> None:
    clock = ServiceClock()
    store = InMemoryPublicResultStore()
    service = build_service(store=store, clock=clock)
    payload = service.run_seo_scan(
        urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
    )

    clock.advance(get_settings().public_result_ttl_seconds + 1)
    with pytest.raises(PublicRefusal) as caught:
        service.read_result(payload.result_token)
    assert caught.value.status_code == 404


def test_an_unknown_token_is_refused_exactly_like_an_expired_one() -> None:
    clock = ServiceClock()
    service = build_service(clock=clock)
    payload = service.run_seo_scan(
        urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
    )

    with pytest.raises(PublicRefusal) as unknown:
        service.read_result("Zm9vYmFyYmF6cXV1eGZvb2JhcmJhenF1dXhmb29iYXJiYXo")

    clock.advance(get_settings().public_result_ttl_seconds + 1)
    with pytest.raises(PublicRefusal) as expired:
        service.read_result(payload.result_token)

    assert unknown.value.error.message == expired.value.error.message
    assert unknown.value.status_code == expired.value.status_code


def test_a_result_expires_at_the_configured_ttl() -> None:
    payload = build_service().run_seo_scan(
        urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
    )
    expected = FIXED_NOW + timedelta(seconds=get_settings().public_result_ttl_seconds)
    assert payload.result_expires_at == expected


# --------------------------------------------------------------------------- #
# Keywords
# --------------------------------------------------------------------------- #


def test_a_keyword_lookup_with_no_credential_returns_states_and_no_numbers() -> None:
    service = build_service()
    payload = service.lookup_keywords(
        keywords=["강남 내과"], client_ip="203.0.113.9", session_id="s-1"
    )

    assert payload.searchad_state.startswith("DISABLED")
    assert payload.keywords
    entry = payload.keywords[0]
    assert entry.normalized_keyword
    assert entry.monthly_total_searches is None
    assert payload.notices_ko


def test_a_keyword_lookup_records_nothing() -> None:
    """Anonymous means anonymous: nothing is written that could be read back."""
    service = build_service()
    payload = service.lookup_keywords(
        keywords=["강남 내과"], client_ip="203.0.113.9", session_id="s-1"
    )
    body = payload.model_dump(mode="json")
    assert "query_id" not in body
    assert "organization_id" not in body
    assert "project_id" not in body


def test_too_many_keywords_are_refused() -> None:
    service = build_service()
    with pytest.raises(PublicRefusal):
        service.lookup_keywords(
            keywords=[f"키워드{index}" for index in range(50)],
            client_ip="203.0.113.9",
            session_id="s-1",
        )


def test_an_unreachable_site_is_reported_rather_than_crashing() -> None:
    service = build_service(pages={})
    payload = service.run_seo_scan(
        urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
    )
    # A 404 is a finding about the site, not an exception.
    assert payload.score.spec_id == "veo.seo.readiness"


def test_a_site_that_refuses_the_connection_is_answered_not_raised() -> None:
    """A dead host is the caller's problem to fix, told to them in Korean."""

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    service = PublicScanService(
        guard=public_guard(),
        transport=httpx.MockTransport(refuse),
        limiter=InMemoryRateLimiter(),
        results=InMemoryPublicResultStore(),
        clock=ServiceClock(),
        searchad=NaverSearchAdClient(credentials=None),
    )
    with pytest.raises(PublicRefusal) as caught:
        service.run_seo_scan(
            urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
        )
    assert caught.value.status_code == 502
    assert caught.value.error.retryable is True
    assert any("가" <= ch <= "힣" for ch in caught.value.error.message)


def test_the_clock_used_for_expiry_is_timezone_aware() -> None:
    payload = build_service().run_seo_scan(
        urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
    )
    assert payload.result_expires_at.tzinfo is not None
    assert payload.result_expires_at.astimezone(UTC) == payload.result_expires_at
