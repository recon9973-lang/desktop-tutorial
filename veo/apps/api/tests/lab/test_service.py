"""The workflow service: transitions, immutability, the golden gate, checksum integrity."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import update
from sqlalchemy.orm import Session
from tests.lab.support import (
    CANDIDATE_VERSION,
    CANDIDATE_WEIGHTS,
    LAB_SPEC_ID,
    Tenant,
    candidate_document,
    lab_document,
)

from veo.authz.errors import PermissionDeniedError
from veo.db.models.analysis import ScoringVersion
from veo.lab import service
from veo.lab.errors import (
    ChecksumMismatchError,
    DuplicateVersionError,
    GoldenFixtureError,
    IllegalTransitionError,
    ImmutableVersionError,
    SpecificationRejectedError,
)
from veo.scoring import SpecStatus, compute_checksum


def _has_hangul(text: str) -> bool:
    return any("가" <= character <= "힣" for character in text)


def _draft(
    db: Session, tenant: Tenant, document: dict[str, Any] | None = None
) -> ScoringVersion:
    version = service.create_draft(
        db,
        tenant.lab_admin,
        specification=document or candidate_document(),
        changelog="알파 카테고리 배점을 60에서 70으로 옮깁니다.",
    )
    db.commit()
    return version


def _approved(
    db: Session, tenant: Tenant, document: dict[str, Any] | None = None
) -> ScoringVersion:
    version = _draft(db, tenant, document)
    service.run_golden(db, tenant.lab_admin, version.id)
    db.commit()
    service.submit_for_review(db, tenant.lab_admin, version.id)
    db.commit()
    service.approve(db, tenant.lab_admin, version.id)
    db.commit()
    return version


# --------------------------------------------------------------------------- #
# The happy path, one transition at a time
# --------------------------------------------------------------------------- #


def test_a_draft_records_the_checksum_of_exactly_what_was_submitted(
    db: Session, tenant: Tenant
) -> None:
    document = candidate_document()
    version = _draft(db, tenant, document)

    assert version.status == SpecStatus.DRAFT
    assert version.spec_id == LAB_SPEC_ID
    assert version.semantic_version == CANDIDATE_VERSION
    assert version.domain == "SEO_READINESS"
    assert version.checksum == compute_checksum(document)
    assert version.specification == document
    assert version.golden_fixture_results == {}


def test_the_full_lifecycle_reaches_published_and_then_retired(
    db: Session, tenant: Tenant
) -> None:
    version = _draft(db, tenant)

    run = service.run_golden(db, tenant.lab_admin, version.id)
    db.commit()
    assert run.all_passed
    db.refresh(version)
    assert version.golden_fixture_results["all_passed"] is True

    service.submit_for_review(db, tenant.lab_admin, version.id)
    db.commit()
    db.refresh(version)
    assert version.status == SpecStatus.REVIEW

    service.approve(db, tenant.lab_admin, version.id)
    db.commit()
    db.refresh(version)
    assert version.status == SpecStatus.APPROVED
    assert version.approved_by == tenant.lab_admin.user_id
    assert version.approved_at is not None

    service.publish(db, tenant.lab_admin, version.id)
    db.commit()
    db.refresh(version)
    assert version.status == SpecStatus.PUBLISHED
    assert version.effective_at is not None

    service.retire(db, tenant.lab_admin, version.id)
    db.commit()
    db.refresh(version)
    assert version.status == SpecStatus.RETIRED


def test_a_reviewer_can_send_a_candidate_back_to_draft(db: Session, tenant: Tenant) -> None:
    version = _draft(db, tenant)
    service.submit_for_review(db, tenant.lab_admin, version.id)
    db.commit()

    service.send_back(db, tenant.lab_admin, version.id)
    db.commit()
    db.refresh(version)
    assert version.status == SpecStatus.DRAFT


def test_publishing_retires_the_version_it_replaces(db: Session, tenant: Tenant) -> None:
    first = _approved(db, tenant)
    service.publish(db, tenant.lab_admin, first.id)
    db.commit()

    second = _approved(
        db,
        tenant,
        lab_document(version="1.2.0", status="PUBLISHED", weights=CANDIDATE_WEIGHTS),
    )
    service.publish(db, tenant.lab_admin, second.id)
    db.commit()

    db.refresh(first)
    db.refresh(second)
    assert second.status == SpecStatus.PUBLISHED
    assert first.status == SpecStatus.RETIRED


# --------------------------------------------------------------------------- #
# Rule 1 — a published version is immutable
# --------------------------------------------------------------------------- #


def test_modifying_a_published_version_fails(db: Session, tenant: Tenant) -> None:
    version = _approved(db, tenant)
    service.publish(db, tenant.lab_admin, version.id)
    db.commit()

    before = dict(version.specification)
    edited = candidate_document()
    edited["categories"][0]["weight"] = 90.0
    edited["categories"][1]["weight"] = 10.0

    with pytest.raises(ImmutableVersionError) as caught:
        service.update_draft(db, tenant.lab_admin, version.id, specification=edited)
    assert _has_hangul(caught.value.message_ko)

    db.rollback()
    db.refresh(version)
    assert version.specification == before
    assert version.checksum == compute_checksum(before)


def test_a_published_version_refuses_a_fresh_golden_run(db: Session, tenant: Tenant) -> None:
    version = _approved(db, tenant)
    service.publish(db, tenant.lab_admin, version.id)
    db.commit()

    with pytest.raises(ImmutableVersionError):
        service.run_golden(db, tenant.lab_admin, version.id)


def test_a_retired_version_refuses_every_change(db: Session, tenant: Tenant) -> None:
    version = _approved(db, tenant)
    service.publish(db, tenant.lab_admin, version.id)
    db.commit()
    service.retire(db, tenant.lab_admin, version.id)
    db.commit()

    with pytest.raises(ImmutableVersionError):
        service.update_draft(db, tenant.lab_admin, version.id, changelog="되돌리기")
    db.rollback()
    with pytest.raises(IllegalTransitionError):
        service.publish(db, tenant.lab_admin, version.id)


def test_editing_a_draft_moves_the_checksum_and_voids_the_golden_run(
    db: Session, tenant: Tenant
) -> None:
    version = _draft(db, tenant)
    service.run_golden(db, tenant.lab_admin, version.id)
    db.commit()
    assert version.golden_fixture_results["all_passed"] is True

    edited = candidate_document()
    edited["changelog"] = [
        {"version": "1.1.0", "date": "2026-08-01", "summary": "문구를 다듬었습니다."}
    ]
    service.update_draft(db, tenant.lab_admin, version.id, specification=edited)
    db.commit()
    db.refresh(version)

    assert version.checksum == compute_checksum(edited)
    assert version.golden_fixture_results == {}


# --------------------------------------------------------------------------- #
# Illegal transitions
# --------------------------------------------------------------------------- #


def test_a_draft_cannot_be_approved_directly(db: Session, tenant: Tenant) -> None:
    version = _draft(db, tenant)
    with pytest.raises(IllegalTransitionError) as caught:
        service.approve(db, tenant.lab_admin, version.id)
    assert "DRAFT" in caught.value.message_ko


def test_a_draft_cannot_be_published_directly(db: Session, tenant: Tenant) -> None:
    version = _draft(db, tenant)
    with pytest.raises(IllegalTransitionError):
        service.publish(db, tenant.lab_admin, version.id)


def test_a_version_in_review_cannot_be_retired(db: Session, tenant: Tenant) -> None:
    version = _draft(db, tenant)
    service.submit_for_review(db, tenant.lab_admin, version.id)
    db.commit()
    with pytest.raises(IllegalTransitionError):
        service.retire(db, tenant.lab_admin, version.id)


# --------------------------------------------------------------------------- #
# Rule 4 — publishing requires the golden fixtures
# --------------------------------------------------------------------------- #


def test_publishing_without_a_golden_run_fails(db: Session, tenant: Tenant) -> None:
    version = _draft(db, tenant)
    service.submit_for_review(db, tenant.lab_admin, version.id)
    db.commit()
    service.approve(db, tenant.lab_admin, version.id)
    db.commit()

    with pytest.raises(GoldenFixtureError) as caught:
        service.publish(db, tenant.lab_admin, version.id)
    assert _has_hangul(caught.value.message_ko)
    db.rollback()
    db.refresh(version)
    assert version.status == SpecStatus.APPROVED


def test_publishing_with_a_failing_golden_fixture_fails(db: Session, tenant: Tenant) -> None:
    """Weights 75/25 changes the arithmetic, so the recorded fixtures no longer hold."""
    document = lab_document(
        version="1.3.0", status="PUBLISHED", weights={"alpha": 75.0, "beta": 25.0}
    )
    version = _draft(db, tenant, document)

    run = service.run_golden(db, tenant.lab_admin, version.id)
    db.commit()
    assert not run.all_passed

    service.submit_for_review(db, tenant.lab_admin, version.id)
    db.commit()
    service.approve(db, tenant.lab_admin, version.id)
    db.commit()

    with pytest.raises(GoldenFixtureError) as caught:
        service.publish(db, tenant.lab_admin, version.id)
    assert "labtest-02-alpha-major-fail" in caught.value.message_ko
    db.rollback()
    db.refresh(version)
    assert version.status == SpecStatus.APPROVED


# --------------------------------------------------------------------------- #
# Rule 3 — a checksum mismatch is a hard error
# --------------------------------------------------------------------------- #


def test_a_tampered_stored_specification_is_refused_on_read(
    db: Session, tenant: Tenant
) -> None:
    version = _draft(db, tenant)
    tampered = candidate_document()
    tampered["categories"][0]["weight"] = 95.0
    tampered["categories"][1]["weight"] = 5.0
    db.execute(
        update(ScoringVersion)
        .where(ScoringVersion.id == version.id)
        .values(specification=tampered)
    )
    db.commit()
    db.expire_all()

    with pytest.raises(ChecksumMismatchError) as caught:
        service.read_detail(db, tenant.lab_admin, version.id)
    assert _has_hangul(caught.value.message_ko)
    assert LAB_SPEC_ID in caught.value.message_ko


def test_a_tampered_stored_specification_cannot_be_published(
    db: Session, tenant: Tenant
) -> None:
    version = _approved(db, tenant)
    tampered = candidate_document()
    tampered["categories"][0]["weight"] = 95.0
    tampered["categories"][1]["weight"] = 5.0
    db.execute(
        update(ScoringVersion)
        .where(ScoringVersion.id == version.id)
        .values(specification=tampered)
    )
    db.commit()
    db.expire_all()

    with pytest.raises(ChecksumMismatchError):
        service.publish(db, tenant.lab_admin, version.id)
    db.rollback()
    db.expire_all()
    stored = db.get(ScoringVersion, version.id)
    assert stored is not None
    # Refused, not repaired.
    assert stored.checksum != compute_checksum(stored.specification)
    assert stored.status == SpecStatus.APPROVED


# --------------------------------------------------------------------------- #
# Validation at the boundary
# --------------------------------------------------------------------------- #


def test_an_invalid_specification_never_becomes_a_draft(db: Session, tenant: Tenant) -> None:
    document = candidate_document()
    document["categories"][0]["weight"] = 10.0  # total is now 40, not 100

    with pytest.raises(SpecificationRejectedError) as caught:
        service.create_draft(db, tenant.lab_admin, specification=document)
    assert _has_hangul(caught.value.message_ko)
    assert caught.value.reasons_ko


def test_the_same_version_cannot_be_registered_twice(db: Session, tenant: Tenant) -> None:
    _draft(db, tenant)
    with pytest.raises(DuplicateVersionError) as caught:
        service.create_draft(db, tenant.lab_admin, specification=candidate_document())
    assert CANDIDATE_VERSION in caught.value.message_ko


def test_a_document_not_authored_as_published_cannot_be_published(
    db: Session, tenant: Tenant
) -> None:
    document = candidate_document()
    document["status"] = "DRAFT"
    version = _approved(db, tenant, document)

    with pytest.raises(SpecificationRejectedError) as caught:
        service.publish(db, tenant.lab_admin, version.id)
    assert _has_hangul(caught.value.message_ko)


# --------------------------------------------------------------------------- #
# Reading a version
# --------------------------------------------------------------------------- #


def test_the_detail_view_carries_the_diff_against_the_published_baseline(
    db: Session, tenant: Tenant
) -> None:
    version = _draft(db, tenant)
    detail = service.read_detail(db, tenant.lab_admin, version.id)

    assert detail.spec.checksum == version.checksum
    assert detail.diff.baseline_version == "1.0.0"
    alpha_line = next(line for line in detail.diff.lines_ko() if "alpha" in line)
    assert "60" in alpha_line and "70" in alpha_line
    assert detail.validation.ok
    assert detail.golden is None


def test_the_detail_view_carries_the_recorded_golden_results(
    db: Session, tenant: Tenant
) -> None:
    version = _draft(db, tenant)
    service.run_golden(db, tenant.lab_admin, version.id)
    db.commit()

    detail = service.read_detail(db, tenant.lab_admin, version.id)
    assert detail.golden is not None
    assert detail.golden["all_passed"] is True
    assert detail.golden["spec_checksum"] == version.checksum


def test_listing_filters_by_spec_and_status(db: Session, tenant: Tenant) -> None:
    _draft(db, tenant)
    _draft(
        db,
        tenant,
        lab_document(version="1.4.0", status="PUBLISHED", weights=CANDIDATE_WEIGHTS),
    )

    rows, total = service.list_versions(
        db, tenant.lab_admin, spec_id=LAB_SPEC_ID, page=1, page_size=10
    )
    assert total == 2
    # Newest first: a reviewer opens the list to find what changed most recently.
    assert [row.semantic_version for row in rows] == ["1.4.0", "1.1.0"]

    rows, total = service.list_versions(
        db,
        tenant.lab_admin,
        spec_id=LAB_SPEC_ID,
        status=SpecStatus.PUBLISHED,
        page=1,
        page_size=10,
    )
    assert total == 0


def test_an_unknown_version_id_reads_as_absent(db: Session, tenant: Tenant) -> None:
    assert service.get_version(db, tenant.lab_admin, uuid.uuid4()) is None


# --------------------------------------------------------------------------- #
# Permissions
# --------------------------------------------------------------------------- #


def test_an_analyst_cannot_author_or_publish(db: Session, tenant: Tenant) -> None:
    version = _approved(db, tenant)

    with pytest.raises(PermissionDeniedError):
        service.create_draft(db, tenant.analyst, specification=candidate_document())
    with pytest.raises(PermissionDeniedError):
        service.publish(db, tenant.analyst, version.id)
    with pytest.raises(PermissionDeniedError):
        service.approve(db, tenant.analyst, version.id)


def test_an_analyst_may_read_a_version(db: Session, tenant: Tenant) -> None:
    version = _draft(db, tenant)
    detail = service.read_detail(db, tenant.analyst, version.id)
    assert detail.version.id == version.id
