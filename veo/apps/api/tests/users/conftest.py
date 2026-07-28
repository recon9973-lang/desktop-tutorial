"""Two organizations and a signed-in administrator in each.

Two, always — a member-management suite with one tenant proves nothing about the rule
that matters most, which is that an administrator of one agency cannot see, name, or
touch a person in another.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session

from veo.api.app import create_app
from veo.auth.passwords import hash_password
from veo.authz import Principal
from veo.authz.deps import get_optional_principal, get_principal
from veo.contracts.enums import Role
from veo.db.models.identity import Organization, RoleAssignment, User
from veo.db.session import get_db

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

OWNER_PASSWORD = "administrator-password-2026"

_TABLES = ("user_invitations", "user_sessions", "role_assignments", "users", "organizations")


@dataclass(frozen=True)
class Tenant:
    organization: Organization
    admin: User
    principal: Principal


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    if DATABASE_URL is None:
        pytest.skip("VEO_TEST_DATABASE_URL is not set")
    created = create_engine(DATABASE_URL, future=True)
    present = set(inspect(created).get_table_names())
    missing = set(_TABLES) - present
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
    for table in _TABLES:
        session.execute(text(f"DELETE FROM {table}"))  # noqa: S608 — fixed identifiers
    session.flush()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def _make_tenant(db: Session, *, slug: str, name: str, email: str) -> Tenant:
    organization = Organization(
        id=uuid.uuid4(), slug=slug, name=name, is_active=True, settings={}
    )
    admin = User(
        id=uuid.uuid4(),
        email=email,
        display_name=f"{name} 관리자",
        password_hash=hash_password(OWNER_PASSWORD),
        is_active=True,
    )
    db.add_all([organization, admin])
    db.flush()
    db.add(
        RoleAssignment(
            id=uuid.uuid4(),
            organization_id=organization.id,
            user_id=admin.id,
            role=Role.SUPER_ADMIN.value,
        )
    )
    db.flush()
    return Tenant(
        organization=organization,
        admin=admin,
        principal=Principal(
            user_id=admin.id,
            organization_id=organization.id,
            roles=(Role.SUPER_ADMIN,),
            session_id=str(uuid.uuid4()),
        ),
    )


@pytest.fixture
def venom(db: Session) -> Tenant:
    return _make_tenant(db, slug="venom", name="베놈", email="admin@venom.test")


@pytest.fixture
def rival(db: Session) -> Tenant:
    return _make_tenant(db, slug="rival", name="경쟁대행사", email="admin@rival.test")


@pytest.fixture
def app(db: Session) -> FastAPI:
    application = create_app()
    application.dependency_overrides[get_db] = lambda: db
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as running:
        yield running


@pytest.fixture
def act_as(app: FastAPI):  # type: ignore[no-untyped-def]
    """Sign a request in as a given principal, without minting a real token."""

    def _act_as(principal: Principal | None) -> None:
        if principal is None:
            app.dependency_overrides.pop(get_principal, None)
            app.dependency_overrides.pop(get_optional_principal, None)
            return
        app.dependency_overrides[get_principal] = lambda: principal
        app.dependency_overrides[get_optional_principal] = lambda: principal

    return _act_as
