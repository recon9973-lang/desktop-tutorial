"""Request-scoped dependencies: correlation ids and response envelopes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request

from veo.contracts.envelope import ApiResponse, ResponseMeta, SourceAttribution

REQUEST_ID_HEADER = "X-Request-Id"


def get_request_id(request: Request) -> str:
    """Resolve one correlation id per request.

    The result is cached on ``request.state`` so the middleware, the route handler and any
    error handler all report the *same* id — otherwise the id in the response header would
    not match the id in the body, and neither would match the logs.

    A caller-supplied value is accepted only when it is short and alphanumeric, so the
    header cannot be used to inject content into logs or responses.
    """
    cached: str | None = getattr(request.state, "veo_request_id", None)
    if cached is not None:
        return cached

    incoming = request.headers.get(REQUEST_ID_HEADER)
    if incoming and 8 <= len(incoming) <= 64 and incoming.replace("-", "").isalnum():
        request_id = incoming
    else:
        request_id = uuid.uuid4().hex

    request.state.veo_request_id = request_id
    return request_id


RequestId = Annotated[str, Depends(get_request_id)]


def build_meta(
    request_id: str,
    *,
    sources: list[SourceAttribution] | None = None,
    spec_id: str | None = None,
    spec_version: str | None = None,
    spec_checksum: str | None = None,
) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id,
        generated_at=datetime.now(UTC),
        sources=sources or [],
        scoring_spec_id=spec_id,
        scoring_spec_version=spec_version,
        scoring_spec_checksum=spec_checksum,
    )


def ok[T](data: T, request_id: str, **meta_kwargs: object) -> ApiResponse[T]:
    return ApiResponse[T](data=data, error=None, meta=build_meta(request_id, **meta_kwargs))  # type: ignore[arg-type]
