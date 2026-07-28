"""The job state machine and its retry policy.

Two rules drive everything here:

* Only declared transitions are legal. Anything else raises, because a job that quietly
  jumps from ``SUCCEEDED`` back to ``RUNNING`` corrupts every number derived from it.
* A retry sequence always terminates. Attempts are bounded and exhausting them lands in
  ``FAILED_FINAL`` — never in a job that sits in ``FAILED_RETRYABLE`` forever waiting for
  a retry that no longer comes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from veo.contracts import RETRYABLE_ERROR_CODES, TERMINAL_JOB_STATUSES, ErrorCode, JobStatus

__all__ = [
    "LEGAL_TRANSITIONS",
    "FailureOutcome",
    "IllegalTransitionError",
    "JobStateMachine",
    "RetryPolicy",
    "TransitionRecord",
    "is_legal_transition",
]

#: The complete transition table. Terminal statuses map to an empty set: they are final.
LEGAL_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.QUEUED: frozenset(
        {
            JobStatus.RUNNING,
            JobStatus.CANCEL_REQUESTED,
            # A job can be cancelled or expire before a worker ever picks it up.
            JobStatus.CANCELLED,
            JobStatus.EXPIRED,
            JobStatus.FAILED_FINAL,
        }
    ),
    JobStatus.RUNNING: frozenset(
        {
            JobStatus.SUCCEEDED,
            JobStatus.PARTIAL_SUCCESS,
            JobStatus.FAILED_RETRYABLE,
            JobStatus.FAILED_FINAL,
            JobStatus.CANCEL_REQUESTED,
            JobStatus.EXPIRED,
        }
    ),
    JobStatus.FAILED_RETRYABLE: frozenset(
        {
            JobStatus.QUEUED,
            JobStatus.FAILED_FINAL,
            JobStatus.CANCEL_REQUESTED,
            JobStatus.CANCELLED,
            JobStatus.EXPIRED,
        }
    ),
    # A cancel request is cooperative: the task observes it at its next checkpoint. If the
    # work happened to finish first, the real outcome is kept rather than thrown away.
    JobStatus.CANCEL_REQUESTED: frozenset(
        {
            JobStatus.CANCELLED,
            JobStatus.SUCCEEDED,
            JobStatus.PARTIAL_SUCCESS,
            JobStatus.FAILED_FINAL,
            JobStatus.EXPIRED,
        }
    ),
    JobStatus.SUCCEEDED: frozenset(),
    JobStatus.PARTIAL_SUCCESS: frozenset(),
    JobStatus.FAILED_FINAL: frozenset(),
    JobStatus.CANCELLED: frozenset(),
    JobStatus.EXPIRED: frozenset(),
}


def is_legal_transition(source: JobStatus, target: JobStatus) -> bool:
    """Whether ``source`` may move to ``target``. Self-transitions are not legal."""
    return target in LEGAL_TRANSITIONS.get(source, frozenset())


class IllegalTransitionError(RuntimeError):
    """An undeclared status transition was attempted."""

    def __init__(self, source: JobStatus, target: JobStatus) -> None:
        self.source = source
        self.target = target
        terminal = " (terminal states are final)" if source in TERMINAL_JOB_STATUSES else ""
        super().__init__(f"Illegal job transition {source.value} -> {target.value}{terminal}.")


@dataclass(frozen=True, slots=True)
class TransitionRecord:
    source: JobStatus
    target: JobStatus
    at: datetime


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Exponential backoff with jitter and a hard cap on attempts.

    Jitter spreads retries so that a provider outage does not produce a synchronised
    stampede when everything wakes up at once. ``jitter_ratio`` is capped below one third
    so the bands for consecutive attempts cannot overlap: attempt *n+1* always waits
    longer than attempt *n*, which keeps backoff meaningful rather than merely random.
    """

    max_attempts: int = 3
    base_delay_seconds: float = 2.0
    max_delay_seconds: float = 300.0
    jitter_ratio: float = 0.2

    #: Above this the jittered ranges of consecutive attempts would overlap.
    MAX_SAFE_JITTER_RATIO = 1.0 / 3.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")
        if self.base_delay_seconds <= 0:
            raise ValueError("base_delay_seconds must be positive.")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max_delay_seconds must be at least base_delay_seconds.")
        if not 0.0 <= self.jitter_ratio < self.MAX_SAFE_JITTER_RATIO:
            raise ValueError(
                "jitter_ratio must be in [0, 1/3); a wider band would let a later attempt "
                "wait less than an earlier one."
            )

    def compute_backoff(self, attempt: int, *, rng: random.Random | None = None) -> float:
        """Delay in seconds before ``attempt`` is retried. ``attempt`` is 1-based."""
        if attempt < 1:
            raise ValueError("attempt must be 1-based.")
        generator = rng or random.Random()  # noqa: S311 - jitter, not a security decision
        undithered = min(self.base_delay_seconds * (2 ** (attempt - 1)), self.max_delay_seconds)
        dither: float = generator.uniform(1.0 - self.jitter_ratio, 1.0 + self.jitter_ratio)
        return float(min(max(undithered * dither, 0.0), self.max_delay_seconds))

    def is_retryable(self, *, attempt: int, error_code: ErrorCode) -> bool:
        return attempt < self.max_attempts and error_code in RETRYABLE_ERROR_CODES


@dataclass(frozen=True, slots=True)
class FailureOutcome:
    """What the runtime decided to do about a failure."""

    status: JobStatus
    error_code: ErrorCode
    attempt: int
    retry_delay_seconds: float | None
    next_retry_at: datetime | None


@dataclass
class JobStateMachine:
    """Tracks one job's status, attempt count and transition history."""

    status: JobStatus = JobStatus.QUEUED
    policy: RetryPolicy = field(default_factory=RetryPolicy)
    rng: random.Random | None = None
    attempts: int = 0
    history: list[TransitionRecord] = field(default_factory=list)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_JOB_STATUSES

    def transition_to(self, target: JobStatus) -> JobStatus:
        """Move to ``target``, or raise and leave the job untouched."""
        if not is_legal_transition(self.status, target):
            raise IllegalTransitionError(self.status, target)
        source = self.status
        self.status = target
        self.history.append(TransitionRecord(source=source, target=target, at=datetime.now(UTC)))
        return target

    def requeue(self) -> JobStatus:
        """Send a retryable failure back to the queue."""
        return self.transition_to(JobStatus.QUEUED)

    def record_failure(
        self,
        error_code: ErrorCode,
        *,
        retryable: bool | None = None,
    ) -> FailureOutcome:
        """Count an attempt and decide between retrying and giving up.

        ``retryable`` overrides the code's default classification. It exists for failures
        that are technically ``INTERNAL_ERROR`` but that no amount of retrying can fix —
        a missing implementation, for instance.
        """
        self.attempts += 1
        may_retry = (
            self.policy.is_retryable(attempt=self.attempts, error_code=error_code)
            if retryable is None
            else retryable and self.attempts < self.policy.max_attempts
        )

        if may_retry:
            delay = self.policy.compute_backoff(self.attempts, rng=self.rng)
            next_retry_at = datetime.now(UTC) + timedelta(seconds=delay)
            self.transition_to(JobStatus.FAILED_RETRYABLE)
            return FailureOutcome(
                status=JobStatus.FAILED_RETRYABLE,
                error_code=error_code,
                attempt=self.attempts,
                retry_delay_seconds=delay,
                next_retry_at=next_retry_at,
            )

        self.transition_to(JobStatus.FAILED_FINAL)
        return FailureOutcome(
            status=JobStatus.FAILED_FINAL,
            error_code=error_code,
            attempt=self.attempts,
            retry_delay_seconds=None,
            next_retry_at=None,
        )
