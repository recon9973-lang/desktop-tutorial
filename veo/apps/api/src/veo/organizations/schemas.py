"""Response models for ``/organizations``.

Read-only in Phase 1, so there is no request model here at all.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from veo.db.models.identity import Organization
from veo.organizations.fields import STRICT, JsonSettings


class OrganizationPayload(BaseModel):
    """The organization the caller authenticated into."""

    model_config = STRICT

    id: uuid.UUID
    slug: str = Field(description="조직 식별자입니다. 조직 전체에서 고유합니다.")
    name: str
    is_active: bool = Field(description="비활성 조직은 신규 작업을 시작할 수 없습니다.")
    settings: JsonSettings = Field(description="조직 단위 설정입니다. 자격증명은 담기지 않습니다.")
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, organization: Organization) -> OrganizationPayload:
        return cls(
            id=organization.id,
            slug=organization.slug,
            name=organization.name,
            is_active=organization.is_active,
            settings=dict(organization.settings or {}),
            created_at=organization.created_at,
            updated_at=organization.updated_at,
        )
