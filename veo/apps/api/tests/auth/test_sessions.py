"""Refresh-token lineage: creation, rotation, revocation and family burn."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from veo.auth.sessions import (
    RevocationReason,
    create_session,
    is_usable,
    load_active_session,
    load_by_refresh_token,
    revoke_family,
    revoke_session,
    rotate_session,
    successor_of,
    sweep_expired,
)
from veo.auth.tokens import hash_refresh_token
from veo.db.models.identity import Organization, User
from veo.db.models.security import UserSession

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(
        not os.environ.get("VEO_TEST_DATABASE_URL"),
        reason="set VEO_TEST_DATABASE_URL to run the auth suite against PostgreSQL",
    ),
]


def test_create_stores_only_the_hash(db: Session, user: User, organization: Organization) -> None:
    issued = create_session(db, user_id=user.id, organization_id=organization.id)

    assert issued.session.refresh_token_hash == hash_refresh_token(issued.refresh_token)
    assert issued.refresh_token not in issued.session.refresh_token_hash
    stored = db.get(UserSession, issued.session.id)
    assert stored is not None
    assert issued.refresh_token not in str(stored.__dict__)


def test_create_seeds_a_family_and_zero_rotations(
    db: Session, user: User, organization: Organization
) -> None:
    issued = create_session(db, user_id=user.id, organization_id=organization.id)

    assert issued.session.family_id is not None
    assert issued.session.rotation_count == 0
    assert issued.session.rotated_from_id is None
    assert issued.session.revoked_at is None
    assert issued.session.expires_at > issued.session.issued_at


def test_load_by_refresh_token_finds_the_row(
    db: Session, user: User, organization: Organization
) -> None:
    issued = create_session(db, user_id=user.id, organization_id=organization.id)

    found = load_by_refresh_token(db, issued.refresh_token)

    assert found is not None
    assert found.id == issued.session.id
    assert load_by_refresh_token(db, "a-token-that-was-never-minted") is None


def test_rotation_revokes_the_old_row_and_links_the_new_one(
    db: Session, user: User, organization: Organization
) -> None:
    first = create_session(db, user_id=user.id, organization_id=organization.id)
    second = rotate_session(db, first.session)

    assert first.session.revoked_at is not None
    assert first.session.revoked_reason == RevocationReason.ROTATED
    assert second.session.rotated_from_id == first.session.id
    assert second.session.family_id == first.session.family_id
    assert second.session.rotation_count == 1
    assert second.refresh_token != first.refresh_token
    assert successor_of(db, first.session) is not None
    assert successor_of(db, first.session).id == second.session.id  # type: ignore[union-attr]


def test_rotated_token_is_no_longer_usable(
    db: Session, user: User, organization: Organization
) -> None:
    first = create_session(db, user_id=user.id, organization_id=organization.id)
    rotate_session(db, first.session)

    stale = load_by_refresh_token(db, first.refresh_token)

    assert stale is not None
    assert is_usable(stale, datetime.now(UTC)) is False


def test_revoke_family_burns_every_generation(
    db: Session, user: User, organization: Organization
) -> None:
    first = create_session(db, user_id=user.id, organization_id=organization.id)
    second = rotate_session(db, first.session)
    third = rotate_session(db, second.session)

    burned = revoke_family(
        db,
        family_id=first.session.family_id,
        organization_id=organization.id,
        reason=RevocationReason.REUSE_DETECTED,
    )

    assert burned >= 1
    db.refresh(third.session)
    assert third.session.revoked_reason == RevocationReason.REUSE_DETECTED
    assert third.session.revoked_at is not None


def test_revoke_family_never_reaches_another_organization(
    db: Session, user: User, organization: Organization, other_organization: Organization
) -> None:
    mine = create_session(db, user_id=user.id, organization_id=organization.id)
    theirs = create_session(db, user_id=user.id, organization_id=other_organization.id)
    # Force the pathological case: the same family id present under two organizations.
    theirs.session.family_id = mine.session.family_id
    db.flush()

    revoke_family(
        db,
        family_id=mine.session.family_id,
        organization_id=organization.id,
        reason=RevocationReason.REUSE_DETECTED,
    )

    db.refresh(theirs.session)
    assert theirs.session.revoked_at is None


def test_revoke_session_is_idempotent(
    db: Session, user: User, organization: Organization
) -> None:
    issued = create_session(db, user_id=user.id, organization_id=organization.id)

    revoke_session(db, issued.session, RevocationReason.LOGOUT)
    first_revoked_at = issued.session.revoked_at
    revoke_session(db, issued.session, RevocationReason.ADMIN_REVOKED)

    assert issued.session.revoked_at == first_revoked_at
    assert issued.session.revoked_reason == RevocationReason.LOGOUT


def test_load_active_session_is_organization_scoped(
    db: Session, user: User, organization: Organization, other_organization: Organization
) -> None:
    issued = create_session(db, user_id=user.id, organization_id=organization.id)

    assert load_active_session(db, issued.session.id, organization.id) is not None
    assert load_active_session(db, issued.session.id, other_organization.id) is None


def test_load_active_session_refuses_a_revoked_or_expired_row(
    db: Session, user: User, organization: Organization
) -> None:
    live = create_session(db, user_id=user.id, organization_id=organization.id)
    revoke_session(db, live.session, RevocationReason.LOGOUT)
    assert load_active_session(db, live.session.id, organization.id) is None

    stale = create_session(
        db,
        user_id=user.id,
        organization_id=organization.id,
        now=datetime.now(UTC) - timedelta(days=90),
    )
    assert load_active_session(db, stale.session.id, organization.id) is None


def test_sweep_marks_expired_rows_and_leaves_live_ones(
    db: Session, user: User, organization: Organization
) -> None:
    stale = create_session(
        db,
        user_id=user.id,
        organization_id=organization.id,
        now=datetime.now(UTC) - timedelta(days=90),
    )
    live = create_session(db, user_id=user.id, organization_id=organization.id)

    swept = sweep_expired(db, organization_id=organization.id)

    assert swept >= 1
    db.refresh(stale.session)
    db.refresh(live.session)
    assert stale.session.revoked_reason == RevocationReason.EXPIRED
    assert live.session.revoked_at is None


def test_sweep_does_not_touch_another_organization(
    db: Session, user: User, organization: Organization, other_organization: Organization
) -> None:
    stale = create_session(
        db,
        user_id=user.id,
        organization_id=other_organization.id,
        now=datetime.now(UTC) - timedelta(days=90),
    )

    sweep_expired(db, organization_id=organization.id)

    db.refresh(stale.session)
    assert stale.session.revoked_at is None


def test_client_fingerprints_are_stored_hashed_or_not_at_all(
    db: Session, user: User, organization: Organization
) -> None:
    issued = create_session(
        db,
        user_id=user.id,
        organization_id=organization.id,
        ip_hash=None,
        user_agent_hash=None,
    )

    assert issued.session.ip_hash is None
    assert issued.session.user_agent_hash is None


def test_rotating_an_unknown_family_id_finds_nothing(
    db: Session, organization: Organization
) -> None:
    assert (
        revoke_family(
            db,
            family_id=uuid.uuid4(),
            organization_id=organization.id,
            reason=RevocationReason.REUSE_DETECTED,
        )
        == 0
    )
