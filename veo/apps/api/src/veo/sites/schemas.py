"""Request and response models for ``/sites``, and the origin rule.

``origin`` decides what VEO will point a crawler at, so it is the strictest field in this
slice. It is stored as a bare scheme-plus-host — no path, no query, no fragment, no
userinfo — because everything downstream (the ``(project_id, origin)`` uniqueness
constraint, per-site rate limiting, the same-origin check on a discovered link) compares
origins as strings, and two spellings of one origin quietly become two sites.

Normalisation runs through :mod:`veo.common.urls`, which already refuses the inputs that
matter: control characters, ``user:pass@``, percent-escaped hosts, and every legacy
``inet_aton`` spelling of a loopback address. What this module adds is the *bare origin*
requirement and an explicit rejection of anything the parser would otherwise drop
silently — a fragment, for instance, disappears during parsing, and dropping it would
mean accepting an input that says something the stored value does not.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from veo.common.urls import HostForm, UrlNormalizationError, normalize_url
from veo.db.models.identity import Site
from veo.organizations.fields import (
    STRICT,
    DisplayName,
    JsonSettings,
    forbid_nulls,
    require_any_field,
)

#: ``Site.origin`` is ``VARCHAR(255)``.
MAX_ORIGIN_LENGTH = 255

ALLOWED_SCHEMES = frozenset({"http", "https"})

_MALFORMED_KO = "origin 형식이 올바르지 않습니다."
#: Never echo the offending input back. It is attacker-controlled and lands in logs.
_REJECTION_KO: dict[str, str] = {
    "MALFORMED_URL": _MALFORMED_KO,
    "ILLEGAL_CHARACTER": "origin에 공백이나 제어문자를 넣을 수 없습니다.",
    "ILLEGAL_HOST": "origin의 호스트가 올바르지 않습니다.",
    "ILLEGAL_ESCAPE": _MALFORMED_KO,
    "INVALID_PORT": "origin의 포트 번호가 올바르지 않습니다.",
    "CREDENTIALS_IN_URL": "origin에 아이디·비밀번호를 포함할 수 없습니다.",
}


def normalize_origin(value: str) -> str:
    """Reduce ``value`` to a canonical bare origin, or raise ``ValueError``.

    ``https://Example.COM:443/`` and ``https://example.com`` are the same origin and both
    end up as ``https://example.com``. A default port is dropped; a non-default one is
    kept, because ``https://example.com:8443`` is a different origin.
    """
    raw = value.strip()
    if not raw:
        raise ValueError("origin을 입력해야 합니다.")
    if "#" in raw:
        # urlsplit discards the fragment, so accepting this would store something the
        # caller did not ask for.
        raise ValueError("origin에는 #프래그먼트를 포함할 수 없습니다.")

    try:
        parsed = normalize_url(raw)
    except UrlNormalizationError as exc:
        raise ValueError(_REJECTION_KO.get(exc.code, _MALFORMED_KO)) from exc

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError("origin은 http 또는 https여야 합니다.")
    if parsed.host_form is HostForm.EMPTY:
        raise ValueError("origin에 호스트가 없습니다.")
    if parsed.host_form is HostForm.OBFUSCATED_IP:
        raise ValueError("origin의 호스트가 올바르지 않습니다.")
    if parsed.path not in ("", "/"):
        raise ValueError("origin에는 경로를 포함할 수 없습니다. 스킴과 호스트만 입력하세요.")
    if parsed.query:
        raise ValueError("origin에는 쿼리 문자열을 포함할 수 없습니다.")
    if parsed.explicit_port is not None and not 1 <= parsed.explicit_port <= 65535:
        raise ValueError("origin의 포트 번호가 올바르지 않습니다.")

    authority = parsed.host_for_url
    if parsed.explicit_port is not None and parsed.explicit_port != parsed.default_port:
        authority = f"{authority}:{parsed.explicit_port}"

    origin = f"{parsed.scheme}://{authority}"
    if len(origin) > MAX_ORIGIN_LENGTH:
        raise ValueError(f"origin은 {MAX_ORIGIN_LENGTH}자를 넘을 수 없습니다.")
    return origin


class SitePayload(BaseModel):
    model_config = STRICT

    id: uuid.UUID
    project_id: uuid.UUID
    origin: str = Field(description="스킴과 호스트만 담긴 정규화된 origin입니다.")
    display_name: str
    is_primary: bool = Field(description="프로젝트를 대표하는 사이트는 하나뿐입니다.")
    crawl_settings: JsonSettings
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, site: Site) -> SitePayload:
        return cls(
            id=site.id,
            project_id=site.project_id,
            origin=site.origin,
            display_name=site.display_name,
            is_primary=site.is_primary,
            crawl_settings=dict(site.crawl_settings or {}),
            created_at=site.created_at,
            updated_at=site.updated_at,
        )


class SiteCreateRequest(BaseModel):
    """새 사이트 등록 요청. `project_id`는 같은 조직의 프로젝트여야 합니다."""

    model_config = STRICT

    project_id: uuid.UUID
    origin: str = Field(
        max_length=MAX_ORIGIN_LENGTH,
        description="예: https://example.com — 경로·쿼리·인증정보는 넣을 수 없습니다.",
    )
    display_name: DisplayName
    is_primary: bool = False
    crawl_settings: JsonSettings = Field(default_factory=dict)

    @field_validator("origin")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return normalize_origin(value)


class SiteUpdateRequest(BaseModel):
    """사이트 부분 수정 요청.

    `project_id`는 바꿀 수 없습니다. 사이트를 다른 프로젝트로 옮기면 이미 쌓인 진단 이력이
    엉뚱한 프로젝트에 매달리게 됩니다. 새 프로젝트에 새 사이트를 등록하세요.
    """

    model_config = STRICT

    origin: str | None = Field(default=None, max_length=MAX_ORIGIN_LENGTH)
    display_name: DisplayName | None = None
    is_primary: bool | None = None
    crawl_settings: JsonSettings | None = None

    @field_validator("origin")
    @classmethod
    def _normalize(cls, value: str | None) -> str | None:
        return None if value is None else normalize_origin(value)

    @model_validator(mode="before")
    @classmethod
    def _reject_null_required(cls, data: Any) -> Any:
        return forbid_nulls(data, "origin", "display_name", "is_primary", "crawl_settings")

    @model_validator(mode="after")
    def _reject_empty_body(self) -> SiteUpdateRequest:
        require_any_field(self)
        return self

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)
