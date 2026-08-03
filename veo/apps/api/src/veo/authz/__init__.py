"""Authorization: who may do what, and inside which organization.

Owned by the integration maintainer. Feature workers depend on these guards; they do not
edit the permission matrix or the tenancy machinery.
"""

from veo.authz.deps import (
    CurrentPrincipal,
    OptionalPrincipal,
    OrganizationMismatch,
    PrincipalResolver,
    get_optional_principal,
    get_principal,
    get_principal_resolver,
    require,
    require_any,
    require_same_organization,
    set_principal_resolver,
)
from veo.authz.errors import (
    AuthenticationError,
    AuthorizationError,
    PermissionDeniedError,
    TenantIsolationError,
)
from veo.authz.permissions import ROLE_PERMISSIONS, Permission, permissions_for
from veo.authz.principal import SYSTEM_USER_ID, Principal, system_principal
from veo.authz.tenancy import (
    assert_tenant_scoped,
    is_tenant_scoped_model,
    tenant_select,
    tenant_table_names,
)

__all__ = [
    "ROLE_PERMISSIONS",
    "SYSTEM_USER_ID",
    "AuthenticationError",
    "AuthorizationError",
    "CurrentPrincipal",
    "OptionalPrincipal",
    "OrganizationMismatch",
    "Permission",
    "PermissionDeniedError",
    "Principal",
    "PrincipalResolver",
    "TenantIsolationError",
    "assert_tenant_scoped",
    "get_optional_principal",
    "get_principal",
    "get_principal_resolver",
    "is_tenant_scoped_model",
    "permissions_for",
    "require",
    "require_any",
    "require_same_organization",
    "set_principal_resolver",
    "system_principal",
    "tenant_select",
    "tenant_table_names",
]
