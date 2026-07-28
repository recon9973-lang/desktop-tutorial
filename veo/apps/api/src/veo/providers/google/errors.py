"""Typed failures for the Google adapters, on the Naver adapters' machinery.

Nothing here reimplements retry, jitter, circuit breaking or ``UNKNOWN``. The behavioural
base is :class:`veo.providers.errors.ProviderError` and the machinery around it lives in
:mod:`veo.providers.naver.errors`; a second copy would be a second set of bugs and a
second place to fix them. What *is* provider-specific is the customer-visible text: a
Korean sentence that says "네이버" when Google timed out is simply wrong, so every error
class below carries its own fixed ``message_ko``.

The rules the Naver module established hold unchanged here:

* Provider error text never reaches a customer. Google's error bodies quote the API key
  back in ``API key not valid. Please pass a valid API key``, and quota messages carry the
  project number. ``message_ko`` is a class constant; the provider's words go no further
  than ``detail``, which stays server-side.
* An absent credential is a *state*, not a failure — and a credential slot filled with a
  placeholder is a third state again, because the remedy differs from an empty one.
* Every path ends at ``UNKNOWN`` with a stated reason. Never ``0``, never a stale value.
"""

from __future__ import annotations

from typing import ClassVar, Final

from veo.contracts.enums import ErrorCode, ProviderState
from veo.providers.errors import CircuitOpenError, ProviderError
from veo.providers.naver.errors import (
    UNKNOWN,
    CallOutcome,
    CircuitBreaker,
    ProviderFailure,
    ResilientCaller,
    RetryPolicy,
    UnknownValue,
)

__all__ = [
    "UNKNOWN",
    "CallOutcome",
    "CircuitBreaker",
    "GoogleCircuitBreaker",
    "GoogleCircuitOpenError",
    "GoogleCredentialInvalidError",
    "GoogleCredentialMissingError",
    "GoogleForbiddenError",
    "GoogleProviderError",
    "GoogleRateLimitedError",
    "GoogleResponseTooLargeError",
    "GoogleSchemaError",
    "GoogleServerError",
    "GoogleTimeoutError",
    "GoogleTransportError",
    "GoogleUnauthorizedError",
    "ProviderFailure",
    "ResilientCaller",
    "RetryPolicy",
    "UnknownValue",
    "classify_status",
    "classify_transport_exception",
]

#: The provider name as it appears to a customer. One constant so the Korean messages
#: below cannot drift apart from each other.
PROVIDER_NAME_KO: Final = "Google"

_UNMEASURABLE_KO: Final = "이 항목은 '측정 불가'로 표시됩니다."


class GoogleProviderError(ProviderError):
    """A call to a Google API that did not produce a usable answer.

    Rooted at the provider-neutral :class:`veo.providers.errors.ProviderError`, which is
    what :class:`~veo.providers.naver.errors.ResilientCaller` catches. A Google failure is
    therefore not, by type, a Naver failure — so a future ``except NaverProviderError``
    written to handle a Naver-specific fallback cannot silently swallow one.
    """

    error_code: ClassVar[ErrorCode] = ErrorCode.PROVIDER_UNAVAILABLE
    provider_state: ClassVar[ProviderState] = ProviderState.DEGRADED
    retryable: ClassVar[bool] = False
    message_ko: ClassVar[str] = f"{PROVIDER_NAME_KO} 응답을 받지 못해 이 항목은 측정 불가입니다."


class GoogleCredentialMissingError(GoogleProviderError):
    """No credential is configured. A state VEO reports, not an exception it survives."""

    provider_state: ClassVar[ProviderState] = ProviderState.DISABLED_NO_CREDENTIAL
    message_ko: ClassVar[str] = (
        "Google 자격증명이 없어 이 제공자는 비활성 상태입니다. 관련 수치는 '측정 불가'이며, "
        "VEO는 추정값을 실제 데이터처럼 표시하지 않습니다."
    )


class GoogleCredentialInvalidError(GoogleProviderError):
    """The slot is filled, but not with a credential.

    Separate from "missing" because the operator's next action differs. An empty slot
    needs a key; a slot holding ``[SENSITIVE]`` needs the *import* fixed, and telling that
    operator "no credential" sends them to paste a key that is already there.
    """

    provider_state: ClassVar[ProviderState] = ProviderState.DISABLED_INVALID_CREDENTIAL
    message_ko: ClassVar[str] = (
        "Google 자격증명 자리에 실제 값이 아닌 자리표시자가 들어 있습니다"
        "(예: 배포 도구가 기록한 '[SENSITIVE]'). 값을 다시 등록하기 전까지 이 항목은 "
        "'측정 불가'입니다."
    )


class GoogleUnauthorizedError(GoogleProviderError):
    """401 — the credential was rejected. Retrying the same key cannot fix it."""

    message_ko: ClassVar[str] = (
        f"Google이 자격증명을 거부했습니다(401). 저장된 키를 다시 확인해 주세요. {_UNMEASURABLE_KO}"
    )


class GoogleForbiddenError(GoogleProviderError):
    """403 — authenticated, but not permitted.

    On Google this most often means the API is not enabled on the project, or the service
    account was never added to the Search Console property. Both are account-side and
    neither is fixed by retrying.
    """

    message_ko: ClassVar[str] = (
        "Google에서 권한이 거부되었습니다(403). 해당 API 사용 설정과 계정 권한을 확인해 주세요. "
        f"{_UNMEASURABLE_KO}"
    )


class GoogleRateLimitedError(GoogleProviderError):
    """429 — quota. The one failure the provider sometimes tells us how to wait out."""

    error_code: ClassVar[ErrorCode] = ErrorCode.PROVIDER_RATE_LIMITED
    retryable: ClassVar[bool] = True
    message_ko: ClassVar[str] = (
        "Google 호출 한도를 초과했습니다(429). 잠시 후 다시 시도해 주세요. "
        "지금은 '측정 불가'로 표시됩니다."
    )


class GoogleServerError(GoogleProviderError):
    """5xx — the provider's problem, and worth retrying."""

    retryable: ClassVar[bool] = True
    message_ko: ClassVar[str] = f"Google 서버가 응답하지 못했습니다. {_UNMEASURABLE_KO}"


class GoogleTimeoutError(GoogleProviderError):
    retryable: ClassVar[bool] = True
    message_ko: ClassVar[str] = f"Google 응답이 제한 시간을 초과했습니다. {_UNMEASURABLE_KO}"


class GoogleTransportError(GoogleProviderError):
    retryable: ClassVar[bool] = True
    message_ko: ClassVar[str] = f"Google에 연결하지 못했습니다. {_UNMEASURABLE_KO}"


class GoogleSchemaError(GoogleProviderError):
    """The answer arrived but is not the shape VEO knows how to read.

    Never partially salvaged. Guessing which field replaced which is how a wrong number
    enters a report, and a wrong number is worse than an admitted gap.
    """

    message_ko: ClassVar[str] = (
        "Google 응답 형식이 VEO가 아는 형식과 다릅니다. 잘못 해석한 수치를 내보내지 않기 위해 "
        "이 항목은 '측정 불가'로 표시합니다."
    )


class GoogleResponseTooLargeError(GoogleProviderError):
    message_ko: ClassVar[str] = f"Google 응답이 허용 한도를 초과했습니다. {_UNMEASURABLE_KO}"


class GoogleCircuitOpenError(CircuitOpenError):
    """Calls are suspended after repeated failures.

    The one place a Google error still inherits a Naver identity, and not by choice:
    ``ResilientCaller.call`` catches :class:`NaverCircuitOpenError` *by name* on the
    breaker branch, and an error outside that hierarchy would escape ``call()`` entirely
    and become a 500 where the honest answer was 측정 불가. What this subclass fixes is
    the only thing that was wrong for Google — the sentence a customer reads.
    ``INTEGRATION_REQUEST.md`` §1 asks for an injectable circuit-open class so this can
    go.
    """

    message_ko: ClassVar[str] = (
        "연속 실패로 Google 호출을 일시 차단했습니다. 잠시 후 자동으로 재시도합니다. "
        "지금은 '측정 불가'로 표시됩니다."
    )


class GoogleCircuitBreaker(CircuitBreaker):
    """The shared breaker, speaking about Google when it refuses a call."""

    def before_call(self) -> None:
        try:
            super().before_call()
        except CircuitOpenError as circuit_open:
            raise GoogleCircuitOpenError(circuit_open.detail) from None


def classify_status(status_code: int, *, retry_after: str | None = None) -> GoogleProviderError:
    """Turn an HTTP status into exactly one typed error."""
    if status_code == 401:
        return GoogleUnauthorizedError(f"status={status_code}")
    if status_code == 403:
        return GoogleForbiddenError(f"status={status_code}")
    if status_code == 429:
        return GoogleRateLimitedError(
            f"status={status_code}", retry_after_seconds=_parse_retry_after(retry_after)
        )
    if 500 <= status_code <= 599:
        return GoogleServerError(f"status={status_code}")
    # Anything else non-2xx is a contract surprise, not a measurement.
    return GoogleSchemaError(f"unexpected status={status_code}")


def classify_transport_exception(exc: Exception) -> GoogleProviderError:
    """Turn a transport-level exception into a typed error without importing its text."""
    if "Timeout" in type(exc).__name__:
        return GoogleTimeoutError(type(exc).__name__)
    return GoogleTransportError(type(exc).__name__)


def _parse_retry_after(value: str | None) -> int | None:
    """Seconds from a ``Retry-After`` header, or ``None``.

    Only the delta-seconds form is honoured, for the reason the Naver module gives: an
    HTTP-date needs a trusted clock, and inventing a delay the provider never asked for is
    worse than falling back to VEO's own backoff.
    """
    if value is None:
        return None
    try:
        seconds = int(value.strip())
    except ValueError:
        return None
    return seconds if seconds >= 0 else None
