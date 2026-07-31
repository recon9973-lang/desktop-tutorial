"""관측을 실제로 돌리고 **실제 PostgreSQL 에 저장되는지** 확인한다.

관측 실행은 되돌릴 수 없는 기록이다. 저장 경로를 한 번도 확인하지 않으면 **첫 고객
실행이 첫 시험**이 되고, 그때 잘못 저장된 것은 고칠 수 없다. 그래서 이 파일은 DB 를
요구한다.

여기서 고정하는 것 가운데 가장 중요한 것은 **못 한 일이 함께 저장되는가**이다.
`runs` 만 남기고 `skipped`·`stopped_reason` 을 버리면, 예산에 걸려 절반만 실행된 관측이
완전한 측정처럼 읽힌다. 그 위에서 계산한 노출률은 분모가 틀린 값이고, 틀렸다는 사실이
어디에도 남지 않는다.

AI 호출은 하지 않는다. 모의 전송이 합성 응답을 돌려주며, 그 응답은 전부
``[합성 응답 — 실제 AI 답변 아님]`` 으로 시작한다.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from veo.authz.principal import Principal
from veo.contracts.enums import JobType, Role
from veo.core.settings import get_settings
from veo.db.models.identity import Organization, Project, RoleAssignment, User
from veo.db.models.observation import (
    AIAnswer,
    BrandIdentity,
    Citation,
    EntityMention,
)
from veo.db.models.observation import ObservationRun as ObservationRunRow
from veo.db.models.observation import Prompt as PromptRow
from veo.db.models.observation import PromptSet as PromptSetRow
from veo.jobs import service as job_service
from veo.jobs.execution import JobFailure
from veo.observations.execution import (
    BrandIdentityMissingError,
    EngineChoice,
    answer_facts,
    execute_observation,
)
from veo.observations.jobs import observation_work
from veo.observations.metrics import visibility_metrics
from veo.observations.providers.registry import ProviderRegistry
from veo.observations.providers.storage import InMemoryAnswerStore
from veo.observations.runs import SearchMode
from veo.observations.sampling import SampleAdequacy

DATABASE_URL = os.environ.get("VEO_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(
        DATABASE_URL is None,
        reason="VEO_TEST_DATABASE_URL 을 설정해야 저장 경로를 확인할 수 있습니다",
    ),
]

SYNTHETIC_MARKER = "[합성 응답 — 실제 AI 답변 아님]"
BRAND_NAME = "합성브랜드"
BRAND_DOMAIN = "synthetic-brand.example"
MODEL = "gpt-5"
MODEL_VERSION = "gpt-5-2026-05-01"

#: 균형 검사를 통과하는 최소 질문 집합. 의도 일곱 가지를 모두 덮는다.
PROMPTS = [
    ("레이저 토닝이란 무엇인가요?", "DEFINITION", "RESEARCH"),
    ("레이저 토닝은 어떻게 받나요?", "HOW_TO", "RESEARCH"),
    ("레이저 토닝 잘하는 곳을 추천해 주세요", "BEST_OR_RECOMMENDED", "RECOMMENDATION"),
    ("레이저 토닝과 IPL 중 무엇이 나은가요?", "COMPARISON", "COMPARISON"),
    ("레이저 토닝 가격은 얼마인가요?", "PRICE", "PURCHASE_OR_VISIT"),
    ("강남역 근처 피부과를 알려주세요", "LOCAL", "PURCHASE_OR_VISIT"),
    ("레이저 토닝 부작용이 있나요?", "TRUST", "AFTERCARE"),
    ("레이저 토닝 후기가 궁금합니다", "TRUST", "RESEARCH"),
]


# --------------------------------------------------------------------------- #
# 자리 만들기
# --------------------------------------------------------------------------- #


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
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    session = factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def tenant(db: Session) -> Callable[..., tuple[Principal, PromptSetRow]]:
    """조직·프로젝트·프롬프트 집합·브랜드 식별자를 한 번에 만든다."""

    def _make(*, with_brand: bool = True) -> tuple[Principal, PromptSetRow]:
        suffix = uuid.uuid4().hex[:8]
        organization = Organization(
            slug=f"veo-obs-{suffix}", name="관측 테스트 조직", is_active=True, settings={}
        )
        db.add(organization)
        user = User(
            email=f"obs-{suffix}@veo-test.invalid", display_name="관측 담당", is_active=True
        )
        db.add(user)
        db.commit()
        db.add(
            RoleAssignment(
                organization_id=organization.id, user_id=user.id, role=str(Role.ANALYST)
            )
        )
        project = Project(
            organization_id=organization.id,
            slug=f"obs-{suffix}",
            name="관측 프로젝트",
            locale="ko-KR",
            settings={},
        )
        db.add(project)
        db.commit()

        if with_brand:
            db.add(
                BrandIdentity(
                    organization_id=organization.id,
                    project_id=project.id,
                    entity_key=f"brand-{suffix}",
                    display_name=BRAND_NAME,
                    aliases=[],
                    address_terms=[],
                    phone_numbers=[],
                    distinguishing_terms=[],
                    own_domains=[BRAND_DOMAIN],
                    is_active=True,
                )
            )

        prompt_set = PromptSetRow(
            organization_id=organization.id,
            project_id=project.id,
            name="관측 집합",
            version="1",
            locale="ko-KR",
            is_locked=False,
        )
        db.add(prompt_set)
        db.commit()

        for text, intent, funnel in PROMPTS:
            db.add(
                PromptRow(
                    organization_id=organization.id,
                    prompt_set_id=prompt_set.id,
                    text=text,
                    intent=intent,
                    funnel=funnel,
                    locale="ko-KR",
                    subject_type="NON_BRAND",
                    business_importance=0.5,
                    expected_demand_is_estimate=True,
                )
            )
        db.commit()

        principal = Principal(
            user_id=user.id,
            organization_id=organization.id,
            roles=frozenset({Role.ANALYST}),
            session_id=f"test-{suffix}",
        )
        return principal, prompt_set

    return _make


# --------------------------------------------------------------------------- #
# 합성 엔진
# --------------------------------------------------------------------------- #


def _payload(text: str, citation_urls: tuple[str, ...] = ()) -> dict:
    annotations = [
        {"type": "url_citation", "url": url, "title": "합성 출처"} for url in citation_urls
    ]
    return {
        "model": MODEL_VERSION,
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": text, "annotations": annotations}
                ],
            }
        ],
        "usage": {"input_tokens": 10, "output_tokens": 20},
    }


@pytest.fixture(autouse=True)
def _no_repetition_wait(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """이 파일이 재는 것은 **무엇이 저장되는가** 이지 시계가 아니다.

    관측은 이제 같은 질문의 반복 사이에 일부러 간격을 둔다(기본 2분). 그대로 두면 이
    파일 하나가 분 단위로 늘어나므로 여기서는 0 으로 내린다. 간격 자체는
    `tests/observations/test_repetition_pacing.py` 가 가짜 시계로 잰다.

    `get_settings` 가 캐시를 들고 있어 환경변수만 바꿔서는 안 먹는다 — 앞뒤로 비운다.
    """
    monkeypatch.setenv("VEO_OBSERVATION_REPETITION_INTERVAL_SECONDS", "0")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


DEFAULT_ANSWER = f"{SYNTHETIC_MARKER} {BRAND_NAME} 를 추천합니다."


def _registry(
    *, text: str = DEFAULT_ANSWER, citations: tuple[str, ...] = ()
) -> ProviderRegistry:
    from veo.core.settings import ProviderCredentials
    from veo.observations.providers.openai import OpenAIAnswerProvider

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_payload(text, citations))

    provider = OpenAIAnswerProvider.from_settings(
        ProviderCredentials(openai_api_key=SecretStr("sk-synthetic-key-for-tests")),
        transport=httpx.MockTransport(handler),
    )
    return ProviderRegistry([provider])


def _run(
    db: Session,
    principal: Principal,
    prompt_set: PromptSetRow,
    *,
    registry: ProviderRegistry | None = None,
    repetitions: int = 3,
) -> ObservationRunRow:
    row = execute_observation(
        db,
        principal,
        prompt_set_row=prompt_set,
        engines=[EngineChoice(engine="OPENAI", model=MODEL, search_mode=SearchMode.BROWSING)],
        repetitions=repetitions,
        registry=registry if registry is not None else _registry(),
        store=InMemoryAnswerStore(),
    )
    db.commit()
    return row


# --------------------------------------------------------------------------- #
# 검사
# --------------------------------------------------------------------------- #


class TestTheRunIsRecorded:
    def test_a_run_row_is_written(self, db: Session, tenant) -> None:
        principal, prompt_set = tenant()

        row = _run(db, principal, prompt_set)

        assert row.id is not None
        assert row.prompt_set_id == prompt_set.id

    def test_every_execution_becomes_an_answer_row(self, db: Session, tenant) -> None:
        """질문 8개, 엔진 1개, 반복 3회 — 모두 24건. 하나라도 빠지면 분모가 틀린다."""
        principal, prompt_set = tenant()

        row = _run(db, principal, prompt_set, repetitions=3)

        answers = db.scalars(
            select(AIAnswer).where(AIAnswer.observation_run_id == row.id)
        ).all()
        assert len(answers) == len(PROMPTS) * 3
        assert row.executions_attempted == len(PROMPTS) * 3

    def test_the_repetition_index_is_recovered_not_guessed(self, db: Session, tenant) -> None:
        """`ObservationRun` 은 회차를 들고 다니지 않는다. `run_id` 에서 되찾는다."""
        principal, prompt_set = tenant()

        row = _run(db, principal, prompt_set, repetitions=3)

        answers = db.scalars(
            select(AIAnswer).where(AIAnswer.observation_run_id == row.id)
        ).all()
        indexes = sorted({answer.repetition_index for answer in answers})
        assert indexes == [1, 2, 3], f"회차가 복원되지 않았다: {indexes}"

    def test_the_model_version_comes_from_the_response(self, db: Session, tenant) -> None:
        """요청한 모델 이름이 아니라 **실제로 답한** 판을 기록한다."""
        principal, prompt_set = tenant()

        row = _run(db, principal, prompt_set)

        answer = db.scalars(
            select(AIAnswer).where(AIAnswer.observation_run_id == row.id)
        ).first()
        assert answer is not None
        assert answer.model_version == MODEL_VERSION


class TestWhatWasNotDoneIsStoredToo:
    def test_a_complete_run_says_so(self, db: Session, tenant) -> None:
        principal, prompt_set = tenant()

        row = _run(db, principal, prompt_set, repetitions=3)

        assert row.is_complete
        assert row.status == "SUCCEEDED"
        assert row.executions_skipped == 0
        assert row.stopped_reason is None

    def test_a_run_below_the_repetition_floor_is_refused(self, db: Session, tenant) -> None:
        """AI 답변은 매번 달라진다. 한 번의 결과를 노출률이라고 부를 수 없다."""
        from veo.observations.runner import RepetitionFloorError

        principal, prompt_set = tenant()

        with pytest.raises(RepetitionFloorError):
            _run(db, principal, prompt_set, repetitions=1)

    def test_the_summary_is_stored_for_reading_later(self, db: Session, tenant) -> None:
        """숫자만 남기면 왜 부분 측정인지 다시 만들어 낼 수 없다."""
        principal, prompt_set = tenant()

        row = _run(db, principal, prompt_set)

        assert row.skipped_detail["summary_ko"]
        assert "실행" in row.skipped_detail["summary_ko"]

    def test_the_planned_count_sits_beside_the_attempted(self, db: Session, tenant) -> None:
        principal, prompt_set = tenant()

        row = _run(db, principal, prompt_set, repetitions=3)

        assert row.executions_planned == row.executions_attempted + row.executions_skipped


class TestEvidenceAndCost:
    def test_a_cited_url_is_recorded_with_its_domain(self, db: Session, tenant) -> None:
        principal, prompt_set = tenant()
        registry = _registry(citations=(f"https://{BRAND_DOMAIN}/clinic",))

        row = _run(db, principal, prompt_set, registry=registry)

        citations = db.scalars(
            select(Citation)
            .join(AIAnswer, Citation.ai_answer_id == AIAnswer.id)
            .where(AIAnswer.observation_run_id == row.id)
        ).all()
        assert citations
        assert all(citation.domain == BRAND_DOMAIN for citation in citations)
        assert all(citation.is_own_domain for citation in citations)

    def test_a_mention_is_recorded_under_the_declared_key_not_the_matched_string(
        self, db: Session, tenant
    ) -> None:
        """`entity_key` 는 선언된 식별자이지 답변에서 걸린 글자가 아니다.

        예전에는 맞은 이름 문자열을 그대로 넣었다. 별칭이 둘이면 같은 브랜드가 한
        답변에서 두 행이 되고, `UniqueConstraint(ai_answer_id, entity_key)` 가 그것을
        막지 못한다 — 그러면 한 답변이 언급 2회로 세어진다. `brand_identities.entity_key`
        가 있는 이유가 그것이다.
        """
        principal, prompt_set = tenant()

        row = _run(db, principal, prompt_set)

        mentions = db.scalars(
            select(EntityMention)
            .join(AIAnswer, EntityMention.ai_answer_id == AIAnswer.id)
            .where(AIAnswer.observation_run_id == row.id)
        ).all()
        assert mentions
        keys = {mention.entity_key for mention in mentions}
        assert len(keys) == 1
        assert BRAND_NAME not in keys, "표면 문자열이 아니라 선언된 식별자여야 한다"
        assert next(iter(keys)).startswith("brand-")

    def test_a_confirmed_mention_carries_the_confidence_it_was_given(
        self, db: Session, tenant
    ) -> None:
        """예전에는 여기에 1.0 이 박혀 있었다 — 무엇이 들어오든 만점이었다(0-A)."""
        principal, prompt_set = tenant()

        row = _run(db, principal, prompt_set)

        mention = db.scalars(
            select(EntityMention)
            .join(AIAnswer, EntityMention.ai_answer_id == AIAnswer.id)
            .where(AIAnswer.observation_run_id == row.id)
        ).first()
        assert mention is not None
        assert mention.needs_human_disambiguation is False
        assert mention.review_state == "NOT_REVIEWED"
        # 고유한 상호이므로 확정선을 넘지만, 그것이 "확실함" 은 아니다.
        assert 0.75 <= mention.match_confidence < 1.0

    def test_the_raw_answer_is_a_pointer_not_the_text(self, db: Session, tenant) -> None:
        """원문은 답변 저장소로 간다. DB 에는 포인터와 해시만 남는다."""
        principal, prompt_set = tenant()

        row = _run(db, principal, prompt_set)

        answer = db.scalars(
            select(AIAnswer).where(AIAnswer.observation_run_id == row.id)
        ).first()
        assert answer is not None
        assert answer.raw_answer_storage_key
        assert answer.raw_answer_hash
        assert SYNTHETIC_MARKER not in (answer.raw_answer_storage_key or "")

    def test_cost_goes_in_the_currency_it_was_measured_in(self, db: Session, tenant) -> None:
        """가격표가 비어 있으면 비용은 없다 — 0원이 아니라 모른다는 뜻이고, 원화 칸은
        환율을 알기 전까지 비어 있어야 한다."""
        principal, prompt_set = tenant()

        row = _run(db, principal, prompt_set)

        answers = db.scalars(
            select(AIAnswer).where(AIAnswer.observation_run_id == row.id)
        ).all()
        assert all(answer.cost_krw is None for answer in answers)


class TestRefusals:
    def test_a_project_without_a_brand_identity_is_refused(self, db: Session, tenant) -> None:
        """이름 없이 언급을 세면 모든 답변이 '언급 없음' 이 된다. 그것은 측정이 아니다."""
        principal, prompt_set = tenant(with_brand=False)

        with pytest.raises(BrandIdentityMissingError) as caught:
            _run(db, principal, prompt_set)

        assert "브랜드" in str(caught.value)


class TestMetricsFromStoredAnswers:
    """저장된 것에서 지표가 나오는가. 특히 **분모**가 맞는가."""

    def test_a_run_that_mentions_every_time_reads_as_full_coverage(
        self, db: Session, tenant
    ) -> None:
        principal, prompt_set = tenant()
        row = _run(db, principal, prompt_set)

        measured = visibility_metrics(
            answer_facts(db, principal, row.id),
            prompts_planned=row.executions_planned,
            run_is_complete=row.is_complete,
        )

        assert measured.mention_rate.value == 1.0
        assert measured.mention_rate.adequacy is SampleAdequacy.ADEQUATE
        # 24번 모두 언급됐어도 확신은 아니다. 정규 근사라면 여기서 하한도 1.0 이 된다.
        assert measured.mention_rate.confidence_low is not None
        assert measured.mention_rate.confidence_low < 1.0

    def test_citations_are_only_counted_when_they_are_ours(self, db: Session, tenant) -> None:
        """경쟁사를 인용한 응답은 우리가 인용된 것이 아니다. 여기서 세면 인용률이 부푼다."""
        principal, prompt_set = tenant()
        registry = _registry(citations=("https://synthetic-rival.example/clinic",))

        row = _run(db, principal, prompt_set, registry=registry)
        measured = visibility_metrics(
            answer_facts(db, principal, row.id),
            prompts_planned=row.executions_planned,
            run_is_complete=row.is_complete,
        )

        assert measured.citation_rate.trials > 0
        assert measured.citation_rate.value == 0.0

    def test_our_own_citation_counts(self, db: Session, tenant) -> None:
        principal, prompt_set = tenant()
        registry = _registry(citations=(f"https://{BRAND_DOMAIN}/clinic",))

        row = _run(db, principal, prompt_set, registry=registry)
        measured = visibility_metrics(
            answer_facts(db, principal, row.id),
            prompts_planned=row.executions_planned,
            run_is_complete=row.is_complete,
        )

        assert measured.citation_rate.value == 1.0

    def test_citation_observability_survives_to_the_metric(self, db: Session, tenant) -> None:
        """검색을 끄면 출처를 볼 수 없다. 그때 인용률은 0%가 아니라 **측정 불가**다."""
        principal, prompt_set = tenant()
        row = execute_observation(
            db,
            principal,
            prompt_set_row=prompt_set,
            engines=[
                EngineChoice(engine="OPENAI", model=MODEL, search_mode=SearchMode.NO_BROWSING)
            ],
            repetitions=3,
            registry=_registry(),
            store=InMemoryAnswerStore(),
        )
        db.commit()

        measured = visibility_metrics(
            answer_facts(db, principal, row.id),
            prompts_planned=row.executions_planned,
            run_is_complete=row.is_complete,
        )

        assert measured.answers_with_visible_citations == 0
        assert measured.citation_rate.value is None, "0%로 보고하면 사이트 탓처럼 읽힌다"
        assert any("모델" in note for note in measured.caveats_ko)


class TestTheJobPath:
    """관측이 요청 밖에서 도는 경로.

    이 경로가 없어서 관측 실행이 요청 안에서 그대로 돌았다. 질문 여덟 개를 세 번씩,
    엔진 하나로만 잡아도 스물네 번의 외부 호출이고 그것은 몇 분이다. 게이트웨이가 먼저
    끊고, 사용자에게는 "기능이 고장났다" 로 보이며, 그 시점에 비용은 이미 나갔다.
    """

    def test_the_work_produces_a_run_and_says_it_is_complete(
        self, db: Session, tenant
    ) -> None:
        principal, prompt_set = tenant()
        job, created = job_service.submit(
            db,
            principal,
            job_type=JobType.GEO_OBSERVATION_RUN,
            parameters={"prompt_set_id": str(prompt_set.id)},
        )
        db.commit()
        assert created

        work = observation_work(
            organization_id=principal.organization_id,
            user_id=principal.user_id,
            roles=principal.roles,
            session_id=principal.session_id,
            prompt_set_id=prompt_set.id,
            choices=[EngineChoice(engine="OPENAI", model=MODEL)],
            repetitions=3,
            allow_below_floor=False,
            registry=_registry(),
            store=InMemoryAnswerStore(),
        )
        outcome = work(db, job.id)
        db.commit()

        assert outcome.result_run_id is not None
        assert outcome.is_partial is False
        stored = db.get(ObservationRunRow, outcome.result_run_id)
        assert stored is not None

    def test_a_missing_prompt_set_fails_with_a_sentence_a_person_can_read(
        self, db: Session, tenant
    ) -> None:
        """작업 실패 메시지는 그대로 화면에 간다. 예외 원문을 옮기면 내부 정보가 샌다."""
        principal, _ = tenant()
        job, _ = job_service.submit(
            db, principal, job_type=JobType.GEO_OBSERVATION_RUN, parameters={}
        )
        db.commit()

        work = observation_work(
            organization_id=principal.organization_id,
            user_id=principal.user_id,
            roles=principal.roles,
            session_id=principal.session_id,
            prompt_set_id=uuid.uuid4(),
            choices=[EngineChoice(engine="OPENAI", model=MODEL)],
            repetitions=3,
            allow_below_floor=False,
            registry=_registry(),
            store=InMemoryAnswerStore(),
        )

        with pytest.raises(JobFailure) as caught:
            work(db, job.id)

        assert caught.value.error_code == "PROMPT_SET_NOT_FOUND"
        assert "질문 집합" in caught.value.message_ko

    def test_the_same_idempotency_key_does_not_buy_a_second_run(
        self, db: Session, tenant
    ) -> None:
        """관측은 돈이 나간다. 새로고침 한 번이 두 번째 청구가 되면 안 된다."""
        principal, prompt_set = tenant()
        parameters = {"prompt_set_id": str(prompt_set.id)}

        first, first_created = job_service.submit(
            db,
            principal,
            job_type=JobType.GEO_OBSERVATION_RUN,
            parameters=parameters,
            idempotency_key="same-click",
        )
        db.commit()
        second, second_created = job_service.submit(
            db,
            principal,
            job_type=JobType.GEO_OBSERVATION_RUN,
            parameters=parameters,
            idempotency_key="same-click",
        )
        db.commit()

        assert first_created is True
        assert second_created is False
        assert first.id == second.id

    def test_another_organization_cannot_read_the_job(self, db: Session, tenant) -> None:
        """남의 조직 작업은 403 이 아니라 **없는 것**이다."""
        owner, prompt_set = tenant()
        stranger, _ = tenant()
        job, _ = job_service.submit(
            db,
            owner,
            job_type=JobType.GEO_OBSERVATION_RUN,
            parameters={"prompt_set_id": str(prompt_set.id)},
        )
        db.commit()

        with pytest.raises(job_service.JobNotFoundError):
            job_service.read(db, stranger, job.id)


# --------------------------------------------------------------------------- #
# #24 — `claim_assessments` 에 쓰는 첫 코드
# --------------------------------------------------------------------------- #
#
# 이 테이블은 지금까지 **쓰는 코드가 0건**이었다. 위험 분류·심각도 표·검수 상태 기계·
# 공개 게이트가 전부 완성되어 있었는데 아무도 부르지 않았고, 그래서 테이블이 실제로 쓸
# 수 있는 모양인지도 확인된 적이 없었다(0-E).
#
# 여기서 고정하는 것은 셋이다.
#   1. 보류된 언급이 판정 행으로 남는가
#   2. 그 행을 **다시 판정 객체로 읽을 수 있는가** — 못 읽으면 근거가 아니라 주장이다
#   3. 게이트를 지난 뒤 고객 문서에 무엇이 남는가

#: 같은 이름의 더 긴 상호. 판별기가 이 고객이라고 말하지 못한다.
HELD_ANSWER = f"{SYNTHETIC_MARKER} 부산 해운대구의 백세{BRAND_NAME}이 유명합니다."


class TestHeldMentionsBecomeReviewableFindings:
    def test_a_held_mention_is_written_to_claim_assessments(
        self, db: Session, tenant
    ) -> None:
        from veo.db.models.observation import ClaimAssessment as ClaimAssessmentRow

        principal, prompt_set = tenant()

        row = _run(db, principal, prompt_set, registry=_registry(text=HELD_ANSWER))

        found = db.scalars(
            select(ClaimAssessmentRow)
            .join(AIAnswer, AIAnswer.id == ClaimAssessmentRow.ai_answer_id)
            .where(AIAnswer.observation_run_id == row.id)
        ).all()

        assert found, "보류된 언급이 검수 큐에 도달하지 않으면 아무도 그것을 보지 못한다"
        assert all(item.assessment_type == "ENTITY_DISAMBIGUATION" for item in found)
        assert all(item.review_state == "PENDING_REVIEW" for item in found)
        assert all(item.review_stage == "PENDING_REVIEW" for item in found)

    def test_the_finding_says_it_is_unknown_not_wrong(self, db: Session, tenant) -> None:
        """"AI 가 당신 병원을 다른 병원과 혼동했습니다" 는 우리가 확인하지 않은 말이다.

        확인한 것은 **우리가 못 가렸다** 는 사실뿐이다. 그래서 판정은 UNKNOWN 이고,
        게이트가 이것을 지적이 아니라 '확인하지 못한 건' 으로 뺀다.
        """
        from veo.db.models.observation import ClaimAssessment as ClaimAssessmentRow

        principal, prompt_set = tenant()

        row = _run(db, principal, prompt_set, registry=_registry(text=HELD_ANSWER))

        item = db.scalars(
            select(ClaimAssessmentRow)
            .join(AIAnswer, AIAnswer.id == ClaimAssessmentRow.ai_answer_id)
            .where(AIAnswer.observation_run_id == row.id)
        ).first()
        assert item is not None
        assert item.automated_verdict == "UNKNOWN"
        assert item.automated_basis == "DETERMINISTIC_RULE"
        assert item.rule_id == "RISK-R020"
        assert "갈리지 않았습니다" in (item.automated_rationale or "")

    def test_a_confirmed_mention_produces_no_finding(self, db: Session, tenant) -> None:
        """멀쩡히 갈린 언급까지 큐에 넣으면 큐가 절대 비지 않고, 비지 않는 큐는 안 읽힌다."""
        from veo.db.models.observation import ClaimAssessment as ClaimAssessmentRow

        principal, prompt_set = tenant()

        row = _run(db, principal, prompt_set)

        assert not db.scalars(
            select(ClaimAssessmentRow)
            .join(AIAnswer, AIAnswer.id == ClaimAssessmentRow.ai_answer_id)
            .where(AIAnswer.observation_run_id == row.id)
        ).all()


class TestTheFindingCanBeOpenedAgain:
    def test_the_stored_row_reads_back_as_a_review_record(
        self, db: Session, tenant
    ) -> None:
        """쓰기만 하고 못 읽는 테이블은 근거가 아니다.

        `claim_text` 만으로는 그 문장이 정말 그 답변의 그 자리였는지 확인할 수 없다.
        포인터·해시·구간이 함께 남아야 나중에 대조할 수 있다(0-A).
        """
        from veo.observations.findings import reviews_for_run

        principal, prompt_set = tenant()
        row = _run(db, principal, prompt_set, registry=_registry(text=HELD_ANSWER))

        reviews = reviews_for_run(db, principal, row.id)

        assert reviews
        evidence = reviews[0].assessment.evidence
        assert evidence.answer_ref
        assert len(evidence.answer_hash) == 64
        assert evidence.span_end - evidence.span_start == len(evidence.quoted_text)
        assert evidence.quoted_text == BRAND_NAME

    def test_the_span_points_at_the_name_inside_the_longer_business(
        self, db: Session, tenant
    ) -> None:
        """검수자는 기계가 **실제로 본 글자**를 봐야 판단할 수 있다."""
        from veo.observations.findings import reviews_for_run

        principal, prompt_set = tenant()
        row = _run(db, principal, prompt_set, registry=_registry(text=HELD_ANSWER))

        evidence = reviews_for_run(db, principal, row.id)[0].assessment.evidence
        assert HELD_ANSWER[evidence.span_start : evidence.span_end] == evidence.quoted_text

    def test_a_row_without_evidence_is_refused_rather_than_guessed(
        self, db: Session, tenant
    ) -> None:
        """빈 자리를 그럴듯한 값으로 메우면 확인할 수 없는 지적이 확인된 것처럼 보인다."""
        from sqlalchemy import update

        from veo.db.models.observation import ClaimAssessment as ClaimAssessmentRow
        from veo.observations.findings import UnreadableAssessmentError, reviews_for_run

        principal, prompt_set = tenant()
        row = _run(db, principal, prompt_set, registry=_registry(text=HELD_ANSWER))

        db.execute(
            update(ClaimAssessmentRow)
            .where(ClaimAssessmentRow.organization_id == principal.organization_id)
            .values(evidence_answer_hash=None)
        )
        db.commit()

        with pytest.raises(UnreadableAssessmentError):
            reviews_for_run(db, principal, row.id)


class TestWhatTheCustomerDocumentMayContain:
    def test_an_unknown_verdict_is_not_a_finding_in_the_customer_payload(
        self, db: Session, tenant
    ) -> None:
        from veo.observations.findings import reviews_for_run
        from veo.observations.review.gating import apply_publication_gate

        principal, prompt_set = tenant()
        row = _run(db, principal, prompt_set, registry=_registry(text=HELD_ANSWER))

        payload = apply_publication_gate(reviews_for_run(db, principal, row.id))

        assert payload.as_customer_payload()["findings"] == []
        assert payload.as_customer_payload()["not_measured"]["total"] > 0

    def test_the_internal_view_still_carries_the_sentence(
        self, db: Session, tenant
    ) -> None:
        """내부 화면은 봐야 판단한다. 그래서 이 payload 는 공개 경로에 연결하면 안 된다."""
        from veo.observations.findings import reviews_for_run
        from veo.observations.review.gating import apply_publication_gate

        principal, prompt_set = tenant()
        row = _run(db, principal, prompt_set, registry=_registry(text=HELD_ANSWER))

        internal = apply_publication_gate(
            reviews_for_run(db, principal, row.id)
        ).as_internal_payload()

        assert internal["items"]
        assert internal["items"][0]["assessment"]["claim_text"] == BRAND_NAME

    def test_zero_findings_is_reported_with_what_we_do_not_measure(self) -> None:
        """"위험 0건" 만 보여주면 위험이 없다로 읽힌다. 8종 중 1종만 재고 있다."""
        from veo.observations.findings import assessment_kinds_not_yet_produced

        missing = assessment_kinds_not_yet_produced()

        assert len(missing) == 7
        assert all(item["reason_ko"] for item in missing)
        kinds = {item["kind"] for item in missing}
        assert "ENTITY_DISAMBIGUATION" not in kinds, "이것 하나는 실제로 재고 있다"
