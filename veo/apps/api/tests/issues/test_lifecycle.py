"""The state machine, exercised edge by edge.

The rule this file defends: **an issue is closed by a re-measurement, not by someone
clicking "done"**. A person may say "I changed something" (``FIX_CLAIMED``); only the
outcome of a targeted re-scan may say "it now passes" (``VERIFIED_RESOLVED``).

So every test below is really one of two assertions: a legal edge exists and names its
trigger, or an illegal edge is refused with a Korean reason. There is no third category,
and in particular there is no edge that lets a human write ``VERIFIED_RESOLVED``.
"""

from __future__ import annotations

import itertools

import pytest

from veo.issues.lifecycle import (
    CLOSED_STATES,
    OPEN_STATES,
    IllegalTransitionError,
    IssueState,
    TransitionTrigger,
    VerificationOutcome,
    allowed_targets,
    assert_transition,
    describe_state_ko,
    is_legal,
    legal_transitions,
    state_for_outcome,
)

HUMAN = TransitionTrigger.HUMAN
REQUEST = TransitionTrigger.VERIFICATION_REQUEST
OUTCOME = TransitionTrigger.VERIFICATION_OUTCOME
RESCAN = TransitionTrigger.RESCAN


# --------------------------------------------------------------------------- #
# The vocabulary
# --------------------------------------------------------------------------- #


def test_every_required_state_exists() -> None:
    required = {
        "OPEN",
        "ACKNOWLEDGED",
        "IN_PROGRESS",
        "FIX_CLAIMED",
        "VERIFYING",
        "VERIFIED_RESOLVED",
        "VERIFICATION_FAILED",
        "WONT_FIX",
        "RECURRED",
    }
    assert required <= {member.value for member in IssueState}


def test_open_and_closed_states_partition_the_vocabulary() -> None:
    assert frozenset(IssueState) == OPEN_STATES | CLOSED_STATES
    assert not OPEN_STATES & CLOSED_STATES


def test_fix_claimed_is_not_a_closed_state() -> None:
    """A human claim of "fixed" must never count as resolved anywhere in the product."""
    assert IssueState.FIX_CLAIMED in OPEN_STATES
    assert IssueState.VERIFYING in OPEN_STATES
    assert IssueState.VERIFICATION_FAILED in OPEN_STATES


def test_every_state_has_a_korean_label() -> None:
    for state in IssueState:
        label = describe_state_ko(state)
        assert label
        assert not label.isascii(), f"{state} 라벨이 한국어가 아닙니다: {label}"


# --------------------------------------------------------------------------- #
# Legal transitions
# --------------------------------------------------------------------------- #


LEGAL_HUMAN_EDGES = [
    (IssueState.OPEN, IssueState.ACKNOWLEDGED),
    (IssueState.OPEN, IssueState.IN_PROGRESS),
    (IssueState.OPEN, IssueState.WONT_FIX),
    (IssueState.ACKNOWLEDGED, IssueState.IN_PROGRESS),
    (IssueState.ACKNOWLEDGED, IssueState.WONT_FIX),
    (IssueState.IN_PROGRESS, IssueState.ACKNOWLEDGED),
    (IssueState.IN_PROGRESS, IssueState.FIX_CLAIMED),
    (IssueState.IN_PROGRESS, IssueState.WONT_FIX),
    (IssueState.FIX_CLAIMED, IssueState.IN_PROGRESS),
    (IssueState.VERIFICATION_FAILED, IssueState.IN_PROGRESS),
    (IssueState.VERIFICATION_FAILED, IssueState.WONT_FIX),
    (IssueState.RECURRED, IssueState.ACKNOWLEDGED),
    (IssueState.RECURRED, IssueState.IN_PROGRESS),
    (IssueState.RECURRED, IssueState.WONT_FIX),
    (IssueState.WONT_FIX, IssueState.OPEN),
]


@pytest.mark.parametrize(("source", "target"), LEGAL_HUMAN_EDGES)
def test_a_person_may_walk_these_edges(source: IssueState, target: IssueState) -> None:
    assert is_legal(source, target, trigger=HUMAN)
    assert_transition(source, target, trigger=HUMAN)


@pytest.mark.parametrize(
    "source", [IssueState.FIX_CLAIMED, IssueState.VERIFICATION_FAILED]
)
def test_requesting_verification_moves_an_issue_to_verifying(source: IssueState) -> None:
    assert_transition(source, IssueState.VERIFYING, trigger=REQUEST)


def test_a_passing_verification_resolves_the_issue() -> None:
    assert_transition(
        IssueState.VERIFYING,
        IssueState.VERIFIED_RESOLVED,
        trigger=OUTCOME,
        outcome=VerificationOutcome.RESOLVED,
    )


def test_a_failing_verification_lands_in_verification_failed() -> None:
    assert_transition(
        IssueState.VERIFYING,
        IssueState.VERIFICATION_FAILED,
        trigger=OUTCOME,
        outcome=VerificationOutcome.STILL_FAILING,
    )


def test_an_inconclusive_verification_returns_to_the_fix_claim() -> None:
    """Not measured is not the same as still broken, and neither is resolved."""
    assert_transition(
        IssueState.VERIFYING,
        IssueState.FIX_CLAIMED,
        trigger=OUTCOME,
        outcome=VerificationOutcome.INCONCLUSIVE,
    )


def test_a_resolved_issue_seen_again_recurs() -> None:
    assert_transition(IssueState.VERIFIED_RESOLVED, IssueState.RECURRED, trigger=RESCAN)


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        (VerificationOutcome.RESOLVED, IssueState.VERIFIED_RESOLVED),
        (VerificationOutcome.STILL_FAILING, IssueState.VERIFICATION_FAILED),
        (VerificationOutcome.INCONCLUSIVE, IssueState.FIX_CLAIMED),
    ],
)
def test_the_outcome_alone_decides_where_a_verification_lands(
    outcome: VerificationOutcome, expected: IssueState
) -> None:
    assert state_for_outcome(outcome) is expected


# --------------------------------------------------------------------------- #
# Illegal transitions — the point of the module
# --------------------------------------------------------------------------- #


def test_open_cannot_shortcut_straight_to_verified_resolved() -> None:
    with pytest.raises(IllegalTransitionError) as caught:
        assert_transition(IssueState.OPEN, IssueState.VERIFIED_RESOLVED, trigger=HUMAN)
    assert not caught.value.message_ko.isascii()


@pytest.mark.parametrize("source", list(IssueState))
def test_no_human_trigger_anywhere_can_reach_verified_resolved(source: IssueState) -> None:
    """The whole module exists for this assertion."""
    assert IssueState.VERIFIED_RESOLVED not in allowed_targets(source, trigger=HUMAN)
    if source is not IssueState.VERIFIED_RESOLVED:
        with pytest.raises(IllegalTransitionError):
            assert_transition(source, IssueState.VERIFIED_RESOLVED, trigger=HUMAN)


@pytest.mark.parametrize("source", list(IssueState))
def test_verified_resolved_is_reachable_only_from_verifying(source: IssueState) -> None:
    reachable = any(
        is_legal(
            source,
            IssueState.VERIFIED_RESOLVED,
            trigger=trigger,
            outcome=VerificationOutcome.RESOLVED,
        )
        for trigger in TransitionTrigger
    )
    assert reachable is (source is IssueState.VERIFYING)


def test_a_verification_outcome_that_is_not_a_pass_cannot_resolve_an_issue() -> None:
    for outcome in (VerificationOutcome.STILL_FAILING, VerificationOutcome.INCONCLUSIVE):
        with pytest.raises(IllegalTransitionError) as caught:
            assert_transition(
                IssueState.VERIFYING,
                IssueState.VERIFIED_RESOLVED,
                trigger=OUTCOME,
                outcome=outcome,
            )
        assert not caught.value.message_ko.isascii()


def test_resolving_without_any_verification_outcome_at_all_is_refused() -> None:
    with pytest.raises(IllegalTransitionError):
        assert_transition(
            IssueState.VERIFYING, IssueState.VERIFIED_RESOLVED, trigger=OUTCOME, outcome=None
        )


def test_fix_claimed_cannot_jump_over_verification() -> None:
    with pytest.raises(IllegalTransitionError):
        assert_transition(IssueState.FIX_CLAIMED, IssueState.VERIFIED_RESOLVED, trigger=OUTCOME)


def test_a_failed_verification_does_not_fall_back_to_open() -> None:
    """Silently reopening would erase the fact that a fix was measured and rejected."""
    assert not is_legal(IssueState.VERIFICATION_FAILED, IssueState.OPEN, trigger=HUMAN)
    assert not is_legal(IssueState.VERIFYING, IssueState.OPEN, trigger=OUTCOME)


def test_recurrence_cannot_be_declared_by_a_person() -> None:
    assert not is_legal(IssueState.VERIFIED_RESOLVED, IssueState.RECURRED, trigger=HUMAN)
    with pytest.raises(IllegalTransitionError):
        assert_transition(IssueState.VERIFIED_RESOLVED, IssueState.RECURRED, trigger=HUMAN)


def test_a_resolved_issue_cannot_be_reopened_by_hand() -> None:
    for target in IssueState:
        if target is IssueState.RECURRED:
            continue
        assert not is_legal(IssueState.VERIFIED_RESOLVED, target, trigger=HUMAN)


def test_verification_cannot_be_requested_before_a_fix_is_claimed() -> None:
    for source in (IssueState.OPEN, IssueState.ACKNOWLEDGED, IssueState.IN_PROGRESS):
        with pytest.raises(IllegalTransitionError):
            assert_transition(source, IssueState.VERIFYING, trigger=REQUEST)


def test_a_state_cannot_transition_to_itself() -> None:
    for state in IssueState:
        for trigger in TransitionTrigger:
            assert not is_legal(state, state, trigger=trigger)


def test_the_transition_table_is_closed() -> None:
    """Nothing outside the declared table is legal under any trigger."""
    declared = {(edge.source, edge.target) for edge in legal_transitions()}
    outcomes: list[VerificationOutcome | None] = [None, *VerificationOutcome]
    for source, target in itertools.product(IssueState, IssueState):
        legal_somehow = any(
            is_legal(source, target, trigger=trigger, outcome=outcome)
            for trigger in TransitionTrigger
            for outcome in outcomes
        )
        assert legal_somehow is ((source, target) in declared)


def test_every_declared_edge_carries_at_least_one_trigger_and_a_korean_reason() -> None:
    for edge in legal_transitions():
        assert edge.triggers
        assert edge.reason_ko
        assert not edge.reason_ko.isascii()


def test_the_rejection_message_names_what_was_possible_instead() -> None:
    with pytest.raises(IllegalTransitionError) as caught:
        assert_transition(IssueState.OPEN, IssueState.FIX_CLAIMED, trigger=HUMAN)
    message = caught.value.message_ko
    assert "IN_PROGRESS" in message or "ACKNOWLEDGED" in message
