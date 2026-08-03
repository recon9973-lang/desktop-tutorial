"""``/users`` — the people in one organization, and how they get a password.

Three groups of routes, with deliberately different protection:

* **Member management** requires ``user:manage``, which only ``SUPER_ADMIN`` holds.
* **Accepting an invitation** requires no session at all. It cannot: the whole point is
  that the account has no password yet. The token is the authority, which is why it is
  32 random bytes, stored only as a hash, single-use and expiring.
* **Changing your own password** requires a session *and* the current password. A session
  alone would mean an unlocked laptop is enough to take an account permanently.

A member of another organization answers 404 on every verb, matching the rest of VEO:
403 would confirm the person exists, which is enough to enumerate a competitor's staff
list one address at a time.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.auth.audit import AuthAuditAction, record_auth_event
from veo.auth.hashing import identifier_hash
from veo.auth.passwords import hash_password, verify_password
from veo.auth.sessions import RevocationReason, revoke_all_for_user
from veo.authz import Permission, Principal
from veo.authz.deps import get_principal
from veo.contracts.enums import ErrorCode
from veo.contracts.envelope import ApiResponse
from veo.core.settings import ConsoleBaseUrlNotSet, get_settings
from veo.db.models.identity import User
from veo.db.session import get_db
from veo.organizations.http import api_error, guard, not_found
from veo.users import invitations, service
from veo.users.schemas import (
    AcceptInvitationRequest,
    ChangePasswordRequest,
    InvitationPayload,
    InvitedMemberPayload,
    MemberPayload,
    MemberRoleUpdateRequest,
    MemberStatusUpdateRequest,
    NewMemberRequest,
)

router = APIRouter(tags=["users"])

DbSession = Annotated[Session, Depends(get_db)]
Reader = Annotated[Principal, Depends(guard(Permission.USER_READ))]
Manager = Annotated[Principal, Depends(guard(Permission.USER_MANAGE))]
SignedIn = Annotated[Principal, Depends(get_principal)]

MEMBER_NOT_FOUND_KO = "구성원을 찾을 수 없습니다."


def _refused(message_ko: str) -> Exception:
    return api_error(status.HTTP_409_CONFLICT, ErrorCode.CONFLICT, message_ko)


def _invitation_base_url() -> str:
    """The origin an invitation link points at, or a refusal an admin can act on.

    A misconfigured server is not the administrator's mistake, but it is the
    administrator who is standing in front of the screen — so the message names the
    variable to set instead of saying "처리하지 못했습니다".
    """
    try:
        return get_settings().invitation_base_url()
    except ConsoleBaseUrlNotSet as exc:
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE, ErrorCode.INTERNAL_ERROR, str(exc)
        ) from exc


def _source_ip_hash(request: Request) -> str | None:
    """Hashed before it is stored. A raw address is personal data in a log."""
    if request.client is None:
        return None
    return identifier_hash(request.client.host)


# --------------------------------------------------------------------------- #
# Member management — SUPER_ADMIN only
# --------------------------------------------------------------------------- #


@router.get(
    "/users",
    response_model=ApiResponse[list[MemberPayload]],
    summary="구성원 목록",
    description=(
        "로그인한 조직의 구성원만 반환합니다. 비밀번호는 어떤 형태로도 포함되지 않으며, "
        "초대를 아직 수락하지 않은 구성원은 `has_password=false` 로 표시됩니다."
    ),
)
def list_members(
    session: DbSession,
    principal: Reader,
    request_id: RequestId,
    include_deactivated: Annotated[
        bool, Query(description="비활성화된 구성원도 함께 조회합니다.")
    ] = False,
) -> ApiResponse[list[MemberPayload]]:
    members = service.list_members(
        session, principal, include_deactivated=include_deactivated
    )
    return ok([MemberPayload.of(member) for member in members], request_id)


@router.post(
    "/users",
    response_model=ApiResponse[InvitedMemberPayload],
    status_code=status.HTTP_201_CREATED,
    summary="구성원 추가 (초대 링크 발급)",
    description=(
        "계정을 만들고 초대 링크를 발급합니다. **관리자는 비밀번호를 정하지 않습니다** — "
        "본인이 링크에서 직접 설정합니다. 계정은 초대를 수락하기 전까지 비활성 상태이며 "
        "로그인할 수 없습니다.\n\n"
        "초대 링크는 **이 응답에서만** 확인할 수 있고 다시 조회할 수 없습니다. VEO 는 메일을 "
        "보내지 않으므로 관리자가 직접 전달해야 합니다."
    ),
)
def add_member(
    payload: NewMemberRequest,
    session: DbSession,
    principal: Manager,
    request_id: RequestId,
    request: Request,
) -> ApiResponse[InvitedMemberPayload]:
    # 주소부터 확인한다 — 계정을 만들고 토큰을 태운 다음 거절하면, 그 초대는 1회용이라
    # 그대로 버려지고 관리자는 이유도 모른 채 재발송을 눌러야 한다.
    base_url = _invitation_base_url()

    try:
        member = service.add_member(
            session,
            principal,
            email=str(payload.email),
            display_name=payload.display_name,
            role=payload.role,
        )
    except service.UserServiceError as exc:
        raise _refused(str(exc)) from exc

    issued = invitations.issue_invitation(
        session,
        user=member.user,
        organization_id=principal.organization_id,
        invited_by=principal.user_id,
    )
    record_auth_event(
        session,
        action=AuthAuditAction.MEMBER_INVITED,
        organization_id=principal.organization_id,
        actor_user_id=principal.user_id,
        target_type="user",
        target_id=str(member.user.id),
        request_id=request_id,
        source_ip_hash=_source_ip_hash(request),
        detail={"role": payload.role.value},
    )

    return ok(
        InvitedMemberPayload(
            member=MemberPayload.of(member),
            invitation=InvitationPayload(
                invite_url=issued.link(base_url),
                expires_at=issued.expires_at,
            ),
        ),
        request_id,
    )


@router.post(
    "/users/{user_id}/invitations",
    response_model=ApiResponse[InvitationPayload],
    summary="초대 링크 재발급",
    description=(
        "링크를 잃어버렸거나 만료된 경우, 또는 비밀번호를 잊은 구성원에게 다시 설정하게 할 때 "
        "사용합니다. 이전 링크는 즉시 무효가 됩니다.\n\n"
        "**주의:** 재발급은 해당 계정의 비밀번호를 다시 정할 권한을 넘기는 것과 같습니다. "
        "관리자가 다른 사람의 계정을 넘겨받는 경로이기도 하므로 감사 로그에 남습니다."
    ),
)
def reissue_invitation(
    user_id: uuid.UUID,
    session: DbSession,
    principal: Manager,
    request_id: RequestId,
    request: Request,
) -> ApiResponse[InvitationPayload]:
    base_url = _invitation_base_url()

    member = service.load_member(session, principal, user_id)
    if member is None:
        raise not_found(MEMBER_NOT_FOUND_KO)

    issued = invitations.issue_invitation(
        session,
        user=member.user,
        organization_id=principal.organization_id,
        invited_by=principal.user_id,
    )
    record_auth_event(
        session,
        action=AuthAuditAction.MEMBER_INVITE_REISSUED,
        organization_id=principal.organization_id,
        actor_user_id=principal.user_id,
        target_type="user",
        target_id=str(user_id),
        request_id=request_id,
        source_ip_hash=_source_ip_hash(request),
    )
    return ok(
        InvitationPayload(
            invite_url=issued.link(base_url),
            expires_at=issued.expires_at,
        ),
        request_id,
    )


@router.patch(
    "/users/{user_id}/role",
    response_model=ApiResponse[MemberPayload],
    summary="구성원 역할 변경",
    description="마지막 관리자의 역할은 바꿀 수 없습니다 — 조직이 스스로를 잠글 수 없어야 합니다.",
)
def change_role(
    user_id: uuid.UUID,
    payload: MemberRoleUpdateRequest,
    session: DbSession,
    principal: Manager,
    request_id: RequestId,
    request: Request,
) -> ApiResponse[MemberPayload]:
    if service.load_member(session, principal, user_id) is None:
        raise not_found(MEMBER_NOT_FOUND_KO)
    try:
        member = service.change_role(session, principal, user_id=user_id, role=payload.role)
    except service.UserServiceError as exc:
        raise _refused(str(exc)) from exc

    record_auth_event(
        session,
        action=AuthAuditAction.MEMBER_ROLE_CHANGED,
        organization_id=principal.organization_id,
        actor_user_id=principal.user_id,
        target_type="user",
        target_id=str(user_id),
        request_id=request_id,
        source_ip_hash=_source_ip_hash(request),
        detail={"role": payload.role.value},
    )
    return ok(MemberPayload.of(member), request_id)


@router.patch(
    "/users/{user_id}/status",
    response_model=ApiResponse[MemberPayload],
    summary="구성원 활성/비활성",
    description=(
        "퇴사 처리는 삭제가 아니라 비활성화입니다. 행을 지우면 감사 기록이 사라진 사용자를 "
        "가리키게 되고, 그것은 기록이 아닙니다.\n\n"
        "비활성화하면 해당 구성원의 모든 세션이 즉시 끊깁니다."
    ),
)
def change_status(
    user_id: uuid.UUID,
    payload: MemberStatusUpdateRequest,
    session: DbSession,
    principal: Manager,
    request_id: RequestId,
    request: Request,
) -> ApiResponse[MemberPayload]:
    if service.load_member(session, principal, user_id) is None:
        raise not_found(MEMBER_NOT_FOUND_KO)
    try:
        member = service.set_active(
            session, principal, user_id=user_id, is_active=payload.is_active
        )
    except service.UserServiceError as exc:
        raise _refused(str(exc)) from exc

    if not payload.is_active:
        # Deactivation that leaves a live session is not deactivation. Roles are read
        # per request, so permissions would already be gone — but the session itself
        # must go too, or the person keeps a working token until it expires.
        revoke_all_for_user(
            session,
            organization_id=principal.organization_id,
            user_id=user_id,
            reason=RevocationReason.ADMIN_REVOKED,
        )
        invitations.revoke_invitations_for(session, user_id=user_id)

    record_auth_event(
        session,
        action=AuthAuditAction.MEMBER_STATUS_CHANGED,
        organization_id=principal.organization_id,
        actor_user_id=principal.user_id,
        target_type="user",
        target_id=str(user_id),
        request_id=request_id,
        source_ip_hash=_source_ip_hash(request),
        detail={"is_active": payload.is_active},
    )
    return ok(MemberPayload.of(member), request_id)


# --------------------------------------------------------------------------- #
# Accepting an invitation — no session, by necessity
# --------------------------------------------------------------------------- #


@router.post(
    "/invitations/{token}/accept",
    response_model=ApiResponse[MemberPayload],
    summary="초대 수락 및 비밀번호 설정 (로그인 불필요)",
    description=(
        "초대 링크로 처음 비밀번호를 설정합니다. 로그인은 필요하지 않습니다 — 아직 비밀번호가 "
        "없기 때문입니다. 토큰은 한 번만 쓸 수 있고 만료됩니다.\n\n"
        "없는 토큰·만료된 토큰·이미 사용한 토큰은 모두 같은 응답을 돌려줍니다. 어떤 토큰이 "
        "실제로 존재했는지 확인해 주는 창구가 되지 않기 위해서입니다."
    ),
)
def accept_invitation(
    token: str,
    payload: AcceptInvitationRequest,
    session: DbSession,
    request_id: RequestId,
    request: Request,
) -> ApiResponse[MemberPayload]:
    try:
        accepted = invitations.accept_invitation(
            session, token=token, password_hash=hash_password(payload.password)
        )
    except invitations.InvitationInvalid as exc:
        raise api_error(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND, str(exc)) from exc

    person = session.get(User, accepted.user_id)
    if person is None:  # pragma: no cover - the invitation just loaded it
        raise not_found(MEMBER_NOT_FOUND_KO)

    record_auth_event(
        session,
        action=AuthAuditAction.MEMBER_INVITE_ACCEPTED,
        organization_id=accepted.organization_id,
        actor_user_id=accepted.user_id,
        target_type="user",
        target_id=str(accepted.user_id),
        request_id=request_id,
        source_ip_hash=_source_ip_hash(request),
    )
    return ok(
        MemberPayload(
            id=person.id,
            email=person.email,
            display_name=person.display_name,
            roles=[],
            status=service.status_of(person),
            is_active=person.is_active,
            has_password=True,
            last_login_at=person.last_login_at,
        ),
        request_id,
    )


# --------------------------------------------------------------------------- #
# Changing your own password
# --------------------------------------------------------------------------- #


@router.post(
    "/auth/password",
    response_model=ApiResponse[MemberPayload],
    summary="내 비밀번호 변경",
    description=(
        "현재 비밀번호를 함께 요구합니다. 세션만으로 바꿀 수 있다면 잠기지 않은 화면 하나가 "
        "계정을 영구히 빼앗기에 충분해집니다.\n\n"
        "변경하면 **다른 모든 기기의 세션이 끊깁니다.** 비밀번호를 바꾸는 이유는 대개 누군가 "
        "알아냈다고 의심할 때인데, 그 사람의 세션이 남아 있으면 바꾼 의미가 없습니다."
    ),
)
def change_own_password(
    payload: ChangePasswordRequest,
    session: DbSession,
    principal: SignedIn,
    request_id: RequestId,
    request: Request,
) -> ApiResponse[MemberPayload]:
    person = session.get(User, principal.user_id)
    if person is None:  # pragma: no cover - the principal came from this row
        raise not_found(MEMBER_NOT_FOUND_KO)

    if not verify_password(person.password_hash, payload.current_password):
        raise api_error(
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.UNAUTHENTICATED,
            "현재 비밀번호가 일치하지 않습니다.",
        )
    if payload.new_password == payload.current_password:
        raise _refused("새 비밀번호가 기존 비밀번호와 같습니다.")

    person.password_hash = hash_password(payload.new_password)
    session.flush()

    # Every other device, but not this one. See ``revoke_all_for_user``.
    #
    # ``Principal.session_id`` is a string because a principal can come from something
    # other than a database session row. A value that is not a UUID therefore matches no
    # row, and the effect is that *every* session is revoked — which is the safe way for
    # this to fail. Written explicitly so nobody later "fixes" it into a bare cast.
    try:
        current_session_id: uuid.UUID | None = uuid.UUID(principal.session_id)
    except (ValueError, AttributeError, TypeError):
        current_session_id = None

    revoke_all_for_user(
        session,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        reason=RevocationReason.PASSWORD_CHANGED,
        except_session_id=current_session_id,
    )
    record_auth_event(
        session,
        action=AuthAuditAction.PASSWORD_CHANGED,
        organization_id=principal.organization_id,
        actor_user_id=principal.user_id,
        target_type="user",
        target_id=str(principal.user_id),
        request_id=request_id,
        source_ip_hash=_source_ip_hash(request),
    )

    member = service.load_member(session, principal, principal.user_id)
    roles = list(member.roles) if member else []
    return ok(
        MemberPayload(
            id=person.id,
            email=person.email,
            display_name=person.display_name,
            roles=roles,
            status=service.status_of(person),
            is_active=person.is_active,
            has_password=True,
            last_login_at=person.last_login_at,
        ),
        request_id,
    )
