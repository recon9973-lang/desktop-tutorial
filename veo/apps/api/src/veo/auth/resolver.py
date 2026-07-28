"""Turning an ``Authorization: Bearer`` header into a :class:`~veo.authz.Principal`.

The rule that shapes this module: **the token says who you claim to be, the database says
what you may do.** Roles are loaded from ``role_assignments`` on every request and the
``roles`` claim is only cross-checked against them. If the claim were trusted, withdrawing
someone's access would take effect whenever their current access token happened to
expire — up to fifteen minutes of authority that an administrator already revoked. Reading
the row costs one indexed query and closes that window entirely.

The same reasoning applies to the session: an access token is not revocable on its own, so
every request re-checks that its session row is still active and unexpired. Revocation is
therefore effective on the next request, not on the next token refresh.

Failures here return ``None`` rather than explaining themselves. ``veo.authz`` turns that
into an ``AuthenticationError``, and the handler installed below renders one generic
Korean sentence for every cause.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager

from fastapi import FastAPI, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.auth.tokens import (
    AccessTokenClaims,
    TokenError,
    decode_access_token,
)
from veo.authz import (
    Principal,
    assert_tenant_scoped,
    set_principal_resolver,
)
from veo.contracts.enums import Role
from veo.db.models.identity import Organization, RoleAssignment, User
from veo.db.session import session_scope

BEARER_PREFIX = "bearer"

PERMISSION_DENIED_MESSAGE_KO = "이 작업을 수행할 권한이 없습니다."
NOT_FOUND_MESSAGE_KO = "요청한 리소스를 찾을 수 없습니다."
LOCKED_OUT_MESSAGE_KO = "로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요."

#: A callable that yields a database session for the duration of one resolution.
type SessionFactory = Callable[[], AbstractContextManager[Session]]


def bearer_token_from(request: Request) -> str | None:
    """Extract the credential from ``Authorization``, or ``None``.

    The scheme is compared case-insensitively — RFC 7235 says it is case-insensitive, and
    rejecting ``bearer`` would fail for correct clients while stopping no attacker.
    """
    header = request.headers.get("authorization")
    if not header:
        return None
    scheme, _, credential = header.partition(" ")
    if scheme.strip().lower() != BEARER_PREFIX:
        return None
    token = credential.strip()
    return token or None


def load_roles(db: Session, user_id: uuid.UUID, organization_id: uuid.UUID) -> frozenset[Role]:
    """The roles this user holds in this organization, right now.

    A stored role name VEO no longer recognises is ignored rather than fatal: a removed
    role must grant nothing, and refusing the whole request would lock a customer out of
    a product they still have valid access to.
    """
    statement = select(RoleAssignment).where(
        RoleAssignment.organization_id == organization_id,
        RoleAssignment.user_id == user_id,
    )
    assert_tenant_scoped(statement, organization_id)

    roles: set[Role] = set()
    for assignment in db.execute(statement).scalars().all():
        try:
            roles.add(Role(assignment.role))
        except ValueError:
            continue
    return frozenset(roles)


class BearerPrincipalResolver:
    """Resolves the caller from a bearer access token.

    Registered on the application by :func:`install_auth`; ``veo.authz`` calls it through
    the ``PrincipalResolver`` protocol.
    """

    def __init__(self, session_factory: SessionFactory | None = None) -> None:
        self._session_factory: SessionFactory = session_factory or session_scope

    async def __call__(self, request: Request) -> Principal | None:
        token = bearer_token_from(request)
        if token is None:
            return None
        try:
            claims = decode_access_token(token)
        except TokenError:
            return None

        with self._session_factory() as db:
            return self._principal_for(db, claims)

    def _principal_for(self, db: Session, claims: AccessTokenClaims) -> Principal | None:
        from veo.auth.sessions import load_active_session

        # Scoped by the organization named in the token: a session belonging to another
        # organization simply is not found, so a swapped ``org`` claim resolves to nothing.
        session_row = load_active_session(db, claims.session_id, claims.organization_id)
        if session_row is None or session_row.user_id != claims.user_id:
            return None

        user = db.get(User, claims.user_id)
        if user is None or not user.is_active:
            return None

        organization = db.get(Organization, claims.organization_id)
        if organization is None or not organization.is_active:
            return None

        roles = load_roles(db, user.id, organization.id)
        if not roles:
            # Membership was withdrawn. There is no such thing as an authenticated caller
            # with no role: it would be a principal that every guard has to special-case.
            return None

        return Principal(
            user_id=user.id,
            organization_id=organization.id,
            roles=roles,
            session_id=str(session_row.id),
            is_service_account=False,
            display_name=user.display_name,
        )


# --------------------------------------------------------------------------- #
# Application wiring
# --------------------------------------------------------------------------- #


def install_auth(app: FastAPI, *, session_factory: SessionFactory | None = None) -> None:
    """Register the resolver and the authentication error handlers on ``app``.

    Mounting the router stays the integrator's call — this only teaches the application
    how to recognise a caller and how to render a refusal. Without it every guarded route
    fails closed, which is the correct behaviour for a misconfigured deployment.

    The HTTP mapping is deliberate:

    * unauthenticated → **401**, one generic sentence, no hint at which check failed;
    * authenticated but not permitted → **403**, without naming the missing permission;
    * a resource in another organization → **404**, never 403, because a 403 would
      confirm that the resource exists;
    * locked out → **429** with ``retry_after_seconds``.
    """
    set_principal_resolver(app, BearerPrincipalResolver(session_factory=session_factory))

    # The error handlers below are NOT registered here. `veo.api.app.create_app` owns the
    # whole HTTP error mapping — 401 / 403 / 404 / 429 / 500 — so there is exactly one
    # place to read and one place to change. Registering a second copy here would let the
    # two drift apart silently, which is how a 404 quietly becomes a 403 that confirms a
    # resource exists. The handler functions stay as the reference implementation and are
    # place to read and one place to change lives in `veo.api.app`.


