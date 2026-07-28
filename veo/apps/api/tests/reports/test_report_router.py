"""The HTTP surface: permissions, tenancy, evidence gating and export parity."""

from __future__ import annotations

import io
import zipfile
from dataclasses import replace
from typing import Any

from fastapi.testclient import TestClient
from report_support import (
    EVIDENCE_SENTINEL,
    GEO_OVERALL,
    REPORTS,
    SEO_OVERALL,
    SPEC_CHECKSUM,
    SPEC_VERSION,
    UNKNOWN_REASON,
    Tenant,
    make_diagnosis,
    new_uuid,
    request_body,
    version_body,
)

from veo.reports.snapshot import UNMEASURED_KO


def _data(response: Any) -> dict[str, Any]:
    body = response.json()
    assert body["error"] is None, body["error"]
    data: dict[str, Any] = body["data"]
    return data


def _create(client: TestClient, tenant: Tenant, act_as, diagnosis=None) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    act_as(tenant.analyst)
    response = client.post(REPORTS, json=request_body(tenant.project_id, diagnosis))
    assert response.status_code == 201, response.text
    return _data(response)


# --------------------------------------------------------------------------- #
# Creating and versioning
# --------------------------------------------------------------------------- #


def test_creating_a_report_freezes_version_one(client, org_a, act_as) -> None:  # type: ignore[no-untyped-def]
    created = _create(client, org_a, act_as)

    assert created["version_number"] == 1
    assert created["content_hash"]
    assert created["spec_versions"]["SEO_READINESS"]["version"] == SPEC_VERSION
    assert created["spec_versions"]["SEO_READINESS"]["checksum"] == SPEC_CHECKSUM


def test_rerunning_the_analysis_produces_a_new_version_and_leaves_the_old_one(  # type: ignore[no-untyped-def]
    client, org_a, act_as
) -> None:
    first = _create(client, org_a, act_as)
    report_id = first["report_id"]

    diagnosis = make_diagnosis()
    lowered = replace(
        diagnosis.domains[0],
        score=diagnosis.domains[0].score.model_copy(update={"overall_score": 41.0}),
    )
    act_as(org_a.analyst)
    response = client.post(
        f"{REPORTS}/{report_id}/versions",
        json=version_body(replace(diagnosis, domains=(lowered, diagnosis.domains[1]))),
    )
    assert response.status_code == 201, response.text
    second = _data(response)
    assert second["version_number"] == 2
    assert second["content_hash"] != first["content_hash"]

    act_as(org_a.analyst)
    original = _data(client.get(f"{REPORTS}/{report_id}/versions/1"))
    assert original["views"]["executive"]["numbers"]["SEO_READINESS.overall"]["display"] == str(
        SEO_OVERALL
    )

    latest = _data(client.get(f"{REPORTS}/{report_id}/versions/2"))
    assert latest["views"]["executive"]["numbers"]["SEO_READINESS.overall"]["display"] == "41.0"
    assert latest["changes"], "the newer version says what moved"


def test_versions_can_be_listed_newest_first(client, org_a, act_as) -> None:  # type: ignore[no-untyped-def]
    created = _create(client, org_a, act_as)
    report_id = created["report_id"]
    act_as(org_a.analyst)
    client.post(f"{REPORTS}/{report_id}/versions", json=version_body())

    act_as(org_a.analyst)
    body = client.get(f"{REPORTS}/{report_id}/versions").json()
    assert body["error"] is None
    numbers = [row["version_number"] for row in body["data"]]
    assert numbers == [2, 1]
    assert all(row["content_hash"] for row in body["data"])


def test_a_reader_without_run_permission_cannot_create_a_version(client, org_a, act_as) -> None:  # type: ignore[no-untyped-def]
    act_as(org_a.viewer)
    response = client.post(REPORTS, json=request_body(org_a.project_id))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_a_report_cannot_be_created_against_another_tenants_project(  # type: ignore[no-untyped-def]
    client, org_a, org_b, act_as
) -> None:
    act_as(org_a.analyst)
    response = client.post(REPORTS, json=request_body(org_b.project_id))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


# --------------------------------------------------------------------------- #
# Tenancy
# --------------------------------------------------------------------------- #


def test_another_tenants_report_is_not_found_rather_than_forbidden(  # type: ignore[no-untyped-def]
    client, org_a, org_b, act_as
) -> None:
    created = _create(client, org_a, act_as)
    report_id = created["report_id"]

    for path in (
        f"{REPORTS}/{report_id}/versions",
        f"{REPORTS}/{report_id}/versions/1",
        f"{REPORTS}/{report_id}/versions/1/export?format=csv",
    ):
        act_as(org_b.analyst)
        response = client.get(path)
        assert response.status_code == 404, path
        assert EVIDENCE_SENTINEL not in response.text


def test_an_unknown_report_id_is_also_not_found(client, org_a, act_as) -> None:  # type: ignore[no-untyped-def]
    act_as(org_a.analyst)
    response = client.get(f"{REPORTS}/{new_uuid()}/versions/1")
    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# Evidence gating
# --------------------------------------------------------------------------- #


def test_a_caller_without_evidence_read_gets_full_scores_and_no_excerpts(  # type: ignore[no-untyped-def]
    client, org_a, act_as
) -> None:
    created = _create(client, org_a, act_as)
    report_id = created["report_id"]

    act_as(org_a.viewer)
    response = client.get(f"{REPORTS}/{report_id}/versions/1")
    assert response.status_code == 200
    assert EVIDENCE_SENTINEL not in response.text

    data = _data(response)
    assert data["evidence_included"] is False
    numbers = data["views"]["executive"]["numbers"]
    assert numbers["SEO_READINESS.overall"]["display"] == str(SEO_OVERALL)
    assert numbers["GEO_READINESS.overall"]["display"] == str(GEO_OVERALL)

    references = data["views"]["developer"]["evidence"]
    assert references, "the reference stays, only the excerpt goes"
    assert all(record["excerpt"] is None for record in references)
    assert all(record["excerpt_redacted"] is True for record in references)
    assert all(record["content_hash"] for record in references)


def test_a_caller_with_evidence_read_sees_the_excerpts(client, org_a, act_as) -> None:  # type: ignore[no-untyped-def]
    created = _create(client, org_a, act_as)
    report_id = created["report_id"]

    act_as(org_a.developer)
    response = client.get(f"{REPORTS}/{report_id}/versions/1")
    assert response.status_code == 200
    assert EVIDENCE_SENTINEL in response.text


def test_the_gated_export_also_carries_no_excerpt(client, org_a, act_as) -> None:  # type: ignore[no-untyped-def]
    created = _create(client, org_a, act_as)
    report_id = created["report_id"]

    act_as(org_a.analyst)
    with_evidence = client.get(f"{REPORTS}/{report_id}/versions/1/export?format=html")
    assert EVIDENCE_SENTINEL in with_evidence.text

    act_as(org_a.viewer)
    denied = client.get(f"{REPORTS}/{report_id}/versions/1/export?format=html")
    assert denied.status_code == 403, "a sales viewer holds no report:export"


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #


def test_every_export_format_carries_the_same_numbers_and_the_methodology(  # type: ignore[no-untyped-def]
    client, org_a, act_as
) -> None:
    created = _create(client, org_a, act_as)
    report_id = created["report_id"]
    base = f"{REPORTS}/{report_id}/versions/1"

    act_as(org_a.analyst)
    read = _data(client.get(base))
    rendered = read["views"]["executive"]["numbers"]["SEO_READINESS.overall"]["display"]

    act_as(org_a.analyst)
    html = client.get(f"{base}/export?format=html")
    assert html.status_code == 200
    assert html.headers["content-type"].startswith("text/html")
    assert rendered in html.text
    assert SPEC_VERSION in html.text and SPEC_CHECKSUM in html.text

    act_as(org_a.analyst)
    csv_response = client.get(f"{base}/export?format=csv")
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    csv_text = csv_response.content.decode("utf-8-sig")
    assert rendered in csv_text
    assert SPEC_CHECKSUM in csv_text
    assert UNMEASURED_KO in csv_text
    assert UNKNOWN_REASON in csv_text

    act_as(org_a.analyst)
    xlsx = client.get(f"{base}/export?format=xlsx")
    assert xlsx.status_code == 200
    assert "spreadsheetml.sheet" in xlsx.headers["content-type"]
    with zipfile.ZipFile(io.BytesIO(xlsx.content)) as archive:
        assert archive.testzip() is None
        sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert rendered in sheet
    assert SPEC_CHECKSUM in sheet

    assert "attachment;" in xlsx.headers["content-disposition"]


def test_the_three_views_returned_over_http_agree_on_every_shared_number(  # type: ignore[no-untyped-def]
    client, org_a, act_as
) -> None:
    created = _create(client, org_a, act_as)
    act_as(org_a.analyst)
    data = _data(client.get(f"{REPORTS}/{created['report_id']}/versions/1"))

    views = data["views"]
    shared = (
        set(views["executive"]["numbers"])
        & set(views["marketing"]["numbers"])
        & set(views["developer"]["numbers"])
    )
    assert shared
    for key in shared:
        rendered = {views[name]["numbers"][key]["display"] for name in views}
        assert len(rendered) == 1, f"{key} disagrees across audiences: {rendered}"
