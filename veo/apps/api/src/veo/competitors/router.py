"""``/competitors`` — competitor comparisons and observed share of voice.

This router is **not mounted here**. ``veo.api.app`` belongs to the integrator; see
``INTEGRATION_REQUEST.md``. Everything below is a plain :class:`~fastapi.APIRouter` that
can be included under the API prefix without further wiring.

Permissions follow the platform matrix exactly: ``competitor:write`` to produce a
comparison, ``competitor:read`` to list and read one. Both are declared as route
dependencies so the check runs before the body is parsed and before any row is looked up
— which is what keeps a read-only caller from telling a missing comparison apart from a
forbidden one.

A refused comparison is a **200**, not an error. "These two were not measured the same
way" is the answer to the question, and it belongs in the body next to the competitor it
concerns, in Korean, with the field that blocked it named. Only a malformed request, an
unauditable score or an unknown competitor produce a non-2xx.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal
from veo.competitors.from_observation import (
    ComparisonSetTooSmallError,
    observed_visibility_from_run,
)
from veo.competitors.schemas import (
    ComparisonCreateRequest,
    ComparisonPayload,
    ComparisonSummaryPayload,
)
from veo.competitors.service import (
    ComparisonRecord,
    ComparisonStore,
    CompetitorDirectory,
    InMemoryComparisonStore,
    MeasurementRejected,
    SqlCompetitorDirectory,
    create_comparison,
    get_comparison,
    list_comparisons,
    summaries,
)
from veo.contracts.enums import ErrorCode
from veo.contracts.envelope import ApiResponse, PagedResponse
from veo.db.session import get_db
from veo.organizations.errors import ReferenceNotFoundError
from veo.organizations.http import PageParams, api_error, guard, not_found, paged

router = APIRouter(prefix="/competitors", tags=["competitors"])

DbSession = Annotated[Session, Depends(get_db)]
Reader = Annotated[Principal, Depends(guard(Permission.COMPETITOR_READ))]
Writer = Annotated[Principal, Depends(guard(Permission.COMPETITOR_WRITE))]

NOT_FOUND_KO = "비교 결과를 찾을 수 없습니다."

#: Process-local until the schema has somewhere to keep a comparison.
#: ``INTEGRATION_REQUEST.md`` §1. Comparisons do not survive a restart and are not shared
#: between workers; the store is a dependency so swapping it is a one-line change.
_STORE = InMemoryComparisonStore()


def get_competitor_directory(session: DbSession) -> CompetitorDirectory:
    return SqlCompetitorDirectory(session)


def get_comparison_store() -> ComparisonStore:
    return _STORE


Directory = Annotated[CompetitorDirectory, Depends(get_competitor_directory)]
Store = Annotated[ComparisonStore, Depends(get_comparison_store)]


@router.post(
    "/comparisons",
    response_model=ApiResponse[ComparisonPayload],
    summary="같은 조건에서 측정된 경쟁사 비교를 생성",
    description=(
        "자사 사이트와 경쟁사들의 **이미 끝난 측정**을 받아 비교합니다. 이 엔드포인트는 "
        "외부에 요청을 보내지 않습니다.\n\n"
        "측정 조건이 다른 상대는 **비교하지 않고 거부하며, 거부 사유를 한국어로 함께 "
        "돌려줍니다.** 거부된 상대에게는 어떤 델타도 계산하지 않습니다. "
        "`allow_scope_variance` 는 검사 페이지 수 차이 **하나만** 예외로 허용하며, "
        "허용해도 그 차이는 결과에 그대로 남습니다. 방법론·기기·렌더러·언어·제공자·"
        "측정 시점 차이는 이 옵션으로도 통과하지 않습니다.\n\n"
        "`share_of_voice` 는 관측된 AI 가시성이며 준비도 점수와 별개 블록입니다. "
        "두 값을 합산하지 마십시오."
    ),
)
def create(
    payload: ComparisonCreateRequest,
    principal: Writer,
    directory: Directory,
    store: Store,
    request_id: RequestId,
    db: DbSession,
) -> ApiResponse[ComparisonPayload]:
    try:
        record = create_comparison(
            principal,
            payload,
            directory=directory,
            store=store,
            observed_visibility=lambda actor, run_id: observed_visibility_from_run(
                db, actor, run_id
            ),
        )
    except ComparisonSetTooSmallError as exc:
        # 측정이 거부된 것이 아니라 **비교 집합이 성립하지 않는** 경우다. 화면에서
        # 안내할 말이 다르다 — "경쟁사를 먼저 등록해 주십시오".
        raise api_error(422, ErrorCode.VALIDATION_FAILED, str(exc)) from exc
    except LookupError as exc:
        raise not_found(str(exc)) from exc
    except ReferenceNotFoundError as exc:
        raise not_found(exc.message_ko) from exc
    except MeasurementRejected as exc:
        # 422 spelled out: the Starlette constant for it was renamed, and pinning a
        # deprecated name here would make this module fail on a routine upgrade.
        raise api_error(422, ErrorCode.VALIDATION_FAILED, exc.message_ko) from exc

    return ok(_payload(record), request_id)


@router.get(
    "/comparisons",
    response_model=PagedResponse[ComparisonSummaryPayload],
    summary="프로젝트의 비교 결과 목록 (최신순)",
    description=(
        "요약만 돌려줍니다. 비교 가능 수와 거부 수를 함께 보여 주어, 목록에서 "
        "'경쟁사 4곳과 비교' 와 '4곳 중 1곳만 비교' 를 구분할 수 있게 합니다."
    ),
)
def index(
    principal: Reader,
    store: Store,
    request_id: RequestId,
    pagination: PageParams,
    project_id: Annotated[
        uuid.UUID, Query(description="비교 결과가 속한 프로젝트입니다.")
    ],
) -> PagedResponse[ComparisonSummaryPayload]:
    records, total = list_comparisons(
        principal,
        project_id,
        store=store,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    rows = [ComparisonSummaryPayload(**summary) for summary in summaries(records)]
    return paged(rows, request_id, pagination=pagination, total_items=total)


@router.get(
    "/comparisons/{comparison_id}",
    response_model=ApiResponse[ComparisonPayload],
    summary="비교 결과 상세",
    description=(
        "생성 시점의 문서를 그대로 돌려줍니다. 거부된 상대의 사유와, 예외로 허용된 "
        "조건 차이도 그대로 남아 있습니다."
    ),
)
def read(
    comparison_id: uuid.UUID,
    principal: Reader,
    store: Store,
    request_id: RequestId,
) -> ApiResponse[ComparisonPayload]:
    record = get_comparison(principal, comparison_id, store=store)
    if record is None:
        raise not_found(NOT_FOUND_KO)
    return ok(_payload(record), request_id)


def _payload(record: ComparisonRecord) -> ComparisonPayload:
    document = record.payload
    return ComparisonPayload(
        id=record.id,
        project_id=record.project_id,
        created_at=record.created_at,
        allow_scope_variance=document["allow_scope_variance"],
        summary_ko=document["summary_ko"],
        confidence=document["confidence"],
        confidence_level_ko=document["confidence_level_ko"],
        confidence_basis_ko=document["confidence_basis_ko"],
        comparable_count=document["comparable_count"],
        refused_count=document["refused_count"],
        baseline=document["baseline"],
        comparison_set=document["comparison_set"],
        pairs=document["pairs"],
        share_of_voice=document["share_of_voice"],
        separation_note_ko=document["separation_note_ko"],
    )


__all__ = ["router"]
