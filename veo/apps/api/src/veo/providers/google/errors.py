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

import json
import re
from typing import Any, ClassVar, Final

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
    "GoogleKeyRejectedError",
    "GoogleProviderError",
    "GoogleRateLimitedError",
    "GoogleRequestRejectedError",
    "GoogleResponseTooLargeError",
    "GoogleSchemaError",
    "GoogleServerError",
    "GoogleTargetUnreachableError",
    "GoogleTimeoutError",
    "GoogleTransportError",
    "GoogleUnauthorizedError",
    "ProviderFailure",
    "ResilientCaller",
    "RetryPolicy",
    "UnknownValue",
    "classify_status",
    "classify_transport_exception",
    "reason_from_error_body",
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


class GoogleRequestRejectedError(GoogleProviderError):
    """4xx — 우리가 보낸 것이 거절됐다. 응답 *형식*이 달라진 것과는 다른 사건이다.

    섞어 놓으면 고치는 사람이 구글 문서에서 바뀐 필드를 찾는 동안, 원인은 우리가 보낸
    요청에 그대로 남아 있게 된다. 네이버 어댑터가 같은 이유로 먼저 갈라 놓았다.
    """

    message_ko: ClassVar[str] = (
        "Google이 이 요청을 받아들이지 않았습니다. 보낸 값이 Google 규격에 맞지 않는 "
        f"경우이며, {_UNMEASURABLE_KO}"
    )


class GoogleKeyRejectedError(GoogleProviderError):
    """400 + ``API_KEY_INVALID`` — **우리 문제다. 고객이 할 수 있는 것이 없다.**

    구글은 거부된 키를 401 이 아니라 400 으로 돌려준다(2026-08-01 실측). 그래서 이것이
    갈라지지 않으면 "응답 형식이 다릅니다" 로 나가고, 그 문장을 읽은 사람은 구글이
    스키마를 바꿨다고 믿은 채 우리 키가 죽어 있는 동안 계속 진단을 돌린다.

    문장이 **사이트의 문제가 아니라고 먼저 말하는** 이유는 성능이 통째로 빠진 보고서를
    받은 고객이 자기 사이트부터 고치려 들기 때문이다(0-J).
    """

    message_ko: ClassVar[str] = (
        "Google이 VEO의 API 키를 거부했습니다. **사이트의 문제가 아니라 VEO 설정 "
        f"문제이며**, 저장된 키를 다시 등록해야 합니다. {_UNMEASURABLE_KO}"
    )


class GoogleTargetUnreachableError(GoogleProviderError):
    """400/5xx + ``FAILED_DOCUMENT_REQUEST`` — 구글이 **대상 페이지를 열지 못했다.**

    같은 400 을 쓰지만 위와 정반대다. 이쪽은 우리 설정이 멀쩡하고 고객에게 알릴 정보가
    있다 — 페이지가 너무 느리거나 외부 접근이 막혀 있다.

    재시도하지 않는다. 못 여는 이유는 대개 느려서이고, 다시 걸어도 같은 답이 온다.
    그 사이 재시도는 **모든 조직이 함께 쓰는 하루 한도**를 태운다.

    이 실패가 성능 점수를 조용히 올리지 않는다는 보장은 여기가 아니라 명세에 있다 —
    `sampling.perf_lab.min_measured_ratio` 가 표본 문턱을 못 넘으면 검사 자체를 측정
    불가로 만든다. 그것이 없으면 **못 연 페이지가 분모에서 빠져 사이트가 더 빨라 보인다.**
    """

    message_ko: ClassVar[str] = (
        "Google이 이 페이지를 열지 못해 성능을 재지 못했습니다. 페이지 응답이 너무 "
        "느리거나 외부 접근이 막혀 있는 경우가 대부분입니다. "
        f"{_UNMEASURABLE_KO}"
    )


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


#: 구글이 오류 본문에 적어 보내는 원인 토큰. 값은 **구글이 정한 문자열 그대로**다 —
#: 우리가 지어낸 이름을 나중에 구글 문서에서 찾을 수 있는 사람은 없다.
REASON_API_KEY_INVALID: Final = "API_KEY_INVALID"
REASON_FAILED_DOCUMENT_REQUEST: Final = "FAILED_DOCUMENT_REQUEST"

#: 원인 토큰으로 받아들일 모양. **산문은 통과하지 못한다.**
#:
#: 이 제한이 이 파일의 규칙 하나를 지킨다: 구글의 오류 문장은 API 키를 그대로 되돌려
#: 주고("API key not valid. Please pass a valid API key") 할당량 메시지에는 프로젝트
#: 번호가 들어 있다. 토큰만 꺼내면 그 문장이 흘러 나갈 통로 자체가 없다.
_REASON_TOKEN: Final = re.compile(r"^[A-Za-z0-9_]{1,64}$")

#: 원인을 찾아볼 자리. 구글이 같은 뜻을 두 군데에 쓴다 — 새 형식(`details`)을 먼저 본다.
_REASON_PATHS: Final = ("details", "errors")


def reason_from_error_body(body: bytes) -> str | None:
    """오류 본문에서 **원인 토큰 하나만** 꺼낸다. 없으면 ``None``.

    실패해도 예외를 올리지 않는다. 이 함수의 답은 상태 코드 분류를 **좁히는** 데만
    쓰이므로, 못 읽었다고 400 자체를 잃어서는 안 된다.
    """
    try:
        payload: Any = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None

    for path in _REASON_PATHS:
        entries = error.get(path)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            reason = entry.get("reason")
            if isinstance(reason, str) and _REASON_TOKEN.match(reason):
                return reason
    return None


def classify_status(
    status_code: int, *, retry_after: str | None = None, reason: str | None = None
) -> GoogleProviderError:
    """Turn an HTTP status — and, when we have it, the reason inside — into one error.

    **원인이 상태 코드보다 먼저다.** 구글은 400 하나에 서로 반대인 두 사건을 담아
    보내고(우리 키가 죽었다 / 고객 페이지를 못 열었다), 상태만 보면 둘이 같은 자리에
    앉는다. 그 자리에서 나가는 문장은 고객이 조치할 수 없는 문장이다.

    ``FAILED_DOCUMENT_REQUEST`` 는 5xx 에 실려 오기도 한다. 그때 상태부터 보면
    **재시도 가능**으로 분류되어, 열리지 않는 페이지를 다시 열어 보느라 모든 조직이
    함께 쓰는 하루 한도를 태운다.
    """
    if reason == REASON_API_KEY_INVALID:
        return GoogleKeyRejectedError(f"status={status_code} reason={reason}")
    if reason == REASON_FAILED_DOCUMENT_REQUEST:
        return GoogleTargetUnreachableError(f"status={status_code} reason={reason}")

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
    if 400 <= status_code <= 499:
        # 우리가 보낸 것이 거절된 것이다. 응답 형식이 달라진 것과 섞지 않는다.
        return GoogleRequestRejectedError(f"status={status_code}")
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
