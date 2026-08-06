"""Fixtures for the issue-tracking suite.

Three seams matter here.

*Authentication is somebody else's package.* These tests never mint a token. They
override the FastAPI dependency ``veo.authz.deps.get_principal`` with a fixture that
returns a :class:`~veo.authz.principal.Principal` directly — the supported way to
exercise an authorized route.

*The router is not mounted.* ``veo.api.app`` belongs to the integration maintainer, so
the test application is ``create_app()`` plus ``veo.issues.router`` included under the
real API prefix. When the integrator mounts it, this fixture stops including it a second
time by consulting the generated OpenAPI document — the only honest way to detect a
mounted router on this FastAPI version.

*Only the database-backed modules need PostgreSQL.* The state machine and the fingerprint
are pure functions and are tested without a database, so this package does not carry a
blanket ``requires_postgres`` marker; the modules that need one declare it themselves.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker
from tests.issues.support import DATABASE_URL, PrincipalBox, Tenant

from veo.api.app import create_app
from veo.authz.deps import get_principal
from veo.authz.errors import AuthenticationError
from veo.authz.principal import Principal
from veo.contracts.enums import Role
from veo.db.models.analysis import CheckResult, Scan, ScanRun
from veo.db.models.identity import (
    AuditLog,
    Organization,
    Project,
    RoleAssignment,
    Site,
    URLRecord,
    User,
)
from veo.db.session import get_db
from veo.scoring import CheckStatus, ScoringSpec, latest_published

API_ROOT = Path(__file__).resolve().parents[2]


def _migrate_to_head() -> None:
    """Bring the test database up to head before the first database-backed test runs.

    ``tests/db/test_migrations.py`` downgrades to base in its teardown, so by the time
    this package starts the database may have no tables at all. Re-running the
    migrations — rather than ``Base.metadata.create_all`` — is what keeps
    ``alembic_version`` honest.
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
    if DATABASE_URL is None:
        pytest.skip("VEO_TEST_DATABASE_URL is not set")
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


@pytest.fixture(scope="session")
def seo_spec() -> ScoringSpec:
    return latest_published("veo.seo.readiness")


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
    from veo.issues.router import router as issues_router

    created = create_app()
    prefix = f"{issues_router.prefix}"
    mounted = any(path.startswith(prefix) for path in created.openapi()["paths"])
    if not mounted:
        from veo.core.settings import get_settings

        created.include_router(issues_router, prefix=get_settings().api_prefix)
        # The document was generated a moment ago to answer "is it mounted?"; drop the
        # cache so anything reading it later sees the router that was just added.
        created.openapi_schema = None
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
            slug=f"veo-issues-{label}-{suffix}",
            name=f"VEO 이슈 테스트 조직 {label}",
            is_active=True,
            settings={},
        )
        db.add(organization)

        analyst_user = User(
            email=f"issues-analyst-{suffix}@veo-test.invalid",
            display_name=f"analyst {suffix}",
            is_active=True,
        )
        viewer_user = User(
            email=f"issues-viewer-{suffix}@veo-test.invalid",
            display_name=f"viewer {suffix}",
            is_active=True,
        )
        db.add_all([analyst_user, viewer_user])
        db.commit()

        # Membership is what makes a user assignable inside this organization; without a
        # role assignment the service must treat the id as belonging to nobody it knows.
        db.add_all(
            [
                RoleAssignment(
                    organization_id=organization.id,
                    user_id=analyst_user.id,
                    role=str(Role.ANALYST),
                ),
                RoleAssignment(
                    organization_id=organization.id,
                    user_id=viewer_user.id,
                    role=str(Role.SALES_VIEWER),
                ),
            ]
        )
        db.commit()

        project = Project(
            organization_id=organization.id,
            slug=f"issues-{suffix}",
            name=f"이슈 프로젝트 {label}",
            locale="ko-KR",
            settings={},
        )
        db.add(project)
        db.commit()

        site = Site(
            organization_id=organization.id,
            project_id=project.id,
            origin=f"https://{label}-{suffix}.veo-test.invalid",
            display_name=f"이슈 사이트 {label}",
            is_primary=True,
            crawl_settings={},
        )
        db.add(site)
        db.commit()

        organization_ids.append(organization.id)
        user_ids.extend([analyst_user.id, viewer_user.id])

        return Tenant(
            organization_id=organization.id,
            project_id=project.id,
            site_id=site.id,
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
        # Audit rows outlive their organization by design (SET NULL), so they go first or
        # the cleanup leaves orphans for the next run to trip over.
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
def make_scan_run(db: Session) -> Callable[..., ScanRun]:
    """A finished scan run belonging to one tenant's project."""

    def _make(tenant: Tenant, *, kind: str = "SEO") -> ScanRun:
        scan = Scan(
            organization_id=tenant.organization_id,
            project_id=tenant.project_id,
            site_id=tenant.site_id,
            kind=kind,
            scope="SITE",
            target_url=None,
            configuration={},
            is_active=True,
        )
        db.add(scan)
        db.commit()

        run = ScanRun(
            organization_id=tenant.organization_id,
            scan_id=scan.id,
            surface="CONSOLE",
            status="SUCCEEDED",
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
            collector_version="test-collector/1.0.0",
            device_profile="MOBILE",
            urls_attempted=1,
            urls_collected=1,
            provider_states={},
            partial_reasons=[],
        )
        db.add(run)
        db.commit()
        return run

    return _make


@pytest.fixture
def make_url_record(db: Session) -> Callable[..., URLRecord]:
    """Get-or-create: ``(site_id, normalized_url)`` is unique, and a test that verifies an
    issue twice legitimately re-measures the same page."""

    def _make(tenant: Tenant, normalized_url: str) -> URLRecord:
        db.rollback()
        existing = db.scalars(
            select(URLRecord)
            .where(URLRecord.site_id == tenant.site_id)
            .where(URLRecord.normalized_url == normalized_url)
        ).first()
        if existing is not None:
            return existing
        record = URLRecord(
            organization_id=tenant.organization_id,
            site_id=tenant.site_id,
            normalized_url=normalized_url,
            original_url=normalized_url,
            importance="CONTENT_OR_PRODUCT",
            importance_source="DEFAULT",
        )
        db.add(record)
        db.commit()
        return record

    return _make


@pytest.fixture
def make_check_result(db: Session, seo_spec: ScoringSpec) -> Callable[..., CheckResult]:
    """One persisted check outcome inside a scan run — what a re-measurement looks like.

    **`evaluated_urls` 를 채우는 것이 요점이다.** 저장 경로(`seo/history.py`)가 실제로
    쓰는 칸이 이것이고, 재검증은 여기서 "이번에 어느 주소를 다시 봤는가" 를 읽는다.

    이 픽스처는 한때 `url_record` 를 받아 `url_record_id` 를 채웠다. 그런데 운영에서
    그 칸은 **한 번도 채워진 적이 없다**(실측 2026-08-06: `url_records` 0행,
    `url_record_id` 2,111행 중 0행). 시험이 운영에 없는 데이터를 스스로 만들어
    넣고 통과했고, 그래서 재검증이 **절대 RESOLVED 를 낼 수 없다**는 사실이
    시험에 걸리지 않았다.
    """

    def _make(
        tenant: Tenant,
        run: ScanRun,
        check_id: str,
        status: CheckStatus,
        *,
        urls: Sequence[str] = (),
    ) -> CheckResult:
        check = seo_spec.check(check_id)
        result = CheckResult(
            organization_id=tenant.organization_id,
            scan_run_id=run.id,
            check_id=check_id,
            category_id=seo_spec.category_of(check_id).id,
            status=str(status),
            severity=str(check.severity),
            confidence=1.0,
            affected_weight=1.0,
            evaluated_weight=1.0,
            observed_value={},
            evidence_ids=[],
            # 저장 경로가 쓰는 그대로. 실패한 주소는 `affected_urls`, 이번에 본
            # 주소 전부는 `evaluated_urls` 다.
            affected_urls=(
                list(urls) if status in (CheckStatus.FAIL, CheckStatus.WARNING) else []
            ),
            evaluated_urls=list(urls),
        )
        db.add(result)
        db.commit()
        return result

    return _make


@pytest.fixture
def audit_rows(db: Session) -> Callable[[uuid.UUID], list[AuditLog]]:
    """The audit trail of one organization, oldest first."""

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
