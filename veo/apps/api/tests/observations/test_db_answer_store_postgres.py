"""원문 답변이 **다음 배포에서도 살아 있는가.**

이 파일이 DB 를 요구하는 이유가 그 질문 자체다. 메모리나 임시 폴더에 대고 시험하면
"저장된다" 까지만 확인되고, 정작 알고 싶은 것 — 프로세스가 죽었다 살아나도 남는가 —
은 확인되지 않는다.

## 왜 이것이 중요한가

`ai_answers` 행에는 저장 키와 해시만 남는다. 원문은 민감해서 본 테이블에 넣지 않는다.
그래서 원문이 사라지면 행은 남는데 가리킬 대상이 없고, **"이 판정의 근거를 보여 달라"
에 답할 수 없다.** 그때 그 관측은 근거가 아니라 주장이 된다(0-A).

실제로 그 상태였다. 답변은 컨테이너 로컬 디스크에만 있었고, 배포 환경의 파일시스템은
재배포마다 초기화된다.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, update
from sqlalchemy.orm import Session, sessionmaker

from veo.db.models.identity import Organization
from veo.db.models.observation import AnswerDocument
from veo.observations.answer_store import AnswerNotFoundError, AnswerTamperedError
from veo.observations.db_answer_store import DatabaseAnswerStore
from veo.observations.providers.base import CitationSupport, CostBasis
from veo.observations.providers.storage import AnswerRecordKey, RecordedAnswer

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(
        DATABASE_URL is None,
        reason="VEO_TEST_DATABASE_URL 을 설정해야 보존 여부를 확인할 수 있습니다",
    ),
]

SYNTHETIC = "[합성 응답 — 실제 AI 답변 아님]"


def _answer(text: str = f"{SYNTHETIC} 온담한의원을 추천합니다.") -> RecordedAnswer:
    return RecordedAnswer(
        engine="OPENAI",
        model="gpt-5",
        model_version="gpt-5-2026-05-01",
        text=text,
        citations=("https://example.test/a",),
        citation_support=CitationSupport.STRUCTURED,
        latency_ms=1200,
        cost_usd=0.0031,
        cost_basis=CostBasis.CALCULATED_FROM_USAGE,
        input_tokens=100,
        output_tokens=200,
        executed_at=datetime(2026, 7, 31, 4, 0, tzinfo=UTC),
    )


KEY = AnswerRecordKey(prompt_id="q1", conditions_fingerprint="fp1", attempt=1)


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    assert DATABASE_URL is not None
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(config, "head")

    created = create_engine(DATABASE_URL, future=True)
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture
def factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


@pytest.fixture
def organization_id(factory: sessionmaker[Session]) -> uuid.UUID:
    suffix = uuid.uuid4().hex[:8]
    with factory() as session:
        organization = Organization(
            slug=f"veo-store-{suffix}", name="보관 테스트 조직", is_active=True, settings={}
        )
        session.add(organization)
        session.commit()
        return organization.id


class TestSurvivingARestart:
    def test_an_answer_written_in_one_session_is_readable_in_another(
        self, factory: sessionmaker[Session], organization_id: uuid.UUID
    ) -> None:
        """세션을 갈아 끼우는 것이 여기서는 "프로세스가 다시 떴다" 를 뜻한다.

        파일 저장소는 이 시험을 통과하지만 **다른 기계·다른 컨테이너**에서는 통과하지
        못한다. DB 는 그 자리에 있다.
        """
        with factory() as writer:
            DatabaseAnswerStore(session=writer, organization_id=organization_id).put(
                KEY, _answer()
            )
            writer.commit()

        with factory() as reader:
            recovered = DatabaseAnswerStore(
                session=reader, organization_id=organization_id
            ).read(KEY.ref)

        assert recovered.text.startswith(SYNTHETIC)
        assert recovered.citations == ("https://example.test/a",)
        assert recovered.cost_usd == 0.0031

    def test_the_pointer_the_run_row_keeps_is_enough_to_find_it(
        self, factory: sessionmaker[Session], organization_id: uuid.UUID
    ) -> None:
        """`ai_answers` 가 들고 있는 것은 이 두 값뿐이다. 그것으로 되찾을 수 있어야 한다."""
        with factory() as writer:
            stored = DatabaseAnswerStore(
                session=writer, organization_id=organization_id
            ).put(KEY, _answer())
            writer.commit()

        with factory() as reader:
            recovered = DatabaseAnswerStore(
                session=reader, organization_id=organization_id
            ).read(stored.ref)

        assert hashlib.sha256(recovered.to_bytes()).hexdigest() == stored.sha256


class TestRefusingToVouchForSomethingChanged:
    def test_a_tampered_body_is_refused_rather_than_returned(
        self, factory: sessionmaker[Session], organization_id: uuid.UUID
    ) -> None:
        """바뀐 것을 근거처럼 돌려주는 것보다 못 읽는 편이 낫다."""
        with factory() as writer:
            DatabaseAnswerStore(session=writer, organization_id=organization_id).put(
                KEY, _answer()
            )
            writer.commit()

        with factory() as vandal:
            vandal.execute(
                update(AnswerDocument)
                .where(AnswerDocument.organization_id == organization_id)
                .values(body=b'{"format":"veo.observations.answer.v1"}')
            )
            vandal.commit()

        with factory() as reader:
            store = DatabaseAnswerStore(session=reader, organization_id=organization_id)
            with pytest.raises(AnswerTamperedError):
                store.read(KEY.ref)

    def test_an_unknown_pointer_is_not_found_rather_than_empty(
        self, factory: sessionmaker[Session], organization_id: uuid.UUID
    ) -> None:
        """빈 답변을 돌려주면 "AI 가 아무 말도 안 했다" 로 읽힌다."""
        with factory() as reader:
            store = DatabaseAnswerStore(session=reader, organization_id=organization_id)
            with pytest.raises(AnswerNotFoundError):
                store.read("veo-answer://없는/키/0001.json")


class TestOneAnswerPerAttempt:
    def test_writing_the_same_attempt_twice_does_not_replace_the_first(
        self, factory: sessionmaker[Session], organization_id: uuid.UUID
    ) -> None:
        """관측은 되돌릴 수 없는 기록이다. 두 번째 실행이 첫 번째를 지우면 안 된다."""
        with factory() as writer:
            store = DatabaseAnswerStore(session=writer, organization_id=organization_id)
            first = store.put(KEY, _answer("첫 번째 답변"))
            second = store.put(KEY, _answer("두 번째 답변"))
            writer.commit()

        assert first.sha256 == second.sha256

        with factory() as reader:
            recovered = DatabaseAnswerStore(
                session=reader, organization_id=organization_id
            ).read(KEY.ref)
        assert recovered.text == "첫 번째 답변"

    def test_find_reports_work_already_recorded(
        self, factory: sessionmaker[Session], organization_id: uuid.UUID
    ) -> None:
        with factory() as writer:
            store = DatabaseAnswerStore(session=writer, organization_id=organization_id)
            assert store.find(KEY) is None
            store.put(KEY, _answer())
            writer.commit()

        with factory() as reader:
            store = DatabaseAnswerStore(session=reader, organization_id=organization_id)
            assert store.find(KEY) is not None


class TestTenantIsolation:
    def test_another_organization_cannot_read_the_answer(
        self, factory: sessionmaker[Session], organization_id: uuid.UUID
    ) -> None:
        """원문은 고객 자료다. 저장 키가 같아도 남의 조직 것은 없는 것이다."""
        with factory() as writer:
            DatabaseAnswerStore(session=writer, organization_id=organization_id).put(
                KEY, _answer()
            )
            writer.commit()

        stranger = uuid.uuid4()
        with factory() as reader:
            store = DatabaseAnswerStore(session=reader, organization_id=stranger)
            assert store.find(KEY) is None
            with pytest.raises(AnswerNotFoundError):
                store.read(KEY.ref)
