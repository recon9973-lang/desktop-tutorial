"""Fixtures for the report suite.

Two suites live here. The pure ones — snapshot, views, renderers — need nothing but
Python. The router and persistence tests need PostgreSQL, because ``ReportVersion`` is a
JSONB table with a uniqueness constraint that only a real database enforces, and an
immutability guarantee asserted against a real flush.

Authentication belongs to another package, so these tests override
``veo.authz.deps.get_principal`` rather than minting a token.
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
from report_support import API_PREFIX, DATABASE_URL, PrincipalBox, Tenant
from sqlalchemy import Engine, create_engine, delete
from sqlalchemy.orm import Session, sessionmaker

from veo.api.app import create_app
from veo.authz.deps import get_principal
from veo.authz.errors import AuthenticationError
from veo.authz.principal import Principal
from veo.contracts.enums import Role
from veo.db.models.identity import AuditLog, Organization, Project, User
from veo.db.models.observation import Report, ReportVersion
from veo.db.session import get_db
from veo.reports.router import router as reports_router

API_ROOT = Path(__file__).resolve().parents[2]

_POSTGRES_MODULES = frozenset(
    {
        "test_report_router",
        "test_report_immutability",
        "test_report_from_scan",
        "test_shared_report_links",
    }
)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Mark only the modules that actually talk to PostgreSQL.

    The snapshot, view and renderer tests are pure functions of their input and must keep
    running with no database at all — they are the ones that guarantee the three formats
    cannot diverge, and losing them on a laptop without PostgreSQL would be the wrong
    trade.
    """
    skip = pytest.mark.skip(
        reason="set VEO_TEST_DATABASE_URL to run the report persistence tests"
    )
    for item in items:
        if item.module.__name__.rsplit(".", 1)[-1] not in _POSTGRES_MODULES:
            continue
        item.add_marker(pytest.mark.requires_postgres)
        if not DATABASE_URL:
            item.add_marker(skip)


def _migrate_to_head() -> None:
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
    """``create_app()`` plus the report router.

    The router is deliberately not mounted in ``veo.api.app`` — that file belongs to the
    integrator (see ``INTEGRATION_REQUEST.md``). Including it here exercises the real
    error handlers, so a 403 or a 404 in these tests is the one a client would see.
    """
    created = create_app()
    created.include_router(reports_router, prefix=API_PREFIX)
    return created


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
            slug=f"veo-report-{label}-{suffix}",
            name=f"VEO 리포트 테스트 조직 {label}",
            is_active=True,
            settings={},
        )
        db.add(organization)
        users = [
            User(
                email=f"{role}-{suffix}@veo-report-test.invalid",
                display_name=f"{role} {suffix}",
                is_active=True,
            )
            for role in ("analyst", "viewer", "developer")
        ]
        db.add_all(users)
        db.commit()

        project = Project(
            organization_id=organization.id,
            customer_id=None,
            slug=f"project-{suffix}",
            name=f"프로젝트 {suffix}",
            locale="ko-KR",
            settings={},
        )
        db.add(project)
        db.commit()

        organization_ids.append(organization.id)
        user_ids.extend(user.id for user in users)

        def principal(user: User, role: Role) -> Principal:
            return Principal(
                user_id=user.id,
                organization_id=organization.id,
                roles=frozenset({role}),
                session_id=f"session-{suffix}-{role.value}",
                display_name=user.display_name,
            )

        return Tenant(
            organization_id=organization.id,
            project_id=project.id,
            analyst=principal(users[0], Role.ANALYST),
            viewer=principal(users[1], Role.SALES_VIEWER),
            developer=principal(users[2], Role.DEVELOPER),
        )

    yield _make

    db.rollback()
    if organization_ids:
        db.execute(
            delete(ReportVersion).where(ReportVersion.organization_id.in_(organization_ids))
        )
        db.execute(delete(Report).where(Report.organization_id.in_(organization_ids)))
        db.execute(delete(AuditLog).where(AuditLog.organization_id.in_(organization_ids)))
    if user_ids:
        db.execute(delete(AuditLog).where(AuditLog.actor_user_id.in_(user_ids)))
    if organization_ids:
        db.execute(delete(Project).where(Project.organization_id.in_(organization_ids)))
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
