"""CRUD, tenancy, roles and referential rules for ``/projects``.

The rule with teeth here is the cross-resource one: a project's ``customer_id`` is
resolved through the caller's own tenant scope, so pointing at another organization's
customer has to come back as a plain 404 — not a foreign-key error, and not a 403 that
would confirm the row exists.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from tests.resources.support import CUSTOMERS, PROJECTS, Tenant, error_code, payload


def create_project(client: TestClient, slug: str = "ondam", **extra: object) -> dict[str, object]:
    body: dict[str, object] = {"slug": slug, "name": "온담의원 SEO", **extra}
    response = client.post(PROJECTS, json=body)
    assert response.status_code == 201, response.text
    return payload(response)


def create_customer(client: TestClient, name: str = "온담의원") -> dict[str, object]:
    response = client.post(CUSTOMERS, json={"name": name})
    assert response.status_code == 201, response.text
    return payload(response)


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #


def test_create_then_read_back(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    customer = create_customer(client)
    created = create_project(
        client,
        slug="ondam-seo",
        customer_id=customer["id"],
        locale="ko-KR",
        settings={"note": "1차"},
    )

    assert created["slug"] == "ondam-seo"
    assert created["customer_id"] == customer["id"]
    assert created["locale"] == "ko-KR"
    assert created["settings"] == {"note": "1차"}
    assert created["default_seo_spec_version"] is None

    assert payload(client.get(f"{PROJECTS}/{created['id']}")) == created


def test_defaults_are_applied(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    created = create_project(client)
    assert created["locale"] == "ko-KR"
    assert created["settings"] == {}
    assert created["customer_id"] is None


def test_update_changes_only_what_was_sent(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    created = create_project(client, settings={"note": "1차"})

    updated = payload(
        client.patch(f"{PROJECTS}/{created['id']}", json={"name": "온담의원 GEO"})
    )
    assert updated["name"] == "온담의원 GEO"
    assert updated["slug"] == created["slug"]
    assert updated["settings"] == {"note": "1차"}


def test_update_can_reassign_the_customer_and_clear_it(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    first = create_customer(client, name="고객사 1")
    second = create_customer(client, name="고객사 2")
    created = create_project(client, customer_id=first["id"])

    moved = payload(client.patch(f"{PROJECTS}/{created['id']}", json={"customer_id": second["id"]}))
    assert moved["customer_id"] == second["id"]

    cleared = payload(client.patch(f"{PROJECTS}/{created['id']}", json={"customer_id": None}))
    assert cleared["customer_id"] is None


def test_list_can_be_filtered_by_customer(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    customer = create_customer(client)
    attached = create_project(client, slug="attached", customer_id=customer["id"])
    create_project(client, slug="detached")

    filtered = client.get(PROJECTS, params={"customer_id": customer["id"]}).json()
    assert [row["id"] for row in filtered["data"]] == [attached["id"]]
    assert filtered["page_info"]["total_items"] == 1

    assert client.get(PROJECTS).json()["page_info"]["total_items"] == 2


# --------------------------------------------------------------------------- #
# Slug rules
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "slug",
    [
        "",
        "a",
        "Ondam",
        "ondam seo",
        "ondam_seo",
        "-ondam",
        "ondam-",
        "ondam--seo",
        "온담",
        "ondam/seo",
        "o" * 81,
    ],
)
def test_bad_slugs_are_rejected(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, slug: str
) -> None:
    act_as(org_a.analyst)
    response = client.post(PROJECTS, json={"slug": slug, "name": "이름"})
    assert response.status_code == 422
    assert error_code(response) == "VALIDATION_FAILED"


@pytest.mark.parametrize("slug", ["ab", "ondam", "ondam-seo-2026", "a1-b2-c3", "o" * 80])
def test_good_slugs_are_accepted(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, slug: str
) -> None:
    act_as(org_a.analyst)
    assert client.post(PROJECTS, json={"slug": slug, "name": "이름"}).status_code == 201


def test_a_slug_is_unique_within_an_organization(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    create_project(client, slug="ondam")

    duplicate = client.post(PROJECTS, json={"slug": "ondam", "name": "다른 이름"})
    assert duplicate.status_code == 409
    assert error_code(duplicate) == "CONFLICT"


def test_the_same_slug_is_free_in_another_organization(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, org_b: Tenant
) -> None:
    act_as(org_a.analyst)
    create_project(client, slug="ondam")

    act_as(org_b.analyst)
    assert client.post(PROJECTS, json={"slug": "ondam", "name": "이름"}).status_code == 201


def test_renaming_a_slug_onto_a_taken_one_conflicts(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    create_project(client, slug="first")
    second = create_project(client, slug="second")

    response = client.patch(f"{PROJECTS}/{second['id']}", json={"slug": "first"})
    assert response.status_code == 409


# --------------------------------------------------------------------------- #
# Cross-resource references
# --------------------------------------------------------------------------- #


def test_creating_with_another_tenants_customer_id_is_404(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, org_b: Tenant
) -> None:
    act_as(org_a.analyst)
    foreign_customer = create_customer(client)

    act_as(org_b.analyst)
    response = client.post(
        PROJECTS, json={"slug": "stolen", "name": "이름", "customer_id": foreign_customer["id"]}
    )
    assert response.status_code == 404
    assert error_code(response) == "NOT_FOUND"


def test_creating_with_an_unknown_customer_id_is_404(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    response = client.post(
        PROJECTS, json={"slug": "ghost", "name": "이름", "customer_id": str(uuid.uuid4())}
    )
    assert response.status_code == 404


def test_a_rejected_reference_leaves_no_project_behind(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, org_b: Tenant
) -> None:
    act_as(org_a.analyst)
    foreign_customer = create_customer(client)

    act_as(org_b.analyst)
    client.post(
        PROJECTS, json={"slug": "stolen", "name": "이름", "customer_id": foreign_customer["id"]}
    )
    assert client.get(PROJECTS).json()["page_info"]["total_items"] == 0


def test_updating_onto_another_tenants_customer_id_is_404(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, org_b: Tenant
) -> None:
    act_as(org_a.analyst)
    foreign_customer = create_customer(client)

    act_as(org_b.analyst)
    created = create_project(client)
    response = client.patch(
        f"{PROJECTS}/{created['id']}", json={"customer_id": foreign_customer["id"]}
    )
    assert response.status_code == 404
    assert payload(client.get(f"{PROJECTS}/{created['id']}"))["customer_id"] is None


# --------------------------------------------------------------------------- #
# Delete
# --------------------------------------------------------------------------- #


def test_a_project_cannot_be_deleted(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    """No ``is_active`` column, and every scan and report cascades off this row.

    A hard delete would silently destroy immutable run history, so the endpoint refuses.
    """
    act_as(org_a.analyst)
    created = create_project(client)

    response = client.delete(f"{PROJECTS}/{created['id']}")
    assert response.status_code == 409
    assert error_code(response) == "CONFLICT"
    assert client.get(f"{PROJECTS}/{created['id']}").status_code == 200


def test_deleting_another_tenants_project_is_still_404(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, org_b: Tenant
) -> None:
    """404 wins over 409 — the conflict answer would confirm the row exists."""
    act_as(org_a.analyst)
    created = create_project(client)

    act_as(org_b.analyst)
    assert client.delete(f"{PROJECTS}/{created['id']}").status_code == 404


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
    created = create_project(client, slug="ondam")
    client.patch(f"{PROJECTS}/{created['id']}", json={"name": "새 이름"})

    rows = [row for row in audit_rows(org_a.organization_id) if row.target_type == "project"]
    assert [row.action for row in rows] == ["project.create", "project.update"]
    assert rows[0].detail["slug"] == "ondam"
    assert rows[1].detail["changed_fields"] == ["name"]
    assert all(row.target_id == created["id"] for row in rows)


# --------------------------------------------------------------------------- #
# Tenancy and roles
# --------------------------------------------------------------------------- #


def test_a_list_never_contains_another_organizations_rows(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, org_b: Tenant
) -> None:
    act_as(org_a.analyst)
    mine = create_project(client, slug="mine")
    act_as(org_b.analyst)
    create_project(client, slug="theirs")

    act_as(org_a.analyst)
    listed = client.get(PROJECTS).json()["data"]
    assert [row["id"] for row in listed] == [mine["id"]]


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_another_organizations_project_is_404(
    client: TestClient,
    act_as: Callable[..., None],
    org_a: Tenant,
    org_b: Tenant,
    method: str,
) -> None:
    act_as(org_a.analyst)
    created = create_project(client)

    act_as(org_b.analyst)
    url = f"{PROJECTS}/{created['id']}"
    response = (
        client.patch(url, json={"name": "탈취"})
        if method == "patch"
        else getattr(client, method)(url)
    )
    assert response.status_code == 404


def test_sales_viewer_reads_but_cannot_write(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    created = create_project(client)

    act_as(org_a.viewer)
    assert client.get(PROJECTS).status_code == 200
    assert client.get(f"{PROJECTS}/{created['id']}").status_code == 200
    assert client.post(PROJECTS, json={"slug": "nope", "name": "이름"}).status_code == 403
    assert client.patch(f"{PROJECTS}/{created['id']}", json={"name": "몰래"}).status_code == 403
    assert client.delete(f"{PROJECTS}/{created['id']}").status_code == 403


# --------------------------------------------------------------------------- #
# Pagination and validation
# --------------------------------------------------------------------------- #


def test_pagination_bounds(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    assert client.get(PROJECTS, params={"page_size": 201}).status_code == 422
    assert client.get(PROJECTS, params={"page": 0}).status_code == 422
    assert client.get(PROJECTS, params={"page_size": 200}).status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        {"name": "이름"},
        {"slug": "ondam"},
        {"slug": "ondam", "name": ""},
        {"slug": "ondam", "name": "이름", "locale": "korean-language-tag"},
        {"slug": "ondam", "name": "이름", "unexpected": "값"},
        {
            "slug": "ondam",
            "name": "이름",
            "organization_id": "00000000-0000-0000-0000-000000000000",
        },
        {"slug": "ondam", "name": "이름", "settings": "문자열"},
    ],
)
def test_create_rejects_bad_input(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, body: dict[str, object]
) -> None:
    act_as(org_a.analyst)
    assert client.post(PROJECTS, json=body).status_code == 422
