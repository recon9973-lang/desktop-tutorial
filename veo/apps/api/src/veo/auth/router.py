"""The four sign-in endpoints.

Not mounted here. The integrator includes this router; :func:`veo.auth.resolver.install_auth`
teaches the application how to read the tokens it hands out.

Two properties the handlers below are built around.

*One answer for every failure.* Wrong password, unknown address, deactivated account,
organization you are not a member of — all of them return the same 401 with the same
Korean sentence and the same body shape, and all of them cost about the same time.
Anything else turns the login endpoint into a service for discovering who has an account.

*/auth/me returns permissions, not just roles.* The front end has to decide what to render
before it knows what a request will be allowed to do. If it re-implemented the role matrix
to make that decision, the navigation and the API would drift apart, and the drift would
show up as buttons that 403. The resolved list ships from the server that enforces it.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.auth.audit import AuthAuditAction, LoginFailureCode, record_auth_event
from veo.auth.hashing import normalize_email, optional_identifier_hash
from veo.auth.passwords import (
    MAX_PASSWORD_LENGTH,
    hash_password,
    needs_rehash,
    verify_password,
)
from veo.auth.sessions import (
    IssuedSession,
    RevocationReason,
    create_session,
    is_usable,
    load_active_session,
    load_by_refresh_token,
    revoke_family,
    revoke_session,
    rotate_session,
)
from veo.auth.throttle import (
    AccountLockedError,
    assert_not_locked,
    clear_failures,
    register_failure,
)
from veo.auth.tokens import GENERIC_AUTH_MESSAGE_KO, encode_access_token
from veo.authz import AuthenticationError, CurrentPrincipal, Principal
from veo.contracts.enums import ErrorCode, Role
from veo.contracts.envelope import ApiError, ApiResponse
from veo.core.settings import get_settings
from veo.db.models.identity import Organization, RoleAssignment, User
from veo.db.models.security import UserSession
from veo.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]

_STRICT = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- #
# Payloads
# --------------------------------------------------------------------------- #


#: Structural check only. Deliverability is proven by the account existing, not by a
#: regular expression, and a stricter pattern would reject addresses that are legal.
EMAIL_PATTERN = r"^[^\s@]{1,64}@[^\s@]{1,255}\.[^\s@.]{2,63}$"


class LoginRequest(BaseModel):
    model_config = _STRICT

    email: str = Field(
        min_length=3,
        max_length=320,
        pattern=EMAIL_PATTERN,
        description="가입한 이메일 주소. 대소문자를 구분하지 않습니다.",
    )
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)
    organization_slug: str | None = Field(
        default=None,
        max_length=64,
        description=(
            "여러 조직에 소속된 계정만 사용합니다. 로그인 시 조직 하나가 확정되며, "
            "이후에는 헤더나 토큰으로 조직을 바꿀 수 없습니다."
        ),
    )


class RefreshRequest(BaseModel):
    model_config = _STRICT

    refresh_token: str = Field(min_length=1, max_length=512)


class UserPayload(BaseModel):
    model_config = _STRICT

    id: str
    email: str
    display_name: str


class OrganizationPayload(BaseModel):
    model_config = _STRICT

    id: str
    slug: str
    name: str


class SessionPayload(BaseModel):
    """What a successful sign-in or refresh returns.

    ``refresh_token`` appears exactly once, here, on its way to the client. VEO stores
    only its SHA-256, so this response is the only place the value ever exists outside the
    caller.
    """

    model_config = _STRICT

    access_token: str
    token_type: Literal["Bearer"] = "Bearer"  # noqa: S105 - the scheme name, not a credential
    expires_in: int = Field(description="액세스 토큰 유효 시간(초).")
    refresh_token: str
    session_id: str
    user: UserPayload
    organization: OrganizationPayload
    roles: list[str]
    permissions: list[str]


class MePayload(BaseModel):
    """The caller, the organization they signed into, and what they may do."""

    model_config = _STRICT

    user: UserPayload
    organization: OrganizationPayload
    roles: list[str]
    permissions: list[str] = Field(
        description=(
            "역할에서 이미 계산된 권한 목록. "
            "프런트엔드가 역할 표를 다시 구현하지 않도록 제공합니다."
        )
    )
    session_id: str
    session_expires_at: datetime


class LogoutPayload(BaseModel):
    model_config = _STRICT

    revoked: bool


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #


@router.post(
    "/login",
    response_model=ApiResponse[SessionPayload],
    summary="로그인 — 액세스 토큰과 갱신 토큰 발급",
    description=(
        "실패 사유는 응답에 드러나지 않습니다. 존재하지 않는 계정과 비밀번호 불일치는 "
        "형태도 소요 시간도 동일합니다."
    ),
    responses={
        401: {"description": "인증 실패 (사유는 구분되지 않습니다)"},
        409: {"description": "여러 조직 소속 — organization_slug 로 조직을 지정해야 합니다"},
        429: {"description": "로그인 시도 제한"},
    },
)
def login(
    payload: LoginRequest, request: Request, request_id: RequestId, db: DbSession
) -> ApiResponse[SessionPayload]:
    email = normalize_email(payload.email)
    ip_hash = optional_identifier_hash(_client_ip(request))
    user_agent_hash = optional_identifier_hash(request.headers.get("user-agent"))
    now = datetime.now(UTC)

    try:
        assert_not_locked(db, email, now=now)
    except AccountLockedError as locked:
        record_auth_event(
            db,
            action=AuthAuditAction.LOGIN_LOCKED_OUT,
            request_id=request_id,
            source_ip_hash=ip_hash,
            detail={
                "outcome": LoginFailureCode.LOCKED_OUT.value,
                "retry_after_seconds": locked.retry_after_seconds,
            },
        )
        db.commit()
        raise

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    usable_hash = user.password_hash if user is not None and user.is_active else None

    # Always runs the hasher, including for an address with no account, so the response
    # time does not answer "does this address exist?".
    if not verify_password(usable_hash, payload.password):
        outcome = (
            LoginFailureCode.NO_SUCH_USER
            if user is None
            else (
                LoginFailureCode.USER_INACTIVE
                if not user.is_active
                else LoginFailureCode.PASSWORD_MISMATCH
            )
        )
        _reject(db, email, request_id, ip_hash, outcome, now)

    assert user is not None  # narrowed by the verify above: no hash, no success
    memberships = _memberships(db, user.id)

    if payload.organization_slug is not None:
        chosen = _pick_named(memberships, payload.organization_slug)
        if chosen is None:
            # Not a member, or the organization does not exist — indistinguishable on
            # purpose, so login cannot be used to probe for organizations.
            _reject(db, email, request_id, ip_hash, LoginFailureCode.NO_ORGANIZATION, now)
    elif not memberships:
        _reject(db, email, request_id, ip_hash, LoginFailureCode.NO_ORGANIZATION, now)
    elif len(memberships) > 1:
        # The password was correct, so this is not a failed attempt: clear the counter
        # and ask which organization, without listing them.
        clear_failures(db, email)
        record_auth_event(
            db,
            action=AuthAuditAction.LOGIN_FAILED,
            actor_user_id=user.id,
            request_id=request_id,
            source_ip_hash=ip_hash,
            detail={"outcome": LoginFailureCode.ORGANIZATION_AMBIGUOUS.value},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ApiError.of(
                ErrorCode.CONFLICT,
                "여러 조직에 소속된 계정입니다. organization_slug 로 조직을 지정해 주세요.",
            ).model_dump(mode="json"),
        )
    else:
        chosen = next(iter(memberships.values()))

    organization, roles = chosen.organization, chosen.roles

    # The password just proved itself, so this is the one moment VEO can upgrade a hash
    # made under weaker parameters.
    if user.password_hash and needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)

    clear_failures(db, email)
    user.last_login_at = now

    issued = create_session(
        db,
        user_id=user.id,
        organization_id=organization.id,
        now=now,
        user_agent_hash=user_agent_hash,
        ip_hash=ip_hash,
    )
    record_auth_event(
        db,
        action=AuthAuditAction.LOGIN_SUCCEEDED,
        organization_id=organization.id,
        actor_user_id=user.id,
        target_type="user_session",
        target_id=str(issued.session.id),
        request_id=request_id,
        source_ip_hash=ip_hash,
        detail={"roles": sorted(role.value for role in roles)},
    )
    db.commit()

    return ok(_session_payload(user, organization, roles, issued), request_id)


@router.post(
    "/refresh",
    response_model=ApiResponse[SessionPayload],
    summary="갱신 토큰 회전 — 새 액세스 토큰 발급",
    description=(
        "갱신 토큰은 1회용입니다. 이미 사용된 토큰이 다시 제출되면 해당 로그인 계보 전체를 "
        "즉시 폐기하고, 호출자에게는 일반적인 인증 실패만 반환합니다."
    ),
    responses={401: {"description": "인증 실패 (사유는 구분되지 않습니다)"}},
)
def refresh(
    payload: RefreshRequest, request: Request, request_id: RequestId, db: DbSession
) -> ApiResponse[SessionPayload]:
    ip_hash = optional_identifier_hash(_client_ip(request))
    user_agent_hash = optional_identifier_hash(request.headers.get("user-agent"))
    now = datetime.now(UTC)

    session_row = load_by_refresh_token(db, payload.refresh_token)
    if session_row is None:
        raise AuthenticationError(GENERIC_AUTH_MESSAGE_KO)

    if session_row.revoked_reason == RevocationReason.ROTATED.value:
        # This token was already exchanged. Two parties hold it and VEO cannot tell which
        # one is the customer, so the whole family goes.
        burned = revoke_family(
            db,
            family_id=session_row.family_id,
            organization_id=session_row.organization_id,
            reason=RevocationReason.REUSE_DETECTED,
            now=now,
        )
        record_auth_event(
            db,
            action=AuthAuditAction.REFRESH_REUSE_DETECTED,
            organization_id=session_row.organization_id,
            actor_user_id=session_row.user_id,
            target_type="user_session",
            target_id=str(session_row.id),
            request_id=request_id,
            source_ip_hash=ip_hash,
            detail={"revoked_sessions": burned, "family_id": str(session_row.family_id)},
        )
        db.commit()
        raise AuthenticationError(GENERIC_AUTH_MESSAGE_KO)

    if not is_usable(session_row, now):
        raise AuthenticationError(GENERIC_AUTH_MESSAGE_KO)

    context = _account_context(db, session_row.user_id, session_row.organization_id)
    if context is None:
        # Access was withdrawn while the session was alive; retire it rather than let it
        # keep rotating into new tokens.
        revoke_session(db, session_row, RevocationReason.ADMIN_REVOKED, now=now)
        db.commit()
        raise AuthenticationError(GENERIC_AUTH_MESSAGE_KO)

    user, organization, roles = context
    issued = rotate_session(
        db,
        session_row,
        now=now,
        user_agent_hash=user_agent_hash,
        ip_hash=ip_hash,
    )
    record_auth_event(
        db,
        action=AuthAuditAction.TOKEN_REFRESHED,
        organization_id=organization.id,
        actor_user_id=user.id,
        target_type="user_session",
        target_id=str(issued.session.id),
        request_id=request_id,
        source_ip_hash=ip_hash,
        detail={"rotation_count": issued.session.rotation_count},
    )
    db.commit()

    return ok(_session_payload(user, organization, roles, issued), request_id)


@router.post(
    "/logout",
    response_model=ApiResponse[LogoutPayload],
    summary="로그아웃 — 현재 세션 폐기",
    description=(
        "현재 액세스 토큰이 가리키는 세션만 폐기합니다. "
        "같은 계정의 다른 조직 세션은 유지됩니다."
    ),
)
def logout(
    principal: CurrentPrincipal, request: Request, request_id: RequestId, db: DbSession
) -> ApiResponse[LogoutPayload]:
    ip_hash = optional_identifier_hash(_client_ip(request))
    session_row = load_active_session(
        db, uuid.UUID(principal.session_id), principal.organization_id
    )

    revoked = False
    if session_row is not None:
        revoked = revoke_session(db, session_row, RevocationReason.LOGOUT)

    record_auth_event(
        db,
        action=AuthAuditAction.LOGOUT,
        organization_id=principal.organization_id,
        actor_user_id=principal.user_id,
        target_type="user_session",
        target_id=principal.session_id,
        request_id=request_id,
        source_ip_hash=ip_hash,
    )
    db.commit()

    return ok(LogoutPayload(revoked=revoked), request_id)


@router.get(
    "/me",
    response_model=ApiResponse[MePayload],
    summary="현재 로그인 정보 — 사용자·조직·역할·권한",
    description=(
        "권한 목록은 서버가 역할 표에서 계산한 결과입니다. 프런트엔드는 이 목록만 보고 "
        "메뉴를 구성하면 되며, 역할 표를 다시 구현할 필요가 없습니다."
    ),
)
def me(principal: CurrentPrincipal, request_id: RequestId, db: DbSession) -> ApiResponse[MePayload]:
    context = _account_context(db, principal.user_id, principal.organization_id)
    if context is None:  # pragma: no cover - the resolver already refused this case
        raise AuthenticationError(GENERIC_AUTH_MESSAGE_KO)

    user, organization, roles = context
    session_row = db.get(UserSession, uuid.UUID(principal.session_id))
    if session_row is None:  # pragma: no cover - resolved from a live row moments ago
        raise AuthenticationError(GENERIC_AUTH_MESSAGE_KO)

    return ok(
        MePayload(
            user=_user_payload(user),
            organization=_organization_payload(organization),
            roles=sorted(role.value for role in roles),
            permissions=_permissions(roles),
            session_id=principal.session_id,
            session_expires_at=session_row.expires_at,
        ),
        request_id,
    )


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


class _Membership:
    """One organization the user belongs to, with the roles they hold there."""

    __slots__ = ("organization", "roles")

    def __init__(self, organization: Organization, roles: frozenset[Role]) -> None:
        self.organization = organization
        self.roles = roles


def _memberships(db: Session, user_id: uuid.UUID) -> dict[uuid.UUID, _Membership]:
    """Every active organization this user holds a recognised role in.

    Not tenant-scoped, and cannot be: choosing the organization is what sign-in does, so
    there is no organization to scope to yet. Nothing about the result reaches the caller
    unless the password already verified.
    """
    rows = db.execute(
        select(RoleAssignment, Organization)
        .join(Organization, Organization.id == RoleAssignment.organization_id)
        .where(RoleAssignment.user_id == user_id, Organization.is_active.is_(True))
    ).all()

    found: dict[uuid.UUID, _Membership] = {}
    for assignment, organization in rows:
        try:
            role = Role(assignment.role)
        except ValueError:
            continue
        existing = found.get(organization.id)
        roles = (existing.roles if existing else frozenset()) | {role}
        found[organization.id] = _Membership(organization=organization, roles=roles)
    return {key: value for key, value in found.items() if value.roles}


def _pick_named(
    memberships: dict[uuid.UUID, _Membership], slug: str
) -> _Membership | None:
    wanted = slug.strip().casefold()
    for membership in memberships.values():
        if membership.organization.slug.casefold() == wanted:
            return membership
    return None


def _account_context(
    db: Session, user_id: uuid.UUID, organization_id: uuid.UUID
) -> tuple[User, Organization, frozenset[Role]] | None:
    """Re-read the account exactly as the resolver does, so both agree on every request."""
    from veo.auth.resolver import load_roles

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    organization = db.get(Organization, organization_id)
    if organization is None or not organization.is_active:
        return None
    roles = load_roles(db, user_id, organization_id)
    if not roles:
        return None
    return user, organization, roles


def _reject(
    db: Session,
    email: str,
    request_id: str,
    ip_hash: str | None,
    outcome: LoginFailureCode,
    now: datetime,
) -> NoReturn:
    """Count the failure, record it, commit both, and return the one generic 401.

    The commit matters: the throttle counter and the audit row must survive the exception
    that follows, or an attacker could guess forever and leave no trace.
    """
    state = register_failure(db, email, now=now)
    record_auth_event(
        db,
        action=AuthAuditAction.LOGIN_FAILED,
        request_id=request_id,
        source_ip_hash=ip_hash,
        detail={"outcome": outcome.value, "failed_count": state.failed_count},
    )
    db.commit()
    raise AuthenticationError(GENERIC_AUTH_MESSAGE_KO)


def _permissions(roles: frozenset[Role]) -> list[str]:
    principal = Principal(
        user_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        roles=roles,
        session_id="",
    )
    return sorted(permission.value for permission in principal.permissions)


def _user_payload(user: User) -> UserPayload:
    return UserPayload(id=str(user.id), email=user.email, display_name=user.display_name)


def _organization_payload(organization: Organization) -> OrganizationPayload:
    return OrganizationPayload(
        id=str(organization.id), slug=organization.slug, name=organization.name
    )


def _session_payload(
    user: User,
    organization: Organization,
    roles: frozenset[Role],
    issued: IssuedSession,
) -> SessionPayload:
    return SessionPayload(
        access_token=encode_access_token(
            user_id=user.id,
            organization_id=organization.id,
            roles=roles,
            session_id=issued.session.id,
        ),
        expires_in=get_settings().access_token_ttl_seconds,
        refresh_token=issued.refresh_token,
        session_id=str(issued.session.id),
        user=_user_payload(user),
        organization=_organization_payload(organization),
        roles=sorted(role.value for role in roles),
        permissions=_permissions(roles),
    )


def _client_ip(request: Request) -> str | None:
    """The caller's address, for hashing only — it is never stored or logged raw.

    ``X-Forwarded-For`` is read because VEO runs behind a proxy. It is attacker-controlled,
    so it is used solely as a throttling and correlation hint and never as an
    authorization input.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else None


__all__ = [
    "LoginRequest",
    "LogoutPayload",
    "MePayload",
    "RefreshRequest",
    "SessionPayload",
    "router",
]
