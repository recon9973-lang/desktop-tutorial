"""Issue persistence: ingest, identity, transitions, verification and recurrence.

Three rules run through every function here.

*Tenant scope is structural.* Every statement is built with
:func:`veo.authz.tenant_select` and checked by :func:`veo.authz.assert_tenant_scoped`
before it runs. Another organization's issue id, project id or scan run id is not an
error to be reported — it is simply not found, and says so in exactly the words an id
that exists nowhere produces.

*Severity is never invented.* It is looked up from the published specification by
``check_id``. A collector that proposed a severity would be overruled; a ``check_id`` the
specification does not define is refused outright, because an issue with no severity in
the spec is an issue whose priority nobody agreed on.

*Resolution comes from measurement.* :func:`transition_issue` is the human door and it is
hard-wired to the ``HUMAN`` trigger, which appears on no edge into ``VERIFIED_RESOLVED``.
:func:`record_verification_outcome` is the measured door and it does not accept a verdict
from its caller — it reads the persisted ``check_results`` of a re-scan the caller's own
organization owns, and derives one.

Where things are stored, given a schema this module does not own and may not extend:

======================  ==========================================================
``issues``              identity (``check_id`` + ``sample_urls``), state, severity,
                        owner, recurrence count, first/last scan run
``fix_recommendations`` the remediation text and the re-verification rule
``verification_runs``   every re-measurement and what it concluded (append-only)
``audit_logs``          every state change and every recurrence (append-only)
======================  ==========================================================

``issues.sample_urls`` holds the **complete** normalised affected URL set, not a sample.
That is what makes the fingerprint recomputable from the row, which in turn is what
keeps identity from needing a second, driftable copy anywhere.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.collect.contract import IssueDraft
from veo.collect.evidence import resolve_evidence
from veo.db.models.analysis import (
    CheckResult,
    Evidence,
    FixRecommendation,
    Issue,
    ScanRun,
    VerificationRun,
)
from veo.db.models.identity import AuditLog, Project, RoleAssignment
from veo.issues import recurrence as recurrence_module
from veo.issues.identity import fingerprint_of_draft, issue_fingerprint, normalize_affected_urls
from veo.issues.lifecycle import (
    IllegalTransitionError,
    IssueState,
    TransitionTrigger,
    allowed_targets,
    assert_transition,
    describe_state_ko,
    parse_state,
    state_for_outcome,
)
from veo.issues.recurrence import RecurrenceHistory
from veo.issues.verification import (
    MeasuredCheck,
    VerificationRequest,
    build_verification_request,
    derive_outcome,
)
from veo.organizations import audit
from veo.organizations.errors import ReferenceNotFoundError
from veo.scoring import CheckStatus, ScoringSpec, SpecCheck

TARGET_TYPE = "issue"

CREATE_ACTION = "issue.create"
TRANSITION_ACTION = "issue.transition"
ASSIGN_ACTION = "issue.assign"
OBSERVE_ACTION = "issue.observed"

#: Every action this module writes to the audit trail, which is also the issue's history.
HISTORY_ACTIONS: frozenset[str] = frozenset(
    {
        CREATE_ACTION,
        TRANSITION_ACTION,
        ASSIGN_ACTION,
        OBSERVE_ACTION,
        recurrence_module.RECURRENCE_ACTION,
    }
)

#: Mirrors ``SpecCheck.remediation_owner``. A value outside this set would be an owner
#: type no console filter knows about, so it is refused at the door.
REMEDIATION_OWNERS: frozenset[str] = frozenset(
    {"DEVELOPER", "MARKETER", "BUSINESS_OWNER", "OPERATIONS"}
)

NOT_FOUND_KO = "이슈를 찾을 수 없습니다."
PROJECT_NOT_FOUND_KO = "프로젝트를 찾을 수 없습니다."
SCAN_RUN_NOT_FOUND_KO = "진단 실행 기록을 찾을 수 없습니다."
ASSIGNEE_NOT_FOUND_KO = "담당자로 지정할 사용자를 찾을 수 없습니다."


# --------------------------------------------------------------------------- #
# Read models
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class IngestResult:
    """What one collector finding did to the issue table."""

    issue: Issue
    fingerprint: str
    created: bool
    recurred: bool


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """One line of an issue's history, taken from the append-only audit trail."""

    at: datetime
    action: str
    from_state: IssueState | None
    to_state: IssueState | None
    trigger: str | None
    actor_user_id: uuid.UUID | None
    request_id: str | None
    summary_ko: str


@dataclass(frozen=True, slots=True)
class IssueDetail:
    """Everything the console shows on one issue, history included."""

    issue: Issue
    fingerprint: str
    affected_urls: tuple[str, ...]
    recommendation: FixRecommendation | None
    verification_runs: tuple[VerificationRun, ...]
    history: tuple[HistoryEntry, ...]
    recurrence: RecurrenceHistory
    summary_ko: str
    #: 이 지적이 부르는 근거 중 **실제로 찾아진** 것.
    #:
    #: 요청한 이름과 개수가 다를 수 있고, 그 차이를 감추지 않는다 — 근거가 몇 개
    #: 사라졌는지는 지적의 신뢰도에 대한 정보다.
    evidence: tuple[Evidence, ...] = ()


# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #


def fingerprint_of_issue(issue: Issue) -> str:
    """Recompute a stored issue's fingerprint from the row itself."""
    return issue_fingerprint(issue.check_id, list(issue.sample_urls or []))


def affected_urls_of(issue: Issue) -> tuple[str, ...]:
    return normalize_affected_urls(issue.sample_urls or [])


# --------------------------------------------------------------------------- #
# Ingest
# --------------------------------------------------------------------------- #


def ingest_drafts(
    session: Session,
    principal: Principal,
    *,
    project_id: uuid.UUID,
    scan_run_id: uuid.UUID,
    drafts: Sequence[IssueDraft],
    spec: ScoringSpec,
    request_id: str | None = None,
) -> list[IngestResult]:
    """Persist a scan's findings, folding each one onto the issue it already is.

    A finding that matches an existing fingerprint updates that issue's evidence and its
    ``last_seen_run_id``; it never creates a second row. If the issue it matches was
    previously verified resolved, the match is a recurrence and is recorded as one.
    """
    project = _require_project(session, principal, project_id)
    scan_run = _require_scan_run(session, principal, scan_run_id)

    results: list[IngestResult] = []
    for draft in drafts:
        check = _require_spec_check(spec, draft.check_id)
        fingerprint = fingerprint_of_draft(draft)
        existing = _find_by_fingerprint(
            session, principal, project_id=project.id, check_id=draft.check_id,
            fingerprint=fingerprint,
        )
        if existing is None:
            issue = _create_issue(
                session,
                principal,
                project_id=project.id,
                scan_run=scan_run,
                draft=draft,
                severity=str(check.severity),
                remediation_owner=_owner_of(draft, str(check.remediation_owner)),
                request_id=request_id,
            )
            results.append(
                IngestResult(issue=issue, fingerprint=fingerprint, created=True, recurred=False)
            )
            continue

        recurred = recurrence_module.has_recurred(existing)
        _refresh_issue(existing, draft, severity=str(check.severity))
        existing.last_seen_run_id = scan_run.id
        _upsert_recommendation(session, principal, existing, draft)

        if recurred:
            recurrence_module.mark_recurred(
                session, principal, existing, scan_run=scan_run, request_id=request_id
            )
        else:
            audit.record(
                session,
                principal,
                action=OBSERVE_ACTION,
                target_type=TARGET_TYPE,
                target_id=existing.id,
                request_id=request_id,
                detail={"check_id": existing.check_id, "scan_run_id": str(scan_run.id)},
            )
        session.flush()
        results.append(
            IngestResult(
                issue=existing, fingerprint=fingerprint, created=False, recurred=recurred
            )
        )

    return results


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #


def list_issues(
    session: Session,
    principal: Principal,
    *,
    project_id: uuid.UUID | None = None,
    states: Sequence[str] | None = None,
    severities: Sequence[str] | None = None,
    remediation_owners: Sequence[str] | None = None,
    check_ids: Sequence[str] | None = None,
    assigned_to: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Issue], int]:
    """Filtered, paginated issues inside the caller's organization."""
    statement = _filtered(
        tenant_select(Issue, principal),
        project_id=project_id,
        states=states,
        severities=severities,
        remediation_owners=remediation_owners,
        check_ids=check_ids,
        assigned_to=assigned_to,
    )
    assert_tenant_scoped(statement, principal.organization_id)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0

    page_statement = (
        statement.order_by(Issue.created_at, Issue.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    assert_tenant_scoped(page_statement, principal.organization_id)
    return list(session.scalars(page_statement)), total


def get_issue(session: Session, principal: Principal, issue_id: uuid.UUID) -> Issue | None:
    statement = tenant_select(Issue, principal).where(Issue.id == issue_id)
    assert_tenant_scoped(statement, principal.organization_id)
    return session.scalars(statement).one_or_none()


def require_issue(session: Session, principal: Principal, issue_id: uuid.UUID) -> Issue:
    issue = get_issue(session, principal, issue_id)
    if issue is None:
        raise ReferenceNotFoundError(NOT_FOUND_KO)
    return issue


def get_issue_detail(
    session: Session, principal: Principal, issue_id: uuid.UUID
) -> IssueDetail | None:
    issue = get_issue(session, principal, issue_id)
    if issue is None:
        return None

    recommendation = _recommendation_for(session, principal, issue)
    runs = _verification_runs(session, principal, issue)
    rows = _audit_rows(session, principal, issue)
    history = recurrence_module.build_history(issue, runs, rows)

    return IssueDetail(
        issue=issue,
        fingerprint=fingerprint_of_issue(issue),
        affected_urls=affected_urls_of(issue),
        recommendation=recommendation,
        verification_runs=runs,
        history=tuple(_history_entry(row) for row in rows),
        recurrence=history,
        summary_ko=summarize_issue(issue),
        evidence=tuple(_evidence_for(session, principal, issue)),
    )


def _evidence_for(session: Session, principal: Principal, issue: Issue) -> list[Evidence]:
    """이 지적을 뒷받침한 자료. 마지막으로 이 문제가 관측된 실행에서 찾는다.

    이슈는 실행마다 새로 만들지 않고 이어 붙이므로, 지금 사람이 열어 볼 근거는 **가장
    최근에 이 문제가 잡힌 실행** 의 것이어야 한다. 처음 잡혔을 때의 자료를 보여주면
    반년 전 화면을 근거라고 내놓게 된다.
    """
    run_id = issue.last_seen_run_id
    if run_id is None:
        return []
    return resolve_evidence(
        session,
        principal=principal,
        scan_run_id=run_id,
        evidence_ids=[str(value) for value in (issue.evidence_ids or [])],
    )


def summarize_issue(issue: Issue) -> str:
    """One Korean sentence that never lets a claimed fix read as a resolved one."""
    state = parse_state(issue.state)
    parts = [
        f"[{issue.severity}] {issue.title_ko}",
        f"영향 URL {issue.affected_url_count}개",
        f"현재 상태: {describe_state_ko(state)}",
    ]
    if state is IssueState.FIX_CLAIMED:
        parts.append("담당자가 수정을 보고했을 뿐, 아직 재측정으로 확인되지 않았습니다.")
    elif state is IssueState.VERIFYING:
        parts.append("표적 재측정 결과를 기다리는 중입니다.")
    elif state is IssueState.VERIFICATION_FAILED:
        parts.append("재측정에서도 문제가 확인되었습니다.")
    elif state is IssueState.VERIFIED_RESOLVED:
        parts.append("표적 재측정에서 통과가 확인되어 해결로 기록되었습니다.")
    elif state is IssueState.WONT_FIX:
        parts.append("조치하지 않기로 한 결정이며, 문제가 사라졌다는 뜻은 아닙니다.")

    if issue.regression_count:
        parts.append(f"해결 확인 후 {issue.regression_count}회 재발했습니다.")
    return " · ".join(parts)


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #


def assign_issue(
    session: Session,
    principal: Principal,
    issue_id: uuid.UUID,
    assigned_to: uuid.UUID | None,
    *,
    request_id: str | None = None,
) -> Issue:
    """Route an issue to a member of the caller's own organization, or unassign it."""
    issue = require_issue(session, principal, issue_id)
    if assigned_to is not None:
        _require_member(session, principal, assigned_to)

    issue.assigned_to = assigned_to
    audit.record(
        session,
        principal,
        action=ASSIGN_ACTION,
        target_type=TARGET_TYPE,
        target_id=issue.id,
        request_id=request_id,
        detail={"assigned": assigned_to is not None},
    )
    session.flush()
    return issue


def transition_issue(
    session: Session,
    principal: Principal,
    issue_id: uuid.UUID,
    target: IssueState,
    *,
    request_id: str | None = None,
) -> Issue:
    """The human door into the state machine — hard-wired to the ``HUMAN`` trigger.

    Because no edge into ``VERIFIED_RESOLVED`` accepts that trigger, there is no request
    a person can make through this function that marks an issue resolved.
    """
    issue = require_issue(session, principal, issue_id)
    source = parse_state(issue.state)
    assert_transition(source, target, trigger=TransitionTrigger.HUMAN)
    return _apply_transition(
        session,
        principal,
        issue,
        source=source,
        target=target,
        trigger=TransitionTrigger.HUMAN,
        request_id=request_id,
    )


def request_verification(
    session: Session,
    principal: Principal,
    issue_id: uuid.UUID,
    *,
    request_id: str | None = None,
) -> tuple[Issue, VerificationRequest]:
    """Move an issue to ``VERIFYING`` and describe the narrow re-scan that will settle it."""
    issue = require_issue(session, principal, issue_id)
    source = parse_state(issue.state)
    assert_transition(
        source, IssueState.VERIFYING, trigger=TransitionTrigger.VERIFICATION_REQUEST
    )

    request = build_verification_request(issue)
    updated = _apply_transition(
        session,
        principal,
        issue,
        source=source,
        target=IssueState.VERIFYING,
        trigger=TransitionTrigger.VERIFICATION_REQUEST,
        request_id=request_id,
        detail={"check_id": request.check_id, "target_url_count": len(request.target_urls)},
    )
    return updated, request


def record_verification_outcome(
    session: Session,
    principal: Principal,
    issue_id: uuid.UUID,
    *,
    scan_run_id: uuid.UUID,
    request_id: str | None = None,
) -> tuple[Issue, VerificationRun]:
    """Read what a re-scan measured, record it, and let the measurement move the issue.

    The caller names a scan run. It does **not** name an outcome: the verdict is derived
    from the ``check_results`` that run persisted for this issue's check, so there is no
    request anyone can send that means "mark it resolved". Nothing is written until the
    move the verdict implies is known to be legal, which is why an issue that never
    entered ``VERIFYING`` leaves no verification run behind.
    """
    issue = require_issue(session, principal, issue_id)
    scan_run = _require_scan_run(session, principal, scan_run_id)

    source = parse_state(issue.state)
    _assert_awaiting_verification(source)

    measurements = _measurements_for(session, principal, issue, scan_run)
    verdict = derive_outcome(measurements, affected_urls=affected_urls_of(issue))
    target = state_for_outcome(verdict.outcome)
    assert_transition(
        source,
        target,
        trigger=TransitionTrigger.VERIFICATION_OUTCOME,
        outcome=verdict.outcome,
    )

    run = VerificationRun(
        organization_id=principal.organization_id,
        issue_id=issue.id,
        scan_run_id=scan_run.id,
        requested_by=None if principal.is_service_account else principal.user_id,
        outcome=str(verdict.outcome),
        detail={
            "check_id": issue.check_id,
            "reason_ko": verdict.reason_ko,
            **verdict.detail,
        },
    )
    session.add(run)

    updated = _apply_transition(
        session,
        principal,
        issue,
        source=source,
        target=target,
        trigger=TransitionTrigger.VERIFICATION_OUTCOME,
        request_id=request_id,
        detail={
            "outcome": str(verdict.outcome),
            "scan_run_id": str(scan_run.id),
            "check_id": issue.check_id,
        },
    )
    session.flush()
    return updated, run


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _filtered(
    statement: Select[tuple[Issue]],
    *,
    project_id: uuid.UUID | None,
    states: Sequence[str] | None,
    severities: Sequence[str] | None,
    remediation_owners: Sequence[str] | None,
    check_ids: Sequence[str] | None,
    assigned_to: uuid.UUID | None,
) -> Select[tuple[Issue]]:
    if project_id is not None:
        statement = statement.where(Issue.project_id == project_id)
    if states:
        statement = statement.where(Issue.state.in_([str(state) for state in states]))
    if severities:
        statement = statement.where(Issue.severity.in_([str(value) for value in severities]))
    if remediation_owners:
        statement = statement.where(
            Issue.remediation_owner.in_([str(value) for value in remediation_owners])
        )
    if check_ids:
        statement = statement.where(Issue.check_id.in_(list(check_ids)))
    if assigned_to is not None:
        statement = statement.where(Issue.assigned_to == assigned_to)
    return statement


def _require_project(session: Session, principal: Principal, project_id: uuid.UUID) -> Project:
    statement = tenant_select(Project, principal).where(Project.id == project_id)
    assert_tenant_scoped(statement, principal.organization_id)
    project = session.scalars(statement).one_or_none()
    if project is None:
        raise ReferenceNotFoundError(PROJECT_NOT_FOUND_KO)
    return project


def _require_scan_run(session: Session, principal: Principal, scan_run_id: uuid.UUID) -> ScanRun:
    statement = tenant_select(ScanRun, principal).where(ScanRun.id == scan_run_id)
    assert_tenant_scoped(statement, principal.organization_id)
    run = session.scalars(statement).one_or_none()
    if run is None:
        raise ReferenceNotFoundError(SCAN_RUN_NOT_FOUND_KO)
    return run


def _require_member(session: Session, principal: Principal, user_id: uuid.UUID) -> None:
    """A user is assignable only if they hold a role inside the caller's organization.

    The refusal is worded like any other missing reference, so probing ids cannot be used
    to learn who exists in some other organization.
    """
    statement = tenant_select(RoleAssignment, principal).where(RoleAssignment.user_id == user_id)
    assert_tenant_scoped(statement, principal.organization_id)
    if session.scalars(statement).first() is None:
        raise ReferenceNotFoundError(ASSIGNEE_NOT_FOUND_KO)


def _require_spec_check(spec: ScoringSpec, check_id: str) -> SpecCheck:
    try:
        return spec.check(check_id)
    except KeyError as exc:
        raise ReferenceNotFoundError(
            f"발행된 점수 명세에 없는 검사 ID입니다: {check_id}. "
            "명세에 없는 검사는 심각도를 정할 근거가 없어 이슈로 저장하지 않습니다."
        ) from exc


def _owner_of(draft: IssueDraft, spec_owner: str) -> str:
    owner = (draft.remediation_owner or "").strip().upper()
    return owner if owner in REMEDIATION_OWNERS else spec_owner


def _find_by_fingerprint(
    session: Session,
    principal: Principal,
    *,
    project_id: uuid.UUID,
    check_id: str,
    fingerprint: str,
) -> Issue | None:
    """Candidates are narrowed by project and check, then matched on the fingerprint.

    The fingerprint is not a column — it is derived from ``check_id`` and the stored URL
    set — so the final comparison happens here rather than in SQL. The candidate set is
    the issues of one check inside one project, which is small by construction.
    """
    statement = (
        tenant_select(Issue, principal)
        .where(Issue.project_id == project_id)
        .where(Issue.check_id == check_id)
    )
    assert_tenant_scoped(statement, principal.organization_id)
    for candidate in session.scalars(statement):
        if fingerprint_of_issue(candidate) == fingerprint:
            return candidate
    return None


def _create_issue(
    session: Session,
    principal: Principal,
    *,
    project_id: uuid.UUID,
    scan_run: ScanRun,
    draft: IssueDraft,
    severity: str,
    remediation_owner: str,
    request_id: str | None,
) -> Issue:
    urls = normalize_affected_urls(draft.affected_urls)
    issue = Issue(
        organization_id=principal.organization_id,
        project_id=project_id,
        first_seen_run_id=scan_run.id,
        last_seen_run_id=scan_run.id,
        check_id=draft.check_id,
        severity=severity,
        state=str(IssueState.OPEN),
        title_ko=draft.title_ko,
        business_impact_ko=draft.business_impact_ko or None,
        affected_url_count=len(urls),
        sample_urls=list(urls),
        evidence_ids=list(draft.evidence_ids),
        remediation_owner=remediation_owner,
        regression_count=0,
    )
    session.add(issue)
    session.flush()

    _upsert_recommendation(session, principal, issue, draft)
    audit.record(
        session,
        principal,
        action=CREATE_ACTION,
        target_type=TARGET_TYPE,
        target_id=issue.id,
        request_id=request_id,
        detail={
            "check_id": issue.check_id,
            "severity": severity,
            "affected_url_count": issue.affected_url_count,
            "scan_run_id": str(scan_run.id),
            "to": str(IssueState.OPEN),
        },
    )
    session.flush()
    return issue


def _refresh_issue(issue: Issue, draft: IssueDraft, *, severity: str) -> None:
    """Re-observing an issue refreshes what it says, never who it is.

    ``check_id`` and the URL set are the identity and are left alone — changing either
    would silently turn this row into a different problem while keeping its history.
    """
    issue.severity = severity
    issue.title_ko = draft.title_ko
    if draft.business_impact_ko:
        issue.business_impact_ko = draft.business_impact_ko
    merged = list(dict.fromkeys([*(issue.evidence_ids or []), *draft.evidence_ids]))
    issue.evidence_ids = merged


def _upsert_recommendation(
    session: Session, principal: Principal, issue: Issue, draft: IssueDraft
) -> FixRecommendation:
    """One recommendation row per issue, carrying the fix and the re-verification rule."""
    statement = (
        tenant_select(FixRecommendation, principal)
        .where(FixRecommendation.issue_id == issue.id)
    )
    assert_tenant_scoped(statement, principal.organization_id)
    recommendation = session.scalars(statement).first()

    rule = {
        "check_id": issue.check_id,
        "urls": list(affected_urls_of(issue)),
        "note_ko": draft.reverification_note_ko
        or "이 이슈에 표시된 URL만 다시 수집해 해당 검사 하나만 재판정합니다.",
    }

    if recommendation is None:
        recommendation = FixRecommendation(
            organization_id=principal.organization_id,
            issue_id=issue.id,
            summary_ko=draft.summary_ko,
            developer_steps_ko=draft.remediation_ko or None,
            code_example=draft.fix_example,
            reverification_rule=rule,
            generated_by="RULE",
            review_state="NOT_REVIEWED",
        )
        session.add(recommendation)
    else:
        recommendation.summary_ko = draft.summary_ko
        recommendation.developer_steps_ko = draft.remediation_ko or None
        recommendation.code_example = draft.fix_example
        recommendation.reverification_rule = rule
    session.flush()
    return recommendation


def _apply_transition(
    session: Session,
    principal: Principal,
    issue: Issue,
    *,
    source: IssueState,
    target: IssueState,
    trigger: TransitionTrigger,
    request_id: str | None,
    detail: dict[str, object] | None = None,
) -> Issue:
    """Write the new state and the one audit row that records the move.

    Exactly one audit row per state change: the history and the state can then never
    disagree, and the trail cannot be padded with entries that look like measurements.
    """
    issue.state = str(target)
    audit.record(
        session,
        principal,
        action=TRANSITION_ACTION,
        target_type=TARGET_TYPE,
        target_id=issue.id,
        request_id=request_id,
        detail={
            "from": str(source),
            "to": str(target),
            "trigger": str(trigger),
            **(detail or {}),
        },
    )
    session.flush()
    return issue


def _assert_awaiting_verification(source: IssueState) -> None:
    """Refuse a verification result for an issue that never asked for one.

    Checked before anything is written, so a rejected result leaves no
    ``verification_runs`` row behind to be mistaken for evidence later.
    """
    if allowed_targets(source, trigger=TransitionTrigger.VERIFICATION_OUTCOME):
        return
    raise IllegalTransitionError(
        f"'{describe_state_ko(source)}' 상태의 이슈에는 재측정 결과를 기록할 수 없습니다. "
        "먼저 수정 보고 후 재검사를 요청해야 합니다."
    )


def _measurements_for(
    session: Session, principal: Principal, issue: Issue, scan_run: ScanRun
) -> list[MeasuredCheck]:
    """The re-scan's persisted outcomes for this issue's one check, with their URLs.

    ## 어느 칸에서 주소를 읽는가 — 2026-08-06 에 고쳤다

    이 함수는 `check_results.url_record_id` → `url_records` 를 조인해 주소를 얻고
    있었다. 그런데 **그 두 칸은 한 번도 채워진 적이 없다** — 운영 실측:
    `url_records` 0행, `url_record_id` 는 2,111행 중 0행.

    결과가 무엇이었나. 조인은 언제나 `NULL` 을 냈고, `derive_outcome` 은
    "재측정한 주소" 를 빈 집합으로 보게 된다. 그러면 영향 URL 이 전부
    "재측정하지 못함" 으로 남아 **판정이 구조적으로 절대 RESOLVED 가 될 수 없다.**
    고객이 문제를 다 고치고 재검사를 눌러도 화면은 늘 "확인 못 함" 이었다.

    주소는 사라진 적이 없다. `check_results.evaluated_urls` 에 들어 있다(실측:
    한 판정에 84·120·122개). 판정마다 주소 **목록**을 갖는 지금 구조에서
    "판정 하나 = 주소 하나" 를 전제한 `url_record_id` 는 옛 설계의 잔재다.

    ``evaluated_urls`` 를 쓰는 이유(``affected_urls`` 가 아니라): 물어야 하는 것은
    "이번에 이 주소를 **재 봤는가**" 이지 "이번에도 실패했는가" 가 아니다. 실패
    여부는 `status` 가 이미 말하고, `derive_outcome` 이 그것을 먼저 본다.

    사이트 전체 검사처럼 주소가 없는 판정은 주소 없는 측정 하나로 남긴다 —
    빼 버리면 "이 검사가 재실행에 아예 없었다" 와 구분되지 않는다.
    """
    statement = (
        select(CheckResult)
        .where(CheckResult.organization_id == principal.organization_id)
        .where(CheckResult.scan_run_id == scan_run.id)
        .where(CheckResult.check_id == issue.check_id)
    )
    assert_tenant_scoped(statement, principal.organization_id)

    measurements: list[MeasuredCheck] = []
    for result in session.execute(statement).scalars():
        urls = [str(url) for url in (result.evaluated_urls or []) if str(url).strip()]
        if not urls:
            measurements.append(
                MeasuredCheck(
                    check_id=result.check_id,
                    status=CheckStatus(result.status),
                    url=None,
                    check_result_id=result.id,
                )
            )
            continue
        measurements.extend(
            MeasuredCheck(
                check_id=result.check_id,
                status=CheckStatus(result.status),
                url=url,
                check_result_id=result.id,
            )
            for url in urls
        )
    return measurements


def _recommendation_for(
    session: Session, principal: Principal, issue: Issue
) -> FixRecommendation | None:
    statement = (
        tenant_select(FixRecommendation, principal)
        .where(FixRecommendation.issue_id == issue.id)
        .order_by(FixRecommendation.created_at)
    )
    assert_tenant_scoped(statement, principal.organization_id)
    return session.scalars(statement).first()


def _verification_runs(
    session: Session, principal: Principal, issue: Issue
) -> tuple[VerificationRun, ...]:
    statement = (
        tenant_select(VerificationRun, principal)
        .where(VerificationRun.issue_id == issue.id)
        .order_by(VerificationRun.created_at)
    )
    assert_tenant_scoped(statement, principal.organization_id)
    return tuple(session.scalars(statement))


def _audit_rows(session: Session, principal: Principal, issue: Issue) -> tuple[AuditLog, ...]:
    """This issue's audit rows, oldest first.

    ``audit_logs.organization_id`` is nullable — rows outlive their organization by
    design — so it is not a tenant-scoped table for the structural guard and is filtered
    explicitly here instead.

    Entries committed inside one database transaction share a timestamp, because
    PostgreSQL's ``now()`` is the transaction clock. There is no monotonic sequence column
    on this table and this module may not add one, so such entries are ordered
    arbitrarily among themselves; entries from different requests always order correctly.
    """
    statement = (
        select(AuditLog)
        .where(AuditLog.organization_id == principal.organization_id)
        .where(AuditLog.target_type == TARGET_TYPE)
        .where(AuditLog.target_id == str(issue.id))
        .where(AuditLog.action.in_(sorted(HISTORY_ACTIONS)))
        .order_by(AuditLog.created_at, AuditLog.id)
    )
    return tuple(session.scalars(statement))


def _history_entry(row: AuditLog) -> HistoryEntry:
    detail = row.detail or {}
    return HistoryEntry(
        at=row.created_at,
        action=row.action,
        from_state=_state_or_none(detail.get("from")),
        to_state=_state_or_none(detail.get("to")),
        trigger=str(detail["trigger"]) if detail.get("trigger") else None,
        actor_user_id=row.actor_user_id,
        request_id=row.request_id,
        summary_ko=_history_summary_ko(row, detail),
    )


def _state_or_none(raw: object) -> IssueState | None:
    if not isinstance(raw, str):
        return None
    try:
        return IssueState(raw)
    except ValueError:
        return None


def _history_summary_ko(row: AuditLog, detail: dict[str, object]) -> str:
    if row.action == CREATE_ACTION:
        return "진단에서 처음 발견되어 이슈로 등록되었습니다."
    if row.action == OBSERVE_ACTION:
        return "새 진단에서도 같은 문제가 다시 관측되었습니다."
    if row.action == ASSIGN_ACTION:
        if detail.get("assigned"):
            return "담당자가 지정되었습니다."
        return "담당자 지정이 해제되었습니다."
    if row.action == recurrence_module.RECURRENCE_ACTION:
        count = detail.get("recurrence_count")
        return f"해결 확인 후 다시 발생했습니다(누적 {count}회)."
    from_state = _state_or_none(detail.get("from"))
    to_state = _state_or_none(detail.get("to"))
    if from_state is None or to_state is None:
        return "상태가 변경되었습니다."
    moved = f"{describe_state_ko(from_state)} → {describe_state_ko(to_state)}"
    outcome = detail.get("outcome")
    if outcome:
        return f"{moved} (재측정 판정: {outcome})"
    return moved


__all__ = [
    "ASSIGN_ACTION",
    "CREATE_ACTION",
    "HISTORY_ACTIONS",
    "OBSERVE_ACTION",
    "REMEDIATION_OWNERS",
    "TARGET_TYPE",
    "TRANSITION_ACTION",
    "HistoryEntry",
    "IngestResult",
    "IssueDetail",
    "affected_urls_of",
    "assign_issue",
    "fingerprint_of_issue",
    "get_issue",
    "get_issue_detail",
    "ingest_drafts",
    "list_issues",
    "record_verification_outcome",
    "request_verification",
    "require_issue",
    "summarize_issue",
    "transition_issue",
]
