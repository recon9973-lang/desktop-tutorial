"""The GEO router.

It is not mounted — ``veo.api.app`` belongs to the integrator — so the test app is
``create_app()`` plus this router. What matters here is the shape of the answer: the
readiness number and the exposure status appear **side by side**, so a console can say
"95점이지만 노출 차단" without either fact hiding the other.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from veo.api.app import create_app
from veo.authz.deps import get_principal
from veo.authz.principal import Principal
from veo.contracts.enums import Role
from veo.geo.router import router as geo_router

FIXTURE_ROOT = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "geo"


def principal(*roles: Role) -> Principal:
    return Principal(
        user_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        roles=frozenset(roles),
        session_id="test-session",
    )


def mounted_paths(application: FastAPI) -> set[str]:
    return {str(getattr(route, "path", "")) for route in application.routes}


@pytest.fixture
def app() -> FastAPI:
    application = create_app()
    if not any(path.startswith("/geo") for path in mounted_paths(application)):
        application.include_router(geo_router)
    return application


@pytest.fixture
def analyst(app: FastAPI) -> Iterator[TestClient]:
    app.dependency_overrides[get_principal] = lambda: principal(Role.ANALYST)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def viewer(app: FastAPI) -> Iterator[TestClient]:
    app.dependency_overrides[get_principal] = lambda: principal(Role.SALES_VIEWER)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def request_body(case: str, *, target: str, page: str = "page.html") -> dict[str, Any]:
    directory = FIXTURE_ROOT / case
    return {
        "target_url": target,
        "documents": [
            {
                "url": target,
                "status": 200,
                "headers": {"content-type": "text/html; charset=utf-8"},
                "html": (directory / page).read_text(encoding="utf-8"),
                "primary": True,
            }
        ],
        "robots_txt": (directory / "robots.txt").read_text(encoding="utf-8")
        if (directory / "robots.txt").is_file()
        else None,
    }


# --------------------------------------------------------------------------- #
# The router is a router, not a mounted route
# --------------------------------------------------------------------------- #


def test_the_router_is_not_mounted_by_the_application() -> None:
    assert not any(path.startswith("/geo") for path in mounted_paths(create_app()))


def test_the_router_declares_a_prefix_and_a_tag() -> None:
    assert geo_router.prefix == "/geo"
    assert geo_router.tags == ["geo"]


# --------------------------------------------------------------------------- #
# Permissions
# --------------------------------------------------------------------------- #


def test_reading_the_specification_needs_only_read_permission(viewer: TestClient) -> None:
    response = viewer.get("/geo/readiness/spec")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["spec_id"] == "veo.geo.readiness"
    assert len(data["categories"]) == 7
    assert data["check_count"] == 37


def test_running_an_analysis_needs_run_permission(viewer: TestClient) -> None:
    body = request_body("hospital_local", target="https://ondam.example.kr/clinic/whitening")
    assert viewer.post("/geo/readiness/analyses", json=body).status_code == 403


def test_an_analyst_may_run_an_analysis(analyst: TestClient) -> None:
    body = request_body("hospital_local", target="https://ondam.example.kr/clinic/whitening")
    assert analyst.post("/geo/readiness/analyses", json=body).status_code == 200


# --------------------------------------------------------------------------- #
# Score and gate, side by side
# --------------------------------------------------------------------------- #


def test_a_healthy_page_reports_a_score_and_no_exposure_problem(analyst: TestClient) -> None:
    body = request_body("hospital_local", target="https://ondam.example.kr/clinic/whitening")
    data = analyst.post("/geo/readiness/analyses", json=body).json()["data"]

    assert data["readiness"]["score"] is not None
    assert data["readiness"]["band_id"]
    assert data["readiness"]["band_label_ko"]
    assert data["exposure"]["blocked"] is False
    assert data["exposure"]["gates"] == []


def test_a_noindex_page_reports_the_score_and_the_block_together(analyst: TestClient) -> None:
    body = request_body("noindex_page", target="https://ondam.example.kr/preview/whitening")
    data = analyst.post("/geo/readiness/analyses", json=body).json()["data"]

    assert data["readiness"]["score"] is not None
    assert data["readiness"]["score"] > 50
    assert data["exposure"]["blocked"] is True
    assert "EXPOSURE_BLOCKED" in data["exposure"]["status_codes"]
    assert data["exposure"]["gates"][0]["label_ko"]


def test_the_exposure_status_never_appears_inside_the_readiness_block(
    analyst: TestClient,
) -> None:
    body = request_body("noindex_page", target="https://ondam.example.kr/preview/whitening")
    readiness = analyst.post("/geo/readiness/analyses", json=body).json()["data"]["readiness"]
    assert "gates" not in readiness
    assert "blocked" not in readiness
    assert "status_codes" not in readiness


def test_the_summary_is_korean_and_states_both_facts(analyst: TestClient) -> None:
    body = request_body("noindex_page", target="https://ondam.example.kr/preview/whitening")
    data = analyst.post("/geo/readiness/analyses", json=body).json()["data"]
    assert "노출" in data["summary_ko"]
    assert "준비도" in data["summary_ko"]
    assert data["scope_notice_ko"]


def test_the_response_carries_the_specification_version_in_its_meta(
    analyst: TestClient,
) -> None:
    body = request_body("hospital_local", target="https://ondam.example.kr/clinic/whitening")
    meta = analyst.post("/geo/readiness/analyses", json=body).json()["meta"]
    assert meta["scoring_spec_id"] == "veo.geo.readiness"
    assert meta["scoring_spec_version"]
    assert meta["scoring_spec_checksum"]


def test_categories_are_reported_with_korean_names(analyst: TestClient) -> None:
    body = request_body("hospital_local", target="https://ondam.example.kr/clinic/whitening")
    data = analyst.post("/geo/readiness/analyses", json=body).json()["data"]
    categories = data["readiness"]["categories"]
    assert len(categories) == 7
    for category in categories:
        assert category["name_ko"]
        assert category["status"] in {"SCORED", "NOT_APPLICABLE", "UNKNOWN"}


def test_a_contradictory_schema_reports_the_risk_gate(analyst: TestClient) -> None:
    body = request_body("contradictory_schema", target="https://deunden.example.kr/care")
    data = analyst.post("/geo/readiness/analyses", json=body).json()["data"]
    assert "STRUCTURED_DATA_MISMATCH" in data["exposure"]["status_codes"]
    assert data["readiness"]["score"] is not None


def test_issues_are_returned_in_korean(analyst: TestClient) -> None:
    body = request_body("generic_service", target="https://best.example.com/")
    data = analyst.post("/geo/readiness/analyses", json=body).json()["data"]
    assert data["issues"]
    for issue in data["issues"]:
        assert issue["title_ko"]
        assert issue["remediation_ko"]


def test_an_empty_document_list_is_rejected(analyst: TestClient) -> None:
    response = analyst.post(
        "/geo/readiness/analyses",
        json={"target_url": "https://example.com/", "documents": []},
    )
    assert response.status_code == 422
