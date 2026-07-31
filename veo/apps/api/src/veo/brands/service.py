"""브랜드 식별 — 고객이 **자기가 누구인지** 말하는 자리.

## 왜 이 모듈이 생겼나

`brand_identities` 와 `competitors` 는 처음부터 있었고, 읽는 코드도 많았다. 그런데
**쓰는 코드가 `src/` 전체에 0건**이었다. 즉 고객은 자기 상호를 등록할 방법이 없었고,
등록이 없으면 `brand_target_for` 가 거부하므로 **GEO 관측이 아예 돌지 않는다.**

지침서 0-E 다. 관측·판별·검수·점유율을 전부 만들어 두고, 그 앞단의 한 칸이 비어 있어서
아무것도 못 쓰는 상태였다.

## 우리와 경쟁사를 같은 표에 둔다

같은 테이블, 같은 필드, 같은 판별기. 점유율은 비율이고, 우리 쪽만 주소·전화번호를 채워
두고 경쟁사는 이름만 적어 두면 **경쟁사 언급이 더 자주 검수 보류로 떨어져 분자에서
빠진다.** 산술을 한 글자도 안 고치고 우리 점유율이 오른다.

그래서 이 모듈은 저장만 하지 않고 **비대칭을 말한다**
(`describe_identity_asymmetry_ko`). 경고를 띄우고도 저장은 한다 — 막아 버리면 사람들이
경쟁사를 아예 등록하지 않게 되고, 그러면 점유율 자체가 사라진다.

## 이름은 바뀌어도 식별자는 안 바뀐다

`entity_key` 는 한 번 정하면 그대로 둔다. `entity_mentions` 가 그 값으로 과거 관측을
가리키고 있어서, 바꾸면 지난 측정과 이번 측정이 다른 브랜드처럼 갈라진다.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.db.models.identity import Competitor, Project
from veo.db.models.observation import BrandIdentity
from veo.observations.brand_identity import (
    BrandIdentityRecord,
    describe_identity_asymmetry_ko,
    describe_identity_gaps_ko,
    normalise_phone,
)
from veo.organizations.errors import DuplicateResourceError, ReferenceNotFoundError

_NON_KEY = re.compile(r"[^a-z0-9]+")


class BrandIdentityConflictError(DuplicateResourceError):
    """같은 프로젝트에 같은 식별자가 이미 있다."""


def _entity_key(display_name: str, existing: set[str]) -> str:
    """표시 이름에서 식별자를 만든다 — 한 번 정하면 바뀌지 않는다.

    한글 상호는 그대로 슬러그가 되지 않으므로 안전한 문자만 남기고, 남는 것이 없으면
    무작위 조각을 붙인다. 사람이 읽을 수 있으면 좋지만 **읽히는 것이 목적이 아니다** —
    과거 관측을 가리키는 안정된 값인 것이 목적이다.
    """
    base = _NON_KEY.sub("-", display_name.strip().lower()).strip("-")
    if not base:
        base = f"brand-{uuid.uuid4().hex[:8]}"
    candidate = base
    suffix = 2
    while candidate in existing:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _record(row: BrandIdentity) -> BrandIdentityRecord:
    return BrandIdentityRecord(
        entity_key=row.entity_key,
        display_name=row.display_name,
        is_own_brand=row.competitor_id is None,
        competitor_id=str(row.competitor_id) if row.competitor_id else None,
        aliases=tuple(str(one) for one in row.aliases or ()),
        own_domains=tuple(str(one) for one in row.own_domains or ()),
        address_terms=tuple(str(one) for one in row.address_terms or ()),
        phone_numbers=tuple(str(one) for one in row.phone_numbers or ()),
        distinguishing_terms=tuple(str(one) for one in row.distinguishing_terms or ()),
        name_is_ambiguous=row.name_is_ambiguous,
    )


@dataclass(frozen=True, slots=True)
class BrandIdentityView:
    """저장된 한 건과, **그것으로 측정이 되는지**에 대한 판단."""

    row: BrandIdentity
    record: BrandIdentityRecord

    @property
    def gaps_ko(self) -> list[str]:
        return describe_identity_gaps_ko(self.record)


@dataclass(frozen=True, slots=True)
class ProjectBrands:
    """한 프로젝트의 브랜드 전부 — 우리 하나와 경쟁사들."""

    ours: BrandIdentityView | None
    competitors: tuple[BrandIdentityView, ...]

    @property
    def asymmetry_ko(self) -> list[str]:
        """우리 쪽만 잘 적혀 있을 때의 경고. 점유율이 조용히 틀리는 경로다."""
        if self.ours is None:
            return []
        return describe_identity_asymmetry_ko(
            self.ours.record, [view.record for view in self.competitors]
        )

    @property
    def can_observe(self) -> bool:
        """관측을 돌릴 수 있는가. 우리 브랜드가 없으면 실행기가 거부한다."""
        return self.ours is not None


def _project(session: Session, principal: Principal, project_id: uuid.UUID) -> Project:
    statement = tenant_select(Project, principal).where(Project.id == project_id)
    assert_tenant_scoped(statement, principal.organization_id)
    row = session.scalars(statement).one_or_none()
    if row is None:
        raise ReferenceNotFoundError("프로젝트를 찾을 수 없습니다.")
    return row


def list_brands(
    session: Session, principal: Principal, project_id: uuid.UUID
) -> ProjectBrands:
    _project(session, principal, project_id)
    statement = (
        tenant_select(BrandIdentity, principal)
        .where(BrandIdentity.project_id == project_id)
        .where(BrandIdentity.is_active.is_(True))
        .order_by(BrandIdentity.entity_key)
    )
    assert_tenant_scoped(statement, principal.organization_id)
    rows = list(session.scalars(statement))

    ours = next((row for row in rows if row.competitor_id is None), None)
    return ProjectBrands(
        ours=BrandIdentityView(ours, _record(ours)) if ours is not None else None,
        competitors=tuple(
            BrandIdentityView(row, _record(row))
            for row in rows
            if row.competitor_id is not None
        ),
    )


def declare_brand(
    session: Session,
    principal: Principal,
    project_id: uuid.UUID,
    *,
    display_name: str,
    is_own_brand: bool,
    aliases: list[str],
    own_domains: list[str],
    address_terms: list[str],
    phone_numbers: list[str],
    distinguishing_terms: list[str],
    name_is_ambiguous: bool | None = None,
    homepage_url: str | None = None,
) -> BrandIdentityView:
    """브랜드 하나를 등록한다. 경쟁사면 `competitors` 행도 함께 만든다."""
    _project(session, principal, project_id)

    existing = list(
        session.scalars(
            tenant_select(BrandIdentity, principal).where(
                BrandIdentity.project_id == project_id
            )
        )
    )
    if is_own_brand and any(row.competitor_id is None for row in existing):
        raise BrandIdentityConflictError(
            "자사 브랜드는 프로젝트당 하나입니다. 이미 등록된 상호를 수정하십시오."
        )

    competitor_id: uuid.UUID | None = None
    if not is_own_brand:
        origin = (homepage_url or "").strip() or f"veo://brand/{uuid.uuid4().hex[:12]}"
        duplicate = session.scalars(
            select(Competitor)
            .where(Competitor.project_id == project_id)
            .where(Competitor.origin == origin)
        ).one_or_none()
        if duplicate is not None:
            raise BrandIdentityConflictError(
                f"이미 등록된 비교 대상입니다: {origin}"
            )
        rival = Competitor(
            organization_id=principal.organization_id,
            project_id=project_id,
            origin=origin,
            display_name=display_name,
            brand_aliases={},
            selection_source="CUSTOMER_SPECIFIED",
        )
        session.add(rival)
        session.flush()
        competitor_id = rival.id

    row = BrandIdentity(
        organization_id=principal.organization_id,
        project_id=project_id,
        competitor_id=competitor_id,
        entity_key=_entity_key(display_name, {one.entity_key for one in existing}),
        display_name=display_name.strip(),
        aliases=[one.strip() for one in aliases if one.strip()],
        own_domains=[one.strip().lower() for one in own_domains if one.strip()],
        address_terms=[one.strip() for one in address_terms if one.strip()],
        # 전화번호는 **저장할 때** 정규화한다. 02-1234-5678 과 0212345678 을 한 값으로
        # 두지 않으면 같은 번호가 답변에서 다른 모양으로 나올 때 못 맞춘다.
        phone_numbers=[
            normalised
            for one in phone_numbers
            if (normalised := normalise_phone(one)) is not None
        ],
        distinguishing_terms=[one.strip() for one in distinguishing_terms if one.strip()],
        name_is_ambiguous=name_is_ambiguous,
        is_active=True,
    )
    session.add(row)
    session.flush()
    return BrandIdentityView(row, _record(row))


def update_brand(
    session: Session,
    principal: Principal,
    brand_id: uuid.UUID,
    *,
    display_name: str | None = None,
    aliases: list[str] | None = None,
    own_domains: list[str] | None = None,
    address_terms: list[str] | None = None,
    phone_numbers: list[str] | None = None,
    distinguishing_terms: list[str] | None = None,
    name_is_ambiguous: bool | None = None,
    is_active: bool | None = None,
) -> BrandIdentityView:
    """등록된 브랜드를 고친다. **`entity_key` 는 절대 바뀌지 않는다.**

    `entity_mentions` 가 그 값으로 과거 관측을 가리킨다. 바꾸면 지난 측정과 이번 측정이
    다른 브랜드처럼 갈라지고, 추이는 조용히 끊긴다.
    """
    statement = tenant_select(BrandIdentity, principal).where(BrandIdentity.id == brand_id)
    assert_tenant_scoped(statement, principal.organization_id)
    row = session.scalars(statement).one_or_none()
    if row is None:
        raise ReferenceNotFoundError("등록된 브랜드를 찾을 수 없습니다.")

    if display_name is not None:
        row.display_name = display_name.strip()
    if aliases is not None:
        row.aliases = [one.strip() for one in aliases if one.strip()]
    if own_domains is not None:
        row.own_domains = [one.strip().lower() for one in own_domains if one.strip()]
    if address_terms is not None:
        row.address_terms = [one.strip() for one in address_terms if one.strip()]
    if phone_numbers is not None:
        row.phone_numbers = [
            normalised
            for one in phone_numbers
            if (normalised := normalise_phone(one)) is not None
        ]
    if distinguishing_terms is not None:
        row.distinguishing_terms = [one.strip() for one in distinguishing_terms if one.strip()]
    if name_is_ambiguous is not None:
        row.name_is_ambiguous = name_is_ambiguous
    if is_active is not None:
        row.is_active = is_active

    session.flush()
    return BrandIdentityView(row, _record(row))


__all__ = [
    "BrandIdentityConflictError",
    "BrandIdentityView",
    "ProjectBrands",
    "declare_brand",
    "list_brands",
    "update_brand",
]
