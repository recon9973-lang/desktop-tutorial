"""The structural half of tenancy: the guard itself, and proof that the services use it.

The endpoint-level 404 matrix lives in the per-resource modules. What is checked here is
one level down — that ``assert_tenant_scoped`` really does reject an unfiltered statement,
and that every list and get path actually calls it before touching the database. A guard
nobody calls protects nothing, and that is exactly the failure mode that would never show
up as a red test anywhere else.
"""

from __future__ import annotations

import importlib
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session
from tests.resources.support import CUSTOMERS, PROJECTS, SITES, Tenant, payload

from veo.authz import assert_tenant_scoped, tenant_select
from veo.authz.errors import TenantIsolationError
from veo.db.models.identity import Customer, Project, Site

SERVICE_MODULES = [
    "veo.customers.service",
    "veo.projects.service",
    "veo.sites.service",
]


# --------------------------------------------------------------------------- #
# The guard itself
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("model", [Customer, Project, Site])
def test_an_unscoped_statement_is_refused(model: type[Any]) -> None:
    with pytest.raises(TenantIsolationError):
        assert_tenant_scoped(select(model), uuid.uuid4())


def test_a_scoped_statement_is_accepted(org_a: Tenant) -> None:
    statement = tenant_select(Customer, org_a.analyst)
    assert_tenant_scoped(statement, org_a.organization_id)


def test_a_statement_scoped_to_somebody_else_is_refused(org_a: Tenant, org_b: Tenant) -> None:
    statement = tenant_select(Customer, org_a.analyst)
    with pytest.raises(TenantIsolationError):
        assert_tenant_scoped(statement, org_b.organization_id)


def test_an_or_branch_defeats_the_filter_and_is_refused(org_a: Tenant) -> None:
    """``org = me OR slug = 'x'`` returns other tenants' rows; the guard must say so."""
    statement = select(Customer).where(
        or_(
            Customer.organization_id == org_a.organization_id,
            Customer.name == "아무거나",
        )
    )
    with pytest.raises(TenantIsolationError):
        assert_tenant_scoped(statement, org_a.organization_id)


# --------------------------------------------------------------------------- #
# The services really call it
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("module_name", SERVICE_MODULES)
def test_each_service_module_imports_the_guard(module_name: str) -> None:
    module = importlib.import_module(module_name)
    assert module.assert_tenant_scoped is assert_tenant_scoped
    assert module.tenant_select is tenant_select


def test_reads_run_the_guard_on_every_statement(
    client: TestClient,
    act_as: Callable[..., None],
    org_a: Tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    act_as(org_a.analyst)
    customer = payload(client.post(CUSTOMERS, json={"name": "온담의원"}))
    project = payload(client.post(PROJECTS, json={"slug": "ondam", "name": "온담 SEO"}))
    site = payload(
        client.post(
            SITES,
            json={
                "project_id": project["id"],
                "origin": "https://ondam.example",
                "display_name": "대표",
            },
        )
    )

    seen: list[tuple[Select[Any], uuid.UUID]] = []

    def spy(statement: Select[Any], organization_id: uuid.UUID) -> None:
        seen.append((statement, organization_id))
        assert_tenant_scoped(statement, organization_id)

    for module_name in SERVICE_MODULES:
        monkeypatch.setattr(importlib.import_module(module_name), "assert_tenant_scoped", spy)

    for url in (
        CUSTOMERS,
        f"{CUSTOMERS}/{customer['id']}",
        PROJECTS,
        f"{PROJECTS}/{project['id']}",
        SITES,
        f"{SITES}/{site['id']}",
    ):
        assert client.get(url).status_code == 200

    assert len(seen) >= 6
    assert {organization_id for _, organization_id in seen} == {org_a.organization_id}


def test_writes_run_the_guard_too(
    client: TestClient,
    act_as: Callable[..., None],
    org_a: Tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    act_as(org_a.analyst)
    customer = payload(client.post(CUSTOMERS, json={"name": "온담의원"}))

    calls: list[uuid.UUID] = []

    def spy(statement: Select[Any], organization_id: uuid.UUID) -> None:
        calls.append(organization_id)
        assert_tenant_scoped(statement, organization_id)

    service = importlib.import_module("veo.customers.service")
    monkeypatch.setattr(service, "assert_tenant_scoped", spy)

    patched = client.patch(f"{CUSTOMERS}/{customer['id']}", json={"name": "새 이름"})
    assert patched.status_code == 200
    assert client.delete(f"{CUSTOMERS}/{customer['id']}").status_code == 200
    assert calls == [org_a.organization_id, org_a.organization_id]


# --------------------------------------------------------------------------- #
# The service layer, below HTTP
# --------------------------------------------------------------------------- #


def test_a_service_lookup_cannot_reach_across_organizations(
    client: TestClient,
    act_as: Callable[..., None],
    org_a: Tenant,
    org_b: Tenant,
    db: Session,
) -> None:
    from veo.customers import service as customer_service

    act_as(org_a.analyst)
    created = payload(client.post(CUSTOMERS, json={"name": "온담의원"}))
    db.rollback()

    customer_id = uuid.UUID(str(created["id"]))
    assert customer_service.get_customer(db, org_a.analyst, customer_id) is not None
    assert customer_service.get_customer(db, org_b.analyst, customer_id) is None


def test_a_service_list_cannot_reach_across_organizations(
    client: TestClient,
    act_as: Callable[..., None],
    org_a: Tenant,
    org_b: Tenant,
    db: Session,
) -> None:
    from veo.customers import service as customer_service

    act_as(org_a.analyst)
    payload(client.post(CUSTOMERS, json={"name": "온담의원"}))
    db.rollback()

    mine, mine_total = customer_service.list_customers(db, org_a.analyst, page=1, page_size=50)
    theirs, theirs_total = customer_service.list_customers(db, org_b.analyst, page=1, page_size=50)

    assert mine_total == 1
    assert len(mine) == 1
    assert theirs_total == 0
    assert theirs == []
