"""Error normalisation, retry, circuit breaking, and degradation to UNKNOWN.

The point of every test here is the same: when Naver will not answer, VEO says so. It
does not return 0, it does not return an average of nothing, and it does not return the
last value it happened to see. It returns ``UNKNOWN`` with a reason.
"""

from __future__ import annotations

import httpx
import pytest

from veo.contracts.enums import ErrorCode, ProviderState
from veo.providers.naver.errors import (
    UNKNOWN,
    CircuitBreaker,
    CircuitState,
    NaverCircuitOpenError,
    NaverCredentialMissingError,
    NaverForbiddenError,
    NaverProviderError,
    NaverRateLimitedError,
    NaverSchemaError,
    NaverServerError,
    NaverTimeoutError,
    NaverTransportError,
    NaverUnauthorizedError,
    ProviderFailure,
    ResilientCaller,
    RetryPolicy,
    UnknownValue,
    classify_status,
    classify_transport_exception,
)


class StubClock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class RecordingSleeper:
    def __init__(self) -> None:
        self.slept: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.slept.append(seconds)


# --------------------------------------------------------------------------- #
# Status -> typed error
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("status", "expected", "error_code", "retryable"),
    [
        (401, NaverUnauthorizedError, ErrorCode.PROVIDER_UNAVAILABLE, False),
        (403, NaverForbiddenError, ErrorCode.PROVIDER_UNAVAILABLE, False),
        (429, NaverRateLimitedError, ErrorCode.PROVIDER_RATE_LIMITED, True),
        (500, NaverServerError, ErrorCode.PROVIDER_UNAVAILABLE, True),
        (502, NaverServerError, ErrorCode.PROVIDER_UNAVAILABLE, True),
        (503, NaverServerError, ErrorCode.PROVIDER_UNAVAILABLE, True),
    ],
)
def test_status_maps_to_a_typed_error(
    status: int, expected: type[NaverProviderError], error_code: ErrorCode, retryable: bool
) -> None:
    error = classify_status(status)
    assert isinstance(error, expected)
    assert error.error_code is error_code
    assert error.retryable is retryable
    assert error.message_ko


def test_rate_limit_carries_retry_after_when_the_provider_supplies_one() -> None:
    error = classify_status(429, retry_after="17")
    assert isinstance(error, NaverRateLimitedError)
    assert error.retry_after_seconds == 17


def test_rate_limit_without_retry_after_does_not_invent_one() -> None:
    error = classify_status(429)
    assert isinstance(error, NaverRateLimitedError)
    assert error.retry_after_seconds is None


def test_unexpected_4xx_is_a_schema_or_contract_failure_not_a_success() -> None:
    error = classify_status(418)
    assert isinstance(error, NaverProviderError)
    assert error.retryable is False


def test_timeout_maps_to_a_typed_error() -> None:
    error = classify_transport_exception(httpx.ReadTimeout("slow"))
    assert isinstance(error, NaverTimeoutError)
    assert error.error_code is ErrorCode.PROVIDER_UNAVAILABLE
    assert error.retryable is True


def test_connection_failure_maps_to_a_typed_error() -> None:
    error = classify_transport_exception(httpx.ConnectError("refused"))
    assert isinstance(error, NaverTransportError)
    assert error.retryable is True


def test_error_message_never_quotes_the_provider_detail() -> None:
    """``message_ko`` is customer-facing; provider text routinely quotes the credential."""
    error = classify_status(401)
    error_with_detail = NaverUnauthorizedError("X-API-KEY 0123456789abcdef rejected")
    assert "0123456789abcdef" not in error.message_ko
    assert "0123456789abcdef" not in error_with_detail.message_ko


# --------------------------------------------------------------------------- #
# Failure records
# --------------------------------------------------------------------------- #


def test_failure_record_keeps_state_and_reason() -> None:
    failure = ProviderFailure.from_error(NaverRateLimitedError(retry_after_seconds=5))
    assert failure.error_code is ErrorCode.PROVIDER_RATE_LIMITED
    assert failure.provider_state is ProviderState.DEGRADED
    assert failure.retry_after_seconds == 5
    assert failure.reason_ko


def test_missing_credential_is_disabled_not_degraded() -> None:
    failure = ProviderFailure.from_error(NaverCredentialMissingError())
    assert failure.provider_state is ProviderState.DISABLED_NO_CREDENTIAL
    assert failure.retryable is False


def test_circuit_open_reports_its_own_state() -> None:
    failure = ProviderFailure.from_error(NaverCircuitOpenError())
    assert failure.provider_state is ProviderState.CIRCUIT_OPEN


# --------------------------------------------------------------------------- #
# Backoff
# --------------------------------------------------------------------------- #


def test_backoff_grows_exponentially_before_jitter() -> None:
    policy = RetryPolicy(base_delay_seconds=0.5, max_delay_seconds=60.0, jitter_ratio=0.0)
    assert policy.delay_for(1, random_value=0.0) == pytest.approx(0.5)
    assert policy.delay_for(2, random_value=0.0) == pytest.approx(1.0)
    assert policy.delay_for(3, random_value=0.0) == pytest.approx(2.0)


def test_backoff_is_capped() -> None:
    policy = RetryPolicy(base_delay_seconds=1.0, max_delay_seconds=4.0, jitter_ratio=0.0)
    assert policy.delay_for(10, random_value=0.0) == pytest.approx(4.0)


def test_jitter_spreads_the_delay_and_never_goes_negative() -> None:
    policy = RetryPolicy(base_delay_seconds=1.0, max_delay_seconds=60.0, jitter_ratio=0.5)
    lowest = policy.delay_for(1, random_value=0.0)
    highest = policy.delay_for(1, random_value=1.0)
    assert lowest == pytest.approx(0.5)
    assert highest == pytest.approx(1.5)
    assert lowest >= 0.0


def test_retry_after_overrides_the_computed_delay() -> None:
    policy = RetryPolicy(base_delay_seconds=0.5, max_delay_seconds=60.0, jitter_ratio=0.0)
    assert policy.delay_for(1, random_value=0.0, retry_after_seconds=30) == pytest.approx(30.0)


# --------------------------------------------------------------------------- #
# Retrying and giving up
# --------------------------------------------------------------------------- #


def test_retries_a_retryable_failure_then_succeeds() -> None:
    sleeper = RecordingSleeper()
    caller = ResilientCaller(
        policy=RetryPolicy(max_attempts=3, jitter_ratio=0.0),
        breaker=CircuitBreaker(clock=StubClock()),
        sleep=sleeper,
        random_value=lambda: 0.0,
    )
    attempts: list[int] = []

    def operation() -> str:
        attempts.append(len(attempts) + 1)
        if len(attempts) < 3:
            raise NaverServerError("upstream wobbled")
        return "ok"

    outcome = caller.call(operation)
    assert outcome.value == "ok"
    assert outcome.attempts == 3
    assert outcome.failure is None
    assert len(sleeper.slept) == 2


def test_gives_up_after_the_last_attempt_and_returns_unknown() -> None:
    sleeper = RecordingSleeper()
    caller = ResilientCaller(
        policy=RetryPolicy(max_attempts=3, jitter_ratio=0.0),
        breaker=CircuitBreaker(failure_threshold=99, clock=StubClock()),
        sleep=sleeper,
        random_value=lambda: 0.0,
    )
    calls = 0

    def operation() -> str:
        nonlocal calls
        calls += 1
        raise NaverServerError("still down")

    outcome = caller.call(operation)
    assert calls == 3
    assert outcome.value is UNKNOWN
    assert isinstance(outcome.value, UnknownValue)
    assert outcome.failure is not None
    assert outcome.failure.error_code is ErrorCode.PROVIDER_UNAVAILABLE
    # Two sleeps for three attempts: it does not sleep after deciding to give up.
    assert len(sleeper.slept) == 2


def test_a_non_retryable_failure_is_not_retried() -> None:
    sleeper = RecordingSleeper()
    caller = ResilientCaller(
        policy=RetryPolicy(max_attempts=5, jitter_ratio=0.0),
        breaker=CircuitBreaker(failure_threshold=99, clock=StubClock()),
        sleep=sleeper,
        random_value=lambda: 0.0,
    )
    calls = 0

    def operation() -> str:
        nonlocal calls
        calls += 1
        raise NaverUnauthorizedError("rejected")

    outcome = caller.call(operation)
    assert calls == 1
    assert outcome.value is UNKNOWN
    assert sleeper.slept == []


@pytest.mark.parametrize(
    "error",
    [
        NaverUnauthorizedError(),
        NaverForbiddenError(),
        NaverRateLimitedError(),
        NaverServerError(),
        NaverTimeoutError(),
        NaverSchemaError(),
    ],
)
def test_every_provider_failure_degrades_to_unknown_never_to_a_number(
    error: NaverProviderError,
) -> None:
    caller = ResilientCaller(
        policy=RetryPolicy(max_attempts=1, jitter_ratio=0.0),
        breaker=CircuitBreaker(failure_threshold=99, clock=StubClock()),
        sleep=RecordingSleeper(),
        random_value=lambda: 0.0,
    )

    def operation() -> int:
        raise error

    outcome = caller.call(operation)
    assert outcome.value is UNKNOWN
    assert not isinstance(outcome.value, int)
    assert outcome.failure is not None


# --------------------------------------------------------------------------- #
# Circuit breaker
# --------------------------------------------------------------------------- #


def test_breaker_opens_after_the_failure_threshold() -> None:
    clock = StubClock()
    breaker = CircuitBreaker(failure_threshold=3, reset_after_seconds=60.0, clock=clock)

    for _ in range(3):
        breaker.before_call()
        breaker.record_failure()

    assert breaker.state is CircuitState.OPEN
    assert breaker.provider_state() is ProviderState.CIRCUIT_OPEN
    with pytest.raises(NaverCircuitOpenError):
        breaker.before_call()


def test_breaker_half_opens_after_the_reset_window_and_closes_on_success() -> None:
    clock = StubClock()
    breaker = CircuitBreaker(failure_threshold=2, reset_after_seconds=30.0, clock=clock)
    for _ in range(2):
        breaker.before_call()
        breaker.record_failure()
    assert breaker.state is CircuitState.OPEN

    clock.advance(31.0)
    breaker.before_call()
    assert breaker.state is CircuitState.HALF_OPEN

    breaker.record_success()
    assert breaker.state is CircuitState.CLOSED
    assert breaker.provider_state() is ProviderState.ENABLED


def test_a_failed_probe_reopens_the_breaker() -> None:
    clock = StubClock()
    breaker = CircuitBreaker(failure_threshold=2, reset_after_seconds=30.0, clock=clock)
    for _ in range(2):
        breaker.before_call()
        breaker.record_failure()
    clock.advance(31.0)
    breaker.before_call()
    breaker.record_failure()
    assert breaker.state is CircuitState.OPEN


def test_success_resets_the_failure_count() -> None:
    breaker = CircuitBreaker(failure_threshold=3, clock=StubClock())
    breaker.before_call()
    breaker.record_failure()
    breaker.before_call()
    breaker.record_success()
    for _ in range(2):
        breaker.before_call()
        breaker.record_failure()
    assert breaker.state is CircuitState.CLOSED


def test_an_open_breaker_short_circuits_the_call_without_touching_the_provider() -> None:
    clock = StubClock()
    breaker = CircuitBreaker(failure_threshold=1, reset_after_seconds=60.0, clock=clock)
    caller = ResilientCaller(
        policy=RetryPolicy(max_attempts=2, jitter_ratio=0.0),
        breaker=breaker,
        sleep=RecordingSleeper(),
        random_value=lambda: 0.0,
    )
    calls = 0

    def operation() -> str:
        nonlocal calls
        calls += 1
        raise NaverServerError("down")

    caller.call(operation)
    calls_after_first = calls

    outcome = caller.call(operation)
    assert calls == calls_after_first  # the provider was never dialled again
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None
    assert outcome.failure.provider_state is ProviderState.CIRCUIT_OPEN


def test_unknown_is_a_singleton_that_is_falsy_and_not_a_number() -> None:
    assert UNKNOWN is UnknownValue()
    assert not UNKNOWN
    assert not isinstance(UNKNOWN, int | float)
    assert repr(UNKNOWN) == "UNKNOWN"
