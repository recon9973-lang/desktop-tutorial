"""``/lab/scoring-versions`` — the workflow VEO-LAB uses to govern measurement.

This router is **not** mounted by :mod:`veo.api.app`; the integrator owns that file. See
``INTEGRATION_REQUEST.md``.

Status codes follow the same convention as the rest of VEO. A refusal that the caller
could resolve by doing something different is a 409 (wrong state, already published,
golden fixtures not run); a document VEO cannot accept at all is a 422; a stored row whose
checksum does not match is a 409 as well, because the resolution — create a new version —
is a real action the caller can take, and pretending it is a server fault would hide a
finding that a person needs to look at.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal
from veo.contracts.enums import ErrorCode
from veo.contracts.envelope import ApiResponse, PagedResponse
from veo.db.session import get_db
from veo.lab import service
from veo.lab.errors import (
    ChecksumMismatchError,
    DuplicateVersionError,
    GoldenFixtureError,
    IllegalTransitionError,
    ImmutableVersionError,
    SpecificationRejectedError,
    VersionNotFoundError,
)
from veo.lab.schemas import (
    CreateDraftRequest,
    DiffPayload,
    GoldenPayload,
    RescoreRequest,
    RescoreSummaryPayload,
    ScoringVersionDetail,
    ScoringVersionSummary,
    UpdateDraftRequest,
    ValidationPayload,
)
from veo.lab.versions import parse_status
from veo.organizations.http import PageParams, api_error, conflict, guard, not_found, paged

router = APIRouter(prefix="/lab/scoring-versions", tags=["lab"])

DbSession = Annotated[Session, Depends(get_db)]
Reader = Annotated[Principal, Depends(guard(Permission.SCORING_SPEC_READ))]
Author = Annotated[Principal, Depends(guard(Permission.SCORING_SPEC_AUTHOR))]
Publisher = Annotated[Principal, Depends(guard(Permission.SCORING_SPEC_PUBLISH))]

NOT_FOUND_KO = "점수 명세 버전을 찾을 수 없습니다."

_LOG = logging.getLogger("veo.lab")


#: 422, spelled as a number because the Starlette constant for it is mid-rename and the
#: deprecated alias emits a warning on every rejected specification.
UNPROCESSABLE = 422


def _invalid(message_ko: str) -> HTTPException:
    return api_error(UNPROCESSABLE, ErrorCode.SCORING_SPEC_INVALID, message_ko)


@router.get(
    "",
    response_model=PagedResponse[ScoringVersionSummary],
    summary="점수 명세 버전 목록",
    description="최근에 만들어진 버전이 먼저 옵니다. `spec_id`와 `status`로 거를 수 있습니다.",
)
def list_versions(
    session: DbSession,
    principal: Reader,
    request_id: RequestId,
    pagination: PageParams,
    spec_id: Annotated[str | None, Query(max_length=120)] = None,
    version_status: Annotated[
        str | None,
        Query(
            alias="status",
            description="DRAFT · REVIEW · APPROVED · PUBLISHED · RETIRED",
        ),
    ] = None,
) -> PagedResponse[ScoringVersionSummary]:
    parsed = None
    if version_status is not None:
        try:
            parsed = parse_status(version_status)
        except ValueError as exc:
            raise _invalid(str(exc)) from exc

    rows, total = service.list_versions(
        session,
        principal,
        spec_id=spec_id,
        status=parsed,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paged(
        [ScoringVersionSummary.of(row) for row in rows],
        request_id,
        pagination=pagination,
        total_items=total,
    )


@router.get(
    "/{version_id}",
    response_model=ApiResponse[ScoringVersionDetail],
    summary="점수 명세 버전 상세 — 변경 요약·검증·골든 결과",
    description=(
        "저장된 명세의 체크섬을 먼저 확인한 뒤, 현재 발행본과 비교한 한국어 변경 요약과 "
        "골든 픽스처 결과를 함께 반환합니다. 체크섬이 맞지 않으면 409로 거부합니다."
    ),
)
def get_version(
    version_id: uuid.UUID,
    session: DbSession,
    principal: Reader,
    request_id: RequestId,
) -> ApiResponse[ScoringVersionDetail]:
    detail = _detail(session, principal, version_id)
    return ok(detail, request_id, spec_id=detail.spec_id, spec_version=detail.semantic_version)


@router.post(
    "",
    response_model=ApiResponse[ScoringVersionSummary],
    status_code=status.HTTP_201_CREATED,
    summary="점수 명세 초안 등록",
    description=(
        "명세를 검증한 뒤 DRAFT로 등록하고 체크섬을 한 번 계산합니다. 이후 이 체크섬은 "
        "본문을 수정하지 않는 한 바뀌지 않습니다."
    ),
)
def create_draft(
    payload: CreateDraftRequest,
    session: DbSession,
    principal: Author,
    request_id: RequestId,
) -> ApiResponse[ScoringVersionSummary]:
    try:
        row = service.create_draft(
            session,
            principal,
            specification=payload.specification,
            changelog=payload.changelog,
            compatible_collector_versions=payload.compatible_collector_versions,
            request_id=request_id,
        )
    except SpecificationRejectedError as exc:
        raise _invalid(exc.message_ko) from exc
    except DuplicateVersionError as exc:
        raise conflict(exc.message_ko) from exc
    return ok(ScoringVersionSummary.of(row), request_id)


@router.patch(
    "/{version_id}",
    response_model=ApiResponse[ScoringVersionSummary],
    summary="초안 수정",
    description=(
        "DRAFT 상태에서만 본문을 바꿀 수 있습니다. 본문을 바꾸면 체크섬이 달라지므로 "
        "기록된 골든 픽스처 결과는 무효가 되고 다시 실행해야 합니다."
    ),
)
def update_draft(
    version_id: uuid.UUID,
    payload: UpdateDraftRequest,
    session: DbSession,
    principal: Author,
    request_id: RequestId,
) -> ApiResponse[ScoringVersionSummary]:
    with _translated():
        row = service.update_draft(
            session,
            principal,
            version_id,
            specification=payload.specification,
            changelog=payload.changelog,
            request_id=request_id,
        )
    return ok(ScoringVersionSummary.of(row), request_id)


@router.post(
    "/{version_id}/golden-run",
    response_model=ApiResponse[GoldenPayload],
    summary="골든 픽스처 검증 실행",
    description=(
        "이 명세 계열의 골든 픽스처를 후보 명세로 다시 실행하고 결과를 기록합니다. "
        "방법론을 바꿨다면 픽스처의 기대값도 함께 갱신해야 통과합니다."
    ),
)
def run_golden(
    version_id: uuid.UUID,
    session: DbSession,
    principal: Author,
    request_id: RequestId,
) -> ApiResponse[GoldenPayload]:
    with _translated():
        run = service.run_golden(session, principal, version_id, request_id=request_id)
    return ok(GoldenPayload.of_run(run), request_id)


@router.post(
    "/{version_id}/submit",
    response_model=ApiResponse[ScoringVersionSummary],
    summary="검토 요청 (DRAFT → REVIEW)",
)
def submit_for_review(
    version_id: uuid.UUID,
    session: DbSession,
    principal: Author,
    request_id: RequestId,
) -> ApiResponse[ScoringVersionSummary]:
    with _translated():
        row = service.submit_for_review(session, principal, version_id, request_id=request_id)
    return ok(ScoringVersionSummary.of(row), request_id)


@router.post(
    "/{version_id}/send-back",
    response_model=ApiResponse[ScoringVersionSummary],
    summary="초안으로 되돌리기 (REVIEW·APPROVED → DRAFT)",
    description="본문을 고치려면 먼저 초안으로 되돌려야 합니다. 승인은 체크섬에 대한 승인입니다.",
)
def send_back(
    version_id: uuid.UUID,
    session: DbSession,
    principal: Author,
    request_id: RequestId,
) -> ApiResponse[ScoringVersionSummary]:
    with _translated():
        row = service.send_back(session, principal, version_id, request_id=request_id)
    return ok(ScoringVersionSummary.of(row), request_id)


@router.post(
    "/{version_id}/approve",
    response_model=ApiResponse[ScoringVersionSummary],
    summary="승인 (REVIEW → APPROVED)",
)
def approve(
    version_id: uuid.UUID,
    session: DbSession,
    principal: Publisher,
    request_id: RequestId,
) -> ApiResponse[ScoringVersionSummary]:
    with _translated():
        row = service.approve(session, principal, version_id, request_id=request_id)
    return ok(ScoringVersionSummary.of(row), request_id)


@router.post(
    "/{version_id}/publish",
    response_model=ApiResponse[ScoringVersionSummary],
    summary="발행 (APPROVED → PUBLISHED)",
    description=(
        "골든 픽스처가 이 체크섬에 대해 통과한 기록이 있어야 발행됩니다. 발행되면 이 행은 "
        "더 이상 수정할 수 없고, 같은 계열의 이전 발행본은 자동으로 폐기됩니다."
    ),
)
def publish(
    version_id: uuid.UUID,
    session: DbSession,
    principal: Publisher,
    request_id: RequestId,
) -> ApiResponse[ScoringVersionSummary]:
    with _translated():
        row = service.publish(session, principal, version_id, request_id=request_id)
    return ok(ScoringVersionSummary.of(row), request_id)


@router.post(
    "/{version_id}/retire",
    response_model=ApiResponse[ScoringVersionSummary],
    summary="폐기 (PUBLISHED → RETIRED)",
)
def retire(
    version_id: uuid.UUID,
    session: DbSession,
    principal: Publisher,
    request_id: RequestId,
) -> ApiResponse[ScoringVersionSummary]:
    with _translated():
        row = service.retire(session, principal, version_id, request_id=request_id)
    return ok(ScoringVersionSummary.of(row), request_id)


@router.post(
    "/{version_id}/rescore",
    response_model=ApiResponse[RescoreSummaryPayload],
    summary="과거 결과 재계산",
    description=(
        "발행된 버전으로 이 조직의 기존 점수를 다시 계산합니다. 원본 점수 행은 그대로 "
        "남고, 재계산 결과는 각각 새 행으로 기록되어 두 숫자가 모두 조회됩니다."
    ),
)
def rescore(
    version_id: uuid.UUID,
    payload: RescoreRequest,
    session: DbSession,
    principal: Publisher,
    request_id: RequestId,
) -> ApiResponse[RescoreSummaryPayload]:
    with _translated():
        summary = service.rescore(
            session,
            principal,
            version_id,
            scan_run_ids=payload.scan_run_ids,
            limit=payload.limit,
            request_id=request_id,
        )
    return ok(RescoreSummaryPayload.of(summary), request_id)


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _detail(
    session: Session, principal: Principal, version_id: uuid.UUID
) -> ScoringVersionDetail:
    with _translated():
        detail = service.read_detail(session, principal, version_id)

    summary = ScoringVersionSummary.of(detail.version)
    return ScoringVersionDetail(
        **summary.model_dump(),
        specification=dict(detail.version.specification),
        diff=DiffPayload.of(detail.diff, baseline_source_ko=detail.baseline_source_ko),
        validation=ValidationPayload.of(detail.validation),
        golden=GoldenPayload.of_record(detail.golden) if detail.golden else None,
        allowed_transitions=[item.value for item in detail.allowed_transitions],
    )


@contextmanager
def _translated() -> Iterator[None]:
    """Turn the service's Korean failures into the standard VEO error envelope."""
    try:
        yield
    except VersionNotFoundError as exc:
        raise not_found(NOT_FOUND_KO) from exc
    except ChecksumMismatchError as exc:
        # Worth a log line: this is either a bug or an unauthorised write, and neither
        # should be discovered only from a customer's screenshot.
        _LOG.error("stored scoring specification failed its checksum: %s", exc.message_ko)
        raise conflict(exc.message_ko) from exc
    except (
        DuplicateVersionError,
        GoldenFixtureError,
        IllegalTransitionError,
        ImmutableVersionError,
    ) as exc:
        raise conflict(exc.message_ko) from exc
    except SpecificationRejectedError as exc:
        raise _invalid(exc.message_ko) from exc
