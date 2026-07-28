"""FastAPI wiring for authorization.

This module is the seam between "who is calling" (the auth package, which owns tokens
and sessions) and "may they do this" (the permission matrix, which lives here). The auth
package registers a resolver; routers depend on :data:`CurrentPrincipal` and
:func:`require`. Neither side has to edit the other.

Routes are deny-by-default: a router that forgets ``require(...)`` still cannot be reached
anonymously, because :func:`get_principal` fails closed when no resolver is registered.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated, Protocol

from fastapi import Depends, FastAPI, Request

from veo.authz.errors import AuthenticationError
from veo.authz.permissions import Permission
from veo.authz.principal import Principal

_RESOLVER_ATTR = "veo_principal_resolver"
_PRINCIPAL_ATTR = "veo_principal"


class PrincipalResolver(Protocol):
    """Turns a request into a principal, or ``None`` when unauthenticated."""

    def __call__(self, request: Request) -> Awaitable[Principal | None]: ...


def set_principal_resolver(app: FastAPI, resolver: PrincipalResolver) -> None:
    setattr(app.state, _RESOLVER_ATTR, resolver)


def get_principal_resolver(app: FastAPI) -> PrincipalResolver | None:
    return getattr(app.state, _RESOLVER_ATTR, None)


async def get_principal(request: Request) -> Principal:
    """Resolve the caller, or fail.

    Caches on ``request.state`` so several dependencies in one request resolve the
    session once. Fails closed: with no resolver registered nothing is authenticated,
    rather than everything.
    """
    cached: Principal | None = getattr(request.state, _PRINCIPAL_ATTR, None)
    if cached is not None:
        return cached

    resolver = getattr(request.app.state, _RESOLVER_ATTR, None)
    if resolver is None:
        raise AuthenticationError("authentication is not configured")

    principal: Principal | None = await resolver(request)
    if principal is None:
        raise AuthenticationError("authentication required")

    setattr(request.state, _PRINCIPAL_ATTR, principal)
    return principal


async def get_optional_principal(request: Request) -> Principal | None:
    """For endpoints that behave differently when signed in but do not demand it."""
    try:
        return await get_principal(request)
    except AuthenticationError:
        return None


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]
OptionalPrincipal = Annotated[Principal | None, Depends(get_optional_principal)]


def require(*permissions: Permission) -> Callable[[Principal], Principal]:
    """Dependency factory demanding every listed permission.

    Usage::

        @router.post("/projects", dependencies=[Depends(require(Permission.PROJECT_WRITE))])
    """
    if not permissions:
        raise ValueError("require() needs at least one permission; use CurrentPrincipal")

    def dependency(principal: CurrentPrincipal) -> Principal:
        principal.require_all(*permissions)
        return principal

    return dependency


def require_any(*permissions: Permission) -> Callable[[Principal], Principal]:
    """Dependency factory demanding at least one of the listed permissions."""
    if not permissions:
        raise ValueError("require_any() needs at least one permission")

    def dependency(principal: CurrentPrincipal) -> Principal:
        principal.require_any(*permissions)
        return principal

    return dependency


class OrganizationMismatch(AuthenticationError):
    """A path organization id does not match the authenticated principal's."""


def require_same_organization(principal: Principal, organization_id: uuid.UUID) -> None:
    """Guard for routes that name an organization in the path.

    Callers should surface this as a 404, not a 403: telling someone their token is
    valid but for a different organization confirms that the organization exists.
    """
    if not principal.in_organization(organization_id):
        raise OrganizationMismatch("resource not found")
