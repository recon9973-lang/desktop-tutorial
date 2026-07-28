"""The reviewer's state machine.

The one sentence this file exists to defend: **an automated verdict never becomes a
confirmed one on its own.** No trigger, no ordering of calls, no request body walks an
assessment from ``PENDING_REVIEW`` to ``CONFIRMED``; a person has to look, and their
decision is recorded *beside* the machine's, never on top of it.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from review_support import NOW, OTHER_REVIEWER, REVIEWER, assessment

from veo.contracts.enums import ReviewState
from veo.observations.review.decisions import (
    HUMAN_ONLY_STAGES,
    TERMINAL_STAGES,
    IllegalReviewTransitionError,
    RejectionReason,
    ReviewStage,
    ReviewTrigger,
    allowed_targets,
    apply_decision,
    assert_review_transition,
    describe_stage_ko,
    legal_transitions,
    open_review,
)
from veo.observations.risk.assessment import AutomatedVerdict


def under_review():  # type: ignore[no-untyped-def]
    return apply_decision(
        open_review(assessment()),
        target=ReviewStage.UNDER_REVIEW,
        trigger=ReviewTrigger.REVIEWER_CLAIM,
        reviewer_id=REVIEWER,
        at=NOW,
    )


# --------------------------------------------------------------------------- #
# The legal path
# --------------------------------------------------------------------------- #


def test_a_new_assessment_starts_pending_review() -> None:
    review = open_review(assessment())
    assert review.stage is ReviewStage.PENDING_REVIEW
    assert review.human is None


def test_the_declared_path_is_pending_then_under_review_then_a_decision() -> None:
    claimed = under_review()
    assert claimed.stage is ReviewStage.UNDER_REVIEW

    confirmed = apply_decision(
        claimed,
        target=ReviewStage.CONFIRMED,
        trigger=ReviewTrigger.REVIEWER_DECISION,
        reviewer_id=REVIEWER,
        at=NOW + timedelta(minutes=5),
    )
    assert confirmed.stage is ReviewStage.CONFIRMED


@pytest.mark.parametrize(
    "target",
    [ReviewStage.CONFIRMED, ReviewStage.REJECTED, ReviewStage.NEEDS_MORE_EVIDENCE],
)
def test_all_three_outcomes_are_reachable_from_under_review(target: ReviewStage) -> None:
    reason = RejectionReason.CLAIM_IS_ACCURATE if target is ReviewStage.REJECTED else None
    decided = apply_decision(
        under_review(),
        target=target,
        trigger=ReviewTrigger.REVIEWER_DECISION,
        reviewer_id=REVIEWER,
        at=NOW,
        rejection_reason=reason,
        note_ko="검수자 메모",
    )
    assert decided.stage is target


def test_needs_more_evidence_can_be_picked_up_again() -> None:
    parked = apply_decision(
        under_review(),
        target=ReviewStage.NEEDS_MORE_EVIDENCE,
        trigger=ReviewTrigger.REVIEWER_DECISION,
        reviewer_id=REVIEWER,
        at=NOW,
        note_ko="원문 답변 재수집 필요",
    )
    resumed = apply_decision(
        parked,
        target=ReviewStage.UNDER_REVIEW,
        trigger=ReviewTrigger.REVIEWER_CLAIM,
        reviewer_id=OTHER_REVIEWER,
        at=NOW + timedelta(hours=2),
    )
    assert resumed.stage is ReviewStage.UNDER_REVIEW


def test_a_claimed_item_can_be_released_back_to_the_queue() -> None:
    released = apply_decision(
        under_review(),
        target=ReviewStage.PENDING_REVIEW,
        trigger=ReviewTrigger.REVIEWER_RELEASE,
        reviewer_id=REVIEWER,
        at=NOW,
    )
    assert released.stage is ReviewStage.PENDING_REVIEW


# --------------------------------------------------------------------------- #
# Every illegal transition
# --------------------------------------------------------------------------- #


def test_an_automated_verdict_alone_never_reaches_confirmed() -> None:
    review = open_review(assessment())
    with pytest.raises(IllegalReviewTransitionError) as excinfo:
        apply_decision(
            review,
            target=ReviewStage.CONFIRMED,
            trigger=ReviewTrigger.REVIEWER_DECISION,
            reviewer_id=REVIEWER,
            at=NOW,
        )
    assert "검수" in excinfo.value.message_ko


def test_no_automated_trigger_appears_on_any_edge() -> None:
    for edge in legal_transitions():
        assert ReviewTrigger.AUTOMATED not in edge.triggers, (
            f"{edge.source} → {edge.target} 에 자동 트리거가 붙었습니다"
        )


@pytest.mark.parametrize("stage", sorted(HUMAN_ONLY_STAGES))
def test_the_automated_trigger_cannot_reach_a_human_only_stage(stage: ReviewStage) -> None:
    with pytest.raises(IllegalReviewTransitionError):
        assert_review_transition(
            ReviewStage.UNDER_REVIEW,
            stage,
            trigger=ReviewTrigger.AUTOMATED,
            reviewer_id=None,
        )


def test_a_human_decision_without_a_reviewer_is_refused() -> None:
    with pytest.raises(IllegalReviewTransitionError, match="검수자"):
        apply_decision(
            under_review(),
            target=ReviewStage.CONFIRMED,
            trigger=ReviewTrigger.REVIEWER_DECISION,
            reviewer_id=None,
            at=NOW,
        )


def test_a_rejection_must_record_a_reason() -> None:
    with pytest.raises(IllegalReviewTransitionError, match="사유"):
        apply_decision(
            under_review(),
            target=ReviewStage.REJECTED,
            trigger=ReviewTrigger.REVIEWER_DECISION,
            reviewer_id=REVIEWER,
            at=NOW,
        )


@pytest.mark.parametrize("terminal", sorted(TERMINAL_STAGES))
@pytest.mark.parametrize("target", list(ReviewStage))
def test_a_decided_assessment_cannot_be_moved_again(
    terminal: ReviewStage, target: ReviewStage
) -> None:
    with pytest.raises(IllegalReviewTransitionError):
        assert_review_transition(
            terminal, target, trigger=ReviewTrigger.REVIEWER_DECISION, reviewer_id=REVIEWER
        )


def test_the_wrong_trigger_on_a_real_edge_is_refused() -> None:
    with pytest.raises(IllegalReviewTransitionError):
        assert_review_transition(
            ReviewStage.PENDING_REVIEW,
            ReviewStage.UNDER_REVIEW,
            trigger=ReviewTrigger.REVIEWER_DECISION,
            reviewer_id=REVIEWER,
        )


def test_staying_put_is_not_a_transition() -> None:
    with pytest.raises(IllegalReviewTransitionError):
        assert_review_transition(
            ReviewStage.UNDER_REVIEW,
            ReviewStage.UNDER_REVIEW,
            trigger=ReviewTrigger.REVIEWER_CLAIM,
            reviewer_id=REVIEWER,
        )


def test_a_refusal_names_what_was_possible_instead() -> None:
    with pytest.raises(IllegalReviewTransitionError) as excinfo:
        assert_review_transition(
            ReviewStage.PENDING_REVIEW,
            ReviewStage.REJECTED,
            trigger=ReviewTrigger.REVIEWER_DECISION,
            reviewer_id=REVIEWER,
        )
    message = excinfo.value.message_ko
    assert describe_stage_ko(ReviewStage.UNDER_REVIEW) in message


def test_the_edge_table_is_the_whole_specification() -> None:
    declared = {(edge.source, edge.target) for edge in legal_transitions()}
    for source in ReviewStage:
        for target in ReviewStage:
            if (source, target) in declared:
                continue
            for trigger in ReviewTrigger:
                with pytest.raises(IllegalReviewTransitionError):
                    assert_review_transition(
                        source, target, trigger=trigger, reviewer_id=REVIEWER
                    )


def test_allowed_targets_is_derived_from_the_table() -> None:
    assert allowed_targets(ReviewStage.PENDING_REVIEW) == frozenset({ReviewStage.UNDER_REVIEW})
    assert allowed_targets(ReviewStage.CONFIRMED) == frozenset()


# --------------------------------------------------------------------------- #
# Machine and human, side by side
# --------------------------------------------------------------------------- #


def test_the_automated_verdict_survives_a_contradicting_human_decision() -> None:
    machine_said = assessment(verdict=AutomatedVerdict.CONTRADICTED)
    rejected = apply_decision(
        apply_decision(
            open_review(machine_said),
            target=ReviewStage.UNDER_REVIEW,
            trigger=ReviewTrigger.REVIEWER_CLAIM,
            reviewer_id=REVIEWER,
            at=NOW,
        ),
        target=ReviewStage.REJECTED,
        trigger=ReviewTrigger.REVIEWER_DECISION,
        reviewer_id=REVIEWER,
        at=NOW + timedelta(minutes=3),
        rejection_reason=RejectionReason.CLAIM_IS_ACCURATE,
        note_ko="원문을 다시 읽어보니 문제 없는 문장입니다.",
    )

    # Both facts are readable afterwards, and they disagree.
    assert rejected.assessment.automated.verdict is AutomatedVerdict.CONTRADICTED
    assert rejected.stage is ReviewStage.REJECTED
    assert rejected.human is not None
    assert rejected.human.rejection_reason is RejectionReason.CLAIM_IS_ACCURATE
    assert rejected.disagrees is True

    row = rejected.to_row()
    assert row["automated_verdict"] == AutomatedVerdict.CONTRADICTED.value
    assert row["review_state"] == ReviewState.HUMAN_REJECTED.value


def test_agreement_is_visible_too() -> None:
    confirmed = apply_decision(
        under_review(),
        target=ReviewStage.CONFIRMED,
        trigger=ReviewTrigger.REVIEWER_DECISION,
        reviewer_id=REVIEWER,
        at=NOW,
    )
    assert confirmed.disagrees is False
    assert confirmed.assessment.automated.verdict is AutomatedVerdict.CONTRADICTED


def test_the_history_records_every_move() -> None:
    confirmed = apply_decision(
        under_review(),
        target=ReviewStage.CONFIRMED,
        trigger=ReviewTrigger.REVIEWER_DECISION,
        reviewer_id=REVIEWER,
        at=NOW,
    )
    assert [entry.to_stage for entry in confirmed.history] == [
        ReviewStage.UNDER_REVIEW,
        ReviewStage.CONFIRMED,
    ]


# --------------------------------------------------------------------------- #
# Mapping onto the stored vocabulary
# --------------------------------------------------------------------------- #


def test_only_a_confirmed_stage_maps_to_human_confirmed() -> None:
    for stage in ReviewStage:
        mapped = stage.to_contract_state()
        if stage is ReviewStage.CONFIRMED:
            assert mapped is ReviewState.HUMAN_CONFIRMED
        else:
            assert mapped is not ReviewState.HUMAN_CONFIRMED


def test_stages_a_human_has_not_finished_store_as_pending() -> None:
    assert ReviewStage.UNDER_REVIEW.to_contract_state() is ReviewState.PENDING_REVIEW
    assert ReviewStage.NEEDS_MORE_EVIDENCE.to_contract_state() is ReviewState.PENDING_REVIEW


def test_every_stage_has_a_korean_label() -> None:
    for stage in ReviewStage:
        assert describe_stage_ko(stage).strip()


def test_every_rejection_reason_has_a_korean_explanation() -> None:
    for reason in RejectionReason:
        assert reason.label_ko.strip()
