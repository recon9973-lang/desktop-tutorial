"""Request and response shapes for member management.

One rule shows up repeatedly below: nothing here ever carries a password, and the
invitation token appears in exactly one response — the one that creates it.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from veo.auth.hashing import EMAIL_SHAPE_PATTERN
from veo.auth.passwords import MAX_PASSWORD_LENGTH
from veo.contracts.enums import Role
from veo.users.service import MemberRecord, MemberStatus

_STRICT = ConfigDict(extra="forbid")

#: Same floor as the bootstrap owner. A console account can reach every customer's
#: report, so the weakest password it accepts is a real decision, not a default.
MIN_MEMBER_PASSWORD_LENGTH = 12

__all__ = [
    "MIN_MEMBER_PASSWORD_LENGTH",
    "AcceptInvitationRequest",
    "ChangePasswordRequest",
    "InvitationPayload",
    "InvitedMemberPayload",
    "MemberPayload",
    "MemberRoleUpdateRequest",
    "MemberStatusUpdateRequest",
    "NewMemberRequest",
]


class MemberPayload(BaseModel):
    """One colleague. No password field exists, in either direction."""

    model_config = _STRICT

    id: uuid.UUID
    email: str
    display_name: str
    roles: list[str]
    status: MemberStatus = Field(
        description=(
            "PENDING = 초대했으나 아직 비밀번호를 설정하지 않음, ACTIVE = 사용 중, "
            "DEACTIVATED = 관리자가 비활성화함."
        )
    )
    is_active: bool
    has_password: bool = Field(
        description="비밀번호를 설정했는지 여부입니다. 초대를 아직 수락하지 않았으면 false 입니다."
    )
    last_login_at: datetime | None = None

    @classmethod
    def of(cls, member: MemberRecord) -> MemberPayload:
        return cls(
            id=member.user.id,
            email=member.user.email,
            display_name=member.user.display_name,
            roles=list(member.roles),
            status=member.status,
            is_active=member.user.is_active,
            has_password=member.user.password_hash is not None,
            last_login_at=member.user.last_login_at,
        )


class InvitationPayload(BaseModel):
    """The one-time link. Returned once and never retrievable again."""

    model_config = _STRICT

    invite_url: str = Field(
        description=(
            "초대 링크입니다. 이 응답에서만 확인할 수 있으며 다시 조회할 수 없습니다. "
            "VEO 는 메일을 보내지 않으므로, 관리자가 직접 전달해야 합니다."
        )
    )
    expires_at: datetime


class InvitedMemberPayload(BaseModel):
    """A newly created colleague, together with the link to hand them."""

    model_config = _STRICT

    member: MemberPayload
    invitation: InvitationPayload


class NewMemberRequest(BaseModel):
    model_config = _STRICT

    email: str = Field(pattern=EMAIL_SHAPE_PATTERN, max_length=320)
    display_name: str = Field(min_length=1, max_length=200)
    role: Role


class MemberRoleUpdateRequest(BaseModel):
    model_config = _STRICT

    role: Role


class MemberStatusUpdateRequest(BaseModel):
    model_config = _STRICT

    is_active: bool


class AcceptInvitationRequest(BaseModel):
    """Setting a password for the first time. Requires no session — the token is the proof."""

    model_config = _STRICT

    password: str = Field(
        min_length=MIN_MEMBER_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH
    )


class ChangePasswordRequest(BaseModel):
    """Changing it later. Requires the current one even though a session is present.

    A stolen laptop with an open console should not be enough to take the account
    permanently; asking for the current password is what makes the theft recoverable.
    """

    model_config = _STRICT

    current_password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)
    new_password: str = Field(
        min_length=MIN_MEMBER_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH
    )
