"""``/reports`` — immutable report versions and their exports.

**This router is deliberately not mounted.** ``veo.api.app`` belongs to the integrator;
including it there is their call, not this worker's. See ``INTEGRATION_REQUEST.md``.

Conventions inherited from the rest of the API:

* Another organization's row is **404, never 403** — a 403 confirms it exists.
* ``REPORT_READ`` reads. ``REPORT_EXPORT`` is additionally required to export, because an
  export leaves the product. Creating a version additionally requires ``SCAN_RUN``: a
  version is the record of a measurement, and whoever may not run a measurement may not
  publish one either. There is no ``REPORT_WRITE`` in the matrix
  (``INTEGRATION_REQUEST.md`` #3).
* ``EVIDENCE_READ`` is checked *inside* the handler rather than as a route dependency. A
  caller without it is not refused the report — they receive it with the raw excerpts
  removed and every score intact.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, build_meta, ok
from veo.authz import CurrentPrincipal, Permission, require
from veo.contracts.enums import ErrorCode
from veo.contracts.envelope import ApiError, ApiResponse, PagedResponse, PageInfo
from veo.db.session import get_db
from veo.reports.render.csv import CSV_CONTENT_TYPE
from veo.reports.render.html import HTML_CONTENT_TYPE
from veo.reports.render.xlsx import XLSX_CONTENT_TYPE
from veo.reports.repository import SqlReportRepository
from veo.reports.schemas import (
    CreatedVersionPayload,
    CreateReportRequest,
    CreateVersionRequest,
    ReportVersionPayload,
    VersionSummaryPayload,
    created_payload,
    read_payload,
    summary_payload,
)
from veo.reports.service import (
    ExportFormat,
    ReportNotFoundError,
    ReportService,
    ReportVersionConflictError,
)

__all__ = ["get_report_service", "router"]

router = APIRouter(prefix="/reports", tags=["reports"])


def get_report_service(session: Annotated[Session, Depends(get_db)]) -> ReportService:
    return ReportService(SqlReportRepository(session))


ServiceDep = Annotated[ReportService, Depends(get_report_service)]
ReportIdPath = Annotated[uuid.UUID, Path(description="리포트 식별자입니다.")]
VersionPath = Annotated[int, Path(ge=1, description="리포트 버전 번호입니다.")]


def _error(status_code: int, code: ErrorCode, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code, detail=ApiError.of(code, message).model_dump(mode="json")
    )


def _not_found() -> HTTPException:
    """One answer for "not there" and "not yours"."""
    return _error(
        status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND, "요청하신 리포트를 찾을 수 없습니다."
    )


def _conflict(message: str) -> HTTPException:
    return _error(status.HTTP_409_CONFLICT, ErrorCode.CONFLICT, message)


_CREATE_DESCRIPTION = (
    "완료된 진단을 고정 스냅샷으로 동결해 새 버전을 발행합니다. 발행된 버전은 수정할 수 "
    "없으며, 재측정 결과는 기존 버전을 덮어쓰지 않고 새 버전으로 추가됩니다. 모든 수치에는 "
    "방법론 버전·체크섬·측정 시점·측정 범위·신뢰도가 함께 고정되고, 측정하지 못한 항목은 "
    "'측정 불가', 적용되지 않는 항목은 '해당 없음'으로 사유와 함께 남습니다. 어느 쪽도 "
    "0으로 바뀌지 않습니다."
)


@router.post(
    "",
    response_model=ApiResponse[CreatedVersionPayload],
    status_code=status.HTTP_201_CREATED,
    summary="리포트 생성 및 1차 버전 발행",
    description=_CREATE_DESCRIPTION,
    dependencies=[
        Depends(require(Permission.REPORT_READ)),
        Depends(require(Permission.SCAN_RUN)),
    ],
)
def create_report(
    body: CreateReportRequest,
    service: ServiceDep,
    principal: CurrentPrincipal,
    request_id: RequestId,
) -> ApiResponse[CreatedVersionPayload]:
    try:
        created = service.create_report(
            principal=principal,
            project_id=body.project_id,
            diagnosis=body.to_diagnosis(),
        )
    except ReportNotFoundError:
        raise _not_found() from None
    except ReportVersionConflictError as exc:
        raise _conflict(str(exc)) from None

    return ok(created_payload(created), request_id, sources=[])


@router.post(
    "/{report_id}/versions",
    response_model=ApiResponse[CreatedVersionPayload],
    status_code=status.HTTP_201_CREATED,
    summary="새 리포트 버전 발행",
    description=_CREATE_DESCRIPTION,
    dependencies=[
        Depends(require(Permission.REPORT_READ)),
        Depends(require(Permission.SCAN_RUN)),
    ],
)
def create_version(
    report_id: ReportIdPath,
    body: CreateVersionRequest,
    service: ServiceDep,
    principal: CurrentPrincipal,
    request_id: RequestId,
) -> ApiResponse[CreatedVersionPayload]:
    try:
        created = service.create_version(
            principal=principal, report_id=report_id, diagnosis=body.to_diagnosis()
        )
    except ReportNotFoundError:
        raise _not_found() from None
    except ReportVersionConflictError as exc:
        raise _conflict(str(exc)) from None

    return ok(created_payload(created), request_id)


@router.get(
    "/{report_id}/versions",
    response_model=PagedResponse[VersionSummaryPayload],
    summary="리포트 버전 목록",
    description=(
        "최신 버전이 먼저 나옵니다. 각 버전에는 발행 시각과 내용 해시가 붙어 있어, 전달한 "
        "문서가 어느 버전이었는지 나중에도 확인할 수 있습니다."
    ),
    dependencies=[Depends(require(Permission.REPORT_READ))],
)
def list_versions(
    report_id: ReportIdPath,
    service: ServiceDep,
    principal: CurrentPrincipal,
    request_id: RequestId,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> PagedResponse[VersionSummaryPayload]:
    try:
        rows = service.list_versions(principal=principal, report_id=report_id)
    except ReportNotFoundError:
        raise _not_found() from None

    start = (page - 1) * page_size
    window = rows[start : start + page_size]
    return PagedResponse[VersionSummaryPayload](
        data=[summary_payload(row) for row in window],
        error=None,
        page_info=PageInfo.build(page=page, page_size=page_size, total_items=len(rows)),
        meta=build_meta(request_id),
    )


@router.get(
    "/{report_id}/versions/{version_number}",
    response_model=ApiResponse[ReportVersionPayload],
    summary="리포트 버전 열람 (경영진·마케팅·개발자 3종)",
    description=(
        "저장된 스냅샷을 그대로 돌려줍니다. 다시 계산하지 않으므로 같은 버전은 언제 읽어도 "
        "같은 숫자입니다. 세 관점은 하나의 스냅샷을 각각 다르게 배열한 것일 뿐이며, 같은 "
        "지표는 세 관점에서 완전히 같은 표기로 나옵니다. `evidence:read` 권한이 없으면 "
        "원문 발췌만 빠지고 점수·측정 범위·신뢰도는 모두 그대로 제공됩니다."
    ),
    dependencies=[Depends(require(Permission.REPORT_READ))],
)
def read_version(
    report_id: ReportIdPath,
    version_number: VersionPath,
    service: ServiceDep,
    principal: CurrentPrincipal,
    request_id: RequestId,
) -> ApiResponse[ReportVersionPayload]:
    try:
        loaded = service.read_version(
            principal=principal, report_id=report_id, version_number=version_number
        )
    except ReportNotFoundError:
        raise _not_found() from None

    snapshot = loaded.snapshot
    first_spec = next(
        (entry for entry in snapshot.provenance.values() if entry.has_spec), None
    )
    return ok(
        read_payload(loaded),
        request_id,
        spec_id=first_spec.spec_id if first_spec else None,
        spec_version=first_spec.spec_version if first_spec else None,
        spec_checksum=first_spec.spec_checksum if first_spec else None,
    )


@router.get(
    "/{report_id}/versions/{version_number}/export",
    summary="리포트 버전 내보내기 (HTML / CSV / XLSX)",
    description=(
        "세 형식 모두 같은 스냅샷을 옮겨 담은 것이며, 같은 지표는 세 형식에서 완전히 같은 "
        "표기로 나옵니다. HTML은 외부 자원을 전혀 참조하지 않는 단일 파일이라 오프라인에서도 "
        "그대로 열립니다. 표 형식에서는 측정하지 못한 칸을 0이 아니라 빈 칸으로 두고, 바로 "
        "옆 열에 '측정 불가' 또는 '해당 없음'과 그 사유를 함께 적습니다."
    ),
    dependencies=[
        Depends(require(Permission.REPORT_READ)),
        Depends(require(Permission.REPORT_EXPORT)),
    ],
    responses={
        200: {
            "content": {
                HTML_CONTENT_TYPE: {},
                CSV_CONTENT_TYPE: {},
                XLSX_CONTENT_TYPE: {},
            }
        }
    },
)
def export_version(
    report_id: ReportIdPath,
    version_number: VersionPath,
    service: ServiceDep,
    principal: CurrentPrincipal,
    format: ExportFormat = "html",
) -> Response:
    try:
        result = service.export(
            principal=principal,
            report_id=report_id,
            version_number=version_number,
            export_format=format,
        )
    except ReportNotFoundError:
        raise _not_found() from None

    return Response(
        content=result.body,
        media_type=result.media_type,
        headers={"content-disposition": f'attachment; filename="{result.filename}"'},
    )
