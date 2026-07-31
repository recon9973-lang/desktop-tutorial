"""저장된 호출에서 이번 달 지출을 읽는다.

`veo.observability.cost` 는 예산 어휘를 전부 갖고 있었고 **호출자가 없었다.**
`BudgetTracker` 는 메모리 누산기라 실행이 끝나면 사라지고, 저장된 행에서 같은 답을
만드는 코드는 어디에도 없었다. 그래서 "이번 달 얼마 썼나" 를 물을 데가 없었다.

여기서 고정하는 것:

* 금액을 못 낸 호출을 **0원으로 더하지 않는다.** 더하면 합계가 "예산 안" 처럼 보이는데
  자료가 그걸 뒷받침하지 않는다.
* 못 낸 이유를 **이유별로** 센다. 다섯 가지고 처방이 각각 다르다.
* 가격표가 비어 있어도 **토큰과 호출 수는 실측**이다.
* 다른 조직의 호출은 세지 않는다.
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
from veo.contracts.enums import Role
from veo.db.models.identity import Organization, Project
from veo.db.models.observation import AIAnswer, AIEngine, Prompt, PromptSet
from veo.db.models.observation import ObservationRun as ObservationRunRow
from veo.observability.cost import CostMeasurement, UnmeasurableReason
from veo.observability.spend import spend_for_month

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(
        DATABASE_URL is None,
        reason="VEO_TEST_DATABASE_URL 을 설정해야 지출 집계를 확인할 수 있습니다",
    ),
]

JULY = datetime(2026, 7, 15, 3, 0, tzinfo=UTC)
JUNE = datetime(2026, 6, 15, 3, 0, tzinfo=UTC)
HASH = "b" * 64


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
        session.rollback()


def _principal(organization_id: uuid.UUID) -> Principal:
    return Principal(
        user_id=uuid.uuid4(),
        organization_id=organization_id,
        roles=frozenset({Role.ANALYST}),
        session_id="spend-test",
    )


@pytest.fixture
def world(db: Session):  # type: ignore[no-untyped-def]
    """조직 둘, 각자 프로젝트와 실행 하나."""
    made = []
    for label in ("가", "나"):
        organization = Organization(
            name=f"조직 {label}", slug=f"org-{uuid.uuid4().hex[:8]}", settings={}
        )
        db.add(organization)
        db.flush()
        project = Project(
            organization_id=organization.id,
            slug=f"p-{uuid.uuid4().hex[:8]}",
            name="프로젝트",
            locale="ko-KR",
            settings={},
        )
        db.add(project)
        db.flush()
        prompt_set = PromptSet(
            organization_id=organization.id,
            project_id=project.id,
            name="집합",
            version="1",
            locale="ko-KR",
            is_locked=True,
        )
        db.add(prompt_set)
        db.flush()
        prompt = Prompt(
            organization_id=organization.id,
            prompt_set_id=prompt_set.id,
            text="강남 한의원 추천",
            intent="RECOMMENDATION",
            funnel="CONSIDERATION",
            locale="ko-KR",
            subject_type="NON_BRAND",
            business_importance=0.5,
        )
        run = ObservationRunRow(
            organization_id=organization.id,
            project_id=project.id,
            prompt_set_id=prompt_set.id,
            repetitions_per_prompt=3,
            engines=["OPENAI"],
            competitor_ids=[],
            started_at=JULY,
            finished_at=JULY,
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
        made.append((organization, prompt, run))
    return made


def _engine_row(db: Session, provider: str) -> AIEngine:
    """`ai_engines` 는 조직에 묶이지 않는 전역 표다. 있으면 쓴다."""
    found = db.scalars(
        select(AIEngine)
        .where(AIEngine.provider == provider)
        .where(AIEngine.model == "m1")
        .where(AIEngine.search_mode == "DEFAULT")
    ).first()
    if found is not None:
        return found
    created = AIEngine(
        provider=provider,
        model="m1",
        search_mode="DEFAULT",
        display_name=f"{provider} m1",
        is_enabled=True,
        provider_state="ENABLED",
    )
    db.add(created)
    db.flush()
    return created


def _answer(  # type: ignore[no-untyped-def]
    db: Session,
    world_entry,
    *,
    provider: str = "OPENAI",
    when: datetime = JULY,
    cost_usd: float | None = None,
    cost_basis: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> AIAnswer:
    organization, prompt, run = world_entry
    answer = AIAnswer(
        organization_id=organization.id,
        observation_run_id=run.id,
        prompt_id=prompt.id,
        ai_engine_id=_engine_row(db, provider).id,
        repetition_index=1,
        model_version="m1-2026-05-01",
        search_mode="DEFAULT",
        account_state="ANONYMOUS",
        locale="ko-KR",
        executed_at=when,
        is_valid_execution=True,
        raw_answer_hash=HASH,
        cost_usd=cost_usd,
        cost_basis=cost_basis,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    db.add(answer)
    db.flush()
    return answer


def test_tokens_are_counted_even_when_nothing_can_be_priced(db: Session, world) -> None:  # type: ignore[no-untyped-def]
    """가격표가 비어 있어도 사용량은 실측이다.

    가격을 모른다고 사용량까지 모르는 것은 아니다. 이 숫자가 지금 유일하게 확실한
    지출 신호다.
    """
    mine = world[0]
    _answer(db, mine, cost_basis="NO_PRICE_CONFIGURED", input_tokens=1200, output_tokens=340)
    _answer(db, mine, cost_basis="NO_PRICE_CONFIGURED", input_tokens=800, output_tokens=160)

    report = spend_for_month(db, principal=_principal(mine[0].id), month="2026-07")

    assert report.total_calls == 2
    assert report.input_tokens == 2000
    assert report.output_tokens == 500
    assert report.budget.spent_usd == 0.0
    assert report.budget.measurement is CostMeasurement.NONE


def test_an_unpriced_call_is_not_counted_as_zero_dollars(db: Session, world) -> None:  # type: ignore[no-untyped-def]
    """0원으로 더하면 합계가 '예산 안' 처럼 보인다. 자료가 그걸 뒷받침하지 않는다."""
    mine = world[0]
    _answer(db, mine, cost_usd=0.25, cost_basis="CALCULATED_FROM_USAGE", input_tokens=100)
    _answer(db, mine, cost_basis="NO_PRICE_CONFIGURED", input_tokens=100)

    report = spend_for_month(db, principal=_principal(mine[0].id), month="2026-07")

    assert report.budget.measured_calls == 1
    assert report.budget.unmeasurable_calls == 1
    assert report.budget.spent_usd == pytest.approx(0.25)
    # 절반만 쟀다. `COMPLETE` 였다면 0.25 달러가 이 달의 전부라는 뜻이 된다.
    assert report.budget.measurement is CostMeasurement.PARTIAL


def test_the_ratio_refuses_to_answer_when_nothing_could_be_priced(db: Session, world) -> None:  # type: ignore[no-untyped-def]
    """0% 는 '여유 있음' 으로 읽힌다. 그 결론은 자료에 없다."""
    mine = world[0]
    _answer(db, mine, cost_basis="NO_PRICE_CONFIGURED", input_tokens=100)

    report = spend_for_month(
        db, principal=_principal(mine[0].id), month="2026-07", limit_usd=50.0
    )

    assert report.budget.ratio is None


def test_each_reason_is_counted_separately(db: Session, world) -> None:  # type: ignore[no-untyped-def]
    """다섯 가지고 처방이 각각 다르다. 합쳐 놓으면 뭘 고칠지 알 수 없다."""
    mine = world[0]
    _answer(db, mine, cost_basis="NO_PRICE_CONFIGURED", input_tokens=100)
    _answer(db, mine, cost_basis="NO_USAGE_REPORTED")
    _answer(db, mine, cost_basis="PRICE_TABLE_STALE", input_tokens=100)

    report = spend_for_month(db, principal=_principal(mine[0].id), month="2026-07")

    assert report.budget.unmeasurable_by_reason == {
        UnmeasurableReason.NO_PRICE_CONFIGURED: 1,
        UnmeasurableReason.NO_USAGE_REPORTED: 1,
        UnmeasurableReason.PRICE_TABLE_STALE: 1,
    }
    assert len(report.remedies_ko()) == 3
    assert all(not line.isascii() for line in report.remedies_ko())


def test_a_call_saved_before_the_reason_column_reads_as_unspecified(
    db: Session, world
) -> None:  # type: ignore[no-untyped-def]
    """이유를 지어내지 않는다. '말해 주지 않았다' 가 정확하다."""
    mine = world[0]
    _answer(db, mine, cost_basis=None)

    report = spend_for_month(db, principal=_principal(mine[0].id), month="2026-07")

    assert report.budget.unmeasurable_by_reason == {UnmeasurableReason.UNSPECIFIED: 1}


def test_engines_are_broken_out(db: Session, world) -> None:  # type: ignore[no-untyped-def]
    mine = world[0]
    _answer(db, mine, provider="OPENAI", input_tokens=100, cost_basis="NO_PRICE_CONFIGURED")
    _answer(db, mine, provider="ANTHROPIC", input_tokens=300, cost_basis="NO_PRICE_CONFIGURED")

    report = spend_for_month(db, principal=_principal(mine[0].id), month="2026-07")

    assert [usage.engine for usage in report.engines] == ["ANTHROPIC", "OPENAI"]
    assert [usage.input_tokens for usage in report.engines] == [300, 100]


def test_another_month_is_not_counted(db: Session, world) -> None:  # type: ignore[no-untyped-def]
    mine = world[0]
    _answer(db, mine, when=JUNE, input_tokens=999, cost_basis="NO_PRICE_CONFIGURED")

    report = spend_for_month(db, principal=_principal(mine[0].id), month="2026-07")

    assert report.total_calls == 0
    assert report.input_tokens == 0


def test_another_organizations_calls_are_not_counted(db: Session, world) -> None:  # type: ignore[no-untyped-def]
    mine, theirs = world[0], world[1]
    _answer(db, theirs, input_tokens=5000, cost_basis="NO_PRICE_CONFIGURED")

    report = spend_for_month(db, principal=_principal(mine[0].id), month="2026-07")

    assert report.total_calls == 0
    assert report.input_tokens == 0


def test_the_summary_says_both_halves(db: Session, world) -> None:  # type: ignore[no-untyped-def]
    """잰 금액과 못 잰 건수가 **같은 문장에** 있어야 한다."""
    mine = world[0]
    _answer(db, mine, cost_usd=1.5, cost_basis="CALCULATED_FROM_USAGE", input_tokens=10)
    _answer(db, mine, cost_basis="NO_PRICE_CONFIGURED", input_tokens=10)

    report = spend_for_month(db, principal=_principal(mine[0].id), month="2026-07")
    line = report.budget.alert_line_ko()

    assert "1.50" in line
    assert "측정 불가" in line
    assert "0원으로 계산하지" in line
