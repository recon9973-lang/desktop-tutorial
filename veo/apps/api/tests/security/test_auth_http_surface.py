"""Integration-maintainer verification of the authentication surface.

Written independently of the auth package's own suite, against the real assembled
application, because a worker's tests can only prove what that worker thought to check.
Everything here goes through HTTP.
"""

from __future__ import annotations

import base64
import json
import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, text
from sqlalchemy.orm import Session, sessionmaker

from veo.api.app import create_app
from veo.contracts.enums import Role
from veo.db.models import Organization, RoleAssignment, User, UserSession

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(not DATABASE_URL, reason="needs VEO_TEST_DATABASE_URL"),
]

PASSWORD = "correct-horse-battery-staple-9134"
JWT_SECRET = "integration-verification-secret-not-a-real-key"


@pytest.fixture(scope="module")
def engine():  # type: ignore[no-untyped-def]
    assert DATABASE_URL is not None
    eng = create_engine(DATABASE_URL)
    yield eng
    eng.dispose()


@pytest.fixture(scope="module", autouse=True)
def app_env() -> Iterator[None]:
    """Point the application itself at the test database.

    ``VEO_TEST_DATABASE_URL`` is what the *tests* connect with; the application reads
    ``VEO_DATABASE_URL``. Without this the app would happily talk to the development
    database while the fixtures wrote to the test one.
    """
    from veo.core.settings import get_settings
    from veo.db import session as db_session

    previous = {
        key: os.environ.get(key) for key in ("VEO_JWT_SECRET", "VEO_DATABASE_URL")
    }
    assert DATABASE_URL is not None
    os.environ["VEO_JWT_SECRET"] = JWT_SECRET
    os.environ["VEO_DATABASE_URL"] = DATABASE_URL

    get_settings.cache_clear()
    db_session.get_engine.cache_clear()
    db_session.get_session_factory.cache_clear()
    yield
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    get_settings.cache_clear()
    db_session.get_engine.cache_clear()
    db_session.get_session_factory.cache_clear()


@pytest.fixture
def db(engine) -> Iterator[Session]:  # type: ignore[no-untyped-def]
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    yield session
    session.close()


@pytest.fixture
def tenants(db: Session) -> Iterator[dict[str, object]]:
    """Two organizations, one user each, plus a user who belongs to neither."""
    marker = uuid.uuid4().hex[:10]
    hasher = PasswordHasher()
    password_hash = hasher.hash(PASSWORD)

    org_a = Organization(slug=f"a-{marker}", name="조직 A", settings={})
    org_b = Organization(slug=f"b-{marker}", name="조직 B", settings={})
    db.add_all([org_a, org_b])
    db.flush()

    alice = User(
        email=f"alice-{marker}@example.test",
        display_name="앨리스",
        password_hash=password_hash,
        is_active=True,
    )
    bob = User(
        email=f"bob-{marker}@example.test",
        display_name="밥",
        password_hash=password_hash,
        is_active=True,
    )
    nobody = User(
        email=f"nobody-{marker}@example.test",
        display_name="무권한",
        password_hash=password_hash,
        is_active=True,
    )
    db.add_all([alice, bob, nobody])
    db.flush()

    db.add_all(
        [
            RoleAssignment(organization_id=org_a.id, user_id=alice.id, role=Role.ANALYST.value),
            RoleAssignment(
                organization_id=org_b.id, user_id=bob.id, role=Role.SALES_VIEWER.value
            ),
        ]
    )
    db.commit()

    payload = {
        "org_a": org_a,
        "org_b": org_b,
        "alice": alice,
        "bob": bob,
        "nobody": nobody,
        "marker": marker,
    }
    yield payload

    db.execute(delete(UserSession).where(UserSession.user_id.in_([alice.id, bob.id, nobody.id])))
    db.execute(
        delete(RoleAssignment).where(RoleAssignment.organization_id.in_([org_a.id, org_b.id]))
    )
    db.execute(delete(User).where(User.id.in_([alice.id, bob.id, nobody.id])))
    db.execute(delete(Organization).where(Organization.id.in_([org_a.id, org_b.id])))
    db.execute(text("DELETE FROM login_attempts"))
    db.execute(text("DELETE FROM audit_logs"))
    db.commit()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def login(client: TestClient, email: str, password: str = PASSWORD) -> dict:
    return client.post(
        "/api/auth/login", json={"email": email, "password": password}
    ).json()


def access_token_of(body: dict) -> str:
    data = body["data"]
    for key in ("access_token", "accessToken", "token"):
        if key in data:
            return str(data[key])
    raise AssertionError(f"no access token in login response: {sorted(data)}")


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------- #
# Unauthenticated surface
# --------------------------------------------------------------------------- #


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_public_endpoints_stay_public(client: TestClient) -> None:
    """Adding auth must not have quietly locked the open surface."""
    for path in ("/api/health", "/api/providers", "/api/scoring/specs"):
        assert client.get(path).status_code == 200, path


def test_garbage_authorization_header_is_401_not_500(client: TestClient) -> None:
    for value in ("", "Bearer", "Bearer ", "Basic abc", "Bearer not.a.jwt", "Bearer " + "a" * 400):
        response = client.get("/api/auth/me", headers={"Authorization": value})
        assert response.status_code == 401, value


# --------------------------------------------------------------------------- #
# Login
# --------------------------------------------------------------------------- #


def test_login_succeeds_and_me_reports_resolved_permissions(
    client: TestClient, tenants: dict
) -> None:
    body = login(client, tenants["alice"].email)
    token = access_token_of(body)

    me = client.get("/api/auth/me", headers=bearer(token))
    assert me.status_code == 200
    data = me.json()["data"]

    permissions = data.get("permissions")
    assert permissions, "the front end needs the resolved permission list"
    assert "project:read" in permissions
    assert "user:manage" not in permissions, "ANALYST must not hold user management"


def test_unknown_user_and_wrong_password_are_indistinguishable(
    client: TestClient, tenants: dict
) -> None:
    unknown = client.post(
        "/api/auth/login",
        json={"email": f"ghost-{tenants['marker']}@example.test", "password": PASSWORD},
    )
    wrong = client.post(
        "/api/auth/login",
        json={"email": tenants["alice"].email, "password": "definitely-not-the-password"},
    )

    assert unknown.status_code == wrong.status_code
    assert unknown.json()["error"]["code"] == wrong.json()["error"]["code"]
    assert unknown.json()["error"]["message"] == wrong.json()["error"]["message"]


def test_login_response_never_echoes_the_password(client: TestClient, tenants: dict) -> None:
    response = client.post(
        "/api/auth/login", json={"email": tenants["alice"].email, "password": PASSWORD}
    )
    assert PASSWORD not in response.text


def test_user_with_no_role_assignment_cannot_sign_in_anywhere(
    client: TestClient, tenants: dict
) -> None:
    """Belonging to no organization must not produce an ambient identity."""
    response = client.post(
        "/api/auth/login", json={"email": tenants["nobody"].email, "password": PASSWORD}
    )
    assert response.status_code in {401, 403}
    assert response.json()["error"]["code"] in {"UNAUTHENTICATED", "PERMISSION_DENIED"}


# --------------------------------------------------------------------------- #
# Token forgery
# --------------------------------------------------------------------------- #


def test_token_signed_with_another_secret_is_rejected(
    client: TestClient, tenants: dict
) -> None:
    forged = jwt.encode(
        {
            "sub": str(tenants["alice"].id),
            "org": str(tenants["org_a"].id),
            "roles": [Role.SUPER_ADMIN.value],
            "sid": str(uuid.uuid4()),
            "jti": uuid.uuid4().hex,
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
            "iss": "veo",
            "aud": "veo-console",
        },
        "the-attackers-own-secret",
        algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers=bearer(forged)).status_code == 401


def test_alg_none_token_is_rejected(client: TestClient, tenants: dict) -> None:
    """The classic JWT bypass: strip the signature and claim the algorithm is none."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    claims = base64.urlsafe_b64encode(
        json.dumps(
            {
                "sub": str(tenants["alice"].id),
                "org": str(tenants["org_a"].id),
                "roles": [Role.SUPER_ADMIN.value],
                "sid": str(uuid.uuid4()),
                "iss": "veo",
                "aud": "veo-console",
                "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
            }
        ).encode()
    )
    token = f"{header.rstrip(b'=').decode()}.{claims.rstrip(b'=').decode()}."
    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 401


def test_expired_token_is_rejected(client: TestClient, tenants: dict) -> None:
    expired = jwt.encode(
        {
            "sub": str(tenants["alice"].id),
            "org": str(tenants["org_a"].id),
            "roles": [Role.ANALYST.value],
            "sid": str(uuid.uuid4()),
            "jti": uuid.uuid4().hex,
            "iat": int((datetime.now(UTC) - timedelta(hours=2)).timestamp()),
            "exp": int((datetime.now(UTC) - timedelta(hours=1)).timestamp()),
            "iss": "veo",
            "aud": "veo-console",
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers=bearer(expired)).status_code == 401


def test_tampered_payload_is_rejected(client: TestClient, tenants: dict) -> None:
    token = access_token_of(login(client, tenants["alice"].email))
    header, payload, signature = token.split(".")
    decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    decoded["roles"] = [Role.SUPER_ADMIN.value]
    swapped = (
        base64.urlsafe_b64encode(json.dumps(decoded).encode()).rstrip(b"=").decode()
    )
    tampered = f"{header}.{swapped}.{signature}"
    assert client.get("/api/auth/me", headers=bearer(tampered)).status_code == 401


def test_role_claim_alone_grants_nothing(client: TestClient, tenants: dict) -> None:
    """A validly-signed token claiming SUPER_ADMIN must still only get DB-backed roles."""
    token = jwt.encode(
        {
            "sub": str(tenants["alice"].id),
            "org": str(tenants["org_a"].id),
            "roles": [Role.SUPER_ADMIN.value],
            "sid": str(uuid.uuid4()),
            "jti": uuid.uuid4().hex,
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(minutes=10)).timestamp()),
            "iss": "veo",
            "aud": "veo-console",
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    response = client.get("/api/auth/me", headers=bearer(token))
    # The session id is fabricated, so this must fail outright rather than resolve.
    assert response.status_code == 401


def test_wrong_audience_is_rejected(client: TestClient, tenants: dict) -> None:
    token = jwt.encode(
        {
            "sub": str(tenants["alice"].id),
            "org": str(tenants["org_a"].id),
            "roles": [Role.ANALYST.value],
            "sid": str(uuid.uuid4()),
            "jti": uuid.uuid4().hex,
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(minutes=10)).timestamp()),
            "iss": "veo",
            "aud": "some-other-service",
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 401


# --------------------------------------------------------------------------- #
# Revocation and role changes take effect
# --------------------------------------------------------------------------- #


def test_removing_a_role_takes_effect_on_the_next_request(
    client: TestClient, tenants: dict, db: Session
) -> None:
    """Roles come from the database, not the token, so revocation is not deferred."""
    token = access_token_of(login(client, tenants["alice"].email))
    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 200

    db.execute(
        delete(RoleAssignment).where(RoleAssignment.user_id == tenants["alice"].id)
    )
    db.commit()

    after = client.get("/api/auth/me", headers=bearer(token))
    if after.status_code == 200:
        assert after.json()["data"]["permissions"] == [], (
            "a user whose roles were removed must hold no permissions"
        )
    else:
        assert after.status_code in {401, 403}


def test_logout_stops_the_session(client: TestClient, tenants: dict) -> None:
    body = login(client, tenants["bob"].email)
    token = access_token_of(body)
    refresh = body["data"].get("refresh_token")

    assert client.post("/api/auth/logout", headers=bearer(token)).status_code in {200, 204}

    if refresh:
        replay = client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert replay.status_code == 401


def test_refresh_rotates_and_the_old_token_dies(client: TestClient, tenants: dict) -> None:
    body = login(client, tenants["alice"].email)
    first = body["data"].get("refresh_token")
    if not first:
        pytest.skip("refresh token is not returned in the body")

    rotated = client.post("/api/auth/refresh", json={"refresh_token": first})
    assert rotated.status_code == 200
    second = rotated.json()["data"]["refresh_token"]
    assert second != first

    replay = client.post("/api/auth/refresh", json={"refresh_token": first})
    assert replay.status_code == 401, "a rotated refresh token must not work again"

    after_reuse = client.post("/api/auth/refresh", json={"refresh_token": second})
    assert after_reuse.status_code == 401, (
        "detecting reuse must burn the whole family, not just the replayed token"
    )


# --------------------------------------------------------------------------- #
# Nothing sensitive leaks
# --------------------------------------------------------------------------- #


def test_no_response_on_the_auth_surface_contains_a_hash_or_secret(
    client: TestClient, tenants: dict
) -> None:
    body = login(client, tenants["alice"].email)
    token = access_token_of(body)
    me = client.get("/api/auth/me", headers=bearer(token))

    for text_body in (json.dumps(body, ensure_ascii=False), me.text):
        assert "$argon2" not in text_body
        assert JWT_SECRET not in text_body
        assert "password_hash" not in text_body
        assert "refresh_token_hash" not in text_body


def test_audit_rows_never_store_the_raw_email_or_password(
    client: TestClient, tenants: dict, db: Session
) -> None:
    login(client, tenants["alice"].email)
    rows = db.execute(text("SELECT detail::text FROM audit_logs")).scalars().all()
    joined = " ".join(rows)
    assert tenants["alice"].email not in joined
    assert PASSWORD not in joined
