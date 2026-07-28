"""The human review queue.

What needs a person, why, and in what order.

**Order is severity first, age second.** Severity alone starves the old findings — a
fatal item from March sits behind every fatal item since. Age alone buries the fatal one
behind forty trivial ones, which is the exact failure the counting methodology exists to
prevent. Both keys, in that order.

**Holding is explicit.** A reviewer claims an item, and until they release it or decide,
nobody else can touch it. Two reviewers silently deciding the same medical finding is how
a queue produces a decision nobody made.

**Everything is written down.** Every enqueue, claim, release and decision lands in an
append-only trail with who and when. A refused action writes nothing — the trail records
what happened, not what was attempted — but it also removes nothing, so a failed claim
cannot be used to quietly rewrite an earlier one.

The queue holds :class:`~veo.observations.review.decisions.ReviewedAssessment` values and
walks them through the declared state machine; it contains no rule of its own about what
a reviewer may do. There is deliberately no method here that concludes a review without a
``reviewer_id``.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from veo.observations.review.decisions import (
    RejectionReason,
    ReviewedAssessment,
    ReviewStage,
    ReviewTrigger,
    apply_decision,
    describe_stage_ko,
    open_review,
)
from veo.observations.risk.assessment import ClaimAssessment
from veo.observations.risk.taxonomy import RiskBand, RiskKind

#: Stages that put an item in front of a human.
_WAITING_STAGES: frozenset[ReviewStage] = frozenset(
    {ReviewStage.PENDING_REVIEW, ReviewStage.NEEDS_MORE_EVIDENCE}
)


class QueueConflictError(Exception):
    """Two people wanted the same item, or somebody acted on an item they do not hold."""

    def __init__(self, message_ko: str) -> None:
        self.message_ko = message_ko
        super().__init__(message_ko)


class QueueEventType(StrEnum):
    ENQUEUED = "ENQUEUED"
    CLAIMED = "CLAIMED"
    RELEASED = "RELEASED"
    DECIDED = "DECIDED"


@dataclass(frozen=True, slots=True)
class QueueEvent:
    """One line of the audit trail."""

    event_type: QueueEventType
    assessment_id: str
    at: datetime
    reviewer_id: str | None
    detail_ko: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "assessment_id": self.assessment_id,
            "at": self.at.isoformat(),
            "reviewer_id": self.reviewer_id,
            "detail_ko": self.detail_ko,
        }


@dataclass(frozen=True, slots=True)
class QueueEntry:
    """One item waiting for a person, and why it is waiting."""

    assessment_id: str
    band: RiskBand
    kind: RiskKind
    stage: ReviewStage
    enqueued_at: datetime
    blocks_publication: bool
    why_ko: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "severity": self.band.value,
            "severity_label_ko": self.band.label_ko,
            "kind": self.kind.value,
            "stage": self.stage.value,
            "stage_label_ko": describe_stage_ko(self.stage),
            "enqueued_at": self.enqueued_at.isoformat(),
            "blocks_publication": self.blocks_publication,
            "why_ko": self.why_ko,
        }


class ReviewQueue:
    """An in-memory review queue.

    Persistence is not implemented here: ``claim_assessments`` has no column for a
    holder, a claim time or a queue event, and this worker may not add one. See
    ``INTEGRATION_REQUEST.md`` requests #3 and #4. Until those land, the console can build
    a queue from ``review_state`` on read and this class is where the rules live.
    """

    def __init__(self) -> None:
        self._reviews: dict[str, ReviewedAssessment] = {}
        self._enqueued_at: dict[str, datetime] = {}
        self._holders: dict[str, str] = {}
        self._trail: list[QueueEvent] = []

    # ----------------------------------------------------------------- #
    # Filling the queue
    # ----------------------------------------------------------------- #

    def enqueue(self, assessment: ClaimAssessment, *, at: datetime) -> ReviewedAssessment:
        """Put a fresh machine finding in front of the humans."""
        key = assessment.assessment_id
        if key in self._reviews:
            raise QueueConflictError(
                f"{key}: 이미 검수 큐에 있는 판정입니다. 같은 판정을 두 번 넣으면 "
                "같은 건을 두 사람이 각각 판단하게 됩니다."
            )
        review = open_review(assessment)
        self._reviews[key] = review
        self._enqueued_at[key] = at
        self._record(QueueEventType.ENQUEUED, key, at, None, self._why_ko(review))
        return review

    # ----------------------------------------------------------------- #
    # Reading it
    # ----------------------------------------------------------------- #

    def pending(self) -> tuple[QueueEntry, ...]:
        """Everything waiting for a person, most severe first, then oldest first."""
        entries = [
            self._entry(key, review)
            for key, review in self._reviews.items()
            if review.stage in _WAITING_STAGES
        ]
        entries.sort(key=lambda entry: (entry.band.rank, entry.enqueued_at, entry.assessment_id))
        return tuple(entries)

    def all_reviews(self) -> tuple[ReviewedAssessment, ...]:
        """Every item the queue has ever held, decided or not."""
        return tuple(self._reviews.values())

    def review_for(self, assessment_id: str) -> ReviewedAssessment:
        return self._require(assessment_id)

    def assigned_to(self, assessment_id: str) -> str | None:
        self._require(assessment_id)
        return self._holders.get(assessment_id)

    def audit_trail(self) -> tuple[QueueEvent, ...]:
        """Every action, in order. A tuple, so a caller cannot append to the record."""
        return tuple(self._trail)

    def __iter__(self) -> Iterator[QueueEntry]:
        return iter(self.pending())

    def __len__(self) -> int:
        return len(self.pending())

    # ----------------------------------------------------------------- #
    # Working it
    # ----------------------------------------------------------------- #

    def claim(self, assessment_id: str, *, reviewer_id: str, at: datetime) -> ReviewedAssessment:
        """Take an item to look at it. Nobody else may act on it until it is let go."""
        review = self._require(assessment_id)
        holder = self._holders.get(assessment_id)
        if holder is not None and holder != reviewer_id:
            raise QueueConflictError(
                f"{assessment_id}: 이미 {holder} 검수자가 맡고 있습니다. "
                "같은 건을 두 사람이 동시에 판단할 수 없습니다."
            )

        moved = apply_decision(
            review,
            target=ReviewStage.UNDER_REVIEW,
            trigger=ReviewTrigger.REVIEWER_CLAIM,
            reviewer_id=reviewer_id,
            at=at,
        )
        self._reviews[assessment_id] = moved
        self._holders[assessment_id] = reviewer_id
        self._record(
            QueueEventType.CLAIMED, assessment_id, at, reviewer_id, "검수자가 이 건을 맡았습니다."
        )
        return moved

    def release(
        self,
        assessment_id: str,
        *,
        reviewer_id: str,
        at: datetime,
        lapsed: bool = False,
    ) -> ReviewedAssessment:
        """Put an item back without concluding anything."""
        review = self._require(assessment_id)
        self._require_holder(assessment_id, reviewer_id)

        moved = apply_decision(
            review,
            target=ReviewStage.PENDING_REVIEW,
            trigger=(
                ReviewTrigger.SYSTEM_LAPSE if lapsed else ReviewTrigger.REVIEWER_RELEASE
            ),
            reviewer_id=reviewer_id,
            at=at,
        )
        self._reviews[assessment_id] = moved
        self._holders.pop(assessment_id, None)
        self._record(
            QueueEventType.RELEASED,
            assessment_id,
            at,
            reviewer_id,
            "점유가 만료되어 큐로 돌아갔습니다." if lapsed else "검수자가 판단 없이 반납했습니다.",
        )
        return moved

    def record_decision(
        self,
        assessment_id: str,
        *,
        target: ReviewStage,
        reviewer_id: str,
        at: datetime,
        rejection_reason: RejectionReason | None = None,
        note_ko: str | None = None,
    ) -> ReviewedAssessment:
        """Record what the reviewer holding this item concluded.

        The decision goes through the state machine, so an item nobody claimed cannot be
        decided and a stage the table does not allow is refused there rather than here.
        """
        review = self._require(assessment_id)
        self._require_holder(assessment_id, reviewer_id)

        moved = apply_decision(
            review,
            target=target,
            trigger=ReviewTrigger.REVIEWER_DECISION,
            reviewer_id=reviewer_id,
            at=at,
            rejection_reason=rejection_reason,
            note_ko=note_ko,
        )
        self._reviews[assessment_id] = moved
        # The item is no longer held either way: a decided item is finished, and one sent
        # back for more evidence belongs to whoever picks it up next.
        self._holders.pop(assessment_id, None)
        self._record(
            QueueEventType.DECIDED,
            assessment_id,
            at,
            reviewer_id,
            f"검수 결과: {describe_stage_ko(target)}"
            + (f" ({rejection_reason.label_ko})" if rejection_reason else ""),
        )
        return moved

    # ----------------------------------------------------------------- #
    # Internals
    # ----------------------------------------------------------------- #

    def _require(self, assessment_id: str) -> ReviewedAssessment:
        try:
            return self._reviews[assessment_id]
        except KeyError as exc:
            raise KeyError(f"검수 큐에 없는 판정입니다: {assessment_id}") from exc

    def _require_holder(self, assessment_id: str, reviewer_id: str) -> None:
        holder = self._holders.get(assessment_id)
        if holder is None:
            raise QueueConflictError(
                f"{assessment_id}: 아무도 맡고 있지 않은 건입니다. 먼저 착수해야 합니다."
            )
        if holder != reviewer_id:
            raise QueueConflictError(
                f"{assessment_id}: {holder} 검수자가 맡고 있는 건입니다. "
                f"{reviewer_id} 검수자는 이 건을 처리할 수 없습니다."
            )

    def _entry(self, assessment_id: str, review: ReviewedAssessment) -> QueueEntry:
        assessment = review.assessment
        return QueueEntry(
            assessment_id=assessment_id,
            band=assessment.band,
            kind=assessment.kind,
            stage=review.stage,
            enqueued_at=self._enqueued_at[assessment_id],
            blocks_publication=assessment.requires_human_review,
            why_ko=self._why_ko(review),
        )

    @staticmethod
    def _why_ko(review: ReviewedAssessment) -> str:
        assessment = review.assessment
        head = (
            f"[{assessment.band.label_ko}] {assessment.kind.value} — "
            f"자동 판정 {assessment.automated.verdict.value}"
        )
        if review.stage is ReviewStage.NEEDS_MORE_EVIDENCE:
            return f"{head}. 근거가 보강되어야 판단할 수 있어 다시 대기 중입니다."
        if assessment.requires_human_review:
            return (
                f"{head}. 이 등급은 사람 검수를 거치지 않으면 고객 보고서에 실을 수 없습니다."
            )
        return (
            f"{head}. 보고서 게재는 막지 않지만, 검수 전까지는 자동 판정으로 표시됩니다."
        )

    def _record(
        self,
        event_type: QueueEventType,
        assessment_id: str,
        at: datetime,
        reviewer_id: str | None,
        detail_ko: str,
    ) -> None:
        self._trail.append(
            QueueEvent(
                event_type=event_type,
                assessment_id=assessment_id,
                at=at,
                reviewer_id=reviewer_id,
                detail_ko=detail_ko,
            )
        )


def build_queue(
    assessments: Sequence[ClaimAssessment], *, at: datetime
) -> ReviewQueue:
    """Load a batch of fresh findings into a queue."""
    queue = ReviewQueue()
    for assessment in assessments:
        queue.enqueue(assessment, at=at)
    return queue


__all__ = [
    "QueueConflictError",
    "QueueEntry",
    "QueueEvent",
    "QueueEventType",
    "ReviewQueue",
    "build_queue",
]
