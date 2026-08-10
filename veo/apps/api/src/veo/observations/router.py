"""``/observations`` — 엔진 상태, 프롬프트 집합, 그리고 실제 관측.

이 라우터가 없어서 **완성된 관측 엔진에 손이 닿지 않았다.** `src/` 안에서
`ObservationRunner` 를 부르는 코드가 하나도 없었고, 제공자 어댑터·인용 탐지·위험 평가·
검수 대기열이 전부 테스트에서만 돌았다.

이 화면들이 거듭 지키는 것 하나: **못 한 일을 한 일과 같은 자리에 둔다.** 엔진 목록은
쓸 수 없는 엔진도 이유와 함께 돌려주고, 실행 결과는 건너뛴 횟수와 중단 사유를 함께
돌려준다. 둘 다 빼면 "여기 있는 게 전부" 로 읽히는데, 그것이 이 제품이 만들지 않기로 한
종류의 그럴듯한 완결성이다.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated, Final

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal
from veo.contracts.enums import JobType, ProviderState
from veo.contracts.envelope import ApiResponse
from veo.core.settings import get_provider_credentials
from veo.db.models.observation import ObservationRun as ObservationRunRow
from veo.db.models.observation import PromptSet as PromptSetRow
from veo.db.session import get_db
from veo.jobs import service as jobs
from veo.jobs.dispatch import dispatch
from veo.jobs.router import job_payload
from veo.jobs.schemas import JobPayload
from veo.observability.spend import spend_for_month
from veo.observations import review_service
from veo.observations.estimate import estimate_work, plan_slots
from veo.observations.execution import EngineChoice, answer_facts
from veo.observations.findings import assessment_kinds_not_yet_produced, reviews_for_run
from veo.observations.jobs import OBSERVATION_STAGES, observation_work
from veo.observations.metrics import visibility_metrics
from veo.observations.prompts import PromptSet, PromptSetImbalanceError
from veo.observations.providers.registry import _STATE_LABELS_KO
from veo.observations.question_sources import harvest_questions
from veo.observations.review.decisions import (
    IllegalReviewTransitionError,
    RejectionReason,
    ReviewedAssessment,
    ReviewStage,
    describe_stage_ko,
)
from veo.observations.review.gating import apply_publication_gate
from veo.observations.runs import AccountState, SearchMode
from veo.observations.schemas import (
    CollectedQuestionPayload,
    EnginePayload,
    EngineSpendPayload,
    EngineStatus,
    EstimatePayload,
    EstimateRequest,
    ManualRunRequest,
    ObservationRunDetailPayload,
    ObservationRunListPayload,
    ObservationRunPayload,
    ObservationRunRequest,
    PromptSetCreateRequest,
    PromptSetListPayload,
    PromptSetPayload,
    PromptSummary,
    QuestionHarvestPayload,
    QuestionSourcePayload,
    QuestionSourceRequest,
    ReviewDecisionRequest,
    ReviewedItemPayload,
    ReviewQueueItem,
    ReviewQueuePayload,
    RiskFindingsPayload,
    SlotEstimatePayload,
    SpendPayload,
    VisibilityMetricsPayload,
)
from veo.observations.service import (
    ENGINE_NOTE_KO,
    SEARCH_OFF_UNAVAILABLE_KO,
    UnknownPromptFieldError,
    build_prompt_set,
    create_manual_prompt_set,
    create_prompt_set,
    engine_registry,
    get_observation_run,
    get_prompt_set,
    list_observation_runs,
    list_prompt_sets,
    price_table_for_estimates,
    prompt_set_of,
    prompts_of,
    token_baselines,
)
from veo.organizations.http import guard
from veo.providers.naver.credentials import datalab_from_settings
from veo.providers.naver.search import NaverSearchClient

router = APIRouter(prefix="/observations", tags=["observations"])

ObservationReader = Annotated[Principal, Depends(guard(Permission.OBSERVATION_READ))]
ObservationRunner_ = Annotated[Principal, Depends(guard(Permission.OBSERVATION_RUN))]
#: 위험 지적을 확정하는 것은 **고객에게 그의 평판에 대해 무엇을 말할지** 정하는 일이다.
#: 보고서 발행과 같은 급이라 별도 권한으로 둔다.
ObservationReviewer = Annotated[Principal, Depends(guard(Permission.OBSERVATION_REVIEW))]
UsageReader = Annotated[Principal, Depends(guard(Permission.USAGE_READ))]

@router.get(
    "/engines",
    response_model=ApiResponse[EnginePayload],
    summary="VEO 가 아는 AI 답변 엔진과 각각의 상태",
    description=(
        "쓸 수 있는 엔진만 돌려주지 않습니다. **아는 엔진을 전부** 돌려주고 각각 왜 쓸 수 "
        "있는지·없는지를 함께 줍니다. 못 쓰는 엔진을 목록에서 빼면 '여기 있는 게 전부' 로 "
        "읽히고, 자격증명만 넣으면 잴 수 있었던 것을 아무도 모른 채 지나갑니다."
    ),
)
def list_engines(principal: ObservationReader, request_id: RequestId) -> ApiResponse[EnginePayload]:
    registry = engine_registry()
    states = registry.states()
    search_off = registry.search_off_support()
    engines = [
        EngineStatus(
            engine=engine,
            state=str(state),
            state_label_ko=_STATE_LABELS_KO.get(state, str(state)),
            usable=state is ProviderState.ENABLED,
            supports_search_off=search_off.get(engine, True),
            search_off_note_ko=(
                "" if search_off.get(engine, True) else SEARCH_OFF_UNAVAILABLE_KO
            ),
        )
        for engine, state in states.items()
    ]
    return ok(
        EnginePayload(
            engines=engines,
            usable_count=sum(1 for entry in engines if entry.usable),
            note_ko=ENGINE_NOTE_KO,
        ),
        request_id,
    )


#: 이 문장은 화면이 늘 함께 보여준다. 목록이 "환자가 묻는 질문 전부" 로 읽히면 안 된다.
HARVEST_NOTE_KO: Final = (
    "사람이 실제로 쓴 질문만 가져옵니다. 지어낸 문장은 하나도 없습니다. "
    "다만 이것이 전부는 아닙니다 — 출처마다 한 번에 가져올 수 있는 상한이 있고, "
    "무엇으로 찾았느냐에 따라 결과가 달라집니다."
)


@router.post(
    "/question-sources",
    response_model=ApiResponse[QuestionHarvestPayload],
    summary="질문을 실제로 모은다 — 지어내지 않는다",
    description=(
        "업체명이나 키워드를 주면 **사람이 실제로 쓴 질문**을 모아 돌려줍니다. "
        "지금은 네이버 지식iN 을 조회합니다.\n\n"
        "**쓸 수 있는 출처만 돌려주지 않습니다.** 아는 출처를 전부 돌려주고 각각 왜 쓸 수 "
        "있는지·없는지를 함께 줍니다 — 구글 관련 질문은 SerpAPI 열쇠가 있어야 켜지고, "
        "없으면 `DISABLED_NO_CREDENTIAL` 로 목록에 남습니다. 목록에서 빼면 열쇠만 넣으면 "
        "얻을 수 있었던 질문을 아무도 모른 채 지나갑니다.\n\n"
        "**의도·퍼널을 자동으로 붙이지 않습니다.** 질문은 실제로 수집한 것인데 분류를 "
        "기계가 지어내면, 그 분류가 집합의 균형 판정을 통과시킵니다. 고르고 분류하는 "
        "것은 사람이 합니다."
    ),
)
def question_sources(
    payload: QuestionSourceRequest,
    principal: ObservationRunner_,
    request_id: RequestId,
) -> ApiResponse[QuestionHarvestPayload]:
    credentials = get_provider_credentials()
    client = NaverSearchClient(credentials=datalab_from_settings(credentials))
    harvest = harvest_questions(
        payload.query,
        naver_client=client,
        serpapi_key=(
            credentials.serpapi_key.get_secret_value()
            if credentials.serpapi_key is not None
            else None
        ),
    )
    return ok(
        QuestionHarvestPayload(
            query=harvest.query,
            sources=[
                QuestionSourcePayload(
                    source=source.source,
                    label_ko=source.label_ko,
                    state=str(source.state),
                    state_reason_ko=source.state_reason_ko,
                    questions=[
                        CollectedQuestionPayload(
                            text=question.text, source=question.source, url=question.url
                        )
                        for question in source.questions
                    ],
                    total=source.total,
                    dropped=source.dropped,
                    failure_reason_ko=source.failure_reason_ko,
                    notes_ko=list(source.notes_ko),
                )
                for source in harvest.sources
            ],
            total_questions=len(harvest.questions),
            note_ko=HARVEST_NOTE_KO,
        ),
        request_id,
    )


@router.post(
    "/prompt-sets",
    response_model=ApiResponse[PromptSetPayload],
    status_code=201,
    summary="프롬프트 집합 만들기",
    description=(
        "질문 목록을 받아 **균형을 먼저 검사하고** 통과한 것만 저장합니다. 브랜드에 "
        "불리한 질문을 빼고 만든 집합으로 재면 노출률이 실제보다 높게 나오고, 그것은 "
        "고객에게 유리한 방향의 거짓이라 더 오래 살아남습니다. 거부될 때는 무엇이 "
        "부족한지 한국어로 그대로 돌려줍니다."
    ),
)
def create(
    payload: PromptSetCreateRequest,
    principal: ObservationRunner_,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
) -> ApiResponse[PromptSetPayload]:
    prompts = [item.model_dump() for item in payload.prompts]
    try:
        built = build_prompt_set(
            name=f"{payload.name}@{payload.version}",
            prompts=prompts,
            exclusions=[item.model_dump() for item in payload.exclusions],
        )
    except PromptSetImbalanceError as exc:
        # 이유를 그대로 옮긴다. "부적합합니다" 로 뭉개면 무엇을 고쳐야 하는지 알 수 없다.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UnknownPromptFieldError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    row = create_prompt_set(
        db,
        principal,
        project_id=payload.project_id,
        name=payload.name,
        version=payload.version,
        locale=payload.locale,
        generation_rule_ko=payload.generation_rule_ko,
        prompt_set=built,
        prompts=prompts,
    )
    db.commit()
    db.refresh(row)
    return ok(_payload(row, built), request_id)


@router.get(
    "/prompt-sets",
    response_model=ApiResponse[PromptSetListPayload],
    summary="프롬프트 집합 목록",
)
def index(
    principal: ObservationReader,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[uuid.UUID | None, Query(description="한 프로젝트로 좁힙니다.")] = None,
) -> ApiResponse[PromptSetListPayload]:
    rows, total = list_prompt_sets(db, principal, project_id=project_id)
    items = [_payload(row, prompt_set_of(row, prompts_of(db, principal, row.id))) for row in rows]
    return ok(PromptSetListPayload(items=items, total=total), request_id)


@router.get(
    "/prompt-sets/{prompt_set_id}",
    response_model=ApiResponse[PromptSetPayload],
    summary="프롬프트 집합 하나",
    description=(
        "`checksum` 은 이 집합의 지문입니다. 비교 두 건이 같은 질문으로 잰 것인지 이 값으로 "
        "확인합니다 — 질문이 다르면 노출률을 나란히 놓을 수 없습니다."
    ),
)
def read(
    prompt_set_id: uuid.UUID,
    principal: ObservationReader,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
) -> ApiResponse[PromptSetPayload]:
    row = get_prompt_set(db, principal, prompt_set_id)
    if row is None:
        raise HTTPException(status_code=404, detail="prompt set not found")
    return ok(_payload(row, prompt_set_of(row, prompts_of(db, principal, row.id))), request_id)


def _payload(row: PromptSetRow, built: PromptSet) -> PromptSetPayload:
    return PromptSetPayload(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        version=row.version,
        locale=row.locale,
        generation_rule_ko=row.generation_rule_ko,
        is_locked=row.is_locked,
        checksum=built.checksum,
        prompts=[
            PromptSummary(
                prompt_id=prompt.prompt_id,
                text=prompt.text,
                intent=str(prompt.intent),
                funnel=str(prompt.funnel),
                subject=str(prompt.subject),
                business_importance=prompt.business_importance,
                persona=prompt.persona,
                locale=prompt.locale,
            )
            for prompt in built.prompts
        ],
        balance_warnings_ko=PromptSet.describe_balance(built.prompts),
    )


@router.post(
    "/runs",
    response_model=ApiResponse[JobPayload],
    status_code=202,
    summary="관측을 시작한다 (즉시 돌아오고, 실행은 뒤에서 돈다)",
    description=(
        "같은 질문을 여러 번 던집니다. AI 답변은 같은 질문에도 매번 달라지므로 한 번의 "
        "결과를 노출률이라고 부를 수 없습니다.\n\n"
        "**202 를 돌려주고 즉시 끝납니다.** 질문 곱하기 엔진 곱하기 반복만큼 외부 AI 를 부르므로 "
        "실행은 몇 분이 걸릴 수 있고, 그것을 요청 안에서 기다리면 게이트웨이가 먼저 "
        "끊습니다. 진행 상황은 `GET /api/jobs/{job_id}`, 결과는 작업이 끝난 뒤 "
        "`result_run_id` 로 `GET /api/observations/runs/{run_id}` 에서 봅니다.\n\n"
        "**모델을 직접 고르셔야 합니다.** 인용을 돌려주는지가 모델마다 다릅니다 — 실측 "
        "결과 `gpt-5`·`gpt-4o` 는 돌려주고 `gpt-4.1`·`gpt-4o-mini` 는 돌려주지 않습니다. "
        "돌려주지 않는 모델로 재면 인용 지표는 0회가 아니라 **측정 불가**로 남습니다.\n\n"
        "`Idempotency-Key` 헤더를 주시면 같은 키로 다시 불러도 **새 실행을 만들지 "
        "않고** 원래 작업을 돌려줍니다. 관측은 돈이 나가는 일이라, 새로고침 한 번이 두 "
        "번 청구되면 안 됩니다."
    ),
)
def run(
    payload: ObservationRunRequest,
    principal: ObservationRunner_,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description="같은 키로 다시 부르면 원래 작업을 돌려줍니다.",
        ),
    ] = None,
) -> ApiResponse[JobPayload]:
    prompt_set_row = get_prompt_set(db, principal, payload.prompt_set_id)
    if prompt_set_row is None:
        raise HTTPException(status_code=404, detail="prompt set not found")

    # 엔진 선택은 **작업을 만들기 전에** 검증한다. 잘못된 엔진 이름 때문에 실패할
    # 작업을 만들어 두면, 사용자는 202 를 받고 몇 초 뒤 실패를 다시 물어봐야 한다.
    try:
        choices = [
            EngineChoice(
                engine=item.engine,
                model=item.model,
                search_mode=SearchMode(item.search_mode),
                account_state=AccountState(item.account_state),
            )
            for item in payload.engines
        ]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    job, created = jobs.submit(
        db,
        principal,
        job_type=JobType.GEO_OBSERVATION_RUN,
        project_id=prompt_set_row.project_id,
        idempotency_key=idempotency_key,
        stages=list(OBSERVATION_STAGES),
        parameters={
            # **큐로 갈 때는 이 값들만 건넌다.** 함수는 프로세스를 건너지 못한다.
            # `observation_work(...)` 의 인자와 하나씩 짝이 맞아야 하고, 하나라도
            # 빠지면 워커가 `KeyError` 로 멈춘다 — 기본값으로 때우면 엉뚱한 조직의
            # 일을 엉뚱한 권한으로 돌린다.
            "organization_id": str(principal.organization_id),
            "user_id": str(principal.user_id),
            "roles": [str(role) for role in principal.roles],
            "session_id": principal.session_id,
            "prompt_set_id": str(payload.prompt_set_id),
            "repetitions": payload.repetitions,
            "allow_below_floor": payload.allow_below_floor,
            "engines": [
                {
                    "engine": choice.engine,
                    "model": choice.model,
                    "search_mode": str(choice.search_mode),
                    "account_state": str(choice.account_state),
                }
                for choice in choices
            ],
        },
    )
    job_id = job.id
    db.commit()
    db.refresh(job)

    if created:
        dispatch(
            job_id,
            observation_work(
                organization_id=principal.organization_id,
                user_id=principal.user_id,
                roles=principal.roles,
                session_id=principal.session_id,
                prompt_set_id=payload.prompt_set_id,
                choices=choices,
                repetitions=payload.repetitions,
                allow_below_floor=payload.allow_below_floor,
            ),
            job_type=JobType.GEO_OBSERVATION_RUN,
            parameters=job.parameters,
        )

    return ok(job_payload(job), request_id)


@router.post(
    "/runs/manual",
    response_model=ApiResponse[JobPayload],
    status_code=202,
    summary="검색어를 직접 잰다 (수동 측정)",
    description=(
        "관리자가 그 자리에서 고른 검색어를 잽니다. 발행된 질문 집합이 필요 없습니다.\n\n"
        "**이 실행은 추이에 올라가지 않습니다.** 정기 관측과 조건(엔진·모델·검색모드)이 "
        "똑같아도 서로 다른 측정입니다 — 정기 관측은 무엇을 언제 물을지가 사람 손을 떠나 "
        "있고, 이쪽은 사람이 그 순간 고릅니다. 섞으면 잘 나오는 검색어를 골라 재는 것만으로 "
        "그래프가 올라갑니다(ADR 0015). 코드가 섞는 것을 거부합니다.\n\n"
        "**돈이 나갑니다.** 누르기 전에 `POST /api/observations/estimates` 로 몇 번 부르는지 "
        "확인하십시오.\n\n"
        "`Idempotency-Key` 헤더를 주시면 같은 키로 다시 불러도 새 실행을 만들지 않습니다."
    ),
)
def run_manual(
    payload: ManualRunRequest,
    principal: ObservationRunner_,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description="같은 키로 다시 부르면 원래 작업을 돌려줍니다.",
        ),
    ] = None,
) -> ApiResponse[JobPayload]:
    # 엔진을 먼저 검증한다. 잘못된 엔진 이름 때문에 실패할 작업을 만들어 두면, 부르는
    # 쪽은 202 를 받고 몇 초 뒤 실패를 다시 물어봐야 한다. 즉석 집합도 남는다.
    try:
        choices = [
            EngineChoice(
                engine=item.engine,
                model=item.model,
                search_mode=SearchMode(item.search_mode),
                account_state=AccountState(item.account_state),
            )
            for item in payload.engines
        ]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        prompt_set_row, _ = create_manual_prompt_set(
            db,
            principal,
            project_id=payload.project_id,
            questions=payload.questions,
            locale=payload.locale,
        )
    except PromptSetImbalanceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    job, created = jobs.submit(
        db,
        principal,
        job_type=JobType.GEO_OBSERVATION_RUN,
        project_id=payload.project_id,
        idempotency_key=idempotency_key,
        stages=list(OBSERVATION_STAGES),
        parameters={
            # **큐로 갈 때는 이 값들만 건넌다.** 함수는 프로세스를 건너지 못한다.
            # `observation_work(...)` 의 인자와 하나씩 짝이 맞아야 하고, 하나라도
            # 빠지면 워커가 `KeyError` 로 멈춘다 — 기본값으로 때우면 엉뚱한 조직의
            # 일을 엉뚱한 권한으로 돌린다.
            "organization_id": str(principal.organization_id),
            "user_id": str(principal.user_id),
            "roles": [str(role) for role in principal.roles],
            "session_id": principal.session_id,
            "prompt_set_id": str(prompt_set_row.id),
            "kind": "MANUAL",
            "repetitions": payload.repetitions,
            "allow_below_floor": payload.allow_below_floor,
            "engines": [
                {
                    "engine": choice.engine,
                    "model": choice.model,
                    "search_mode": str(choice.search_mode),
                    "account_state": str(choice.account_state),
                }
                for choice in choices
            ],
        },
    )
    job_id = job.id
    prompt_set_id = prompt_set_row.id
    db.commit()
    db.refresh(job)

    if created:
        dispatch(
            job_id,
            observation_work(
                organization_id=principal.organization_id,
                user_id=principal.user_id,
                roles=principal.roles,
                session_id=principal.session_id,
                prompt_set_id=prompt_set_id,
                choices=choices,
                repetitions=payload.repetitions,
                allow_below_floor=payload.allow_below_floor,
            ),
            job_type=JobType.GEO_OBSERVATION_RUN,
            parameters=job.parameters,
        )

    return ok(job_payload(job), request_id)


@router.post(
    "/estimates",
    response_model=ApiResponse[EstimatePayload],
    summary="누르기 전에 얼마나 드는가",
    description=(
        "**호출 수는 정확합니다** — 질문 수 x 조건 수 x 반복 수입니다.\n\n"
        "**금액은 근거가 있을 때만 냅니다.** 금액은 단가 x 토큰인데, 토큰은 재 봐야 "
        "압니다. 같은 조건(엔진·모델·검색모드)으로 이미 잰 답변이 있으면 그 중앙값으로 "
        "계산하고, 없으면 금액 자리를 `null` 로 둡니다. 그 `null` 은 0원이 아니라 "
        "**모른다**는 뜻이고, 무엇이 있어야 알 수 있는지는 `remedies_ko` 에 적힙니다.\n\n"
        "일부 조건만 계산되면 합계도 내지 않습니다. 부분 합계는 전체처럼 읽히고, 그 값에 "
        "맞춰 예산을 잡게 됩니다."
    ),
)
def estimate(
    payload: EstimateRequest,
    principal: UsageReader,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
) -> ApiResponse[EstimatePayload]:
    try:
        slots = [
            (item.engine, item.model, SearchMode(item.search_mode)) for item in payload.engines
        ]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    plans = plan_slots(
        prompt_count=payload.question_count,
        slots=slots,
        repetitions=payload.repetitions,
    )
    result = estimate_work(
        plans,
        prices=price_table_for_estimates(),
        baselines=token_baselines(db, principal),
    )
    return ok(
        EstimatePayload(
            total_calls=result.total_calls,
            amount_usd=result.amount_usd,
            measurement=result.measurement,
            slots=[
                SlotEstimatePayload(
                    slot=item.slot,
                    engine=item.engine,
                    model=item.model,
                    search_mode=item.search_mode,
                    calls=item.calls,
                    amount_usd=item.amount_usd,
                    basis=item.basis,
                    baseline_samples=item.baseline_samples,
                    reason_ko=item.reason_ko,
                )
                for item in result.slots
            ],
            remedies_ko=list(result.remedies_ko),
            summary_ko=result.summary_ko,
        ),
        request_id,
    )


@router.get(
    "/spend",
    response_model=ApiResponse[SpendPayload],
    summary="이번 달 AI 호출 사용량과 비용",
    description=(
        "저장된 답변에서 셉니다. **금액을 못 낸 호출을 0원으로 더하지 않습니다** — "
        "더하면 합계가 '예산 안'처럼 보이는데 자료가 그것을 뒷받침하지 않습니다.\n\n"
        "가격표가 비어 있어도 이 응답은 쓸모가 있습니다. 호출 수와 토큰 수는 언제나 "
        "실측이고, 금액을 못 낸 이유마다 무엇을 하면 되는지가 함께 나옵니다."
    ),
)
def spend(
    principal: UsageReader,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
    month: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$", description="예: 2026-07")] = None,
) -> ApiResponse[SpendPayload]:
    report = spend_for_month(db, principal=principal, month=month)
    budget = report.budget
    return ok(
        SpendPayload(
            month=budget.month,
            total_calls=report.total_calls,
            measured_calls=budget.measured_calls,
            unmeasurable_calls=budget.unmeasurable_calls,
            measured_cost_usd=budget.spent_usd,
            input_tokens=report.input_tokens,
            output_tokens=report.output_tokens,
            measurement=str(budget.measurement),
            engines=[
                EngineSpendPayload(
                    engine=usage.engine,
                    calls=usage.calls,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    measured_cost_usd=usage.measured_cost_usd,
                    unmeasurable_calls=usage.unmeasurable_calls,
                )
                for usage in report.engines
            ],
            remedies_ko=list(report.remedies_ko()),
            summary_ko=budget.alert_line_ko(),
        ),
        request_id,
    )


@router.get(
    "/runs",
    response_model=ApiResponse[ObservationRunListPayload],
    summary="관측 실행 이력",
    description="최신순입니다. 부분 실행도 그대로 들어 있습니다 — 빼면 그 실행이 없던 일이 됩니다.",
)
def run_index(
    principal: ObservationReader,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[uuid.UUID | None, Query()] = None,
    kind: Annotated[
        str | None,
        Query(
            pattern="^(SCHEDULED|MANUAL)$",
            description=(
                "종류로 거릅니다. 비워 두면 **둘 다** 나옵니다 — 목록에서 조용히 빼면 "
                "그 실행이 없던 일이 되므로, 거르는 것은 부르는 쪽이 정합니다."
            ),
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ApiResponse[ObservationRunListPayload]:
    rows, total = list_observation_runs(
        db, principal, project_id=project_id, kind=kind, limit=limit
    )
    return ok(
        ObservationRunListPayload(items=[_run_payload(row) for row in rows], total=total),
        request_id,
    )


@router.get(
    "/runs/{run_id}",
    response_model=ApiResponse[ObservationRunDetailPayload],
    summary="관측 실행 하나와 그 지표",
    description=(
        "**`value` 가 `null` 인 것과 `0.0` 인 것은 정반대의 뜻입니다.** `null` 은 잴 수 "
        "없었다는 뜻이고 `0.0` 은 쟀는데 한 번도 없었다는 뜻입니다.\n\n"
        "인용률의 분모는 **출처를 확인할 수 있었던 응답**뿐입니다. 엔진이 출처를 밝히지 "
        "않은 응답을 분모에 넣으면 인용률이 낮게 나오고, 그 낮은 값은 사이트 탓처럼 "
        "읽힙니다 — 실제로는 그 모델이 출처를 알려주지 않은 것입니다."
    ),
)
def run_read(
    run_id: uuid.UUID,
    principal: ObservationReader,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
) -> ApiResponse[ObservationRunDetailPayload]:
    row = get_observation_run(db, principal, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="observation run not found")

    measured = visibility_metrics(
        answer_facts(db, principal, row.id),
        prompts_planned=row.executions_planned,
        run_is_complete=row.is_complete,
    )
    return ok(
        ObservationRunDetailPayload(
            run=_run_payload(row),
            metrics=VisibilityMetricsPayload.model_validate(measured.as_dict()),
        ),
        request_id,
    )


@router.get(
    "/runs/{run_id}/risks",
    response_model=ApiResponse[RiskFindingsPayload],
    summary="관측 실행이 남긴 위험 판정 (검수 게이트 통과 후)",
    description=(
        "**`customer` 와 `internal` 은 용도가 다릅니다.** `customer` 는 고객 문서에 실어도 "
        "되는 것만 담으며, 검수되지 않은 치명·높음 지적의 문장은 들어 있지 않습니다. "
        "`internal` 은 내부 화면 전용이고 보류된 지적의 원문을 포함하므로 공개 리포트 "
        "경로에 연결하면 안 됩니다.\n\n"
        "**`customer.findings` 가 비어 있다고 위험이 없는 것이 아닙니다.** 지금 규칙으로 "
        "낼 수 있는 위험 유형은 방법론 8종 가운데 1종(동명 업체 혼동)뿐이고, 나머지 7종이 "
        "왜 없는지는 `kinds_not_yet_produced` 가 말합니다.\n\n"
        "위험 영역에는 종합 점수가 없습니다. 심각도별 건수만 보고합니다."
    ),
)
def run_risks(
    run_id: uuid.UUID,
    principal: ObservationReader,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
) -> ApiResponse[RiskFindingsPayload]:
    row = get_observation_run(db, principal, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="observation run not found")

    # 게이트를 반드시 지난다. 자동 판정을 그대로 내보내면 검수되지 않은 지적이 고객
    # 문서에 실린다 — `risk/INTEGRATION_REQUEST.md` 요청 #5 가 요구하는 것이 이것이다.
    gated = apply_publication_gate(reviews_for_run(db, principal, run_id))
    return ok(
        RiskFindingsPayload(
            customer=gated.as_customer_payload(),
            internal=gated.as_internal_payload(),
            kinds_not_yet_produced=[dict(item) for item in assessment_kinds_not_yet_produced()],
        ),
        request_id,
    )


@router.get(
    "/review-queue",
    response_model=ApiResponse[ReviewQueuePayload],
    summary="사람이 확인해야 하는 위험 지적",
    description=(
        "심각한 것부터 나옵니다. 결론이 난 건은 빠지지만 **근거 보강 대기는 남습니다** — "
        "그것은 끝난 것이 아니라 멈춰 있는 것이고, 목록에서 빠지면 영영 아무도 다시 보지 "
        "않습니다.\n\n"
        "`claim_text` 는 기계가 답변에서 잘라낸 **그 문장 그대로**입니다. 요약하면 "
        "'백세온담한의원'과 '온담한의원'의 차이가 사라지고, 그 차이가 이 판정의 전부입니다."
    ),
)
def review_queue(
    principal: ObservationReviewer,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
) -> ApiResponse[ReviewQueuePayload]:
    items = review_service.pending_for_review(db, principal)
    return ok(
        ReviewQueuePayload(
            items=[_queue_item(db, principal, row_id, review) for row_id, review in items],
            total=len(items),
            rejection_reasons=[
                {"value": reason.value, "label_ko": reason.label_ko}
                for reason in RejectionReason
            ],
        ),
        request_id,
    )


@router.post(
    "/review-queue/{assessment_id}/claim",
    response_model=ApiResponse[ReviewedItemPayload],
    summary="이 건을 맡는다",
    description=(
        "자동 판정이 사람 앞에 놓이는 **유일한 입구**입니다. 맡지 않은 건은 판정할 수 "
        f"없으며, 맡은 뒤 {int(review_service.CLAIM_EXPIRES_AFTER.total_seconds() // 60)}분 "
        "동안 판단이 없으면 점유가 풀려 다른 검수자가 집을 수 있습니다 — 반납을 눌러야만 "
        "풀리게 두면 큐가 서서히 잠깁니다."
    ),
)
def review_claim(
    assessment_id: uuid.UUID,
    principal: ObservationReviewer,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
) -> ApiResponse[ReviewedItemPayload]:
    return _review_call(
        db,
        request_id,
        lambda: review_service.claim(db, principal, assessment_id, request_id=request_id),
    )


@router.post(
    "/review-queue/{assessment_id}/release",
    response_model=ApiResponse[ReviewedItemPayload],
    summary="판단하지 않고 반납한다",
    description="판단하지 않았다는 사실도 기록으로 남습니다.",
)
def review_release(
    assessment_id: uuid.UUID,
    principal: ObservationReviewer,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
) -> ApiResponse[ReviewedItemPayload]:
    return _review_call(
        db,
        request_id,
        lambda: review_service.release(db, principal, assessment_id, request_id=request_id),
    )


@router.post(
    "/review-queue/{assessment_id}/decide",
    response_model=ApiResponse[ReviewedItemPayload],
    summary="검수 결론을 남긴다",
    description=(
        "**자동 판정은 이 요청으로 바뀌지 않습니다.** 사람의 결론은 별도 칸에 쌓이고, "
        "두 기록이 어긋나는 경우까지 나란히 남습니다 — 사람이 옳다고 해서 기계가 뭐라고 "
        "했는지를 지우면 자동 판정이 어디서 빗나가는지 셀 수 없게 됩니다.\n\n"
        "맡지 않은 건은 판정할 수 없습니다. 전이 규칙이 그 간선을 선언하지 않았습니다."
    ),
)
def review_decide(
    assessment_id: uuid.UUID,
    body: ReviewDecisionRequest,
    principal: ObservationReviewer,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
) -> ApiResponse[ReviewedItemPayload]:
    if body.decision == "REJECTED" and body.rejection_reason is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "기각에는 사유가 필요합니다. 사유 없는 기각은 자동 판정이 어디서 "
                "빗나가는지 세는 데 아무 도움이 되지 않습니다."
            ),
        )
    return _review_call(
        db,
        request_id,
        lambda: review_service.decide(
            db,
            principal,
            assessment_id,
            target=ReviewStage(body.decision),
            rejection_reason=(
                RejectionReason(body.rejection_reason) if body.rejection_reason else None
            ),
            note_ko=body.note_ko,
            request_id=request_id,
        ),
    )


def _review_call(
    db: Session, request_id: str, action: Callable[[], ReviewedAssessment]
) -> ApiResponse[ReviewedItemPayload]:
    """검수 호출 셋이 공유하는 것: 실패를 어떤 상태 코드로 말하는가.

    409 와 422 를 구분한다. 전자는 **지금은 안 되지만 나중엔 될 수 있다**(다른 사람이
    맡고 있다), 후자는 **이 순서로는 안 된다**(맡지도 않고 판정하려 한다). 둘을 합치면
    검수자가 새로고침만 반복하게 된다.
    """
    try:
        moved = action()
    except review_service.AssessmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="assessment not found") from exc
    except review_service.ReviewConflictError as exc:
        raise HTTPException(status_code=409, detail=exc.message_ko) from exc
    except IllegalReviewTransitionError as exc:
        raise HTTPException(status_code=422, detail=exc.message_ko) from exc
    db.commit()
    return ok(
        ReviewedItemPayload(
            assessment_id=uuid.UUID(moved.assessment.assessment_id),
            stage=moved.stage.value,
            stage_label_ko=describe_stage_ko(moved.stage),
            stored_as=moved.stage.to_contract_state().value,
            is_reviewed=moved.is_reviewed,
            disagrees_with_automation=moved.disagrees,
        ),
        request_id,
    )


def _queue_item(
    db: Session, principal: Principal, row_id: uuid.UUID, review: ReviewedAssessment
) -> ReviewQueueItem:
    from veo.db.models.observation import ClaimAssessment as ClaimAssessmentRow

    row = db.get(ClaimAssessmentRow, row_id)
    held_by = row.claimed_by if row is not None else None
    return ReviewQueueItem(
        assessment_id=row_id,
        kind=review.assessment.kind.value,
        band_label_ko=review.assessment.band.label_ko,
        severity=review.assessment.severity.value,
        claim_text=review.assessment.claim_text,
        automated_verdict=review.assessment.automated.verdict.value,
        automated_rationale_ko=review.assessment.automated.rationale_ko,
        stage=review.stage.value,
        stage_label_ko=describe_stage_ko(review.stage),
        is_held_by_someone=held_by is not None and held_by != principal.user_id,
        is_mine=held_by == principal.user_id,
    )


def _run_payload(row: ObservationRunRow) -> ObservationRunPayload:
    detail = dict(row.skipped_detail or {})
    return ObservationRunPayload(
        id=row.id,
        project_id=row.project_id,
        prompt_set_id=row.prompt_set_id,
        kind=row.kind,
        status=row.status,
        is_complete=row.is_complete,
        engines=[str(engine) for engine in row.engines or ()],
        repetitions_per_prompt=row.repetitions_per_prompt,
        executions_planned=row.executions_planned,
        executions_attempted=row.executions_attempted,
        executions_valid=row.executions_valid,
        executions_skipped=row.executions_skipped,
        stopped_reason=row.stopped_reason,
        summary_ko=str(detail.get("summary_ko", "")),
        unpriced_calls=int(detail.get("unpriced_calls", 0) or 0),
        total_cost_usd=float(detail.get("total_cost_usd", 0.0) or 0.0),
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


__all__ = ["router"]
