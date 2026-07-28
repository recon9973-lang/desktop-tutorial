"""Principal resolution: the token is a hint, the database is the authority."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from veo.auth.sessions import RevocationReason, create_session, revoke_session
from veo.auth.tokens import encode_access_token
from veo.contracts.enums import ErrorCode, Role
from veo.db.models.identity import Organization, RoleAssignment, User

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(
        not os.environ.get("VEO_TEST_DATABASE_URL"),
        reason="set VEO_TEST_DATABASE_URL to run the auth suite against PostgreSQL",
    ),
]

PROBE = "/api/_probe/scan-run"
WHOAMI = "/api/_probe/whoami"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def live_token(db: Session, user: User, organization: Organization) -> tuple[str, uuid.UUID]:
    issued = create_session(db, user_id=user.id, organization_id=organization.id)
    token = encode_access_token(
        user_id=user.id,
        organization_id=organization.id,
        roles=frozenset({Role.ANALYST, Role.SALES_VIEWER}),
        session_id=issued.session.id,
    )
    return token, issued.session.id


def _error_code(response: object) -> str:
    body = response.json()  # type: ignore[attr-defined]
    return str(body["error"]["code"])


def test_a_live_session_resolves(client: TestClient, live_token: tuple[str, uuid.UUID]) -> None:
    token, session_id = live_token

    response = client.get(WHOAMI, headers=_bearer(token))

    assert response.status_code == 200
    assert response.json()["session_id"] == str(session_id)


def test_no_header_is_401_unauthenticated(client: TestClient) -> None:
    response = client.get(WHOAMI)

    assert response.status_code == 401
    assert _error_code(response) == ErrorCode.UNAUTHENTICATED


@pytest.mark.parametrize(
    "header",
    [
        {"Authorization": "Basic abc"},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer "},
        {"Authorization": "bearer not.a.token"},
        {"Authorization": "Token abc"},
    ],
)
def test_unusable_authorization_headers_are_401(
    client: TestClient, header: dict[str, str]
) -> None:
    response = client.get(WHOAMI, headers=header)

    assert response.status_code == 401
    assert _error_code(response) == ErrorCode.UNAUTHENTICATED


def test_expired_access_token_is_401(
    client: TestClient, db: Session, user: User, organization: Organization
) -> None:
    issued = create_session(db, user_id=user.id, organization_id=organization.id)
    token = encode_access_token(
        user_id=user.id,
        organization_id=organization.id,
        roles=frozenset({Role.ANALYST}),
        session_id=issued.session.id,
        issued_at=datetime.now(UTC) - timedelta(hours=3),
        ttl_seconds=60,
    )

    response = client.get(WHOAMI, headers=_bearer(token))

    assert response.status_code == 401
    assert _error_code(response) == ErrorCode.UNAUTHENTICATED


def test_revoked_session_cannot_resolve_a_principal(
    client: TestClient, db: Session, live_token: tuple[str, uuid.UUID]
) -> None:
    token, session_id = live_token
    assert client.get(WHOAMI, headers=_bearer(token)).status_code == 200

    from veo.db.models.security import UserSession

    session_row = db.get(UserSession, session_id)
    assert session_row is not None
    revoke_session(db, session_row, RevocationReason.LOGOUT)
    db.flush()

    assert client.get(WHOAMI, headers=_bearer(token)).status_code == 401


def test_a_token_whose_session_never_existed_is_401(
    client: TestClient, user: User, organization: Organization
) -> None:
    token = encode_access_token(
        user_id=user.id,
        organization_id=organization.id,
        roles=frozenset({Role.ANALYST}),
        session_id=uuid.uuid4(),
    )

    assert client.get(WHOAMI, headers=_bearer(token)).status_code == 401


def test_token_org_claim_must_match_the_session_row(
    client: TestClient,
    db: Session,
    user: User,
    organization: Organization,
    other_organization: Organization,
) -> None:
    issued = create_session(db, user_id=user.id, organization_id=organization.id)
    forged = encode_access_token(
        user_id=user.id,
        organization_id=other_organization.id,
        roles=frozenset({Role.ANALYST}),
        session_id=issued.session.id,
    )

    assert client.get(WHOAMI, headers=_bearer(forged)).status_code == 401


def test_token_subject_must_match_the_session_row(
    client: TestClient, db: Session, user: User, organization: Organization
) -> None:
    issued = create_session(db, user_id=user.id, organization_id=organization.id)
    forged = encode_access_token(
        user_id=uuid.uuid4(),
        organization_id=organization.id,
        roles=frozenset({Role.ANALYST}),
        session_id=issued.session.id,
    )

    assert client.get(WHOAMI, headers=_bearer(forged)).status_code == 401


def test_roles_come_from_the_database_not_the_claim(
    client: TestClient, db: Session, user: User, organization: Organization
) -> None:
    """A token that claims SUPER_ADMIN gets exactly what the database grants."""
    issued = create_session(db, user_id=user.id, organization_id=organization.id)
    inflated = encode_access_token(
        user_id=user.id,
        organization_id=organization.id,
        roles=frozenset({Role.SUPER_ADMIN}),
        session_id=issued.session.id,
    )

    me = client.get("/api/auth/me", headers=_bearer(inflated))

    assert me.status_code == 200
    assert sorted(me.json()["data"]["roles"]) == ["ANALYST", "SALES_VIEWER"]
    assert "org:manage" not in me.json()["data"]["permissions"]


def test_a_role_removed_in_the_database_stops_granting_on_the_next_request(
    client: TestClient, db: Session, user: User, organization: Organization,
    live_token: tuple[str, uuid.UUID],
) -> None:
    token, _ = live_token
    assert client.get(PROBE, headers=_bearer(token)).status_code == 200

    db.execute(
        delete(RoleAssignment).where(
            RoleAssignment.user_id == user.id,
            RoleAssignment.organization_id == organization.id,
            RoleAssignment.role == Role.ANALYST.value,
        )
    )
    db.flush()

    denied = client.get(PROBE, headers=_bearer(token))

    assert denied.status_code == 403
    assert _error_code(denied) == ErrorCode.PERMISSION_DENIED
    # The remaining role still works: this is a narrowing, not a logout.
    assert client.get(WHOAMI, headers=_bearer(token)).status_code == 200


def test_losing_every_role_ends_the_principal_entirely(
    client: TestClient, db: Session, user: User, organization: Organization,
    live_token: tuple[str, uuid.UUID],
) -> None:
    token, _ = live_token

    db.execute(
        delete(RoleAssignment).where(
            RoleAssignment.user_id == user.id,
            RoleAssignment.organization_id == organization.id,
        )
    )
    db.flush()

    assert client.get(WHOAMI, headers=_bearer(token)).status_code == 401


def test_a_deactivated_user_stops_resolving(
    client: TestClient, db: Session, user: User, live_token: tuple[str, uuid.UUID]
) -> None:
    token, _ = live_token
    user.is_active = False
    db.flush()

    assert client.get(WHOAMI, headers=_bearer(token)).status_code == 401


def test_a_deactivated_organization_stops_resolving(
    client: TestClient, db: Session, organization: Organization,
    live_token: tuple[str, uuid.UUID],
) -> None:
    token, _ = live_token
    organization.is_active = False
    db.flush()

    assert client.get(WHOAMI, headers=_bearer(token)).status_code == 401


def test_missing_permission_is_403_not_404_or_500(
    client: TestClient, db: Session, user: User, organization: Organization
) -> None:
    db.execute(
        delete(RoleAssignment).where(
            RoleAssignment.user_id == user.id,
            RoleAssignment.organization_id == organization.id,
            RoleAssignment.role == Role.ANALYST.value,
        )
    )
    db.flush()
    issued = create_session(db, user_id=user.id, organization_id=organization.id)
    token = encode_access_token(
        user_id=user.id,
        organization_id=organization.id,
        roles=frozenset({Role.SALES_VIEWER}),
        session_id=issued.session.id,
    )

    response = client.get(PROBE, headers=_bearer(token))

    assert response.status_code == 403
    assert _error_code(response) == ErrorCode.PERMISSION_DENIED
