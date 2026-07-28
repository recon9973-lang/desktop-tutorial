"""Response envelope, error shape and pagination — identical on every VEO endpoint."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from veo.contracts.enums import RETRYABLE_ERROR_CODES, DataSource, ErrorCode, ProviderState

_STRICT = ConfigDict(extra="forbid")


class FieldError(BaseModel):
    model_config = _STRICT

    field: str = Field(description="Dotted path to the offending input field.")
    code: str
    message: str = Field(description="Safe, user-facing message. Never contains secrets.")


class ApiError(BaseModel):
    """The only error shape VEO returns.

    ``message`` is safe to show a customer. Anything sensitive stays behind
    ``internal_error_ref``, which correlates to server-side logs.
    """

    model_config = _STRICT

    code: ErrorCode
    message: str
    field_errors: list[FieldError] = Field(default_factory=list)
    retryable: bool = False
    retry_after_seconds: int | None = None
    internal_error_ref: str | None = None
    documentation_url: str | None = None

    @classmethod
    def of(cls, code: ErrorCode, message: str, **kwargs: Any) -> ApiError:
        kwargs.setdefault("retryable", code in RETRYABLE_ERROR_CODES)
        return cls(code=code, message=message, **kwargs)


class SourceAttribution(BaseModel):
    """Provenance for a value. Attached wherever VEO shows a number it did not compute."""

    model_config = _STRICT

    source: DataSource
    provider_state: ProviderState = ProviderState.ENABLED
    collected_at: datetime | None = None
    source_period: str | None = Field(
        default=None, description="Period the source data covers, e.g. '2026-06'."
    )
    api_version: str | None = None
    raw_response_hash: str | None = None
    cache_hit: bool = False
    note_ko: str | None = None


class ResponseMeta(BaseModel):
    model_config = _STRICT

    request_id: str
    generated_at: datetime
    sources: list[SourceAttribution] = Field(default_factory=list)
    scoring_spec_id: str | None = None
    scoring_spec_version: str | None = None
    scoring_spec_checksum: str | None = None


class PageInfo(BaseModel):
    model_config = _STRICT

    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=200)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_next: bool
    has_previous: bool

    @classmethod
    def build(cls, *, page: int, page_size: int, total_items: int) -> PageInfo:
        total_pages = (total_items + page_size - 1) // page_size if page_size else 0
        return cls(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )


class ApiResponse[T](BaseModel):
    """Exactly one of ``data`` or ``error`` is populated."""

    model_config = _STRICT

    data: T | None = None
    error: ApiError | None = None
    meta: ResponseMeta


class PagedResponse[T](BaseModel):
    model_config = _STRICT

    data: list[T] = Field(default_factory=list)
    error: ApiError | None = None
    page_info: PageInfo
    meta: ResponseMeta
