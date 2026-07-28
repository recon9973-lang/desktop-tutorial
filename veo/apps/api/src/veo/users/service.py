"""Adding, listing and changing the people in one organization.

Two rules run through every function here.

**Tenancy is structural.** Every read goes through ``tenant_select`` so a colleague in
another agency cannot be found, named, or altered — not even by id. A user row itself is
global (one address, one account), so membership is what is scoped: a person is *in* this
organization only if a ``RoleAssignment`` says so, and every query joins through it.

**Nobody may lock the organization out of itself.** The last remaining administrator
cannot be demoted, deactivated, or stripped of their role. Without that rule the product
has a one-click path to a state only a database console can undo, and the person who
clicks it will be someone tidying up an account they thought was unused.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import final

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from veo.auth.hashing import looks_like_email, normalize_email
from veo.authz import Principal
from veo.authz.permissions import ROLE_PERMISSIONS
from veo.authz.tenancy import tenant_select
from veo.contracts.enums import Role
from veo.db.models.identity import RoleAssignment, User

__all__ = [
    "MemberRecord",
    "MemberStatus",
    "UserServiceError",
    "add_member",
    "change_role",
    "count_administrators",
    "list_members",
    "load_member",
    "set_active",
]


class MemberStatus(StrEnum):
    """Where a colleague is in their life with the product.

    ``is_active`` alone could not express this, and conflating the two states hid a real
    bug: a colleague who had just been invited was indistinguishable from one who had
    left, so adding somebody made them disappear from the list until they accepted. The
    administrator's reasonable conclusion would be that it had not worked.
    """

    #: Invited, has never set a password, cannot sign in yet.
    PENDING = "PENDING"
    #: Has a password and may sign in.
    ACTIVE = "ACTIVE"
    #: Switched off by an administrator. Kept, not deleted, so the audit trail still
    #: points at a real person.
    DEACTIVATED = "DEACTIVATED"


def status_of(person: User) -> MemberStatus:
    if person.password_hash is None:
        # No password has ever been set. Deactivating such an account is possible, but it
        # is still fundamentally somebody who never arrived.
        return MemberStatus.PENDING
    return MemberStatus.ACTIVE if person.is_active else MemberStatus.DEACTIVATED


class UserServiceError(Exception):
    """A refusal the router turns into a 4xx with this message."""


@final
@dataclass(frozen=True, slots=True)
class MemberRecord:
    """One person as this organization sees them."""

    user: User
    roles: tuple[str, ...]

    @property
    def status(self) -> MemberStatus:
        return status_of(self.user)


def _membership(principal: Principal) -> Select[tuple[RoleAssignment]]:
    return tenant_select(RoleAssignment, principal)


def count_administrators(db: Session, principal: Principal) -> int:
    """How many people can still administer this organization, counting active ones only.

    A deactivated administrator cannot sign in, so they do not count as a way back in.
    """
    statement = (
        _membership(principal)
        .join(User, User.id == RoleAssignment.user_id)
        .where(RoleAssignment.role == Role.SUPER_ADMIN.value, User.is_active.is_(True))
        .with_only_columns(func.count(func.distinct(RoleAssignment.user_id)))
    )
    return int(db.scalar(statement) or 0)


def list_members(
    db: Session, principal: Principal, *, include_deactivated: bool = False
) -> list[MemberRecord]:
    """Everyone in this organization.

    Pending colleagues are included by default — they are members, they simply have not
    finished setting up. Only people an administrator has switched off are hidden, and
    only until asked for.
    """
    statement = _membership(principal).join(User, User.id == RoleAssignment.user_id)
    if not include_deactivated:
        # ``password_hash IS NULL`` is the pending case, which stays visible.
        statement = statement.where(
            (User.is_active.is_(True)) | (User.password_hash.is_(None))
        )

    by_user: dict[uuid.UUID, MemberRecord] = {}
    for assignment in db.scalars(statement.order_by(RoleAssignment.created_at)):
        person = db.get(User, assignment.user_id)
        if person is None:  # pragma: no cover - foreign key makes this unreachable
            continue
        existing = by_user.get(person.id)
        roles = (*existing.roles, assignment.role) if existing else (assignment.role,)
        by_user[person.id] = MemberRecord(user=person, roles=roles)
    return list(by_user.values())


def load_member(
    db: Session, principal: Principal, user_id: uuid.UUID
) -> MemberRecord | None:
    """One member, or ``None`` if they are not in *this* organization."""
    assignments = list(
        db.scalars(
            _membership(principal).where(
                RoleAssignment.user_id == user_id
            )
        )
    )
    if not assignments:
        return None
    person = db.get(User, user_id)
    if person is None:  # pragma: no cover
        return None
    return MemberRecord(user=person, roles=tuple(a.role for a in assignments))


def add_member(
    db: Session,
    principal: Principal,
    *,
    email: str,
    display_name: str,
    role: Role,
) -> MemberRecord:
    """Create the account and its role. The password is set later, by its owner.

    The account is created **inactive**: it becomes usable only when the invitation is
    accepted. An active account with no password is a row that looks like a member,
    appears in lists, and cannot be signed into — a permanent puzzle for whoever inherits
    the organization.
    """
    address = normalize_email(email)
    name = display_name.strip()
    if not name:
        raise UserServiceError("이름을 입력해 주세요.")
    if not looks_like_email(address):
        raise UserServiceError("이메일 형식이 올바르지 않습니다.")
    if role not in ROLE_PERMISSIONS:
        raise UserServiceError(f"알 수 없는 역할입니다: {role}")

    existing = db.scalars(select(User).where(User.email == address)).one_or_none()
    if existing is not None:
        # The address may belong to this organization or to another one, and the message
        # is the same either way. "That address is in another agency" would confirm a
        # person's employer to anyone who can type an email address.
        raise UserServiceError(f"이미 사용 중인 이메일입니다: {address}")

    person = User(
        id=uuid.uuid4(),
        email=address,
        display_name=name,
        password_hash=None,
        is_active=False,
    )
    db.add(person)
    db.flush()

    db.add(
        RoleAssignment(
            id=uuid.uuid4(),
            organization_id=principal.organization_id,
            user_id=person.id,
            role=role.value,
            granted_by=principal.user_id,
        )
    )
    db.flush()
    return MemberRecord(user=person, roles=(role.value,))


def change_role(
    db: Session, principal: Principal, *, user_id: uuid.UUID, role: Role
) -> MemberRecord:
    member = load_member(db, principal, user_id)
    if member is None:
        raise UserServiceError("구성원을 찾을 수 없습니다.")
    if role not in ROLE_PERMISSIONS:
        raise UserServiceError(f"알 수 없는 역할입니다: {role}")

    losing_admin = (
        Role.SUPER_ADMIN.value in member.roles and role is not Role.SUPER_ADMIN
    )
    if losing_admin and count_administrators(db, principal) <= 1:
        raise UserServiceError(
            "마지막 관리자의 역할은 바꿀 수 없습니다. "
            "먼저 다른 사람을 관리자로 지정한 뒤에 변경하십시오."
        )

    for assignment in db.scalars(
        _membership(principal).where(RoleAssignment.user_id == user_id)
    ):
        db.delete(assignment)
    db.flush()

    db.add(
        RoleAssignment(
            id=uuid.uuid4(),
            organization_id=principal.organization_id,
            user_id=user_id,
            role=role.value,
            granted_by=principal.user_id,
        )
    )
    db.flush()
    return MemberRecord(user=member.user, roles=(role.value,))


def set_active(
    db: Session, principal: Principal, *, user_id: uuid.UUID, is_active: bool
) -> MemberRecord:
    """Switch an account on or off. Deactivating is how somebody leaves.

    Rows are not deleted: an audit trail that points at a vanished user is not a trail.
    """
    member = load_member(db, principal, user_id)
    if member is None:
        raise UserServiceError("구성원을 찾을 수 없습니다.")

    if not is_active:
        if user_id == principal.user_id:
            raise UserServiceError("자기 자신을 비활성화할 수 없습니다.")
        if (
            Role.SUPER_ADMIN.value in member.roles
            and count_administrators(db, principal) <= 1
        ):
            raise UserServiceError(
                "마지막 관리자를 비활성화할 수 없습니다. "
                "먼저 다른 사람을 관리자로 지정하십시오."
            )

    member.user.is_active = is_active
    db.flush()
    return member
