"""The sign-in endpoints end to end: login, refresh rotation, replay, logout, me."""

from __future__ import annotations

import os
import statistics
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.auth.tokens import hash_refresh_token
from veo.contracts.enums import ErrorCode, Role
from veo.core.settings import get_settings
from veo.db.models.identity import Organization, RoleAssignment, User
from veo.db.models.security import UserSession

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
ME = "/api/auth/me"
WHOAMI = "/api/_probe/whoami"

FIXTURE_PASSWORD = "correct-horse-battery-staple-9f3"
FIXTURE_EMAIL = "Analyst@Example.Test"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _stable_shape(payload: dict[str, object]) -> object:
    """Everything about a response except the per-request correlation fields."""
    body = dict(payload)
    body.pop("meta", None)
    return body


# --------------------------------------------------------------------------- #
# Login
# --------------------------------------------------------------------------- #


def test_correct_password_signs_in(
    client: TestClient, user: User, login_body: dict[str, str]
) -> None:
    response = client.post(LOGIN, json=login_body)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == get_settings().access_token_ttl_seconds
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == FIXTURE_EMAIL.lower()
    assert sorted(data["roles"]) == ["ANALYST", "SALES_VIEWER"]
    assert "scan:run" in data["permissions"]


def test_login_email_is_case_insensitive(client: TestClient, user: User) -> None:
    response = client.post(
        LOGIN, json={"email": FIXTURE_EMAIL.upper(), "password": FIXTURE_PASSWORD}
    )

    assert response.status_code == 200


def test_login_creates_exactly_one_session_row(
    client: TestClient, db: Session, user: User, login_body: dict[str, str]
) -> None:
    response = client.post(LOGIN, json=login_body)

    rows = db.execute(select(UserSession).where(UserSession.user_id == user.id)).scalars().all()
    assert len(rows) == 1
    assert rows[0].refresh_token_hash == hash_refresh_token(
        response.json()["data"]["refresh_token"]
    )


def test_the_access_token_it_returns_actually_works(
    client: TestClient, user: User, login_body: dict[str, str]
) -> None:
    token = client.post(LOGIN, json=login_body).json()["data"]["access_token"]

    assert client.get(WHOAMI, headers=_bearer(token)).status_code == 200


def test_wrong_password_is_rejected(client: TestClient, user: User) -> None:
    response = client.post(LOGIN, json={"email": FIXTURE_EMAIL, "password": "not-it"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == ErrorCode.UNAUTHENTICATED
    assert response.json()["data"] is None


def test_unknown_user_and_wrong_password_are_indistinguishable(
    client: TestClient, user: User
) -> None:
    unknown = client.post(LOGIN, json={"email": "nobody@example.test", "password": "not-it"})
    wrong = client.post(LOGIN, json={"email": FIXTURE_EMAIL, "password": "not-it"})

    assert unknown.status_code == wrong.status_code == 401
    assert _stable_shape(unknown.json()) == _stable_shape(wrong.json())


def test_unknown_user_and_wrong_password_take_roughly_the_same_time(
    client: TestClient, user: User
) -> None:
    def _timed(body: dict[str, str]) -> float:
        start = time.perf_counter()
        client.post(LOGIN, json=body)
        return time.perf_counter() - start

    unknown = statistics.median(
        _timed({"email": f"ghost{n}@example.test", "password": "not-it"}) for n in range(5)
    )
    wrong = statistics.median(
        _timed({"email": FIXTURE_EMAIL, "password": "not-it"}) for _ in range(5)
    )

    ratio = unknown / wrong
    assert 0.4 < ratio < 2.5, f"timing side channel: unknown={unknown:.4f}s wrong={wrong:.4f}s"


def test_a_deactivated_user_cannot_sign_in(
    client: TestClient, db: Session, user: User, login_body: dict[str, str]
) -> None:
    user.is_active = False
    db.flush()

    assert client.post(LOGIN, json=login_body).status_code == 401


def test_a_user_with_no_role_in_any_organization_cannot_sign_in(
    client: TestClient, db: Session, user: User, organization: Organization,
    login_body: dict[str, str],
) -> None:
    for assignment in (
        db.execute(select(RoleAssignment).where(RoleAssignment.user_id == user.id))
        .scalars()
        .all()
    ):
        db.delete(assignment)
    db.flush()

    assert client.post(LOGIN, json=login_body).status_code == 401


def test_a_user_in_two_organizations_must_name_one(
    client: TestClient, db: Session, user: User, other_organization: Organization,
    login_body: dict[str, str],
) -> None:
    db.add(
        RoleAssignment(
            id=uuid.uuid4(),
            organization_id=other_organization.id,
            user_id=user.id,
            role=Role.DEVELOPER.value,
        )
    )
    db.flush()

    ambiguous = client.post(LOGIN, json=login_body)
    assert ambiguous.status_code == 409
    assert ambiguous.json()["error"]["code"] == ErrorCode.CONFLICT

    chosen = client.post(
        LOGIN, json={**login_body, "organization_slug": other_organization.slug}
    )
    assert chosen.status_code == 200
    assert chosen.json()["data"]["organization"]["slug"] == other_organization.slug
    assert chosen.json()["data"]["roles"] == ["DEVELOPER"]


def test_naming_an_organization_you_have_no_role_in_looks_like_a_bad_password(
    client: TestClient, other_organization: Organization, user: User, login_body: dict[str, str]
) -> None:
    response = client.post(
        LOGIN, json={**login_body, "organization_slug": other_organization.slug}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == ErrorCode.UNAUTHENTICATED


def test_lockout_after_the_configured_failures_and_release_after_the_window(
    client: TestClient, db: Session, user: User, login_body: dict[str, str]
) -> None:
    settings = get_settings()
    for _ in range(settings.login_max_failed_attempts):
        client.post(LOGIN, json={"email": FIXTURE_EMAIL, "password": "not-it"})

    locked = client.post(LOGIN, json=login_body)
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == ErrorCode.RATE_LIMITED
    assert locked.json()["error"]["retry_after_seconds"] > 0

    from veo.auth.hashing import identifier_hash
    from veo.db.models.security import LoginAttempt

    row = db.execute(
        select(LoginAttempt).where(
            LoginAttempt.identifier_hash == identifier_hash(FIXTURE_EMAIL)
        )
    ).scalar_one()
    row.locked_until = None
    row.failed_count = 0
    row.first_failed_at = None
    db.flush()

    assert client.post(LOGIN, json=login_body).status_code == 200


def test_a_successful_login_clears_earlier_failures(
    client: TestClient, db: Session, user: User, login_body: dict[str, str]
) -> None:
    from veo.auth.hashing import identifier_hash
    from veo.db.models.security import LoginAttempt

    for _ in range(2):
        client.post(LOGIN, json={"email": FIXTURE_EMAIL, "password": "not-it"})
    client.post(LOGIN, json=login_body)

    row = db.execute(
        select(LoginAttempt).where(
            LoginAttempt.identifier_hash == identifier_hash(FIXTURE_EMAIL)
        )
    ).scalar_one()
    assert row.failed_count == 0


# --------------------------------------------------------------------------- #
# Refresh
# --------------------------------------------------------------------------- #


def test_refresh_rotates_and_returns_a_working_pair(
    client: TestClient, user: User, login_body: dict[str, str]
) -> None:
    first = client.post(LOGIN, json=login_body).json()["data"]

    second = client.post(REFRESH, json={"refresh_token": first["refresh_token"]})

    assert second.status_code == 200
    rotated = second.json()["data"]
    assert rotated["refresh_token"] != first["refresh_token"]
    assert client.get(WHOAMI, headers=_bearer(rotated["access_token"])).status_code == 200


def test_the_old_refresh_token_stops_working_after_rotation(
    client: TestClient, user: User, login_body: dict[str, str]
) -> None:
    first = client.post(LOGIN, json=login_body).json()["data"]
    client.post(REFRESH, json={"refresh_token": first["refresh_token"]})

    replay = client.post(REFRESH, json={"refresh_token": first["refresh_token"]})

    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == ErrorCode.UNAUTHENTICATED


def test_replaying_a_rotated_refresh_token_burns_the_whole_family(
    client: TestClient, db: Session, user: User, login_body: dict[str, str]
) -> None:
    first = client.post(LOGIN, json=login_body).json()["data"]
    second = client.post(REFRESH, json={"refresh_token": first["refresh_token"]}).json()["data"]
    third = client.post(REFRESH, json={"refresh_token": second["refresh_token"]}).json()["data"]
    assert client.get(WHOAMI, headers=_bearer(third["access_token"])).status_code == 200

    stolen = client.post(REFRESH, json={"refresh_token": first["refresh_token"]})

    assert stolen.status_code == 401
    # The newest refresh token is dead too.
    assert client.post(REFRESH, json={"refresh_token": third["refresh_token"]}).status_code == 401
    # And so is the access token minted from it, on its very next use.
    assert client.get(WHOAMI, headers=_bearer(third["access_token"])).status_code == 401

    rows = db.execute(select(UserSession).where(UserSession.user_id == user.id)).scalars().all()
    assert len(rows) == 3
    assert all(row.revoked_at is not None for row in rows)
    assert any(row.revoked_reason == "REUSE_DETECTED" for row in rows)


def test_the_reuse_response_says_nothing_about_a_replay(
    client: TestClient, user: User, login_body: dict[str, str]
) -> None:
    first = client.post(LOGIN, json=login_body).json()["data"]
    client.post(REFRESH, json={"refresh_token": first["refresh_token"]})

    replayed = client.post(REFRESH, json={"refresh_token": first["refresh_token"]})
    never_existed = client.post(REFRESH, json={"refresh_token": "totally-made-up-token"})

    assert replayed.status_code == never_existed.status_code == 401
    assert _stable_shape(replayed.json()) == _stable_shape(never_existed.json())
    assert "reuse" not in replayed.text.lower()
    assert "family" not in replayed.text.lower()


def test_refresh_with_an_unknown_token_is_401(client: TestClient) -> None:
    response = client.post(REFRESH, json={"refresh_token": "no-such-token"})

    assert response.status_code == 401


# --------------------------------------------------------------------------- #
# Logout and me
# --------------------------------------------------------------------------- #


def test_logout_revokes_the_session(
    client: TestClient, db: Session, user: User, login_body: dict[str, str]
) -> None:
    signed_in = client.post(LOGIN, json=login_body).json()["data"]

    out = client.post(LOGOUT, headers=_bearer(signed_in["access_token"]))

    assert out.status_code == 200
    assert client.get(WHOAMI, headers=_bearer(signed_in["access_token"])).status_code == 401
    assert (
        client.post(REFRESH, json={"refresh_token": signed_in["refresh_token"]}).status_code == 401
    )
    row = db.execute(select(UserSession).where(UserSession.user_id == user.id)).scalar_one()
    assert row.revoked_reason == "LOGOUT"


def test_logout_without_a_token_is_401(client: TestClient) -> None:
    assert client.post(LOGOUT).status_code == 401


def test_me_returns_the_resolved_permission_list(
    client: TestClient, user: User, organization: Organization, login_body: dict[str, str]
) -> None:
    token = client.post(LOGIN, json=login_body).json()["data"]["access_token"]

    me = client.get(ME, headers=_bearer(token))

    assert me.status_code == 200
    data = me.json()["data"]
    assert data["user"]["id"] == str(user.id)
    assert data["user"]["email"] == FIXTURE_EMAIL.lower()
    assert data["organization"]["id"] == str(organization.id)
    assert sorted(data["roles"]) == ["ANALYST", "SALES_VIEWER"]
    assert data["permissions"] == sorted(set(data["permissions"]))
    assert "scan:run" in data["permissions"]
    assert "org:manage" not in data["permissions"]
    assert "credential:manage" not in data["permissions"]


def test_me_never_leaks_a_password_hash(
    client: TestClient, user: User, login_body: dict[str, str]
) -> None:
    token = client.post(LOGIN, json=login_body).json()["data"]["access_token"]

    body = client.get(ME, headers=_bearer(token)).text

    assert "$argon2" not in body
    assert "password" not in body.lower()
