"""성능 배선 — 어댑터를 실제로 부르는 자리.

이 모듈이 생기기 전까지 PageSpeed 어댑터는 **호출자가 하나도 없었다.** 완성돼 있고
시험도 있었지만 아무도 부르지 않았고, 그래서 키를 넣어도 화면에는 계속 "측정 불가"
가 나왔다. `INTEGRATION_REQUEST.md` 요청 #8 에 상태 '열림' 으로 적혀 있던 것이다.

배선에는 배선만의 위험이 있다. 재는 쪽이 표본을 **다시 고르면** 채점하는 쪽과 목록이
어긋나고, 그 어긋남은 조용히 점수를 올린다 — 잰 것만 분모에 들어가기 때문이다.
이 파일의 절반이 그것을 막는다.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import SecretStr
from tests.seo.support import build_context

from veo.contracts.enums import ProviderState
from veo.providers.google.credentials import PageSpeedCredentials
from veo.providers.google.errors import UNKNOWN, CallOutcome, GoogleServerError, ProviderFailure
from veo.providers.google.pagespeed import PageSpeedClient, Strategy, normalize_runpagespeed
from veo.seo.collectors.performance_ux import PerformanceUxCollector, lab_sample
from veo.seo.measure_performance import (
    STRATEGY,
    PerformanceMeasurement,
    measure_performance,
    with_performance,
)

COLLECTED_AT = datetime(2026, 8, 1, tzinfo=UTC)
#: 합성 값이다. 이 파일은 가짜 클라이언트로만 재므로 네트워크로 나가지 않는다.
CREDENTIALS = PageSpeedCredentials(api_key=SecretStr("synthetic-pagespeed-key"))


def runpagespeed(*, url: str, score: float = 0.9, with_origin: bool = False) -> dict:
    """구글 응답의 최소 형태. 실제 응답에서 우리가 읽는 것만."""
    payload: dict = {
        "lighthouseResult": {
            "lighthouseVersion": "13.4.1",
            "categories": {"performance": {"score": score}},
            "audits": {
                audit: {
                    "score": score,
                    "displayValue": "2.0 초",
                    "numericValue": 2000.0,
                    "numericUnit": "millisecond",
                }
                for audit in (
                    "largest-contentful-paint",
                    "cumulative-layout-shift",
                    "total-blocking-time",
                    "first-contentful-paint",
                )
            },
        }
    }
    if with_origin:
        payload["originLoadingExperience"] = {
            "id": "https://healthy.example.kr",
            "overall_category": "SLOW",
            "metrics": {
                "INTERACTION_TO_NEXT_PAINT": {"category": "SLOW", "percentile": 480}
            },
        }
    return payload


class FakeClient:
    """부르는 URL 을 기록하고, 정해 둔 결과를 돌려준다."""

    def __init__(self, *, fail: set[str] | None = None, with_origin: bool = False) -> None:
        self.calls: list[tuple[str, Strategy]] = []
        self._fail = fail or set()
        self._with_origin = with_origin

    def measure(self, url: str, *, strategy: Strategy = Strategy.MOBILE):  # type: ignore[no-untyped-def]
        self.calls.append((url, strategy))
        if url in self._fail:
            return CallOutcome(
                value=UNKNOWN,
                failure=ProviderFailure.from_error(
                    GoogleServerError("status=500"), occurred_at=COLLECTED_AT
                ),
                attempts=1,
            )
        return CallOutcome(
            value=normalize_runpagespeed(
                runpagespeed(url=url, with_origin=self._with_origin),
                url=url,
                strategy=strategy,
                collected_at=COLLECTED_AT,
                raw_bytes=b"{}",
            ),
            failure=None,
            attempts=1,
        )


# --------------------------------------------------------------------------- #
# 자격증명이 없으면 소켓을 열지 않는다
# --------------------------------------------------------------------------- #


class TestNoCredentialMeansNoCall:
    def test_without_a_credential_nothing_is_measured(self) -> None:
        result = measure_performance(["https://a.example.kr/"], credentials=None)

        assert result.payloads == {}
        assert result.measured == ()
        assert result.states["GOOGLE_PAGESPEED"] is ProviderState.DISABLED_NO_CREDENTIAL

    def test_an_empty_sample_does_not_open_a_connection(self) -> None:
        """표본이 비었는데 부르면 남의 서버에 이유 없이 요청하는 것이다."""
        client = FakeClient()
        result = measure_performance([], credentials=CREDENTIALS, client=client)  # type: ignore[arg-type]

        assert client.calls == []
        assert result.payloads == {}


# --------------------------------------------------------------------------- #
# 표본은 채점하는 쪽과 같은 함수로 고른다
# --------------------------------------------------------------------------- #


class TestTheSampleMatchesWhatScoringExpects:
    def test_only_the_sampled_urls_are_called(self) -> None:
        """**이 시험이 배선의 자물쇠다.**

        재는 쪽이 표본을 다시 고르면 채점하는 쪽과 목록이 어긋난다. 어긋나면 채점기가
        "재려던 것" 을 잘못 알고, 표본 문턱이 제 일을 못 한다.
        """
        context = build_context("healthy")
        site = PerformanceUxCollector().observe(context)
        planned = lab_sample(context, site)

        client = FakeClient()
        measure_performance(planned, credentials=CREDENTIALS, client=client)  # type: ignore[arg-type]

        # 순서가 아니라 **집합**을 본다. 병렬로 던지므로 호출 순서는 보장되지 않고,
        # 순서를 단언하면 부하에 따라 깨지는 시험이 된다 — 실제로 전체 실행에서
        # 그렇게 깨졌다. 지켜야 할 성질은 "재려던 것만 재고, 하나도 빠뜨리지 않는다".
        assert sorted(url for url, _ in client.calls) == sorted(planned)

    def test_every_call_uses_the_mobile_strategy(self) -> None:
        """국내 병원 검색은 모바일 중심이고, 명세의 viewport 검사가 같은 전제다.

        전략이 섞이면 같은 URL 의 두 측정이 서로 다른 것을 잰 값이 된다.
        """
        client = FakeClient()
        measure_performance(
            ["https://a.example.kr/", "https://a.example.kr/b/"],
            credentials=CREDENTIALS,  # type: ignore[arg-type]
            client=client,
        )
        assert {strategy for _, strategy in client.calls} == {STRATEGY}


# --------------------------------------------------------------------------- #
# 한 장의 실패가 진단을 죽이지 않고, 값으로 바뀌지도 않는다
# --------------------------------------------------------------------------- #


class TestAFailedPageIsNotAValue:
    def test_the_other_pages_are_still_measured(self) -> None:
        urls = ["https://a.example.kr/", "https://a.example.kr/b/", "https://a.example.kr/c/"]
        client = FakeClient(fail={urls[1]})

        result = measure_performance(urls, credentials=CREDENTIALS, client=client)  # type: ignore[arg-type]

        assert set(result.measured) == {urls[0], urls[2]}

    def test_a_failed_page_leaves_no_entry_in_the_payload(self) -> None:
        """실패를 0점으로 적으면 없는 결함을 지어내는 것이다(0-A).

        빼 두면 표본이 얇아지고, 그 사실이 점수에 반영된다 — 그것이 정직한 경로다.
        """
        urls = ["https://a.example.kr/", "https://a.example.kr/b/"]
        client = FakeClient(fail={urls[1]})

        result = measure_performance(urls, credentials=CREDENTIALS, client=client)  # type: ignore[arg-type]

        assert urls[1] not in result.payloads["GOOGLE_PAGESPEED"]

    def test_the_plan_is_remembered_even_when_pages_fail(self) -> None:
        """"재려던 것" 을 잃으면 표본이 얇은지 아닌지 알 방법이 없다."""
        urls = ["https://a.example.kr/", "https://a.example.kr/b/"]
        result = measure_performance(
            urls,
            credentials=CREDENTIALS,  # type: ignore[arg-type]
            client=FakeClient(fail=set(urls)),
        )
        assert result.planned == tuple(urls)
        assert result.attempted == 2
        assert result.measured == ()


# --------------------------------------------------------------------------- #
# 사이트 전체(origin) 값을 한 번만 싣는다
# --------------------------------------------------------------------------- #


class TestTheOriginScopeRidesAlong:
    def test_the_site_wide_field_value_reaches_the_payload(self) -> None:
        """구글이 같은 응답에 담아 주는 값이다. 버리면 표본 문제를 스스로 만든다."""
        urls = ["https://a.example.kr/", "https://a.example.kr/b/"]
        result = measure_performance(
            urls,
            credentials=CREDENTIALS,  # type: ignore[arg-type]
            client=FakeClient(with_origin=True),
        )
        crux = result.payloads["GOOGLE_CRUX"]
        origins = [entry for entry in crux.values() if entry.get("scope") == "ORIGIN"]
        assert len(origins) == 1, "사이트 전체 값은 하나여야 한다"

    def test_the_site_wide_value_is_not_repeated_per_page(self) -> None:
        """같은 사실을 페이지 수만큼 넣으면 여러 페이지의 판정으로 오해된다."""
        urls = [f"https://a.example.kr/{n}/" for n in range(4)]
        result = measure_performance(
            urls,
            credentials=CREDENTIALS,  # type: ignore[arg-type]
            client=FakeClient(with_origin=True),
        )
        crux = result.payloads["GOOGLE_CRUX"]
        assert sum(1 for entry in crux.values() if entry.get("scope") == "ORIGIN") == 1


# --------------------------------------------------------------------------- #
# 문맥에 실제로 들어간다
# --------------------------------------------------------------------------- #


class TestTheContextActuallyChanges:
    def test_the_payload_lands_where_the_collector_reads_it(self) -> None:
        """수집기가 읽는 자리에 들어가지 않으면 배선한 것이 아니다(0-E)."""
        context = build_context("healthy")
        assert context.provider_payloads.get("GOOGLE_PAGESPEED") in (None, {})

        site = PerformanceUxCollector().observe(context)
        result = measure_performance(
            lab_sample(context, site),
            credentials=CREDENTIALS,  # type: ignore[arg-type]
            client=FakeClient(),
        )

        assert result.payloads["GOOGLE_PAGESPEED"]
        assert result.states["GOOGLE_PAGESPEED"] is ProviderState.ENABLED

    def test_without_a_credential_the_context_is_untouched(self) -> None:
        """키 없는 배포에서 이 줄은 아무 일도 하지 않아야 한다."""
        context = build_context("healthy")
        filled, measurement = with_performance(context, credentials=None)
        assert filled is context
        assert measurement is None


def test_the_real_client_type_is_what_we_wired() -> None:
    """가짜로만 시험하면 진짜 클라이언트의 서명이 바뀌어도 초록불이 유지된다(0-F)."""
    assert hasattr(PageSpeedClient, "measure")
    assert isinstance(PerformanceMeasurement.attempted, property)


# --------------------------------------------------------------------------- #
# 사용량 — 한도를 쓴 것은 사실이다
# --------------------------------------------------------------------------- #


class TestEveryCallIsRecorded:
    """PageSpeed 는 하루 25,000회다. 넘기면 그날의 모든 고객 진단에서 성능이 사라진다.

    돈이 아니라 **그날 하루**가 위험이라, 이 기록의 목적은 청구서가 아니라
    "한도까지 얼마나 남았는가" 다.
    """

    def test_a_successful_call_leaves_a_record(self) -> None:
        result = measure_performance(
            ["https://a.example.kr/"],
            credentials=CREDENTIALS,  # type: ignore[arg-type]
            client=FakeClient(),
        )
        assert len(result.calls) == 1
        assert result.calls[0].succeeded is True

    def test_a_failed_call_is_recorded_too(self) -> None:
        """실패해도 요청은 나갔고 한도를 썼다. 빼면 남은 한도를 실제보다 많게 센다."""
        url = "https://a.example.kr/"
        result = measure_performance(
            [url],
            credentials=CREDENTIALS,  # type: ignore[arg-type]
            client=FakeClient(fail={url}),
        )
        assert len(result.calls) == 1
        assert result.calls[0].succeeded is False
        assert result.calls[0].failure_code

    def test_the_record_count_matches_the_sample_size(self) -> None:
        urls = [f"https://a.example.kr/{n}/" for n in range(4)]
        result = measure_performance(
            urls,
            credentials=CREDENTIALS,  # type: ignore[arg-type]
            client=FakeClient(fail={urls[0], urls[2]}),
        )
        assert len(result.calls) == len(urls)

    def test_a_cache_hit_is_measured_not_guessed(self) -> None:
        """응답이 빨랐다고 캐시라고 적으면 그것은 추론이지 관측이 아니다(0-A).

        구글이 응답에 담아 주는 분석 시각을 본다 — 우리가 요청을 보내기 **전에**
        분석된 것이면 새로 돌린 것이 아니다.
        """
        from veo.seo.measure_performance import CallRecord

        requested = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
        cached = CallRecord(
            url="https://a.example.kr/",
            latency_ms=300,
            succeeded=True,
            analysed_at="2026-08-01T11:00:00Z",
            requested_at=requested,
        )
        fresh = CallRecord(
            url="https://a.example.kr/",
            latency_ms=24_000,
            succeeded=True,
            analysed_at="2026-08-01T12:00:30Z",
            requested_at=requested,
        )
        assert cached.was_cache_hit is True
        assert fresh.was_cache_hit is False

    def test_without_a_timestamp_the_cache_answer_is_unknown_not_false(self) -> None:
        """"새로 쟀다" 와 "모른다" 는 다른 사실이다.

        False 로 단정하면 나중에 그 기록을 아무도 믿을 수 없다.
        """
        from veo.seo.measure_performance import CallRecord

        record = CallRecord(url="https://a.example.kr/", latency_ms=100, succeeded=True)
        assert record.was_cache_hit is None
