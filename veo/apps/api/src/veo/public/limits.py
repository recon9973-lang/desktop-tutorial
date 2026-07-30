"""Rate limiting for the only surface VEO exposes to strangers.

Three buckets, counted independently, and a request must fit in all three:

``CLIENT_IP``
    Stops one machine from draining the free tier. Charged once per **scan**, from
    ``public_rate_limit_per_hour``.

``SESSION``
    Stops one browser from doing the same behind a shared address — an office, a campus
    or a mobile carrier NAT can put hundreds of honest users on one IP, so the session
    bucket is what lets the IP bucket stay generous. Also once per **scan**, from
    ``public_rate_limit_per_hour``.

``TARGET_HOST``
    Stops VEO being the weapon. Limiting only by caller means an attacker with a botnet
    can point every one of those requests at a single third-party site and have VEO
    fetch it, from VEO's addresses, at VEO's expense.

Two settings, because there are two units
-----------------------------------------
The caller buckets read ``public_rate_limit_per_hour`` and are charged once per **scan**.
The host bucket reads ``public_target_host_limit_per_hour`` and is charged once per
outbound **request** — and one scan makes two of those, the page and its ``robots.txt``.

The two figures are therefore **not comparable and must not be tuned as if they were**:
"10" as a caller limit and "10" as a host limit describe different quantities, and a
host limit of 60 permits roughly 30 scans of one site per hour, not 60. These were
briefly a single setting, which meant one number quietly meant two limits — raising it
to give an honest site owner more scans also widened the amplification cap, and
tightening the cap silently throttled the owner.

What the host bucket does and does not guarantee
------------------------------------------------
It is charged **one unit per outbound HTTP request, keyed on the host VEO is about to
contact, at the moment the guard approves that hop** — see :class:`HostBudgetGuard`.
Stating it that precisely is not pedantry; an earlier version of this module keyed the
bucket on the host the *caller submitted*, before the fetch, and claimed to cap traffic
at a victim. It did not, and two routes were demonstrated against it:

* a redirect from a throwaway hostname, which minted a fresh unused bucket key on every
  request while every fetch landed on the victim; and
* a multi-URL scan, where the bucket was charged for the first URL while the fetch loop
  visited all of them.

Both delivered eighty requests to a host whose configured hourly limit was ten. Keying
on what VEO *contacts* rather than on what it was *asked to contact* is the whole fix.

What it still does not cover, said plainly:

* **The request that reveals a redirect is already spent.** VEO must send a request to
  the attacker's own host to learn where it points; only the *followed* hop can be
  refused. One redirect chain therefore costs the victim nothing, but costs VEO one
  request to a host of the attacker's choosing — which the ``CLIENT_IP`` and ``SESSION``
  buckets, not this one, are what bound.
* **Per process.** See :data:`MEMORY_BACKEND_LIMITATION_KO`. With *n* API workers the
  real cap against any one victim is *n* times the configured figure.
* **Host, not owner.** A victim on many hostnames gets a bucket per hostname. Limiting
  by registrable domain would need a public-suffix list, which is a dependency this
  package does not have.

A refusal never says which key it counted. "clinic.example has been scanned ten times
this hour" is a fact about somebody else, and a public endpoint that reports it is an
oracle. The scope is returned — the caller may know *which rule* they hit — and the key
is not.

Every refusal carries ``retry_after_seconds``, computed from the oldest hit still inside
the window, so the answer is a real wait rather than a guess.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, final, runtime_checkable

from veo.common.security.url_guard import UrlDecision, UrlGuard
from veo.contracts.enums import ErrorCode
from veo.contracts.envelope import ApiError

__all__ = [
    "MEMORY_BACKEND_LIMITATION_KO",
    "TARGET_HOST_WINDOW_SECONDS",
    "Bucket",
    "HostBudgetExceeded",
    "HostBudgetGuard",
    "InMemoryRateLimiter",
    "LimitScope",
    "RateLimitDecision",
    "RateLimiter",
]

#: The target-host window. One hour, matching ``public_rate_limit_per_hour``.
TARGET_HOST_WINDOW_SECONDS = 3600

#: Said out loud rather than buried: this implementation counts inside one process.
#: Two API workers mean twice the effective limit, four mean four times. The production
#: backing is Redis, shared by every process, and it is **not** built in this module.
#: Until it exists, deployments must either run a single public-facing process or treat
#: the configured limit as a per-process figure and divide accordingly.
MEMORY_BACKEND_LIMITATION_KO = (
    "이 제한기는 프로세스 안에서만 카운트합니다. API 프로세스를 여러 개 띄우면 실제 허용량이 "
    "프로세스 수만큼 늘어납니다. 운영 환경의 정답은 모든 프로세스가 공유하는 Redis 백엔드이며, "
    "그것은 이 모듈에 구현되어 있지 않습니다."
)


class LimitScope(StrEnum):
    """Which counter refused. Safe to return; the key behind it is not."""

    CLIENT_IP = "CLIENT_IP"
    SESSION = "SESSION"
    TARGET_HOST = "TARGET_HOST"


_SCOPE_REASON_KO: dict[LimitScope, str] = {
    LimitScope.CLIENT_IP: "같은 네트워크 주소에서 요청이 너무 많습니다.",
    LimitScope.SESSION: "이 브라우저에서 요청이 너무 많습니다.",
    LimitScope.TARGET_HOST: (
        "같은 사이트에 대한 무료 진단 요청이 너무 많습니다. "
        "무료 진단은 한 사이트에 보낼 수 있는 요청 수를 제한합니다."
    ),
}


@final
@dataclass(frozen=True, slots=True)
class Bucket:
    """One counter to check: what it counts, for whom, how many and over how long."""

    scope: LimitScope
    key: str
    limit: int
    window_seconds: int

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.limit < 0:
            raise ValueError("limit must not be negative")
        if not self.key:
            raise ValueError("a bucket needs a key")


@final
@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """Allowed, or refused with a scope, a wait and a Korean sentence."""

    allowed: bool
    scope: LimitScope | None = None
    retry_after_seconds: int = 0
    message_ko: str = ""
    limit: int = 0
    window_seconds: int = 0

    @classmethod
    def allow(cls) -> RateLimitDecision:
        return cls(allowed=True)

    @classmethod
    def refuse(cls, bucket: Bucket, *, retry_after_seconds: int) -> RateLimitDecision:
        wait = max(1, retry_after_seconds)
        window_minutes = max(1, bucket.window_seconds // 60)
        return cls(
            allowed=False,
            scope=bucket.scope,
            retry_after_seconds=wait,
            message_ko=(
                f"{_SCOPE_REASON_KO[bucket.scope]} "
                f"{window_minutes}분 동안 {bucket.limit}회까지 요청할 수 있습니다. "
                f"약 {wait}초 뒤에 다시 시도해 주세요."
            ),
            limit=bucket.limit,
            window_seconds=bucket.window_seconds,
        )

    def as_api_error(self) -> ApiError:
        """The platform error envelope for this refusal."""
        if self.allowed:
            raise ValueError("decision is allowed; there is no error to render")
        return ApiError.of(
            ErrorCode.RATE_LIMITED,
            self.message_ko,
            retry_after_seconds=self.retry_after_seconds,
        )


@runtime_checkable
class RateLimiter(Protocol):
    """What the public service needs from a limiter, and nothing more.

    ``acquire`` is all-or-nothing: if any bucket is full, none of them is charged. That
    matters because a refusal by the target-host bucket must not also spend the caller's
    own allowance — otherwise a busy victim site would quietly burn through the quota of
    every innocent visitor who tried to scan it.
    """

    def acquire(
        self, buckets: Sequence[Bucket], *, now: float | None = None
    ) -> RateLimitDecision: ...


@final
class InMemoryRateLimiter:
    """A sliding-window limiter held in this process's memory.

    **Limitation, stated plainly:** the counters live in one process. Running several
    API workers multiplies the effective limit by the number of workers, and a restart
    forgets every counter. The production backing is Redis — one shared window across
    every process — and it is deliberately not implemented here; see
    :data:`MEMORY_BACKEND_LIMITATION_KO` and the integration request.

    A sliding window rather than a fixed one, because a fixed window lets a caller spend
    the whole allowance at ``:59`` and the whole of the next one at ``:01``.

    **Every counter access holds a lock.** ``acquire`` checks each bucket and then charges
    it, and those are two separate steps: without a lock, two threads can both pass the
    check before either charges, and both are allowed. That is not theoretical — forcing
    thread switches (``sys.setswitchinterval(1e-9)``) with 32 threads against a limit of
    10 let **14** through, reproducibly. The crawler fetches pages concurrently, so this
    is the ordinary case rather than an exotic one, and the bucket it would break is the
    one that stops VEO being pointed at a third party. ``test_limits.py`` keeps the
    reproduction.
    """

    __slots__ = ("_clock", "_hits", "_last_sweep", "_lock", "_sweep_interval")

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        sweep_interval_seconds: float = 60.0,
    ) -> None:
        self._clock = clock
        self._hits: dict[tuple[LimitScope, str], _Counter] = {}
        self._sweep_interval = sweep_interval_seconds
        self._last_sweep: float | None = None
        self._lock = threading.Lock()

    def acquire(
        self, buckets: Sequence[Bucket], *, now: float | None = None
    ) -> RateLimitDecision:
        moment = self._clock() if now is None else now

        # 검사와 청구가 한 덩어리여야 한다. 사이에 다른 스레드가 끼면 둘 다 통과한다.
        with self._lock:
            self._sweep_if_due(moment)

            for bucket in buckets:
                counter = self._live_counter(bucket, moment)
                if counter is not None and len(counter.hits) >= bucket.limit:
                    return RateLimitDecision.refuse(
                        bucket, retry_after_seconds=_retry_after(bucket, counter, moment)
                    )
                if bucket.limit == 0:
                    return RateLimitDecision.refuse(
                        bucket, retry_after_seconds=bucket.window_seconds
                    )

            for bucket in buckets:
                counter = self._hits.setdefault(
                    (bucket.scope, bucket.key), _Counter(window_seconds=bucket.window_seconds)
                )
                counter.window_seconds = bucket.window_seconds
                counter.hits.append(moment)

        return RateLimitDecision.allow()

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
            self._last_sweep = None

    def tracked_key_count(self) -> int:
        """How many keys are currently held. Used by tests to prove the sweep works."""
        with self._lock:
            return len(self._hits)

    # ----------------------------------------------------------------- #
    # Internals
    # ----------------------------------------------------------------- #

    def _live_counter(self, bucket: Bucket, moment: float) -> _Counter | None:
        counter = self._hits.get((bucket.scope, bucket.key))
        if counter is None:
            return None
        counter.drop_expired(moment)
        if not counter.hits:
            del self._hits[(bucket.scope, bucket.key)]
            return None
        return counter

    def _sweep_if_due(self, moment: float) -> None:
        """Drop keys whose every hit has aged out.

        Without this the dictionary grows once per distinct address, forever, driven
        entirely by strangers — an unbounded allocation on the one endpoint anybody can
        call. Each counter remembers its own window, so a sweep can never discard a hit
        that still counts.
        """
        if self._last_sweep is None:
            self._last_sweep = moment
            return
        if moment - self._last_sweep < self._sweep_interval:
            return
        self._last_sweep = moment
        for key, counter in list(self._hits.items()):
            counter.drop_expired(moment)
            if not counter.hits:
                del self._hits[key]


@final
@dataclass(slots=True)
class _Counter:
    """The hits recorded for one key, and the window they are counted over."""

    window_seconds: int
    hits: deque[float] = field(default_factory=deque)

    def drop_expired(self, moment: float) -> None:
        cutoff = moment - self.window_seconds
        while self.hits and self.hits[0] <= cutoff:
            self.hits.popleft()


def _retry_after(bucket: Bucket, counter: _Counter, moment: float) -> int:
    """Seconds until the oldest counted hit leaves the window."""
    if not counter.hits:
        return bucket.window_seconds
    # Once ``limit`` hits are in the window, room appears when the oldest one expires.
    return max(1, math.ceil(counter.hits[0] + bucket.window_seconds - moment))


# --------------------------------------------------------------------------- #
# Charging the host budget where the contact actually happens
# --------------------------------------------------------------------------- #


class HostBudgetExceeded(Exception):
    """VEO was about to contact a host whose hourly budget is spent.

    Deliberately an exception rather than a ``UrlDecision`` rejection. It is raised from
    inside :meth:`HostBudgetGuard.validate`, which :class:`~veo.common.security.fetcher.SafeFetcher`
    calls before every hop, and it has to travel out through the fetcher untouched so
    the caller can answer ``429`` with a wait. Rendering it as a guard rejection would
    turn "come back in twenty minutes" into "분석할 수 없는 도메인입니다", which is both
    wrong and unactionable.
    """

    def __init__(self, decision: RateLimitDecision) -> None:
        self.decision = decision
        super().__init__(decision.message_ko)


@final
class HostBudgetGuard(UrlGuard):
    """A :class:`UrlGuard` that also charges the target-host bucket, per hop.

    This exists because of *where* it sits. ``SafeFetcher.fetch`` calls
    ``guard.validate(url, hop=n)`` immediately before opening each connection — for the
    original URL and again for every redirect it is asked to follow. Charging here
    therefore means:

    * every URL in a multi-URL scan is charged, not only the first;
    * the ``robots.txt`` fetch is charged, because it is a real second request;
    * a redirect is charged against the host it *lands on*, before it is followed; and
    * a full bucket aborts the fetch **before** the request is sent, because ``validate``
      runs ahead of ``_stream``.

    Charging in the service, keyed on the submitted URL, achieved none of those. That
    version was demonstrated delivering eighty requests to a host limited to ten.

    The security decision itself is delegated untouched to ``inner``: this class never
    approves anything the real guard refused, and it never resolves a host of its own.
    A refused decision is returned as-is and costs nothing, so a rejected URL cannot be
    used to burn a third party's budget.
    """

    __slots__ = ("_inner", "_limit", "_limiter", "_window_seconds")

    def __init__(
        self,
        inner: UrlGuard,
        *,
        limiter: RateLimiter,
        limit: int,
        window_seconds: int = TARGET_HOST_WINDOW_SECONDS,
    ) -> None:
        # The policy is mirrored so ``SafeFetcher`` reads the same redirect ceiling and
        # port allowlist it would have read from ``inner``. The inherited resolver is
        # never used: every decision is delegated.
        super().__init__(policy=inner.policy)
        self._inner = inner
        self._limiter = limiter
        self._limit = limit
        self._window_seconds = window_seconds

    def validate(self, raw_url: str, *, hop: int = 0) -> UrlDecision:
        decision = self._inner.validate(raw_url, hop=hop)
        if not decision.allowed or decision.host is None:
            return decision

        budget = self._limiter.acquire(
            [
                Bucket(
                    scope=LimitScope.TARGET_HOST,
                    key=decision.host,
                    limit=self._limit,
                    window_seconds=self._window_seconds,
                )
            ]
        )
        if not budget.allowed:
            raise HostBudgetExceeded(budget)
        return decision
