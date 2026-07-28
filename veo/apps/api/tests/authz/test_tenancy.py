"""Cross-tenant isolation, enforced structurally rather than by reviewer discipline.

The rule under test: knowing another organization's row id must never be enough to read
it, and a query against a tenant-owned table that forgot its organization filter must
fail loudly instead of quietly returning someone else's data.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from veo.authz import (
    Permission,
    Principal,
    TenantIsolationError,
    assert_tenant_scoped,
    is_tenant_scoped_model,
    tenant_select,
)
from veo.contracts.enums import Role
from veo.db.models import (
    AIEngine,
    Customer,
    Organization,
    Project,
    ScanRun,
    ScoringVersion,
    Site,
    User,
)

ORG_A = uuid.UUID("11111111-1111-4111-8111-111111111111")
ORG_B = uuid.UUID("22222222-2222-4222-8222-222222222222")


def principal(org: uuid.UUID = ORG_A, *roles: Role) -> Principal:
    return Principal(
        user_id=uuid.uuid4(),
        organization_id=org,
        roles=frozenset(roles or (Role.ANALYST,)),
        session_id="sess-test",
    )


# --------------------------------------------------------------------------- #
# Which models are tenant-owned
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("model", [Customer, Project, Site, ScanRun])
def test_tenant_owned_models_are_recognised(model: type) -> None:
    assert is_tenant_scoped_model(model)


@pytest.mark.parametrize("model", [Organization, User, ScoringVersion, AIEngine])
def test_global_models_are_not_tenant_scoped(model: type) -> None:
    assert not is_tenant_scoped_model(model)


# --------------------------------------------------------------------------- #
# tenant_select always carries the filter
# --------------------------------------------------------------------------- #


def test_tenant_select_filters_by_the_callers_organization() -> None:
    stmt = tenant_select(Project, principal(ORG_A))
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "organization_id" in compiled
    # PostgreSQL renders a UUID literal without hyphens.
    assert ORG_A.hex in compiled.replace("-", "")


def test_tenant_select_of_one_organization_never_mentions_another() -> None:
    stmt = tenant_select(Project, principal(ORG_A))
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True})).replace("-", "")
    assert ORG_B.hex not in compiled
    assert ORG_A.hex in compiled


def test_tenant_select_refuses_a_global_model() -> None:
    """Scoping a global table would silently return nothing; say so instead."""
    with pytest.raises(TenantIsolationError, match="not tenant-scoped"):
        tenant_select(Organization, principal())


def test_tenant_select_survives_additional_filters() -> None:
    stmt = tenant_select(Project, principal(ORG_A)).where(Project.slug == "acme")
    assert_tenant_scoped(stmt, ORG_A)


# --------------------------------------------------------------------------- #
# assert_tenant_scoped catches the forgotten filter
# --------------------------------------------------------------------------- #


def test_unscoped_query_on_a_tenant_table_is_rejected() -> None:
    with pytest.raises(TenantIsolationError) as exc:
        assert_tenant_scoped(select(Project), ORG_A)
    assert "projects" in str(exc.value)


def test_query_scoped_to_a_different_organization_is_rejected() -> None:
    stmt = tenant_select(Project, principal(ORG_B))
    with pytest.raises(TenantIsolationError):
        assert_tenant_scoped(stmt, ORG_A)


def test_filtering_only_by_primary_key_is_not_enough() -> None:
    """The classic hole: WHERE id = :guessed_uuid with no tenant predicate."""
    stmt = select(Project).where(Project.id == uuid.uuid4())
    with pytest.raises(TenantIsolationError):
        assert_tenant_scoped(stmt, ORG_A)


def test_query_on_a_global_table_needs_no_tenant_filter() -> None:
    assert_tenant_scoped(select(Organization), ORG_A)
    assert_tenant_scoped(select(ScoringVersion), ORG_A)


def test_join_pulling_in_a_tenant_table_must_still_be_scoped() -> None:
    stmt = select(Organization).join(Project, Project.organization_id == Organization.id)
    with pytest.raises(TenantIsolationError):
        assert_tenant_scoped(stmt, ORG_A)


def test_join_is_accepted_once_the_tenant_predicate_is_present() -> None:
    stmt = (
        select(Organization)
        .join(Project, Project.organization_id == Organization.id)
        .where(Project.organization_id == ORG_A)
    )
    assert_tenant_scoped(stmt, ORG_A)


def test_or_condition_does_not_satisfy_the_tenant_filter() -> None:
    """`WHERE org = me OR slug = 'x'` leaks every row whose slug matches."""
    from sqlalchemy import or_

    stmt = select(Project).where(
        or_(Project.organization_id == ORG_A, Project.slug == "public")
    )
    with pytest.raises(TenantIsolationError):
        assert_tenant_scoped(stmt, ORG_A)


def test_multiple_tenant_tables_all_need_scoping() -> None:
    stmt = (
        select(Project)
        .join(Site, Site.project_id == Project.id)
        .where(Project.organization_id == ORG_A)
    )
    with pytest.raises(TenantIsolationError, match="sites"):
        assert_tenant_scoped(stmt, ORG_A)


def test_all_tenant_tables_scoped_passes() -> None:
    stmt = (
        select(Project)
        .join(Site, Site.project_id == Project.id)
        .where(Project.organization_id == ORG_A)
        .where(Site.organization_id == ORG_A)
    )
    assert_tenant_scoped(stmt, ORG_A)


# --------------------------------------------------------------------------- #
# Every tenant-owned table in the schema is covered
# --------------------------------------------------------------------------- #


def test_every_model_with_organization_id_is_treated_as_tenant_scoped() -> None:
    from veo.db.models import Base

    for mapper_table in Base.metadata.tables.values():
        if "organization_id" not in mapper_table.c:
            continue
        if mapper_table.c.organization_id.nullable:
            # Nullable means the row can outlive its organization (audit, usage).
            continue
        assert mapper_table.name in _tenant_table_names(), (
            f"{mapper_table.name} carries organization_id but is not enforced"
        )


def _tenant_table_names() -> set[str]:
    from veo.authz.tenancy import tenant_table_names

    return tenant_table_names()


def test_principal_permissions_are_independent_of_tenancy() -> None:
    """Being in the right tenant does not grant a permission, and vice versa."""
    a = principal(ORG_A, Role.ANALYST)
    b = principal(ORG_B, Role.ANALYST)
    assert a.permissions == b.permissions
    assert a.organization_id != b.organization_id
    assert a.has(Permission.PROJECT_READ)
