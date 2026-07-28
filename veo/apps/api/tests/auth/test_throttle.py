"""Sign-in throttling, keyed by a hash so lockout state cannot enumerate accounts."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.auth.hashing import identifier_hash
from veo.auth.throttle import (
    AccountLockedError,
    assert_not_locked,
    clear_failures,
    lockout_state,
    register_failure,
)
from veo.core.settings import get_settings
from veo.db.models.security import LoginAttempt

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(
        not os.environ.get("VEO_TEST_DATABASE_URL"),
        reason="set VEO_TEST_DATABASE_URL to run the auth suite against PostgreSQL",
    ),
]

EMAIL = "Locked.Out@Example.Test"


def _row(db: Session, email: str) -> LoginAttempt | None:
    return db.execute(
        select(LoginAttempt).where(LoginAttempt.identifier_hash == identifier_hash(email))
    ).scalar_one_or_none()


def test_identifier_is_stored_hashed_and_case_folded(db: Session) -> None:
    register_failure(db, EMAIL)

    row = _row(db, EMAIL)
    assert row is not None
    assert row.identifier_hash == identifier_hash(EMAIL.lower())
    assert len(row.identifier_hash) == 64
    assert "@" not in row.identifier_hash
    assert EMAIL.lower() not in str(row.__dict__)


def test_a_fresh_identifier_is_not_locked(db: Session) -> None:
    state = lockout_state(db, EMAIL)

    assert state.locked is False
    assert state.failed_count == 0
    assert state.retry_after_seconds == 0


def test_lockout_engages_only_after_the_configured_number_of_failures(db: Session) -> None:
    limit = get_settings().login_max_failed_attempts

    for attempt in range(1, limit):
        state = register_failure(db, EMAIL)
        assert state.locked is False, f"locked early at attempt {attempt}"

    final = register_failure(db, EMAIL)

    assert final.locked is True
    assert final.failed_count == limit
    assert final.retry_after_seconds > 0


def test_assert_not_locked_raises_once_locked(db: Session) -> None:
    for _ in range(get_settings().login_max_failed_attempts):
        register_failure(db, EMAIL)

    with pytest.raises(AccountLockedError) as caught:
        assert_not_locked(db, EMAIL)

    assert caught.value.retry_after_seconds > 0


def test_lockout_releases_after_the_window(db: Session) -> None:
    settings = get_settings()
    start = datetime.now(UTC)
    for _ in range(settings.login_max_failed_attempts):
        register_failure(db, EMAIL, now=start)

    assert lockout_state(db, EMAIL, now=start).locked is True

    later = start + timedelta(seconds=settings.login_lockout_seconds + 1)
    released = lockout_state(db, EMAIL, now=later)

    assert released.locked is False
    assert released.failed_count == 0
    assert_not_locked(db, EMAIL, now=later)


def test_failures_outside_the_window_do_not_accumulate(db: Session) -> None:
    settings = get_settings()
    start = datetime.now(UTC)

    for _ in range(settings.login_max_failed_attempts - 1):
        register_failure(db, EMAIL, now=start)

    much_later = start + timedelta(seconds=settings.login_failure_window_seconds + 60)
    state = register_failure(db, EMAIL, now=much_later)

    assert state.failed_count == 1
    assert state.locked is False


def test_a_success_clears_the_counter(db: Session) -> None:
    register_failure(db, EMAIL)
    register_failure(db, EMAIL)

    clear_failures(db, EMAIL)

    state = lockout_state(db, EMAIL)
    assert state.failed_count == 0
    assert state.locked is False


def test_two_identifiers_are_throttled_independently(db: Session) -> None:
    for _ in range(get_settings().login_max_failed_attempts):
        register_failure(db, EMAIL)

    assert lockout_state(db, EMAIL).locked is True
    assert lockout_state(db, "someone.else@example.test").locked is False
