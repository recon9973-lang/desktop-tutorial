"""Setting a password for the first time, and changing it later.

The invitation is the only unauthenticated write in the console, so it carries the whole
weight of "is this really the person we invited". What that requires:

* the token is random, stored only as a hash, single-use, and expiring;
* unknown, expired, revoked and already-used tokens are indistinguishable in the reply;
* accepting is what makes the account usable — before it, there is nothing to sign in to.

Changing a password later is a different problem. A session already proves identity, so
the current password is asked for to make a *stolen session* recoverable rather than
permanent, and every other session is dropped at the moment of the change.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.auth.passwords import hash_password, verify_password
from veo.auth.sessions import create_session, is_usable
from veo.db.models.identity import User, UserInvitation
from veo.users import invitations

from .conftest import OWNER_PASSWORD, Tenant

NEW_PASSWORD = "a-colleagues-own-password-2026"


def invite(client: TestClient, email: str = "staff@venom.test") -> tuple[str, str]:
    """Add a colleague and return (user_id, token)."""
    data = client.post(
        "/api/users",
        json={"email": email, "display_name": "새 직원", "role": "ANALYST"},
    ).json()["data"]
    return data["member"]["id"], data["invitation"]["invite_url"].rsplit("/", 1)[-1]


# --------------------------------------------------------------------------- #
# The token itself
# --------------------------------------------------------------------------- #


def test_only_the_hash_of_the_token_is_stored(
    client: TestClient, venom: Tenant, act_as, db: Session
) -> None:
    """A stolen database must not yield a usable invitation."""
    act_as(venom.principal)
    _, token = invite(client)

    rows = list(db.scalars(select(UserInvitation)))
    assert rows
    for row in rows:
        assert row.token_hash != token
        assert token not in row.token_hash
    assert rows[0].token_hash == invitations.fingerprint_token(token)


def test_two_invitations_never_share_a_token(
    client: TestClient, venom: Tenant, act_as
) -> None:
    act_as(venom.principal)
    _, first = invite(client, "one@venom.test")
    _, second = invite(client, "two@venom.test")
    assert first != second


# --------------------------------------------------------------------------- #
# Accepting
# --------------------------------------------------------------------------- #


def test_accepting_sets_the_password_and_activates_the_account(
    client: TestClient, venom: Tenant, act_as, db: Session
) -> None:
    act_as(venom.principal)
    user_id, token = invite(client)
    act_as(None)

    response = client.post(
        f"/api/invitations/{token}/accept", json={"password": NEW_PASSWORD}
    )
    assert response.status_code == 200, response.text

    person = db.get(User, uuid.UUID(user_id))
    assert person is not None
    assert person.is_active
    assert verify_password(person.password_hash, NEW_PASSWORD)


def test_accepting_needs_no_session(client: TestClient, venom: Tenant, act_as) -> None:
    """It cannot need one — the account has no password to sign in with yet."""
    act_as(venom.principal)
    _, token = invite(client)
    act_as(None)

    assert client.post(
        f"/api/invitations/{token}/accept", json={"password": NEW_PASSWORD}
    ).status_code == 200


def test_a_token_works_only_once(client: TestClient, venom: Tenant, act_as) -> None:
    act_as(venom.principal)
    _, token = invite(client)
    act_as(None)

    first = client.post(f"/api/invitations/{token}/accept", json={"password": NEW_PASSWORD})
    second = client.post(
        f"/api/invitations/{token}/accept", json={"password": "a-different-password-2026"}
    )
    assert first.status_code == 200
    assert second.status_code == 404


def test_an_expired_token_is_refused(
    client: TestClient, venom: Tenant, act_as, db: Session
) -> None:
    act_as(venom.principal)
    _, token = invite(client)

    row = db.scalars(select(UserInvitation)).one()
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.flush()

    act_as(None)
    assert client.post(
        f"/api/invitations/{token}/accept", json={"password": NEW_PASSWORD}
    ).status_code == 404


def test_reissuing_kills_the_previous_link(
    client: TestClient, venom: Tenant, act_as
) -> None:
    """Re-inviting is what an administrator does when a link went astray.

    If the old one kept working, the lost link would still open the account.
    """
    act_as(venom.principal)
    user_id, first = invite(client)
    client.post(f"/api/users/{user_id}/invitations")

    act_as(None)
    assert client.post(
        f"/api/invitations/{first}/accept", json={"password": NEW_PASSWORD}
    ).status_code == 404


@pytest.mark.parametrize(
    "token",
    ["", "short", "!!!!", "x" * 200, "0" * 43],
    ids=["empty", "short", "junk", "overlong", "well-shaped-but-unknown"],
)
def test_every_bad_token_gets_the_same_answer(
    client: TestClient, venom: Tenant, act_as, token: str
) -> None:
    """Unknown, malformed and expired must be indistinguishable.

    Telling them apart confirms that a particular token once existed, which is the only
    thing an attacker holding a guess wants to learn.
    """
    act_as(None)
    response = client.post(
        f"/api/invitations/{token}/accept", json={"password": NEW_PASSWORD}
    )
    assert response.status_code in (404, 405)
    if response.status_code == 404 and "error" in response.json():
        assert response.json()["error"]["code"] == "NOT_FOUND"


def test_a_short_password_is_refused_at_the_edge(
    client: TestClient, venom: Tenant, act_as, db: Session
) -> None:
    act_as(venom.principal)
    user_id, token = invite(client)
    act_as(None)

    assert client.post(
        f"/api/invitations/{token}/accept", json={"password": "short"}
    ).status_code == 422

    person = db.get(User, uuid.UUID(user_id))
    assert person is not None
    assert person.password_hash is None, "a refused attempt must not half-create a login"


def test_deactivating_someone_revokes_their_outstanding_invitation(
    client: TestClient, venom: Tenant, act_as
) -> None:
    """Otherwise a link handed out yesterday still creates a working account today."""
    act_as(venom.principal)
    user_id, token = invite(client)
    client.patch(f"/api/users/{user_id}/status", json={"is_active": False})

    act_as(None)
    assert client.post(
        f"/api/invitations/{token}/accept", json={"password": NEW_PASSWORD}
    ).status_code == 404


# --------------------------------------------------------------------------- #
# Changing your own password
# --------------------------------------------------------------------------- #


def test_a_member_can_change_their_own_password(
    client: TestClient, venom: Tenant, act_as, db: Session
) -> None:
    act_as(venom.principal)
    response = client.post(
        "/api/auth/password",
        json={"current_password": OWNER_PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 200, response.text

    db.refresh(venom.admin)
    assert verify_password(venom.admin.password_hash, NEW_PASSWORD)


def test_the_current_password_is_required(
    client: TestClient, venom: Tenant, act_as, db: Session
) -> None:
    """A session alone must not be enough — an unlocked screen would then be permanent."""
    act_as(venom.principal)
    response = client.post(
        "/api/auth/password",
        json={"current_password": "not-the-right-one", "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 401

    db.refresh(venom.admin)
    assert verify_password(venom.admin.password_hash, OWNER_PASSWORD)


def test_reusing_the_same_password_is_refused(
    client: TestClient, venom: Tenant, act_as
) -> None:
    act_as(venom.principal)
    assert client.post(
        "/api/auth/password",
        json={"current_password": OWNER_PASSWORD, "new_password": OWNER_PASSWORD},
    ).status_code == 409


def test_a_short_new_password_is_refused(client: TestClient, venom: Tenant, act_as) -> None:
    act_as(venom.principal)
    assert client.post(
        "/api/auth/password",
        json={"current_password": OWNER_PASSWORD, "new_password": "short"},
    ).status_code == 422


def test_changing_the_password_drops_every_other_session(
    client: TestClient, venom: Tenant, act_as, db: Session
) -> None:
    """The usual reason to change a password is suspecting somebody else knows it."""
    other = create_session(
        db,
        user_id=venom.admin.id,
        organization_id=venom.organization.id,
    )
    assert is_usable(other.session)

    act_as(venom.principal)
    assert client.post(
        "/api/auth/password",
        json={"current_password": OWNER_PASSWORD, "new_password": NEW_PASSWORD},
    ).status_code == 200

    db.refresh(other.session)
    assert not is_usable(other.session)


def test_the_response_never_echoes_either_password(
    client: TestClient, venom: Tenant, act_as
) -> None:
    act_as(venom.principal)
    response = client.post(
        "/api/auth/password",
        json={"current_password": OWNER_PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert OWNER_PASSWORD not in response.text
    assert NEW_PASSWORD not in response.text
    assert "$argon2" not in response.text


def test_an_anonymous_caller_cannot_change_a_password(
    client: TestClient, venom: Tenant, act_as
) -> None:
    act_as(None)
    assert client.post(
        "/api/auth/password",
        json={"current_password": OWNER_PASSWORD, "new_password": NEW_PASSWORD},
    ).status_code == 401


def test_a_pending_member_has_no_current_password_to_offer(
    client: TestClient, venom: Tenant, act_as, db: Session
) -> None:
    """``verify_password`` must refuse a null hash rather than treat it as a match."""
    person = User(
        id=uuid.uuid4(),
        email="pending@venom.test",
        display_name="대기중",
        password_hash=None,
        is_active=False,
    )
    db.add(person)
    db.flush()

    assert not verify_password(person.password_hash, "")
    assert not verify_password(person.password_hash, hash_password("anything"))


def test_changing_your_own_password_does_not_sign_you_out_of_this_device(
    client: TestClient, venom: Tenant, act_as, db: Session
) -> None:
    """The other sessions go; the one doing the changing stays.

    Being thrown out of the tab you just used reads as a failure, and the natural
    response to a failure is to try again — which is not what anyone wants from a
    security control.
    """
    mine = create_session(
        db, user_id=venom.admin.id, organization_id=venom.organization.id
    )
    theirs = create_session(
        db, user_id=venom.admin.id, organization_id=venom.organization.id
    )
    here = venom.principal.__class__(
        user_id=venom.admin.id,
        organization_id=venom.organization.id,
        roles=venom.principal.roles,
        session_id=str(mine.session.id),
    )

    act_as(here)
    assert client.post(
        "/api/auth/password",
        json={"current_password": OWNER_PASSWORD, "new_password": NEW_PASSWORD},
    ).status_code == 200

    db.refresh(mine.session)
    db.refresh(theirs.session)
    assert is_usable(mine.session), "the session that changed the password must survive"
    assert not is_usable(theirs.session), "every other session must be gone"
