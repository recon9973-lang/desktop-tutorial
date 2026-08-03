"""성능 측정 캐시 — 같은 값을 두 번 재지 않되, 오래된 값을 쓰지도 않는다.

진단 180초 중 약 130초가 구글 PageSpeed 를 기다리는 시간이다(2026-08-03 실측). 우리가
줄일 수 있는 것은 같은 값을 두 번 재지 않는 것뿐이라 캐시를 뒀다.

캐시는 **틀린 값을 빠르게 주는 장치가 되기 쉽다.** 그래서 여기서 지키는 것은 속도가
아니라 정직성이다: 수명이 지난 값은 없는 것과 같고, 캐시에서 온 값이 수명을 스스로
연장하지 못한다.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from veo.seo.perf_cache import PerformanceCache

MOMENT = datetime(2026, 8, 3, 9, 0, tzinfo=UTC)
MOBILE = "MOBILE"


def _cache(hours: int = 6) -> PerformanceCache:
    # 전역을 쓰지 않는다 — 시험끼리 서로의 값을 보면 실패가 순서에 따라 달라진다.
    return PerformanceCache(ttl=timedelta(hours=hours))


class TestKeepsWhatItJustMeasured:
    def test_returns_the_stored_value(self) -> None:
        cache = _cache()
        cache.put("https://a.example/", MOBILE, {"lcp": 2.1}, now=MOMENT)

        found = cache.get("https://a.example/", MOBILE, now=MOMENT)

        assert found is not None
        assert found.value == {"lcp": 2.1}

    def test_a_different_url_is_a_different_value(self) -> None:
        cache = _cache()
        cache.put("https://a.example/", MOBILE, {"lcp": 2.1}, now=MOMENT)

        assert cache.get("https://b.example/", MOBILE, now=MOMENT) is None

    def test_a_different_form_factor_is_a_different_value(self) -> None:
        """모바일과 데스크톱은 다른 측정이다. 같은 칸에 두면 조용히 섞인다."""
        cache = _cache()
        cache.put("https://a.example/", MOBILE, {"lcp": 2.1}, now=MOMENT)

        assert cache.get("https://a.example/", "DESKTOP", now=MOMENT) is None


class TestNeverServesAStaleValue:
    def test_expired_value_is_gone(self) -> None:
        cache = _cache(hours=6)
        cache.put("https://a.example/", MOBILE, {"lcp": 2.1}, now=MOMENT)

        later = MOMENT + timedelta(hours=6, minutes=1)

        assert cache.get("https://a.example/", MOBILE, now=later) is None

    def test_value_still_inside_its_life_is_served(self) -> None:
        cache = _cache(hours=6)
        cache.put("https://a.example/", MOBILE, {"lcp": 2.1}, now=MOMENT)

        assert cache.get("https://a.example/", MOBILE, now=MOMENT + timedelta(hours=5)) is not None

    def test_expiry_frees_the_slot(self) -> None:
        """수명이 지난 값은 읽는 자리에서 버린다 — 메모리에 계속 남지 않게."""
        cache = _cache(hours=1)
        cache.put("https://a.example/", MOBILE, {"lcp": 2.1}, now=MOMENT)

        cache.get("https://a.example/", MOBILE, now=MOMENT + timedelta(hours=2))

        assert cache.size() == 0

    def test_it_reports_how_old_the_value_is(self) -> None:
        """언제 잰 값인지 함께 준다 — 부르는 쪽이 그 사실을 결과에 실을 수 있어야 한다."""
        cache = _cache()
        cache.put("https://a.example/", MOBILE, {"lcp": 2.1}, now=MOMENT)

        found = cache.get("https://a.example/", MOBILE, now=MOMENT + timedelta(minutes=30))

        assert found is not None
        assert found.age_seconds(now=MOMENT + timedelta(minutes=30)) == 1800


class TestItDoesNotGrowForever:
    def test_oldest_is_dropped_past_the_limit(self) -> None:
        cache = PerformanceCache(ttl=timedelta(hours=6), max_entries=2)
        cache.put("https://a.example/", MOBILE, 1, now=MOMENT)
        cache.put("https://b.example/", MOBILE, 2, now=MOMENT + timedelta(minutes=1))
        cache.put("https://c.example/", MOBILE, 3, now=MOMENT + timedelta(minutes=2))

        assert cache.size() == 2
        # 가장 오래 전에 잰 것이 나간다.
        assert cache.get("https://a.example/", MOBILE, now=MOMENT + timedelta(minutes=2)) is None
        newest = cache.get("https://c.example/", MOBILE, now=MOMENT + timedelta(minutes=2))
        assert newest is not None


class TestMeasurementUsesTheCache:
    """`measure_performance` 가 캐시를 실제로 쓰는가 — 이것이 시간을 줄이는 자리다."""

    def test_a_cached_url_is_not_measured_again(self) -> None:
        from veo.providers.google.credentials import PageSpeedCredentials
        from veo.seo.measure_performance import STRATEGY, measure_performance

        cache = _cache()
        # 미리 재 둔 값이 있다고 해 둔다(크롤과 동시에 잰 대표 주소가 이 모습이다).
        cache.put("https://a.example/", str(STRATEGY), _fake_result(), now=datetime.now(UTC))

        class NeverCalled:
            def measure(self, url: str, **_: object) -> object:  # pragma: no cover
                raise AssertionError(f"캐시가 있는데 {url} 을 다시 쟀습니다")

        outcome = measure_performance(
            ["https://a.example/"],
            credentials=PageSpeedCredentials(api_key="k"),
            client=NeverCalled(),  # type: ignore[arg-type]
            cache=cache,
        )

        assert outcome.measured == ("https://a.example/",)

    def test_cache_hits_do_not_extend_their_own_life(self) -> None:
        """캐시에서 온 값을 다시 넣으면 값은 그대로인데 수명만 늘어난다 — 그러면
        오래된 값이 영원히 산다."""
        from veo.providers.google.credentials import PageSpeedCredentials
        from veo.seo.measure_performance import STRATEGY, measure_performance

        cache = _cache(hours=6)
        stored_at = datetime.now(UTC) - timedelta(hours=5)
        cache.put("https://a.example/", str(STRATEGY), _fake_result(), now=stored_at)

        class NeverCalled:
            def measure(self, url: str, **_: object) -> object:  # pragma: no cover
                raise AssertionError("다시 재면 안 됩니다")

        measure_performance(
            ["https://a.example/"],
            credentials=PageSpeedCredentials(api_key="k"),
            client=NeverCalled(),  # type: ignore[arg-type]
            cache=cache,
        )

        found = cache.get("https://a.example/", str(STRATEGY))
        assert found is not None
        # 잰 시각이 그대로여야 한다(오차 몇 초는 시험 실행 시간).
        assert abs((found.measured_at - stored_at).total_seconds()) < 5


def _fake_result() -> object:
    """수집기가 읽는 최소한의 모양. 실제 구글 응답을 흉내 내지 않는다 — 여기서 재는
    것은 캐시의 동작이지 응답 해석이 아니다."""
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
