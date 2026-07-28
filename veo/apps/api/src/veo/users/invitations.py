"""One-time links that let a new colleague choose their own password.

An administrator creates the account; the person who will use it chooses the password.
That split is the whole design. If an administrator set the password they would hold a
credential belonging to somebody else, and every later action by that person would be
deniable — "the admin knew my password" is a complete defence against any audit trail.

The token is random material, and only its SHA-256 is stored. The link is shown once, at
creation, and cannot be recovered afterwards: a stolen database therefore yields no usable
invitations. It is single-use and it expires.

**VEO does not send email.** There is no mail infrastructure here and inventing one would
be a bigger decision than this module should make. So the link is returned to the
administrator, who passes it to their colleague by whatever channel they already trust.
That is worth saying plainly rather than hiding: the administrator can see the link, and
could therefore use it themselves. In an organization where the administrator is already
``SUPER_ADMIN`` this grants them nothing they did not have — but it does mean an
invitation is only as private as the channel it is sent over.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final, final

from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.db.models.identity import User, UserInvitation

__all__ = [
    "DEFAULT_INVITATION_TTL_DAYS",
    "INVITATION_TOKEN_BYTES",
    "AcceptedInvitation",
    "InvitationError",
    "InvitationInvalid",
    "IssuedInvitation",
    "accept_invitation",
    "fingerprint_token",
    "issue_invitation",
    "looks_like_invitation_token",
    "revoke_invitations_for",
]

#: 32 bytes of ``secrets`` output. The token is the only thing standing between a stranger
#: and an account, and it is not rate-limited by a login throttle because there is no
#: account to throttle yet.
INVITATION_TOKEN_BYTES: Final = 32

#: Long enough that a colleague can be reached over a weekend, short enough that a link
#: forgotten in a chat log stops working.
DEFAULT_INVITATION_TTL_DAYS: Final = 7

#: ``token_urlsafe(32)`` yields 43 characters. Accept a small range rather than an exact
#: length so the constant above can change without silently rejecting every token.
_MIN_TOKEN_LENGTH: Final = 32
_MAX_TOKEN_LENGTH: Final = 128


class InvitationError(Exception):
    """Something is wrong with an invitation."""


class InvitationInvalid(InvitationError):
    """Unknown, expired, revoked or already used.

    Deliberately one exception for all four. Telling a caller which one it was confirms
    that a particular token once existed, which is the only thing an attacker holding a
    guess actually wants to learn.
    """


@final
@dataclass(frozen=True, slots=True)
class IssuedInvitation:
    """A freshly minted invitation. ``token`` exists only in this object."""

    invitation_id: uuid.UUID
    user_id: uuid.UUID
    token: str
    expires_at: datetime

    def link(self, base_url: str) -> str:
        """The URL to hand to the colleague."""
        return f"{base_url.rstrip('/')}/invite/{self.token}"


@final
@dataclass(frozen=True, slots=True)
class AcceptedInvitation:
    """Who just finished setting up, so the caller can audit it."""

    invitation_id: uuid.UUID
    user_id: uuid.UUID
    organization_id: uuid.UUID


def fingerprint_token(token: str) -> str:
    """What is stored. The token itself never is."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def looks_like_invitation_token(token: str) -> bool:
    """A cheap shape check, so a junk value never reaches the database."""
    return _MIN_TOKEN_LENGTH <= len(token) <= _MAX_TOKEN_LENGTH and token.isascii()


def issue_invitation(
    db: Session,
    *,
    user: User,
    organization_id: uuid.UUID,
    invited_by: uuid.UUID | None,
    ttl_days: int = DEFAULT_INVITATION_TTL_DAYS,
    now: datetime | None = None,
) -> IssuedInvitation:
    """Mint an invitation, revoking any earlier one for the same person.

    Revoking first matters: re-inviting somebody is what an administrator does when the
    first link went astray, and leaving the old one alive would mean the lost link still
    works.
    """
    moment = now or datetime.now(UTC)
    revoke_invitations_for(db, user_id=user.id, now=moment)

    token = secrets.token_urlsafe(INVITATION_TOKEN_BYTES)
    invitation = UserInvitation(
        id=uuid.uuid4(),
        organization_id=organization_id,
        user_id=user.id,
        token_hash=fingerprint_token(token),
        expires_at=moment + timedelta(days=ttl_days),
        invited_by=invited_by,
    )
    db.add(invitation)
    db.flush()

    return IssuedInvitation(
        invitation_id=invitation.id,
        user_id=user.id,
        token=token,
        expires_at=invitation.expires_at,
    )


def revoke_invitations_for(
    db: Session, *, user_id: uuid.UUID, now: datetime | None = None
) -> int:
    """Kill every outstanding invitation for one person. Returns how many."""
    moment = now or datetime.now(UTC)
    outstanding = list(
        db.scalars(
            select(UserInvitation).where(
                UserInvitation.user_id == user_id,
                UserInvitation.accepted_at.is_(None),
                UserInvitation.revoked_at.is_(None),
            )
        )
    )
    for invitation in outstanding:
        invitation.revoked_at = moment
    if outstanding:
        db.flush()
    return len(outstanding)


def accept_invitation(
    db: Session, *, token: str, password_hash: str, now: datetime | None = None
) -> AcceptedInvitation:
    """Spend the invitation and set the password. Raises :class:`InvitationInvalid`.

    The password arrives already hashed. This module has no business holding a plaintext
    password, and taking one would put it in a second place where it could be logged.
    """
    moment = now or datetime.now(UTC)
    if not looks_like_invitation_token(token):
        raise InvitationInvalid("초대 링크가 올바르지 않습니다.")

    invitation = db.scalars(
        select(UserInvitation).where(UserInvitation.token_hash == fingerprint_token(token))
    ).one_or_none()

    if invitation is None or invitation.accepted_at or invitation.revoked_at:
        raise InvitationInvalid("초대 링크가 만료되었거나 이미 사용되었습니다.")
    if _as_utc(invitation.expires_at) <= moment:
        raise InvitationInvalid("초대 링크가 만료되었거나 이미 사용되었습니다.")

    person = db.get(User, invitation.user_id)
    if person is None:
        raise InvitationInvalid("초대 링크가 만료되었거나 이미 사용되었습니다.")

    person.password_hash = password_hash
    # The account exists but cannot be signed into until this moment. Creating it active
    # with no password would leave a live account nobody can use and nobody is watching.
    person.is_active = True
    invitation.accepted_at = moment
    db.flush()

    return AcceptedInvitation(
        invitation_id=invitation.id,
        user_id=person.id,
        organization_id=invitation.organization_id,
    )


def _as_utc(value: datetime) -> datetime:
    """PostgreSQL hands back an aware datetime; SQLite and fixtures may not."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)
