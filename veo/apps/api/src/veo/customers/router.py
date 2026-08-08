"""``/customers`` — the agency's client list, inside one organization.

A customer belonging to another organization answers 404 on every verb, including the
ones the caller holds the write permission for. 403 would confirm the row exists, and
"this id is real, you just cannot touch it" is enough to enumerate a competitor's client
list one guess at a time.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal
from veo.contracts.envelope import ApiResponse, PagedResponse
from veo.customers import service
from veo.customers.schemas import CustomerCreateRequest, CustomerPayload, CustomerUpdateRequest
from veo.db.session import get_db
from veo.organizations.http import PageParams, guard, not_found, paged

router = APIRouter(prefix="/customers", tags=["customers"])

DbSession = Annotated[Session, Depends(get_db)]
Reader = Annotated[Principal, Depends(guard(Permission.CUSTOMER_READ))]
Writer = Annotated[Principal, Depends(guard(Permission.CUSTOMER_WRITE))]

NOT_FOUND_KO = "고객사를 찾을 수 없습니다."


@router.get(
    "",
    response_model=PagedResponse[CustomerPayload],
    summary="고객사 목록",
    description=(
        "인증된 세션이 속한 조직의 고객사만 반환합니다. 기본적으로 삭제 처리된 고객사는 "
        "제외되며, `include_inactive=true`로 함께 조회할 수 있습니다."
    ),
)
def list_customers(
    session: DbSession,
    principal: Reader,
    request_id: RequestId,
    pagination: PageParams,
    include_inactive: Annotated[
        bool, Query(description="삭제 처리된 고객사도 함께 조회합니다.")
    ] = False,
    q: Annotated[
        str | None, Query(max_length=200, description="고객사명 부분 일치 검색어입니다.")
    ] = None,
    registered: Annotated[
        bool | None,
        Query(
            description=(
                "true면 거래처로 등록된 곳만, false면 주소만 넣고 재 본 자리만 "
                "반환합니다. 생략하면 둘 다 반환합니다."
            )
        ),
    ] = None,
) -> PagedResponse[CustomerPayload]:
    customers, total = service.list_customers(
        session,
        principal,
        page=pagination.page,
        page_size=pagination.page_size,
        include_inactive=include_inactive,
        name_query=q,
        registered=registered,
    )
    return paged(
        [CustomerPayload.of(customer) for customer in customers],
        request_id,
        pagination=pagination,
        total_items=total,
    )


@router.post(
    "",
    response_model=ApiResponse[CustomerPayload],
    status_code=status.HTTP_201_CREATED,
    summary="고객사 등록",
    description="조직은 인증 정보에서 결정되며 요청 본문으로는 지정할 수 없습니다.",
)
def create_customer(
    payload: CustomerCreateRequest,
    session: DbSession,
    principal: Writer,
    request_id: RequestId,
) -> ApiResponse[CustomerPayload]:
    customer = service.create_customer(
        session,
        principal,
        name=payload.name,
        industry=payload.industry,
        address=payload.address,
        contact_note=payload.contact_note,
        is_registered=payload.is_registered,
        request_id=request_id,
    )
    return ok(CustomerPayload.of(customer), request_id)


@router.get(
    "/{customer_id}",
    response_model=ApiResponse[CustomerPayload],
    summary="고객사 조회",
    description="다른 조직의 고객사 ID는 존재 여부와 무관하게 404를 반환합니다.",
)
def get_customer(
    customer_id: uuid.UUID,
    session: DbSession,
    principal: Reader,
    request_id: RequestId,
) -> ApiResponse[CustomerPayload]:
    customer = service.get_customer(session, principal, customer_id)
    if customer is None:
        raise not_found(NOT_FOUND_KO)
    return ok(CustomerPayload.of(customer), request_id)


@router.patch(
    "/{customer_id}",
    response_model=ApiResponse[CustomerPayload],
    summary="고객사 수정",
    description="요청 본문에 담긴 항목만 변경됩니다. 빈 본문은 422로 거절합니다.",
)
def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdateRequest,
    session: DbSession,
    principal: Writer,
    request_id: RequestId,
) -> ApiResponse[CustomerPayload]:
    customer = service.update_customer(
        session, principal, customer_id, payload.changes(), request_id=request_id
    )
    if customer is None:
        raise not_found(NOT_FOUND_KO)
    return ok(CustomerPayload.of(customer), request_id)


@router.delete(
    "/{customer_id}",
    response_model=ApiResponse[CustomerPayload],
    summary="고객사 삭제 (soft delete)",
    description=(
        "행을 지우지 않고 `is_active`를 false로 바꿉니다. 과거 진단·리포트가 이 고객사를 "
        "참조하고 있으므로 실제 삭제는 이력을 함께 지우는 일이 됩니다."
    ),
)
def delete_customer(
    customer_id: uuid.UUID,
    session: DbSession,
    principal: Writer,
    request_id: RequestId,
) -> ApiResponse[CustomerPayload]:
    customer = service.deactivate_customer(session, principal, customer_id, request_id=request_id)
    if customer is None:
        raise not_found(NOT_FOUND_KO)
    return ok(CustomerPayload.of(customer), request_id)
