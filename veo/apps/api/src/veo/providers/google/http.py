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
    GoogleResponseTooLargeError,
    GoogleSchemaError,
    classify_status,
    classify_transport_exception,
)

__all__ = [
    "DEFAULT_MAX_RESPONSE_BYTES",
    "DEFAULT_TIMEOUT_SECONDS",
    "GoogleHttpCaller",
    "HttpAnswer",
]

DEFAULT_TIMEOUT_SECONDS: Final = 15.0

#: A PageSpeed response with full Lighthouse detail is comfortably over a megabyte, which
#: is why this ceiling is higher than the Naver adapters'. It is still a ceiling: an answer
#: that keeps arriving is refused rather than buffered.
DEFAULT_MAX_RESPONSE_BYTES: Final = 8 * 1024 * 1024


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


class GoogleHttpCaller:
    """Sends one request and returns its bytes, or raises a typed error."""

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        self._transport = transport
        self._timeout = timeout_seconds
        self._max_response_bytes = max_response_bytes

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



