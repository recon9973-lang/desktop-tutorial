"""Fixtures for the keyword suite.

Two seams keep these tests off the network and off PostgreSQL:

* the provider clients take an ``httpx`` transport, so a lookup is answered by a handler
  in the test rather than by Naver;
* the service takes a :class:`~veo.keywords.repository.KeywordRepository`, and this module
  supplies an in-memory one. The SQLAlchemy implementation is exercised separately in
  ``test_persistence.py``, which is marked ``requires_postgres``.

Authentication belongs to another worker, so the tests override
``veo.authz.deps.get_principal`` with a principal built by hand — the same approach the
credential and resource suites already use.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from veo.api.app import create_app
from veo.authz import Principal
from veo.authz.deps import get_principal
from veo.contracts.enums import Role
from veo.keywords.repository import InMemoryKeywordRepository, KeywordRepository
from veo.keywords.router import get_keyword_service
from veo.keywords.service import KeywordService
from veo.providers.naver.datalab import DataLabCredentials, NaverDataLabClient
from veo.providers.naver.searchad import NaverSearchAdClient, SearchAdCredentials

from pydantic import SecretStr  # isort: skip

API_PREFIX = "/api"
NOW = datetime(2026, 7, 28, 3, 0, tzinfo=UTC)

SEARCHAD_CREDENTIALS = SearchAdCredentials(
    api_key=SecretStr("synthetic-access-license"),
    secret_key=SecretStr("synthetic-secret"),
    customer_id="9999999",
)
DATALAB_CREDENTIALS = DataLabCredentials(
    client_id=SecretStr("synthetic-client-id"),
    client_secret=SecretStr("synthetic-client-secret"),
)


@pytest.fixture
def organization_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def principal_box() -> dict[str, Principal]:
    return {}


@pytest.fixture
def principal(organization_id: uuid.UUID) -> Principal:
    return Principal(
        user_id=uuid.uuid4(),
        organization_id=organization_id,
        roles=frozenset({Role.ANALYST}),
        session_id="synthetic-session",
    )


@pytest.fixture
def repository() -> KeywordRepository:
    return InMemoryKeywordRepository()


def make_service(
    *,
    repository: KeywordRepository,
    searchad_handler: Callable[[httpx.Request], httpx.Response] | None = None,
    datalab_handler: Callable[[httpx.Request], httpx.Response] | None = None,
    searchad_credentials: SearchAdCredentials | None = SEARCHAD_CREDENTIALS,
    datalab_credentials: DataLabCredentials | None = DATALAB_CREDENTIALS,
    now: datetime = NOW,
) -> KeywordService:
    def refuse(request: httpx.Request) -> httpx.Response:  # pragma: no cover - guard
        raise AssertionError("no outbound call was expected in this test")

    return KeywordService(
        searchad=NaverSearchAdClient(
            credentials=searchad_credentials,
            transport=httpx.MockTransport(searchad_handler or refuse),
            clock=lambda: now,
            sleep=lambda seconds: None,
        ),
        datalab=NaverDataLabClient(
            credentials=datalab_credentials,
            transport=httpx.MockTransport(datalab_handler or refuse),
            clock=lambda: now,
            sleep=lambda seconds: None,
        ),
        repository=repository,
        clock=lambda: now,
    )


@pytest.fixture
def service_box() -> dict[str, KeywordService]:
    return {}


@pytest.fixture
def app(
    principal: Principal,
    principal_box: dict[str, Principal],
    service_box: dict[str, KeywordService],
    repository: KeywordRepository,
) -> FastAPI:
    """The real application, with this suite's dependencies swapped in.

    ``create_app()`` mounts the keywords router itself now. This used to include it again
    behind a guard that inspected ``app.routes`` — which cannot work on this FastAPI
    version, where an included router appears as a single ``_IncludedRouter`` with
    ``path=None``. The guard therefore never matched, the router was mounted twice, and
    every operation id was duplicated.
    """
    principal_box.setdefault("principal", principal)
    service_box.setdefault("service", make_service(repository=repository))

    built = create_app()
    built.dependency_overrides[get_principal] = lambda: principal_box["principal"]
    built.dependency_overrides[get_keyword_service] = lambda: service_box["service"]
    return built


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as opened:
        yield opened
