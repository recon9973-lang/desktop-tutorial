"""Three buckets, counted separately — and the target-host one counted honestly.

Rate-limiting a public scanner by IP alone protects VEO and nobody else: one attacker
rotating addresses can still point every request at one victim's site and let VEO do the
hammering. So the target host is its own bucket, and the first half of this file checks
that each of the three moves only when its own key repeats.

The second half exists because the first half is not enough, and shipped code proved it.
A bucket keyed on the host an attacker *submits* is not a limit on the host VEO
*contacts*. Two laundering routes were demonstrated against this package:

1. **Redirect.** Submit ``https://s{i}.attacker.example/`` behind wildcard DNS and 302
   to the victim. Every request minted a brand-new bucket key, and the victim was never
   charged: 40 scans served, 80 requests delivered, at the shipped defaults.
2. **Ordering.** The bucket was charged for ``targets[0]`` while the fetch loop visited
   every target. ``[attacker{i}, victim, victim]`` produced the same 80 requests.

Both are asserted below by counting requests **at the transport**, which is the only
place the guarantee is observable. Counting refusals instead is what let the defect
ship: the service refused nothing, because from its own point of view nothing was wrong.
"""

from __future__ import annotations

import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from public_support import (
    PUBLIC_IP,
    RequestLog,
    ServiceClock,
    clinic_site,
    public_guard,
    site_transport,
)

from veo.contracts.enums import ErrorCode
from veo.core.settings import get_settings
from veo.providers.naver.searchad import NaverSearchAdClient
from veo.public.limits import (
    MEMORY_BACKEND_LIMITATION_KO,
    Bucket,
    InMemoryRateLimiter,
    LimitScope,
    RateLimiter,
)
from veo.public.service import (
    InMemoryPublicResultStore,
    PublicRefusal,
    PublicScanService,
)


def buckets(
    *, ip: str = "203.0.113.9", session: str = "s-1", host: str = "clinic.example", limit: int = 3
) -> list[Bucket]:
    return [
        Bucket(scope=LimitScope.CLIENT_IP, key=ip, limit=limit, window_seconds=3600),
        Bucket(scope=LimitScope.SESSION, key=session, limit=limit, window_seconds=3600),
        Bucket(scope=LimitScope.TARGET_HOST, key=host, limit=limit, window_seconds=3600),
    ]


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_the_in_memory_limiter_satisfies_the_protocol() -> None:
    limiter: RateLimiter = InMemoryRateLimiter()
    assert isinstance(limiter, RateLimiter)


def test_requests_under_the_limit_are_allowed() -> None:
    limiter = InMemoryRateLimiter(clock=FakeClock())
    for _ in range(3):
        decision = limiter.acquire(buckets(limit=3))
        assert decision.allowed is True
        assert decision.scope is None


def test_the_client_ip_bucket_fires_on_its_own() -> None:
    """Same IP, fresh session and fresh host every time: only the IP bucket can trip."""
    limiter = InMemoryRateLimiter(clock=FakeClock())
    for index in range(3):
        assert limiter.acquire(
            buckets(session=f"s-{index}", host=f"h{index}.example", limit=3)
        ).allowed

    refused = limiter.acquire(buckets(session="s-9", host="h9.example", limit=3))
    assert refused.allowed is False
    assert refused.scope is LimitScope.CLIENT_IP
    assert refused.retry_after_seconds > 0


def test_the_session_bucket_fires_on_its_own() -> None:
    limiter = InMemoryRateLimiter(clock=FakeClock())
    for index in range(3):
        assert limiter.acquire(
            buckets(ip=f"203.0.113.{index}", host=f"h{index}.example", limit=3)
        ).allowed

    refused = limiter.acquire(buckets(ip="198.51.100.7", host="h9.example", limit=3))
    assert refused.allowed is False
    assert refused.scope is LimitScope.SESSION


def test_the_target_host_bucket_fires_on_its_own() -> None:
    """The amplification guard: many attackers, one victim, still capped."""
    limiter = InMemoryRateLimiter(clock=FakeClock())
    for index in range(3):
        assert limiter.acquire(
            buckets(ip=f"203.0.113.{index}", session=f"s-{index}", limit=3)
        ).allowed

    refused = limiter.acquire(buckets(ip="198.51.100.7", session="s-9", limit=3))
    assert refused.allowed is False
    assert refused.scope is LimitScope.TARGET_HOST
    assert "clinic.example" not in refused.message_ko


def test_every_refusal_carries_retry_after_seconds_and_a_korean_reason() -> None:
    limiter = InMemoryRateLimiter(clock=FakeClock())
    for _ in range(2):
        limiter.acquire(buckets(limit=2))
    refused = limiter.acquire(buckets(limit=2))

    assert refused.retry_after_seconds > 0
    assert refused.message_ko
    assert any("가" <= ch <= "힣" for ch in refused.message_ko)

    error = refused.as_api_error()
    assert error.code is ErrorCode.RATE_LIMITED
    assert error.retryable is True
    assert error.retry_after_seconds == refused.retry_after_seconds


def test_a_refused_request_consumes_nothing() -> None:
    """All-or-nothing. A host-bucket refusal must not spend the caller's own quota."""
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock=clock)
    for index in range(3):
        limiter.acquire(buckets(ip=f"203.0.113.{index}", session=f"s-{index}", limit=3))

    refused = limiter.acquire(buckets(ip="198.51.100.7", session="s-new", limit=3))
    assert refused.allowed is False

    # The fresh caller was charged nothing, so a different host still works for them.
    allowed = limiter.acquire(
        buckets(ip="198.51.100.7", session="s-new", host="other.example", limit=3)
    )
    assert allowed.allowed is True


def test_the_window_slides_and_releases() -> None:
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock=clock)
    for _ in range(3):
        limiter.acquire(buckets(limit=3))
    assert limiter.acquire(buckets(limit=3)).allowed is False

    clock.advance(3601)
    assert limiter.acquire(buckets(limit=3)).allowed is True


def test_retry_after_shrinks_as_the_window_drains() -> None:
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock=clock)
    for _ in range(2):
        limiter.acquire(buckets(limit=2))

    first = limiter.acquire(buckets(limit=2)).retry_after_seconds
    clock.advance(600)
    second = limiter.acquire(buckets(limit=2)).retry_after_seconds
    assert second < first


def test_expired_entries_are_swept_rather_than_accumulating() -> None:
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock=clock)
    for index in range(50):
        limiter.acquire(buckets(ip=f"203.0.113.{index}", session=f"s-{index}", limit=3))
    assert limiter.tracked_key_count() > 0

    clock.advance(7200)
    limiter.acquire(buckets(ip="198.51.100.1", session="s-fresh", host="fresh.example"))
    assert limiter.tracked_key_count() <= 3


def test_a_zero_limit_refuses_everything() -> None:
    limiter = InMemoryRateLimiter(clock=FakeClock())
    refused = limiter.acquire(buckets(limit=0))
    assert refused.allowed is False
    assert refused.retry_after_seconds > 0


def test_the_per_process_limitation_is_stated_not_hidden() -> None:
    """Several API processes multiply the effective limit. Say so, in the module."""
    assert "Redis" in MEMORY_BACKEND_LIMITATION_KO
    assert InMemoryRateLimiter.__doc__ is not None
    assert "Redis" in InMemoryRateLimiter.__doc__


def test_a_bucket_rejects_a_negative_window() -> None:
    with pytest.raises(ValueError, match="window_seconds"):
        Bucket(scope=LimitScope.CLIENT_IP, key="x", limit=1, window_seconds=0)


# --------------------------------------------------------------------------- #
# The guarantee, end to end: how many requests reach one third party
# --------------------------------------------------------------------------- #


def host_limit() -> int:
    """Requests per hour to any one host, from the whole public surface."""
    return get_settings().public_target_host_limit_per_hour


def caller_limit() -> int:
    """Scans per hour per address and per session."""
    return get_settings().public_rate_limit_per_hour


def amplification_service(
    transport: object,
    *,
    limiter: InMemoryRateLimiter,
    max_urls: int | None = None,
    caller_per_hour: int | None = None,
    host_per_hour: int | None = None,
) -> PublicScanService:
    overrides: dict[str, int] = {}
    if max_urls is not None:
        overrides["public_max_urls_per_scan"] = max_urls
    if caller_per_hour is not None:
        overrides["public_rate_limit_per_hour"] = caller_per_hour
    if host_per_hour is not None:
        overrides["public_target_host_limit_per_hour"] = host_per_hour
    settings = get_settings().model_copy(update=overrides) if overrides else get_settings()
    return PublicScanService(
        guard=public_guard(PUBLIC_IP),
        transport=transport,  # type: ignore[arg-type]
        limiter=limiter,
        results=InMemoryPublicResultStore(),
        settings=settings,
        clock=ServiceClock(),
        searchad=NaverSearchAdClient(credentials=None),
        # 성능 실측도 마찬가지다: 기본값은 설정에서 키를 읽으므로, 여기서 막지
        # 않으면 시험이 개발자 .env 를 타고 진짜 구글로 나간다(0-F).
        performance=lambda context, **_: (context, None),
    )


def drive_until_refused(
    service: PublicScanService, urls_for: object, *, attempts: int | None = None
) -> tuple[int, PublicRefusal | None]:
    """Run scans from a fresh address and session each time, as a botnet would.

    Returns the number served and the refusal that stopped it, so a caller can assert on
    both the traffic delivered and the reason given.
    """
    served = 0
    for index in range(attempts if attempts is not None else host_limit() + 2):
        try:
            service.run_seo_scan(
                urls=urls_for(index),  # type: ignore[operator]
                client_ip=f"198.51.100.{index}",
                session_id=f"sid-{index:04d}",
            )
        except PublicRefusal as refusal:
            return served, refusal
        served += 1
    return served, None


def test_a_redirect_cannot_launder_traffic_onto_an_uncharged_host() -> None:
    """The reported bypass, at the shipped defaults.

    Wildcard DNS gives the attacker an unlimited supply of never-before-seen hostnames,
    each of which redirects to the victim. If the budget is charged for the submitted
    host, every request is free. The guarantee is about the victim, so the assertion is
    about the victim.
    """
    log = RequestLog()
    limiter = InMemoryRateLimiter()
    service = amplification_service(
        site_transport(
            clinic_site(),
            log=log,
            serve_unknown_hosts=True,
            redirect_suffix=(".attacker.example", "https://victim.example/"),
        ),
        limiter=limiter,
    )

    drive_until_refused(service, lambda index: [f"https://s{index}.attacker.example/"])

    assert log.count("victim.example") <= host_limit(), (
        f"VEO delivered {log.count('victim.example')} requests to the victim "
        f"with the hourly target-host limit set to {host_limit()}"
    )


def test_every_target_host_is_charged_not_only_the_first() -> None:
    """The second reported bypass: the victim sits behind a decoy in the URL list.

    Latent at the shipped page cap of 1, but the endpoint advertises a raised page count
    as the paid difference, so raising it is the expected operator action — and it must
    not silently void the defence.
    """
    log = RequestLog()
    service = amplification_service(
        site_transport(clinic_site(), log=log, serve_unknown_hosts=True),
        limiter=InMemoryRateLimiter(),
        max_urls=3,
    )

    drive_until_refused(
        service,
        lambda index: [
            f"https://attacker{index}.example/",
            "https://victim.example/",
            "https://victim.example/pricing",
        ],
    )

    assert log.count("victim.example") <= host_limit()


def test_the_robots_fetch_is_charged_to_the_host_it_actually_contacts() -> None:
    """``robots.txt`` is a second request to the target, and it counts as one."""
    log = RequestLog()
    service = amplification_service(
        site_transport(
            clinic_site(),
            log=log,
            serve_unknown_hosts=True,
            redirect_suffix=(".attacker.example", "https://victim.example/"),
        ),
        limiter=InMemoryRateLimiter(),
    )

    service.run_seo_scan(
        urls=["https://s0.attacker.example/"], client_ip="198.51.100.1", session_id="sid-1"
    )
    # One redirected page fetch plus one robots.txt fetch, both landing on the victim.
    assert log.count("victim.example") == 2


def test_a_full_host_budget_stops_the_redirect_before_it_is_followed() -> None:
    """The revealing request is spent; the followed one is preventable, so prevent it."""
    log = RequestLog()
    limiter = InMemoryRateLimiter()
    limit = host_limit()
    service = amplification_service(
        site_transport(
            clinic_site(),
            log=log,
            serve_unknown_hosts=True,
            redirect_suffix=(".attacker.example", "https://victim.example/"),
        ),
        limiter=limiter,
    )

    # Fill the victim's bucket directly, then try to launder one more request onto it.
    for _ in range(limit):
        limiter.acquire(
            [
                Bucket(
                    scope=LimitScope.TARGET_HOST,
                    key="victim.example",
                    limit=limit,
                    window_seconds=3600,
                )
            ]
        )

    with pytest.raises(PublicRefusal) as caught:
        service.run_seo_scan(
            urls=["https://s0.attacker.example/"],
            client_ip="198.51.100.2",
            session_id="sid-2",
        )

    assert caught.value.error.code is ErrorCode.RATE_LIMITED
    assert log.count("victim.example") == 0
    # The attacker's own host was still contacted — that request revealed the redirect
    # and cannot be recalled. It is the followed hop that the budget prevents.
    assert log.count("s0.attacker.example") == 1


# --------------------------------------------------------------------------- #
# Two settings, two units, no coupling
# --------------------------------------------------------------------------- #
#
# ``public_rate_limit_per_hour`` bounds the caller and is charged once per **scan**.
# ``public_target_host_limit_per_hour`` bounds the traffic aimed at one third party and
# is charged once per outbound **request** — and a scan makes two of those, the page and
# its robots.txt. The two numbers therefore measure different things and are not
# comparable. They were briefly the same setting, which meant one figure quietly meant
# two limits; the tests below exist so a future refactor cannot collapse them back
# without something failing.


def test_the_host_budget_reads_its_own_setting_not_the_caller_one() -> None:
    log = RequestLog()
    service = amplification_service(
        site_transport(clinic_site(), log=log, serve_unknown_hosts=True),
        limiter=InMemoryRateLimiter(),
        caller_per_hour=1000,
        host_per_hour=4,
    )

    served, refusal = drive_until_refused(
        service, lambda _index: ["https://victim.example/"], attempts=20
    )

    # Four requests, two per scan: two scans get through and the third is refused.
    assert log.count("victim.example") == 4
    assert served == 2
    assert refusal is not None
    assert refusal.error.code is ErrorCode.RATE_LIMITED


def test_raising_the_host_limit_does_not_buy_the_caller_more_scans() -> None:
    """A generous host budget must not loosen the per-address bucket."""
    service = amplification_service(
        site_transport(clinic_site(), serve_unknown_hosts=True),
        limiter=InMemoryRateLimiter(),
        caller_per_hour=3,
        host_per_hour=100_000,
    )

    served = 0
    refusal: PublicRefusal | None = None
    for index in range(20):
        try:
            # A different host every time, so only the caller's own buckets can bind.
            service.run_seo_scan(
                urls=[f"https://h{index}.example/"],
                client_ip="198.51.100.7",
                session_id="one-session",
            )
        except PublicRefusal as exc:
            refusal = exc
            break
        served += 1

    assert served == 3
    assert refusal is not None
    assert "같은 네트워크 주소에서" in refusal.error.message
    assert "3회" in refusal.error.message


def test_raising_the_caller_limit_does_not_buy_more_traffic_to_one_host() -> None:
    """The mirror image: a generous caller budget must not loosen the host bucket."""
    log = RequestLog()
    service = amplification_service(
        site_transport(clinic_site(), log=log, serve_unknown_hosts=True),
        limiter=InMemoryRateLimiter(),
        caller_per_hour=100_000,
        host_per_hour=6,
    )

    drive_until_refused(service, lambda _index: ["https://victim.example/"], attempts=50)
    assert log.count("victim.example") == 6


def test_the_host_refusal_message_quotes_the_host_limit_and_not_the_caller_limit() -> None:
    """A wrong number in a user-facing refusal is worse than a vague one.

    The message is rendered from the bucket that actually refused, so it has to name the
    host figure — quoting the caller figure would tell an honest site owner to wait for a
    quota that was never the one they hit.
    """
    service = amplification_service(
        site_transport(clinic_site(), serve_unknown_hosts=True),
        limiter=InMemoryRateLimiter(),
        caller_per_hour=999,
        host_per_hour=4,
    )

    _served, refusal = drive_until_refused(
        service, lambda _index: ["https://victim.example/"], attempts=20
    )

    assert refusal is not None
    message = refusal.error.message
    assert "같은 사이트에 대한" in message
    assert "60분 동안 4회까지" in message
    assert "999" not in message


def test_the_two_limits_are_documented_as_different_units() -> None:
    """The gap that caused the defect was conceptual, so it is written down."""
    from veo.public import limits as limits_module

    assert limits_module.__doc__ is not None
    assert "public_target_host_limit_per_hour" in limits_module.__doc__
    assert "public_rate_limit_per_hour" in limits_module.__doc__


# --------------------------------------------------------------------------- #
# 병렬 호출 — 검사와 청구 사이가 벌어지면 예산이 무력해진다
# --------------------------------------------------------------------------- #


def test_the_counter_holds_under_concurrent_callers() -> None:
    """`acquire` 는 검사한 뒤 청구한다. 그 사이에 다른 스레드가 끼면 둘 다 통과한다.

    락이 없던 구현은 이 조건에서 **제한 10에 14개**를 통과시켰다. 재현에는 스레드 전환을
    강제해야 한다 — GIL 아래에서 이 함수는 짧아서 평소에는 좀처럼 갈라지지 않고, 그래서
    락 없이도 200회 시도가 조용히 통과했다. 통과한 것은 안전하다는 뜻이 아니었다.

    콘솔 크롤이 페이지를 동시에 가져오므로 이것은 예외적 조건이 아니라 평범한 조건이고,
    깨지는 것은 **VEO 가 남의 서버를 두드리는 것을 막는 유일한 통제**다.
    """
    limit = 10
    threads = 32
    original = sys.getswitchinterval()
    sys.setswitchinterval(1e-9)
    try:
        worst = 0
        for _ in range(200):
            limiter = InMemoryRateLimiter()
            gate = threading.Barrier(threads)

            def attempt(
                _: int,
                limiter: InMemoryRateLimiter = limiter,
                gate: threading.Barrier = gate,
            ) -> bool:
                bucket = Bucket(
                    scope=LimitScope.TARGET_HOST,
                    key="victim.example",
                    limit=limit,
                    window_seconds=3600,
                )
                gate.wait()
                return limiter.acquire([bucket]).allowed

            with ThreadPoolExecutor(max_workers=threads) as pool:
                worst = max(worst, sum(pool.map(attempt, range(threads))))
    finally:
        sys.setswitchinterval(original)

    assert worst == limit, f"제한 {limit} 인데 {worst} 개를 통과시켰다"


def test_concurrent_callers_are_charged_exactly_once_each() -> None:
    """허용한 횟수와 기록된 횟수가 같아야 한다. 어긋나면 다음 요청의 판단도 틀린다."""
    limit = 50
    threads = 16
    limiter = InMemoryRateLimiter()

    def attempt(_: int) -> bool:
        bucket = Bucket(
            scope=LimitScope.TARGET_HOST,
            key="victim.example",
            limit=limit,
            window_seconds=3600,
        )
        return limiter.acquire([bucket]).allowed

    with ThreadPoolExecutor(max_workers=threads) as pool:
        allowed = sum(pool.map(attempt, range(limit)))

    assert allowed == limit
    # 예산을 정확히 다 썼으므로 다음 한 번은 반드시 거절돼야 한다.
    assert not attempt(0)
