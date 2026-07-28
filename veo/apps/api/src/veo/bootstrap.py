"""Creating the first organization and the first person who can sign in.

Every route in VEO requires a principal, a principal comes from a sign-in, and a sign-in
requires a user row. Until this module existed there was nothing — no endpoint, no
migration, no script — that could create one, so a freshly deployed VEO could not be
logged into at all. The release walkthrough could not take its first step, which is how
it was found; no test had noticed, because every suite builds its rows directly through
SQLAlchemy and never asks how a real deployment would get them.

**Why a script and not an endpoint.** A self-serve route that mints an owner is reachable
by anyone who finds it, and guarding it with "it refuses once an organization exists"
turns the whole security of a deployment into a race against the first stranger to hit
it. Running this requires database credentials and shell access on the host — which is
the authority the action actually needs.

**The owner is a SUPER_ADMIN**, because someone has to be able to grant every other role
and there is nobody yet to grant it to them. That is a real concentration of power and
the reason this is a one-shot: once an organization exists, the door closes.

Refusals happen before anything is written. A partially-created organization — a row with
no owner, or an owner with no role — is worse than no organization, because it looks
finished.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Final, final

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from veo.auth.hashing import looks_like_email, normalize_email
from veo.auth.passwords import PasswordPolicyError, hash_password
from veo.contracts.enums import Role
from veo.db.models.identity import Organization, RoleAssignment, User

__all__ = [
    "MIN_BOOTSTRAP_PASSWORD_LENGTH",
    "BootstrapRefused",
    "BootstrapResult",
    "bootstrap_first_organization",
]

#: Deliberately stricter than :data:`veo.auth.passwords.MIN_PASSWORD_LENGTH`, which is
#: permissive because it governs *existing* credentials and must not lock anyone out of
#: an account they already have. This one governs the single most powerful account in a
#: deployment, created once, by an operator, with no rate limit in front of it.
MIN_BOOTSTRAP_PASSWORD_LENGTH: Final = 12

_SLUG_SHAPE = re.compile(r"\A[a-z0-9][a-z0-9-]{0,62}[a-z0-9]\Z")


class BootstrapRefused(Exception):
    """The bootstrap will not proceed, and nothing has been written."""


@final
@dataclass(frozen=True, slots=True)
class BootstrapResult:
    """What was created. Carries no secret, so a caller cannot print one by accident."""

    organization_id: uuid.UUID
    organization_slug: str
    user_id: uuid.UUID
    email: str
    role: str


def bootstrap_first_organization(
    db: Session,
    *,
    organization_name: str,
    organization_slug: str,
    email: str,
    display_name: str,
    password: str,
) -> BootstrapResult:
    """Create the first organization, its owner, and the owner's role.

    Raises :class:`BootstrapRefused` — before writing anything — if the input is unusable,
    if an organization already exists, or if the address is already taken.
    """
    name = organization_name.strip()
    slug = organization_slug.strip().lower()
    person_name = display_name.strip()
    address = normalize_email(email)

    if not name:
        raise BootstrapRefused("조직 이름이 비어 있습니다.")
    if not _SLUG_SHAPE.fullmatch(slug):
        raise BootstrapRefused(
            f"조직 식별자('{organization_slug}')는 영소문자·숫자·하이픈만 쓸 수 있고 "
            "하이픈으로 시작하거나 끝날 수 없습니다."
        )
    if not person_name:
        raise BootstrapRefused("사용자 이름이 비어 있습니다.")
    if not looks_like_email(address):
        raise BootstrapRefused(f"이메일 형식이 올바르지 않습니다: {email!r}")
    if len(password) < MIN_BOOTSTRAP_PASSWORD_LENGTH:
        # The length is named, the password is not — an error message is written to a
        # terminal and often into a ticket.
        raise BootstrapRefused(
            f"비밀번호는 최소 {MIN_BOOTSTRAP_PASSWORD_LENGTH}자 이상이어야 합니다. "
            "이 계정은 모든 권한을 가지며 로그인 시도 제한 뒤에 있지 않습니다."
        )

    if db.scalar(select(exists().where(Organization.id.isnot(None)))):
        raise BootstrapRefused(
            "이미 조직이 존재합니다. 최초 설정은 한 번만 실행할 수 있습니다. "
            "구성원을 추가하려면 관리자 계정으로 로그인해 사용자 관리를 이용하십시오."
        )

    if db.scalar(select(exists().where(User.email == address))):
        raise BootstrapRefused(f"이미 등록된 이메일입니다: {address}")

    try:
        password_hash = hash_password(password)
    except PasswordPolicyError as exc:
        raise BootstrapRefused(str(exc)) from exc

    organization = Organization(
        id=uuid.uuid4(), slug=slug, name=name, is_active=True, settings={}
    )
    owner = User(
        id=uuid.uuid4(),
        email=address,
        display_name=person_name,
        password_hash=password_hash,
        is_active=True,
    )
    # Flushed in two steps rather than one. The role assignment carries foreign keys to
    # both rows above, and leaving the ordering to the unit of work is a bet on how it
    # sorts mappers — a bet that loses here. Both flushes are inside the caller's
    # transaction, so a failure on the second still rolls the first back.
    db.add_all([organization, owner])
    db.flush()

    db.add(
        RoleAssignment(
            id=uuid.uuid4(),
            organization_id=organization.id,
            user_id=owner.id,
            role=Role.SUPER_ADMIN.value,
            granted_by=None,
        )
    )
    db.flush()

    return BootstrapResult(
        organization_id=organization.id,
        organization_slug=organization.slug,
        user_id=owner.id,
        email=owner.email,
        role=Role.SUPER_ADMIN.value,
    )
