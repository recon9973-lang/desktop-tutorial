"""A delivered number is still that number six months later.

``ReportVersion`` carries no ``updated_at`` by design. These tests prove the intent is
enforced rather than merely documented: an attempt to edit a stored version fails, and a
corrected measurement arrives as a new version beside the old one.
"""

from __future__ import annotations

import pytest
from report_support import SEO_OVERALL, Tenant, make_diagnosis
from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.db.models.observation import ReportVersion
from veo.reports.repository import ReportVersionImmutableError, SqlReportRepository
from veo.reports.service import ReportService
from veo.reports.snapshot import from_payload


def _service(session: Session) -> ReportService:
    return ReportService(SqlReportRepository(session))


def test_a_stored_version_cannot_be_edited(db: Session, org_a: Tenant) -> None:
    service = _service(db)
    stored = service.create_report(
        principal=org_a.analyst,
        project_id=org_a.project_id,
        diagnosis=make_diagnosis(),
    )
    db.commit()

    row = db.get(ReportVersion, stored.version_id)
    assert row is not None

    row.content = {"snapshot": {}, "content_hash": "tampered"}
    with pytest.raises(ReportVersionImmutableError):
        db.flush()
    db.rollback()

    reloaded = db.get(ReportVersion, stored.version_id)
    assert reloaded is not None
    assert reloaded.content["content_hash"] == stored.content_hash


def test_even_a_harmless_looking_field_cannot_be_edited(db: Session, org_a: Tenant) -> None:
    service = _service(db)
    stored = service.create_report(
        principal=org_a.analyst, project_id=org_a.project_id, diagnosis=make_diagnosis()
    )
    db.commit()

    row = db.get(ReportVersion, stored.version_id)
    assert row is not None
    row.export_formats = ["html"]
    with pytest.raises(ReportVersionImmutableError):
        db.flush()
    db.rollback()


def test_a_correction_arrives_as_a_new_version_beside_the_old_one(
    db: Session, org_a: Tenant
) -> None:
    service = _service(db)
    first = service.create_report(
        principal=org_a.analyst, project_id=org_a.project_id, diagnosis=make_diagnosis()
    )
    db.commit()

    diagnosis = make_diagnosis()
    from dataclasses import replace

    corrected = replace(
        diagnosis.domains[0],
        score=diagnosis.domains[0].score.model_copy(update={"overall_score": 33.0}),
    )
    second = service.create_version(
        principal=org_a.analyst,
        report_id=first.report_id,
        diagnosis=replace(diagnosis, domains=(corrected, diagnosis.domains[1])),
    )
    db.commit()

    assert second.version_number == 2
    rows = list(
        db.scalars(
            select(ReportVersion)
            .where(ReportVersion.report_id == first.report_id)
            .where(ReportVersion.organization_id == org_a.organization_id)
            .order_by(ReportVersion.version_number)
        )
    )
    assert [row.version_number for row in rows] == [1, 2]

    original = from_payload(rows[0].content)
    assert original.metric("SEO_READINESS.overall").value.value == SEO_OVERALL
    assert from_payload(rows[1].content).metric("SEO_READINESS.overall").value.value == 33.0


def test_the_stored_payload_verifies_its_own_content_hash(db: Session, org_a: Tenant) -> None:
    service = _service(db)
    stored = service.create_report(
        principal=org_a.analyst, project_id=org_a.project_id, diagnosis=make_diagnosis()
    )
    db.commit()

    row = db.get(ReportVersion, stored.version_id)
    assert row is not None
    snapshot = from_payload(row.content)
    assert snapshot.metric("SEO_READINESS.overall").value.value == SEO_OVERALL
    assert row.scoring_versions["SEO_READINESS"]["checksum"]
    assert row.export_formats == ["html", "csv", "xlsx"]
    assert row.disclosures_ko
    assert row.included_run_ids
