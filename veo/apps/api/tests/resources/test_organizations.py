"""``/organizations`` is read-only in Phase 1, and reads exactly one row: your own.

The interesting assertions are the negative ones — there is no route that lists every
organization, no route that writes one, and asking for somebody else's id is byte-for-byte
indistinguishable from asking for an id that does not exist.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient
from tests.resources.support import ORGANIZATIONS, Tenant, error_code, payload


def test_current_returns_the_callers_own_organization(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    response = client.get(f"{ORGANIZATIONS}/current")

    assert response.status_code == 200
    data = payload(response)
    assert data["id"] == str(org_a.organization_id)
    assert data["slug"] == org_a.slug
    assert data["name"] == org_a.name
    assert data["is_active"] is True


def test_get_by_id_returns_the_callers_own_organization(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    response = client.get(f"{ORGANIZATIONS}/{org_a.organization_id}")

    assert response.status_code == 200
    assert payload(response)["id"] == str(org_a.organization_id)


def test_another_organization_is_not_found_not_forbidden(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, org_b: Tenant
) -> None:
    act_as(org_b.analyst)
    response = client.get(f"{ORGANIZATIONS}/{org_a.organization_id}")

    assert response.status_code == 404
    assert error_code(response) == "NOT_FOUND"


def test_unknown_organization_is_not_found(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    assert client.get(f"{ORGANIZATIONS}/{uuid.uuid4()}").status_code == 404


def test_a_missing_organization_and_a_foreign_one_are_indistinguishable(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, org_b: Tenant
) -> None:
    act_as(org_b.analyst)
    foreign = client.get(f"{ORGANIZATIONS}/{org_a.organization_id}")
    missing = client.get(f"{ORGANIZATIONS}/{uuid.uuid4()}")

    assert foreign.status_code == missing.status_code == 404
    assert foreign.json()["error"]["code"] == missing.json()["error"]["code"]
    assert foreign.json()["error"]["message"] == missing.json()["error"]["message"]


def test_sales_viewer_may_read_its_organization(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.viewer)
    assert client.get(f"{ORGANIZATIONS}/current").status_code == 200


def test_there_is_no_endpoint_that_lists_organizations(app: FastAPI) -> None:
    paths = {getattr(route, "path", "") for route in app.routes}
    assert ORGANIZATIONS not in paths
    assert f"{ORGANIZATIONS}/" not in paths


def test_organizations_expose_no_write_verbs(app: FastAPI) -> None:
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith(ORGANIZATIONS):
            methods = set(getattr(route, "methods", set()))
            assert methods <= {"GET", "HEAD", "OPTIONS"}, (path, methods)
