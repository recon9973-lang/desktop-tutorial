"""Refresh-token sessions: create, rotate, revoke, and burn a stolen family.

One sign-in produces one *family*. Every refresh replaces the current row with a new one
carrying the same ``family_id`` and a ``rotated_from_id`` pointing back at its
predecessor, so the whole lineage is walkable in both directions from any generation.

That linkage is what makes theft detectable. A refresh token is single-use: the moment it
is exchanged, its row is revoked as ``ROTATED``. If that same token turns up again, two
parties hold it — the legitimate client and someone else — and there is no way to tell
which one just presented it. The only safe answer is to revoke the entire family and make
both of them sign in again. Callers get a plain 401 either way; telling the presenter
that a replay was detected would tell an attacker exactly when to stop.

Every query here is scoped to one organization and checked by
:func:`veo.authz.assert_tenant_scoped`, with one deliberate exception documented on
:func:`load_by_refresh_token`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from veo.auth.tokens import hash_refresh_token, mint_refresh_token
from veo.authz import assert_tenant_scoped
from veo.core.settings import get_settings
from veo.db.models.security import UserSession


class RevocationReason(StrEnum):
    """Why a session row stopped being usable.

    Mirrors the closed set documented on ``UserSession.revoked_reason``.
    """

    LOGOUT = "LOGOUT"
    ROTATED = "ROTATED"
    REUSE_DETECTED = "REUSE_DETECTED"
    ADMIN_REVOKED = "ADMIN_REVOKED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"  # noqa: S105 - a reason code, not a credential
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class IssuedSession:
    """A stored session row plus the one and only copy of its refresh token.

    The plaintext exists here, in memory, on the way to the client. It is never written
    anywhere: the row holds SHA-256 of it and nothing else.
    """

    session: UserSession
    refresh_token: str


def is_usable(session: UserSession, now: datetime | None = None) -> bool:
    """Whether this row may still be exchanged or resolved against."""
    moment = now or datetime.now(UTC)
    return session.revoked_at is None and session.expires_at > moment


def create_session(
    db: Session,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    now: datetime | None = None,
    ttl_seconds: int | None = None,
    user_agent_hash: str | None = None,
    ip_hash: str | None = None,
) -> IssuedSession:
    """Open a new family for one user inside one organization."""
    issued_at = now or datetime.now(UTC)
    ttl = ttl_seconds if ttl_seconds is not None else get_settings().refresh_token_ttl_seconds
    token = mint_refresh_token()

    row = UserSession(
        id=uuid.uuid4(),
        organization_id=organization_id,
        user_id=user_id,
        refresh_token_hash=hash_refresh_token(token),
        family_id=uuid.uuid4(),
        rotated_from_id=None,
        rotation_count=0,
        issued_at=issued_at,
        expires_at=issued_at + timedelta(seconds=ttl),
        last_used_at=None,
        user_agent_hash=user_agent_hash,
        ip_hash=ip_hash,
    )
    db.add(row)
    db.flush()
    return IssuedSession(session=row, refresh_token=token)


def load_by_refresh_token(db: Session, refresh_token: str) -> UserSession | None:
    """Find the row a refresh token belongs to, whatever state it is in.

    This is the one lookup that cannot be organization-scoped up front: the token *is*
    the tenant selector, and the caller has no verified organization until the row is
    read. The hash column is globally unique, so exactly one row can match, and every
    query derived from that row — rotation, family revocation — is scoped to the
    organization it names.

    Revoked and expired rows are returned deliberately. Reuse detection depends on being
    able to see that a token was already spent; silently returning ``None`` would turn
    theft into an ordinary failed refresh.
    """
    if not refresh_token:
        return None
    statement = select(UserSession).where(
        UserSession.refresh_token_hash == hash_refresh_token(refresh_token)
    )
    return db.execute(statement).scalar_one_or_none()


def load_active_session(
    db: Session,
    session_id: uuid.UUID,
    organization_id: uuid.UUID,
    now: datetime | None = None,
) -> UserSession | None:
    """Load a session that is still usable, inside one organization."""
    statement = _scoped(organization_id).where(UserSession.id == session_id)
    row = db.execute(statement).scalar_one_or_none()
    if row is None or not is_usable(row, now):
        return None
    return row


def successor_of(db: Session, session: UserSession) -> UserSession | None:
    """The row this one rotated into, if it has been rotated.

    ``UserSession`` stores the backward link only. The forward direction — what the
    design calls ``rotated_to`` — is this query, which needs no extra column and cannot
    drift out of sync with the link it mirrors.
    """
    statement = _scoped(session.organization_id).where(
        UserSession.rotated_from_id == session.id
    )
    return db.execute(statement).scalars().first()


def rotate_session(
    db: Session,
    session: UserSession,
    *,
    now: datetime | None = None,
    ttl_seconds: int | None = None,
    user_agent_hash: str | None = None,
    ip_hash: str | None = None,
) -> IssuedSession:
    """Spend ``session`` and issue its successor in the same family.

    The predecessor is revoked as ``ROTATED`` in the same transaction as the insert, so
    there is never a moment when two tokens of one family are both usable.
    """
    moment = now or datetime.now(UTC)
    ttl = ttl_seconds if ttl_seconds is not None else get_settings().refresh_token_ttl_seconds
    token = mint_refresh_token()

    session.last_used_at = moment
    revoke_session(db, session, RevocationReason.ROTATED, now=moment)

    successor = UserSession(
        id=uuid.uuid4(),
        organization_id=session.organization_id,
        user_id=session.user_id,
        refresh_token_hash=hash_refresh_token(token),
        family_id=session.family_id,
        rotated_from_id=session.id,
        rotation_count=session.rotation_count + 1,
        issued_at=moment,
        expires_at=moment + timedelta(seconds=ttl),
        last_used_at=None,
        user_agent_hash=user_agent_hash if user_agent_hash is not None else session.user_agent_hash,
        ip_hash=ip_hash if ip_hash is not None else session.ip_hash,
    )
    db.add(successor)
    db.flush()
    return IssuedSession(session=successor, refresh_token=token)


def revoke_session(
    db: Session,
    session: UserSession,
    reason: RevocationReason,
    now: datetime | None = None,
) -> bool:
    """Revoke one row. Idempotent: the first reason and timestamp win.

    Keeping the original reason matters for forensics — a row revoked by ``ROTATED`` and
    later swept as ``EXPIRED`` should still read as the rotation that actually retired it.
    """
    if session.revoked_at is not None:
        return False
    session.revoked_at = now or datetime.now(UTC)
    session.revoked_reason = reason.value
    db.flush()
    return True


def revoke_family(
    db: Session,
    *,
    family_id: uuid.UUID,
    organization_id: uuid.UUID,
    reason: RevocationReason,
    now: datetime | None = None,
) -> int:
    """Revoke every still-usable row in one family. Returns how many were burned."""
    statement = _scoped(organization_id).where(UserSession.family_id == family_id)
    moment = now or datetime.now(UTC)
    burned = 0
    for row in db.execute(statement).scalars().all():
        if revoke_session(db, row, reason, now=moment):
            burned += 1
    return burned


def revoke_all_for_user(
    db: Session,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    reason: RevocationReason,
    now: datetime | None = None,
) -> int:
    """Sign a user out of one organization everywhere at once.

    Used when a password changes or an administrator withdraws access; every other
    organization the user belongs to is untouched, because those sessions are separate
    by construction.
    """
    statement = _scoped(organization_id).where(UserSession.user_id == user_id)
    moment = now or datetime.now(UTC)
    burned = 0
    for row in db.execute(statement).scalars().all():
        if revoke_session(db, row, reason, now=moment):
            burned += 1
    return burned


def sweep_expired(
    db: Session, *, organization_id: uuid.UUID, now: datetime | None = None
) -> int:
    """Mark rows whose lifetime has run out, so the table reads honestly.

    Expiry is already enforced at every read; this only stops long-dead rows from
    looking active to an operator browsing the table or to a future retention job.
    """
    moment = now or datetime.now(UTC)
    statement = _scoped(organization_id).where(UserSession.expires_at <= moment)
    swept = 0
    for row in db.execute(statement).scalars().all():
        if revoke_session(db, row, RevocationReason.EXPIRED, now=moment):
            swept += 1
    return swept


def _scoped(organization_id: uuid.UUID) -> Select[tuple[UserSession]]:
    """A ``SELECT`` over sessions that is already filtered to one organization.

    The guard is re-asserted rather than assumed: if someone later adds a clause that
    weakens the filter into an ``OR`` branch, this raises instead of quietly widening.
    """
    statement = select(UserSession).where(UserSession.organization_id == organization_id)
    assert_tenant_scoped(statement, organization_id)
    return statement
