from __future__ import annotations

import random

import pytest
from veo.contracts import TERMINAL_JOB_STATUSES, ErrorCode, JobStatus

from veo_worker.runtime.state import (
    IllegalTransitionError,
    JobStateMachine,
    RetryPolicy,
    is_legal_transition,
)

LEGAL = [
    (JobStatus.QUEUED, JobStatus.RUNNING),
    (JobStatus.QUEUED, JobStatus.CANCEL_REQUESTED),
    (JobStatus.QUEUED, JobStatus.CANCELLED),
    (JobStatus.QUEUED, JobStatus.EXPIRED),
    (JobStatus.RUNNING, JobStatus.SUCCEEDED),
    (JobStatus.RUNNING, JobStatus.PARTIAL_SUCCESS),
    (JobStatus.RUNNING, JobStatus.FAILED_RETRYABLE),
    (JobStatus.RUNNING, JobStatus.FAILED_FINAL),
    (JobStatus.RUNNING, JobStatus.CANCEL_REQUESTED),
    (JobStatus.FAILED_RETRYABLE, JobStatus.QUEUED),
    (JobStatus.FAILED_RETRYABLE, JobStatus.FAILED_FINAL),
    (JobStatus.CANCEL_REQUESTED, JobStatus.CANCELLED),
    (JobStatus.CANCEL_REQUESTED, JobStatus.SUCCEEDED),
    (JobStatus.CANCEL_REQUESTED, JobStatus.PARTIAL_SUCCESS),
]

ILLEGAL = [
    (JobStatus.QUEUED, JobStatus.SUCCEEDED),
    (JobStatus.QUEUED, JobStatus.PARTIAL_SUCCESS),
    (JobStatus.RUNNING, JobStatus.QUEUED),
    (JobStatus.RUNNING, JobStatus.CANCELLED),
    (JobStatus.SUCCEEDED, JobStatus.RUNNING),
    (JobStatus.SUCCEEDED, JobStatus.FAILED_FINAL),
    (JobStatus.FAILED_FINAL, JobStatus.RUNNING),
    (JobStatus.FAILED_FINAL, JobStatus.QUEUED),
    (JobStatus.CANCELLED, JobStatus.RUNNING),
    (JobStatus.PARTIAL_SUCCESS, JobStatus.SUCCEEDED),
    (JobStatus.EXPIRED, JobStatus.RUNNING),
    (JobStatus.CANCEL_REQUESTED, JobStatus.RUNNING),
]


class TestTransitionTable:
    @pytest.mark.parametrize(("source", "target"), LEGAL)
    def test_legal_transitions_are_accepted(self, source: JobStatus, target: JobStatus) -> None:
        assert is_legal_transition(source, target) is True
        machine = JobStateMachine(status=source)
        machine.transition_to(target)
        assert machine.status is target

    @pytest.mark.parametrize(("source", "target"), ILLEGAL)
    def test_illegal_transitions_raise(self, source: JobStatus, target: JobStatus) -> None:
        assert is_legal_transition(source, target) is False
        machine = JobStateMachine(status=source)
        with pytest.raises(IllegalTransitionError) as excinfo:
            machine.transition_to(target)
        assert excinfo.value.source is source
        assert excinfo.value.target is target
        assert machine.status is source, "a rejected transition must not mutate the job"

    @pytest.mark.parametrize("terminal", sorted(TERMINAL_JOB_STATUSES))
    def test_terminal_states_have_no_outgoing_transitions(self, terminal: JobStatus) -> None:
        for target in JobStatus:
            assert is_legal_transition(terminal, target) is False

    def test_self_transition_is_illegal(self) -> None:
        assert is_legal_transition(JobStatus.RUNNING, JobStatus.RUNNING) is False

    def test_history_is_recorded(self) -> None:
        machine = JobStateMachine()
        machine.transition_to(JobStatus.RUNNING)
        machine.transition_to(JobStatus.SUCCEEDED)
        assert [entry.target for entry in machine.history] == [
            JobStatus.RUNNING,
            JobStatus.SUCCEEDED,
        ]

    def test_cancel_path_reaches_cancelled(self) -> None:
        machine = JobStateMachine()
        machine.transition_to(JobStatus.RUNNING)
        machine.transition_to(JobStatus.CANCEL_REQUESTED)
        machine.transition_to(JobStatus.CANCELLED)
        assert machine.status is JobStatus.CANCELLED
        assert machine.is_terminal is True


class TestRetryPolicy:
    def test_backoff_increases_with_attempt(self) -> None:
        policy = RetryPolicy(max_attempts=6, base_delay_seconds=2.0, max_delay_seconds=1000.0)
        rng = random.Random(7)
        delays = [policy.compute_backoff(attempt, rng=rng) for attempt in range(1, 6)]
        assert delays == sorted(delays)
        assert len(set(delays)) == len(delays)

    def test_backoff_is_bounded_by_max_delay(self) -> None:
        policy = RetryPolicy(max_attempts=40, base_delay_seconds=2.0, max_delay_seconds=30.0)
        rng = random.Random(11)
        for attempt in range(1, 40):
            delay = policy.compute_backoff(attempt, rng=rng)
            assert 0.0 < delay <= 30.0

    def test_backoff_includes_jitter(self) -> None:
        policy = RetryPolicy(base_delay_seconds=10.0, max_delay_seconds=10_000.0)
        samples = {policy.compute_backoff(3, rng=random.Random(seed)) for seed in range(40)}
        assert len(samples) > 1, "backoff must be jittered, not a fixed schedule"
        undithered = 10.0 * 2**2
        assert min(samples) < undithered < max(samples)

    def test_jitter_stays_within_the_declared_band(self) -> None:
        policy = RetryPolicy(
            base_delay_seconds=10.0, max_delay_seconds=10_000.0, jitter_ratio=0.25
        )
        undithered = 10.0 * 2**2
        for seed in range(200):
            delay = policy.compute_backoff(3, rng=random.Random(seed))
            assert undithered * 0.75 <= delay <= undithered * 1.25

    def test_monotonicity_holds_even_at_jitter_extremes(self) -> None:
        policy = RetryPolicy(base_delay_seconds=10.0, max_delay_seconds=10_000.0, jitter_ratio=0.3)
        for attempt in range(1, 6):
            lo_next = min(
                policy.compute_backoff(attempt + 1, rng=random.Random(s)) for s in range(200)
            )
            hi_this = max(policy.compute_backoff(attempt, rng=random.Random(s)) for s in range(200))
            assert hi_this < lo_next

    def test_jitter_ratio_that_would_break_monotonicity_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="jitter_ratio"):
            RetryPolicy(jitter_ratio=0.5)

    def test_attempt_count_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="max_attempts"):
            RetryPolicy(max_attempts=0)


class TestFailureHandling:
    def _running(self, policy: RetryPolicy | None = None) -> JobStateMachine:
        machine = JobStateMachine(
            policy=policy or RetryPolicy(max_attempts=3), rng=random.Random(3)
        )
        machine.transition_to(JobStatus.RUNNING)
        return machine

    def test_retryable_error_below_the_cap_is_retryable(self) -> None:
        machine = self._running()
        outcome = machine.record_failure(ErrorCode.PROVIDER_UNAVAILABLE)
        assert outcome.status is JobStatus.FAILED_RETRYABLE
        assert outcome.attempt == 1
        assert outcome.retry_delay_seconds is not None
        assert outcome.retry_delay_seconds > 0

    def test_non_retryable_error_fails_finally_on_the_first_attempt(self) -> None:
        machine = self._running()
        outcome = machine.record_failure(ErrorCode.TARGET_URL_REJECTED)
        assert outcome.status is JobStatus.FAILED_FINAL
        assert outcome.retry_delay_seconds is None
        assert machine.status is JobStatus.FAILED_FINAL

    def test_explicit_non_retryable_override_wins(self) -> None:
        machine = self._running()
        outcome = machine.record_failure(ErrorCode.INTERNAL_ERROR, retryable=False)
        assert outcome.status is JobStatus.FAILED_FINAL

    def test_exhausting_retries_ends_in_failed_final(self) -> None:
        policy = RetryPolicy(max_attempts=3, base_delay_seconds=1.0, max_delay_seconds=60.0)
        machine = JobStateMachine(policy=policy, rng=random.Random(5))
        seen: list[JobStatus] = []

        for _ in range(policy.max_attempts):
            machine.transition_to(JobStatus.RUNNING)
            outcome = machine.record_failure(ErrorCode.PROVIDER_UNAVAILABLE)
            seen.append(outcome.status)
            if outcome.status is JobStatus.FAILED_RETRYABLE:
                machine.requeue()

        assert seen == [
            JobStatus.FAILED_RETRYABLE,
            JobStatus.FAILED_RETRYABLE,
            JobStatus.FAILED_FINAL,
        ]
        assert machine.status is JobStatus.FAILED_FINAL
        assert machine.attempts == 3
        assert machine.is_terminal is True

    def test_retry_never_stalls_short_of_a_terminal_state(self) -> None:
        policy = RetryPolicy(max_attempts=5, base_delay_seconds=1.0, max_delay_seconds=10.0)
        machine = JobStateMachine(policy=policy, rng=random.Random(1))
        for _ in range(50):
            if machine.is_terminal:
                break
            if machine.status is JobStatus.FAILED_RETRYABLE:
                machine.requeue()
            if machine.status is JobStatus.QUEUED:
                machine.transition_to(JobStatus.RUNNING)
            machine.record_failure(ErrorCode.RATE_LIMITED)
        assert machine.status is JobStatus.FAILED_FINAL

    def test_requeue_from_a_non_retryable_state_is_illegal(self) -> None:
        machine = self._running()
        machine.record_failure(ErrorCode.TARGET_URL_REJECTED)
        with pytest.raises(IllegalTransitionError):
            machine.requeue()
