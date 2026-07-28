"""Fixtures for the ``veo.auth`` suite.

Every database test runs inside one outer transaction that is rolled back afterwards, so
a full run leaves ``veo_test`` exactly as it found it. The session is bound to the open
connection with ``join_transaction_mode="create_savepoint"``, which means production code
may call ``commit()`` normally — the commit releases a savepoint instead of ending the
outer transaction.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.orm import Session

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

# Deterministic, test-only signing key. Set before anything imports settings so the
# cached Settings instance already carries it.
TEST_JWT_SECRET = "veo-test-signing-key-do-not-use-anywhere-else"
os.environ.setdefault("VEO_JWT_SECRET", TEST_JWT_SECRET)
os.environ["VEO_ENVIRONMENT"] = "test"
if DATABASE_URL:
    os.environ["VEO_DATABASE_URL"] = DATABASE_URL

from veo.api.app import create_app  # noqa: E402
from veo.auth.hashing import normalize_email  # noqa: E402
from veo.auth.passwords import hash_password  # noqa: E402
from veo.auth.resolver import install_auth  # noqa: E402
from veo.authz import CurrentPrincipal, Permission, Principal, require  # noqa: E402
from veo.contracts.enums import Role  # noqa: E402
from veo.core.settings import get_settings  # noqa: E402
from veo.db.models.identity import Organization, RoleAssignment, User  # noqa: E402
from veo.db.session import get_db  # noqa: E402

skip_without_postgres = pytest.mark.skipif(
    not DATABASE_URL,
    reason="set VEO_TEST_DATABASE_URL to run the auth suite against PostgreSQL",
)

#: Password used by every seeded fixture user.
FIXTURE_PASSWORD = "correct-horse-battery-staple-9f3"
FIXTURE_EMAIL = "Analyst@Example.Test"


@pytest.fixture(scope="session", autouse=True)
def _settings_environment() -> Iterator[None]:
    """Point settings at the test database and the test signing key."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    assert DATABASE_URL is not None
    created = create_engine(DATABASE_URL, future=True)
    present = set(inspect(created).get_table_names())
    missing = {"users", "user_sessions", "login_attempts", "audit_logs"} - present
    if missing:
        created.dispose()
        pytest.skip(f"veo_test is not migrated; missing {sorted(missing)}")
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def session_factory(db: Session):  # type: ignore[no-untyped-def]
    """A ``session_scope``-shaped factory that hands out the test's own session."""

    @contextmanager
    def factory() -> Iterator[Session]:
        yield db
        db.flush()

    return factory


# --------------------------------------------------------------------------- #
# Seed data
# --------------------------------------------------------------------------- #


@pytest.fixture
def organization(db: Session) -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        slug=f"acme-{uuid.uuid4().hex[:10]}",
        name="ACME 마케팅",
        is_active=True,
        settings={},
    )
    db.add(org)
    db.flush()
    return org


@pytest.fixture
def other_organization(db: Session) -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        slug=f"other-{uuid.uuid4().hex[:10]}",
        name="다른 조직",
        is_active=True,
        settings={},
    )
    db.add(org)
    db.flush()
    return org


@pytest.fixture
def user(db: Session, organization: Organization) -> User:
    person = User(
        id=uuid.uuid4(),
        email=normalize_email(FIXTURE_EMAIL),
        display_name="분석가",
        password_hash=hash_password(FIXTURE_PASSWORD),
        is_active=True,
    )
    db.add(person)
    db.flush()
    for role in (Role.ANALYST, Role.SALES_VIEWER):
        db.add(
            RoleAssignment(
                id=uuid.uuid4(),
                organization_id=organization.id,
                user_id=person.id,
                role=role.value,
            )
        )
    db.flush()
    return person


@pytest.fixture
def principal(user: User, organization: Organization) -> Principal:
    return Principal(
        user_id=user.id,
        organization_id=organization.id,
        roles=frozenset({Role.ANALYST}),
        session_id=str(uuid.uuid4()),
    )


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


# --------------------------------------------------------------------------- #
# HTTP surface
# --------------------------------------------------------------------------- #


@pytest.fixture
def app(db: Session, session_factory) -> FastAPI:  # type: ignore[no-untyped-def]
    """The real application factory, with the auth router mounted for the test only.

    Production mounting is the integrator's job; the suite mounts it here so the router
    is exercised through the same envelope, middleware and error handlers as production.
    """
    application = create_app()
    # create_app() already mounts the auth router and installs the default resolver;
    # this re-installs the resolver so it uses the suite's session factory.
    install_auth(application, session_factory=session_factory)

    @application.get("/api/_probe/scan-run", dependencies=[Depends(require(Permission.SCAN_RUN))])
    def _probe_scan_run() -> dict[str, bool]:
        return {"ok": True}

    @application.get("/api/_probe/whoami")
    def _probe_whoami(caller: CurrentPrincipal) -> dict[str, str]:
        return {"session_id": caller.session_id}

    def _override_db() -> Iterator[Session]:
        yield db

    application.dependency_overrides[get_db] = _override_db
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def login_body() -> dict[str, str]:
    return {"email": FIXTURE_EMAIL, "password": FIXTURE_PASSWORD}
