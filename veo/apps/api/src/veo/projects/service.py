"""Project data access.

Two rules shape this module.

*Tenant scope is structural.* Every statement is built by
:func:`veo.authz.tenant_select` and checked by :func:`veo.authz.assert_tenant_scoped`
before it runs.

*A foreign key is resolved, not trusted.* ``customer_id`` arrives from the request, so it
is looked up through the caller's own scope before it is stored. A customer id belonging
to another organization therefore raises
:class:`~veo.organizations.errors.ReferenceNotFoundError` — the same failure an id that
exists nowhere produces — instead of reaching PostgreSQL and coming back as a foreign-key
violation that says the row is real.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.db.models.identity import Customer, Project
from veo.organizations import audit
from veo.organizations.errors import (
    DuplicateResourceError,
    ReferenceNotFoundError,
    UndeletableResourceError,
)
from veo.organizations.http import changed_fields

TARGET_TYPE = "project"

UPDATABLE = frozenset(
    {
        "slug",
        "name",
        "customer_id",
        "locale",
        "default_seo_spec_version",
        "default_geo_spec_version",
        "settings",
    }
)

DUPLICATE_SLUG_KO = "이미 같은 slug를 쓰는 프로젝트가 있습니다."
CUSTOMER_NOT_FOUND_KO = "고객사를 찾을 수 없습니다."
UNDELETABLE_KO = (
    "프로젝트는 삭제할 수 없습니다. 진단 이력·리포트가 이 프로젝트를 참조하고 있어 "
    "삭제하면 되돌릴 수 없는 측정 기록까지 함께 사라집니다."
)


def list_projects(
    session: Session,
    principal: Principal,
    *,
    page: int,
    page_size: int,
    customer_id: uuid.UUID | None = None,
) -> tuple[list[Project], int]:
    statement = tenant_select(Project, principal)
    if customer_id is not None:
        statement = statement.where(Project.customer_id == customer_id)
    assert_tenant_scoped(statement, principal.organization_id)

    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0

    page_statement = (
        statement.order_by(Project.created_at, Project.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    assert_tenant_scoped(page_statement, principal.organization_id)
    return list(session.scalars(page_statement)), total


def get_project(session: Session, principal: Principal, project_id: uuid.UUID) -> Project | None:
    statement = tenant_select(Project, principal).where(Project.id == project_id)
    assert_tenant_scoped(statement, principal.organization_id)
    return session.scalars(statement).one_or_none()


def require_project(session: Session, principal: Principal, project_id: uuid.UUID) -> Project:
    """Resolve a project id supplied by a caller, or refuse it as not found.

    Used by the sites package as well: a site may only ever be attached to a project the
    caller can already see.
    """
    project = get_project(session, principal, project_id)
    if project is None:
        raise ReferenceNotFoundError("프로젝트를 찾을 수 없습니다.")
    return project


def create_project(
    session: Session,
    principal: Principal,
    *,
    slug: str,
    name: str,
    customer_id: uuid.UUID | None = None,
    locale: str = "ko-KR",
    default_seo_spec_version: str | None = None,
    default_geo_spec_version: str | None = None,
    settings: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> Project:
    if customer_id is not None:
        _require_customer(session, principal, customer_id)
    _reject_taken_slug(session, principal, slug)

    project = Project(
        organization_id=principal.organization_id,
        customer_id=customer_id,
        slug=slug,
        name=name,
        locale=locale,
        default_seo_spec_version=default_seo_spec_version,
        default_geo_spec_version=default_geo_spec_version,
        settings=dict(settings or {}),
    )
    _add_or_conflict(session, project, DUPLICATE_SLUG_KO)

    audit.record(
        session,
        principal,
        action=f"{TARGET_TYPE}.create",
        target_type=TARGET_TYPE,
        target_id=project.id,
        request_id=request_id,
        # A slug is an operational identifier the agency chose, not customer data.
        detail={"slug": project.slug, "has_customer": customer_id is not None},
    )
    session.flush()
    return project


def update_project(
    session: Session,
    principal: Principal,
    project_id: uuid.UUID,
    changes: dict[str, Any],
    *,
    request_id: str | None = None,
) -> Project | None:
    project = get_project(session, principal, project_id)
    if project is None:
        return None

    applied = {name: value for name, value in changes.items() if name in UPDATABLE}

    new_customer_id = applied.get("customer_id")
    if "customer_id" in applied and new_customer_id is not None:
        _require_customer(session, principal, new_customer_id)

    new_slug = applied.get("slug")
    if new_slug is not None and new_slug != project.slug:
        _reject_taken_slug(session, principal, new_slug)

    moved = changed_fields(project, applied)
    for name, value in applied.items():
        setattr(project, name, value)
    _flush_or_conflict(session, DUPLICATE_SLUG_KO)

    audit.record(
        session,
        principal,
        action=f"{TARGET_TYPE}.update",
        target_type=TARGET_TYPE,
        target_id=project.id,
        request_id=request_id,
        detail={"changed_fields": moved},
    )
    session.flush()
    return project


def delete_project(session: Session, principal: Principal, project_id: uuid.UUID) -> None:
    """Always refuses — but only after confirming the caller could see the row at all.

    ``Project`` has no ``is_active`` column, and scans, evidence, score results, issues
    and reports all cascade off it. There is no honest delete to perform, so the answer
    is a conflict. Resolving the row first matters: for someone else's project the answer
    must stay 404, because a 409 would confirm it exists.
    """
    require_project(session, principal, project_id)
    raise UndeletableResourceError(UNDELETABLE_KO)


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _require_customer(
    session: Session, principal: Principal, customer_id: uuid.UUID
) -> Customer:
    statement = tenant_select(Customer, principal).where(Customer.id == customer_id)
    assert_tenant_scoped(statement, principal.organization_id)
    customer = session.scalars(statement).one_or_none()
    if customer is None:
        raise ReferenceNotFoundError(CUSTOMER_NOT_FOUND_KO)
    return customer


def _reject_taken_slug(session: Session, principal: Principal, slug: str) -> None:
    statement = tenant_select(Project, principal).where(Project.slug == slug)
    assert_tenant_scoped(statement, principal.organization_id)
    if session.scalars(statement).first() is not None:
        raise DuplicateResourceError(DUPLICATE_SLUG_KO)


def _add_or_conflict(session: Session, project: Project, message_ko: str) -> None:
    """Insert inside a savepoint so a lost uniqueness race is a 409, not a 500.

    The pre-check above closes the common case; this closes the window between it and
    the INSERT, where a concurrent request can take the same slug.
    """
    try:
        with session.begin_nested():
            session.add(project)
            session.flush()
    except IntegrityError as exc:
        raise DuplicateResourceError(message_ko) from exc


def _flush_or_conflict(session: Session, message_ko: str) -> None:
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as exc:
        raise DuplicateResourceError(message_ko) from exc
