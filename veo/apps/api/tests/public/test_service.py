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
        # 성능 실측도 마찬가지다: 기본값은 설정에서 키를 읽으므로, 여기서 막지
        # 않으면 시험이 개발자 .env 를 타고 진짜 구글로 나간다(0-F).
        performance=lambda context: (context, None),
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

    # 답에 등장하는 모든 URL 은 호출자가 입력한 그 호스트여야 한다. 수집기 문장이
    # 실리면서(2026-08-02) URL 이 문장 안에도 나타난다 — 문자열 전체가 아니라
    # 문장 속 URL 을 뽑아 host 를 본다. 지키는 성질은 같다: 남의 주소는 없다.
    import re
    from urllib.parse import urlsplit

    found = [url for text in strings for url in re.findall(r"https?://[^\s\u201d\u201c\"']+", text)]
    page_hosts = {
        urlsplit(url).hostname
        for url in re.findall(r"https?://[^\s\"'<>]+", CLINIC_HTML)
    }
    assert found, "URL 이 하나도 없다면 target_url 마저 사라진 것이다"
    # 호출자의 호스트, 그리고 호출자 페이지가 스스로 참조하는 리소스 호스트까지만.
    # 그 밖의 호스트가 나오면 남의 것이 샌 것이다.
    # 수집기의 고정 조치 문구가 언급하는 잘 알려진 인프라 호스트. 여기 없는
    # 호스트가 나오면 시험이 이름을 대며 실패한다 — 추가는 의식적 결정이어야 한다.
    well_known = {"schema.org", "www.w3.org", "fonts.gstatic.com", "fonts.googleapis.com"}
    assert {urlsplit(url).hostname for url in found} <= (
        {"clinic.example"} | page_hosts | well_known
    )


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
        # 성능 실측도 마찬가지다: 기본값은 설정에서 키를 읽으므로, 여기서 막지
        # 않으면 시험이 개발자 .env 를 타고 진짜 구글로 나간다(0-F).
        performance=lambda context: (context, None),
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


# --------------------------------------------------------------------------- #
# 확정 화면(2026-08-02)이 요구하는 필드 — 전체 검사·단계·카운트·미리보기·조치 코드
# --------------------------------------------------------------------------- #


class TestTheFullChecklistPayload:
    """무료 결과가 상위 몇 건이 아니라 **전체**를 내보낸다 — 화면 확정의 결정.

    페이지 간 비교 항목이 여기서 측정 불가로 남는 것 자체가 전체 진단(콘솔)의
    이유가 되므로, 숨겨서 얻는 전환 대신 다 보여주는 쪽을 택했다.
    """

    def _payload(self):  # type: ignore[no-untyped-def]
        return build_service().run_seo_scan(
            urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
        )

    def test_every_evaluated_check_appears_exactly_once(self) -> None:
        payload = self._payload()

        spec = latest_published("veo.seo.readiness")
        declared = {check.id for category in spec.categories for check in category.checks}
        listed = [row.check_id for row in payload.checks]

        assert set(listed) <= declared
        assert len(listed) == len(set(listed)), "같은 검사가 두 번 실렸다"
        assert len(listed) == sum(
            (
                payload.counts.failed,
                payload.counts.warned,
                payload.counts.passed,
                payload.counts.unknown,
                payload.counts.not_applicable,
            )
        ), "필터 칩의 합과 목록 길이가 다르면 화면이 세다가 틀린다"

    def test_stages_are_the_scoring_categories_in_spec_order(self) -> None:
        payload = self._payload()

        spec = latest_published("veo.seo.readiness")
        expected = [c.id for c in spec.categories if c.contributes_to_score]
        assert [stage.category_id for stage in payload.stages] == expected
        assert any(stage.is_gate for stage in payload.stages), "관문 표시가 사라졌다"

    def test_a_failing_check_with_a_canonical_fix_carries_code(self) -> None:
        """더보기가 보여줄 코드 — 정답이 하나로 정해지는 검사에만 실린다."""
        payload = self._payload()
        rows = {row.check_id: row for row in payload.checks}

        fixable = [
            row
            for row in payload.checks
            if row.status in ("FAIL", "WARNING") and row.code_example is not None
        ]
        assert fixable, "실패 항목 중 코드 예시가 하나도 없다 — 배선이 끊겼다"
        for row in rows.values():
            if row.status in ("PASS", "NOT_APPLICABLE", "UNKNOWN"):
                assert row.code_example is None, (
                    f"{row.check_id}: 통과·미측정 항목에 조치 코드가 실렸다"
                )

    def test_a_failing_check_carries_the_collectors_diagnosis_and_fix(self) -> None:
        """진단 문장과 조치 문장은 수집기의 것 그대로 — 화면이 다시 쓰지 않는다.

        2026-08-02 제품 결정: 공개 진단은 호출자가 직접 입력한 한 페이지만 재므로,
        그 페이지에 대한 수집기 문장은 호출자 자신의 것이다. 본문 발췌·증거 키는
        여전히 나가지 않는다(위의 no_evidence 시험이 지킨다).
        """
        payload = self._payload()
        broken = [row for row in payload.checks if row.status in ("FAIL", "WARNING")]
        assert broken, "픽스처에 실패·주의가 하나도 없다"
        carried = [row for row in broken if row.detail_ko or row.fix_ko]
        assert carried, "수집기 진단·조치 문장이 한 줄도 실리지 않았다 — 배선이 끊겼다"
        for row in payload.checks:
            if row.status not in ("FAIL", "WARNING"):
                assert row.detail_ko is None and row.fix_ko is None, (
                    f"{row.check_id}: 통과·미측정 항목에 진단 문장이 실렸다"
                )

    def test_previews_reflect_what_the_page_actually_declares(self) -> None:
        payload = self._payload()

        assert payload.previews is not None
        # 픽스처 홈페이지에는 title 이 있다 — 있는 것은 값으로, 없는 것은 None 으로.
        assert payload.previews.serp_title
        assert isinstance(payload.previews.has_og_image, bool)

    def test_reach_travels_with_the_score(self) -> None:
        payload = self._payload()

        assert 0.0 <= payload.reach <= 1.0


# --------------------------------------------------------------------------- #
# PageSpeed wiring
# --------------------------------------------------------------------------- #


class _FakeMeasurement:
    """with_performance 가 돌려주는 것 중 서비스가 읽는 두 가지만 흉내낸다."""

    def __init__(self, calls: list[str]) -> None:
        self.calls = calls


class TestPublicPerformanceWiring:
    """공개 SEO 스캔도 성능을 잰다 — 콘솔만 배선하고 공개를 빼먹었던 결함의 회귀 시험.

    2026-08-02 라이브에서 확인된 결함: 서버에 키가 있는데도 무료 진단의 성능 4항목이
    상시 "측정 불가" 였다. 원인은 코드가 아니라 배선 — ``with_performance`` 의
    호출자가 콘솔 경로에만 있었다.
    """

    def test_the_scan_scores_the_context_the_performance_step_returned(self) -> None:
        seen: list[object] = []

        def fake_performance(context: object) -> tuple[object, None]:
            seen.append(context)
            return context, None

        site = clinic_site()
        service = PublicScanService(
            guard=public_guard(PUBLIC_IP),
            transport=site_transport(site),
            limiter=InMemoryRateLimiter(),
            results=InMemoryPublicResultStore(),
            clock=ServiceClock(),
            searchad=NaverSearchAdClient(credentials=None),
            performance=fake_performance,
        )
        service.run_seo_scan(
            urls=["https://clinic.example/"], client_ip="203.0.113.9", session_id="s-1"
        )

        assert len(seen) == 1, "성능 측정 단계가 스캔당 정확히 한 번 불려야 한다"

    def test_spent_calls_reach_the_usage_callback(self) -> None:
        recorded: list[object] = []
        measurement = _FakeMeasurement(calls=["pagespeed-call-1"])

        site = clinic_site()
        service = PublicScanService(
            guard=public_guard(PUBLIC_IP),
            transport=site_transport(site),
            limiter=InMemoryRateLimiter(),
            results=InMemoryPublicResultStore(),
            clock=ServiceClock(),
            searchad=NaverSearchAdClient(credentials=None),
            performance=lambda context: (context, measurement),
        )
        service.run_seo_scan(
            urls=["https://clinic.example/"],
            client_ip="203.0.113.9",
            session_id="s-1",
            record_usage=recorded.extend,
        )

        assert recorded == ["pagespeed-call-1"], "쓴 호출이 기록 콜백에 닿지 않았다"

    def test_nothing_measured_records_nothing(self) -> None:
        """키가 없어 측정하지 못했으면 기록도 없어야 한다 — 0건 이벤트는 소음이다."""
        recorded: list[object] = []
        service = build_service()
        service.run_seo_scan(
            urls=["https://clinic.example/"],
            client_ip="203.0.113.9",
            session_id="s-1",
            record_usage=recorded.extend,
        )

        assert recorded == []
