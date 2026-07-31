"""점유율이 **관측에서** 나온다 — 사람이 적어 넣지 않는다.

## 무엇이 틀려 있었나

`sov.py` 는 완성되어 있었다. 그런데 그 입력이 **요청 본문**이었다 — "우리 12건, A병원
7건" 을 사람이 손으로 적어 넣는 구조였다. 손으로 넣은 숫자는 잰 값처럼 보이지만 잰
값이 아니고, 틀려도 아무도 모른다. 대조할 원본이 없기 때문이다(0-A).

게다가 틀리는 방향은 한쪽으로 몰린다. 자기 숫자를 적는 사람은 자기에게 유리하게 적는다.

## 여기서 고정하는 것

1. 실행 하나에서 참여자별 숫자가 **세어진다** — 우리 것과 경쟁사 것이 같은 규칙으로
2. 한 답변이 이름을 여러 번 불러도 **1건**이다
3. 보류된 언급은 분자에 **안 들어간다** — 여기서 세면 우리 쪽만 부푼다
4. 비긴 프롬프트는 승자도 없고 **분모에서도 빠진다**
5. 경쟁사가 없으면 100% 를 만들지 않고 **거부한다**
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from veo.authz.principal import Principal
from veo.competitors.from_observation import (
    ComparisonSetTooSmallError,
    observed_visibility_from_run,
)
from veo.contracts.enums import Role
from veo.db.models.identity import Competitor, Organization, Project
from veo.db.models.observation import (
    AIAnswer,
    AIEngine,
    BrandIdentity,
    Citation,
    EntityMention,
)
from veo.db.models.observation import ObservationRun as ObservationRunRow
from veo.db.models.observation import Prompt as PromptRow
from veo.db.models.observation import PromptSet as PromptSetRow

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(DATABASE_URL is None, reason="VEO_TEST_DATABASE_URL 이 필요합니다"),
]

NOW = datetime(2026, 7, 31, 7, 0, tzinfo=UTC)


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
def db(engine: Engine) -> Iterator[Session]:
    with sessionmaker(bind=engine, expire_on_commit=False, class_=Session)() as session:
        yield session


class World:
    """한 프로젝트, 한 실행, 그리고 그 위에 답변을 놓을 수 있는 자리."""

    def __init__(self, db: Session) -> None:
        self.db = db
        suffix = uuid.uuid4().hex[:8]
        organization = Organization(
            slug=f"sov-{suffix}", name="점유율 테스트 조직", is_active=True, settings={}
        )
        db.add(organization)
        db.flush()
        self.organization_id = organization.id
        self.principal = Principal(
            user_id=uuid.uuid4(),
            organization_id=organization.id,
            roles=frozenset({Role.ANALYST}),
            session_id=uuid.uuid4().hex,
        )

        project = Project(
            organization_id=organization.id,
            slug=f"sov-{suffix}",
            name="점유율 프로젝트",
            locale="ko-KR",
            settings={},
        )
        db.add(project)
        db.flush()
        self.project_id = project.id

        prompt_set = PromptSetRow(
            organization_id=organization.id,
            project_id=project.id,
            name="집합",
            version="1",
            locale="ko-KR",
        )
        db.add(prompt_set)
        db.flush()

        self.engine_row = db.scalars(
            select(AIEngine)
            .where(AIEngine.provider == "OPENAI")
            .where(AIEngine.model == "gpt-5")
            .where(AIEngine.search_mode == "BROWSING")
        ).first()
        if self.engine_row is None:
            self.engine_row = AIEngine(
                provider="OPENAI",
                model="gpt-5",
                search_mode="BROWSING",
                display_name="OPENAI gpt-5",
                is_enabled=True,
                provider_state="ENABLED",
            )
            db.add(self.engine_row)
            db.flush()

        self.run = ObservationRunRow(
            organization_id=organization.id,
            project_id=project.id,
            prompt_set_id=prompt_set.id,
            repetitions_per_prompt=3,
            engines=["OPENAI"],
            competitor_ids=[],
            started_at=NOW,
            finished_at=NOW,
            status="SUCCEEDED",
            executions_attempted=0,
            executions_valid=0,
            executions_planned=0,
            executions_skipped=0,
            is_complete=True,
            skipped_detail={},
            confidence_breakdown={},
            prompts_below_repetition_floor=[],
        )
        db.add(self.run)
        db.flush()
        self._prompt_set_id = prompt_set.id
        self._prompts: dict[str, uuid.UUID] = {}

    def declare(self, key: str, name: str, *, own: bool) -> None:
        db = self.db
        competitor_id = None
        if not own:
            rival = Competitor(
                organization_id=self.organization_id,
                project_id=self.project_id,
                origin=f"https://{key}.example",
                display_name=name,
                brand_aliases={},
            )
            db.add(rival)
            db.flush()
            competitor_id = rival.id
        db.add(
            BrandIdentity(
                organization_id=self.organization_id,
                project_id=self.project_id,
                competitor_id=competitor_id,
                entity_key=key,
                display_name=name,
                aliases=[],
                address_terms=[],
                phone_numbers=[],
                distinguishing_terms=[],
                own_domains=[f"{key}.example"],
                is_active=True,
            )
        )
        db.flush()

    def prompt(self, label: str) -> uuid.UUID:
        if label not in self._prompts:
            row = PromptRow(
                organization_id=self.organization_id,
                prompt_set_id=self._prompt_set_id,
                text=f"합성 질문 {label}",
                intent="DEFINITION",
                funnel="PROBLEM_AWARE",
                subject_type="NON_BRAND",
                business_importance=1,
                locale="ko-KR",
            )
            self.db.add(row)
            self.db.flush()
            self._prompts[label] = row.id
        return self._prompts[label]

    def answer(
        self,
        prompt_label: str,
        *,
        mentions: dict[str, int] | None = None,
        pending: tuple[str, ...] = (),
        own_citation: bool = False,
    ) -> None:
        """답변 한 건과 그 안에서 확인된 브랜드들."""
        row = AIAnswer(
            organization_id=self.organization_id,
            observation_run_id=self.run.id,
            prompt_id=self.prompt(prompt_label),
            ai_engine_id=self.engine_row.id,
            repetition_index=1,
            model_version="gpt-5-2026-05-01",
            search_mode="BROWSING",
            account_state="ANONYMOUS",
            locale="ko-KR",
            executed_at=NOW,
            is_valid_execution=True,
            raw_answer_storage_key=f"veo-answer://sov/{uuid.uuid4().hex}.json",
            raw_answer_hash="d" * 64,
            citation_support="STRUCTURED",
        )
        self.db.add(row)
        self.db.flush()

        for key, occurrences in (mentions or {}).items():
            self.db.add(
                EntityMention(
                    organization_id=self.organization_id,
                    ai_answer_id=row.id,
                    entity_key=key,
                    is_own_brand=key == "ours",
                    raw_occurrence_count=occurrences,
                    match_confidence=0.9,
                    needs_human_disambiguation=False,
                    review_state="NOT_REVIEWED",
                )
            )
        for key in pending:
            self.db.add(
                EntityMention(
                    organization_id=self.organization_id,
                    ai_answer_id=row.id,
                    entity_key=key,
                    is_own_brand=key == "ours",
                    raw_occurrence_count=1,
                    match_confidence=0.0,
                    needs_human_disambiguation=True,
                    review_state="PENDING_REVIEW",
                )
            )
        if own_citation:
            self.db.add(
                Citation(
                    organization_id=self.organization_id,
                    ai_answer_id=row.id,
                    url="https://ours.example/page",
                    domain="ours.example",
                    position=1,
                    is_own_domain=True,
                )
            )
        self.db.flush()


@pytest.fixture
def world(db: Session) -> World:
    made = World(db)
    made.declare("ours", "온담한의원", own=True)
    made.declare("rival-a", "가나한의원", own=False)
    return made


class TestTheNumbersAreCountedNotTyped:
    def test_each_participant_is_counted_from_the_run(self, world: World) -> None:
        world.answer("q1", mentions={"ours": 1, "rival-a": 1})
        world.answer("q2", mentions={"ours": 1})
        world.answer("q3", mentions={"rival-a": 1})
        world.db.commit()

        observed = observed_visibility_from_run(world.db, world.principal, world.run.id)

        counts = {p.key: p.mentioned_answer_count for p in observed.participants}
        assert counts == {"ours": 2, "rival-a": 2}
        assert observed.observed_answer_count == 3

    def test_repeating_a_name_in_one_answer_is_still_one(self, world: World) -> None:
        """되풀이가 노출을 늘리지 않는다. 세면 모든 하위 비율이 함께 부푼다."""
        world.answer("q1", mentions={"ours": 7})
        world.db.commit()

        observed = observed_visibility_from_run(world.db, world.principal, world.run.id)

        ours = next(p for p in observed.participants if p.is_own_brand)
        assert ours.mentioned_answer_count == 1

    def test_a_held_mention_is_not_counted(self, world: World) -> None:
        """보류를 세면 **우리 쪽만** 부푼다 — 경쟁사는 보통 확정되기 때문이다."""
        world.answer("q1", pending=("ours",))
        world.db.commit()

        observed = observed_visibility_from_run(world.db, world.principal, world.run.id)

        ours = next(p for p in observed.participants if p.is_own_brand)
        assert ours.mentioned_answer_count == 0

    def test_our_citation_needs_the_mention_too(self, world: World) -> None:
        world.answer("q1", mentions={"ours": 1}, own_citation=True)
        world.db.commit()

        observed = observed_visibility_from_run(world.db, world.principal, world.run.id)

        ours = next(p for p in observed.participants if p.is_own_brand)
        assert ours.cited_answer_count == 1


class TestWhoWonAPrompt:
    def test_the_participant_named_in_more_answers_wins(self, world: World) -> None:
        world.answer("q1", mentions={"ours": 1})
        world.answer("q1", mentions={"ours": 1})
        world.answer("q1", mentions={"rival-a": 1})
        world.db.commit()

        observed = observed_visibility_from_run(world.db, world.principal, world.run.id)

        wins = {p.key: p.won_prompt_count for p in observed.participants}
        assert wins == {"ours": 1, "rival-a": 0}
        assert observed.decided_prompt_count == 1

    def test_a_tie_is_nobody_s_win_and_leaves_the_denominator(self, world: World) -> None:
        """비긴 것을 분모에 남겨 두면 비길수록 모두의 승률이 내려간다."""
        world.answer("q1", mentions={"ours": 1, "rival-a": 1})
        world.db.commit()

        observed = observed_visibility_from_run(world.db, world.principal, world.run.id)

        assert observed.decided_prompt_count == 0
        assert all(p.won_prompt_count == 0 for p in observed.participants)


class TestRefusingToInventAComparison:
    def test_no_competitors_means_no_share_of_voice(self, db: Session) -> None:
        """참여자가 우리뿐이면 모든 점유율이 100% 다. 그것은 측정이 아니다."""
        alone = World(db)
        alone.declare("ours", "온담한의원", own=True)
        alone.answer("q1", mentions={"ours": 1})
        db.commit()

        with pytest.raises(ComparisonSetTooSmallError, match="경쟁사를 먼저 등록"):
            observed_visibility_from_run(db, alone.principal, alone.run.id)

    def test_another_organization_cannot_read_the_run(self, world: World) -> None:
        world.answer("q1", mentions={"ours": 1})
        world.db.commit()
        stranger = Principal(
            user_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            roles=frozenset({Role.ANALYST}),
            session_id=uuid.uuid4().hex,
        )

        with pytest.raises(LookupError):
            observed_visibility_from_run(world.db, stranger, world.run.id)
