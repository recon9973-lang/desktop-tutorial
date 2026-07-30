"""``/observations`` — 프롬프트 집합과 엔진 상태.

이 라우터가 없어서 **완성된 관측 엔진에 손이 닿지 않았다.** `src/` 안에서
`ObservationRunner` 를 부르는 코드가 하나도 없었고, 제공자 어댑터·인용 탐지·위험 평가·
검수 대기열이 전부 테스트에서만 돌았다.

관측 실행(`POST /observations/runs`)은 아직 여기 없다. 실행은 답변 원문 저장, 브랜드
식별자, 인용·언급 기록을 함께 남겨야 하고 그것들은 별도의 판에서 붙인다. 지금 얹으면
반쯤 저장되는 실행이 생기는데, 관측 실행은 immutable 기록이라 반쯤 남은 것이 가장 나쁘다.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal
from veo.contracts.enums import ProviderState
from veo.contracts.envelope import ApiResponse
from veo.db.models.observation import PromptSet as PromptSetRow
from veo.db.session import get_db
from veo.observations.prompts import PromptSet, PromptSetImbalanceError
from veo.observations.providers.registry import _STATE_LABELS_KO
from veo.observations.schemas import (
    EnginePayload,
    EngineStatus,
    PromptSetCreateRequest,
    PromptSetListPayload,
    PromptSetPayload,
    PromptSummary,
)
from veo.observations.service import (
    ENGINE_NOTE_KO,
    UnknownPromptFieldError,
    build_prompt_set,
    create_prompt_set,
    engine_registry,
    get_prompt_set,
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


__all__ = ["router"]
