"""One HTTP execution path for the three Google adapters.

Every outbound call in this package goes through :class:`GoogleHttpCaller`, so the byte
ceiling, the redirect policy, the cookie policy and the status classification are decided
once. Three adapters each opening their own client is three chances to forget the cap.

Nothing here retries or breaks circuits — that is
:class:`~veo.providers.naver.errors.ResilientCaller`'s job, and this layer's contribution
is to raise the typed error it knows how to act on.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final, final

import httpx

from veo.common.http import read_capped
from veo.providers.google.errors import (
    GoogleProviderError,
    GoogleResponseTooLargeError,
    GoogleSchemaError,
    classify_status,
    classify_transport_exception,
    reason_from_error_body,
)

__all__ = [
    "API_KEY_HEADER",
    "DEFAULT_MAX_RESPONSE_BYTES",
    "DEFAULT_TIMEOUT_SECONDS",
    "ERROR_BODY_MAX_BYTES",
    "GoogleHttpCaller",
    "HttpAnswer",
]

#: Where an API key belongs on a Google request.
#:
#: Google documents ``?key=`` as well, and it works. It is not used here: a URL is the one
#: part of a request that everything it passes through writes down by default — access
#: logs, proxy histories, error reports. A header is not unloggable, but nothing logs it
#: without being told to.
#:
#: Verified live on 2026-08-01 against both ``pagespeedonline`` (200, identical payload to
#: the query-string form) and ``chromeuxreport`` (identical status to the query-string
#: form, so the header is read the same way on both hosts).
API_KEY_HEADER: Final = "X-goog-api-key"

DEFAULT_TIMEOUT_SECONDS: Final = 15.0

#: A PageSpeed response with full Lighthouse detail is comfortably over a megabyte, which
#: is why this ceiling is higher than the Naver adapters'. It is still a ceiling: an answer
#: that keeps arriving is refused rather than buffered.
DEFAULT_MAX_RESPONSE_BYTES: Final = 8 * 1024 * 1024

#: 오류 본문을 읽을 때의 상한. 성공 응답의 상한과 **따로** 둔다.
#:
#: 오류 설명은 작다. 실패한 요청에 8MB 를 허용할 이유가 없고, 그만큼 오는 것이 있다면
#: 그것은 오류 설명이 아니다. 여기서 꺼내는 것은 원인 토큰 하나뿐이라 이 정도면 넉넉하다.
ERROR_BODY_MAX_BYTES: Final = 64 * 1024


@final
@dataclass(frozen=True, slots=True)
class HttpAnswer:
    """A response that arrived with an acceptable status, and its bytes."""

    status_code: int
    body: bytes

    def json_object(self) -> Mapping[str, Any]:
        """The body as a JSON object, or a schema error.

        A maintenance page returning HTML with a 200 is the common case here, and it must
        not be mistaken for an empty result.
        """
        try:
            payload = json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise GoogleSchemaError(f"body is not JSON: {type(exc).__name__}") from None
        if not isinstance(payload, dict):
            raise GoogleSchemaError("body is not a JSON object")
        return payload


def _error_reason(response: httpx.Response, max_bytes: int) -> str | None:
    """실패 응답에서 원인 토큰만 꺼낸다. 못 꺼내면 ``None``.

    **여기서 나는 어떤 실패도 위로 올리지 않는다.** 이 값은 분류를 좁히는 데만 쓰이고,
    본문을 읽다 만 것 때문에 400 이 전송 오류로 둔갑하면 남는 것은 상태 코드마저 잃은
    진단이다. 못 읽었으면 원인 없이 상태만으로 분류한다 — 지금까지 하던 그대로다.
    """
    try:
        body = read_capped(response, max_bytes, GoogleResponseTooLargeError)
    except (httpx.HTTPError, GoogleProviderError):
        return None
    return reason_from_error_body(body)


class GoogleHttpCaller:
    """Sends one request and returns its bytes, or raises a typed error."""

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        max_error_bytes: int = ERROR_BODY_MAX_BYTES,
    ) -> None:
        self._transport = transport
        self._timeout = timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._max_error_bytes = max_error_bytes

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        json_body: Mapping[str, Any] | None = None,
        form_body: Mapping[str, str] | None = None,
        accept_statuses: Sequence[int] = (200,),
    ) -> HttpAnswer:
        """Perform one call.

        ``accept_statuses`` exists for the one case where a non-200 is an *answer* rather
        than a failure: CrUX replies 404 for a URL with too few real-user samples, and
        that is data — "no field measurement exists" — not an error to retry.
        """
        with httpx.Client(
            transport=self._transport,
            timeout=httpx.Timeout(self._timeout),
            follow_redirects=False,
            cookies=None,
        ) as client:
            request = client.build_request(
                method,
                url,
                params=dict(params) if params else None,
                headers=dict(headers) if headers else None,
                json=dict(json_body) if json_body is not None else None,
                data=dict(form_body) if form_body is not None else None,
            )
            try:
                response = client.send(request, stream=True)
            except httpx.HTTPError as exc:
                raise classify_transport_exception(exc) from None

            try:
                if response.status_code not in accept_statuses:
                    raise classify_status(
                        response.status_code,
                        retry_after=response.headers.get("retry-after"),
                        # 구글은 400 하나에 서로 반대인 두 사건을 담는다. 본문을 읽지
                        # 않으면 둘을 가를 수 없고, 가르지 못하면 우리 키가 죽은 날에도
                        # 화면은 고객 사이트를 탓하는 문장을 내보낸다.
                        reason=_error_reason(response, self._max_error_bytes),
                    )
                return HttpAnswer(
                    status_code=response.status_code,
                    body=read_capped(
                        response, self._max_response_bytes, GoogleResponseTooLargeError
                    ),
                )
            except httpx.HTTPError as exc:
                raise classify_transport_exception(exc) from None
            finally:
                response.close()

def as_number(value: Any) -> float | None:
    """제공자가 준 값을 실수로 — **못 읽으면 `0.0` 이 아니라 `None`.**

    구글 세 어댑터(PageSpeed·CrUX·Search Console)가 이 함수를 한 벌씩 갖고 있었다
    (2026-08-09 실측, 본문은 글자까지 같았다). 중복은 낭비로 끝나지 않는다 — 나중에
    만든 쪽이 원본의 제약을 모른 채 더 관대해진다(지침서 0-D).

    지키는 것 둘:

    * ``bool`` 은 숫자가 아니다. 파이썬에서 ``True`` 는 ``1`` 이라 걸러 두지 않으면
      "켜져 있음" 이 점수 ``1.0`` 으로 흘러간다.
    * 못 읽으면 ``None``. ``0.0`` 으로 접으면 **재지 못한 것이 "0 점" 이 된다** —
      정반대의 사실이다(ADR 0002).
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None
