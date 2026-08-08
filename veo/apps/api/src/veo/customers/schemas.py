"""Request and response models for ``/customers``."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from veo.db.models.identity import Customer
from veo.organizations.fields import (
    STRICT,
    Address,
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
    address: str | None = Field(
        default=None,
        description=(
            "소재지입니다. 상호는 식별자가 아니라서 — 서울치과는 수십 곳입니다 — "
            "이름만으로는 목록에서 어느 곳인지 가려지지 않습니다. 측정에 쓰는 값이 "
            "아닙니다: AI 답변과 대조하는 소재지 표현은 브랜드 식별의 address_terms "
            "입니다."
        ),
    )
    contact_note: str | None = Field(
        description="담당자 메모입니다. 감사 로그에는 이 값이 기록되지 않습니다."
    )
    is_active: bool = Field(description="false면 삭제 처리된 고객사입니다. 이력은 남습니다.")
    is_registered: bool = Field(
        description=(
            "사람이 거래처로 등록했으면 true입니다. 주소만 넣고 한 번 재 본 자리는 "
            "false로 만들어지며, 거래처 목록에 나오지 않습니다. is_active와는 다른 "
            "축입니다 — 저것은 지웠는가, 이것은 우리 거래처인가입니다."
        )
    )
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, customer: Customer) -> CustomerPayload:
        return cls(
            id=customer.id,
            name=customer.name,
            industry=customer.industry,
            address=customer.address,
            contact_note=customer.contact_note,
            is_active=customer.is_active,
            is_registered=customer.is_registered,
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
    address: Address | None = None
    contact_note: FreeNote | None = None
    is_registered: bool = Field(
        default=True,
        description=(
            "거래처로 등록하는 것이면 true(기본값)입니다. 주소만 넣고 재 보려고 자리를 "
            "만드는 경우에만 false를 보냅니다."
        ),
    )


class CustomerUpdateRequest(BaseModel):
    """고객사 부분 수정 요청. 보낸 항목만 바뀝니다."""

    model_config = STRICT

    name: DisplayName | None = None
    industry: ShortLabel | None = None
    address: Address | None = None
    contact_note: FreeNote | None = None
    #: 재 보기만 하던 자리를 거래처로 올리는 길. 되돌리는 것도 같은 자리에서 한다.
    is_registered: bool | None = None

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
