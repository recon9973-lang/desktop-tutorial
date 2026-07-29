"""``veo.seo`` 저장 계층 테스트용 픽스처.

`auth` 스위트와 같은 방식이다 — 바깥 트랜잭션 하나 안에서 돌리고 끝나면 되돌린다.
`join_transaction_mode="create_savepoint"` 라 운영 코드가 평소처럼 `commit()` 을 불러도
세이브포인트만 풀리고 바깥 트랜잭션은 살아 있다.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.orm import Session

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

os.environ.setdefault("VEO_JWT_SECRET", "veo-test-signing-key-do-not-use-anywhere-else")
os.environ["VEO_ENVIRONMENT"] = "test"
if DATABASE_URL:
    os.environ["VEO_DATABASE_URL"] = DATABASE_URL

#: 실패·측정불가 항목이 함께 나오는 픽스처. 둘 다 있어야 저장 규칙을 검증한다.
FIXTURE_NAME = "broken_jsonld"

skip_without_postgres = pytest.mark.skipif(
    not DATABASE_URL,
    reason="set VEO_TEST_DATABASE_URL to run scan-history tests against PostgreSQL",
)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    if not DATABASE_URL:
        pytest.skip("VEO_TEST_DATABASE_URL is not set")
    created = create_engine(DATABASE_URL, future=True)
    present = set(inspect(created).get_table_names())
    missing = {"scans", "scan_runs", "score_results", "check_results", "issues"} - present
    if missing:
        created.dispose()
        pytest.skip(f"veo_test is not migrated; missing {sorted(missing)}")
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
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
def organization(db_session: Session):  # type: ignore[no-untyped-def]
    from veo.db.models.identity import Organization

    row = Organization(
        id=uuid.uuid4(),
        slug=f"org-{uuid.uuid4().hex[:10]}",
        name="테스트 조직",
        is_active=True,
        settings={},
    )
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def other_organization(db_session: Session):  # type: ignore[no-untyped-def]
    from veo.db.models.identity import Organization

    row = Organization(
        id=uuid.uuid4(),
        slug=f"other-{uuid.uuid4().hex[:10]}",
        name="다른 조직",
        is_active=True,
        settings={},
    )
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def principal(organization, user):  # type: ignore[no-untyped-def]
    from veo.authz import Principal
    from veo.contracts.enums import Role

    return Principal(
        user_id=user.id,
        organization_id=organization.id,
        roles=frozenset({Role.ANALYST}),
        session_id=str(uuid.uuid4()),
    )


@pytest.fixture
def other_principal(other_organization):  # type: ignore[no-untyped-def]
    from veo.authz import Principal
    from veo.contracts.enums import Role

    return Principal(
        user_id=uuid.uuid4(),
        organization_id=other_organization.id,
        roles=frozenset({Role.ANALYST}),
        session_id=str(uuid.uuid4()),
    )


@pytest.fixture
def scan_result():  # type: ignore[no-untyped-def]
    """실제 채점기를 통과한 결과 하나.

    합성 페이로드를 손으로 만들지 않는다 — 그러면 저장 계층이 **실제 결과가 아니라 내
    상상**과 맞는지만 확인하게 된다. `broken` 픽스처는 실패 항목과 측정 불가 항목을
    함께 만들어 내므로, 이슈 저장과 측정불가 사유 저장을 한 번에 검증할 수 있다.
    """
    from tests.seo.support import build_context

    import veo.api.app  # noqa: F401  순환 참조를 피하려면 앱을 먼저 올려야 한다
    from veo.seo.service import run_seo_scan

    return run_seo_scan(build_context(FIXTURE_NAME))


@pytest.fixture
def user(db_session, organization):  # type: ignore[no-untyped-def]
    """진단을 실행하는 직원 한 명."""
    from veo.db.models.identity import User

    row = User(
        id=uuid.uuid4(),
        email=f"analyst-{uuid.uuid4().hex[:8]}@example.test",
        display_name="이재훈",
        password_hash="x" * 16,
        is_active=True,
    )
    db_session.add(row)
    db_session.flush()
    return row
