"""The OpenAPI document is the API contract, and it must not drift.

If any of these fail, regenerate the artefacts rather than editing them by hand:
    python scripts/export_openapi.py
    python scripts/export_shared_types.py
    pnpm --filter @veo/api-client generate
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from veo.api.app import create_app
from veo.contracts.enums import ProviderState

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
OPENAPI_PATH = API_ROOT / "openapi.json"
SHARED_TYPES_PATH = REPO_ROOT / "packages" / "shared-types" / "src" / "enums.ts"
GENERATED_CLIENT_PATH = REPO_ROOT / "packages" / "api-client" / "src" / "schema.d.ts"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(scope="module")
def committed_document() -> dict:
    return json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))


def test_committed_openapi_matches_the_running_application(committed_document: dict) -> None:
    from scripts.export_openapi import render

    assert OPENAPI_PATH.read_text(encoding="utf-8") == render(), (
        "openapi.json is stale — run: python scripts/export_openapi.py"
    )


def test_generated_typescript_client_exists_and_covers_every_path(
    committed_document: dict,
) -> None:
    assert GENERATED_CLIENT_PATH.is_file(), (
        "the TypeScript client has never been generated — "
        "run: pnpm --filter @veo/api-client generate"
    )
    generated = GENERATED_CLIENT_PATH.read_text(encoding="utf-8")
    for path in committed_document["paths"]:
        assert f'"{path}"' in generated, f"generated client is missing {path}"


def test_shared_types_are_generated_from_the_python_contract() -> None:
    from scripts.export_shared_types import render

    assert SHARED_TYPES_PATH.read_text(encoding="utf-8") == render(), (
        "shared-types is stale — run: python scripts/export_shared_types.py"
    )


def test_every_python_contract_enum_value_reaches_typescript() -> None:
    from veo.contracts import enums as contract_enums
    from veo.scoring.models import CheckStatus

    generated = SHARED_TYPES_PATH.read_text(encoding="utf-8")
    for enum_cls in (
        contract_enums.JobStatus,
        contract_enums.ErrorCode,
        contract_enums.DataSource,
        contract_enums.ProviderState,
        contract_enums.ValueQuality,
        CheckStatus,
    ):
        for member in enum_cls:
            assert f'"{member.value}"' in generated, (
                f"{enum_cls.__name__}.{member.name} is missing from shared-types"
            )


# --------------------------------------------------------------------------- #
# Envelope shape
# --------------------------------------------------------------------------- #


def test_success_response_uses_the_standard_envelope(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200

    body = response.json()
    assert set(body) == {"data", "error", "meta"}
    assert body["error"] is None
    assert body["meta"]["request_id"]
    assert body["meta"]["generated_at"]
    assert response.headers["X-Request-Id"] == body["meta"]["request_id"]


def test_error_response_uses_the_same_envelope(client: TestClient) -> None:
    response = client.get("/api/scoring/specs/veo.does.not.exist/9.9.9")
    assert response.status_code == 404

    body = response.json()
    assert set(body) == {"data", "error", "meta"}
    assert body["data"] is None
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"]
    assert body["error"]["retryable"] is False


def test_validation_error_reports_field_level_detail(client: TestClient) -> None:
    response = client.post(
        "/api/scoring/evaluate",
        json={"spec_id": "veo.seo.readiness", "spec_version": "1.0.0", "outcomes": []},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_FAILED"
    assert body["error"]["field_errors"]


def test_caller_supplied_request_id_is_echoed(client: TestClient) -> None:
    response = client.get("/api/health", headers={"X-Request-Id": "trace-abcdef12"})
    assert response.headers["X-Request-Id"] == "trace-abcdef12"


def test_malicious_request_id_is_not_reflected(client: TestClient) -> None:
    """A caller must not be able to inject content through the correlation header."""
    response = client.get("/api/health", headers={"X-Request-Id": "<script>alert(1)</script>"})
    assert "<script>" not in response.headers["X-Request-Id"]
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["X-Request-Id"])


# --------------------------------------------------------------------------- #
# Product invariants visible through the API
# --------------------------------------------------------------------------- #


def test_health_states_the_ownership_of_the_product(client: TestClient) -> None:
    data = client.get("/api/health").json()["data"]
    assert data["app_name"] == "VEO"
    assert data["developed_by"] == "VENOM"
    assert data["methodology_by"] == "VEO-LAB"
    assert data["tagline"] == "SEO · GEO · Naver Keyword Intelligence Platform"


def test_provider_endpoint_reports_disabled_providers_honestly(client: TestClient) -> None:
    """With no credentials configured, VEO must say so rather than pretend."""
    providers = client.get("/api/providers").json()["data"]["providers"]
    assert providers

    by_name = {item["provider"]: item for item in providers}
    assert "NAVER_SEARCH_AD" in by_name
    assert "NAVER_DATALAB" in by_name

    for item in providers:
        assert item["state"] in {state.value for state in ProviderState}
        assert item["reason_ko"]


def test_published_specs_are_exposed_in_full(client: TestClient) -> None:
    listing = client.get("/api/scoring/specs").json()["data"]["specs"]
    spec_ids = {item["spec_id"] for item in listing}
    assert {"veo.seo.readiness", "veo.geo.readiness"} <= spec_ids

    for item in listing:
        assert item["is_rank_prediction"] is False
        assert item["methodology_owner"] == "VEO-LAB"
        assert len(item["checksum"]) == 64


def test_spec_detail_publishes_weights_caps_and_release_conditions(client: TestClient) -> None:
    detail = client.get("/api/scoring/specs/veo.seo.readiness/1.0.0").json()["data"]

    assert sum(c["weight"] for c in detail["categories"]) == pytest.approx(100.0)
    assert detail["severity_coefficients"]["BLOCKER"] == 1.0
    assert detail["url_importance"]["CONVERSION_OR_HOME"] == 3.0
    for cap in detail["caps"]:
        assert cap["reason_ko"] and cap["release_condition_ko"]


def test_evaluate_returns_the_score_with_its_full_provenance(client: TestClient) -> None:
    detail = client.get("/api/scoring/specs/veo.geo.readiness/1.0.0").json()["data"]
    outcomes = [
        {"check_id": check["id"], "status": "PASS", "confidence": 1.0}
        for category in detail["categories"]
        for check in category["checks"]
    ]

    response = client.post(
        "/api/scoring/evaluate",
        json={
            "spec_id": "veo.geo.readiness",
            "spec_version": "1.0.0",
            "outcomes": outcomes,
        },
    )
    assert response.status_code == 200

    body = response.json()
    data = body["data"]
    assert data["score"] == 100.0
    assert data["is_rank_prediction"] is False
    assert data["spec_version"] == "1.0.0"
    assert len(data["spec_checksum"]) == 64
    assert data["coverage"] == 1.0
    assert data["confidence"] == 1.0
    assert data["calculation_trace"]["checks"]
    assert data["calculation_trace"]["overall"]["formula"]

    assert body["meta"]["scoring_spec_version"] == "1.0.0"
    assert body["meta"]["scoring_spec_checksum"] == data["spec_checksum"]


def test_evaluate_rejects_a_partial_outcome_set(client: TestClient) -> None:
    """Omitting a check must be an error, not a silent pass."""
    response = client.post(
        "/api/scoring/evaluate",
        json={
            "spec_id": "veo.seo.readiness",
            "spec_version": "1.0.0",
            "outcomes": [
                {"check_id": "seo.http.status_ok", "status": "PASS", "confidence": 1.0}
            ],
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_not_applicable_never_reads_as_zero_through_the_api(client: TestClient) -> None:
    detail = client.get("/api/scoring/specs/veo.seo.readiness/1.0.0").json()["data"]
    structured_data_checks = {
        check["id"]
        for category in detail["categories"]
        if category["id"] == "structured_data"
        for check in category["checks"]
    }

    outcomes = [
        {
            "check_id": check["id"],
            "status": "NOT_APPLICABLE" if check["id"] in structured_data_checks else "PASS",
            "confidence": 1.0,
        }
        for category in detail["categories"]
        for check in category["checks"]
    ]

    data = client.post(
        "/api/scoring/evaluate",
        json={"spec_id": "veo.seo.readiness", "spec_version": "1.0.0", "outcomes": outcomes},
    ).json()["data"]

    assert data["score"] == 100.0
    assert data["effective_weight_total"] == 90.0

    structured = next(c for c in data["categories"] if c["category_id"] == "structured_data")
    assert structured["status"] == "NOT_APPLICABLE"
    assert structured["score"] is None


def test_every_provider_state_has_a_korean_reason() -> None:
    """A new ProviderState must come with an explanation, not a fallback.

    The endpoint no longer raises on an unknown state, so this is what keeps the map
    honest — otherwise a new state would quietly render as "설명이 등록되지 않았습니다".
    """
    from veo.api.routes.meta import _STATE_REASONS_KO
    from veo.contracts.enums import ProviderState

    missing = sorted(state for state in ProviderState if state not in _STATE_REASONS_KO)
    assert not missing, f"ProviderState without a Korean reason: {missing}"
