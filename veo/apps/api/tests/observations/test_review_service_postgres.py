"""검수 — **재기동해도, 서버가 두 대여도** 같은 건을 두 사람이 판정하지 않는다.

이 파일이 DB 를 요구하는 이유가 그 문장이다. 인메모리 큐로 시험하면 "점유가 된다"
까지만 확인되고, 정작 알고 싶은 것 — 프로세스가 둘일 때 어떻게 되는가 — 은 확인되지
않는다. 실제로 그 상태였다: `review/queue.py` 의 점유는 전부 프로세스 메모리에 있었고,
서버가 두 대면 둘 다 자기 쪽에서 "내가 점유했다" 를 보므로 **아무도 충돌을 모른다.**

여기서 고정하는 것 넷.

1. 맡지 않은 건은 판정할 수 없다 — 상태 기계가 그 간선을 선언하지 않았다
2. 다른 사람이 맡은 건은 뺏을 수 없다 (409), 다만 오래 방치되면 풀린다
3. **사람의 결론이 자동 판정을 지우지 않는다** — 어긋난 경우까지 나란히 남는다
4. 무엇을 했든 감사 로그에 남는다
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from veo.authz.principal import Principal
from veo.contracts.enums import Role
from veo.db.models.identity import AuditLog, Organization, Project, User
from veo.db.models.observation import (
    AIAnswer,
    AIEngine,
)
from veo.db.models.observation import (
    ClaimAssessment as ClaimAssessmentRow,
)
from veo.db.models.observation import (
    ObservationRun as ObservationRunRow,
)
from veo.db.models.observation import (
    Prompt as PromptRow,
)
from veo.db.models.observation import (
    PromptSet as PromptSetRow,
)
from veo.observations import review_service
from veo.observations.findings import assessment_from_held_mention, new_assessment_row
from veo.observations.review.decisions import (
    IllegalReviewTransitionError,
    RejectionReason,
    ReviewStage,
    open_review,
)

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(
        DATABASE_URL is None,
        reason="VEO_TEST_DATABASE_URL 을 설정해야 점유 충돌을 확인할 수 있습니다",
    ),
]

NOW = datetime(2026, 7, 31, 5, 0, tzinfo=UTC)
SYNTHETIC = "[합성 응답 — 실제 AI 답변 아님]"
HASH = "a" * 64


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
def db(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as session:
        yield session


@pytest.fixture
def world(db: Session) -> tuple[Principal, Principal, uuid.UUID]:
    """한 조직, 검수자 둘, 그리고 검수 대기 판정 하나."""
    suffix = uuid.uuid4().hex[:8]
    organization = Organization(
        slug=f"review-{suffix}", name="검수 테스트 조직", is_active=True, settings={}
    )
    db.add(organization)
    db.flush()

    people = []
    for who in ("first", "second"):
        user = User(
            email=f"{who}-{suffix}@example.invalid",
            display_name=f"검수자 {who}",
            password_hash="x",
            is_active=True,
        )
        db.add(user)
        people.append(user)
    db.flush()

    project = Project(
        organization_id=organization.id,
        slug=f"p-{suffix}",
        name="검수 프로젝트",
        locale="ko-KR",
        settings={},
    )
    db.add(project)
    db.flush()

    prompt_set = PromptSetRow(
        organization_id=organization.id,
        project_id=project.id,
        name="집합",
        version="1",
        locale="ko-KR",
    )
    db.add(prompt_set)
    db.flush()
    prompt = PromptRow(
        organization_id=organization.id,
        prompt_set_id=prompt_set.id,
        text="합성 질문입니다.",
        intent="DEFINITION",
        funnel="PROBLEM_AWARE",
        subject_type="NON_BRAND",
        business_importance=1,
        locale="ko-KR",
    )
    # `ai_engines` 는 조직에 묶이지 않는 전역 표이고 (provider, model, search_mode) 가
    # 유일하다. 다른 시험이 이미 만들어 두었으면 그것을 쓴다.
    ai_engine = db.scalars(
        select(AIEngine)
        .where(AIEngine.provider == "OPENAI")
        .where(AIEngine.model == "gpt-5")
        .where(AIEngine.search_mode == "BROWSING")
    ).first()
    if ai_engine is None:
        ai_engine = AIEngine(
            provider="OPENAI",
            model="gpt-5",
            search_mode="BROWSING",
            display_name="OPENAI gpt-5",
            is_enabled=True,
            provider_state="ENABLED",
        )
        db.add(ai_engine)
        db.flush()
    run = ObservationRunRow(
        organization_id=organization.id,
        project_id=project.id,
        prompt_set_id=prompt_set.id,
        repetitions_per_prompt=3,
        engines=["OPENAI"],
        competitor_ids=[],
        started_at=NOW,
        finished_at=NOW,
        status="SUCCEEDED",
        executions_attempted=1,
        executions_valid=1,
        executions_planned=1,
        executions_skipped=0,
        is_complete=True,
        skipped_detail={},
        confidence_breakdown={},
        prompts_below_repetition_floor=[],
    )
    db.add_all([prompt, run])
    db.flush()

    answer = AIAnswer(
        organization_id=organization.id,
        observation_run_id=run.id,
        prompt_id=prompt.id,
        ai_engine_id=ai_engine.id,
        repetition_index=1,
        model_version="gpt-5-2026-05-01",
        search_mode="BROWSING",
        account_state="ANONYMOUS",
        locale="ko-KR",
        executed_at=NOW,
        is_valid_execution=True,
        raw_answer_storage_key="veo-answer://synthetic/0001.json",
        raw_answer_hash=HASH,
        citation_support="STRUCTURED",
    )
    db.add(answer)
    db.flush()

    review = open_review(
        assessment_from_held_mention(
            answer_id=answer.id,
            answer_ref=answer.raw_answer_storage_key or "",
            answer_hash=HASH,
            span_start=10,
            quoted_text="온담한의원",
            reasons_ko=("이름 앞뒤에 다른 한글이 붙어 있습니다.",),
            decided_at=NOW,
        )
    )
    row = new_assessment_row(
        review, organization_id=organization.id, answer_id=answer.id
    )
    db.add(row)
    db.commit()

    def principal_for(user: User) -> Principal:
        return Principal(
            user_id=user.id,
            organization_id=organization.id,
            roles=frozenset({Role.ANALYST}),
            session_id=uuid.uuid4().hex,
        )

    return principal_for(people[0]), principal_for(people[1]), row.id


class TestNobodyDecidesWhatTheyHaveNotPickedUp:
    def test_deciding_without_claiming_is_refused(
        self, db: Session, world: tuple[Principal, Principal, uuid.UUID]
    ) -> None:
        """`PENDING_REVIEW → CONFIRMED` 간선은 선언되어 있지 않다.

        착수를 건너뛸 수 있으면 "원문을 열어 보지 않고 확정" 이 가능해진다. 그 확정은
        고객 문서에 실린다.
        """
        first, _second, assessment_id = world

        with pytest.raises(IllegalReviewTransitionError):
            review_service.decide(
                db, first, assessment_id, target=ReviewStage.CONFIRMED, now=NOW
            )

    def test_claiming_puts_it_in_front_of_a_person(
        self, db: Session, world: tuple[Principal, Principal, uuid.UUID]
    ) -> None:
        first, _second, assessment_id = world

        moved = review_service.claim(db, first, assessment_id, now=NOW)
        db.commit()

        assert moved.stage is ReviewStage.UNDER_REVIEW
        row = db.get(ClaimAssessmentRow, assessment_id)
        assert row is not None
        assert row.claimed_by == first.user_id
        # 아직 판단하지 않았다. 이 둘을 합치면 착수만 한 건이 검수 완료로 읽힌다.
        assert row.reviewed_by is None
        assert row.review_state == "PENDING_REVIEW"


class TestTwoReviewersOnOneFinding:
    def test_a_second_reviewer_cannot_take_a_held_item(
        self, db: Session, world: tuple[Principal, Principal, uuid.UUID]
    ) -> None:
        """인메모리 큐로는 확인할 수 없던 것. 서버가 두 대면 둘 다 통과했다."""
        first, second, assessment_id = world
        review_service.claim(db, first, assessment_id, now=NOW)
        db.commit()

        with pytest.raises(review_service.ReviewConflictError):
            review_service.claim(db, second, assessment_id, now=NOW)

    def test_the_conflict_message_does_not_name_the_holder(
        self, db: Session, world: tuple[Principal, Principal, uuid.UUID]
    ) -> None:
        """검수 화면이 조직원 명단을 흘리는 자리가 되면 안 된다."""
        first, second, assessment_id = world
        review_service.claim(db, first, assessment_id, now=NOW)
        db.commit()

        with pytest.raises(review_service.ReviewConflictError) as caught:
            review_service.claim(db, second, assessment_id, now=NOW)

        assert str(first.user_id) not in caught.value.message_ko
        assert "다른 검수자" in caught.value.message_ko

    def test_an_abandoned_claim_lapses_rather_than_locking_the_queue(
        self, db: Session, world: tuple[Principal, Principal, uuid.UUID]
    ) -> None:
        """사람은 자리를 비우고 브라우저는 닫힌다. 반납을 눌러야만 풀리면 큐가 잠긴다."""
        first, second, assessment_id = world
        review_service.claim(db, first, assessment_id, now=NOW)
        db.commit()

        later = NOW + review_service.CLAIM_EXPIRES_AFTER + timedelta(minutes=1)
        moved = review_service.claim(db, second, assessment_id, now=later)
        db.commit()

        assert moved.stage is ReviewStage.UNDER_REVIEW
        row = db.get(ClaimAssessmentRow, assessment_id)
        assert row is not None and row.claimed_by == second.user_id
        # 큐로 돌아간 순간이 이력에 남아야 한다. 곧장 주인만 바뀌면 그 순간이 사라진다.
        moves = [str(entry["to_stage"]) for entry in row.review_history]
        assert moves == ["UNDER_REVIEW", "PENDING_REVIEW", "UNDER_REVIEW"]
        assert str(row.review_history[1]["trigger"]) == "SYSTEM_LAPSE"

    def test_reclaiming_my_own_item_does_not_add_to_the_history(
        self, db: Session, world: tuple[Principal, Principal, uuid.UUID]
    ) -> None:
        """새로고침 한 번이 이력을 늘리면, 그 이력을 읽는 사람은 뭔가 일어난 줄 안다."""
        first, _second, assessment_id = world
        review_service.claim(db, first, assessment_id, now=NOW)
        review_service.claim(db, first, assessment_id, now=NOW + timedelta(minutes=1))
        db.commit()

        row = db.get(ClaimAssessmentRow, assessment_id)
        assert row is not None
        assert len(row.review_history) == 1

    def test_releasing_returns_it_to_the_queue(
        self, db: Session, world: tuple[Principal, Principal, uuid.UUID]
    ) -> None:
        first, second, assessment_id = world
        review_service.claim(db, first, assessment_id, now=NOW)
        review_service.release(db, first, assessment_id, now=NOW)
        db.commit()

        moved = review_service.claim(db, second, assessment_id, now=NOW)
        db.commit()
        assert moved.stage is ReviewStage.UNDER_REVIEW


class TestTheHumanDecisionNeverOverwritesTheMachine:
    def test_confirming_leaves_the_automated_verdict_untouched(
        self, db: Session, world: tuple[Principal, Principal, uuid.UUID]
    ) -> None:
        """사람이 옳다고 해서 기계가 뭐라고 했는지를 지우면, 자동 판정이 어디서 빗나가는지
        셀 수 없게 된다."""
        first, _second, assessment_id = world
        before = db.get(ClaimAssessmentRow, assessment_id)
        assert before is not None
        original = (before.automated_verdict, before.automated_rationale, before.rule_id)

        review_service.claim(db, first, assessment_id, now=NOW)
        review_service.decide(
            db, first, assessment_id, target=ReviewStage.CONFIRMED, now=NOW
        )
        db.commit()

        after = db.get(ClaimAssessmentRow, assessment_id)
        assert after is not None
        assert (after.automated_verdict, after.automated_rationale, after.rule_id) == original
        assert after.review_state == "HUMAN_CONFIRMED"
        assert after.reviewed_by == first.user_id

    def test_a_rejection_keeps_its_reason(
        self, db: Session, world: tuple[Principal, Principal, uuid.UUID]
    ) -> None:
        """기각 사유가 닫힌 목록인 이유 — 자동 판정이 어디서 빗나가는지 세기 위해서다."""
        first, _second, assessment_id = world
        review_service.claim(db, first, assessment_id, now=NOW)
        review_service.decide(
            db,
            first,
            assessment_id,
            target=ReviewStage.REJECTED,
            rejection_reason=RejectionReason.WRONG_ENTITY,
            now=NOW,
        )
        db.commit()

        row = db.get(ClaimAssessmentRow, assessment_id)
        assert row is not None
        assert row.review_state == "HUMAN_REJECTED"
        assert "동명의 다른 업체" in (row.reviewer_note or "")

    def test_needs_more_evidence_stays_in_the_queue(
        self, db: Session, world: tuple[Principal, Principal, uuid.UUID]
    ) -> None:
        """끝난 것이 아니라 멈춰 있는 것이다. 목록에서 빠지면 영영 다시 보지 않는다."""
        first, _second, assessment_id = world
        review_service.claim(db, first, assessment_id, now=NOW)
        review_service.decide(
            db,
            first,
            assessment_id,
            target=ReviewStage.NEEDS_MORE_EVIDENCE,
            now=NOW,
        )
        db.commit()

        waiting = review_service.pending_for_review(db, first)
        assert assessment_id in {row_id for row_id, _ in waiting}

    def test_a_decided_item_leaves_the_queue(
        self, db: Session, world: tuple[Principal, Principal, uuid.UUID]
    ) -> None:
        first, _second, assessment_id = world
        review_service.claim(db, first, assessment_id, now=NOW)
        review_service.decide(
            db, first, assessment_id, target=ReviewStage.CONFIRMED, now=NOW
        )
        db.commit()

        assert assessment_id not in {
            row_id for row_id, _ in review_service.pending_for_review(db, first)
        }

    def test_the_path_to_the_decision_is_kept_not_just_its_endpoint(
        self, db: Session, world: tuple[Principal, Principal, uuid.UUID]
    ) -> None:
        """끝점만 남기면 어떻게 거기까지 갔는지 알 수 없고, 검수 기록에서 그것이 가장
        자주 필요한 질문이다."""
        first, _second, assessment_id = world
        review_service.claim(db, first, assessment_id, now=NOW)
        review_service.release(db, first, assessment_id, now=NOW)
        review_service.claim(db, first, assessment_id, now=NOW)
        review_service.decide(
            db, first, assessment_id, target=ReviewStage.CONFIRMED, now=NOW
        )
        db.commit()

        row = db.get(ClaimAssessmentRow, assessment_id)
        assert row is not None
        moves = [str(entry["to_stage"]) for entry in row.review_history]
        assert moves == ["UNDER_REVIEW", "PENDING_REVIEW", "UNDER_REVIEW", "CONFIRMED"]


class TestSurvivingARestart:
    def test_a_claim_made_in_one_session_is_visible_in_another(
        self, factory: sessionmaker[Session], world: tuple[Principal, Principal, uuid.UUID]
    ) -> None:
        """세션을 갈아 끼우는 것이 여기서는 "프로세스가 다시 떴다" 를 뜻한다."""
        first, second, assessment_id = world
        with factory() as one:
            review_service.claim(one, first, assessment_id, now=NOW)
            one.commit()

        with factory() as two, pytest.raises(review_service.ReviewConflictError):
            review_service.claim(two, second, assessment_id, now=NOW)


class TestTheAuditTrail:
    def test_every_move_is_recorded(
        self, db: Session, world: tuple[Principal, Principal, uuid.UUID]
    ) -> None:
        first, _second, assessment_id = world
        review_service.claim(db, first, assessment_id, now=NOW)
        review_service.decide(
            db,
            first,
            assessment_id,
            target=ReviewStage.REJECTED,
            rejection_reason=RejectionReason.SPAN_MISREAD,
            note_ko="원문을 열어 보니 다른 문장이었습니다.",
            now=NOW,
        )
        db.commit()

        actions = [
            row.action
            for row in db.scalars(
                select(AuditLog)
                .where(AuditLog.target_id == str(assessment_id))
                .order_by(AuditLog.created_at)
            )
        ]
        assert actions == [
            review_service.CLAIM_ACTION,
            review_service.DECIDE_ACTION,
        ]

    def test_the_reviewer_note_does_not_land_in_the_audit_log(
        self, db: Session, world: tuple[Principal, Principal, uuid.UUID]
    ) -> None:
        """자유 서술이라 고객 연락처가 섞일 수 있다. 감사 로그는 그런 값을 담는 자리가 아니다."""
        first, _second, assessment_id = world
        note = "환자 보호자 010-0000-0000 확인함"
        review_service.claim(db, first, assessment_id, now=NOW)
        review_service.decide(
            db,
            first,
            assessment_id,
            target=ReviewStage.REJECTED,
            rejection_reason=RejectionReason.DUPLICATE,
            note_ko=note,
            now=NOW,
        )
        db.commit()

        entries = db.scalars(
            select(AuditLog).where(AuditLog.target_id == str(assessment_id))
        ).all()
        assert entries
        assert all(note not in str(entry.detail) for entry in entries)
        assert any(entry.detail.get("has_note") is True for entry in entries)


class TestTenantIsolation:
    def test_another_organization_cannot_claim_the_finding(
        self, db: Session, world: tuple[Principal, Principal, uuid.UUID]
    ) -> None:
        _first, _second, assessment_id = world
        stranger = Principal(
            user_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            roles=frozenset({Role.ANALYST}),
            session_id=uuid.uuid4().hex,
        )

        with pytest.raises(review_service.AssessmentNotFoundError):
            review_service.claim(db, stranger, assessment_id, now=NOW)
