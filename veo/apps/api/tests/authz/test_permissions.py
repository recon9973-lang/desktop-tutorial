"""The role/permission matrix is a security boundary, so it is asserted, not assumed.

Deny by default: a role holds exactly what the matrix grants it and nothing else.
These tests exist so that widening a role is a deliberate, reviewed change rather than
something that happens by accident while adding a feature.
"""

from __future__ import annotations

import dataclasses

import pytest

from veo.authz import (
    ROLE_PERMISSIONS,
    Permission,
    PermissionDeniedError,
    Principal,
    permissions_for,
)
from veo.contracts.enums import Role

WRITE_PERMISSIONS = frozenset(
    p for p in Permission if p.value.split(":", 1)[1] not in {"read", "read_state"}
)


def make_principal(*roles: Role) -> Principal:
    import uuid

    return Principal(
        user_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        roles=frozenset(roles),
        session_id="sess-test",
    )


# --------------------------------------------------------------------------- #
# Matrix integrity
# --------------------------------------------------------------------------- #


def test_every_role_appears_in_the_matrix() -> None:
    assert set(ROLE_PERMISSIONS) == set(Role)


def test_every_permission_is_granted_to_at_least_one_role() -> None:
    granted = frozenset().union(*ROLE_PERMISSIONS.values())
    orphans = set(Permission) - granted
    assert not orphans, f"permissions nobody can ever hold: {sorted(orphans)}"


def test_super_admin_holds_every_permission() -> None:
    assert ROLE_PERMISSIONS[Role.SUPER_ADMIN] == frozenset(Permission)


def test_no_role_other_than_super_admin_holds_everything() -> None:
    for role, granted in ROLE_PERMISSIONS.items():
        if role is Role.SUPER_ADMIN:
            continue
        assert granted != frozenset(Permission), f"{role} is a second super admin"


def test_permission_values_are_namespaced() -> None:
    for permission in Permission:
        resource, _, action = permission.value.partition(":")
        assert resource and action, f"{permission} is not resource:action"


# --------------------------------------------------------------------------- #
# Least privilege per role
# --------------------------------------------------------------------------- #


def test_viewer_roles_hold_no_write_permission() -> None:
    for role in (Role.SALES_VIEWER, Role.CLIENT_VIEWER):
        writes = ROLE_PERMISSIONS[role] & WRITE_PERMISSIONS
        assert not writes, f"{role} can write: {sorted(writes)}"


def test_only_super_admin_manages_provider_credentials() -> None:
    """A stored Naver or OpenAI secret is the crown jewel; one role touches it."""
    holders = {r for r, p in ROLE_PERMISSIONS.items() if Permission.CREDENTIAL_MANAGE in p}
    assert holders == {Role.SUPER_ADMIN}


def test_no_role_can_read_a_credential_secret_back() -> None:
    """There is deliberately no read-the-secret permission — only its state."""
    assert not any(p.value.startswith("credential:read_secret") for p in Permission)


def test_only_lab_roles_publish_a_scoring_specification() -> None:
    """VEO-LAB owns methodology. An analyst must not be able to move a score band."""
    holders = {r for r, p in ROLE_PERMISSIONS.items() if Permission.SCORING_SPEC_PUBLISH in p}
    assert holders == {Role.SUPER_ADMIN, Role.LAB_ADMIN}


def test_client_viewer_cannot_reach_internal_material() -> None:
    granted = ROLE_PERMISSIONS[Role.CLIENT_VIEWER]
    for forbidden in (
        Permission.EVIDENCE_READ,
        Permission.AUDIT_READ,
        Permission.USAGE_READ,
        Permission.USER_READ,
        Permission.CREDENTIAL_READ_STATE,
    ):
        assert forbidden not in granted, f"CLIENT_VIEWER should not hold {forbidden}"


def test_sales_viewer_cannot_read_raw_evidence() -> None:
    """Raw crawl and AI-answer material is not sales-facing."""
    assert Permission.EVIDENCE_READ not in ROLE_PERMISSIONS[Role.SALES_VIEWER]


def test_developer_can_read_evidence_and_work_issues() -> None:
    granted = ROLE_PERMISSIONS[Role.DEVELOPER]
    assert Permission.EVIDENCE_READ in granted
    assert Permission.ISSUE_WRITE in granted


def test_analyst_can_run_scans_but_not_manage_users() -> None:
    granted = ROLE_PERMISSIONS[Role.ANALYST]
    assert Permission.SCAN_RUN in granted
    assert Permission.USER_MANAGE not in granted
    assert Permission.ROLE_ASSIGN not in granted


def test_only_super_admin_assigns_roles() -> None:
    holders = {r for r, p in ROLE_PERMISSIONS.items() if Permission.ROLE_ASSIGN in p}
    assert holders == {Role.SUPER_ADMIN}


# --------------------------------------------------------------------------- #
# Resolution
# --------------------------------------------------------------------------- #


def test_no_role_means_no_permission() -> None:
    assert permissions_for(frozenset()) == frozenset()


def test_multiple_roles_union_their_permissions() -> None:
    combined = permissions_for(frozenset({Role.SALES_VIEWER, Role.DEVELOPER}))
    assert combined == ROLE_PERMISSIONS[Role.SALES_VIEWER] | ROLE_PERMISSIONS[Role.DEVELOPER]


def test_principal_without_roles_is_denied_everything() -> None:
    principal = make_principal()
    assert principal.permissions == frozenset()
    for permission in Permission:
        assert not principal.has(permission)


def test_principal_require_raises_with_the_permission_named() -> None:
    principal = make_principal(Role.SALES_VIEWER)
    with pytest.raises(PermissionDeniedError) as exc:
        principal.require(Permission.PROJECT_WRITE)
    assert Permission.PROJECT_WRITE.value in str(exc.value)


def test_principal_require_passes_for_a_granted_permission() -> None:
    principal = make_principal(Role.ANALYST)
    principal.require(Permission.PROJECT_READ)


def test_principal_require_all_needs_every_permission() -> None:
    principal = make_principal(Role.SALES_VIEWER)
    with pytest.raises(PermissionDeniedError):
        principal.require_all(Permission.REPORT_READ, Permission.PROJECT_WRITE)


def test_principal_is_hashable_and_frozen() -> None:
    principal = make_principal(Role.ANALYST)
    hash(principal)
    with pytest.raises(dataclasses.FrozenInstanceError):
        principal.roles = frozenset()  # type: ignore[misc]


def test_permission_denied_error_never_echoes_the_organization_id() -> None:
    """An error message must not confirm which tenant the caller probed."""
    principal = make_principal(Role.CLIENT_VIEWER)
    with pytest.raises(PermissionDeniedError) as exc:
        principal.require(Permission.ORG_MANAGE)
    assert str(principal.organization_id) not in str(exc.value)
    assert str(principal.user_id) not in str(exc.value)
