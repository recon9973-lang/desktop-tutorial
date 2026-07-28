"""Provider-neutral error base, shared by every outbound integration.

This exists because the retry and circuit-breaker machinery has to catch *something*,
and for a while that something was ``NaverProviderError``. The answer-engine adapters
then had to inherit from it, so an OpenAI timeout was, by type, a Naver error. Nothing
broke — but the next person to read a traceback would have had to unlearn it, and the
next provider after that would have inherited the confusion too.

The customer-facing rules live here, and every provider follows them:

* ``message_ko`` is a class constant. A provider's own error text frequently echoes the
  credential that failed, so it never reaches a caller — only this fixed sentence does.
* ``detail`` is for developers and stays server-side.
* An error is a *state*, not a value. A provider that could not answer produces
  ``측정 불가``, never a zero and never a guess.
"""

from __future__ import annotations

from typing import ClassVar

from veo.contracts.enums import ErrorCode, ProviderState


class ProviderError(Exception):
    """An outbound call that did not produce a usable answer.

    Subclass per provider family to give the customer-facing sentence the right subject,
    and per failure kind to carry the right error code and retryability.
    """

    error_code: ClassVar[ErrorCode] = ErrorCode.PROVIDER_UNAVAILABLE
    provider_state: ClassVar[ProviderState] = ProviderState.DEGRADED
    retryable: ClassVar[bool] = False
    message_ko: ClassVar[str] = "외부 제공자 응답을 받지 못해 이 항목은 측정 불가입니다."

    def __init__(self, detail: str = "", *, retry_after_seconds: int | None = None) -> None:
        self.detail = detail
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"{type(self).__name__}: {detail}" if detail else type(self).__name__)


class CircuitOpenError(ProviderError):
    """The breaker is open, so no call was attempted.

    Lives on the neutral base rather than on any one provider's, because
    :class:`~veo.providers.naver.errors.ResilientCaller` catches this type by name to
    tell "we did not try" apart from "we tried and it failed". When it was a Naver
    subclass, every other provider had to inherit Naver's identity to stay inside the
    machinery — and one that did not would have escaped ``call()`` and surfaced as a 500.
    """

    retryable: ClassVar[bool] = False
    message_ko: ClassVar[str] = (
        "연속 실패로 호출을 일시 차단했습니다. 이 항목은 측정 불가입니다."
    )


__all__ = ["CircuitOpenError", "ProviderError"]
