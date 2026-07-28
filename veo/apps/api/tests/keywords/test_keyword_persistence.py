"""The SQLAlchemy repository, against a real PostgreSQL.

The in-memory repository proves the service's logic. This proves the part that only a
real database can: that ``0``, ``NULL``-because-suppressed, ``NULL``-because-missing and
``NULL``-because-range-bounded survive a write and a read as four distinguishable facts.
A column is nullable and a ``*_quality`` flag sits beside it precisely so this test can
pass; if a future change starts writing 0 for a suppressed value, this is what fails.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, delete
from sqlalchemy.orm import Session, sessionmaker
from tests.keywords.conftest import NOW, make_service
from tests.keywords.naver_fixtures import load

from veo.authz import Principal
from veo.contracts.enums import ProviderState, Role, ValueQuality
from veo.db.models.identity import Organization, Project
from veo.db.models.keywords import (
    KeywordList,
    KeywordMetric,
    KeywordOpportunity,
    KeywordQuery,
    KeywordTrend,
    RelatedKeyword,
)
from veo.keywords.repository import SqlKeywordRepository

DATABASE_URL = os.getenv("VEO_TEST_DATABASE_URL")
API_ROOT = Path(__file__).resolve().parents[2]

#: Without ``VEO_TEST_DATABASE_URL`` the ``engine`` fixture skips every test here.
pytestmark = pytest.mark.requires_postgres


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    if not DATABASE_URL:
        pytest.skip("VEO_TEST_DATABASE_URL is not set")
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

    created = create_engine(DATABASE_URL, future=True)
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    opened = factory()
    try:
        yield opened
    finally:
        opened.rollback()
        opened.close()


@pytest.fixture
def db_organization(db_session: Session) -> Iterator[Organization]:
    slug = f"veo-keyword-test-{uuid.uuid4().hex[:8]}"
    organization = Organization(slug=slug, name=slug, is_active=True, settings={})
    db_session.add(organization)
    db_session.commit()
    try:
        yield organization
    finally:
        db_session.rollback()
        for model in (
            KeywordOpportunity,
            KeywordTrend,
            RelatedKeyword,
            KeywordMetric,
            KeywordList,
            KeywordQuery,
        ):
            db_session.execute(
                delete(model).where(model.organization_id == organization.id)  # type: ignore[attr-defined]
            )
        db_session.execute(delete(Organization).where(Organization.id == organization.id))
        db_session.commit()


@pytest.fixture
def db_project(db_session: Session, db_organization: Organization) -> Iterator[Project]:
    slug = f"kw-{uuid.uuid4().hex[:8]}"
    project = Project(
        organization_id=db_organization.id, slug=slug, name=slug, locale="ko-KR", settings={}
    )
    db_session.add(project)
    db_session.commit()
    try:
        yield project
    finally:
        db_session.rollback()
        db_session.execute(delete(KeywordList).where(KeywordList.project_id == project.id))
        db_session.execute(delete(Project).where(Project.id == project.id))
        db_session.commit()


@pytest.fixture
def db_principal(db_organization: Organization) -> Principal:
    return Principal(
        user_id=uuid.uuid4(),
        organization_id=db_organization.id,
        roles=frozenset({Role.ANALYST}),
        session_id="persistence",
    )


def searchad_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=load("searchad_keywordstool_synthetic.json"))


def test_zero_suppressed_missing_and_range_survive_a_round_trip(
    db_session: Session, db_principal: Principal
) -> None:
    repository = SqlKeywordRepository(db_session)
    service = make_service(repository=repository, searchad_handler=searchad_ok)

    result = service.lookup(
        principal=db_principal,
        keywords=["합성키워드-A", "합성키워드-B", "합성키워드-C", "합성키워드-D"],
        include_trend=False,
    )
    assert result.query_id is not None
    db_session.expire_all()

    reloaded = repository.load_lookup(
        organization_id=db_principal.organization_id, query_id=result.query_id
    )
    assert reloaded is not None
    by_keyword = {metric.normalized_keyword: metric for metric in reloaded.metrics}

    exact = by_keyword["합성키워드-a"]
    assert exact.monthly_pc_searches == 1111
    assert exact.monthly_pc_searches_quality is ValueQuality.EXACT

    zero = by_keyword["합성키워드-b"]
    assert zero.monthly_pc_searches == 0
    assert zero.monthly_pc_searches_quality is ValueQuality.EXACT

    below = by_keyword["합성키워드-c"]
    assert below.monthly_pc_searches is None
    assert below.monthly_pc_searches_quality is ValueQuality.BELOW_PROVIDER_THRESHOLD

    suppressed = by_keyword["합성키워드-d"]
    assert suppressed.monthly_pc_searches is None
    assert suppressed.monthly_pc_searches_quality is ValueQuality.SUPPRESSED_BY_PROVIDER

    # Four rows, four different facts, none of them collapsed into 0.
    facts = {
        (metric.monthly_pc_searches, metric.monthly_pc_searches_quality)
        for metric in by_keyword.values()
    }
    assert len(facts) == 4


def test_the_raw_provider_response_is_kept_beside_the_mapping(
    db_session: Session, db_principal: Principal
) -> None:
    repository = SqlKeywordRepository(db_session)
    service = make_service(repository=repository, searchad_handler=searchad_ok)
    result = service.lookup(
        principal=db_principal, keywords=["합성키워드-C"], include_trend=False
    )
    assert result.query_id is not None

    row = db_session.query(KeywordMetric).filter_by(keyword_query_id=result.query_id).first()
    assert row is not None
    assert row.provider_raw["monthlyPcQcCnt"] == "< 10"
    assert row.raw_response_hash


def test_a_disabled_lookup_writes_a_query_row_and_no_metric_rows(
    db_session: Session, db_principal: Principal
) -> None:
    repository = SqlKeywordRepository(db_session)
    service = make_service(
        repository=repository, searchad_credentials=None, datalab_credentials=None
    )
    result = service.lookup(principal=db_principal, keywords=["합성키워드-A"])
    assert result.query_id is not None

    query_row = db_session.get(KeywordQuery, result.query_id)
    assert query_row is not None
    assert query_row.provider_state == ProviderState.DISABLED_NO_CREDENTIAL.value
    assert query_row.requested_at == NOW
    assert db_session.query(KeywordMetric).filter_by(keyword_query_id=result.query_id).count() == 0
    assert (
        db_session.query(KeywordOpportunity).filter_by(keyword_query_id=result.query_id).count()
        == 0
    )


def test_another_organizations_query_is_invisible(
    db_session: Session, db_principal: Principal
) -> None:
    repository = SqlKeywordRepository(db_session)
    service = make_service(repository=repository, searchad_handler=searchad_ok)
    result = service.lookup(
        principal=db_principal, keywords=["합성키워드-A"], include_trend=False
    )
    assert result.query_id is not None

    assert (
        repository.load_lookup(organization_id=uuid.uuid4(), query_id=result.query_id) is None
    )


def test_keyword_lists_round_trip(
    db_session: Session, db_principal: Principal, db_project: Project
) -> None:
    repository = SqlKeywordRepository(db_session)
    service = make_service(repository=repository)
    created = service.create_list(
        principal=db_principal,
        project_id=db_project.id,
        name="합성 목록",
        description="설명",
        keywords=["합성키워드-A"],
    )
    fetched = service.get_list(principal=db_principal, list_id=created.id)
    assert fetched is not None
    assert fetched.keywords == ("합성키워드-a",)
