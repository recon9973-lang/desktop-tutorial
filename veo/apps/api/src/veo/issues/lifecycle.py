"""The issue state machine.

One rule shapes every line of this module:

    **An issue is closed by a re-measurement, not by someone clicking "done".**

A person may say "I changed something" — that is :attr:`IssueState.FIX_CLAIMED`, and it
is an *open* state. Only the outcome of a targeted re-scan may say "the check now
passes", and that is the only way into :attr:`IssueState.VERIFIED_RESOLVED`. The two are
kept apart because collapsing them produces the worst possible artefact: a clean
dashboard over an unchanged website.

The machine is a table, not a set of ``if`` statements. Every legal edge is declared once
with the triggers that may walk it and a Korean sentence explaining why it exists;
anything absent from the table is refused, and the refusal names what *was* possible so
the caller can act on it. That closure is asserted by the tests — no edge can be added
by accident, and in particular no edge into ``VERIFIED_RESOLVED`` can be added without
someone deleting a test that says a human must never get there.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class IssueState(StrEnum):
    """Where an issue stands.

    ``FIX_CLAIMED``, ``VERIFYING`` and ``VERIFICATION_FAILED`` are all *open*: work has
    happened, but nothing has been measured that would justify calling the problem gone.
    ``RECURRED`` is open too, and carries the extra fact that this problem was verified
    resolved once already.
    """

    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    FIX_CLAIMED = "FIX_CLAIMED"
    VERIFYING = "VERIFYING"
    VERIFIED_RESOLVED = "VERIFIED_RESOLVED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    WONT_FIX = "WONT_FIX"
    RECURRED = "RECURRED"


class TransitionTrigger(StrEnum):
    """What caused a move.

    The trigger is not decoration: it is half the authorization. ``HUMAN`` appears on no
    edge that ends at ``VERIFIED_RESOLVED``, so there is no request body, no ordering of
    calls and no role that lets a person write that state.
    """

    HUMAN = "HUMAN"
    """A person acted in the console."""

    VERIFICATION_REQUEST = "VERIFICATION_REQUEST"
    """A targeted re-scan was asked for."""

    VERIFICATION_OUTCOME = "VERIFICATION_OUTCOME"
    """A targeted re-scan came back and its measured outcome decided the move."""

    RESCAN = "RESCAN"
    """A regular scan observed the problem again."""


class VerificationOutcome(StrEnum):
    """What a re-measurement concluded.

    ``INCONCLUSIVE`` is deliberately distinct from ``STILL_FAILING``. "We could not
    measure it" is not "it is still broken", and neither of them is "it is fixed".
    """

    RESOLVED = "RESOLVED"
    STILL_FAILING = "STILL_FAILING"
    INCONCLUSIVE = "INCONCLUSIVE"


#: States in which the problem is still, as far as VEO can tell, present.
OPEN_STATES: frozenset[IssueState] = frozenset(
    {
        IssueState.OPEN,
        IssueState.ACKNOWLEDGED,
        IssueState.IN_PROGRESS,
        IssueState.FIX_CLAIMED,
        IssueState.VERIFYING,
        IssueState.VERIFICATION_FAILED,
        IssueState.RECURRED,
    }
)

#: States in which no further work is expected. ``WONT_FIX`` is a decision, not a
#: measurement; ``VERIFIED_RESOLVED`` is a measurement, not a decision.
CLOSED_STATES: frozenset[IssueState] = frozenset(
    {IssueState.VERIFIED_RESOLVED, IssueState.WONT_FIX}
)

_STATE_LABELS_KO: dict[IssueState, str] = {
    IssueState.OPEN: "미확인",
    IssueState.ACKNOWLEDGED: "확인함",
    IssueState.IN_PROGRESS: "조치 중",
    IssueState.FIX_CLAIMED: "수정했다고 보고됨(재측정 전)",
    IssueState.VERIFYING: "재측정 대기",
    IssueState.VERIFIED_RESOLVED: "재측정으로 해결 확인",
    IssueState.VERIFICATION_FAILED: "재측정 실패(여전히 문제 있음)",
    IssueState.WONT_FIX: "조치하지 않음",
    IssueState.RECURRED: "재발",
}


class IllegalTransitionError(Exception):
    """A move the state machine refuses.

    ``message_ko`` is safe to show a caller verbatim and names what was possible instead,
    so the console can offer the right buttons rather than a dead end.
    """

    def __init__(self, message_ko: str) -> None:
        self.message_ko = message_ko
        super().__init__(message_ko)


@dataclass(frozen=True, slots=True)
class Transition:
    """One declared edge, and who is allowed to walk it."""

    source: IssueState
    target: IssueState
    triggers: frozenset[TransitionTrigger]
    reason_ko: str


def _human(source: IssueState, target: IssueState, reason_ko: str) -> Transition:
    return Transition(source, target, frozenset({TransitionTrigger.HUMAN}), reason_ko)


_EDGES: tuple[Transition, ...] = (
    # --- a person triaging and working -------------------------------------- #
    _human(IssueState.OPEN, IssueState.ACKNOWLEDGED, "담당자가 문제를 확인했습니다."),
    _human(IssueState.OPEN, IssueState.IN_PROGRESS, "확인 절차 없이 바로 조치에 들어갑니다."),
    _human(IssueState.OPEN, IssueState.WONT_FIX, "조치하지 않기로 결정했습니다."),
    _human(IssueState.ACKNOWLEDGED, IssueState.IN_PROGRESS, "조치를 시작했습니다."),
    _human(IssueState.ACKNOWLEDGED, IssueState.WONT_FIX, "확인 후 조치하지 않기로 했습니다."),
    _human(
        IssueState.IN_PROGRESS, IssueState.ACKNOWLEDGED, "조치를 중단하고 대기 상태로 돌립니다."
    ),
    _human(
        IssueState.IN_PROGRESS,
        IssueState.FIX_CLAIMED,
        "'무언가를 바꿨다'는 보고입니다. 아직 해결이 아니며 재측정이 남아 있습니다.",
    ),
    _human(IssueState.IN_PROGRESS, IssueState.WONT_FIX, "조치하지 않기로 결정했습니다."),
    _human(IssueState.FIX_CLAIMED, IssueState.IN_PROGRESS, "수정 보고를 철회하고 다시 작업합니다."),
    _human(
        IssueState.VERIFICATION_FAILED, IssueState.IN_PROGRESS, "재측정 실패 후 다시 조치합니다."
    ),
    _human(
        IssueState.VERIFICATION_FAILED,
        IssueState.WONT_FIX,
        "재측정에서도 문제가 남았지만 조치하지 않기로 했습니다.",
    ),
    _human(IssueState.RECURRED, IssueState.ACKNOWLEDGED, "재발 사실을 확인했습니다."),
    _human(IssueState.RECURRED, IssueState.IN_PROGRESS, "재발 건에 대한 조치를 시작했습니다."),
    _human(IssueState.RECURRED, IssueState.WONT_FIX, "재발했지만 조치하지 않기로 했습니다."),
    _human(IssueState.WONT_FIX, IssueState.OPEN, "조치하지 않기로 한 결정을 되돌립니다."),
    # --- asking for a targeted re-measurement -------------------------------- #
    Transition(
        IssueState.FIX_CLAIMED,
        IssueState.VERIFYING,
        frozenset({TransitionTrigger.VERIFICATION_REQUEST}),
        "수정 보고에 대한 표적 재검사를 요청했습니다.",
    ),
    Transition(
        IssueState.VERIFICATION_FAILED,
        IssueState.VERIFYING,
        frozenset({TransitionTrigger.VERIFICATION_REQUEST}),
        "실패한 재검사를 다시 요청했습니다. 판정은 다시 측정 결과가 내립니다.",
    ),
    # --- the measurement speaks ---------------------------------------------- #
    Transition(
        IssueState.VERIFYING,
        IssueState.VERIFIED_RESOLVED,
        frozenset({TransitionTrigger.VERIFICATION_OUTCOME}),
        "재측정에서 해당 검사가 통과했습니다. 해결로 인정되는 유일한 경로입니다.",
    ),
    Transition(
        IssueState.VERIFYING,
        IssueState.VERIFICATION_FAILED,
        frozenset({TransitionTrigger.VERIFICATION_OUTCOME}),
        "재측정에서도 검사가 통과하지 못했습니다.",
    ),
    Transition(
        IssueState.VERIFYING,
        IssueState.FIX_CLAIMED,
        frozenset({TransitionTrigger.VERIFICATION_OUTCOME}),
        "재측정이 판정을 내리지 못해(측정 불가) 수정 보고 상태로 되돌립니다.",
    ),
    # --- the problem comes back ---------------------------------------------- #
    Transition(
        IssueState.VERIFIED_RESOLVED,
        IssueState.RECURRED,
        frozenset({TransitionTrigger.RESCAN}),
        "해결 확인된 문제가 새 진단에서 다시 관측되었습니다.",
    ),
)

_INDEX: dict[tuple[IssueState, IssueState], Transition] = {
    (edge.source, edge.target): edge for edge in _EDGES
}

#: The only (trigger, outcome) pair that may reach ``VERIFIED_RESOLVED``.
_RESOLVING_OUTCOME = VerificationOutcome.RESOLVED

_OUTCOME_TARGETS: dict[VerificationOutcome, IssueState] = {
    VerificationOutcome.RESOLVED: IssueState.VERIFIED_RESOLVED,
    VerificationOutcome.STILL_FAILING: IssueState.VERIFICATION_FAILED,
    VerificationOutcome.INCONCLUSIVE: IssueState.FIX_CLAIMED,
}


def legal_transitions() -> tuple[Transition, ...]:
    """Every declared edge. The table is the specification; nothing else is legal."""
    return _EDGES


def transition_for(source: IssueState, target: IssueState) -> Transition | None:
    return _INDEX.get((source, target))


def allowed_targets(
    source: IssueState, *, trigger: TransitionTrigger | None = None
) -> frozenset[IssueState]:
    """Where an issue in ``source`` may go, optionally restricted to one trigger."""
    return frozenset(
        edge.target
        for edge in _EDGES
        if edge.source is source and (trigger is None or trigger in edge.triggers)
    )


def human_transitions_from(source: IssueState) -> tuple[Transition, ...]:
    """The moves a person may make from ``source``, in the order they were declared.

    This exists so that a console can offer buttons without restating the table. A screen
    that keeps its own list of "what you can do next" drifts from this one, and the drift
    always goes the same direction: a button appears for a move the machine refuses, and
    the person clicking it concludes the tool is broken rather than that the move was
    never allowed. There is one table, and callers read it.
    """
    return tuple(
        edge
        for edge in _EDGES
        if edge.source is source and TransitionTrigger.HUMAN in edge.triggers
    )


def is_legal(
    source: IssueState,
    target: IssueState,
    *,
    trigger: TransitionTrigger,
    outcome: VerificationOutcome | None = None,
) -> bool:
    """Whether this exact move is permitted. Never raises."""
    try:
        assert_transition(source, target, trigger=trigger, outcome=outcome)
    except IllegalTransitionError:
        return False
    return True


def assert_transition(
    source: IssueState,
    target: IssueState,
    *,
    trigger: TransitionTrigger,
    outcome: VerificationOutcome | None = None,
) -> Transition:
    """Permit the move or refuse it with a Korean reason.

    The ``VERIFIED_RESOLVED`` guard is checked last and separately from the table, so it
    holds even if someone later adds an edge that ends there: reaching that state always
    requires a verification outcome that says the check passed.
    """
    if source is target:
        raise IllegalTransitionError(
            f"이미 '{describe_state_ko(source)}' 상태입니다. 같은 상태로는 전이할 수 없습니다."
        )

    edge = _INDEX.get((source, target))
    if edge is None:
        raise IllegalTransitionError(_no_such_edge_ko(source, target))

    if trigger not in edge.triggers:
        raise IllegalTransitionError(
            f"'{describe_state_ko(source)}' → '{describe_state_ko(target)}' 전이는 "
            f"{_triggers_ko(edge.triggers)}(으)로만 가능합니다. "
            f"요청한 방식({_trigger_ko(trigger)})으로는 이 상태를 바꿀 수 없습니다."
        )

    if target is IssueState.VERIFIED_RESOLVED and outcome is not _RESOLVING_OUTCOME:
        raise IllegalTransitionError(
            "해결(VERIFIED_RESOLVED)은 표적 재측정에서 해당 검사가 통과했을 때만 기록됩니다. "
            "사람이 '수정함'으로 표시하는 것으로는 해결되지 않습니다. "
            f"(이번 재측정 판정: {_outcome_ko(outcome)})"
        )

    return edge


def state_for_outcome(outcome: VerificationOutcome) -> IssueState:
    """Where a verification result lands an issue. The outcome decides, nothing else."""
    return _OUTCOME_TARGETS[outcome]


def describe_state_ko(state: IssueState) -> str:
    return _STATE_LABELS_KO[state]


def is_open(state: IssueState) -> bool:
    return state in OPEN_STATES


def parse_state(raw: str) -> IssueState:
    """Turn a stored string into a state, refusing anything the machine does not know."""
    try:
        return IssueState(raw)
    except ValueError as exc:
        raise IllegalTransitionError(f"알 수 없는 이슈 상태입니다: {raw}") from exc


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #

_TRIGGER_LABELS_KO: dict[TransitionTrigger, str] = {
    TransitionTrigger.HUMAN: "담당자 조작",
    TransitionTrigger.VERIFICATION_REQUEST: "재검사 요청",
    TransitionTrigger.VERIFICATION_OUTCOME: "재측정 결과",
    TransitionTrigger.RESCAN: "정기 재진단 관측",
}


def _trigger_ko(trigger: TransitionTrigger) -> str:
    return _TRIGGER_LABELS_KO[trigger]


def _triggers_ko(triggers: frozenset[TransitionTrigger]) -> str:
    return "·".join(_trigger_ko(trigger) for trigger in sorted(triggers))


def _outcome_ko(outcome: VerificationOutcome | None) -> str:
    if outcome is None:
        return "재측정 결과 없음"
    return {
        VerificationOutcome.RESOLVED: "통과",
        VerificationOutcome.STILL_FAILING: "여전히 실패",
        VerificationOutcome.INCONCLUSIVE: "측정 불가",
    }[outcome]


def _no_such_edge_ko(source: IssueState, target: IssueState) -> str:
    possible = sorted(allowed_targets(source, trigger=TransitionTrigger.HUMAN))
    if possible:
        options = ", ".join(f"{state.value}({describe_state_ko(state)})" for state in possible)
        tail = f"지금 담당자가 선택할 수 있는 상태는 {options} 입니다."
    else:
        tail = "지금 이 이슈는 담당자 조작으로 바꿀 수 있는 상태가 없습니다."
    return (
        f"'{describe_state_ko(source)}'({source.value}) 상태에서 "
        f"'{describe_state_ko(target)}'({target.value})(으)로는 전이할 수 없습니다. {tail}"
    )


__all__ = [
    "CLOSED_STATES",
    "OPEN_STATES",
    "IllegalTransitionError",
    "IssueState",
    "Transition",
    "TransitionTrigger",
    "VerificationOutcome",
    "allowed_targets",
    "assert_transition",
    "describe_state_ko",
    "human_transitions_from",
    "is_legal",
    "is_open",
    "legal_transitions",
    "parse_state",
    "state_for_outcome",
    "transition_for",
]
