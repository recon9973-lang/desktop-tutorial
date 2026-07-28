"""Authorization failures.

These deliberately carry no identifiers. An authorization error is often rendered to the
caller, and an error that echoes an organization or row id turns a denial into a
confirmation that the thing exists.
"""

from __future__ import annotations

from veo.authz.permissions import Permission


class AuthorizationError(Exception):
    """Base class for every authorization failure."""


class PermissionDeniedError(AuthorizationError):
    """The caller is authenticated but lacks the required permission."""

    def __init__(self, *permissions: Permission) -> None:
        self.permissions = tuple(permissions)
        names = ", ".join(p.value for p in permissions)
        super().__init__(f"missing required permission: {names}")


class TenantIsolationError(AuthorizationError):
    """A query would have crossed an organization boundary.

    Raised by the structural guard, not by user input. Reaching this means a code path
    forgot its tenant filter — it is a bug in VEO, never a customer's fault, and it must
    fail loudly rather than return someone else's rows.
    """


class AuthenticationError(AuthorizationError):
    """No usable credential was presented, or the credential is no longer valid."""

    def __init__(self, reason: str = "authentication required") -> None:
        super().__init__(reason)
