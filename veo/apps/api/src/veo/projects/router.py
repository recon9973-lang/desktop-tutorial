"""``/projects`` — the unit a scan, a keyword set and a report all hang off.

Note what ``DELETE`` does here: it refuses. A project has no ``is_active`` column and
every measurement table cascades off it, so removing the row would take immutable run
history with it. The endpoint exists so that the refusal is explicit and documented
rather than a 405 the client has to guess the meaning of — and it still answers 404 for
another organization's project, because a 409 would confirm the row is real.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal
from veo.contracts.envelope import ApiResponse, PagedResponse
from veo.db.session import get_db
from veo.organizations.errors import (
    DuplicateResourceError,
    ReferenceNotFoundError,
    UndeletableResourceError,
)
from veo.organizations.http import PageParams, conflict, guard, not_found, paged
from veo.projects import service
from veo.projects.schemas import ProjectCreateRequest, ProjectPayload, ProjectUpdateRequest

router = APIRouter(prefix="/projects", tags=["projects"])

DbSession = Annotated[Session, Depends(get_db)]
Reader = Annotated[Principal, Depends(guard(Permission.PROJECT_READ))]
Writer = Annotated[Principal, Depends(guard(Permission.PROJECT_WRITE))]

NOT_FOUND_KO = "프로젝트를 찾을 수 없습니다."


@router.get(
    "",
    response_model=PagedResponse[ProjectPayload],
    summary="프로젝트 목록",
    description="인증된 세션이 속한 조직의 프로젝트만 반환합니다.",
)
def list_projects(
    session: DbSession,
    principal: Reader,
    request_id: RequestId,
    pagination: PageParams,
    customer_id: Annotated[
        uuid.UUID | None, Query(description="특정 고객사의 프로젝트만 조회합니다.")
    ] = None,
) -> PagedResponse[ProjectPayload]:
    projects, total = service.list_projects(
        session,
        principal,
        page=pagination.page,
        page_size=pagination.page_size,
        customer_id=customer_id,
    )
    return paged(
        [ProjectPayload.of(project) for project in projects],
        request_id,
        pagination=pagination,
        total_items=total,
    )


@router.post(
    "",
    response_model=ApiResponse[ProjectPayload],
    status_code=status.HTTP_201_CREATED,
    summary="프로젝트 생성",
    description=(
        "`slug`는 조직 안에서 고유해야 하며 중복이면 409를 반환합니다. `customer_id`는 "
        "같은 조직의 고객사여야 하고, 그렇지 않으면 404를 반환합니다."
    ),
)
def create_project(
    payload: ProjectCreateRequest,
    session: DbSession,
    principal: Writer,
    request_id: RequestId,
) -> ApiResponse[ProjectPayload]:
    try:
        project = service.create_project(
            session,
            principal,
            slug=payload.slug,
            name=payload.name,
            customer_id=payload.customer_id,
            locale=payload.locale,
            default_seo_spec_version=payload.default_seo_spec_version,
            default_geo_spec_version=payload.default_geo_spec_version,
            settings=payload.settings,
            request_id=request_id,
        )
    except ReferenceNotFoundError as exc:
        raise not_found(exc.message_ko) from exc
    except DuplicateResourceError as exc:
        raise conflict(exc.message_ko) from exc
    return ok(ProjectPayload.of(project), request_id)


@router.get(
    "/{project_id}",
    response_model=ApiResponse[ProjectPayload],
    summary="프로젝트 조회",
    description="다른 조직의 프로젝트 ID는 존재 여부와 무관하게 404를 반환합니다.",
)
def get_project(
    project_id: uuid.UUID,
    session: DbSession,
    principal: Reader,
    request_id: RequestId,
) -> ApiResponse[ProjectPayload]:
    project = service.get_project(session, principal, project_id)
    if project is None:
        raise not_found(NOT_FOUND_KO)
    return ok(ProjectPayload.of(project), request_id)


@router.patch(
    "/{project_id}",
    response_model=ApiResponse[ProjectPayload],
    summary="프로젝트 수정",
    description="요청 본문에 담긴 항목만 변경됩니다. 빈 본문은 422로 거절합니다.",
)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    session: DbSession,
    principal: Writer,
    request_id: RequestId,
) -> ApiResponse[ProjectPayload]:
    try:
        project = service.update_project(
            session, principal, project_id, payload.changes(), request_id=request_id
        )
    except ReferenceNotFoundError as exc:
        raise not_found(exc.message_ko) from exc
    except DuplicateResourceError as exc:
        raise conflict(exc.message_ko) from exc
    if project is None:
        raise not_found(NOT_FOUND_KO)
    return ok(ProjectPayload.of(project), request_id)


@router.delete(
    "/{project_id}",
    response_model=ApiResponse[ProjectPayload],
    summary="프로젝트 삭제 (지원하지 않음)",
    description=(
        "프로젝트는 삭제할 수 없으며 409를 반환합니다. `is_active` 같은 보관용 컬럼이 없고 "
        "진단·근거·점수·리포트가 모두 이 행에 연결되어 있어, 삭제는 곧 되돌릴 수 없는 "
        "측정 이력의 삭제가 됩니다. 다른 조직의 프로젝트라면 409가 아니라 404를 반환합니다."
    ),
)
def delete_project(
    project_id: uuid.UUID,
    session: DbSession,
    principal: Writer,
    request_id: RequestId,
) -> ApiResponse[ProjectPayload]:
    try:
        service.delete_project(session, principal, project_id)
    except ReferenceNotFoundError as exc:
        raise not_found(NOT_FOUND_KO) from exc
    except UndeletableResourceError as exc:
        raise conflict(exc.message_ko) from exc
    raise conflict(service.UNDELETABLE_KO)
