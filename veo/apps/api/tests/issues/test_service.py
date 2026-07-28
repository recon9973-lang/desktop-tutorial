"""Persisted issue behaviour: identity across scans, transitions, verification, recurrence.

These tests talk to PostgreSQL because the questions they ask are questions about rows —
whether two scans produced one issue or two, whether a count survived a cycle, whether
another tenant's id is invisible. An in-memory double would answer all of them yes.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.issues.support import (
    BLOCKER_CHECK,
    CRITICAL_CHECK,
    MAJOR_CHECK,
    Tenant,
    requires_database,
)

from veo.collect.contract import IssueDraft
from veo.db.models.analysis import FixRecommendation, Issue, ScanRun, VerificationRun
from veo.db.models.identity import AuditLog, URLRecord
from veo.issues import service
from veo.issues.identity import issue_fingerprint
from veo.issues.lifecycle import IllegalTransitionError, IssueState
from veo.issues.verification import VerificationScopeError
from veo.organizations.errors import ReferenceNotFoundError
from veo.scoring import CheckStatus, ScoringSpec

pytestmark = [pytest.mark.requires_postgres, requires_database]


PAGE_A = "https://shop.example.com/a"
PAGE_B = "https://shop.example.com/b"


def draft(check_id: str, *urls: str, title: str = "정규 URL 선언 누락") -> IssueDraft:
    return IssueDraft(
        check_id=check_id,
        title_ko=title,
        summary_ko="해당 페이지에 rel=canonical이 없습니다.",
        affected_urls=urls,
        evidence_ids=("http_response:deadbeef",),
        remediation_ko="<link rel=\"canonical\">를 추가하세요.",
        remediation_owner="DEVELOPER",
        business_impact_ko="중복 색인으로 색인 예산이 낭비됩니다.",
        fix_example='<link rel="canonical" href="https://shop.example.com/a">',
        reverification_note_ko="해당 URL만 다시 수집해 canonical 존재 여부를 확인합니다.",
    )


def ingest(
    db: Session,
    tenant: Tenant,
    run: ScanRun,
    spec: ScoringSpec,
    *drafts: IssueDraft,
) -> list[service.IngestResult]:
    results = service.ingest_drafts(
        db,
        tenant.analyst,
        project_id=tenant.project_id,
        scan_run_id=run.id,
        drafts=drafts,
        spec=spec,
        request_id="req-ingest",
    )
    db.commit()
    return results


def drive_to_verifying(db: Session, tenant: Tenant, issue_id: uuid.UUID) -> None:
    service.transition_issue(
        db, tenant.analyst, issue_id, IssueState.IN_PROGRESS, request_id="req-1"
    )
    service.transition_issue(
        db, tenant.analyst, issue_id, IssueState.FIX_CLAIMED, request_id="req-2"
    )
    service.request_verification(db, tenant.analyst, issue_id, request_id="req-3")
    db.commit()


# --------------------------------------------------------------------------- #
# Ingest and identity
# --------------------------------------------------------------------------- #


def test_a_draft_becomes_an_issue_carrying_everything_the_console_needs(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A, PAGE_B))

    issue = result.issue
    assert result.created is True
    assert issue.check_id == CRITICAL_CHECK
    assert issue.state == IssueState.OPEN
    assert issue.title_ko == "정규 URL 선언 누락"
    assert issue.business_impact_ko
    assert issue.affected_url_count == 2
    assert set(issue.sample_urls) == {PAGE_A, PAGE_B}
    assert issue.evidence_ids == ["http_response:deadbeef"]
    assert issue.remediation_owner == "DEVELOPER"
    assert issue.first_seen_run_id == run.id
    assert issue.last_seen_run_id == run.id


def test_the_severity_comes_from_the_specification_and_not_from_the_collector(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> None:
    run = make_scan_run(org_a)
    [blocker] = ingest(db, org_a, run, seo_spec, draft(BLOCKER_CHECK, PAGE_A))
    [major] = ingest(db, org_a, run, seo_spec, draft(MAJOR_CHECK, PAGE_A))

    assert blocker.issue.severity == str(seo_spec.check(BLOCKER_CHECK).severity)
    assert major.issue.severity == str(seo_spec.check(MAJOR_CHECK).severity)
    assert blocker.issue.severity != major.issue.severity


def test_a_check_the_specification_does_not_define_is_refused(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> None:
    """No spec entry means no severity, and a made-up severity is exactly what is banned."""
    run = make_scan_run(org_a)
    with pytest.raises(ReferenceNotFoundError):
        ingest(db, org_a, run, seo_spec, draft("seo.invented.check", PAGE_A))


def test_the_same_problem_found_in_two_scans_is_one_issue_with_history(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> None:
    monday = make_scan_run(org_a)
    friday = make_scan_run(org_a)

    [first] = ingest(db, org_a, monday, seo_spec, draft(CRITICAL_CHECK, PAGE_A, PAGE_B))
    [second] = ingest(
        db, org_a, friday, seo_spec, draft(CRITICAL_CHECK, PAGE_B, "HTTPS://shop.example.com:443/a")
    )

    assert second.created is False
    assert second.issue.id == first.issue.id
    assert second.issue.first_seen_run_id == monday.id
    assert second.issue.last_seen_run_id == friday.id

    rows = db.scalars(select(Issue).where(Issue.project_id == org_a.project_id)).all()
    assert len(rows) == 1


def test_a_different_affected_url_set_is_a_different_issue(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> None:
    run = make_scan_run(org_a)
    ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))
    ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A, PAGE_B))

    rows = db.scalars(select(Issue).where(Issue.project_id == org_a.project_id)).all()
    assert len(rows) == 2


def test_the_stored_issue_reproduces_its_own_fingerprint(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_B, PAGE_A))
    assert service.fingerprint_of_issue(result.issue) == issue_fingerprint(
        CRITICAL_CHECK, [PAGE_A, PAGE_B]
    )


def test_the_fix_recommendation_carries_the_remediation_and_the_reverification_rule(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))

    recommendation = db.scalars(
        select(FixRecommendation).where(FixRecommendation.issue_id == result.issue.id)
    ).one()
    assert recommendation.summary_ko
    assert recommendation.developer_steps_ko
    assert recommendation.code_example
    assert recommendation.generated_by == "RULE"
    rule = recommendation.reverification_rule
    assert rule["check_id"] == CRITICAL_CHECK
    assert rule["urls"] == [PAGE_A]
    assert rule["note_ko"]


# --------------------------------------------------------------------------- #
# Human transitions
# --------------------------------------------------------------------------- #


def test_a_person_may_acknowledge_and_claim_a_fix(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))

    service.transition_issue(
        db, org_a.analyst, result.issue.id, IssueState.IN_PROGRESS, request_id="r"
    )
    issue = service.transition_issue(
        db, org_a.analyst, result.issue.id, IssueState.FIX_CLAIMED, request_id="r"
    )
    db.commit()
    assert issue.state == IssueState.FIX_CLAIMED


def test_a_person_cannot_mark_an_issue_verified_resolved(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))
    drive_to_verifying(db, org_a, result.issue.id)

    with pytest.raises(IllegalTransitionError):
        service.transition_issue(
            db, org_a.analyst, result.issue.id, IssueState.VERIFIED_RESOLVED, request_id="r"
        )
    db.rollback()
    assert service.get_issue(db, org_a.analyst, result.issue.id).state == IssueState.VERIFYING


def test_a_rejected_transition_leaves_the_row_untouched(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))

    with pytest.raises(IllegalTransitionError):
        service.transition_issue(
            db, org_a.analyst, result.issue.id, IssueState.VERIFYING, request_id="r"
        )
    db.rollback()
    assert service.get_issue(db, org_a.analyst, result.issue.id).state == IssueState.OPEN


def test_every_transition_leaves_an_audit_row(
    db: Session,
    org_a: Tenant,
    make_scan_run: Callable[..., ScanRun],
    seo_spec: ScoringSpec,
    audit_rows: Callable[[uuid.UUID], list[AuditLog]],
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))
    service.transition_issue(
        db, org_a.analyst, result.issue.id, IssueState.ACKNOWLEDGED, request_id="req-x"
    )
    db.commit()

    transitions = [
        row
        for row in audit_rows(org_a.organization_id)
        if row.action == "issue.transition" and row.target_id == str(result.issue.id)
    ]
    assert transitions
    assert transitions[-1].detail["from"] == IssueState.OPEN
    assert transitions[-1].detail["to"] == IssueState.ACKNOWLEDGED
    assert transitions[-1].detail["trigger"] == "HUMAN"


def test_assigning_an_issue_records_the_owner(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))
    issue = service.assign_issue(
        db, org_a.analyst, result.issue.id, org_a.analyst.user_id, request_id="r"
    )
    db.commit()
    assert issue.assigned_to == org_a.analyst.user_id


# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #


def test_verification_cannot_be_requested_before_a_fix_is_claimed(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))
    with pytest.raises(IllegalTransitionError):
        service.request_verification(db, org_a.analyst, result.issue.id, request_id="r")
    db.rollback()


def test_a_verification_request_names_only_the_affected_urls_and_one_check(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A, PAGE_B))
    service.transition_issue(
        db, org_a.analyst, result.issue.id, IssueState.IN_PROGRESS, request_id="r"
    )
    service.transition_issue(
        db, org_a.analyst, result.issue.id, IssueState.FIX_CLAIMED, request_id="r"
    )
    issue, request = service.request_verification(
        db, org_a.analyst, result.issue.id, request_id="r"
    )
    db.commit()

    assert issue.state == IssueState.VERIFYING
    assert request.check_id == CRITICAL_CHECK
    assert set(request.target_urls) == {PAGE_A, PAGE_B}


def test_a_passing_re_scan_is_what_resolves_an_issue(
    db: Session,
    org_a: Tenant,
    make_scan_run: Callable[..., ScanRun],
    make_url_record: Callable[..., URLRecord],
    make_check_result: Callable[..., object],
    seo_spec: ScoringSpec,
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))
    drive_to_verifying(db, org_a, result.issue.id)

    rescan = make_scan_run(org_a)
    record = make_url_record(org_a, PAGE_A)
    make_check_result(org_a, rescan, CRITICAL_CHECK, CheckStatus.PASS, url_record=record)

    issue, verification = service.record_verification_outcome(
        db, org_a.analyst, result.issue.id, scan_run_id=rescan.id, request_id="r"
    )
    db.commit()

    assert issue.state == IssueState.VERIFIED_RESOLVED
    assert verification.outcome == "RESOLVED"
    assert verification.scan_run_id == rescan.id
    assert verification.detail["check_id"] == CRITICAL_CHECK


def test_a_failing_re_scan_lands_in_verification_failed_not_open(
    db: Session,
    org_a: Tenant,
    make_scan_run: Callable[..., ScanRun],
    make_url_record: Callable[..., URLRecord],
    make_check_result: Callable[..., object],
    seo_spec: ScoringSpec,
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))
    drive_to_verifying(db, org_a, result.issue.id)

    rescan = make_scan_run(org_a)
    record = make_url_record(org_a, PAGE_A)
    make_check_result(org_a, rescan, CRITICAL_CHECK, CheckStatus.FAIL, url_record=record)

    issue, verification = service.record_verification_outcome(
        db, org_a.analyst, result.issue.id, scan_run_id=rescan.id, request_id="r"
    )
    db.commit()

    assert issue.state == IssueState.VERIFICATION_FAILED
    assert verification.outcome == "STILL_FAILING"


def test_a_re_scan_that_never_measured_the_check_cannot_resolve_anything(
    db: Session,
    org_a: Tenant,
    make_scan_run: Callable[..., ScanRun],
    seo_spec: ScoringSpec,
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))
    drive_to_verifying(db, org_a, result.issue.id)

    empty_rescan = make_scan_run(org_a)
    issue, verification = service.record_verification_outcome(
        db, org_a.analyst, result.issue.id, scan_run_id=empty_rescan.id, request_id="r"
    )
    db.commit()

    assert verification.outcome == "INCONCLUSIVE"
    assert issue.state == IssueState.FIX_CLAIMED


def test_an_outcome_cannot_be_recorded_before_verification_was_requested(
    db: Session,
    org_a: Tenant,
    make_scan_run: Callable[..., ScanRun],
    make_url_record: Callable[..., URLRecord],
    make_check_result: Callable[..., object],
    seo_spec: ScoringSpec,
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))

    rescan = make_scan_run(org_a)
    record = make_url_record(org_a, PAGE_A)
    make_check_result(org_a, rescan, CRITICAL_CHECK, CheckStatus.PASS, url_record=record)

    with pytest.raises(IllegalTransitionError):
        service.record_verification_outcome(
            db, org_a.analyst, result.issue.id, scan_run_id=rescan.id, request_id="r"
        )
    db.rollback()
    assert service.get_issue(db, org_a.analyst, result.issue.id).state == IssueState.OPEN
    assert not db.scalars(
        select(VerificationRun).where(VerificationRun.issue_id == result.issue.id)
    ).all()


def test_another_tenants_scan_run_cannot_be_used_as_evidence(
    db: Session,
    org_a: Tenant,
    org_b: Tenant,
    make_scan_run: Callable[..., ScanRun],
    make_url_record: Callable[..., URLRecord],
    make_check_result: Callable[..., object],
    seo_spec: ScoringSpec,
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))
    drive_to_verifying(db, org_a, result.issue.id)

    foreign = make_scan_run(org_b)
    record = make_url_record(org_b, PAGE_A)
    make_check_result(org_b, foreign, CRITICAL_CHECK, CheckStatus.PASS, url_record=record)

    with pytest.raises(ReferenceNotFoundError):
        service.record_verification_outcome(
            db, org_a.analyst, result.issue.id, scan_run_id=foreign.id, request_id="r"
        )
    db.rollback()


def test_a_site_wide_issue_with_no_urls_cannot_request_verification(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK))
    service.transition_issue(
        db, org_a.analyst, result.issue.id, IssueState.IN_PROGRESS, request_id="r"
    )
    service.transition_issue(
        db, org_a.analyst, result.issue.id, IssueState.FIX_CLAIMED, request_id="r"
    )
    with pytest.raises(VerificationScopeError):
        service.request_verification(db, org_a.analyst, result.issue.id, request_id="r")
    db.rollback()


# --------------------------------------------------------------------------- #
# Recurrence
# --------------------------------------------------------------------------- #


def resolve_once(
    db: Session,
    tenant: Tenant,
    issue_id: uuid.UUID,
    make_scan_run: Callable[..., ScanRun],
    make_url_record: Callable[..., URLRecord],
    make_check_result: Callable[..., object],
) -> None:
    drive_to_verifying(db, tenant, issue_id)
    rescan = make_scan_run(tenant)
    record = make_url_record(tenant, PAGE_A)
    make_check_result(tenant, rescan, CRITICAL_CHECK, CheckStatus.PASS, url_record=record)
    service.record_verification_outcome(
        db, tenant.analyst, issue_id, scan_run_id=rescan.id, request_id="r"
    )
    db.commit()


def test_a_resolved_issue_found_again_recurs_and_increments_the_count(
    db: Session,
    org_a: Tenant,
    make_scan_run: Callable[..., ScanRun],
    make_url_record: Callable[..., URLRecord],
    make_check_result: Callable[..., object],
    seo_spec: ScoringSpec,
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))
    resolve_once(db, org_a, result.issue.id, make_scan_run, make_url_record, make_check_result)

    later = make_scan_run(org_a)
    [again] = ingest(db, org_a, later, seo_spec, draft(CRITICAL_CHECK, PAGE_A))

    assert again.issue.id == result.issue.id
    assert again.recurred is True
    assert again.issue.state == IssueState.RECURRED
    assert again.issue.regression_count == 1


def test_three_recurrences_are_a_different_conversation_from_one(
    db: Session,
    org_a: Tenant,
    make_scan_run: Callable[..., ScanRun],
    make_url_record: Callable[..., URLRecord],
    make_check_result: Callable[..., object],
    seo_spec: ScoringSpec,
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))
    issue_id = result.issue.id

    for _ in range(3):
        resolve_once(db, org_a, issue_id, make_scan_run, make_url_record, make_check_result)
        later = make_scan_run(org_a)
        ingest(db, org_a, later, seo_spec, draft(CRITICAL_CHECK, PAGE_A))

    detail = service.get_issue_detail(db, org_a.analyst, issue_id)
    assert detail is not None
    assert detail.issue.regression_count == 3
    assert detail.recurrence.count == 3
    assert len(detail.recurrence.cycles) == 4, "세 번 재발하면 주기는 네 개입니다"
    assert all(cycle.opened_at is not None for cycle in detail.recurrence.cycles)
    assert [cycle.resolved_at is not None for cycle in detail.recurrence.cycles] == [
        True,
        True,
        True,
        False,
    ]
    assert [cycle.recurred_at is not None for cycle in detail.recurrence.cycles] == [
        True,
        True,
        True,
        False,
    ]
    timestamps = [cycle.opened_at for cycle in detail.recurrence.cycles]
    assert timestamps == sorted(timestamps)


def test_an_unresolved_issue_seen_again_does_not_recur(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> None:
    first = make_scan_run(org_a)
    ingest(db, org_a, first, seo_spec, draft(CRITICAL_CHECK, PAGE_A))
    second = make_scan_run(org_a)
    [again] = ingest(db, org_a, second, seo_spec, draft(CRITICAL_CHECK, PAGE_A))

    assert again.recurred is False
    assert again.issue.state == IssueState.OPEN
    assert again.issue.regression_count == 0


# --------------------------------------------------------------------------- #
# Listing, detail and tenancy
# --------------------------------------------------------------------------- #


def test_issues_can_be_filtered_by_state_severity_owner_and_check(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> None:
    run = make_scan_run(org_a)
    ingest(db, org_a, run, seo_spec, draft(BLOCKER_CHECK, PAGE_A))
    [critical] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))
    service.transition_issue(
        db, org_a.analyst, critical.issue.id, IssueState.ACKNOWLEDGED, request_id="r"
    )
    db.commit()

    by_state, total = service.list_issues(
        db, org_a.analyst, states=[IssueState.ACKNOWLEDGED], page=1, page_size=20
    )
    assert total == 1
    assert by_state[0].id == critical.issue.id

    by_severity, _ = service.list_issues(
        db,
        org_a.analyst,
        severities=[str(seo_spec.check(BLOCKER_CHECK).severity)],
        page=1,
        page_size=20,
    )
    assert {row.check_id for row in by_severity} == {BLOCKER_CHECK}

    by_check, _ = service.list_issues(
        db, org_a.analyst, check_ids=[CRITICAL_CHECK], page=1, page_size=20
    )
    assert {row.check_id for row in by_check} == {CRITICAL_CHECK}

    by_owner, _ = service.list_issues(
        db, org_a.analyst, remediation_owners=["MARKETER"], page=1, page_size=20
    )
    assert by_owner == []


def test_the_detail_view_carries_the_full_history(
    db: Session,
    org_a: Tenant,
    make_scan_run: Callable[..., ScanRun],
    make_url_record: Callable[..., URLRecord],
    make_check_result: Callable[..., object],
    seo_spec: ScoringSpec,
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))
    resolve_once(db, org_a, result.issue.id, make_scan_run, make_url_record, make_check_result)

    detail = service.get_issue_detail(db, org_a.analyst, result.issue.id)
    assert detail is not None
    assert detail.recommendation is not None
    assert len(detail.verification_runs) == 1
    assert detail.verification_runs[0].outcome == "RESOLVED"
    assert [entry.to_state for entry in detail.history][-1] == IssueState.VERIFIED_RESOLVED
    assert detail.summary_ko
    assert not detail.summary_ko.isascii()


def test_another_organizations_issue_is_simply_not_there(
    db: Session, org_a: Tenant, org_b: Tenant, make_scan_run: Callable[..., ScanRun],
    seo_spec: ScoringSpec
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))

    assert service.get_issue(db, org_b.analyst, result.issue.id) is None
    assert service.get_issue_detail(db, org_b.analyst, result.issue.id) is None
    rows, total = service.list_issues(db, org_b.analyst, page=1, page_size=20)
    assert rows == [] and total == 0


def test_an_issue_id_from_another_organization_cannot_be_transitioned(
    db: Session, org_a: Tenant, org_b: Tenant, make_scan_run: Callable[..., ScanRun],
    seo_spec: ScoringSpec
) -> None:
    run = make_scan_run(org_a)
    [result] = ingest(db, org_a, run, seo_spec, draft(CRITICAL_CHECK, PAGE_A))
    with pytest.raises(ReferenceNotFoundError):
        service.transition_issue(
            db, org_b.analyst, result.issue.id, IssueState.ACKNOWLEDGED, request_id="r"
        )
    db.rollback()


def test_ingesting_into_another_organizations_project_is_refused(
    db: Session, org_a: Tenant, org_b: Tenant, make_scan_run: Callable[..., ScanRun],
    seo_spec: ScoringSpec
) -> None:
    run = make_scan_run(org_a)
    with pytest.raises(ReferenceNotFoundError):
        service.ingest_drafts(
            db,
            org_b.analyst,
            project_id=org_a.project_id,
            scan_run_id=run.id,
            drafts=[draft(CRITICAL_CHECK, PAGE_A)],
            spec=seo_spec,
            request_id="r",
        )
    db.rollback()
