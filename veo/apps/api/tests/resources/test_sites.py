"""CRUD, tenancy, roles and origin rules for ``/sites``.

``origin`` is the field that decides what VEO is allowed to crawl, so it is stored as a
bare scheme-plus-host and nothing else. A path, a query, a credential or a stray
``inet_aton`` spelling of localhost is a validation failure, not something to normalise
away quietly.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from tests.resources.support import PROJECTS, SITES, Tenant, error_code, payload


def create_project(client: TestClient, slug: str = "ondam") -> dict[str, object]:
    response = client.post(PROJECTS, json={"slug": slug, "name": "온담의원 SEO"})
    assert response.status_code == 201, response.text
    return payload(response)


def create_site(
    client: TestClient, project_id: object, origin: str = "https://ondam.example", **extra: object
) -> dict[str, object]:
    response = client.post(
        SITES,
        json={
            "project_id": project_id,
            "origin": origin,
            "display_name": "대표 사이트",
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return payload(response)


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #


def test_create_then_read_back(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    project = create_project(client)
    created = create_site(client, project["id"], is_primary=True, crawl_settings={"depth": 3})

    assert created["project_id"] == project["id"]
    assert created["origin"] == "https://ondam.example"
    assert created["display_name"] == "대표 사이트"
    assert created["is_primary"] is True
    assert created["crawl_settings"] == {"depth": 3}

    assert payload(client.get(f"{SITES}/{created['id']}")) == created


def test_update_changes_only_what_was_sent(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    project = create_project(client)
    created = create_site(client, project["id"], crawl_settings={"depth": 3})

    updated = payload(client.patch(f"{SITES}/{created['id']}", json={"display_name": "본원"}))
    assert updated["display_name"] == "본원"
    assert updated["origin"] == created["origin"]
    assert updated["crawl_settings"] == {"depth": 3}


def test_a_project_has_at_most_one_primary_site(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    project = create_project(client)
    first = create_site(client, project["id"], origin="https://one.example", is_primary=True)
    second = create_site(client, project["id"], origin="https://two.example", is_primary=True)

    assert second["is_primary"] is True
    assert payload(client.get(f"{SITES}/{first['id']}"))["is_primary"] is False

    payload(client.patch(f"{SITES}/{first['id']}", json={"is_primary": True}))
    assert payload(client.get(f"{SITES}/{second['id']}"))["is_primary"] is False


def test_promoting_a_primary_does_not_touch_another_project(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    first_project = create_project(client, slug="first")
    second_project = create_project(client, slug="second")
    theirs = create_site(
        client, second_project["id"], origin="https://other.example", is_primary=True
    )

    create_site(client, first_project["id"], origin="https://mine.example", is_primary=True)
    assert payload(client.get(f"{SITES}/{theirs['id']}"))["is_primary"] is True


def test_list_can_be_filtered_by_project(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    first_project = create_project(client, slug="first")
    second_project = create_project(client, slug="second")
    mine = create_site(client, first_project["id"], origin="https://one.example")
    create_site(client, second_project["id"], origin="https://two.example")

    filtered = client.get(SITES, params={"project_id": first_project["id"]}).json()
    assert [row["id"] for row in filtered["data"]] == [mine["id"]]
    assert client.get(SITES).json()["page_info"]["total_items"] == 2


def test_listing_by_another_tenants_project_is_404(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, org_b: Tenant
) -> None:
    act_as(org_a.analyst)
    project = create_project(client)

    act_as(org_b.analyst)
    response = client.get(SITES, params={"project_id": project["id"]})
    assert response.status_code == 404
    assert error_code(response) == "NOT_FOUND"


# --------------------------------------------------------------------------- #
# Origin rules
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("given", "stored"),
    [
        ("https://ondam.example", "https://ondam.example"),
        ("HTTPS://Ondam.Example", "https://ondam.example"),
        ("https://ondam.example/", "https://ondam.example"),
        ("  https://ondam.example  ", "https://ondam.example"),
        ("https://ondam.example:443", "https://ondam.example"),
        ("http://ondam.example:80", "http://ondam.example"),
        ("https://ondam.example:8443", "https://ondam.example:8443"),
        ("https://www.ondam.example.", "https://www.ondam.example"),
    ],
)
def test_origins_are_stored_in_a_canonical_bare_form(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, given: str, stored: str
) -> None:
    act_as(org_a.analyst)
    project = create_project(client)
    assert create_site(client, project["id"], origin=given)["origin"] == stored


@pytest.mark.parametrize(
    "origin",
    [
        "",
        "ondam.example",
        "https://",
        "https://ondam.example/clinic",
        "https://ondam.example?utm=1",
        "https://ondam.example#top",
        "https://user:secret@ondam.example",
        "ftp://ondam.example",
        "javascript:alert(1)",
        "file:///etc/passwd",
        "https://ondam.example:0",
        "https://ondam.example:99999",
        "https://ondam example",
        "https://ondam.example\nX-Evil: 1",
        "https://0177.0.0.1",
        "https://2130706433",
        "https://" + "o" * 260 + ".example",
    ],
)
def test_bad_origins_are_rejected(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, origin: str
) -> None:
    act_as(org_a.analyst)
    project = create_project(client)
    response = client.post(
        SITES, json={"project_id": project["id"], "origin": origin, "display_name": "이름"}
    )
    assert response.status_code == 422, response.text
    assert error_code(response) == "VALIDATION_FAILED"


def test_an_origin_is_unique_within_a_project(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    project = create_project(client)
    create_site(client, project["id"])

    duplicate = client.post(
        SITES,
        json={
            "project_id": project["id"],
            "origin": "HTTPS://Ondam.Example/",
            "display_name": "중복",
        },
    )
    assert duplicate.status_code == 409
    assert error_code(duplicate) == "CONFLICT"


def test_the_same_origin_is_free_in_another_project(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    first_project = create_project(client, slug="first")
    second_project = create_project(client, slug="second")
    create_site(client, first_project["id"])
    assert create_site(client, second_project["id"])["origin"] == "https://ondam.example"


# --------------------------------------------------------------------------- #
# Cross-resource references
# --------------------------------------------------------------------------- #


def test_creating_under_another_tenants_project_is_404(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, org_b: Tenant
) -> None:
    act_as(org_a.analyst)
    project = create_project(client)

    act_as(org_b.analyst)
    response = client.post(
        SITES,
        json={"project_id": project["id"], "origin": "https://stolen.example", "display_name": "x"},
    )
    assert response.status_code == 404
    assert error_code(response) == "NOT_FOUND"


def test_creating_under_an_unknown_project_is_404(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    response = client.post(
        SITES,
        json={
            "project_id": str(uuid.uuid4()),
            "origin": "https://ghost.example",
            "display_name": "x",
        },
    )
    assert response.status_code == 404


def test_a_site_cannot_be_moved_between_projects(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    first_project = create_project(client, slug="first")
    second_project = create_project(client, slug="second")
    created = create_site(client, first_project["id"])

    response = client.patch(f"{SITES}/{created['id']}", json={"project_id": second_project["id"]})
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Delete
# --------------------------------------------------------------------------- #


def test_a_site_cannot_be_deleted(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    """No ``is_active`` column, and scans and URL records cascade off this row."""
    act_as(org_a.analyst)
    project = create_project(client)
    created = create_site(client, project["id"])

    response = client.delete(f"{SITES}/{created['id']}")
    assert response.status_code == 409
    assert error_code(response) == "CONFLICT"
    assert client.get(f"{SITES}/{created['id']}").status_code == 200


def test_deleting_another_tenants_site_is_still_404(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, org_b: Tenant
) -> None:
    act_as(org_a.analyst)
    project = create_project(client)
    created = create_site(client, project["id"])

    act_as(org_b.analyst)
    assert client.delete(f"{SITES}/{created['id']}").status_code == 404


# --------------------------------------------------------------------------- #
# Audit
# --------------------------------------------------------------------------- #


def test_writes_are_audited(
    client: TestClient,
    act_as: Callable[..., None],
    org_a: Tenant,
    audit_rows: Callable[..., list],
) -> None:
    act_as(org_a.analyst)
    project = create_project(client)
    created = create_site(client, project["id"])
    client.patch(f"{SITES}/{created['id']}", json={"display_name": "본원"})

    rows = [row for row in audit_rows(org_a.organization_id) if row.target_type == "site"]
    assert [row.action for row in rows] == ["site.create", "site.update"]
    assert rows[0].detail["origin"] == "https://ondam.example"
    assert rows[0].detail["project_id"] == project["id"]
    assert rows[1].detail["changed_fields"] == ["display_name"]


# --------------------------------------------------------------------------- #
# Tenancy and roles
# --------------------------------------------------------------------------- #


def test_a_list_never_contains_another_organizations_rows(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, org_b: Tenant
) -> None:
    act_as(org_a.analyst)
    mine = create_site(client, create_project(client)["id"], origin="https://mine.example")
    act_as(org_b.analyst)
    create_site(client, create_project(client)["id"], origin="https://theirs.example")

    act_as(org_a.analyst)
    assert [row["id"] for row in client.get(SITES).json()["data"]] == [mine["id"]]


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_another_organizations_site_is_404(
    client: TestClient,
    act_as: Callable[..., None],
    org_a: Tenant,
    org_b: Tenant,
    method: str,
) -> None:
    act_as(org_a.analyst)
    created = create_site(client, create_project(client)["id"])

    act_as(org_b.analyst)
    url = f"{SITES}/{created['id']}"
    response = (
        client.patch(url, json={"display_name": "탈취"})
        if method == "patch"
        else getattr(client, method)(url)
    )
    assert response.status_code == 404


def test_sales_viewer_reads_but_cannot_write(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    project = create_project(client)
    created = create_site(client, project["id"])

    act_as(org_a.viewer)
    assert client.get(SITES).status_code == 200
    assert client.get(f"{SITES}/{created['id']}").status_code == 200
    assert (
        client.post(
            SITES,
            json={"project_id": project["id"], "origin": "https://x.example", "display_name": "x"},
        ).status_code
        == 403
    )
    patched = client.patch(f"{SITES}/{created['id']}", json={"display_name": "몰래"})
    assert patched.status_code == 403
    assert client.delete(f"{SITES}/{created['id']}").status_code == 403


def test_pagination_bounds(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    assert client.get(SITES, params={"page_size": 201}).status_code == 422
    assert client.get(SITES, params={"page": 0}).status_code == 422
    assert client.get(SITES, params={"page_size": 200}).status_code == 200
