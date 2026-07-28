"""Site data access.

A site is reachable two ways — by its own id, and through its project — and both are
tenant-scoped. ``project_id`` from a request is resolved through
:func:`veo.projects.service.require_project`, so attaching a site to another
organization's project fails as "not found" rather than as a foreign-key violation.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.db.models.identity import Site
from veo.organizations import audit
from veo.organizations.errors import DuplicateResourceError, UndeletableResourceError
from veo.organizations.http import changed_fields
from veo.projects.service import require_project

TARGET_TYPE = "site"

UPDATABLE = frozenset({"origin", "display_name", "is_primary", "crawl_settings"})

DUPLICATE_ORIGIN_KO = "이 프로젝트에는 이미 같은 origin의 사이트가 있습니다."
UNDELETABLE_KO = (
    "사이트는 삭제할 수 없습니다. 수집한 URL·진단 이력이 이 사이트를 참조하고 있어 "
    "삭제하면 되돌릴 수 없는 측정 기록까지 함께 사라집니다."
)


def list_sites(
    session: Session,
    principal: Principal,
    *,
    page: int,
    page_size: int,
    project_id: uuid.UUID | None = None,
) -> tuple[list[Site], int]:
    """One page of sites. A ``project_id`` filter is resolved before it is used.

    Filtering by a project the caller cannot see raises
    :class:`~veo.organizations.errors.ReferenceNotFoundError` rather than returning an
    empty page: an empty page and a forbidden project would otherwise be the same answer,
    and the caller could not tell a real empty project from someone else's.
    """
    statement = tenant_select(Site, principal)
    if project_id is not None:
        require_project(session, principal, project_id)
        statement = statement.where(Site.project_id == project_id)
    assert_tenant_scoped(statement, principal.organization_id)

    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0

    page_statement = (
        statement.order_by(Site.created_at, Site.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    assert_tenant_scoped(page_statement, principal.organization_id)
    return list(session.scalars(page_statement)), total


def get_site(session: Session, principal: Principal, site_id: uuid.UUID) -> Site | None:
    statement = tenant_select(Site, principal).where(Site.id == site_id)
    assert_tenant_scoped(statement, principal.organization_id)
    return session.scalars(statement).one_or_none()


def create_site(
    session: Session,
    principal: Principal,
    *,
    project_id: uuid.UUID,
    origin: str,
    display_name: str,
    is_primary: bool = False,
    crawl_settings: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> Site:
    require_project(session, principal, project_id)
    _reject_taken_origin(session, principal, project_id, origin)

    site = Site(
        organization_id=principal.organization_id,
        project_id=project_id,
        origin=origin,
        display_name=display_name,
        is_primary=is_primary,
        crawl_settings=dict(crawl_settings or {}),
    )
    try:
        with session.begin_nested():
            session.add(site)
            session.flush()
    except IntegrityError as exc:
        raise DuplicateResourceError(DUPLICATE_ORIGIN_KO) from exc

    if is_primary:
        _demote_other_primaries(session, principal, project_id, site.id)

    audit.record(
        session,
        principal,
        action=f"{TARGET_TYPE}.create",
        target_type=TARGET_TYPE,
        target_id=site.id,
        request_id=request_id,
        # An origin is a public address the agency configured, not customer data.
        detail={"origin": site.origin, "project_id": str(project_id)},
    )
    session.flush()
    return site


def update_site(
    session: Session,
    principal: Principal,
    site_id: uuid.UUID,
    changes: dict[str, Any],
    *,
    request_id: str | None = None,
) -> Site | None:
    site = get_site(session, principal, site_id)
    if site is None:
        return None

    applied = {name: value for name, value in changes.items() if name in UPDATABLE}

    new_origin = applied.get("origin")
    if new_origin is not None and new_origin != site.origin:
        _reject_taken_origin(session, principal, site.project_id, new_origin)

    moved = changed_fields(site, applied)
    for name, value in applied.items():
        setattr(site, name, value)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as exc:
        raise DuplicateResourceError(DUPLICATE_ORIGIN_KO) from exc

    if applied.get("is_primary"):
        _demote_other_primaries(session, principal, site.project_id, site.id)

    audit.record(
        session,
        principal,
        action=f"{TARGET_TYPE}.update",
        target_type=TARGET_TYPE,
        target_id=site.id,
        request_id=request_id,
        detail={"changed_fields": moved},
    )
    session.flush()
    return site


def delete_site(session: Session, principal: Principal, site_id: uuid.UUID) -> None:
    """Always refuses, and only after the row has been resolved in the caller's scope.

    ``Site`` has no ``is_active`` column, and ``url_records`` and ``scans`` cascade off
    it. Another organization's site still answers 404 — the conflict would confirm it
    exists.
    """
    site = get_site(session, principal, site_id)
    if site is None:
        return None
    raise UndeletableResourceError(UNDELETABLE_KO)


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _reject_taken_origin(
    session: Session, principal: Principal, project_id: uuid.UUID, origin: str
) -> None:
    statement = (
        tenant_select(Site, principal)
        .where(Site.project_id == project_id)
        .where(Site.origin == origin)
    )
    assert_tenant_scoped(statement, principal.organization_id)
    if session.scalars(statement).first() is not None:
        raise DuplicateResourceError(DUPLICATE_ORIGIN_KO)


def _demote_other_primaries(
    session: Session, principal: Principal, project_id: uuid.UUID, keep_id: uuid.UUID
) -> None:
    """At most one primary site per project.

    Done by loading the siblings rather than issuing a bulk UPDATE, because a bulk
    statement would bypass ``tenant_select`` and there is no structural guard on UPDATE.
    A project has a handful of sites, so the read costs nothing worth saving.
    """
    statement = (
        tenant_select(Site, principal)
        .where(Site.project_id == project_id)
        .where(Site.id != keep_id)
        .where(Site.is_primary.is_(True))
    )
    assert_tenant_scoped(statement, principal.organization_id)
    for sibling in session.scalars(statement):
        sibling.is_primary = False
    session.flush()
