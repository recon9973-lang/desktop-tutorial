"""The ``/competitors`` HTTP surface.

The router is not mounted — ``veo.api.app`` belongs to the integrator — so the test
application is ``create_app()`` plus this router, which means the real error handlers,
the real permission matrix and the real envelope are all in play.

Two seams are faked, both behind protocols the package owns: the competitor directory
(so most of this file runs without PostgreSQL — the real SQL directory is exercised in
``test_competitor_directory_postgres.py``) and the comparison store.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from veo.api.app import create_app
from veo.authz.deps import get_principal
from veo.authz.principal import Principal
from veo.competitors.router import router as competitors_router
from veo.competitors.service import (
    CompetitorRef,
    InMemoryComparisonStore,
    InMemoryCompetitorDirectory,
)
from veo.contracts.enums import Role
from veo.scoring import latest_published

ORGANIZATION_ID = uuid.uuid4()
OTHER_ORGANIZATION_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()
RIVAL_A = uuid.uuid4()
RIVAL_B = uuid.uuid4()

SPEC = latest_published("veo.seo.readiness")


def principal(*roles: Role, organization_id: uuid.UUID = ORGANIZATION_ID) -> Principal:
    return Principal(
        user_id=uuid.uuid4(),
        organization_id=organization_id,
        roles=frozenset(roles),
        session_id="test-session",
    )


def mounted_paths(application: FastAPI) -> set[str]:
    return {str(getattr(route, "path", "")) for route in application.routes}


def competitor(competitor_id: uuid.UUID, name: str, origin: str) -> CompetitorRef:
    return CompetitorRef(
        id=competitor_id,
        display_name=name,
        origin=origin,
        selection_source="CUSTOMER_SPECIFIED",
        is_active=True,
    )


@pytest.fixture
def directory() -> InMemoryCompetitorDirectory:
    fake = InMemoryCompetitorDirectory()
    fake.add(ORGANIZATION_ID, PROJECT_ID, competitor(RIVAL_A, "경쟁사 A", "https://a.example"))
    fake.add(ORGANIZATION_ID, PROJECT_ID, competitor(RIVAL_B, "경쟁사 B", "https://b.example"))
    return fake


@pytest.fixture
def store() -> InMemoryComparisonStore:
    return InMemoryComparisonStore()


@pytest.fixture
def app(directory: InMemoryCompetitorDirectory, store: InMemoryComparisonStore) -> FastAPI:
    from veo.competitors import router as router_module

    application = create_app()
    if not any(path.startswith("/competitors") for path in mounted_paths(application)):
        application.include_router(competitors_router)
    application.dependency_overrides[router_module.get_competitor_directory] = lambda: directory
    application.dependency_overrides[router_module.get_comparison_store] = lambda: store
    return application


@contextmanager
def acting_as(application: FastAPI, caller: Principal) -> Iterator[TestClient]:
    """One client bound to one caller. Two callers in one test get two blocks."""
    application.dependency_overrides[get_principal] = lambda: caller
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def analyst(app: FastAPI) -> Iterator[TestClient]:
    with acting_as(app, principal(Role.ANALYST)) as test_client:
        yield test_client


# --------------------------------------------------------------------------- #
# Bodies
# --------------------------------------------------------------------------- #


def measurement_body(
    *,
    overall: float = 70.0,
    coverage: float = 0.9,
    category_score: float = 80.0,
    checks: dict[str, str] | None = None,
    **condition_overrides: Any,
) -> dict[str, Any]:
    conditions: dict[str, Any] = {
        "collector_version": "veo-collector/1.4.0",
        "device": "MOBILE",
        "renderer": "HEADLESS_CHROME",
        "pages_examined": 30,
        "locale": "ko-KR",
        "enabled_providers": ["google_psi"],
        "measured_at": "2026-07-01T09:00:00Z",
    }
    conditions.update(condition_overrides)
    return {
        "conditions": conditions,
        "score": {
            "spec_id": SPEC.spec_id,
            "spec_version": SPEC.version,
            "spec_checksum": SPEC.checksum,
            "overall_score": overall,
            "coverage": coverage,
            "confidence": 0.9,
            "categories": [
                {
                    "category_id": "crawl_indexability",
                    "score": category_score,
                    "coverage": 1.0,
                    "scored_check_ids": ["seo.http.status_ok"],
                }
            ],
            "check_statuses": checks
            or {"seo.http.status_ok": "PASS", "seo.robots.txt_allows_url": "PASS"},
        },
    }


def create_body(
    *,
    competitor_ids: list[uuid.UUID] | None = None,
    allow_scope_variance: bool = False,
    competitor_overrides: dict[str, Any] | None = None,
    project_id: uuid.UUID = PROJECT_ID,
) -> dict[str, Any]:
    ids = competitor_ids if competitor_ids is not None else [RIVAL_A]
    return {
        "project_id": str(project_id),
        "allow_scope_variance": allow_scope_variance,
        "baseline": {"label_ko": "우리 사이트", "measurement": measurement_body()},
        "competitors": [
            {
                "competitor_id": str(competitor_id),
                "measurement": measurement_body(
                    overall=75.0, category_score=90.0, **(competitor_overrides or {})
                ),
            }
            for competitor_id in ids
        ],
    }


def data_of(response: Any) -> dict[str, Any]:
    body = response.json()
    assert body["error"] is None, body["error"]
    payload: dict[str, Any] = body["data"]
    return payload


# --------------------------------------------------------------------------- #
# The router is a router
# --------------------------------------------------------------------------- #


def test_the_router_is_not_mounted_by_the_application() -> None:
    assert not any(path.startswith("/competitors") for path in mounted_paths(create_app()))


def test_the_router_declares_a_prefix_and_a_tag() -> None:
    assert competitors_router.prefix == "/competitors"
    assert competitors_router.tags == ["competitors"]


# --------------------------------------------------------------------------- #
# Permissions
# --------------------------------------------------------------------------- #


def test_competitor_read_cannot_create_a_comparison(app: FastAPI) -> None:
    with acting_as(app, principal(Role.SALES_VIEWER)) as viewer:
        response = viewer.post("/competitors/comparisons", json=create_body())

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"
    assert "competitor:write" in response.json()["error"]["message"]


def test_competitor_read_may_list_and_read(app: FastAPI) -> None:
    with acting_as(app, principal(Role.ANALYST)) as analyst:
        created = data_of(analyst.post("/competitors/comparisons", json=create_body()))

    with acting_as(app, principal(Role.SALES_VIEWER)) as viewer:
        listing = viewer.get(
            "/competitors/comparisons", params={"project_id": str(PROJECT_ID)}
        )
        single = viewer.get(f"/competitors/comparisons/{created['id']}")

    assert listing.status_code == 200
    assert single.status_code == 200


# --------------------------------------------------------------------------- #
# Create / list / read
# --------------------------------------------------------------------------- #


def test_a_clean_comparison_comes_back_with_deltas_and_a_korean_summary(
    analyst: TestClient,
) -> None:
    payload = data_of(analyst.post("/competitors/comparisons", json=create_body()))

    assert payload["project_id"] == str(PROJECT_ID)
    assert payload["summary_ko"]
    pair = payload["pairs"][0]
    assert pair["comparable"] is True
    assert pair["competitor_label_ko"] == "경쟁사 A"
    assert pair["overall_delta"] == pytest.approx(-5.0)
    assert payload["comparison_set"][0]["label_ko"] == "경쟁사 A"


def test_a_refusal_is_a_two_hundred_that_explains_itself_not_a_number(
    analyst: TestClient,
) -> None:
    body = create_body(competitor_overrides={"device": "DESKTOP"})
    payload = data_of(analyst.post("/competitors/comparisons", json=body))

    pair = payload["pairs"][0]
    assert pair["comparable"] is False
    assert pair["overall_delta"] is None
    assert pair["categories"] == []
    assert "device" in [d["field"] for d in pair["blocking_differences"]]
    assert pair["refusal_ko"]
    assert "기기" in pair["refusal_ko"]


def test_the_scope_waiver_must_be_asked_for_and_is_still_reported(
    analyst: TestClient,
) -> None:
    body = create_body(competitor_overrides={"pages_examined": 300})

    refused = data_of(analyst.post("/competitors/comparisons", json=body))
    assert refused["pairs"][0]["comparable"] is False

    body["allow_scope_variance"] = True
    waived = data_of(analyst.post("/competitors/comparisons", json=body))
    pair = waived["pairs"][0]
    assert pair["comparable"] is True
    assert pair["waived_scope_variance"] is True
    assert "pages_examined" in [d["field"] for d in pair["waived_differences"]]


def test_a_comparison_can_be_read_back_exactly_as_it_was_created(
    analyst: TestClient,
) -> None:
    created = data_of(analyst.post("/competitors/comparisons", json=create_body()))
    fetched = data_of(analyst.get(f"/competitors/comparisons/{created['id']}"))
    assert fetched == created


def test_the_list_is_scoped_to_the_project_and_newest_first(analyst: TestClient) -> None:
    first = data_of(analyst.post("/competitors/comparisons", json=create_body()))
    second = data_of(
        analyst.post("/competitors/comparisons", json=create_body(competitor_ids=[RIVAL_B]))
    )

    body = analyst.get(
        "/competitors/comparisons", params={"project_id": str(PROJECT_ID)}
    ).json()
    assert body["page_info"]["total_items"] == 2
    assert [row["id"] for row in body["data"]] == [second["id"], first["id"]]
    assert body["data"][0]["comparable_count"] == 1

    empty = analyst.get(
        "/competitors/comparisons", params={"project_id": str(uuid.uuid4())}
    ).json()
    assert empty["page_info"]["total_items"] == 0


# --------------------------------------------------------------------------- #
# Tenancy and input integrity
# --------------------------------------------------------------------------- #


def test_a_competitor_outside_the_callers_organization_is_not_found(
    app: FastAPI, directory: InMemoryCompetitorDirectory
) -> None:
    stranger = uuid.uuid4()
    directory.add(
        OTHER_ORGANIZATION_ID,
        PROJECT_ID,
        competitor(stranger, "남의 조직 경쟁사", "https://elsewhere.example"),
    )

    with acting_as(app, principal(Role.ANALYST)) as analyst:
        response = analyst.post(
            "/competitors/comparisons", json=create_body(competitor_ids=[stranger])
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_another_organizations_comparison_is_not_readable(app: FastAPI) -> None:
    with acting_as(app, principal(Role.ANALYST)) as analyst:
        created = data_of(analyst.post("/competitors/comparisons", json=create_body()))

    with acting_as(
        app, principal(Role.ANALYST, organization_id=OTHER_ORGANIZATION_ID)
    ) as stranger:
        assert stranger.get(f"/competitors/comparisons/{created['id']}").status_code == 404


def test_a_score_whose_checksum_does_not_match_the_published_spec_is_rejected(
    analyst: TestClient,
) -> None:
    body = create_body()
    body["baseline"]["measurement"]["score"]["spec_checksum"] = "0" * 64
    response = analyst.post("/competitors/comparisons", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_a_comparison_needs_at_least_one_competitor(analyst: TestClient) -> None:
    response = analyst.post("/competitors/comparisons", json=create_body(competitor_ids=[]))
    assert response.status_code == 422


def test_the_same_competitor_may_not_be_listed_twice(analyst: TestClient) -> None:
    response = analyst.post(
        "/competitors/comparisons", json=create_body(competitor_ids=[RIVAL_A, RIVAL_A])
    )
    assert response.status_code == 422


def test_a_blank_declared_condition_is_rejected_rather_than_defaulted(
    analyst: TestClient,
) -> None:
    body = create_body()
    body["baseline"]["measurement"]["conditions"]["renderer"] = "   "
    assert analyst.post("/competitors/comparisons", json=body).status_code == 422
