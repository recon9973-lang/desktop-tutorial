"""What the audit trail records — and, more importantly, what it must never record."""

from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.auth.audit import REDACTED, AuthAuditAction, record_auth_event, sanitize_detail
from veo.auth.hashing import identifier_hash
from veo.db.models.identity import AuditLog, Organization, User

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(
        not os.environ.get("VEO_TEST_DATABASE_URL"),
        reason="set VEO_TEST_DATABASE_URL to run the auth suite against PostgreSQL",
    ),
]

LOGIN = "/api/auth/login"
REFRESH = "/api/auth/refresh"
LOGOUT = "/api/auth/logout"

FIXTURE_PASSWORD = "correct-horse-battery-staple-9f3"
FIXTURE_EMAIL = "Analyst@Example.Test"

#: Anything that must never appear anywhere in a serialized audit row.
FORBIDDEN_SUBSTRINGS = (
    FIXTURE_PASSWORD,
    FIXTURE_EMAIL,
    FIXTURE_EMAIL.lower(),
    "analyst@example.test",
    "$argon2",
    "203.0.113.7",
)


@pytest.fixture(autouse=True)
def _audit_baseline(db: Session) -> set:
    """Ids that already existed before this test ran.

    ``audit_logs`` is shared by every suite, and several of them legitimately write to
    it. Reading the whole table made these assertions depend on which suites happened to
    run first — under randomised ordering they failed for reasons that had nothing to do
    with authentication. Excluding pre-existing rows makes each test see only its own.
    """
    return {row.id for row in db.execute(select(AuditLog)).scalars().all()}


def _audit_rows(db: Session, baseline: set | None = None) -> list[AuditLog]:
    rows = list(db.execute(select(AuditLog).order_by(AuditLog.created_at)).scalars().all())
    if baseline is None:
        return rows
    return [row for row in rows if row.id not in baseline]


def _serialized(rows: list[AuditLog]) -> str:
    return json.dumps(
        [
            {
                "action": row.action,
                "actor_kind": row.actor_kind,
                "actor_user_id": str(row.actor_user_id),
                "organization_id": str(row.organization_id),
                "target_type": row.target_type,
                "target_id": row.target_id,
                "request_id": row.request_id,
                "source_ip_hash": row.source_ip_hash,
                "detail": row.detail,
            }
            for row in rows
        ],
        ensure_ascii=False,
    )


# --------------------------------------------------------------------------- #
# The scrubber itself
# --------------------------------------------------------------------------- #


def test_sanitize_drops_keys_that_are_not_on_the_allowlist() -> None:
    cleaned = sanitize_detail({"outcome": "OK", "password": "hunter2", "token": "abc"})

    assert cleaned == {"outcome": "OK"}


@pytest.mark.parametrize(
    "value",
    [
        "analyst@example.test",
        "203.0.113.7",
        "2001:db8::1",
        "$argon2id$v=19$m=65536,t=3,p=1$abc$def",
        "a" * 200,
    ],
)
def test_sanitize_redacts_values_that_look_sensitive(value: str) -> None:
    assert sanitize_detail({"outcome": value}) == {"outcome": REDACTED}


def test_sanitize_keeps_ordinary_machine_readable_values() -> None:
    cleaned = sanitize_detail({"outcome": "PASSWORD_MISMATCH", "attempt": 3, "locked": True})

    assert cleaned == {"outcome": "PASSWORD_MISMATCH", "attempt": 3, "locked": True}


def test_record_rejects_an_unknown_action(
    db: Session, _audit_baseline: set, organization: Organization
) -> None:
    with pytest.raises(ValueError):
        record_auth_event(db, action="auth.whatever", organization_id=organization.id)  # type: ignore[arg-type]


def test_record_hashes_nothing_it_was_not_given_hashed(
    db: Session, _audit_baseline: set, organization: Organization, user: User
) -> None:
    row = record_auth_event(
        db,
        action=AuthAuditAction.LOGIN_SUCCEEDED,
        organization_id=organization.id,
        actor_user_id=user.id,
        source_ip_hash=identifier_hash("203.0.113.7"),
    )

    assert row.source_ip_hash is not None
    assert len(row.source_ip_hash) == 64
    assert "203.0.113.7" not in row.source_ip_hash


# --------------------------------------------------------------------------- #
# End-to-end: every auth event, and nothing sensitive in any of them
# --------------------------------------------------------------------------- #


def test_a_successful_login_is_audited(
    client: TestClient,
    db: Session,
    _audit_baseline: set,
    user: User,
    organization: Organization,
    login_body: dict[str, str],
) -> None:
    client.post(LOGIN, json=login_body)

    actions = [row.action for row in _audit_rows(db, _audit_baseline)]
    assert AuthAuditAction.LOGIN_SUCCEEDED in actions


def test_a_failed_login_is_audited_without_naming_the_account(
    client: TestClient, db: Session, _audit_baseline: set, user: User
) -> None:
    client.post(LOGIN, json={"email": FIXTURE_EMAIL, "password": "not-it"})

    rows = _audit_rows(db, _audit_baseline)
    assert [row.action for row in rows] == [AuthAuditAction.LOGIN_FAILED]
    assert rows[0].actor_user_id is None
    assert FIXTURE_EMAIL.lower() not in _serialized(rows)


def test_a_failed_login_for_an_unknown_account_is_audited_identically(
    client: TestClient, db: Session, _audit_baseline: set
) -> None:
    client.post(LOGIN, json={"email": "ghost@example.test", "password": "not-it"})

    rows = _audit_rows(db, _audit_baseline)
    assert [row.action for row in rows] == [AuthAuditAction.LOGIN_FAILED]
    assert "ghost@example.test" not in _serialized(rows)


def test_lockout_refresh_logout_and_reuse_are_all_audited(
    client: TestClient, db: Session, _audit_baseline: set, user: User, login_body: dict[str, str]
) -> None:
    from veo.core.settings import get_settings

    for _ in range(get_settings().login_max_failed_attempts):
        client.post(LOGIN, json={"email": FIXTURE_EMAIL, "password": "not-it"})
    client.post(LOGIN, json=login_body)  # locked out

    from veo.auth.hashing import identifier_hash as _hash
    from veo.db.models.security import LoginAttempt

    row = db.execute(
        select(LoginAttempt).where(LoginAttempt.identifier_hash == _hash(FIXTURE_EMAIL))
    ).scalar_one()
    row.locked_until = None
    row.failed_count = 0
    row.first_failed_at = None
    db.flush()

    signed_in = client.post(LOGIN, json=login_body).json()["data"]
    rotated = client.post(REFRESH, json={"refresh_token": signed_in["refresh_token"]}).json()[
        "data"
    ]
    client.post(LOGOUT, headers={"Authorization": f"Bearer {rotated['access_token']}"})
    client.post(REFRESH, json={"refresh_token": signed_in["refresh_token"]})  # replay

    actions = {row.action for row in _audit_rows(db, _audit_baseline)}
    assert AuthAuditAction.LOGIN_LOCKED_OUT in actions
    assert AuthAuditAction.TOKEN_REFRESHED in actions
    assert AuthAuditAction.REFRESH_REUSE_DETECTED in actions
    assert AuthAuditAction.LOGOUT in actions


def test_no_audit_row_from_any_auth_event_contains_a_secret(
    client: TestClient, db: Session, _audit_baseline: set, user: User, login_body: dict[str, str]
) -> None:
    headers = {"X-Forwarded-For": "203.0.113.7"}
    client.post(LOGIN, json={"email": FIXTURE_EMAIL, "password": "not-it"}, headers=headers)
    signed_in = client.post(LOGIN, json=login_body, headers=headers).json()["data"]
    rotated = client.post(
        REFRESH, json={"refresh_token": signed_in["refresh_token"]}, headers=headers
    ).json()["data"]
    client.post(REFRESH, json={"refresh_token": signed_in["refresh_token"]}, headers=headers)
    client.post(LOGOUT, headers={**headers, "Authorization": f"Bearer {rotated['access_token']}"})

    blob = _serialized(_audit_rows(db, _audit_baseline))

    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert forbidden not in blob, f"audit trail leaked {forbidden!r}"
    for token in (
        signed_in["refresh_token"],
        rotated["refresh_token"],
        signed_in["access_token"],
        rotated["access_token"],
    ):
        assert token not in blob


def test_no_error_body_from_any_auth_failure_contains_a_secret(
    client: TestClient, user: User, login_body: dict[str, str]
) -> None:
    signed_in = client.post(LOGIN, json=login_body).json()["data"]
    client.post(REFRESH, json={"refresh_token": signed_in["refresh_token"]})

    bodies = [
        client.post(LOGIN, json={"email": FIXTURE_EMAIL, "password": "not-it"}).text,
        client.post(LOGIN, json={"email": "ghost@example.test", "password": "not-it"}).text,
        client.post(REFRESH, json={"refresh_token": signed_in["refresh_token"]}).text,
        client.get("/api/auth/me", headers={"Authorization": "Bearer a.b.c"}).text,
    ]

    for body in bodies:
        assert FIXTURE_PASSWORD not in body
        assert FIXTURE_EMAIL.lower() not in body
        assert "$argon2" not in body
        assert signed_in["refresh_token"] not in body
        assert "veo-test-signing-key" not in body
        assert "EXPIRED" not in body
        assert "BAD_SIGNATURE" not in body
