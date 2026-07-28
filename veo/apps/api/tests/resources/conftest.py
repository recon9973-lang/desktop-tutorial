"""Fixtures for the Phase 1 resource routers (organizations, customers, projects, sites).

Two seams matter here.

*Authentication is somebody else's package.* These tests never build a token. They
override the FastAPI dependency ``veo.authz.deps.get_principal`` with a fixture that
returns a :class:`~veo.authz.principal.Principal` constructed directly, which is the
supported way to exercise an authorized route before the auth worker lands.

*The routers are not mounted yet.* The integrator owns ``veo.api.app``, so the test app
is ``create_app()`` plus the four routers included under the real API prefix. Once the
integrator mounts them the fixture keeps working — it checks before including, so the
paths are never registered twice.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker
from tests.resources.support import DATABASE_URL, PrincipalBox, Tenant

from veo.api.app import create_app
from veo.authz.deps import get_principal
from veo.authz.errors import AuthenticationError
from veo.authz.principal import Principal
from veo.contracts.enums import Role
from veo.db.models.identity import AuditLog, Organization, User
from veo.db.session import get_db


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Every test in this package talks to PostgreSQL — mark them all in one place."""
    skip = pytest.mark.skip(
        reason="set VEO_TEST_DATABASE_URL to run resource tests against PostgreSQL"
    )
    for item in items:
        item.add_marker(pytest.mark.requires_postgres)
        if not DATABASE_URL:
            item.add_marker(skip)


API_ROOT = Path(__file__).resolve().parents[2]


def _migrate_to_head() -> None:
    """Bring the test database up to head before the first resource test runs.

    ``tests/db/test_migrations.py`` downgrades to base in its teardown and collects
    before this package does, so by the time these tests start the database may have no
    tables at all. Re-running the migrations — rather than ``Base.metadata.create_all``
    — is what keeps ``alembic_version`` honest: a schema created behind Alembic's back
    leaves the version table at base while the tables exist, and the *next* run of the
    migration tests then fails with ``DuplicateTable``.
    """
    assert DATABASE_URL is not None
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "alembic"))
    previous = os.environ.get("VEO_DATABASE_URL")
    os.environ["VEO_DATABASE_URL"] = DATABASE_URL
    try:
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("VEO_DATABASE_URL", None)
        else:
            os.environ["VEO_DATABASE_URL"] = previous


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    assert DATABASE_URL is not None
    _migrate_to_head()
    created = create_engine(DATABASE_URL, future=True)
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture(scope="session")
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """A session for arranging rows and asserting on them, separate from the request's."""
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def principal_box() -> PrincipalBox:
    return PrincipalBox()


@pytest.fixture
def act_as(principal_box: PrincipalBox) -> Callable[[Principal], None]:
    def _act_as(principal: Principal) -> None:
        principal_box.current = principal

    return _act_as


@pytest.fixture(scope="session")
def app(engine: Engine) -> FastAPI:
    # create_app() mounts these routers. Re-including them here behind a routes-based
    # guard cannot work: on this FastAPI version an included router is one
    # `_IncludedRouter` entry with `path=None`, so the guard never matches and the
    # routers get mounted twice.
    return create_app()


@pytest.fixture
def client(
    app: FastAPI, session_factory: sessionmaker[Session], principal_box: PrincipalBox
) -> Iterator[TestClient]:
    def override_db() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def override_principal() -> Principal:
        if principal_box.current is None:
            raise AuthenticationError("no principal set; call act_as(...) first")
        return principal_box.current

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_principal] = override_principal
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def make_tenant(db: Session) -> Iterator[Callable[[str], Tenant]]:
    organization_ids: list[uuid.UUID] = []
    user_ids: list[uuid.UUID] = []

    def _make(label: str) -> Tenant:
        suffix = uuid.uuid4().hex[:8]
        organization = Organization(
            slug=f"veo-test-{label}-{suffix}",
            name=f"VEO 테스트 조직 {label}",
            is_active=True,
            settings={},
        )
        db.add(organization)

        analyst_user = User(
            email=f"analyst-{suffix}@veo-test.invalid",
            display_name=f"analyst {suffix}",
            is_active=True,
        )
        viewer_user = User(
            email=f"viewer-{suffix}@veo-test.invalid",
            display_name=f"viewer {suffix}",
            is_active=True,
        )
        db.add_all([analyst_user, viewer_user])
        db.commit()

        organization_ids.append(organization.id)
        user_ids.extend([analyst_user.id, viewer_user.id])

        return Tenant(
            organization_id=organization.id,
            slug=organization.slug,
            name=organization.name,
            analyst=Principal(
                user_id=analyst_user.id,
                organization_id=organization.id,
                roles=frozenset({Role.ANALYST}),
                session_id=f"session-{suffix}-analyst",
                display_name=analyst_user.display_name,
            ),
            viewer=Principal(
                user_id=viewer_user.id,
                organization_id=organization.id,
                roles=frozenset({Role.SALES_VIEWER}),
                session_id=f"session-{suffix}-viewer",
                display_name=viewer_user.display_name,
            ),
        )

    yield _make

    db.rollback()
    if organization_ids:
        # Audit rows outlive their organization by design (SET NULL), so they have to go
        # first or the cleanup leaves orphans behind for the next run to trip over.
        db.execute(delete(AuditLog).where(AuditLog.organization_id.in_(organization_ids)))
    if user_ids:
        db.execute(delete(AuditLog).where(AuditLog.actor_user_id.in_(user_ids)))
    if organization_ids:
        db.execute(delete(Organization).where(Organization.id.in_(organization_ids)))
    if user_ids:
        db.execute(delete(User).where(User.id.in_(user_ids)))
    db.commit()


@pytest.fixture
def org_a(make_tenant: Callable[[str], Tenant]) -> Tenant:
    return make_tenant("a")


@pytest.fixture
def org_b(make_tenant: Callable[[str], Tenant]) -> Tenant:
    return make_tenant("b")


@pytest.fixture
def audit_rows(db: Session) -> Callable[[uuid.UUID], list[AuditLog]]:
    """The audit trail of one organization, oldest first.

    ``db.rollback()`` first: the request wrote through a different session, and this one
    would otherwise keep serving the snapshot it opened before that commit.
    """

    def _rows(organization_id: uuid.UUID) -> list[AuditLog]:
        db.rollback()
        return list(
            db.scalars(
                select(AuditLog)
                .where(AuditLog.organization_id == organization_id)
                .order_by(AuditLog.created_at, AuditLog.action)
            )
        )

    return _rows
