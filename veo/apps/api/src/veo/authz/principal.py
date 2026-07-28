"""Who is making a request, and what they are allowed to do."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from functools import cached_property

from veo.authz.errors import PermissionDeniedError
from veo.authz.permissions import Permission, permissions_for
from veo.contracts.enums import Role


@dataclass(frozen=True)
class Principal:
    """An authenticated caller, bound to exactly one organization.

    A principal is per-organization by construction. A user who belongs to two
    organizations authenticates into one of them and gets one principal; there is no
    ambient "all my organizations" identity that a handler could accidentally trust.
    """

    user_id: uuid.UUID
    organization_id: uuid.UUID
    roles: frozenset[Role]
    session_id: str
    is_service_account: bool = False
    display_name: str = field(default="", compare=False)

    @cached_property
    def permissions(self) -> frozenset[Permission]:
        return permissions_for(self.roles)

    def has(self, permission: Permission) -> bool:
        return permission in self.permissions

    def has_any(self, *permissions: Permission) -> bool:
        return any(p in self.permissions for p in permissions)

    def require(self, permission: Permission) -> None:
        """Raise unless the caller holds ``permission``.

        The message names the missing permission — useful to a developer reading logs —
        but never the user or organization id, so an error can be surfaced without
        confirming anything about the caller's tenant.
        """
        if permission not in self.permissions:
            raise PermissionDeniedError(permission)

    def require_all(self, *permissions: Permission) -> None:
        for permission in permissions:
            self.require(permission)

    def require_any(self, *permissions: Permission) -> None:
        if not self.has_any(*permissions):
            raise PermissionDeniedError(*permissions)

    def in_organization(self, organization_id: uuid.UUID) -> bool:
        return self.organization_id == organization_id
