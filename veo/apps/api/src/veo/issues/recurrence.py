"""Recurrence: what happens when a verified-resolved problem shows up again.

"We found this once" and "we have fixed this three times and it keeps coming back" call
for completely different conversations — the second one is about a process or a
deployment pipeline, not about a missing tag. So the data has to support saying it, which
means a count *and* the timestamps of every cycle, not a boolean.

Where the history lives is constrained by the schema, which this module does not own.
``issues.regression_count`` holds the count. The timestamps are reconstructed from two
append-only sources that already exist and cannot be quietly edited:

* ``verification_runs`` — when a cycle was closed by a passing re-measurement, and by
  which run.
* ``audit_logs`` rows with action ``issue.recurred`` — when the problem was observed
  again, under which request, by whom.

Reconstructing rather than storing a summary means the count and the timeline cannot
disagree: there is exactly one place each fact is written, and it is a table nobody can
update in place.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from veo.authz import Principal
from veo.db.models.analysis import Issue, ScanRun, VerificationRun
from veo.db.models.identity import AuditLog
from veo.issues.lifecycle import (
    IssueState,
    TransitionTrigger,
    assert_transition,
    parse_state,
)
from veo.organizations import audit

#: The audit action that marks one recurrence. Read back by :func:`build_history`, so it
#: is a constant rather than a literal typed in two places.
RECURRENCE_ACTION = "issue.recurred"

TARGET_TYPE = "issue"

RESOLVED_OUTCOME = "RESOLVED"


@dataclass(frozen=True, slots=True)
class RecurrenceCycle:
    """One pass through the lifecycle: found, (maybe) resolved, (maybe) back again.

    The last cycle of a live issue has ``resolved_at`` and ``recurred_at`` unset — it is
    the one still in progress.
    """

    index: int
    opened_at: datetime
    resolved_at: datetime | None
    recurred_at: datetime | None
    verification_run_id: uuid.UUID | None

    @property
    def is_closed(self) -> bool:
        return self.recurred_at is not None


@dataclass(frozen=True, slots=True)
class RecurrenceHistory:
    """Every cycle an issue has been through, oldest first."""

    count: int
    cycles: tuple[RecurrenceCycle, ...]

    @property
    def first_seen_at(self) -> datetime:
        return self.cycles[0].opened_at

    @property
    def last_recurred_at(self) -> datetime | None:
        closed = [cycle.recurred_at for cycle in self.cycles if cycle.recurred_at is not None]
        return closed[-1] if closed else None

    def summary_ko(self) -> str:
        last = self.last_recurred_at
        if self.count == 0 or last is None:
            return "재발 이력이 없습니다."
        return (
            f"해결 확인 후 {self.count}회 재발했습니다. "
            f"마지막 재발 시각은 {last:%Y-%m-%d %H:%M}입니다. "
            "반복 재발은 개별 페이지 문제가 아니라 배포·운영 절차의 문제일 가능성이 큽니다."
        )


def build_history(
    issue: Issue,
    verification_runs: Iterable[VerificationRun],
    audit_rows: Iterable[AuditLog],
) -> RecurrenceHistory:
    """Reconstruct the cycles from the append-only record.

    Rows may arrive in any order; they are sorted here, because the caller's query order
    is not something the reconstruction should depend on.
    """
    resolutions = sorted(
        (run for run in verification_runs if run.outcome == RESOLVED_OUTCOME),
        key=lambda run: run.created_at,
    )
    recurrences = sorted(
        (row for row in audit_rows if row.action == RECURRENCE_ACTION),
        key=lambda row: row.created_at,
    )

    cycles: list[RecurrenceCycle] = []
    opened_at = issue.created_at
    for index in range(len(recurrences) + 1):
        resolution = resolutions[index] if index < len(resolutions) else None
        recurrence = recurrences[index] if index < len(recurrences) else None
        cycles.append(
            RecurrenceCycle(
                index=index,
                opened_at=opened_at,
                resolved_at=None if resolution is None else resolution.created_at,
                recurred_at=None if recurrence is None else recurrence.created_at,
                verification_run_id=None if resolution is None else resolution.id,
            )
        )
        if recurrence is None:
            break
        opened_at = recurrence.created_at

    return RecurrenceHistory(count=len(recurrences), cycles=tuple(cycles))


def has_recurred(issue: Issue) -> bool:
    """Whether observing this issue again would be a recurrence rather than a repeat."""
    return parse_state(issue.state) is IssueState.VERIFIED_RESOLVED


def mark_recurred(
    session: Session,
    principal: Principal,
    issue: Issue,
    *,
    scan_run: ScanRun,
    request_id: str | None = None,
) -> Issue:
    """Move a verified-resolved issue back to ``RECURRED`` and record the cycle.

    The transition is asserted with the ``RESCAN`` trigger, which no console action can
    supply — a recurrence is something VEO observed, never something a person declared.
    """
    source = parse_state(issue.state)
    assert_transition(
        source, IssueState.RECURRED, trigger=TransitionTrigger.RESCAN
    )

    issue.state = IssueState.RECURRED
    issue.regression_count = int(issue.regression_count or 0) + 1
    issue.last_seen_run_id = scan_run.id

    audit.record(
        session,
        principal,
        action=RECURRENCE_ACTION,
        target_type=TARGET_TYPE,
        target_id=issue.id,
        request_id=request_id,
        detail={
            "check_id": issue.check_id,
            "scan_run_id": str(scan_run.id),
            "recurrence_count": issue.regression_count,
            "from": str(source),
            "to": str(IssueState.RECURRED),
            "trigger": str(TransitionTrigger.RESCAN),
        },
    )
    session.flush()
    return issue


def recurrence_audit_rows(rows: Sequence[AuditLog]) -> tuple[AuditLog, ...]:
    """Just the recurrence entries, oldest first."""
    return tuple(
        sorted((row for row in rows if row.action == RECURRENCE_ACTION), key=lambda r: r.created_at)
    )


__all__ = [
    "RECURRENCE_ACTION",
    "RecurrenceCycle",
    "RecurrenceHistory",
    "build_history",
    "has_recurred",
    "mark_recurred",
    "recurrence_audit_rows",
]
