"""The reviewer's state machine.

One rule shapes every line here:

    **An automated verdict is a proposal. Only a person turns it into a reviewed one.**

The machine is a table, in the shape :mod:`veo.issues.lifecycle` established: every legal
edge is declared once with the triggers that may walk it and a Korean sentence saying why
it exists. Anything absent is refused, and the refusal names what *was* possible so the
console can offer the right buttons instead of a dead end.

Two properties are asserted by tests and are the reason the table is a table:

* :attr:`ReviewTrigger.AUTOMATED` appears on **no edge at all**. There is no request body,
  no ordering of calls and no role that lets a batch job confirm its own finding.
* ``PENDING_REVIEW → CONFIRMED`` is not an edge. A reviewer has to claim the item first,
  which is the moment the queue records who is looking.

And one rule about what a decision *does*:

    **The human decision sits beside the automated verdict, never on top of it.**

:class:`ReviewedAssessment` holds the original
:class:`~veo.observations.risk.assessment.ClaimAssessment` unchanged. When the machine
said "contradicted" and the reviewer says "no, that sentence is fine", both statements
survive and :attr:`ReviewedAssessment.disagrees` is ``True``. That disagreement is the
only signal VEO has about how good its own automation is; overwriting the verdict would
destroy the measurement and make the automation look perfect forever.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Any

from veo.contracts.enums import ReviewState
from veo.observations.risk.assessment import FINDING_VERDICTS, ClaimAssessment


class ReviewStage(StrEnum):
    """Where a finding stands with the humans.

    Finer-grained than :class:`~veo.contracts.enums.ReviewState`, which this worker does
    not own. ``UNDER_REVIEW`` and ``NEEDS_MORE_EVIDENCE`` both store as
    ``PENDING_REVIEW``: the round trip loses detail, and it loses it in the safe
    direction — an unfinished review never reads back as a finished one. Widening the
    stored vocabulary is request #2 in ``INTEGRATION_REQUEST.md``.
    """

    PENDING_REVIEW = "PENDING_REVIEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"

    def to_contract_state(self) -> ReviewState:
        """The value written to ``claim_assessments.review_state``."""
        return _CONTRACT_STATES[self]


_CONTRACT_STATES: dict[ReviewStage, ReviewState] = {
    ReviewStage.PENDING_REVIEW: ReviewState.PENDING_REVIEW,
    # A claimed item is being looked at. Nobody has concluded anything, so it stores as
    # pending — the same as an untouched one, which is the honest reading.
    ReviewStage.UNDER_REVIEW: ReviewState.PENDING_REVIEW,
    ReviewStage.CONFIRMED: ReviewState.HUMAN_CONFIRMED,
    ReviewStage.REJECTED: ReviewState.HUMAN_REJECTED,
    ReviewStage.NEEDS_MORE_EVIDENCE: ReviewState.PENDING_REVIEW,
}

#: Stages only a person can put an assessment into. ``PENDING_REVIEW`` is absent: the
#: system may always push work back into the queue, it may never pull work out of it.
HUMAN_ONLY_STAGES: frozenset[ReviewStage] = frozenset(
    {
        ReviewStage.UNDER_REVIEW,
        ReviewStage.CONFIRMED,
        ReviewStage.REJECTED,
        ReviewStage.NEEDS_MORE_EVIDENCE,
    }
)

#: Once a person has concluded, the record is closed. A changed mind produces a new
#: assessment from a new observation run, not an edit of the old decision.
TERMINAL_STAGES: frozenset[ReviewStage] = frozenset(
    {ReviewStage.CONFIRMED, ReviewStage.REJECTED}
)

_STAGE_LABELS_KO: dict[ReviewStage, str] = {
    ReviewStage.PENDING_REVIEW: "검수 대기",
    ReviewStage.UNDER_REVIEW: "검수 중",
    ReviewStage.CONFIRMED: "검수 확정(문제 맞음)",
    ReviewStage.REJECTED: "검수 기각(문제 아님)",
    ReviewStage.NEEDS_MORE_EVIDENCE: "근거 보강 필요",
}


class ReviewTrigger(StrEnum):
    """What caused a move. Half the authorization, as in the issue lifecycle."""

    REVIEWER_CLAIM = "REVIEWER_CLAIM"
    """A person took the item to look at it."""

    REVIEWER_DECISION = "REVIEWER_DECISION"
    """A person concluded something."""

    REVIEWER_RELEASE = "REVIEWER_RELEASE"
    """A person put the item back without concluding."""

    SYSTEM_LAPSE = "SYSTEM_LAPSE"
    """A claim expired unused and the item returned to the queue."""

    AUTOMATED = "AUTOMATED"
    """A batch job. Present in the vocabulary and on no edge — so that a test can say so,
    and so that a future edge added with this trigger fails that test loudly."""


class RejectionReason(StrEnum):
    """Why a reviewer said the machine was wrong.

    A closed set, because free text cannot be counted and the whole point of recording
    rejections is to measure where the automation misfires.
    """

    CLAIM_IS_ACCURATE = "CLAIM_IS_ACCURATE"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    WRONG_ENTITY = "WRONG_ENTITY"
    SPAN_MISREAD = "SPAN_MISREAD"
    DUPLICATE = "DUPLICATE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"

    @property
    def label_ko(self) -> str:
        return _REJECTION_LABELS_KO[self]


_REJECTION_LABELS_KO: dict[RejectionReason, str] = {
    RejectionReason.CLAIM_IS_ACCURATE: "지적된 문장이 실제로 사실입니다.",
    RejectionReason.EVIDENCE_INSUFFICIENT: "근거가 자동 판정을 뒷받침하지 못합니다.",
    RejectionReason.WRONG_ENTITY: "고객이 아니라 동명의 다른 업체에 대한 내용입니다.",
    RejectionReason.SPAN_MISREAD: "원문에서 문장을 잘못 잘라내 판정했습니다.",
    RejectionReason.DUPLICATE: "이미 처리한 지적과 같은 건입니다.",
    RejectionReason.OUT_OF_SCOPE: "이번 보고 범위에 해당하지 않습니다.",
}


class IllegalReviewTransitionError(Exception):
    """A move the machine refuses. ``message_ko`` is safe to show a reviewer verbatim."""

    def __init__(self, message_ko: str) -> None:
        self.message_ko = message_ko
        super().__init__(message_ko)


@dataclass(frozen=True, slots=True)
class ReviewTransition:
    """One declared edge, and who may walk it."""

    source: ReviewStage
    target: ReviewStage
    triggers: frozenset[ReviewTrigger]
    reason_ko: str


_EDGES: tuple[ReviewTransition, ...] = (
    ReviewTransition(
        ReviewStage.PENDING_REVIEW,
        ReviewStage.UNDER_REVIEW,
        frozenset({ReviewTrigger.REVIEWER_CLAIM}),
        "검수자가 이 건을 맡았습니다. 자동 판정이 사람 앞에 놓이는 유일한 입구입니다.",
    ),
    ReviewTransition(
        ReviewStage.UNDER_REVIEW,
        ReviewStage.CONFIRMED,
        frozenset({ReviewTrigger.REVIEWER_DECISION}),
        "검수자가 원문과 근거를 확인하고 지적이 맞다고 판단했습니다.",
    ),
    ReviewTransition(
        ReviewStage.UNDER_REVIEW,
        ReviewStage.REJECTED,
        frozenset({ReviewTrigger.REVIEWER_DECISION}),
        "검수자가 자동 판정이 틀렸다고 판단했습니다. 사유가 함께 기록됩니다.",
    ),
    ReviewTransition(
        ReviewStage.UNDER_REVIEW,
        ReviewStage.NEEDS_MORE_EVIDENCE,
        frozenset({ReviewTrigger.REVIEWER_DECISION}),
        "지금 있는 근거로는 판단할 수 없습니다. 확정도 기각도 아닌 상태로 남습니다.",
    ),
    ReviewTransition(
        ReviewStage.UNDER_REVIEW,
        ReviewStage.PENDING_REVIEW,
        frozenset({ReviewTrigger.REVIEWER_RELEASE, ReviewTrigger.SYSTEM_LAPSE}),
        "검수자가 판단하지 않고 반납했거나, 점유가 만료되어 큐로 돌아갔습니다.",
    ),
    ReviewTransition(
        ReviewStage.NEEDS_MORE_EVIDENCE,
        ReviewStage.UNDER_REVIEW,
        frozenset({ReviewTrigger.REVIEWER_CLAIM}),
        "근거가 보강되어 다시 검수합니다.",
    ),
)

_INDEX: dict[tuple[ReviewStage, ReviewStage], ReviewTransition] = {
    (edge.source, edge.target): edge for edge in _EDGES
}


def legal_transitions() -> tuple[ReviewTransition, ...]:
    """Every declared edge. The table is the specification; nothing else is legal."""
    return _EDGES


def allowed_targets(
    source: ReviewStage, *, trigger: ReviewTrigger | None = None
) -> frozenset[ReviewStage]:
    return frozenset(
        edge.target
        for edge in _EDGES
        if edge.source is source and (trigger is None or trigger in edge.triggers)
    )


def describe_stage_ko(stage: ReviewStage) -> str:
    return _STAGE_LABELS_KO[stage]


def assert_review_transition(
    source: ReviewStage,
    target: ReviewStage,
    *,
    trigger: ReviewTrigger,
    reviewer_id: str | None,
    rejection_reason: RejectionReason | None = None,
) -> ReviewTransition:
    """Permit the move or refuse it with a Korean reason.

    The human-only guard is checked *after* the table and separately from it, so it holds
    even if someone later adds an edge into a decided stage: reaching one always requires
    a reviewer trigger and a named reviewer.
    """
    if source is target:
        raise IllegalReviewTransitionError(
            f"이미 '{describe_stage_ko(source)}' 상태입니다. 같은 상태로는 전이할 수 없습니다."
        )

    edge = _INDEX.get((source, target))
    if edge is None:
        raise IllegalReviewTransitionError(_no_such_edge_ko(source, target))

    if trigger not in edge.triggers:
        raise IllegalReviewTransitionError(
            f"'{describe_stage_ko(source)}' → '{describe_stage_ko(target)}' 전이는 "
            f"{_triggers_ko(edge.triggers)}(으)로만 가능합니다. "
            f"요청한 방식({_trigger_ko(trigger)})으로는 이 상태를 바꿀 수 없습니다."
        )

    if target in HUMAN_ONLY_STAGES:
        if trigger is ReviewTrigger.AUTOMATED:
            raise IllegalReviewTransitionError(
                f"'{describe_stage_ko(target)}' 상태는 사람만 기록할 수 있습니다. "
                "자동 판정은 제안일 뿐 검수 결과가 아닙니다."
            )
        if not reviewer_id:
            raise IllegalReviewTransitionError(
                f"'{describe_stage_ko(target)}' 상태에는 검수자가 반드시 기록되어야 합니다."
            )

    if target is ReviewStage.REJECTED and rejection_reason is None:
        raise IllegalReviewTransitionError(
            "기각에는 사유가 필요합니다. 사유 없는 기각은 자동 판정이 어디서 틀렸는지 "
            "집계할 수 없게 만듭니다."
        )

    return edge


@dataclass(frozen=True, slots=True)
class HumanDecision:
    """What one person decided, and when."""

    stage: ReviewStage
    reviewer_id: str
    decided_at: datetime
    rejection_reason: RejectionReason | None = None
    note_ko: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "stage_label_ko": describe_stage_ko(self.stage),
            "reviewer_id": self.reviewer_id,
            "decided_at": self.decided_at.isoformat(),
            "rejection_reason": (
                self.rejection_reason.value if self.rejection_reason else None
            ),
            "rejection_reason_ko": (
                self.rejection_reason.label_ko if self.rejection_reason else None
            ),
            "note_ko": self.note_ko,
        }


@dataclass(frozen=True, slots=True)
class ReviewHistoryEntry:
    """One move, kept so the path to a decision is readable, not just its endpoint."""

    from_stage: ReviewStage
    to_stage: ReviewStage
    trigger: ReviewTrigger
    at: datetime
    reviewer_id: str | None
    rejection_reason: RejectionReason | None = None
    note_ko: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "from_stage": self.from_stage.value,
            "to_stage": self.to_stage.value,
            "trigger": self.trigger.value,
            "at": self.at.isoformat(),
            "reviewer_id": self.reviewer_id,
            "rejection_reason": (
                self.rejection_reason.value if self.rejection_reason else None
            ),
            "note_ko": self.note_ko,
        }


@dataclass(frozen=True, slots=True)
class ReviewedAssessment:
    """A machine finding plus whatever humans have done about it.

    ``assessment`` is never modified. Everything a reviewer contributes lands in
    ``stage``, ``human`` and ``history``, so the two accounts can always be read side by
    side — including when they disagree.
    """

    assessment: ClaimAssessment
    stage: ReviewStage = ReviewStage.PENDING_REVIEW
    human: HumanDecision | None = None
    history: tuple[ReviewHistoryEntry, ...] = ()

    @property
    def is_reviewed(self) -> bool:
        """Whether a person has actually concluded. Being looked at is not concluded."""
        return self.stage in TERMINAL_STAGES

    @property
    def disagrees(self) -> bool:
        """Whether the human decision contradicts the automated verdict.

        Only meaningful once a person has concluded. A rejection of a finding, or a
        confirmation of something the machine did not consider a finding, both count.
        """
        if self.human is None or not self.is_reviewed:
            return False
        machine_says_problem = self.assessment.automated.verdict in FINDING_VERDICTS
        human_says_problem = self.stage is ReviewStage.CONFIRMED
        return machine_says_problem != human_says_problem

    def to_row(self) -> dict[str, Any]:
        """The full ``claim_assessments`` row: machine columns plus review columns.

        The automated columns are copied from the assessment untouched. A human decision
        never rewrites them — that is the whole design.
        """
        row = self.assessment.to_row()
        row["review_state"] = self.stage.to_contract_state().value
        row["reviewed_by"] = self.human.reviewer_id if self.human else None
        row["reviewer_note"] = self._reviewer_note_ko()
        return row

    def _reviewer_note_ko(self) -> str | None:
        if self.human is None:
            return None
        parts = []
        if self.human.rejection_reason is not None:
            parts.append(self.human.rejection_reason.label_ko)
        if self.human.note_ko:
            parts.append(self.human.note_ko)
        return " ".join(parts) if parts else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "assessment": self.assessment.as_dict(),
            "review": {
                "stage": self.stage.value,
                "stage_label_ko": describe_stage_ko(self.stage),
                "stored_as": self.stage.to_contract_state().value,
                "is_reviewed": self.is_reviewed,
                "disagrees_with_automation": self.disagrees,
                "decision": self.human.as_dict() if self.human else None,
                "history": [entry.as_dict() for entry in self.history],
            },
        }


def open_review(assessment: ClaimAssessment) -> ReviewedAssessment:
    """Put a fresh machine finding in front of the humans. Nothing is decided yet."""
    return ReviewedAssessment(assessment=assessment)


def apply_decision(
    review: ReviewedAssessment,
    *,
    target: ReviewStage,
    trigger: ReviewTrigger,
    reviewer_id: str | None,
    at: datetime,
    rejection_reason: RejectionReason | None = None,
    note_ko: str | None = None,
) -> ReviewedAssessment:
    """Walk one declared edge, returning a new record and leaving the old one intact.

    The automated judgement is carried across untouched. There is no parameter here that
    could change it, and no branch below that writes to it.
    """
    assert_review_transition(
        review.stage,
        target,
        trigger=trigger,
        reviewer_id=reviewer_id,
        rejection_reason=rejection_reason,
    )

    entry = ReviewHistoryEntry(
        from_stage=review.stage,
        to_stage=target,
        trigger=trigger,
        at=at,
        reviewer_id=reviewer_id,
        rejection_reason=rejection_reason,
        note_ko=note_ko,
    )

    human = review.human
    if trigger is ReviewTrigger.REVIEWER_DECISION and reviewer_id:
        human = HumanDecision(
            stage=target,
            reviewer_id=reviewer_id,
            decided_at=at,
            rejection_reason=rejection_reason,
            note_ko=note_ko,
        )

    return replace(
        review,
        stage=target,
        human=human,
        history=(*review.history, entry),
    )


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #

_TRIGGER_LABELS_KO: dict[ReviewTrigger, str] = {
    ReviewTrigger.REVIEWER_CLAIM: "검수자 착수",
    ReviewTrigger.REVIEWER_DECISION: "검수자 판단",
    ReviewTrigger.REVIEWER_RELEASE: "검수자 반납",
    ReviewTrigger.SYSTEM_LAPSE: "점유 만료",
    ReviewTrigger.AUTOMATED: "자동 처리",
}


def _trigger_ko(trigger: ReviewTrigger) -> str:
    return _TRIGGER_LABELS_KO[trigger]


def _triggers_ko(triggers: frozenset[ReviewTrigger]) -> str:
    return "·".join(_trigger_ko(trigger) for trigger in sorted(triggers))


def _no_such_edge_ko(source: ReviewStage, target: ReviewStage) -> str:
    possible = sorted(allowed_targets(source))
    if possible:
        options = ", ".join(f"{stage.value}({describe_stage_ko(stage)})" for stage in possible)
        tail = f"지금 가능한 다음 상태는 {options} 입니다."
    else:
        tail = "이 건은 이미 검수가 끝나 더 이상 상태를 바꿀 수 없습니다."
    return (
        f"'{describe_stage_ko(source)}'({source.value}) 상태에서 "
        f"'{describe_stage_ko(target)}'({target.value})(으)로는 전이할 수 없습니다. {tail}"
    )


__all__ = [
    "HUMAN_ONLY_STAGES",
    "TERMINAL_STAGES",
    "HumanDecision",
    "IllegalReviewTransitionError",
    "RejectionReason",
    "ReviewHistoryEntry",
    "ReviewStage",
    "ReviewTransition",
    "ReviewTrigger",
    "ReviewedAssessment",
    "allowed_targets",
    "apply_decision",
    "assert_review_transition",
    "describe_stage_ko",
    "legal_transitions",
    "open_review",
]
