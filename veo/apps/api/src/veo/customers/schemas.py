"""Request and response models for ``/customers``."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from veo.db.models.identity import Customer
from veo.organizations.fields import (
    STRICT,
    DisplayName,
    FreeNote,
    ShortLabel,
    forbid_nulls,
    require_any_field,
)


class CustomerPayload(BaseModel):
    model_config = STRICT

    id: uuid.UUID
    name: str
    industry: str | None
    contact_note: str | None = Field(
        description="담당자 메모입니다. 감사 로그에는 이 값이 기록되지 않습니다."
    )
    is_active: bool = Field(description="false면 삭제 처리된 고객사입니다. 이력은 남습니다.")
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, customer: Customer) -> CustomerPayload:
        return cls(
            id=customer.id,
            name=customer.name,
            industry=customer.industry,
            contact_note=customer.contact_note,
            is_active=customer.is_active,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
        )


class CustomerCreateRequest(BaseModel):
    """새 고객사 등록 요청.

    조직은 인증된 세션에서 결정되므로 본문에 담지 않습니다. 본문으로 조직을 받으면
    그 값이 곧 다른 조직에 행을 심는 통로가 됩니다.
    """

    model_config = STRICT

    name: DisplayName
    industry: ShortLabel | None = None
    contact_note: FreeNote | None = None


class CustomerUpdateRequest(BaseModel):
    """고객사 부분 수정 요청. 보낸 항목만 바뀝니다."""

    model_config = STRICT

    name: DisplayName | None = None
    industry: ShortLabel | None = None
    contact_note: FreeNote | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_null_name(cls, data: Any) -> Any:
        return forbid_nulls(data, "name")

    @model_validator(mode="after")
    def _reject_empty_body(self) -> CustomerUpdateRequest:
        require_any_field(self)
        return self

    def changes(self) -> dict[str, Any]:
        """Only the fields the caller actually sent, ``null`` included where allowed."""
        return self.model_dump(exclude_unset=True)
