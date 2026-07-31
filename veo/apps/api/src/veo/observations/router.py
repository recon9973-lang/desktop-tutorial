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
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal
from veo.contracts.enums import JobType, ProviderState
from veo.contracts.envelope import ApiResponse
from veo.db.models.observation import ObservationRun as ObservationRunRow
from veo.db.models.observation import PromptSet as PromptSetRow
from veo.db.session import get_db
from veo.jobs import service as jobs
from veo.jobs.execution import run_detached
from veo.jobs.router import job_payload
from veo.jobs.schemas import JobPayload
from veo.observations.execution import EngineChoice, answer_facts
from veo.observations.findings import assessment_kinds_not_yet_produced, reviews_for_run
from veo.observations.jobs import OBSERVATION_STAGES, observation_work
from veo.observations.metrics import visibility_metrics
from veo.observations.prompts import PromptSet, PromptSetImbalanceError
from veo.observations.providers.registry import _STATE_LABELS_KO
from veo.observations.review.gating import apply_publication_gate
from veo.observations.runs import AccountState, SearchMode
from veo.observations.schemas import (
    EnginePayload,
    EngineStatus,
    ObservationRunDetailPayload,
    ObservationRunListPayload,
    ObservationRunPayload,
    ObservationRunRequest,
    PromptSetCreateRequest,
    PromptSetListPayload,
    PromptSetPayload,
    PromptSummary,
    RiskFindingsPayload,
    VisibilityMetricsPayload,
)
from veo.observations.service import (
    ENGINE_NOTE_KO,
    UnknownPromptFieldError,
    build_prompt_set,
    create_prompt_set,
    engine_registry,
    get_observation_run,
    get_prompt_set,
    list_observation_runs,
    list_prompt_sets,
    prompt_set_of,
    prompts_of,
)
from veo.organizations.http import guard

router = APIRouter(prefix="/observations", tags=["observations"])

ObservationReader = Annotated[Principal, Depends(guard(Permission.OBSERVATION_READ))]
ObservationRunner_ = Annotated[Principal, Depends(guard(Permission.OBSERVATION_RUN))]

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
    states = engine_registry().states()
    engines = [
        EngineStatus(
            engine=engine,
            state=str(state),
            state_label_ko=_STATE_LABELS_KO.get(state, str(state)),
            usable=state is ProviderState.ENABLED,
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
        run_detached(
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
        )

    return ok(job_payload(job), request_id)


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
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ApiResponse[ObservationRunListPayload]:
    rows, total = list_observation_runs(db, principal, project_id=project_id, limit=limit)
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


def _run_payload(row: ObservationRunRow) -> ObservationRunPayload:
    detail = dict(row.skipped_detail or {})
    return ObservationRunPayload(
        id=row.id,
        project_id=row.project_id,
        prompt_set_id=row.prompt_set_id,
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
