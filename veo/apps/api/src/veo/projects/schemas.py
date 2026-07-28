"""Request and response models for ``/projects``."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from veo.db.models.identity import Project
from veo.organizations.fields import (
    STRICT,
    DisplayName,
    JsonSettings,
    Locale,
    Slug,
    SpecVersion,
    forbid_nulls,
    require_any_field,
)


class ProjectPayload(BaseModel):
    model_config = STRICT

    id: uuid.UUID
    customer_id: uuid.UUID | None
    slug: str = Field(description="조직 안에서 고유한 프로젝트 식별자입니다.")
    name: str
    locale: str = Field(description="진단 기준이 되는 언어·지역 태그입니다. 예: ko-KR")
    default_seo_spec_version: str | None = Field(
        description="비워 두면 서버 기본 SEO 명세 버전이 적용됩니다."
    )
    default_geo_spec_version: str | None = Field(
        description="비워 두면 서버 기본 GEO 명세 버전이 적용됩니다."
    )
    settings: JsonSettings
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, project: Project) -> ProjectPayload:
        return cls(
            id=project.id,
            customer_id=project.customer_id,
            slug=project.slug,
            name=project.name,
            locale=project.locale,
            default_seo_spec_version=project.default_seo_spec_version,
            default_geo_spec_version=project.default_geo_spec_version,
            settings=dict(project.settings or {}),
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


class ProjectCreateRequest(BaseModel):
    """새 프로젝트 생성 요청.

    `customer_id`는 같은 조직의 고객사여야 합니다. 다른 조직의 ID를 넣으면 404를
    반환합니다 — 외래키 오류를 그대로 노출하면 그 ID가 실재한다는 사실이 드러납니다.
    """

    model_config = STRICT

    slug: Slug
    name: DisplayName
    customer_id: uuid.UUID | None = None
    locale: Locale = "ko-KR"
    default_seo_spec_version: SpecVersion | None = None
    default_geo_spec_version: SpecVersion | None = None
    settings: JsonSettings = Field(default_factory=dict)


class ProjectUpdateRequest(BaseModel):
    """프로젝트 부분 수정 요청. 보낸 항목만 바뀝니다."""

    model_config = STRICT

    slug: Slug | None = None
    name: DisplayName | None = None
    customer_id: uuid.UUID | None = None
    locale: Locale | None = None
    default_seo_spec_version: SpecVersion | None = None
    default_geo_spec_version: SpecVersion | None = None
    settings: JsonSettings | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_null_required(cls, data: Any) -> Any:
        return forbid_nulls(data, "slug", "name", "locale", "settings")

    @model_validator(mode="after")
    def _reject_empty_body(self) -> ProjectUpdateRequest:
        require_any_field(self)
        return self

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)
