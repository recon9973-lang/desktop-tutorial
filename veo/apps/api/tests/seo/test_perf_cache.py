"""성능 측정은 **한 진단 안에서만** 나눠 쓴다.

가장 중요한 규칙 하나: **진단과 진단 사이에는 재사용하지 않는다.** 담당자는 사이트를
고치고 다시 재서 확인하려고 진단을 누른다. 그 순간 옛 값을 돌려주면 고쳤는데 점수가
그대로인 화면을 보게 되고, "고쳐도 안 바뀌네" 라는 잘못된 결론에 이른다. 빨라진 대가로
도구가 거짓말을 하는 것이라 어떤 시간 단축과도 바꿀 수 없다.

그 규칙을 **수명이 아니라 범위**로 지킨다: 캐시는 진단 하나가 만들고 진단이 끝나면
버려진다. 전역 기억이 없으니 옛 값이 살아남을 자리 자체가 없다.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from veo.seo.perf_cache import PerformanceCache

MOMENT = datetime(2026, 8, 3, 9, 0, tzinfo=UTC)
MOBILE = "MOBILE"


class TestThereIsNoSharedMemoryBetweenScans:
    def test_the_module_offers_no_global_cache(self) -> None:
        """전역 객체가 있으면 누군가 반드시 쓰게 되고, 그날 이 규칙이 깨진다."""
        import veo.seo.perf_cache as module

        assert not hasattr(module, "PERFORMANCE_CACHE")

    def test_a_new_scan_starts_empty(self) -> None:
        first = PerformanceCache()
        first.put("https://a.example/", MOBILE, {"lcp": 4.1}, now=MOMENT)

        # 다음 진단은 자기 것을 만든다 — 앞 진단의 값이 보이지 않는다.
        second = PerformanceCache()

        assert second.get("https://a.example/", MOBILE) is None
        assert second.size() == 0

    def test_a_fix_is_visible_on_the_next_scan(self) -> None:
        """고친 뒤 다시 재면 새 값이 나와야 한다 — 이 도구의 존재 이유다."""
        before = PerformanceCache()
        before.put("https://a.example/", MOBILE, {"lcp": 4.1}, now=MOMENT)

        after = PerformanceCache()
        after.put("https://a.example/", MOBILE, {"lcp": 1.9}, now=MOMENT + timedelta(minutes=10))

        found = after.get("https://a.example/", MOBILE)
        assert found is not None
        assert found.value == {"lcp": 1.9}


class TestWithinOneScanItSharesTheValue:
    def test_the_prewarmed_value_is_found(self) -> None:
        """크롤과 동시에 재 둔 대표 주소를, 몇십 초 뒤 표본 측정이 집어 간다."""
        cache = PerformanceCache()
        cache.put("https://a.example/", MOBILE, {"lcp": 2.1}, now=MOMENT)

        found = cache.get("https://a.example/", MOBILE)

        assert found is not None
        assert found.value == {"lcp": 2.1}

    def test_a_different_url_is_a_different_value(self) -> None:
        cache = PerformanceCache()
        cache.put("https://a.example/", MOBILE, {"lcp": 2.1}, now=MOMENT)

        assert cache.get("https://b.example/", MOBILE) is None

    def test_a_different_form_factor_is_a_different_value(self) -> None:
        """모바일과 데스크톱은 다른 측정이다. 같은 칸에 두면 조용히 섞인다."""
        cache = PerformanceCache()
        cache.put("https://a.example/", MOBILE, {"lcp": 2.1}, now=MOMENT)

        assert cache.get("https://a.example/", "DESKTOP") is None

    def test_it_reports_when_the_value_was_measured(self) -> None:
        cache = PerformanceCache()
        cache.put("https://a.example/", MOBILE, {"lcp": 2.1}, now=MOMENT)

        found = cache.get("https://a.example/", MOBILE)

        assert found is not None
        assert found.age_seconds(now=MOMENT + timedelta(minutes=1)) == 60


class TestMeasurementUsesTheScanCache:
    """`measure_performance` 가 이번 진단의 값을 실제로 집어 가는가."""

    def test_a_prewarmed_url_is_not_measured_again(self) -> None:
        from veo.providers.google.credentials import PageSpeedCredentials
        from veo.seo.measure_performance import STRATEGY, measure_performance

        cache = PerformanceCache()
        cache.put("https://a.example/", str(STRATEGY), _fake_result())

        class NeverCalled:
            def measure(self, url: str, **_: object) -> object:  # pragma: no cover
                raise AssertionError(f"이번 진단에서 이미 잰 {url} 을 다시 쟀습니다")

        outcome = measure_performance(
            ["https://a.example/"],
            credentials=PageSpeedCredentials(api_key="k"),
            client=NeverCalled(),  # type: ignore[arg-type]
            cache=cache,
        )

        assert outcome.measured == ("https://a.example/",)

    def test_without_a_cache_every_url_is_measured(self) -> None:
        """캐시를 건네지 않으면 아무것도 재사용하지 않는다 — 기본이 그쪽이다."""
        from veo.providers.google.credentials import PageSpeedCredentials
        from veo.seo.measure_performance import measure_performance

        asked: list[str] = []

        class Recording:
            def measure(self, url: str, **_: object) -> object:
                asked.append(url)

                class Ok:
                    succeeded = True
                    value = _fake_result()

                return Ok()

        measure_performance(
            ["https://a.example/"],
            credentials=PageSpeedCredentials(api_key="k"),
            client=Recording(),  # type: ignore[arg-type]
        )

        assert asked == ["https://a.example/"]


def _fake_result() -> object:
    """수집기가 읽는 최소한의 모양. 여기서 재는 것은 캐시의 동작이지 응답 해석이 아니다."""
    from veo.providers.google.crux import FieldDataState, FieldMeasurement, FieldScope
    from veo.providers.google.pagespeed import LabMeasurement, PageSpeedResult
    from veo.seo.measure_performance import STRATEGY

    return PageSpeedResult(
        lab=LabMeasurement(
            url="https://a.example/",
            strategy=STRATEGY,
            audits={},
            collected_at=MOMENT,
        ),
        field=FieldMeasurement(
            url="https://a.example/",
            scope=FieldScope.URL,
            state=FieldDataState.NOT_APPLICABLE,
            metrics={},
            collected_at=MOMENT,
        ),
    )
