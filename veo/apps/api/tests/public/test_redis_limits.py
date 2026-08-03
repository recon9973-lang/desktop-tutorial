"""여러 서버가 하나의 한도를 함께 셀 때 지켜야 하는 것.

인메모리 리미터는 한 프로세스 안에서만 센다 — 워커가 둘이면 실효 한도가 두 배가 되고,
막으려던 것을 못 막는다(기획서 E6). 여기서 재는 것은 그 자리를 채운 Redis 구현의 규칙이다.

**Redis 를 띄우지 않는다.** 여기서 확인하는 것은 결정 규칙이지 Redis 자체가 아니고,
살아 있는 Redis 를 요구하는 시험은 그것이 없는 곳에서 조용히 건너뛴다 — 건너뛴 시험은
통과가 아니라 공백이다(0-F). 스크립트가 돌려주는 값의 모양만 흉내낸다.
"""

from __future__ import annotations

from typing import Any

from veo.public.limits import Bucket, LimitScope, RateLimiter
from veo.public.redis_limits import REDIS_UNAVAILABLE_KO, RedisRateLimiter


class _Client:
    """스크립트가 무엇을 돌려줄지 시험이 정하는 가짜 Redis."""

    def __init__(self, result: Any = (0, 0), *, raises: Exception | None = None) -> None:
        self.result = result
        self.raises = raises
        self.calls: list[dict[str, Any]] = []

    def register_script(self, _source: str) -> Any:
        def run(*, keys: list[str], args: list[Any]) -> Any:
            self.calls.append({"keys": keys, "args": args})
            if self.raises is not None:
                raise self.raises
            return self.result

        return run


def _bucket(scope: LimitScope = LimitScope.CLIENT_IP, limit: int = 10) -> Bucket:
    return Bucket(scope=scope, key="1.2.3.4", limit=limit, window_seconds=3600)


class TestItIsInterchangeableWithTheInMemoryOne:
    def test_it_satisfies_the_limiter_contract(self) -> None:
        """계약이 같아야 배선 한 줄로 바꿔 끼울 수 있다 — 시험은 인메모리로 빠르게 돌고
        운영은 이것으로 돈다."""
        assert isinstance(RedisRateLimiter(_Client()), RateLimiter)

    def test_no_buckets_means_nothing_to_refuse(self) -> None:
        client = _Client()

        assert RedisRateLimiter(client).acquire([]).allowed is True
        # 셀 것이 없으면 Redis 를 부르지도 않는다.
        assert client.calls == []


class TestTheDecision:
    def test_a_pass_is_allowed(self) -> None:
        limiter = RedisRateLimiter(_Client(result=(0, 0)))

        assert limiter.acquire([_bucket()]).allowed is True

    def test_a_refusal_names_the_bucket_that_refused(self) -> None:
        """어느 통이 막았는지가 사람에게 보이는 문장을 정한다 — 방문자 자신의 한도와
        대상 사이트의 한도는 다른 이야기다."""
        caller = _bucket(LimitScope.CLIENT_IP)
        target = _bucket(LimitScope.TARGET_HOST)
        # 두 번째 통이 막았다고 스크립트가 답한 경우.
        limiter = RedisRateLimiter(_Client(result=(2, 42)))

        decision = limiter.acquire([caller, target])

        assert decision.allowed is False
        assert decision.scope is LimitScope.TARGET_HOST
        assert decision.retry_after_seconds == 42

    def test_a_zero_wait_is_lifted_to_one_second(self) -> None:
        """0초 뒤에 다시 오라는 안내는 즉시 재시도를 부르고, 그러면 또 거절이다."""
        limiter = RedisRateLimiter(_Client(result=(1, 0)))

        assert limiter.acquire([_bucket()]).retry_after_seconds == 1


class TestWhenTheBackendIsDownItRefuses:
    """통과시키면 장애 시간이 그대로 남용 창구가 된다. 그 피해는 우리가 아니라 우리가
    크롤하는 남의 서버가 입는다 — 무료 도구가 잠시 멈추는 것과 비교할 수 없다."""

    def test_an_unreachable_backend_refuses(self) -> None:
        limiter = RedisRateLimiter(_Client(raises=ConnectionError("redis down")))

        decision = limiter.acquire([_bucket()])

        assert decision.allowed is False

    def test_the_message_does_not_blame_the_visitor(self) -> None:
        """한도를 넘긴 것이 아니라 우리 쪽이 셀 수 없는 상태다 — 우리 한계를 방문자
        탓으로 적지 않는다(0-J)."""
        limiter = RedisRateLimiter(_Client(raises=ConnectionError("redis down")))

        decision = limiter.acquire([_bucket()])

        assert decision.message_ko == REDIS_UNAVAILABLE_KO
        assert "많이" not in decision.message_ko

    def test_it_still_says_when_to_come_back(self) -> None:
        limiter = RedisRateLimiter(_Client(raises=TimeoutError()))

        assert limiter.acquire([_bucket()]).retry_after_seconds > 0


class TestWhatItSendsToRedis:
    def test_every_bucket_becomes_one_key(self) -> None:
        """통마다 자기 키가 있어야 각자의 한도를 센다. 한 키에 몰면 둘이 서로의 몫을
        태운다."""
        client = _Client()
        limiter = RedisRateLimiter(client)

        limiter.acquire([_bucket(LimitScope.CLIENT_IP), _bucket(LimitScope.TARGET_HOST)])

        keys = client.calls[0]["keys"]
        assert len(keys) == 2
        assert len(set(keys)) == 2

    def test_the_key_carries_the_scope(self) -> None:
        """같은 값이 다른 뜻으로 두 통에 들어갈 수 있다(주소가 방문자이자 대상일 때)."""
        client = _Client()

        RedisRateLimiter(client).acquire([_bucket(LimitScope.TARGET_HOST)])

        assert "TARGET_HOST" in client.calls[0]["keys"][0]

    def test_limits_and_windows_travel_with_each_bucket(self) -> None:
        client = _Client()
        limiter = RedisRateLimiter(client)

        limiter.acquire([Bucket(scope=LimitScope.SESSION, key="s", limit=7, window_seconds=60)])

        args = client.calls[0]["args"]
        # now, member, limit, window_ms
        assert args[2] == 7
        assert args[3] == 60_000


class TestWhichLimiterTheDeploymentGets:
    """배선이 실제로 바뀌는가 — 여기가 이 작업의 목적이다."""

    def test_no_redis_url_means_in_process_counting(self, monkeypatch: Any) -> None:
        """로컬과 시험은 Redis 없이 돌아야 한다. 빈 값은 '설정 안 됨' 이다."""
        from veo.public import router
        from veo.public.limits import InMemoryRateLimiter

        monkeypatch.setattr(router, "_SHARED_LIMITER", None)
        monkeypatch.setattr(
            router, "get_settings", lambda: type("S", (), {"redis_url": ""})()
        )

        assert isinstance(router.get_rate_limiter(), InMemoryRateLimiter)

    def test_a_redis_url_means_shared_counting(self, monkeypatch: Any) -> None:
        from veo.public import router

        monkeypatch.setattr(router, "_SHARED_LIMITER", None)
        monkeypatch.setattr(
            router,
            "get_settings",
            lambda: type("S", (), {"redis_url": "redis://example:6379/0"})(),
        )
        # 연결은 만들지 않는다 — 여기서 재는 것은 **어느 구현이 선택되는가** 이다.
        monkeypatch.setattr("redis.Redis.from_url", lambda _url: _Client())

        assert isinstance(router.get_rate_limiter(), RedisRateLimiter)

    def test_the_shared_limiter_is_built_once(self, monkeypatch: Any) -> None:
        """요청마다 연결하면 연결 수가 요청 수만큼 늘어난다."""
        from veo.public import router

        built = []

        def _from_url(_url: str) -> Any:
            built.append(_url)
            return _Client()

        monkeypatch.setattr(router, "_SHARED_LIMITER", None)
        monkeypatch.setattr(
            router,
            "get_settings",
            lambda: type("S", (), {"redis_url": "redis://example:6379/0"})(),
        )
        monkeypatch.setattr("redis.Redis.from_url", _from_url)

        router.get_rate_limiter()
        router.get_rate_limiter()

        assert len(built) == 1
