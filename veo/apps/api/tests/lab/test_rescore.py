"""Re-scoring stored results under a new version.

Rule 2: both numbers survive. The original row is not touched, the recomputed value lands
in a new row, and each one carries the specification version and checksum that produced
it. A methodology change that quietly rewrote its own history would be unfalsifiable.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from tests.lab.support import (
    BASELINE_VERSION,
    CANDIDATE_VERSION,
    LAB_SPEC_ID,
    SCORES_UNDER_BASELINE,
    SCORES_UNDER_CANDIDATE,
    Tenant,
    candidate_document,
    outcomes_for,
    score_rows,
    seed_score,
    snapshot,
)

from veo.authz.errors import PermissionDeniedError
from veo.db.models.analysis import ScoreResult as ScoreResultRow
from veo.db.models.analysis import ScoringVersion
from veo.lab import rescore, service
from veo.lab.errors import IllegalTransitionError
from veo.scoring import CheckStatus, ScoringSpec, build_spec, evaluate, load_spec

TOLERANCE = 1e-6


def _has_hangul(text: str) -> bool:
    return any("가" <= character <= "힣" for character in text)


@pytest.fixture
def baseline_spec() -> ScoringSpec:
    return load_spec(LAB_SPEC_ID, BASELINE_VERSION)


@pytest.fixture
def published(db: Session, tenant: Tenant) -> ScoringVersion:
    version = service.create_draft(
        db, tenant.lab_admin, specification=candidate_document(), changelog="배점 이동"
    )
    db.commit()
    service.run_golden(db, tenant.lab_admin, version.id)
    db.commit()
    service.submit_for_review(db, tenant.lab_admin, version.id)
    db.commit()
    service.approve(db, tenant.lab_admin, version.id)
    db.commit()
    service.publish(db, tenant.lab_admin, version.id)
    db.commit()
    return version


# --------------------------------------------------------------------------- #
# Reconstructing the inputs
# --------------------------------------------------------------------------- #


def test_outcomes_are_rebuilt_from_the_stored_trace(baseline_spec: ScoringSpec) -> None:
    original = evaluate(baseline_spec, outcomes_for(baseline_spec, ("lab.alpha.two",)))
    rebuilt = rescore.outcomes_from_trace(baseline_spec, original.trace)

    assert {o.check_id for o in rebuilt} == set(baseline_spec.check_ids)
    by_id = {o.check_id: o for o in rebuilt}
    assert by_id["lab.alpha.two"].status is CheckStatus.FAIL
    assert by_id["lab.alpha.one"].status is CheckStatus.PASS

    replayed = evaluate(baseline_spec, rebuilt)
    assert replayed.overall_score == pytest.approx(original.overall_score, abs=TOLERANCE)


def test_a_check_the_old_run_never_measured_becomes_unknown_not_a_failure(
    baseline_spec: ScoringSpec,
) -> None:
    original = evaluate(baseline_spec, outcomes_for(baseline_spec))

    document = candidate_document()
    document["categories"][1]["checks"].append(
        {
            "id": "lab.beta.three",
            "title_ko": "새로 추가된 점검",
            "title_en": "new check",
            "severity": "MAJOR",
            "scope": "URL",
            "remediation_owner": "DEVELOPER",
        }
    )
    candidate = build_spec(document)

    rebuilt = rescore.outcomes_from_trace(candidate, original.trace)
    added = next(o for o in rebuilt if o.check_id == "lab.beta.three")
    assert added.status is CheckStatus.UNKNOWN

    replayed = evaluate(candidate, rebuilt)
    assert replayed.overall_score == pytest.approx(100.0, abs=TOLERANCE)
    assert replayed.coverage < 1.0


# --------------------------------------------------------------------------- #
# Writing the recomputed row
# --------------------------------------------------------------------------- #


def test_rescoring_writes_a_new_row_and_leaves_the_original_byte_identical(
    db: Session, tenant: Tenant, baseline_spec: ScoringSpec, published: ScoringVersion
) -> None:
    original = seed_score(
        db, tenant, baseline_spec, label="alpha-fail", failing=("lab.alpha.two",)
    )
    before = snapshot(original)
    assert original.score == pytest.approx(SCORES_UNDER_BASELINE["alpha_fail"], abs=TOLERANCE)

    summary = service.rescore(db, tenant.lab_admin, published.id)
    db.commit()

    assert summary.total == 1
    assert summary.fallen == 1

    db.expire_all()
    rows = _rows_for(db, original.scan_run_id)
    assert len(rows) == 2

    survivor = next(row for row in rows if row.id == original.id)
    assert snapshot(survivor) == before

    recomputed = next(row for row in rows if row.id != original.id)
    assert recomputed.recomputed_from_score_result_id == original.id
    assert recomputed.spec_version == CANDIDATE_VERSION
    assert recomputed.spec_checksum == published.checksum
    assert recomputed.score == pytest.approx(
        SCORES_UNDER_CANDIDATE["alpha_fail"], abs=TOLERANCE
    )


def test_both_scores_stay_retrievable_with_their_version_and_checksum(
    db: Session, tenant: Tenant, baseline_spec: ScoringSpec, published: ScoringVersion
) -> None:
    original = seed_score(
        db, tenant, baseline_spec, label="alpha-fail", failing=("lab.alpha.two",)
    )
    service.rescore(db, tenant.lab_admin, published.id)
    db.commit()
    db.expire_all()

    history = service.score_history(db, tenant.lab_admin, original.scan_run_id)
    labelled = {
        (row.spec_version, row.spec_checksum): row.score for row in history
    }
    assert len(labelled) == 2
    assert labelled[(BASELINE_VERSION, baseline_spec.checksum)] == pytest.approx(
        SCORES_UNDER_BASELINE["alpha_fail"], abs=TOLERANCE
    )
    assert labelled[(CANDIDATE_VERSION, published.checksum)] == pytest.approx(
        SCORES_UNDER_CANDIDATE["alpha_fail"], abs=TOLERANCE
    )


def test_the_korean_summary_counts_risen_fallen_and_unchanged(
    db: Session, tenant: Tenant, baseline_spec: ScoringSpec, published: ScoringVersion
) -> None:
    seed_score(db, tenant, baseline_spec, label="down", failing=("lab.alpha.two",))
    seed_score(db, tenant, baseline_spec, label="up", failing=("lab.beta.one",))
    seed_score(db, tenant, baseline_spec, label="flat")

    summary = service.rescore(db, tenant.lab_admin, published.id)
    db.commit()

    assert summary.total == 3
    assert summary.risen == 1
    assert summary.fallen == 1
    assert summary.unchanged == 1
    assert summary.max_rise == pytest.approx(
        SCORES_UNDER_CANDIDATE["beta_fail"] - SCORES_UNDER_BASELINE["beta_fail"],
        abs=TOLERANCE,
    )
    assert summary.max_fall == pytest.approx(
        SCORES_UNDER_CANDIDATE["alpha_fail"] - SCORES_UNDER_BASELINE["alpha_fail"],
        abs=TOLERANCE,
    )

    text = summary.summary_ko()
    assert _has_hangul(text)
    assert "3" in text and "상승" in text and "하락" in text


def test_rescoring_twice_does_not_duplicate_a_row(
    db: Session, tenant: Tenant, baseline_spec: ScoringSpec, published: ScoringVersion
) -> None:
    original = seed_score(
        db, tenant, baseline_spec, label="alpha-fail", failing=("lab.alpha.two",)
    )
    service.rescore(db, tenant.lab_admin, published.id)
    db.commit()

    again = service.rescore(db, tenant.lab_admin, published.id)
    db.commit()
    assert again.total == 0
    assert again.skipped == 1

    db.expire_all()
    assert len(_rows_for(db, original.scan_run_id)) == 2


def test_rescoring_only_touches_the_callers_organization(
    db: Session,
    tenant: Tenant,
    other_tenant: Tenant,
    baseline_spec: ScoringSpec,
    published: ScoringVersion,
) -> None:
    mine = seed_score(db, tenant, baseline_spec, label="mine", failing=("lab.alpha.two",))
    theirs = seed_score(
        db, other_tenant, baseline_spec, label="theirs", failing=("lab.alpha.two",)
    )

    summary = service.rescore(db, tenant.lab_admin, published.id)
    db.commit()
    db.expire_all()

    assert summary.total == 1
    assert len(_rows_for(db, mine.scan_run_id)) == 2
    assert len(_rows_for(db, theirs.scan_run_id)) == 1


def test_rescoring_can_be_limited_to_named_runs(
    db: Session, tenant: Tenant, baseline_spec: ScoringSpec, published: ScoringVersion
) -> None:
    picked = seed_score(db, tenant, baseline_spec, label="picked", failing=("lab.alpha.two",))
    skipped = seed_score(db, tenant, baseline_spec, label="skipped", failing=("lab.alpha.two",))

    summary = service.rescore(
        db, tenant.lab_admin, published.id, scan_run_ids=[picked.scan_run_id]
    )
    db.commit()
    db.expire_all()

    assert summary.total == 1
    assert len(_rows_for(db, picked.scan_run_id)) == 2
    assert len(_rows_for(db, skipped.scan_run_id)) == 1


# --------------------------------------------------------------------------- #
# Guards
# --------------------------------------------------------------------------- #


def test_only_a_published_version_may_rescore(db: Session, tenant: Tenant) -> None:
    version = service.create_draft(
        db, tenant.lab_admin, specification=candidate_document()
    )
    db.commit()
    with pytest.raises(IllegalTransitionError) as caught:
        service.rescore(db, tenant.lab_admin, version.id)
    assert _has_hangul(caught.value.message_ko)


def test_an_analyst_cannot_trigger_a_rescore(
    db: Session, tenant: Tenant, published: ScoringVersion
) -> None:
    with pytest.raises(PermissionDeniedError):
        service.rescore(db, tenant.analyst, published.id)


def _rows_for(db: Session, scan_run_id: uuid.UUID) -> list[ScoreResultRow]:
    return score_rows(db, scan_run_id)
