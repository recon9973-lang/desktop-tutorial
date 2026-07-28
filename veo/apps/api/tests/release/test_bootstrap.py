"""Creating the first organization and the first person who can sign in.

Found by the release walkthrough, which could not begin: a freshly migrated VEO had no
organizations, no users, and nothing anywhere — API, migration or script — that could
create one. Every route requires a principal, a principal comes from a sign-in, and a
sign-in needs a user that no code path could produce. The product was unusable on the
day it was deployed, and no test noticed because every suite builds its own rows
directly through SQLAlchemy.

So the bootstrap is the one privileged entry point, and it is deliberately a script an
operator runs on the host rather than an HTTP route. A self-serve endpoint that mints an
owner would be reachable by anyone who found it, and "it refuses once the first
organization exists" is a race, not a control.

The properties that matter are about handling a password on a shared machine:

* it is never accepted as a command-line argument, because argv is world-readable in
  ``ps`` and lands in shell history;
* it is never printed, echoed or logged, not even on success;
* a weak or empty one is refused before any row is written.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.auth.passwords import verify_password
from veo.contracts.enums import Role
from veo.db.models.identity import Organization, RoleAssignment, User

from veo.bootstrap import (  # isort: skip
    BootstrapRefused,
    BootstrapResult,
    bootstrap_first_organization,
)

PASSWORD = "a-long-enough-operator-password-2026"


def _org_count(db: Session) -> int:
    return len(list(db.scalars(select(Organization))))


# --------------------------------------------------------------------------- #
# The happy path — one organization, one owner, one role
# --------------------------------------------------------------------------- #


def test_a_fresh_database_gets_an_organization_an_owner_and_a_role(db: Session) -> None:
    result = bootstrap_first_organization(
        db,
        organization_name="베놈",
        organization_slug="venom",
        email="Owner@Example.com",
        display_name="이재훈",
        password=PASSWORD,
    )

    assert isinstance(result, BootstrapResult)

    organization = db.get(Organization, result.organization_id)
    assert organization is not None
    assert organization.name == "베놈"
    assert organization.slug == "venom"
    assert organization.is_active

    person = db.get(User, result.user_id)
    assert person is not None
    assert person.display_name == "이재훈"
    assert person.is_active

    assignment = db.scalars(
        select(RoleAssignment).where(RoleAssignment.user_id == result.user_id)
    ).one()
    assert assignment.role == Role.SUPER_ADMIN
    assert assignment.organization_id == result.organization_id


def test_the_owner_can_actually_sign_in_with_the_password_that_was_set(db: Session) -> None:
    """The point of the whole exercise. A hash that does not verify is a locked door."""
    result = bootstrap_first_organization(
        db,
        organization_name="베놈",
        organization_slug="venom",
        email="owner@example.com",
        display_name="이재훈",
        password=PASSWORD,
    )

    person = db.get(User, result.user_id)
    assert person is not None
    assert verify_password(person.password_hash, PASSWORD)
    assert not verify_password(person.password_hash, PASSWORD + "x")


def test_the_email_is_stored_normalised_so_case_cannot_split_one_account_in_two(
    db: Session,
) -> None:
    result = bootstrap_first_organization(
        db,
        organization_name="베놈",
        organization_slug="venom",
        email="  Owner@Example.COM  ",
        display_name="이재훈",
        password=PASSWORD,
    )
    person = db.get(User, result.user_id)
    assert person is not None
    assert person.email == "owner@example.com"


# --------------------------------------------------------------------------- #
# The password never becomes readable
# --------------------------------------------------------------------------- #


def test_the_plaintext_password_is_not_stored(db: Session) -> None:
    result = bootstrap_first_organization(
        db,
        organization_name="베놈",
        organization_slug="venom",
        email="owner@example.com",
        display_name="이재훈",
        password=PASSWORD,
    )
    person = db.get(User, result.user_id)
    assert person is not None
    assert person.password_hash is not None
    assert PASSWORD not in person.password_hash
    assert person.password_hash.startswith("$argon2")


def test_the_result_carries_no_password_anywhere_in_it(db: Session) -> None:
    """Whatever the caller prints, it must not be able to print the password."""
    result = bootstrap_first_organization(
        db,
        organization_name="베놈",
        organization_slug="venom",
        email="owner@example.com",
        display_name="이재훈",
        password=PASSWORD,
    )
    assert PASSWORD not in repr(result)
    assert PASSWORD not in str(result)


def test_the_script_never_takes_a_password_on_the_command_line() -> None:
    """``ps`` shows argv to every user on the box, and the shell writes it to history.

    Asserted against the source because the mistake is a single plausible-looking
    ``add_argument("--password")`` that no behavioural test would catch.
    """
    source = (
        Path(__file__).resolve().parents[2] / "scripts" / "bootstrap.py"
    ).read_text(encoding="utf-8")

    assert "--password" not in source, (
        "a password passed as an argument is visible in ps and in shell history; "
        "read it from the environment or prompt for it instead"
    )


# --------------------------------------------------------------------------- #
# Refusals — before anything is written
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("organization_name", "  "),
        ("organization_slug", ""),
        ("email", "not-an-email"),
        ("display_name", " "),
        ("password", "short"),
        ("password", ""),
    ],
)
def test_bad_input_is_refused_and_writes_nothing(
    db: Session, field: str, value: str
) -> None:
    payload: dict[str, str] = {
        "organization_name": "베놈",
        "organization_slug": "venom",
        "email": "owner@example.com",
        "display_name": "이재훈",
        "password": PASSWORD,
    }
    payload[field] = value

    before = _org_count(db)
    with pytest.raises(BootstrapRefused):
        bootstrap_first_organization(db, **payload)  # type: ignore[arg-type]
    assert _org_count(db) == before, "a refused bootstrap must leave no partial rows"


def test_a_second_bootstrap_is_refused_once_an_organization_exists(db: Session) -> None:
    """The privileged path closes itself after the first use.

    Not a security boundary on its own — the script needs database credentials to run at
    all — but it stops an operator from silently creating a second owner on a live system
    while believing they are setting up a new one.
    """
    bootstrap_first_organization(
        db,
        organization_name="베놈",
        organization_slug="venom",
        email="owner@example.com",
        display_name="이재훈",
        password=PASSWORD,
    )

    with pytest.raises(BootstrapRefused) as caught:
        bootstrap_first_organization(
            db,
            organization_name="다른곳",
            organization_slug="other",
            email="second@example.com",
            display_name="다른 사람",
            password=PASSWORD,
        )
    assert "이미" in str(caught.value)


def test_a_duplicate_email_is_refused_rather_than_raising_a_database_error(
    db: Session,
) -> None:
    db.add(
        User(
            id=uuid.uuid4(),
            email="owner@example.com",
            display_name="기존 사용자",
            password_hash=None,
            is_active=True,
        )
    )
    db.flush()

    with pytest.raises(BootstrapRefused) as caught:
        bootstrap_first_organization(
            db,
            organization_name="베놈",
            organization_slug="venom",
            email="Owner@example.com",
            display_name="이재훈",
            password=PASSWORD,
        )
    assert "owner@example.com" in str(caught.value)
