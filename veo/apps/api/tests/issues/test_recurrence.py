"""Cycle reconstruction: how many times a problem came back, and when.

"Fixed once" and "fixed three times and back again" are different conversations to have
with a customer, so the history has to survive as data rather than as a single counter.
These tests run without a database: the reconstruction reads rows, it does not query.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from veo.db.models.analysis import Issue, VerificationRun
from veo.db.models.identity import AuditLog
from veo.issues.recurrence import RECURRENCE_ACTION, build_history

START = datetime(2026, 1, 1, tzinfo=UTC)


def at(hours: int) -> datetime:
    return START + timedelta(hours=hours)


def issue_row(*, created_at: datetime, regression_count: int) -> Issue:
    row = Issue(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        check_id="seo.http.status_ok",
        severity="BLOCKER",
        state="RECURRED",
        title_ko="제목",
        affected_url_count=1,
        sample_urls=["https://e.com/a"],
        evidence_ids=[],
        remediation_owner="DEVELOPER",
        regression_count=regression_count,
    )
    row.created_at = created_at
    return row


def resolved_run(when: datetime) -> VerificationRun:
    run = VerificationRun(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        issue_id=uuid.uuid4(),
        outcome="RESOLVED",
        detail={},
    )
    run.created_at = when
    return run


def failed_run(when: datetime) -> VerificationRun:
    run = resolved_run(when)
    run.outcome = "STILL_FAILING"
    return run


def recurrence_row(when: datetime) -> AuditLog:
    row = AuditLog(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        actor_kind="SERVICE",
        action=RECURRENCE_ACTION,
        target_type="issue",
        target_id=str(uuid.uuid4()),
        detail={},
    )
    row.created_at = when
    return row


def test_an_issue_that_never_resolved_has_one_open_cycle() -> None:
    history = build_history(issue_row(created_at=at(0), regression_count=0), [], [])
    assert history.count == 0
    assert len(history.cycles) == 1
    assert history.cycles[0].opened_at == at(0)
    assert history.cycles[0].resolved_at is None
    assert history.cycles[0].recurred_at is None


def test_a_resolved_issue_that_never_came_back_has_one_closed_cycle() -> None:
    history = build_history(
        issue_row(created_at=at(0), regression_count=0), [resolved_run(at(5))], []
    )
    assert history.count == 0
    assert len(history.cycles) == 1
    assert history.cycles[0].resolved_at == at(5)
    assert history.cycles[0].recurred_at is None


def test_one_recurrence_opens_a_second_cycle_at_the_moment_it_came_back() -> None:
    history = build_history(
        issue_row(created_at=at(0), regression_count=1),
        [resolved_run(at(5))],
        [recurrence_row(at(9))],
    )
    assert history.count == 1
    assert len(history.cycles) == 2
    assert history.cycles[0].recurred_at == at(9)
    assert history.cycles[1].opened_at == at(9)
    assert history.cycles[1].resolved_at is None


def test_every_cycle_keeps_its_own_timestamps() -> None:
    history = build_history(
        issue_row(created_at=at(0), regression_count=2),
        [resolved_run(at(5)), resolved_run(at(20))],
        [recurrence_row(at(9)), recurrence_row(at(30))],
    )
    assert history.count == 2
    assert [(c.opened_at, c.resolved_at, c.recurred_at) for c in history.cycles] == [
        (at(0), at(5), at(9)),
        (at(9), at(20), at(30)),
        (at(30), None, None),
    ]


def test_a_failed_verification_does_not_close_a_cycle() -> None:
    history = build_history(
        issue_row(created_at=at(0), regression_count=0),
        [failed_run(at(3)), resolved_run(at(7))],
        [],
    )
    assert len(history.cycles) == 1
    assert history.cycles[0].resolved_at == at(7)


def test_the_cycle_carries_the_verification_run_that_closed_it() -> None:
    run = resolved_run(at(5))
    history = build_history(issue_row(created_at=at(0), regression_count=0), [run], [])
    assert history.cycles[0].verification_run_id == run.id


def test_rows_arriving_out_of_order_are_still_reconstructed_chronologically() -> None:
    history = build_history(
        issue_row(created_at=at(0), regression_count=2),
        [resolved_run(at(20)), resolved_run(at(5))],
        [recurrence_row(at(30)), recurrence_row(at(9))],
    )
    assert [c.recurred_at for c in history.cycles] == [at(9), at(30), None]


def test_the_history_reports_when_the_problem_last_came_back() -> None:
    history = build_history(
        issue_row(created_at=at(0), regression_count=1),
        [resolved_run(at(5))],
        [recurrence_row(at(9))],
    )
    assert history.first_seen_at == at(0)
    assert history.last_recurred_at == at(9)


def test_unrelated_audit_actions_are_ignored() -> None:
    noise = recurrence_row(at(4))
    noise.action = "issue.transition"
    history = build_history(issue_row(created_at=at(0), regression_count=0), [], [noise])
    assert history.count == 0
    assert len(history.cycles) == 1
