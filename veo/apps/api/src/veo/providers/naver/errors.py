"""Typed failures, retry, circuit breaking, and the single value VEO degrades to.

Every path in this module ends in the same place: when Naver will not answer, the caller
receives :data:`UNKNOWN` and a :class:`ProviderFailure` that says why. It never receives
``0``, an average of nothing, or a stale value presented as fresh. ADR 0004 makes that a
product rule; this module is where it is enforced for the Naver adapters.

Three mechanisms, in the order they engage:

* **Classification.** An HTTP status or a transport exception becomes one typed error
  carrying a machine :class:`~veo.contracts.enums.ErrorCode`, a customer-safe Korean
  message, and whether retrying could possibly help.
* **Backoff.** Retryable failures are retried with exponential delay and jitter, and the
  provider's own ``Retry-After`` wins when it supplies one. Jitter matters because
  without it every worker that failed at the same moment retries at the same moment.
* **Circuit breaking.** After enough consecutive failures the breaker opens and calls
  stop being made at all — which is both politeness toward a struggling provider and the
  difference between one slow request and a queue of workers all waiting on a timeout.

Provider error text is never propagated. It routinely quotes the credential back, so
``message_ko`` is a fixed string per error class and the provider's own words go no
further than a debug log line.
"""

from __future__ import annotations

import json
import random
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar, Self, final

from veo.contracts.enums import ErrorCode, ProviderState
from veo.providers.errors import CircuitOpenError, ProviderError

__all__ = [
    "UNKNOWN",
    "CallOutcome",
    "CircuitBreaker",
    "CircuitState",
    "NaverCircuitOpenError",
    "NaverCredentialMissingError",
    "NaverForbiddenError",
    "NaverProviderError",
    "NaverRateLimitedError",
    "NaverRequestRejectedError",
    "NaverResponseTooLargeError",
    "NaverSchemaError",
    "NaverServerError",
    "NaverTimeoutError",
    "NaverTransportError",
    "NaverUnauthorizedError",
    "ProviderFailure",
    "ResilientCaller",
    "RetryPolicy",
    "UnknownValue",
    "classify_status",
    "classify_transport_exception",
]


# --------------------------------------------------------------------------- #
# UNKNOWN
# --------------------------------------------------------------------------- #


@final
class UnknownValue:
    """The absence of a measurement. A singleton, and deliberately not a number.

    It is falsy so that ``if value:`` guards behave, but it is not an ``int``, has no
    arithmetic, and formats as ``UNKNOWN`` — so a value that reaches a template or a log
    line announces itself rather than rendering as ``0`` or ``None``.
    """

    _instance: ClassVar[UnknownValue | None] = None

    def __new__(cls) -> UnknownValue:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "UNKNOWN"

    def __str__(self) -> str:
        return "UNKNOWN"


#: The one value every unanswerable provider call resolves to.
UNKNOWN = UnknownValue()


# --------------------------------------------------------------------------- #
# Typed errors
# --------------------------------------------------------------------------- #


class NaverProviderError(ProviderError):
    """A call to Naver that did not produce a usable answer.

    The behaviour lives in :class:`veo.providers.errors.ProviderError`; this subclass
    exists to give the customer-facing sentence the right subject. It used to be the
    shared base for every provider, which made an OpenAI timeout a Naver error by type.
    """

    message_ko: ClassVar[str] = "네이버 응답을 받지 못해 이 항목은 측정 불가입니다."


class NaverCredentialMissingError(NaverProviderError):
    """No credential is configured. Not a failure — a state, reported as one."""

    provider_state: ClassVar[ProviderState] = ProviderState.DISABLED_NO_CREDENTIAL
    retryable: ClassVar[bool] = False
    message_ko: ClassVar[str] = (
        "네이버 자격증명이 없어 이 제공자는 비활성 상태입니다. 관련 수치는 '측정 불가'이며, "
        "VEO는 추정값을 실제 데이터처럼 표시하지 않습니다."
    )


class NaverUnauthorizedError(NaverProviderError):
    """401 — the credential was rejected. Retrying the same key cannot fix it."""

    retryable: ClassVar[bool] = False
    message_ko: ClassVar[str] = (
        "네이버가 자격증명을 거부했습니다(401). 저장된 키를 다시 확인해 주세요. "
        "이 항목은 '측정 불가'로 표시됩니다."
    )


class NaverForbiddenError(NaverProviderError):
    """403 — authenticated, but not permitted. Also not fixable by retrying."""

    retryable: ClassVar[bool] = False
    message_ko: ClassVar[str] = (
        "네이버에서 권한이 거부되었습니다(403). 계정 권한을 확인해 주세요. "
        "이 항목은 '측정 불가'로 표시됩니다."
    )


class NaverRateLimitedError(NaverProviderError):
    """429 — too many calls. The one failure the provider tells us how to fix."""

    error_code: ClassVar[ErrorCode] = ErrorCode.PROVIDER_RATE_LIMITED
    retryable: ClassVar[bool] = True
    message_ko: ClassVar[str] = (
        "네이버 호출 한도를 초과했습니다(429). 잠시 후 다시 시도해 주세요. "
        "지금은 '측정 불가'로 표시됩니다."
    )


class NaverServerError(NaverProviderError):
    """5xx — the provider's problem, and worth retrying."""

    retryable: ClassVar[bool] = True
    message_ko: ClassVar[str] = (
        "네이버 서버가 응답하지 못했습니다. 이 항목은 '측정 불가'로 표시됩니다."
    )


class NaverTimeoutError(NaverProviderError):
    retryable: ClassVar[bool] = True
    message_ko: ClassVar[str] = (
        "네이버 응답이 제한 시간을 초과했습니다. 이 항목은 '측정 불가'로 표시됩니다."
    )


class NaverTransportError(NaverProviderError):
    retryable: ClassVar[bool] = True
    message_ko: ClassVar[str] = (
        "네이버에 연결하지 못했습니다. 이 항목은 '측정 불가'로 표시됩니다."
    )


class NaverSchemaError(NaverProviderError):
    """The answer arrived but is not the shape VEO knows how to read.

    Not retryable and never partially salvaged: guessing which field replaced which is
    exactly how a wrong number enters a report. VEO stops and says it cannot measure.
    """

    retryable: ClassVar[bool] = False
    message_ko: ClassVar[str] = (
        "네이버 응답 형식이 VEO가 아는 형식과 다릅니다. 잘못 해석한 수치를 내보내지 않기 위해 "
        "이 항목은 '측정 불가'로 표시합니다."
    )


class NaverRequestRejectedError(NaverProviderError):
    """네이버가 **우리 요청**을 거절했다. 응답 형식 문제가 아니다.

    이 둘을 갈라 놓는 이유는 고치는 사람이 어디를 봐야 하는지가 정반대이기 때문이다.
    형식 오류라고 적으면 네이버가 계약을 바꿨는지 뒤지게 되는데, 실제로는 우리가 보낸
    값이 규격에 안 맞는 것이다. 실제로 그렇게 헤맬 뻔했다 — 띄어쓰기가 든 키워드가
    400 을 받고 있었고, 메시지는 "응답 형식이 다릅니다" 라고 말하고 있었다.
    """

    retryable: ClassVar[bool] = False
    message_ko: ClassVar[str] = (
        "네이버가 이 요청을 받아들이지 않았습니다. 보낸 값이 네이버 규격에 맞지 않는 "
        "경우이며, 이 항목은 '측정 불가'로 표시됩니다."
    )


class NaverResponseTooLargeError(NaverProviderError):
    retryable: ClassVar[bool] = False
    message_ko: ClassVar[str] = (
        "네이버 응답이 허용 한도를 초과했습니다. 이 항목은 '측정 불가'로 표시됩니다."
    )


class NaverCircuitOpenError(CircuitOpenError):
    """Calls are suspended after repeated failures."""

    provider_state: ClassVar[ProviderState] = ProviderState.CIRCUIT_OPEN
    retryable: ClassVar[bool] = False
    message_ko: ClassVar[str] = (
        "연속 실패로 네이버 호출을 일시 차단했습니다. 잠시 후 자동으로 재시도합니다. "
        "지금은 '측정 불가'로 표시됩니다."
    )


def classify_status(status_code: int, *, retry_after: str | None = None) -> NaverProviderError:
    """Turn an HTTP status into exactly one typed error."""
    if status_code == 401:
        return NaverUnauthorizedError(f"status={status_code}")
    if status_code == 403:
        return NaverForbiddenError(f"status={status_code}")
    if status_code == 429:
        return NaverRateLimitedError(
            f"status={status_code}", retry_after_seconds=_parse_retry_after(retry_after)
        )
    if 500 <= status_code <= 599:
        return NaverServerError(f"status={status_code}")
    if 400 <= status_code <= 499:
        # 우리가 보낸 것이 거절된 것이다. 응답 **형식**이 달라진 것과 섞으면, 고치는
        # 사람이 네이버 문서를 뒤지는 동안 원인은 우리 쪽에 그대로 남는다.
        return NaverRequestRejectedError(f"status={status_code}")
    # Anything else with a non-2xx status is a contract surprise, not a measurement.
    return NaverSchemaError(f"unexpected status={status_code}")


def classify_transport_exception(exc: Exception) -> NaverProviderError:
    """Turn a transport-level exception into a typed error without importing its text."""
    name = type(exc).__name__
    if "Timeout" in name:
        return NaverTimeoutError(name)
    return NaverTransportError(name)


def _parse_retry_after(value: str | None) -> int | None:
    """Seconds from a ``Retry-After`` header, or ``None``.

    Only the delta-seconds form is honoured. An HTTP-date form would need a trusted clock
    comparison, and defaulting to *some* number when the header is unparseable would be
    inventing a delay the provider never asked for.
    """
    if value is None:
        return None
    try:
        seconds = int(value.strip())
    except ValueError:
        return None
    return seconds if seconds >= 0 else None


# --------------------------------------------------------------------------- #
# Failure records
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ProviderFailure:
    """Everything a caller may know about a failed call. No provider text."""

    error_code: ErrorCode
    provider_state: ProviderState
    reason_ko: str
    retryable: bool
    retry_after_seconds: int | None
    occurred_at: datetime

    @classmethod
    def from_error(cls, error: ProviderError, *, occurred_at: datetime | None = None) -> Self:
        """Build a failure from any provider's error, not only Naver's.

        Typed against the neutral base so the answer-engine adapters, which raise their
        own family, produce the same failure shape without inheriting Naver's identity.
        """
        return cls(
            error_code=error.error_code,
            provider_state=error.provider_state,
            reason_ko=error.message_ko,
            retryable=error.retryable,
            retry_after_seconds=error.retry_after_seconds,
            occurred_at=occurred_at or datetime.now(UTC),
        )


@dataclass(frozen=True, slots=True)
class CallOutcome[T]:
    """The result of a resilient call: a value, or UNKNOWN with a reason."""

    value: T | UnknownValue
    failure: ProviderFailure | None
    attempts: int

    @property
    def succeeded(self) -> bool:
        return not isinstance(self.value, UnknownValue)


# --------------------------------------------------------------------------- #
# Backoff
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Exponential backoff with jitter.

    ``jitter_ratio`` spreads each delay across ``±ratio`` of its computed value. With
    several workers failing on the same provider outage, an unjittered policy has them
    all return at the same instant and reproduce the outage themselves.
    """

    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 8.0
    jitter_ratio: float = 0.5

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay_seconds < 0 or self.max_delay_seconds < 0:
            raise ValueError("delays must not be negative")
        if not 0.0 <= self.jitter_ratio <= 1.0:
            raise ValueError("jitter_ratio must be between 0 and 1")

    def delay_for(
        self, attempt: int, *, random_value: float, retry_after_seconds: int | None = None
    ) -> float:
        """Seconds to wait before ``attempt + 1``. ``attempt`` is 1-based.

        A provider-supplied ``Retry-After`` wins outright: it is the only number in this
        calculation that came from the provider rather than from VEO's own guess.
        """
        if retry_after_seconds is not None:
            return float(retry_after_seconds)
        raw: float = self.base_delay_seconds * float(2 ** (attempt - 1))
        capped: float = min(raw, self.max_delay_seconds)
        spread: float = capped * self.jitter_ratio
        jittered: float = capped - spread + (2.0 * spread * random_value)
        return max(0.0, jittered)


# --------------------------------------------------------------------------- #
# Circuit breaker
# --------------------------------------------------------------------------- #


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Stops calling a provider that keeps failing, and probes it later.

    The clock is injected so the reset window is testable without sleeping through it.
    """

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        reset_after_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        self._threshold = failure_threshold
        self._reset_after = reset_after_seconds
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None
        self._half_open = False

    @property
    def state(self) -> CircuitState:
        if self._opened_at is None:
            return CircuitState.CLOSED
        return CircuitState.HALF_OPEN if self._half_open else CircuitState.OPEN

    def provider_state(self) -> ProviderState:
        return (
            ProviderState.CIRCUIT_OPEN
            if self.state is CircuitState.OPEN
            else ProviderState.ENABLED
        )

    def before_call(self) -> None:
        """Raise :class:`NaverCircuitOpenError` unless a call may be attempted."""
        if self._opened_at is None:
            return
        if self._clock() - self._opened_at >= self._reset_after:
            self._half_open = True
            return
        raise NaverCircuitOpenError(f"open for {self._clock() - self._opened_at:.1f}s")

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None
        self._half_open = False

    def record_failure(self) -> None:
        if self._half_open:
            # The probe failed: back to open, and the window starts again.
            self._half_open = False
            self._opened_at = self._clock()
            return
        self._failures += 1
        if self._failures >= self._threshold:
            self._opened_at = self._clock()


# --------------------------------------------------------------------------- #
# The caller
# --------------------------------------------------------------------------- #


class ResilientCaller:
    """Runs one provider operation with retry, breaking, and degradation to UNKNOWN.

    :meth:`call` does not raise a provider error. That is the whole point: a caller that
    has to remember a ``try`` block is a caller that will one day forget one and let an
    exception become a 500 where the honest answer was "측정 불가".
    """

    def __init__(
        self,
        *,
        policy: RetryPolicy | None = None,
        breaker: CircuitBreaker | None = None,
        sleep: Callable[[float], None] = time.sleep,
        random_value: Callable[[], float] = random.random,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._policy = policy or RetryPolicy()
        self._breaker = breaker or CircuitBreaker()
        self._sleep = sleep
        self._random = random_value
        self._now = now

    @property
    def breaker(self) -> CircuitBreaker:
        return self._breaker

    def call[T](self, operation: Callable[[], T]) -> CallOutcome[T]:
        last: ProviderError = NaverServerError("no attempt was made")
        attempts = 0

        for attempt in range(1, self._policy.max_attempts + 1):
            try:
                self._breaker.before_call()
            # Neutral base: any provider's circuit-open error must be recognised as
            # "not attempted" rather than escaping the caller as an unhandled error.
            except CircuitOpenError as circuit_open:
                return CallOutcome(
                    value=UNKNOWN,
                    failure=ProviderFailure.from_error(circuit_open, occurred_at=self._now()),
                    attempts=attempts,
                )

            attempts = attempt
            try:
                value = operation()
            # Catches the neutral base, not the Naver subclass: the answer-engine
            # adapters raise their own family, and they need the same retry, backoff
            # and circuit-breaker behaviour. Narrowing this to Naver would let an
            # OpenAI timeout escape the machinery entirely.
            except ProviderError as error:
                last = error
                self._breaker.record_failure()
                if not error.retryable or attempt == self._policy.max_attempts:
                    break
                self._sleep(
                    self._policy.delay_for(
                        attempt,
                        random_value=self._random(),
                        retry_after_seconds=error.retry_after_seconds,
                    )
                )
                continue
            else:
                self._breaker.record_success()
                return CallOutcome(value=value, failure=None, attempts=attempts)

        return CallOutcome(
            value=UNKNOWN,
            failure=ProviderFailure.from_error(last, occurred_at=self._now()),
            attempts=attempts,
        )

def parse_json_object(body: bytes) -> Mapping[str, Any]:
    """네이버가 준 본문을 객체로 — **아니면 그 자리에서 멈춘다.**

    검색광고와 데이터랩 어댑터가 이 함수를 한 벌씩 갖고 있었다(2026-08-09 실측).

    객체가 아닐 때 빈 사전으로 넘기지 않는다. 그러면 뒤쪽 코드가 "값이 없다" 로 읽고,
    **응답을 못 읽은 것이 "검색량 0" 이 되어** 그대로 거래처 화면까지 간다.
    """
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise NaverSchemaError(f"body is not JSON: {type(exc).__name__}") from None
    if not isinstance(payload, dict):
        raise NaverSchemaError("body is not a JSON object")
    return payload
