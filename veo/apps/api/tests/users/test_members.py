"""Adding a colleague, giving them a role, and taking it away.

The rules worth stating, because each of them is a way the product could quietly become
unusable or unsafe:

* an administrator never chooses somebody else's password;
* an account with no password cannot be signed into, and does not pretend it can;
* the last administrator cannot be removed, demoted, or switched off;
* nothing here reaches a person in another organization, by any verb, including by id.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from veo.contracts.enums import Role
from veo.db.models.identity import User
from veo.users import service

from .conftest import Tenant


def add(client: TestClient, *, email: str, name: str = "새 직원", role: str = "ANALYST"):  # type: ignore[no-untyped-def]
    return client.post(
        "/api/users", json={"email": email, "display_name": name, "role": role}
    )


# --------------------------------------------------------------------------- #
# Creating a colleague
# --------------------------------------------------------------------------- #


def test_an_administrator_can_add_a_colleague_and_gets_a_link(
    client: TestClient, venom: Tenant, act_as
) -> None:
    act_as(venom.principal)
    response = add(client, email="staff@venom.test")

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["member"]["email"] == "staff@venom.test"
    assert data["member"]["roles"] == ["ANALYST"]
    assert data["invitation"]["invite_url"].startswith("http")
    assert "/invite/" in data["invitation"]["invite_url"]


def test_a_new_colleague_has_no_password_and_cannot_sign_in_yet(
    client: TestClient, venom: Tenant, act_as, db: Session
) -> None:
    """The account exists but is not yet an account anybody can use."""
    act_as(venom.principal)
    data = add(client, email="staff@venom.test").json()["data"]

    assert data["member"]["has_password"] is False
    assert data["member"]["is_active"] is False

    person = db.get(User, uuid.UUID(data["member"]["id"]))
    assert person is not None
    assert person.password_hash is None


def test_the_administrator_cannot_choose_the_colleagues_password(
    client: TestClient, venom: Tenant, act_as
) -> None:
    """Asserted against the schema, not by hoping nobody adds the field.

    If an administrator set the password they would hold a credential belonging to
    somebody else, and every later action by that person would be deniable.
    """
    act_as(venom.principal)
    response = client.post(
        "/api/users",
        json={
            "email": "staff@venom.test",
            "display_name": "새 직원",
            "role": "ANALYST",
            "password": "chosen-by-the-admin",
        },
    )
    assert response.status_code == 422


def test_a_duplicate_address_is_refused(client: TestClient, venom: Tenant, act_as) -> None:
    act_as(venom.principal)
    add(client, email="staff@venom.test")
    again = add(client, email="Staff@Venom.test")
    assert again.status_code == 409


def test_an_address_already_used_in_another_agency_does_not_say_so(
    client: TestClient, venom: Tenant, rival: Tenant, act_as
) -> None:
    """The refusal must not confirm where somebody works."""
    act_as(rival.principal)
    add(client, email="shared@example.test")

    act_as(venom.principal)
    response = add(client, email="shared@example.test")

    assert response.status_code == 409
    assert "경쟁대행사" not in response.text
    assert "rival" not in response.text


# --------------------------------------------------------------------------- #
# Permission
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("role", [Role.ANALYST, Role.DEVELOPER, Role.SALES_VIEWER])
def test_only_an_administrator_may_add_a_colleague(
    client: TestClient, venom: Tenant, act_as, role: Role
) -> None:
    act_as(
        venom.principal.__class__(
            user_id=venom.admin.id,
            organization_id=venom.organization.id,
            roles=(role,),
            session_id=str(uuid.uuid4()),
        )
    )
    assert add(client, email="staff@venom.test").status_code == 403


def test_signing_out_leaves_no_way_in(client: TestClient, venom: Tenant, act_as) -> None:
    act_as(None)
    assert client.get("/api/users").status_code == 401


# --------------------------------------------------------------------------- #
# Cross-tenant isolation
# --------------------------------------------------------------------------- #


def test_a_list_shows_only_this_organizations_people(
    client: TestClient, venom: Tenant, rival: Tenant, act_as
) -> None:
    act_as(rival.principal)
    add(client, email="theirs@rival.test")

    act_as(venom.principal)
    add(client, email="ours@venom.test")
    emails = {row["email"] for row in client.get("/api/users").json()["data"]}

    assert "ours@venom.test" in emails
    assert "theirs@rival.test" not in emails
    assert "admin@rival.test" not in emails


def test_a_person_in_another_organization_cannot_be_touched_by_id(
    client: TestClient, venom: Tenant, rival: Tenant, act_as
) -> None:
    """404 rather than 403 — the id must not be confirmed as real."""
    act_as(rival.principal)
    theirs = add(client, email="theirs@rival.test").json()["data"]["member"]["id"]

    act_as(venom.principal)
    role_change = client.patch(f"/api/users/{theirs}/role", json={"role": "SUPER_ADMIN"})
    deactivate = client.patch(f"/api/users/{theirs}/status", json={"is_active": False})
    assert role_change.status_code == 404
    assert deactivate.status_code == 404
    assert client.post(f"/api/users/{theirs}/invitations").status_code == 404


def test_an_attack_across_organizations_changes_nothing(
    client: TestClient, venom: Tenant, rival: Tenant, act_as, db: Session
) -> None:
    act_as(rival.principal)
    theirs = add(client, email="theirs@rival.test").json()["data"]["member"]["id"]

    act_as(venom.principal)
    client.patch(f"/api/users/{theirs}/status", json={"is_active": False})

    person = db.get(User, uuid.UUID(theirs))
    assert person is not None
    assert person.email == "theirs@rival.test"


# --------------------------------------------------------------------------- #
# The organization cannot lock itself out
# --------------------------------------------------------------------------- #


def test_the_last_administrator_cannot_be_demoted(
    client: TestClient, venom: Tenant, act_as
) -> None:
    act_as(venom.principal)
    response = client.patch(
        f"/api/users/{venom.admin.id}/role", json={"role": "ANALYST"}
    )
    assert response.status_code == 409
    assert "마지막 관리자" in response.json()["error"]["message"]


def test_the_last_administrator_cannot_be_deactivated(
    client: TestClient, venom: Tenant, act_as
) -> None:
    act_as(venom.principal)
    response = client.patch(
        f"/api/users/{venom.admin.id}/status", json={"is_active": False}
    )
    assert response.status_code == 409


def test_an_administrator_can_be_demoted_once_there_is_another_one(
    client: TestClient, venom: Tenant, act_as, db: Session
) -> None:
    act_as(venom.principal)
    second = add(client, email="second@venom.test", role="SUPER_ADMIN").json()["data"]["member"]
    # A second administrator who has not accepted their invitation is inactive, and an
    # inactive administrator is not a way back into the organization.
    assert client.patch(
        f"/api/users/{venom.admin.id}/role", json={"role": "ANALYST"}
    ).status_code == 409

    person = db.get(User, uuid.UUID(second["id"]))
    assert person is not None
    person.is_active = True
    db.flush()

    assert client.patch(
        f"/api/users/{venom.admin.id}/role", json={"role": "ANALYST"}
    ).status_code == 200


def test_an_administrator_cannot_switch_themselves_off(
    client: TestClient, venom: Tenant, act_as, db: Session
) -> None:
    act_as(venom.principal)
    second = add(client, email="second@venom.test", role="SUPER_ADMIN").json()["data"]["member"]
    person = db.get(User, uuid.UUID(second["id"]))
    assert person is not None
    person.is_active = True
    db.flush()

    response = client.patch(
        f"/api/users/{venom.admin.id}/status", json={"is_active": False}
    )
    assert response.status_code == 409
    assert "자기 자신" in response.json()["error"]["message"]


def test_counting_administrators_ignores_deactivated_ones(
    db: Session, venom: Tenant
) -> None:
    assert service.count_administrators(db, venom.principal) == 1
    venom.admin.is_active = False
    db.flush()
    assert service.count_administrators(db, venom.principal) == 0


# --------------------------------------------------------------------------- #
# Leaving
# --------------------------------------------------------------------------- #


def test_deactivating_keeps_the_row_so_the_audit_trail_still_points_somewhere(
    client: TestClient, venom: Tenant, act_as, db: Session
) -> None:
    act_as(venom.principal)
    staff = add(client, email="staff@venom.test").json()["data"]["member"]["id"]

    assert client.patch(
        f"/api/users/{staff}/status", json={"is_active": False}
    ).status_code == 200
    assert db.get(User, uuid.UUID(staff)) is not None


def test_no_response_anywhere_carries_a_password_field(
    client: TestClient, venom: Tenant, act_as
) -> None:
    act_as(venom.principal)
    created = add(client, email="staff@venom.test")
    listed = client.get("/api/users")

    for response in (created, listed):
        body = response.text
        assert "password_hash" not in body
        assert "$argon2" not in body
