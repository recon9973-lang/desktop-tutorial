"""CRUD, tenancy, roles and pagination for ``/customers``.

A customer row carries the only free-text contact field in this slice
(``contact_note``), so this module also pins down what the audit trail is allowed to
remember about it: that the field changed, never what it changed to.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from tests.resources.support import CUSTOMERS, Tenant, error_code, payload


def create_customer(
    client: TestClient, name: str = "온담의원", **extra: object
) -> dict[str, object]:
    response = client.post(CUSTOMERS, json={"name": name, **extra})
    assert response.status_code == 201, response.text
    return payload(response)


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #


def test_create_then_read_back(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    created = create_customer(
        client, name="온담의원", industry="의료", contact_note="담당 김실장"
    )

    assert created["name"] == "온담의원"
    assert created["industry"] == "의료"
    assert created["contact_note"] == "담당 김실장"
    assert created["is_active"] is True

    fetched = payload(client.get(f"{CUSTOMERS}/{created['id']}"))
    assert fetched == created


def test_update_changes_only_what_was_sent(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    created = create_customer(client, industry="의료", contact_note="담당 김실장")

    updated = payload(
        client.patch(f"{CUSTOMERS}/{created['id']}", json={"name": "온담의원 강남점"})
    )
    assert updated["name"] == "온담의원 강남점"
    assert updated["industry"] == "의료"
    assert updated["contact_note"] == "담당 김실장"


def test_update_can_clear_a_nullable_field(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    created = create_customer(client, contact_note="담당 김실장")

    updated = payload(client.patch(f"{CUSTOMERS}/{created['id']}", json={"contact_note": None}))
    assert updated["contact_note"] is None


def test_update_with_no_fields_is_rejected(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    created = create_customer(client)

    response = client.patch(f"{CUSTOMERS}/{created['id']}", json={})
    assert response.status_code == 422
    assert error_code(response) == "VALIDATION_FAILED"


def test_delete_is_soft_and_hides_the_row_from_the_default_list(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    created = create_customer(client)

    deleted = payload(client.delete(f"{CUSTOMERS}/{created['id']}"))
    assert deleted["is_active"] is False

    listed = client.get(CUSTOMERS).json()["data"]
    assert [row["id"] for row in listed] == []

    with_inactive = client.get(CUSTOMERS, params={"include_inactive": True}).json()["data"]
    assert [row["id"] for row in with_inactive] == [created["id"]]

    # The row is still readable by id — soft delete removes it from lists, not from history.
    assert client.get(f"{CUSTOMERS}/{created['id']}").status_code == 200


def test_deleting_twice_is_idempotent(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    created = create_customer(client)

    assert client.delete(f"{CUSTOMERS}/{created['id']}").status_code == 200
    second = client.delete(f"{CUSTOMERS}/{created['id']}")
    assert second.status_code == 200
    assert payload(second)["is_active"] is False


# --------------------------------------------------------------------------- #
# Audit
# --------------------------------------------------------------------------- #


def test_every_write_leaves_an_audit_row_without_contact_details(
    client: TestClient,
    act_as: Callable[..., None],
    org_a: Tenant,
    audit_rows: Callable[..., list],
) -> None:
    act_as(org_a.analyst)
    created = create_customer(client, contact_note="담당 김실장 010-0000-0000")
    client.patch(f"{CUSTOMERS}/{created['id']}", json={"contact_note": "다른 담당자"})
    client.delete(f"{CUSTOMERS}/{created['id']}")

    rows = audit_rows(org_a.organization_id)
    assert [row.action for row in rows] == [
        "customer.create",
        "customer.update",
        "customer.delete",
    ]
    for row in rows:
        assert row.target_type == "customer"
        assert row.target_id == created["id"]
        assert row.actor_user_id == org_a.analyst.user_id
        assert row.actor_kind == "USER"
        assert row.organization_id == org_a.organization_id
        assert row.request_id
        serialized = str(row.detail)
        assert "김실장" not in serialized
        assert "010-0000-0000" not in serialized
        assert "다른 담당자" not in serialized

    assert rows[1].detail["changed_fields"] == ["contact_note"]


# --------------------------------------------------------------------------- #
# Pagination
# --------------------------------------------------------------------------- #


def test_pagination_splits_the_result_and_reports_totals(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    for index in range(5):
        create_customer(client, name=f"고객사 {index}")

    first = client.get(CUSTOMERS, params={"page": 1, "page_size": 2}).json()
    assert len(first["data"]) == 2
    assert first["page_info"] == {
        "page": 1,
        "page_size": 2,
        "total_items": 5,
        "total_pages": 3,
        "has_next": True,
        "has_previous": False,
    }

    last = client.get(CUSTOMERS, params={"page": 3, "page_size": 2}).json()
    assert len(last["data"]) == 1
    assert last["page_info"]["has_next"] is False
    assert last["page_info"]["has_previous"] is True

    past_the_end = client.get(CUSTOMERS, params={"page": 9, "page_size": 2}).json()
    assert past_the_end["data"] == []
    assert past_the_end["page_info"]["total_items"] == 5


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page": -1},
        {"page_size": 0},
        {"page_size": 201},
        {"page_size": -5},
    ],
)
def test_pagination_bounds_are_enforced(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, params: dict[str, int]
) -> None:
    act_as(org_a.analyst)
    response = client.get(CUSTOMERS, params=params)
    assert response.status_code == 422
    assert error_code(response) == "VALIDATION_FAILED"


def test_the_maximum_page_size_is_two_hundred(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    response = client.get(CUSTOMERS, params={"page_size": 200})
    assert response.status_code == 200
    assert response.json()["page_info"]["page_size"] == 200


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"name": ""},
        {"name": "   "},
        {"name": "가" * 201},
        {"name": "정상", "industry": "가" * 121},
        {"name": "정상", "unexpected": "값"},
        {"name": "정상", "is_active": False},
        {"name": "정상", "organization_id": "00000000-0000-0000-0000-000000000000"},
    ],
)
def test_create_rejects_bad_input(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, body: dict[str, object]
) -> None:
    act_as(org_a.analyst)
    response = client.post(CUSTOMERS, json=body)
    assert response.status_code == 422
    assert error_code(response) == "VALIDATION_FAILED"


# --------------------------------------------------------------------------- #
# Tenancy
# --------------------------------------------------------------------------- #


def test_a_list_never_contains_another_organizations_rows(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, org_b: Tenant
) -> None:
    act_as(org_a.analyst)
    mine = create_customer(client, name="A 조직 고객사")
    act_as(org_b.analyst)
    theirs = create_customer(client, name="B 조직 고객사")

    act_as(org_a.analyst)
    listed = client.get(CUSTOMERS).json()["data"]
    assert [row["id"] for row in listed] == [mine["id"]]
    assert theirs["id"] not in {row["id"] for row in listed}


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_another_organizations_customer_is_404(
    client: TestClient,
    act_as: Callable[..., None],
    org_a: Tenant,
    org_b: Tenant,
    method: str,
) -> None:
    act_as(org_a.analyst)
    created = create_customer(client)

    act_as(org_b.analyst)
    url = f"{CUSTOMERS}/{created['id']}"
    response = (
        client.patch(url, json={"name": "탈취"})
        if method == "patch"
        else getattr(client, method)(url)
    )

    assert response.status_code == 404
    assert error_code(response) == "NOT_FOUND"


def test_a_foreign_id_and_an_unknown_id_look_the_same(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, org_b: Tenant
) -> None:
    act_as(org_a.analyst)
    created = create_customer(client)

    act_as(org_b.analyst)
    foreign = client.get(f"{CUSTOMERS}/{created['id']}")
    missing = client.get(f"{CUSTOMERS}/{uuid.uuid4()}")
    assert foreign.json()["error"] == missing.json()["error"]


def test_a_denied_cross_tenant_write_does_not_touch_the_row(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, org_b: Tenant
) -> None:
    act_as(org_a.analyst)
    created = create_customer(client, name="원래 이름")

    act_as(org_b.analyst)
    assert client.delete(f"{CUSTOMERS}/{created['id']}").status_code == 404

    act_as(org_a.analyst)
    assert payload(client.get(f"{CUSTOMERS}/{created['id']}"))["is_active"] is True


# --------------------------------------------------------------------------- #
# Roles
# --------------------------------------------------------------------------- #


def test_sales_viewer_reads(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    created = create_customer(client)

    act_as(org_a.viewer)
    assert client.get(CUSTOMERS).status_code == 200
    assert client.get(f"{CUSTOMERS}/{created['id']}").status_code == 200


def test_sales_viewer_cannot_write(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.analyst)
    created = create_customer(client)

    act_as(org_a.viewer)
    assert client.post(CUSTOMERS, json={"name": "몰래"}).status_code == 403
    assert client.patch(f"{CUSTOMERS}/{created['id']}", json={"name": "몰래"}).status_code == 403
    assert client.delete(f"{CUSTOMERS}/{created['id']}").status_code == 403


def test_a_forbidden_write_reports_permission_denied(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant
) -> None:
    act_as(org_a.viewer)
    response = client.post(CUSTOMERS, json={"name": "몰래"})
    assert error_code(response) == "PERMISSION_DENIED"


def test_permission_is_checked_before_existence(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, org_b: Tenant
) -> None:
    """A viewer must not be able to probe for rows by comparing 403 against 404."""
    act_as(org_a.analyst)
    created = create_customer(client)

    act_as(org_b.viewer)
    foreign = client.delete(f"{CUSTOMERS}/{created['id']}")
    missing = client.delete(f"{CUSTOMERS}/{uuid.uuid4()}")
    assert foreign.status_code == missing.status_code == 403
