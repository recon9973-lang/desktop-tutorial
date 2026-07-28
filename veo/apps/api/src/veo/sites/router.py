"""``/sites`` — the origins a project's scans are allowed to touch.

``DELETE`` refuses for the same reason it does on projects: ``Site`` carries no
``is_active``, and URL records and scans cascade off it. Another organization's site
answers 404 rather than 409 on every verb.
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
from veo.sites import service
from veo.sites.schemas import SiteCreateRequest, SitePayload, SiteUpdateRequest

router = APIRouter(prefix="/sites", tags=["sites"])

DbSession = Annotated[Session, Depends(get_db)]
Reader = Annotated[Principal, Depends(guard(Permission.SITE_READ))]
Writer = Annotated[Principal, Depends(guard(Permission.SITE_WRITE))]

NOT_FOUND_KO = "사이트를 찾을 수 없습니다."


@router.get(
    "",
    response_model=PagedResponse[SitePayload],
    summary="사이트 목록",
    description=(
        "인증된 세션이 속한 조직의 사이트만 반환합니다. `project_id`로 거를 수 있으며, "
        "다른 조직의 프로젝트 ID를 넣으면 빈 목록이 아니라 404를 반환합니다."
    ),
)
def list_sites(
    session: DbSession,
    principal: Reader,
    request_id: RequestId,
    pagination: PageParams,
    project_id: Annotated[
        uuid.UUID | None, Query(description="특정 프로젝트의 사이트만 조회합니다.")
    ] = None,
) -> PagedResponse[SitePayload]:
    try:
        sites, total = service.list_sites(
            session,
            principal,
            page=pagination.page,
            page_size=pagination.page_size,
            project_id=project_id,
        )
    except ReferenceNotFoundError as exc:
        raise not_found(exc.message_ko) from exc
    return paged(
        [SitePayload.of(site) for site in sites],
        request_id,
        pagination=pagination,
        total_items=total,
    )


@router.post(
    "",
    response_model=ApiResponse[SitePayload],
    status_code=status.HTTP_201_CREATED,
    summary="사이트 등록",
    description=(
        "`origin`은 스킴과 호스트만 담긴 형태로 정규화되어 저장됩니다. 같은 프로젝트에 "
        "동일한 origin이 이미 있으면 409를 반환합니다. `is_primary=true`로 등록하면 "
        "같은 프로젝트의 기존 대표 사이트는 자동으로 해제됩니다."
    ),
)
def create_site(
    payload: SiteCreateRequest,
    session: DbSession,
    principal: Writer,
    request_id: RequestId,
) -> ApiResponse[SitePayload]:
    try:
        site = service.create_site(
            session,
            principal,
            project_id=payload.project_id,
            origin=payload.origin,
            display_name=payload.display_name,
            is_primary=payload.is_primary,
            crawl_settings=payload.crawl_settings,
            request_id=request_id,
        )
    except ReferenceNotFoundError as exc:
        raise not_found(exc.message_ko) from exc
    except DuplicateResourceError as exc:
        raise conflict(exc.message_ko) from exc
    return ok(SitePayload.of(site), request_id)


@router.get(
    "/{site_id}",
    response_model=ApiResponse[SitePayload],
    summary="사이트 조회",
    description="다른 조직의 사이트 ID는 존재 여부와 무관하게 404를 반환합니다.",
)
def get_site(
    site_id: uuid.UUID,
    session: DbSession,
    principal: Reader,
    request_id: RequestId,
) -> ApiResponse[SitePayload]:
    site = service.get_site(session, principal, site_id)
    if site is None:
        raise not_found(NOT_FOUND_KO)
    return ok(SitePayload.of(site), request_id)


@router.patch(
    "/{site_id}",
    response_model=ApiResponse[SitePayload],
    summary="사이트 수정",
    description=(
        "요청 본문에 담긴 항목만 변경됩니다. `project_id`는 바꿀 수 없습니다 — 사이트를 "
        "옮기면 이미 쌓인 진단 이력이 엉뚱한 프로젝트에 매달립니다."
    ),
)
def update_site(
    site_id: uuid.UUID,
    payload: SiteUpdateRequest,
    session: DbSession,
    principal: Writer,
    request_id: RequestId,
) -> ApiResponse[SitePayload]:
    try:
        site = service.update_site(
            session, principal, site_id, payload.changes(), request_id=request_id
        )
    except DuplicateResourceError as exc:
        raise conflict(exc.message_ko) from exc
    if site is None:
        raise not_found(NOT_FOUND_KO)
    return ok(SitePayload.of(site), request_id)


@router.delete(
    "/{site_id}",
    response_model=ApiResponse[SitePayload],
    summary="사이트 삭제 (지원하지 않음)",
    description=(
        "사이트는 삭제할 수 없으며 409를 반환합니다. 보관용 컬럼이 없고 수집한 URL과 "
        "진단 이력이 이 행에 연결되어 있습니다. 다른 조직의 사이트라면 404를 반환합니다."
    ),
)
def delete_site(
    site_id: uuid.UUID,
    session: DbSession,
    principal: Writer,
    request_id: RequestId,
) -> ApiResponse[SitePayload]:
    try:
        service.delete_site(session, principal, site_id)
    except UndeletableResourceError as exc:
        raise conflict(exc.message_ko) from exc
    raise not_found(NOT_FOUND_KO)
