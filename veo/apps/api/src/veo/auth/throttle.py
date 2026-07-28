"""Sign-in throttling, keyed by a hash so the counter cannot enumerate accounts.

An unthrottled login endpoint is a password-guessing service. Throttling it introduces a
second problem, though: if VEO only counted failures against addresses that exist, an
attacker could ask "did that lock out?" and learn which addresses have accounts. So the
counter is keyed by SHA-256 of the lowercased address and is incremented for *every*
failure, real account or not. The lockout state for ``ghost@example.test`` looks exactly
like the lockout state for a customer.

The trade-off this creates is deliberate: someone who knows a customer's address can lock
them out for the window. VEO accepts that over letting an attacker either guess passwords
without limit or enumerate the customer list. The window is short and self-releasing, and
:mod:`veo.auth.audit` records the lockout so a pattern of them is visible.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veo.auth.hashing import identifier_hash
from veo.authz import AuthenticationError
from veo.core.settings import get_settings
from veo.db.models.security import LoginAttempt


class AccountLockedError(AuthenticationError):
    """Too many recent failures for this identifier.

    Carries how long to wait so the API can send ``retry_after_seconds``. It carries no
    identifier and no failure count — an attacker learns only that they must stop, which
    is true for a non-existent address too.
    """

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("too many sign-in attempts")


@dataclass(frozen=True)
class LockoutState:
    """A read of the throttle counter at one moment."""

    locked: bool
    failed_count: int
    retry_after_seconds: int


_UNTHROTTLED = LockoutState(locked=False, failed_count=0, retry_after_seconds=0)


def lockout_state(db: Session, email: str, now: datetime | None = None) -> LockoutState:
    """Read the current throttle state without changing it.

    A lock whose window has passed reads as released, and the stale counters are cleared
    in passing so the next failure starts a fresh window.
    """
    moment = now or datetime.now(UTC)
    row = _find(db, email)
    if row is None:
        return _UNTHROTTLED

    if row.locked_until is not None:
        if row.locked_until > moment:
            return LockoutState(
                locked=True,
                failed_count=row.failed_count,
                retry_after_seconds=_seconds_until(row.locked_until, moment),
            )
        _reset(row)
        db.flush()
        return _UNTHROTTLED

    if _window_has_passed(row, moment):
        _reset(row)
        db.flush()
        return _UNTHROTTLED

    return LockoutState(locked=False, failed_count=row.failed_count, retry_after_seconds=0)


def assert_not_locked(db: Session, email: str, now: datetime | None = None) -> None:
    """Raise :class:`AccountLockedError` if this identifier is inside its lockout."""
    state = lockout_state(db, email, now=now)
    if state.locked:
        raise AccountLockedError(state.retry_after_seconds)


def register_failure(db: Session, email: str, now: datetime | None = None) -> LockoutState:
    """Count one failed sign-in and lock the identifier once the limit is reached."""
    settings = get_settings()
    moment = now or datetime.now(UTC)
    row = _find_or_create(db, email)

    if row.locked_until is not None and row.locked_until <= moment:
        _reset(row)
    if _window_has_passed(row, moment):
        _reset(row)

    row.failed_count += 1
    row.last_failed_at = moment
    if row.first_failed_at is None:
        row.first_failed_at = moment

    if row.failed_count >= settings.login_max_failed_attempts:
        row.locked_until = moment + timedelta(seconds=settings.login_lockout_seconds)

    db.flush()

    locked = row.locked_until is not None and row.locked_until > moment
    return LockoutState(
        locked=locked,
        failed_count=row.failed_count,
        retry_after_seconds=_seconds_until(row.locked_until, moment) if locked else 0,
    )


def clear_failures(db: Session, email: str) -> None:
    """Forget this identifier's failures. Called after a successful sign-in."""
    row = _find(db, email)
    if row is None:
        return
    _reset(row)
    db.flush()


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _find(db: Session, email: str) -> LoginAttempt | None:
    return db.execute(
        select(LoginAttempt).where(LoginAttempt.identifier_hash == identifier_hash(email))
    ).scalar_one_or_none()


def _find_or_create(db: Session, email: str) -> LoginAttempt:
    """Get the counter row, creating it if this identifier has never failed before.

    ``login_attempts`` has no ``organization_id`` and is not tenant-scoped by design: at
    the moment a sign-in fails there is no authenticated organization, and scoping the
    counter per organization would let an attacker reset it by naming a different one.
    """
    existing = _find(db, email)
    if existing is not None:
        return existing

    row = LoginAttempt(
        id=uuid.uuid4(),
        identifier_hash=identifier_hash(email),
        failed_count=0,
        first_failed_at=None,
        last_failed_at=None,
        locked_until=None,
    )
    savepoint = db.begin_nested()
    try:
        db.add(row)
        savepoint.commit()
    except IntegrityError:
        # Another request created the same counter between the read and the insert.
        savepoint.rollback()
        concurrent = _find(db, email)
        if concurrent is None:  # pragma: no cover - only reachable on a vanished row
            raise
        return concurrent
    return row


def _reset(row: LoginAttempt) -> None:
    row.failed_count = 0
    row.first_failed_at = None
    row.last_failed_at = None
    row.locked_until = None


def _window_has_passed(row: LoginAttempt, moment: datetime) -> bool:
    if row.first_failed_at is None:
        return False
    window = timedelta(seconds=get_settings().login_failure_window_seconds)
    return row.first_failed_at + window <= moment


def _seconds_until(deadline: datetime | None, moment: datetime) -> int:
    if deadline is None:
        return 0
    return max(1, math.ceil((deadline - moment).total_seconds()))
