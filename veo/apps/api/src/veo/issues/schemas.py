"""Request and response shapes for ``/issues``.

Two of these schemas are load-bearing rather than decorative.

:class:`TransitionRequest` accepts a state name and nothing else, and every model here
forbids unknown fields. So does :class:`VerificationResultRequest`, which is the one that
matters: it names a *scan run*, never a verdict. A body carrying ``outcome`` is rejected
at the door rather than ignored, because a field that is silently dropped is a field
somebody will eventually believe in.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from veo.db.models.analysis import Issue, VerificationRun
from veo.issues.lifecycle import IssueState, VerificationOutcome, describe_state_ko, is_open
from veo.issues.service import HistoryEntry, IssueDetail
from veo.issues.verification import VerificationRequest

_STRICT = ConfigDict(extra="forbid")

RemediationOwner = Literal["DEVELOPER", "MARKETER", "BUSINESS_OWNER", "OPERATIONS"]


class IssuePayload(BaseModel):
    """One issue as a list row."""

    model_config = _STRICT

    id: uuid.UUID
    project_id: uuid.UUID
    check_id: str
    severity: str
    state: IssueState
    state_label_ko: str
    is_open: bool
    title_ko: str
    business_impact_ko: str | None = None
    affected_url_count: int
    remediation_owner: str
    assigned_to: uuid.UUID | None = None
    recurrence_count: int
    first_seen_run_id: uuid.UUID | None = None
    last_seen_run_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    summary_ko: str

    @classmethod
    def of(cls, issue: Issue, *, summary_ko: str) -> IssuePayload:
        state = IssueState(issue.state)
        return cls(
            id=issue.id,
            project_id=issue.project_id,
            check_id=issue.check_id,
            severity=issue.severity,
            state=state,
            state_label_ko=describe_state_ko(state),
            is_open=is_open(state),
            title_ko=issue.title_ko,
            business_impact_ko=issue.business_impact_ko,
            affected_url_count=issue.affected_url_count,
            remediation_owner=issue.remediation_owner,
            assigned_to=issue.assigned_to,
            recurrence_count=issue.regression_count,
            first_seen_run_id=issue.first_seen_run_id,
            last_seen_run_id=issue.last_seen_run_id,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
            summary_ko=summary_ko,
        )


class VerificationRunPayload(BaseModel):
    model_config = _STRICT

    id: uuid.UUID
    scan_run_id: uuid.UUID | None = None
    outcome: VerificationOutcome
    reason_ko: str | None = None
    created_at: datetime

    @classmethod
    def of(cls, run: VerificationRun) -> VerificationRunPayload:
        detail = run.detail or {}
        reason = detail.get("reason_ko")
        return cls(
            id=run.id,
            scan_run_id=run.scan_run_id,
            outcome=VerificationOutcome(run.outcome),
            reason_ko=str(reason) if reason else None,
            created_at=run.created_at,
        )


class RecurrenceCyclePayload(BaseModel):
    model_config = _STRICT

    index: int
    opened_at: datetime
    resolved_at: datetime | None = None
    recurred_at: datetime | None = None
    verification_run_id: uuid.UUID | None = None


class RecurrencePayload(BaseModel):
    """How many times the problem came back, and when each cycle ran."""

    model_config = _STRICT

    count: int
    cycles: list[RecurrenceCyclePayload] = Field(default_factory=list)
    summary_ko: str


class HistoryEntryPayload(BaseModel):
    model_config = _STRICT

    at: datetime
    action: str
    from_state: IssueState | None = None
    to_state: IssueState | None = None
    trigger: str | None = None
    actor_user_id: uuid.UUID | None = None
    request_id: str | None = None
    summary_ko: str

    @classmethod
    def of(cls, entry: HistoryEntry) -> HistoryEntryPayload:
        return cls(
            at=entry.at,
            action=entry.action,
            from_state=entry.from_state,
            to_state=entry.to_state,
            trigger=entry.trigger,
            actor_user_id=entry.actor_user_id,
            request_id=entry.request_id,
            summary_ko=entry.summary_ko,
        )


class IssueDetailPayload(IssuePayload):
    """One issue with everything needed to act on it and to audit it."""

    fingerprint: str
    affected_urls: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    remediation_summary_ko: str | None = None
    remediation_steps_ko: str | None = None
    fix_example: str | None = None
    reverification_note_ko: str | None = None
    verification_runs: list[VerificationRunPayload] = Field(default_factory=list)
    history: list[HistoryEntryPayload] = Field(default_factory=list)
    recurrence: RecurrencePayload

    @classmethod
    def of_detail(cls, detail: IssueDetail) -> IssueDetailPayload:
        base = IssuePayload.of(detail.issue, summary_ko=detail.summary_ko)
        recommendation = detail.recommendation
        rule: dict[str, Any] = (
            dict(recommendation.reverification_rule or {}) if recommendation else {}
        )
        note = rule.get("note_ko")
        return cls(
            **base.model_dump(),
            fingerprint=detail.fingerprint,
            affected_urls=list(detail.affected_urls),
            evidence_ids=[str(value) for value in (detail.issue.evidence_ids or [])],
            remediation_summary_ko=recommendation.summary_ko if recommendation else None,
            remediation_steps_ko=recommendation.developer_steps_ko if recommendation else None,
            fix_example=recommendation.code_example if recommendation else None,
            reverification_note_ko=str(note) if note else None,
            verification_runs=[VerificationRunPayload.of(run) for run in detail.verification_runs],
            history=[HistoryEntryPayload.of(entry) for entry in detail.history],
            recurrence=RecurrencePayload(
                count=detail.recurrence.count,
                cycles=[
                    RecurrenceCyclePayload(
                        index=cycle.index,
                        opened_at=cycle.opened_at,
                        resolved_at=cycle.resolved_at,
                        recurred_at=cycle.recurred_at,
                        verification_run_id=cycle.verification_run_id,
                    )
                    for cycle in detail.recurrence.cycles
                ],
                summary_ko=detail.recurrence.summary_ko(),
            ),
        )


class AssignRequest(BaseModel):
    model_config = _STRICT

    assigned_to: uuid.UUID | None = Field(
        default=None, description="같은 조직에 소속된 사용자 ID입니다. null이면 지정을 해제합니다."
    )


class TransitionRequest(BaseModel):
    """A state change requested by a person.

    ``VERIFIED_RESOLVED`` is a valid member of the enum and is still refused by the state
    machine, deliberately: the refusal carries a Korean explanation of why a human cannot
    close a finding, which a schema-level rejection could not.
    """

    model_config = _STRICT

    to_state: IssueState


class VerificationRequestPayload(BaseModel):
    """The narrow re-scan that will settle one issue."""

    model_config = _STRICT

    check_id: str
    target_urls: list[str] = Field(default_factory=list)
    note_ko: str
    scan_parameters: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def of(cls, request: VerificationRequest) -> VerificationRequestPayload:
        return cls(
            check_id=request.check_id,
            target_urls=list(request.target_urls),
            note_ko=request.note_ko,
            scan_parameters=request.as_scan_parameters(),
        )


class VerificationRequestedPayload(BaseModel):
    model_config = _STRICT

    id: uuid.UUID
    state: IssueState
    state_label_ko: str
    summary_ko: str
    request: VerificationRequestPayload


class VerificationResultRequest(BaseModel):
    """Names the re-scan to read. It cannot name a verdict — that is the whole point."""

    model_config = _STRICT

    scan_run_id: uuid.UUID = Field(
        description=(
            "재측정을 수행한 진단 실행 ID입니다. 판정은 이 실행이 남긴 검사 결과에서 "
            "도출되며, 요청 본문으로 지정할 수 없습니다."
        )
    )


class VerificationRecordedPayload(BaseModel):
    model_config = _STRICT

    id: uuid.UUID
    state: IssueState
    state_label_ko: str
    outcome: VerificationOutcome
    reason_ko: str
    verification_run_id: uuid.UUID
    scan_run_id: uuid.UUID | None = None
    summary_ko: str


__all__ = [
    "AssignRequest",
    "HistoryEntryPayload",
    "IssueDetailPayload",
    "IssuePayload",
    "RecurrenceCyclePayload",
    "RecurrencePayload",
    "RemediationOwner",
    "TransitionRequest",
    "VerificationRecordedPayload",
    "VerificationRequestPayload",
    "VerificationRequestedPayload",
    "VerificationResultRequest",
    "VerificationRunPayload",
]
