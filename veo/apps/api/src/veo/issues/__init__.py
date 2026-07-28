"""Issue lifecycle: from a collector's finding to a verified, re-measured resolution.

The rule that defines this package:

    **An issue is closed by a re-measurement, not by someone clicking "done".**

A person may mark an issue *fix claimed* — "I changed something". Only a targeted re-scan
of the affected URLs, judged against the same published specification that found the
problem, can move it to *verified resolved*. The two are separate states and the state
machine has no edge that lets a human write the second one. A tool that lets people close
their own findings produces clean dashboards and unchanged websites.

Module map:

``lifecycle``
    The states and the table of legal transitions, each with the triggers that may walk
    it. Anything not in the table is refused with a Korean reason.
``identity``
    The fingerprint over ``(check_id, normalised affected URL set)`` that makes the same
    problem in two scans one issue with history rather than two rows.
``recurrence``
    Cycles: how many times a verified-resolved problem came back, and when each cycle
    opened, closed and reopened.
``verification``
    The targeted re-scan request — the affected URLs and one check, never a whole site —
    and the derivation of a verdict from what was actually measured.
``service`` / ``schemas`` / ``router``
    Persistence, payloads and the HTTP surface. The router is not mounted; see
    ``INTEGRATION_REQUEST.md``.
"""

from veo.issues.identity import (
    fingerprint_of_draft,
    issue_fingerprint,
    normalize_affected_urls,
)
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
from veo.issues.recurrence import RecurrenceCycle, RecurrenceHistory, build_history
from veo.issues.verification import (
    MeasuredCheck,
    VerificationRequest,
    VerificationScopeError,
    VerificationVerdict,
    build_verification_request,
    derive_outcome,
)

__all__ = [
    "CLOSED_STATES",
    "OPEN_STATES",
    "IllegalTransitionError",
    "IssueState",
    "MeasuredCheck",
    "RecurrenceCycle",
    "RecurrenceHistory",
    "TransitionTrigger",
    "VerificationOutcome",
    "VerificationRequest",
    "VerificationScopeError",
    "VerificationVerdict",
    "allowed_targets",
    "assert_transition",
    "build_history",
    "build_verification_request",
    "derive_outcome",
    "describe_state_ko",
    "fingerprint_of_draft",
    "is_legal",
    "issue_fingerprint",
    "legal_transitions",
    "normalize_affected_urls",
    "state_for_outcome",
]
