"""Customer data access.

Every statement starts at :func:`veo.authz.tenant_select` and is handed to
:func:`veo.authz.assert_tenant_scoped` immediately before execution. The second call is
redundant while the first one is written correctly — which is the point. It costs a walk
over the WHERE clause and it turns "somebody edited this query and dropped the filter"
from a silent cross-tenant read into a loud exception.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.db.models.identity import Customer
from veo.organizations import audit
from veo.organizations.http import changed_fields

TARGET_TYPE = "customer"

#: Fields a PATCH may set. Anything else in a change map is a programming error, not
#: caller input — the request schema has already rejected unknown keys.
#: 부분 수정으로 바꿀 수 있는 칸. `is_registered` 가 여기 있어야 "거래처로 등록"
#: 이 같은 창구를 쓴다 — 등록만을 위한 두 번째 길을 내면 감사 기록이 두 갈래가 된다.
UPDATABLE = frozenset({"name", "industry", "contact_note", "is_registered"})


def list_customers(
    session: Session,
    principal: Principal,
    *,
    page: int,
    page_size: int,
    include_inactive: bool = False,
    name_query: str | None = None,
    registered: bool | None = None,
) -> tuple[list[Customer], int]:
    """One page of customers, plus the total the page was taken from.

    ``registered`` 는 세 값을 갖는다: True 면 거래처만, False 면 재 보기만 한 자리만,
    ``None`` 이면 둘 다. 기본을 True 로 두지 않는 이유는, 이 함수를 부르는 곳이 여럿이고
    그중 하나라도 "전부"를 뜻했다면 조용히 절반만 받게 되기 때문이다 — 무엇을 원하는지는
    부르는 쪽이 말한다.
    """
    statement = tenant_select(Customer, principal)
    if not include_inactive:
        statement = statement.where(Customer.is_active.is_(True))
    if registered is not None:
        statement = statement.where(Customer.is_registered.is_(registered))
    if name_query:
        statement = statement.where(
            Customer.name.ilike(f"%{_escape_like(name_query)}%", escape="\\")
        )
    assert_tenant_scoped(statement, principal.organization_id)

    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0

    page_statement = (
        statement.order_by(Customer.created_at, Customer.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    assert_tenant_scoped(page_statement, principal.organization_id)
    return list(session.scalars(page_statement)), total


def get_customer(
    session: Session, principal: Principal, customer_id: uuid.UUID
) -> Customer | None:
    """The customer, or ``None`` — including when it belongs to another organization."""
    statement = tenant_select(Customer, principal).where(Customer.id == customer_id)
    assert_tenant_scoped(statement, principal.organization_id)
    return session.scalars(statement).one_or_none()


def create_customer(
    session: Session,
    principal: Principal,
    *,
    name: str,
    industry: str | None = None,
    contact_note: str | None = None,
    is_registered: bool = True,
    request_id: str | None = None,
) -> Customer:
    values = {"name": name, "industry": industry, "contact_note": contact_note}
    customer = Customer(
        organization_id=principal.organization_id,
        is_active=True,
        # 기본은 거래처다. 주소만 넣고 재 보려고 자리를 만드는 쪽이 예외이고, 그쪽이
        # 명시적으로 False 를 보낸다 — 기본을 False 로 두면 손으로 등록한 업체가
        # 어딘가에서 값을 빠뜨렸을 때 목록에서 사라진다.
        is_registered=is_registered,
        **values,
    )
    session.add(customer)
    session.flush()

    audit.record(
        session,
        principal,
        action=f"{TARGET_TYPE}.create",
        target_type=TARGET_TYPE,
        target_id=customer.id,
        request_id=request_id,
        # Field names only. A customer's name, industry and contact note are the
        # customer's data, not VEO's operational record.
        detail={"fields": sorted(key for key, value in values.items() if value is not None)},
    )
    session.flush()
    return customer


def update_customer(
    session: Session,
    principal: Principal,
    customer_id: uuid.UUID,
    changes: dict[str, Any],
    *,
    request_id: str | None = None,
) -> Customer | None:
    customer = get_customer(session, principal, customer_id)
    if customer is None:
        return None

    applied = {name: value for name, value in changes.items() if name in UPDATABLE}
    moved = changed_fields(customer, applied)
    for name, value in applied.items():
        setattr(customer, name, value)
    session.flush()

    audit.record(
        session,
        principal,
        action=f"{TARGET_TYPE}.update",
        target_type=TARGET_TYPE,
        target_id=customer.id,
        request_id=request_id,
        detail={"changed_fields": moved},
    )
    session.flush()
    return customer


def deactivate_customer(
    session: Session,
    principal: Principal,
    customer_id: uuid.UUID,
    *,
    request_id: str | None = None,
) -> Customer | None:
    """Soft delete. The row keeps its id so existing scans and reports still resolve it.

    Idempotent: deleting an already-inactive customer succeeds and writes another audit
    row, because "somebody tried to delete this again" is worth knowing.
    """
    customer = get_customer(session, principal, customer_id)
    if customer is None:
        return None

    was_active = customer.is_active
    customer.is_active = False
    session.flush()

    audit.record(
        session,
        principal,
        action=f"{TARGET_TYPE}.delete",
        target_type=TARGET_TYPE,
        target_id=customer.id,
        request_id=request_id,
        detail={"soft": True, "was_active": was_active},
    )
    session.flush()
    return customer


def _escape_like(value: str) -> str:
    """Neutralise LIKE wildcards so a search term stays a search term."""
    return value.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
