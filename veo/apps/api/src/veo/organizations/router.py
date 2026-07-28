"""``/organizations`` — read-only, and only your own.

There is deliberately no list route and no write route in Phase 1. Creating an
organization is an onboarding action that happens outside the tenant-scoped API, and a
list would hand every signed-in caller the customer roster of a competitor who happens to
share the platform.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal
from veo.contracts.envelope import ApiResponse
from veo.db.session import get_db
from veo.organizations import service
from veo.organizations.http import guard, not_found
from veo.organizations.schemas import OrganizationPayload

router = APIRouter(prefix="/organizations", tags=["organizations"])

DbSession = Annotated[Session, Depends(get_db)]
Reader = Annotated[Principal, Depends(guard(Permission.ORG_READ))]

NOT_FOUND_KO = "조직을 찾을 수 없습니다."


@router.get(
    "/current",
    response_model=ApiResponse[OrganizationPayload],
    summary="내가 속한 조직 조회",
    description=(
        "인증된 세션이 속한 조직 하나를 반환합니다. 경로에 조직 ID를 넣지 않으므로 "
        "다른 조직을 조회할 여지가 없습니다."
    ),
)
def get_current_organization(
    session: DbSession, principal: Reader, request_id: RequestId
) -> ApiResponse[OrganizationPayload]:
    organization = service.get_own_organization(session, principal)
    if organization is None:
        raise not_found(NOT_FOUND_KO)
    return ok(OrganizationPayload.of(organization), request_id)


@router.get(
    "/{organization_id}",
    response_model=ApiResponse[OrganizationPayload],
    summary="조직 조회",
    description=(
        "자신이 속한 조직만 조회할 수 있습니다. 다른 조직의 ID를 넣으면 존재 여부와 "
        "무관하게 404를 반환합니다. 403을 돌려주면 그 조직이 실재한다는 사실이 노출됩니다."
    ),
)
def get_organization(
    organization_id: uuid.UUID,
    session: DbSession,
    principal: Reader,
    request_id: RequestId,
) -> ApiResponse[OrganizationPayload]:
    organization = service.get_organization(session, principal, organization_id)
    if organization is None:
        raise not_found(NOT_FOUND_KO)
    return ok(OrganizationPayload.of(organization), request_id)
