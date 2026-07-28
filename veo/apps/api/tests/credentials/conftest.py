"""Fixtures for the credential-vault suite.

The vault is a database component, so its tests run against a real, migrated PostgreSQL
(``VEO_TEST_DATABASE_URL``). Every fixture deletes the rows it created; a leftover
``provider_credentials`` row would quietly change the next run's assertions.

Authentication belongs to another worker. These tests never build a token: they override
``veo.authz.deps.get_principal`` with a :class:`Principal` constructed by hand.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, delete
from sqlalchemy.orm import Session, sessionmaker
from vaulthelpers import DATABASE_URL, MASTER_KEY_V1_B64, MASTER_KEY_V2_B64, make_principal

from veo.api.app import create_app
from veo.authz import Principal
from veo.authz.deps import get_principal
from veo.contracts.enums import Role
from veo.credentials.cipher import MasterKey
from veo.credentials.router import get_vault
from veo.credentials.vault import CredentialVault
from veo.db.models import Organization, ProviderCredential, User
from veo.db.session import get_db


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    if not DATABASE_URL:
        pytest.skip("VEO_TEST_DATABASE_URL is not set")
    created = create_engine(DATABASE_URL, future=True)
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    opened = factory()
    try:
        yield opened
    finally:
        opened.rollback()
        opened.close()


def _make_organization(session: Session, slug: str) -> Iterator[Organization]:
    unique = f"{slug}-{uuid.uuid4().hex[:8]}"
    organization = Organization(slug=unique, name=unique, is_active=True, settings={})
    session.add(organization)
    session.commit()
    try:
        yield organization
    finally:
        session.rollback()
        session.execute(
            delete(ProviderCredential).where(
                ProviderCredential.organization_id == organization.id
            )
        )
        session.execute(delete(Organization).where(Organization.id == organization.id))
        session.commit()


@pytest.fixture
def organization_a(session: Session) -> Iterator[Organization]:
    yield from _make_organization(session, "veo-test-org-a")


@pytest.fixture
def organization_b(session: Session) -> Iterator[Organization]:
    yield from _make_organization(session, "veo-test-org-b")


@pytest.fixture
def user(session: Session) -> Iterator[User]:
    created = User(
        email=f"vault-test-{uuid.uuid4().hex[:10]}@veo.invalid",
        display_name="Vault Test",
        is_active=True,
    )
    session.add(created)
    session.commit()
    try:
        yield created
    finally:
        session.rollback()
        session.execute(delete(User).where(User.id == created.id))
        session.commit()


@pytest.fixture
def principal(organization_a: Organization, user: User) -> Principal:
    return make_principal(organization_a, user, Role.SUPER_ADMIN)


@pytest.fixture
def master_key() -> MasterKey:
    return MasterKey.from_base64(MASTER_KEY_V1_B64, version=1)


@pytest.fixture
def next_master_key() -> MasterKey:
    return MasterKey.from_base64(MASTER_KEY_V2_B64, version=2)


@pytest.fixture
def vault(session: Session, master_key: MasterKey) -> CredentialVault:
    return CredentialVault(session, master_key=master_key)


@pytest.fixture
def app(session: Session, vault: CredentialVault, principal: Principal) -> FastAPI:
    """The real application, with this suite's dependencies swapped in.

    ``create_app()`` now mounts the credentials router itself, so this no longer includes
    it a second time — doing so registered every route twice and produced duplicate
    OpenAPI operation ids, which breaks TypeScript client generation.
    """
    built = create_app()
    built.dependency_overrides[get_db] = lambda: session
    built.dependency_overrides[get_vault] = lambda: vault
    built.dependency_overrides[get_principal] = lambda: principal
    return built


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as opened:
        yield opened
