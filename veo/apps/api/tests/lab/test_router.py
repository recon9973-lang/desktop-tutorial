"""The VEO-LAB HTTP surface.

The router is not mounted by ``veo.api.app`` — the integrator owns that file — so the
test application in ``conftest`` includes it under the real API prefix.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.lab.support import (
    CANDIDATE_VERSION,
    LAB_SPEC_ID,
    VERSIONS,
    Tenant,
    candidate_document,
    error_code,
    error_message,
    lab_document,
    payload,
    seed_score,
)

from veo.authz.principal import Principal
from veo.scoring import load_spec

Act = Callable[[Principal], None]


def _has_hangul(text: str) -> bool:
    return any("가" <= character <= "힣" for character in text)


def _create(client: TestClient, document: dict | None = None) -> dict:
    response = client.post(
        VERSIONS,
        json={
            "specification": document or candidate_document(),
            "changelog": "알파 배점을 60에서 70으로 옮깁니다.",
        },
    )
    assert response.status_code == 201, response.text
    return payload(response)


def _publish(client: TestClient, version_id: str) -> dict:
    assert client.post(f"{VERSIONS}/{version_id}/golden-run").status_code == 200
    assert client.post(f"{VERSIONS}/{version_id}/submit").status_code == 200
    assert client.post(f"{VERSIONS}/{version_id}/approve").status_code == 200
    response = client.post(f"{VERSIONS}/{version_id}/publish")
    assert response.status_code == 200, response.text
    return payload(response)


def test_the_lab_router_is_reachable_in_the_assembled_application() -> None:
    """Inverted at integration: the integrator has now mounted this router.

    The previous version asserted the opposite by inspecting ``app.routes``, which cannot
    see an included router on this FastAPI version — so it passed either way.
    ``openapi()`` is the honest source of truth.
    """
    from veo.api.app import create_app

    paths = create_app().openapi()["paths"]
    assert any(path.startswith("/api/lab/scoring-versions") for path in paths)


def test_a_lab_admin_walks_a_version_from_draft_to_published(
    client: TestClient, tenant: Tenant, act_as: Act
) -> None:
    act_as(tenant.lab_admin)

    created = _create(client)
    assert created["status"] == "DRAFT"
    assert created["spec_id"] == LAB_SPEC_ID
    assert created["semantic_version"] == CANDIDATE_VERSION
    assert _has_hangul(created["status_label_ko"])

    golden = payload(client.post(f"{VERSIONS}/{created['id']}/golden-run"))
    assert golden["all_passed"] is True
    assert golden["total"] == 2
    assert _has_hangul(golden["summary_ko"])

    assert payload(client.post(f"{VERSIONS}/{created['id']}/submit"))["status"] == "REVIEW"
    assert payload(client.post(f"{VERSIONS}/{created['id']}/approve"))["status"] == "APPROVED"

    published = payload(client.post(f"{VERSIONS}/{created['id']}/publish"))
    assert published["status"] == "PUBLISHED"
    assert published["effective_at"]

    retired = payload(client.post(f"{VERSIONS}/{created['id']}/retire"))
    assert retired["status"] == "RETIRED"


def test_the_detail_endpoint_shows_the_korean_diff(
    client: TestClient, tenant: Tenant, act_as: Act
) -> None:
    act_as(tenant.lab_admin)
    created = _create(client)

    detail = payload(client.get(f"{VERSIONS}/{created['id']}"))
    diff = detail["diff"]
    assert diff["baseline_version"] == "1.0.0"
    assert diff["has_changes"] is True
    alpha_line = next(line for line in diff["lines_ko"] if "alpha" in line)
    assert "60" in alpha_line and "70" in alpha_line
    assert detail["validation"]["ok"] is True
    assert detail["golden"] is None
    assert "REVIEW" in detail["allowed_transitions"]


def test_listing_returns_a_page_with_korean_status_labels(
    client: TestClient, tenant: Tenant, act_as: Act
) -> None:
    act_as(tenant.lab_admin)
    _create(client)

    response = client.get(VERSIONS, params={"spec_id": LAB_SPEC_ID})
    assert response.status_code == 200
    body = response.json()
    assert body["page_info"]["total_items"] == 1
    assert _has_hangul(body["data"][0]["status_label_ko"])


def test_a_sales_viewer_may_read_but_not_author(
    client: TestClient, tenant: Tenant, act_as: Act
) -> None:
    act_as(tenant.lab_admin)
    created = _create(client)

    act_as(tenant.viewer)
    assert client.get(f"{VERSIONS}/{created['id']}").status_code == 200
    denied = client.post(VERSIONS, json={"specification": candidate_document()})
    assert denied.status_code == 403
    assert error_code(denied) == "PERMISSION_DENIED"


def test_an_analyst_cannot_publish(client: TestClient, tenant: Tenant, act_as: Act) -> None:
    act_as(tenant.lab_admin)
    created = _create(client)
    client.post(f"{VERSIONS}/{created['id']}/golden-run")
    client.post(f"{VERSIONS}/{created['id']}/submit")
    client.post(f"{VERSIONS}/{created['id']}/approve")

    act_as(tenant.analyst)
    denied = client.post(f"{VERSIONS}/{created['id']}/publish")
    assert denied.status_code == 403
    assert error_code(denied) == "PERMISSION_DENIED"

    act_as(tenant.lab_admin)
    assert payload(client.get(f"{VERSIONS}/{created['id']}"))["status"] == "APPROVED"


def test_publishing_without_a_golden_run_is_a_conflict(
    client: TestClient, tenant: Tenant, act_as: Act
) -> None:
    act_as(tenant.lab_admin)
    created = _create(client)
    client.post(f"{VERSIONS}/{created['id']}/submit")
    client.post(f"{VERSIONS}/{created['id']}/approve")

    refused = client.post(f"{VERSIONS}/{created['id']}/publish")
    assert refused.status_code == 409
    assert error_code(refused) == "CONFLICT"
    assert _has_hangul(error_message(refused))


def test_editing_a_published_version_is_a_conflict(
    client: TestClient, tenant: Tenant, act_as: Act
) -> None:
    act_as(tenant.lab_admin)
    created = _create(client)
    _publish(client, created["id"])

    edited = candidate_document()
    edited["categories"][0]["weight"] = 90.0
    edited["categories"][1]["weight"] = 10.0
    refused = client.patch(f"{VERSIONS}/{created['id']}", json={"specification": edited})
    assert refused.status_code == 409
    assert _has_hangul(error_message(refused))

    stored = payload(client.get(f"{VERSIONS}/{created['id']}"))
    assert stored["checksum"] == created["checksum"]


def test_an_invalid_candidate_is_rejected_with_reasons(
    client: TestClient, tenant: Tenant, act_as: Act
) -> None:
    act_as(tenant.lab_admin)
    document = lab_document(
        version="1.5.0", status="PUBLISHED", weights={"alpha": 50.0, "beta": 20.0}
    )
    refused = client.post(VERSIONS, json={"specification": document})
    assert refused.status_code == 422
    assert error_code(refused) == "SCORING_SPEC_INVALID"
    assert _has_hangul(error_message(refused))


def test_an_unknown_version_is_a_generic_404(
    client: TestClient, tenant: Tenant, act_as: Act
) -> None:
    act_as(tenant.lab_admin)
    response = client.get(f"{VERSIONS}/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert error_code(response) == "NOT_FOUND"


def test_the_rescore_endpoint_returns_a_korean_summary(
    client: TestClient, db: Session, tenant: Tenant, act_as: Act
) -> None:
    spec = load_spec(LAB_SPEC_ID, "1.0.0")
    seed_score(db, tenant, spec, label="down", failing=("lab.alpha.two",))
    seed_score(db, tenant, spec, label="up", failing=("lab.beta.one",))

    act_as(tenant.lab_admin)
    created = _create(client)
    _publish(client, created["id"])

    summary = payload(client.post(f"{VERSIONS}/{created['id']}/rescore", json={}))
    assert summary["total"] == 2
    assert summary["risen"] == 1
    assert summary["fallen"] == 1
    assert _has_hangul(summary["summary_ko"])
    assert summary["to_version"] == CANDIDATE_VERSION
    shifts = {shift["direction"] for shift in summary["shifts"]}
    assert shifts == {"RISEN", "FALLEN"}
