"""Who is making a request, and what they are allowed to do."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from functools import cached_property
from typing import Final

from veo.authz.errors import PermissionDeniedError
from veo.authz.permissions import Permission, permissions_for
from veo.contracts.enums import Role


@dataclass(frozen=True)
class Principal:
    """An authenticated caller, bound to exactly one organization.

    A principal is per-organization by construction. A user who belongs to two
    organizations authenticates into one of them and gets one principal; there is no
    ambient "all my organizations" identity that a handler could accidentally trust.
    """

    user_id: uuid.UUID
    organization_id: uuid.UUID
    roles: frozenset[Role]
    session_id: str
    is_service_account: bool = False
    display_name: str = field(default="", compare=False)

    @cached_property
    def permissions(self) -> frozenset[Permission]:
        return permissions_for(self.roles)

    def has(self, permission: Permission) -> bool:
        return permission in self.permissions

    def has_any(self, *permissions: Permission) -> bool:
        return any(p in self.permissions for p in permissions)

    def require(self, permission: Permission) -> None:
        """Raise unless the caller holds ``permission``.

        The message names the missing permission — useful to a developer reading logs —
        but never the user or organization id, so an error can be surfaced without
        confirming anything about the caller's tenant.
        """
        if permission not in self.permissions:
            raise PermissionDeniedError(permission)

    def require_all(self, *permissions: Permission) -> None:
        for permission in permissions:
            self.require(permission)

    def require_any(self, *permissions: Permission) -> None:
        if not self.has_any(*permissions):
            raise PermissionDeniedError(*permissions)

    def in_organization(self, organization_id: uuid.UUID) -> bool:
        return self.organization_id == organization_id


#: 예약 실행 주체의 자리표시 식별자. **DB 에 기록되지 않는다** — 저장 경로는
#: ``is_service_account`` 를 보고 실행자 칸을 비운다(스키마 주석: "예약 실행이면 NULL").
SYSTEM_USER_ID: Final = uuid.UUID(int=0)


def system_principal(organization_id: uuid.UUID, *, session_id: str) -> Principal:
    """예약 실행의 주체 — 사람이 아니다.

    ``user_id`` 는 자리표시일 뿐이며 users 테이블에 없다. 그래서 이 주체로 저장하는
    경로는 반드시 ``is_service_account`` 를 확인해 실행자 기록을 비워야 한다 —
    그대로 쓰면 FK 위반이고, 어찌 통과돼도 거짓 기록이다. 역할은 분석가와 같다:
    스케줄 실행이 사람보다 더 많은 것을 할 이유가 없다.
    """
    return Principal(
        user_id=SYSTEM_USER_ID,
        organization_id=organization_id,
        roles=frozenset({Role.ANALYST}),
        session_id=session_id,
        is_service_account=True,
    )
