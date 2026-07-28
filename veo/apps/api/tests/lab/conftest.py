"""Fixtures for the VEO-LAB scoring-version workflow tests.

Three seams.

*The specification root is a copy.* A package-scoped fixture copies
``packages/scoring-specs`` to a temporary directory, adds the synthetic
``veo.lab_test.readiness`` family and its golden fixtures, and points
``VEO_SCORING_SPECS_DIR`` at the copy for the duration of this package. Nothing under
``packages/`` is written to, and the real published specifications stay loadable because
they were copied along with everything else.

*Authentication is somebody else's package.* These tests never build a token. They
override ``veo.authz.deps.get_principal`` with a box the ``act_as`` fixture swaps.

*The lab router is deliberately not mounted.* ``veo.api.app`` belongs to the integrator,
so the test application is ``create_app()`` plus this one router under the real API
prefix. The fixture is session-scoped so the router is included exactly once.
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
from sqlalchemy import Engine, create_engine, delete
from sqlalchemy.orm import Session, sessionmaker
from tests.lab.support import (
    DATABASE_URL,
    LAB_SPEC_ID,
    PrincipalBox,
    Tenant,
    build_specs_root,
    make_tenant,
)

from veo.api.app import create_app
from veo.authz.deps import get_principal
from veo.authz.errors import AuthenticationError
from veo.authz.principal import Principal
from veo.core.settings import get_settings
from veo.db.models.analysis import Scan, ScanRun, ScoringVersion
from veo.db.models.analysis import ScoreResult as ScoreResultRow
from veo.db.models.identity import AuditLog, Organization, Project, Site, User
from veo.db.session import get_db

API_ROOT = Path(__file__).resolve().parents[2]


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Mark only the tests that actually reach PostgreSQL."""
    skip = pytest.mark.skip(
        reason="set VEO_TEST_DATABASE_URL to run the VEO-LAB tests against PostgreSQL"
    )
    for item in items:
        requested = set(getattr(item, "fixturenames", ()))
        needs_db = bool({"db", "client", "session_factory"} & requested)
        if not needs_db:
            continue
        item.add_marker(pytest.mark.requires_postgres)
        if not DATABASE_URL:
            item.add_marker(skip)


@pytest.fixture(scope="package", autouse=True)
def lab_specs_root(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """Point the spec loader at a copy that also contains the synthetic family."""
    destination = tmp_path_factory.mktemp("veo-lab-specs") / "scoring-specs"
    root = build_specs_root(destination)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("VEO_SCORING_SPECS_DIR", root)
        yield root


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


@pytest.fixture(autouse=True)
def clean_scoring_versions(request: pytest.FixtureRequest) -> Iterator[None]:
    """Remove every synthetic scoring version this test created.

    ``scoring_versions`` is global rather than tenant-scoped, so leftovers from one test
    would become another test's "currently published" baseline.
    """
    if "session_factory" not in request.fixturenames:
        yield
        return
    factory: sessionmaker[Session] = request.getfixturevalue("session_factory")

    def purge() -> None:
        with factory() as session:
            session.execute(
                delete(ScoringVersion).where(ScoringVersion.spec_id.like("veo.lab_test%"))
            )
            session.commit()

    purge()
    yield
    purge()


@pytest.fixture
def tenant(db: Session) -> Iterator[Tenant]:
    created = make_tenant(db, "a")
    yield created
    _purge_tenant(db, created)


@pytest.fixture
def other_tenant(db: Session) -> Iterator[Tenant]:
    created = make_tenant(db, "b")
    yield created
    _purge_tenant(db, created)


def _purge_tenant(db: Session, tenant: Tenant) -> None:
    db.rollback()
    organization_id: uuid.UUID = tenant.organization_id
    user_ids = [
        tenant.lab_admin.user_id,
        tenant.analyst.user_id,
        tenant.viewer.user_id,
    ]
    db.execute(
        delete(ScoreResultRow).where(ScoreResultRow.organization_id == organization_id)
    )
    db.execute(delete(ScanRun).where(ScanRun.organization_id == organization_id))
    db.execute(delete(Scan).where(Scan.organization_id == organization_id))
    db.execute(delete(Site).where(Site.organization_id == organization_id))
    db.execute(delete(Project).where(Project.organization_id == organization_id))
    db.execute(delete(AuditLog).where(AuditLog.organization_id == organization_id))
    if user_ids:
        db.execute(delete(AuditLog).where(AuditLog.actor_user_id.in_(user_ids)))
    db.execute(delete(Organization).where(Organization.id == organization_id))
    if user_ids:
        db.execute(delete(User).where(User.id.in_(user_ids)))
    db.commit()


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
    from veo.lab.router import router as lab_router

    created = create_app()
    created.include_router(lab_router, prefix=get_settings().api_prefix)
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
def lab_spec_id() -> str:
    return LAB_SPEC_ID
