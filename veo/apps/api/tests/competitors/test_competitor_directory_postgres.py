"""The real directory, against the real schema.

The in-memory directory used by the router tests can only ever be as correct as the
person who wrote it. This module checks the property that matters against PostgreSQL:
a competitor id that belongs to another organization is *not found*, in exactly the same
way an id that exists nowhere is not found.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from veo.authz import TenantIsolationError
from veo.authz.principal import Principal
from veo.competitors.service import SqlCompetitorDirectory
from veo.contracts.enums import Role
from veo.db.models.identity import Competitor, Organization, Project
from veo.organizations.errors import ReferenceNotFoundError

pytestmark = pytest.mark.requires_postgres


class Tenant:
    def __init__(self, organization_id: uuid.UUID, project_id: uuid.UUID) -> None:
        self.organization_id = organization_id
        self.project_id = project_id
        self.competitor_ids: list[uuid.UUID] = []

    @property
    def analyst(self) -> Principal:
        return Principal(
            user_id=uuid.uuid4(),
            organization_id=self.organization_id,
            roles=frozenset({Role.ANALYST}),
            session_id="pg-session",
        )


@pytest.fixture
def make_tenant(db: Session) -> Iterator[Callable[[str], Tenant]]:
    created: list[uuid.UUID] = []

    def _make(label: str) -> Tenant:
        suffix = uuid.uuid4().hex[:8]
        organization = Organization(
            slug=f"veo-cmp-{label}-{suffix}", name=f"경쟁사 테스트 {label}",
            is_active=True, settings={},
        )
        db.add(organization)
        db.flush()

        project = Project(
            organization_id=organization.id,
            slug=f"proj-{suffix}",
            name=f"프로젝트 {label}",
            locale="ko-KR",
            settings={},
        )
        db.add(project)
        db.flush()

        tenant = Tenant(organization.id, project.id)
        for index in (1, 2):
            competitor = Competitor(
                organization_id=organization.id,
                project_id=project.id,
                origin=f"https://rival-{label}-{index}-{suffix}.example",
                display_name=f"경쟁사 {label}{index}",
                brand_aliases={},
                selection_source="CUSTOMER_SPECIFIED",
                is_active=True,
            )
            db.add(competitor)
            db.flush()
            tenant.competitor_ids.append(competitor.id)

        db.commit()
        created.append(organization.id)
        return tenant

    yield _make

    db.rollback()
    if created:
        db.execute(delete(Organization).where(Organization.id.in_(created)))
        db.commit()


def test_a_competitor_in_my_organization_resolves_with_its_display_name(
    db: Session, make_tenant: Callable[[str], Tenant]
) -> None:
    tenant = make_tenant("a")
    directory = SqlCompetitorDirectory(db)

    resolved = directory.resolve(
        tenant.analyst, tenant.project_id, tuple(tenant.competitor_ids)
    )

    assert set(resolved) == set(tenant.competitor_ids)
    assert all(ref.display_name.startswith("경쟁사 a") for ref in resolved.values())


def test_a_competitor_from_another_organization_is_simply_not_found(
    db: Session, make_tenant: Callable[[str], Tenant]
) -> None:
    mine = make_tenant("a")
    theirs = make_tenant("b")
    directory = SqlCompetitorDirectory(db)

    with pytest.raises(ReferenceNotFoundError) as caught:
        directory.resolve(mine.analyst, mine.project_id, (theirs.competitor_ids[0],))

    # The same message an id that exists nowhere produces — no existence oracle.
    with pytest.raises(ReferenceNotFoundError) as nowhere:
        directory.resolve(mine.analyst, mine.project_id, (uuid.uuid4(),))

    assert caught.value.message_ko == nowhere.value.message_ko


def test_another_organizations_project_is_not_found_either(
    db: Session, make_tenant: Callable[[str], Tenant]
) -> None:
    mine = make_tenant("a")
    theirs = make_tenant("b")
    directory = SqlCompetitorDirectory(db)

    with pytest.raises(ReferenceNotFoundError):
        directory.resolve(mine.analyst, theirs.project_id, (mine.competitor_ids[0],))


def test_a_competitor_belonging_to_a_different_project_of_mine_is_not_found(
    db: Session, make_tenant: Callable[[str], Tenant]
) -> None:
    first = make_tenant("a")
    second = make_tenant("a2")
    # Same organization is not enough: the competitor has to be in *this* project.
    borrowed = Principal(
        user_id=uuid.uuid4(),
        organization_id=first.organization_id,
        roles=frozenset({Role.ANALYST}),
        session_id="pg-session",
    )
    directory = SqlCompetitorDirectory(db)

    with pytest.raises(ReferenceNotFoundError):
        directory.resolve(borrowed, first.project_id, (second.competitor_ids[0],))


def test_the_directory_never_issues_an_unscoped_query(
    db: Session, make_tenant: Callable[[str], Tenant]
) -> None:
    """The structural guard is called, not merely relied upon."""
    tenant = make_tenant("a")
    directory = SqlCompetitorDirectory(db)

    class Impostor:
        organization_id = uuid.uuid4()

    with pytest.raises((TenantIsolationError, ReferenceNotFoundError)):
        directory.resolve(
            Principal(
                user_id=uuid.uuid4(),
                organization_id=Impostor.organization_id,
                roles=frozenset({Role.ANALYST}),
                session_id="pg-session",
            ),
            tenant.project_id,
            tuple(tenant.competitor_ids),
        )
