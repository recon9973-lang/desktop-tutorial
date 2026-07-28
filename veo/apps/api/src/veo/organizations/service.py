"""Reading the caller's own organization.

``organizations`` is the one table in this slice that :func:`veo.authz.tenant_select`
refuses, and correctly so: it has no ``organization_id`` column because it *is* the
organization. The equivalent guard is that the only id this module will ever look up is
``principal.organization_id`` — the caller's id is never taken from the request.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.authz import Principal
from veo.db.models.identity import Organization


def get_own_organization(session: Session, principal: Principal) -> Organization | None:
    """The organization the principal belongs to, or ``None`` if the row is gone.

    A missing row means the organization was deleted while a session was still live. The
    caller renders that as a 404 rather than a 500 — there is nothing for the caller to
    fix, and nothing to leak.
    """
    statement = select(Organization).where(Organization.id == principal.organization_id)
    return session.scalars(statement).one_or_none()


def get_organization(
    session: Session, principal: Principal, organization_id: uuid.UUID
) -> Organization | None:
    """The organization named in the path, but only if it is the caller's own.

    Any other id — including one that exists — returns ``None``, so the route can answer
    404 and say nothing about which organizations are real.
    """
    if not principal.in_organization(organization_id):
        return None
    return get_own_organization(session, principal)
