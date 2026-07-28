"""Writing the audit trail for resource changes.

Every create, update and delete leaves exactly one row: who did it, in which
organization, to what, and under which request id.

What a ``detail`` may contain is the part worth being strict about. The audit trail is
read by support staff and exported during incident review, so it holds identifiers and
field *names* only. A customer's name, industry or contact note never goes in — that is
the data the customer trusted VEO with, and duplicating it into a second store that
outlives the row (``organization_id`` is ``SET NULL`` on delete, so audit rows survive
their organization) is how a deletion request stops being honourable.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from veo.authz import Principal
from veo.db.models.identity import AuditLog


def record(
    session: Session,
    principal: Principal,
    *,
    action: str,
    target_type: str,
    target_id: uuid.UUID | str,
    request_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditLog:
    """Append one audit row. Flushed by the caller's unit of work, never committed here.

    ``action`` is ``resource.verb`` (``customer.create``). ``detail`` must be
    JSON-serialisable and must carry no customer contact details and no secrets.
    """
    entry = AuditLog(
        organization_id=principal.organization_id,
        actor_user_id=None if principal.is_service_account else principal.user_id,
        actor_kind="SERVICE" if principal.is_service_account else "USER",
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        request_id=request_id,
        detail=dict(detail or {}),
    )
    session.add(entry)
    return entry
