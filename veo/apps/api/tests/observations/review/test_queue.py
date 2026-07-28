"""The human review queue.

What needs a person, why, and in what order. Ordering is severity first and age second,
because the failure mode of a review queue is a fatal finding sitting behind forty
trivial ones, and the failure mode of severity-only ordering is a fatal finding from
March never being reached at all.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from review_support import NOW, OTHER_REVIEWER, REVIEWER, assessment

from veo.observations.review.decisions import (
    RejectionReason,
    ReviewStage,
)
from veo.observations.review.queue import (
    QueueConflictError,
    QueueEventType,
    ReviewQueue,
)
from veo.observations.risk.taxonomy import ClaimDomain, RiskBand, RiskKind


def queue_with_three() -> ReviewQueue:
    queue = ReviewQueue()
    queue.enqueue(
        assessment("as-low", kind=RiskKind.STALENESS, domain=ClaimDomain.GENERAL),
        at=NOW,
    )
    queue.enqueue(
        assessment("as-fatal-new", domain=ClaimDomain.MEDICAL),
        at=NOW + timedelta(days=2),
    )
    queue.enqueue(
        assessment("as-fatal-old", domain=ClaimDomain.PRICING),
        at=NOW + timedelta(days=1),
    )
    return queue


# --------------------------------------------------------------------------- #
# What is in the queue and why
# --------------------------------------------------------------------------- #


def test_pending_items_come_out_severity_first_then_oldest_first() -> None:
    pending = queue_with_three().pending()
    assert [entry.assessment_id for entry in pending] == [
        "as-fatal-old",
        "as-fatal-new",
        "as-low",
    ]


def test_every_entry_explains_why_a_person_is_needed() -> None:
    for entry in queue_with_three().pending():
        assert entry.why_ko.strip()


def test_an_entry_above_the_threshold_says_it_blocks_publication() -> None:
    entry = next(e for e in queue_with_three().pending() if e.assessment_id == "as-fatal-old")
    assert entry.band is RiskBand.FATAL
    assert entry.blocks_publication is True
    assert "보고서" in entry.why_ko


def test_an_entry_below_the_threshold_does_not_block_publication() -> None:
    entry = next(e for e in queue_with_three().pending() if e.assessment_id == "as-low")
    assert entry.blocks_publication is False


def test_the_same_assessment_cannot_be_queued_twice() -> None:
    queue = ReviewQueue()
    queue.enqueue(assessment("as-1"), at=NOW)
    with pytest.raises(QueueConflictError):
        queue.enqueue(assessment("as-1"), at=NOW)


# --------------------------------------------------------------------------- #
# Assignment
# --------------------------------------------------------------------------- #


def test_claiming_assigns_the_item_and_takes_it_out_of_the_pending_list() -> None:
    queue = queue_with_three()
    claimed = queue.claim("as-fatal-old", reviewer_id=REVIEWER, at=NOW + timedelta(hours=1))
    assert claimed.stage is ReviewStage.UNDER_REVIEW
    assert "as-fatal-old" not in [entry.assessment_id for entry in queue.pending()]
    assert queue.assigned_to("as-fatal-old") == REVIEWER


def test_a_second_reviewer_cannot_claim_a_claimed_item() -> None:
    queue = queue_with_three()
    queue.claim("as-fatal-old", reviewer_id=REVIEWER, at=NOW)
    with pytest.raises(QueueConflictError) as excinfo:
        queue.claim("as-fatal-old", reviewer_id=OTHER_REVIEWER, at=NOW)
    assert REVIEWER in str(excinfo.value)


def test_releasing_puts_the_item_back_at_the_front_of_its_severity_band() -> None:
    queue = queue_with_three()
    queue.claim("as-fatal-old", reviewer_id=REVIEWER, at=NOW)
    queue.release("as-fatal-old", reviewer_id=REVIEWER, at=NOW + timedelta(hours=1))
    assert next(entry.assessment_id for entry in queue.pending()) == "as-fatal-old"
    assert queue.assigned_to("as-fatal-old") is None


def test_only_the_holder_may_release() -> None:
    queue = queue_with_three()
    queue.claim("as-fatal-old", reviewer_id=REVIEWER, at=NOW)
    with pytest.raises(QueueConflictError):
        queue.release("as-fatal-old", reviewer_id=OTHER_REVIEWER, at=NOW)


def test_an_unknown_assessment_is_refused_rather_than_created() -> None:
    with pytest.raises(KeyError):
        ReviewQueue().claim("as-nope", reviewer_id=REVIEWER, at=NOW)


# --------------------------------------------------------------------------- #
# Decisions leave the queue
# --------------------------------------------------------------------------- #


def test_a_decided_item_leaves_the_pending_list() -> None:
    queue = queue_with_three()
    queue.claim("as-fatal-old", reviewer_id=REVIEWER, at=NOW)
    reviewed = queue.record_decision(
        "as-fatal-old",
        target=ReviewStage.CONFIRMED,
        reviewer_id=REVIEWER,
        at=NOW + timedelta(minutes=10),
    )
    assert reviewed.stage is ReviewStage.CONFIRMED
    assert "as-fatal-old" not in [entry.assessment_id for entry in queue.pending()]


def test_needs_more_evidence_returns_to_the_pending_list() -> None:
    queue = queue_with_three()
    queue.claim("as-fatal-old", reviewer_id=REVIEWER, at=NOW)
    queue.record_decision(
        "as-fatal-old",
        target=ReviewStage.NEEDS_MORE_EVIDENCE,
        reviewer_id=REVIEWER,
        at=NOW,
        note_ko="인용 원문을 다시 받아야 판단할 수 있습니다.",
    )
    assert "as-fatal-old" in [entry.assessment_id for entry in queue.pending()]


def test_a_reviewer_who_does_not_hold_the_item_cannot_decide_it() -> None:
    queue = queue_with_three()
    queue.claim("as-fatal-old", reviewer_id=REVIEWER, at=NOW)
    with pytest.raises(QueueConflictError):
        queue.record_decision(
            "as-fatal-old",
            target=ReviewStage.CONFIRMED,
            reviewer_id=OTHER_REVIEWER,
            at=NOW,
        )


# --------------------------------------------------------------------------- #
# Audit trail
# --------------------------------------------------------------------------- #


def test_every_action_lands_in_an_append_only_audit_trail() -> None:
    queue = ReviewQueue()
    queue.enqueue(assessment("as-1"), at=NOW)
    queue.claim("as-1", reviewer_id=REVIEWER, at=NOW + timedelta(minutes=1))
    queue.release("as-1", reviewer_id=REVIEWER, at=NOW + timedelta(minutes=2))
    queue.claim("as-1", reviewer_id=OTHER_REVIEWER, at=NOW + timedelta(minutes=3))
    queue.record_decision(
        "as-1",
        target=ReviewStage.REJECTED,
        reviewer_id=OTHER_REVIEWER,
        at=NOW + timedelta(minutes=4),
        rejection_reason=RejectionReason.WRONG_ENTITY,
    )

    kinds = [event.event_type for event in queue.audit_trail()]
    assert kinds == [
        QueueEventType.ENQUEUED,
        QueueEventType.CLAIMED,
        QueueEventType.RELEASED,
        QueueEventType.CLAIMED,
        QueueEventType.DECIDED,
    ]
    assert [event.at for event in queue.audit_trail()] == sorted(
        event.at for event in queue.audit_trail()
    )


def test_the_audit_trail_cannot_be_edited_through_the_accessor() -> None:
    queue = ReviewQueue()
    queue.enqueue(assessment("as-1"), at=NOW)
    trail = queue.audit_trail()
    assert isinstance(trail, tuple)
    before = len(queue.audit_trail())
    assert before == 1


def test_a_failed_action_still_leaves_the_earlier_trail_intact() -> None:
    queue = ReviewQueue()
    queue.enqueue(assessment("as-1"), at=NOW)
    queue.claim("as-1", reviewer_id=REVIEWER, at=NOW)
    with pytest.raises(QueueConflictError):
        queue.claim("as-1", reviewer_id=OTHER_REVIEWER, at=NOW)
    assert [event.event_type for event in queue.audit_trail()] == [
        QueueEventType.ENQUEUED,
        QueueEventType.CLAIMED,
    ]


def test_the_audit_entry_names_the_reviewer_and_the_moment() -> None:
    queue = ReviewQueue()
    queue.enqueue(assessment("as-1"), at=NOW)
    queue.claim("as-1", reviewer_id=REVIEWER, at=NOW + timedelta(minutes=1))
    claimed = queue.audit_trail()[-1]
    assert claimed.reviewer_id == REVIEWER
    assert claimed.at == NOW + timedelta(minutes=1)
    assert claimed.assessment_id == "as-1"


def test_reviewed_items_are_readable_after_the_fact() -> None:
    queue = queue_with_three()
    queue.claim("as-fatal-old", reviewer_id=REVIEWER, at=NOW)
    queue.record_decision(
        "as-fatal-old",
        target=ReviewStage.CONFIRMED,
        reviewer_id=REVIEWER,
        at=NOW,
    )
    everything = {item.assessment.assessment_id: item for item in queue.all_reviews()}
    assert everything["as-fatal-old"].stage is ReviewStage.CONFIRMED
    assert everything["as-low"].stage is ReviewStage.PENDING_REVIEW
