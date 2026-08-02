"""공유 결과 DB 저장소 — 실제 PostgreSQL 왕복.

이 파일이 resources 스위트에 사는 이유는 하나다: 여기 conftest 만이 마이그레이션을
head 까지 적용한 실제 DB 엔진을 준다(requires_postgres 자동 표시 포함). 시험 대상은
리소스 라우터가 아니라 :class:`veo.api.public_result_store.DbPublicResultStore` 다.

지키는 성질:
1. 저장한 결과를 **다른 저장소 인스턴스**가 읽을 수 있다 — 재시작 생존이 곧 목적이다.
2. 만료된 행은 걸러지는 게 아니라 읽는 자리에서 지워진다(인메모리와 같은 규칙).
3. 읽어 온 payload 의 result_token 은 비어 있다 — DB 에서 공유 주소를 복원할 수 없다.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session, sessionmaker

from veo.api.public_result_store import DbPublicResultStore
from veo.db.models import PublicSharedResult
from veo.public.schemas import PublicScoreBlock, PublicSeoScanPayload
from veo.public.service import StoredPublicResult

NOW = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)


@pytest.fixture
def scope(session_factory: sessionmaker[Session]):  # type: ignore[no-untyped-def]
    """세션 팩토리를 테스트 DB 에 묶은 session_scope 대역."""

    @contextmanager
    def factory() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    yield factory
    with factory() as db:
        db.execute(delete(PublicSharedResult))


def result(fingerprint: str, *, expires_at: datetime) -> StoredPublicResult:
    return StoredPublicResult(
        fingerprint=fingerprint,
        payload=PublicSeoScanPayload(
            target_url="https://clinic.example/",
            scanned_url_count=1,
            summary_ko="요약",
            score=PublicScoreBlock(
                spec_id="veo.seo.readiness",
                spec_version="1.0.0",
                spec_checksum="abc",
                status="SCORED",
                score=42.0,
                band_id="warn",
                band_label_ko="주의",
                coverage=0.8,
                confidence=0.9,
            ),
            result_token="raw-token-not-for-disk",
            result_expires_at=expires_at,
        ),
        expires_at=expires_at,
    )


def test_a_fresh_store_instance_reads_what_another_wrote(scope) -> None:  # type: ignore[no-untyped-def]
    """저장소 인스턴스가 바뀌어도(=프로세스가 재시작해도) 링크는 살아 있다."""
    DbPublicResultStore(scope=scope).put(
        result("fp-roundtrip", expires_at=NOW + timedelta(days=7))
    )

    read = DbPublicResultStore(scope=scope).get("fp-roundtrip", now=NOW)

    assert read is not None
    assert read.payload.kind == "SEO"
    assert read.payload.target_url == "https://clinic.example/"
    assert read.payload.score.score == 42.0
    # 원문 토큰은 디스크에 없다 — 읽어 와도 되살아나지 않는다.
    assert read.payload.result_token == ""


def test_an_expired_row_is_deleted_on_read(scope) -> None:  # type: ignore[no-untyped-def]
    store = DbPublicResultStore(scope=scope)
    store.put(result("fp-expired", expires_at=NOW - timedelta(seconds=1)))

    assert store.get("fp-expired", now=NOW) is None
    with scope() as db:
        assert db.get(PublicSharedResult, "fp-expired") is None


def test_a_missing_fingerprint_is_none_not_an_error(scope) -> None:  # type: ignore[no-untyped-def]
    assert DbPublicResultStore(scope=scope).get("fp-never-existed", now=NOW) is None
