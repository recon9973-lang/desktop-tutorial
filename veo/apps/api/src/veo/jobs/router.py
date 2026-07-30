"""``/jobs`` — 요청 밖에서 도는 일의 진행 상황.

관측처럼 몇 분 걸리는 일은 요청 안에서 돌 수 없다(지침서 0-G). 실행을 시작한 요청은
곧바로 작업 하나를 돌려주고, 화면은 여기로 물어본다.

**이 화면이 가장 조심해야 하는 것은 `RUNNING` 이다.** 서버가 재시작하면 돌던 작업은
그대로 죽는데, DB 의 행은 `RUNNING` 인 채 남는다. 그것을 계속 "실행 중" 이라고 보여주면
사용자는 오지 않을 결과를 기다린다. 그래서 `is_stale` 을 함께 준다 — 참이면 **끝났는지
아닌지 우리도 모른다**는 뜻이고, 화면은 그렇게 말해야 한다.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal
from veo.contracts.enums import JobType
from veo.contracts.envelope import ApiResponse
from veo.db.models.analysis import Job as JobRow
from veo.db.session import get_db
from veo.jobs import service
from veo.jobs.schemas import JobListPayload, JobPayload
from veo.organizations.http import guard

router = APIRouter(prefix="/jobs", tags=["jobs"])

DbSession = Annotated[Session, Depends(get_db)]
JobReader = Annotated[Principal, Depends(guard(Permission.SCAN_READ))]

NOT_FOUND_KO = "작업을 찾을 수 없습니다."


def job_payload(row: JobRow) -> JobPayload:
    return JobPayload(
        id=row.id,
        type=row.type,
        status=row.status,
        is_stale=service.is_stale(row),
        progress=row.progress,
        current_stage=row.current_stage,
        stages=[str(stage) for stage in (row.stages or [])],
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
        attempts=row.attempts,
        error_code=row.error_code,
        safe_error_message=row.safe_error_message,
        result_run_id=row.result_run_id,
        partial_result_available=row.partial_result_available,
        note_ko=service.status_note_ko(row),
    )


@router.get(
    "",
    response_model=ApiResponse[JobListPayload],
    summary="최근 작업",
    description="최신순입니다. 실패한 작업도 그대로 들어 있습니다 — 빼면 없던 일이 됩니다.",
)
def index(
    session: DbSession,
    principal: JobReader,
    request_id: RequestId,
    job_type: Annotated[
        JobType | None, Query(description="작업 종류로 거릅니다.", alias="type")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ApiResponse[JobListPayload]:
    rows = service.recent(session, principal, job_type=job_type, limit=limit)
    payload = JobListPayload(
        items=[job_payload(row) for row in rows],
        total=len(rows),
    )
    return ok(payload, request_id)


@router.get(
    "/{job_id}",
    response_model=ApiResponse[JobPayload],
    summary="작업 하나의 진행 상황",
    description=(
        "**`status` 만 보고 그리지 마십시오.** `is_stale` 이 참이면 그 작업의 소식이 "
        "끊긴 것이고, 끝났는지 아닌지 저희도 알지 못합니다. 실행 중과 같게 표시하면 "
        "사용자가 오지 않을 결과를 기다리게 됩니다.\n\n"
        "다른 조직의 작업은 403이 아니라 **404**입니다. 존재 여부 자체를 알려주지 "
        "않습니다."
    ),
)
def read(
    job_id: uuid.UUID,
    session: DbSession,
    principal: JobReader,
    request_id: RequestId,
) -> ApiResponse[JobPayload]:
    try:
        row = service.read(session, principal, job_id)
    except service.JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail=NOT_FOUND_KO) from exc
    return ok(job_payload(row), request_id)


__all__ = ["job_payload", "router"]
