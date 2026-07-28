"""The façade a task body drives, and the store the API reads.

:class:`JobRuntime` wires the state machine, progress tracker, cancellation token and
partial-result accumulator into one object, and re-publishes a
:class:`~veo.contracts.JobDescriptor` after every meaningful change. That descriptor is
the single thing the API needs to read; nothing else about the worker is public.
"""

from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from veo.contracts import JobDescriptor, JobStatus, JobType, Surface

from veo_worker.runtime.cancellation import (
    CANCELLATION_REGISTRY,
    CancellationRegistry,
    CancellationToken,
    JobCancelledError,
)
from veo_worker.runtime.errors import SafeError, to_safe_error
from veo_worker.runtime.partial import PartialResultAccumulator
from veo_worker.runtime.progress import ProgressTracker, StageDefinition
from veo_worker.runtime.state import JobStateMachine, RetryPolicy

__all__ = [
    "JOB_STORE",
    "InMemoryJobStore",
    "JobRuntime",
    "JobStore",
]


@runtime_checkable
class JobStore(Protocol):
    """Where job descriptors are published for the API to read."""

    def save(self, descriptor: JobDescriptor) -> None: ...

    def get(self, job_id: str) -> JobDescriptor | None: ...


class InMemoryJobStore:
    """Process-local job store for Phase 0.

    The durable implementation is the API's database. This exists so the runtime's
    contract — "every transition publishes a descriptor" — is testable now, without
    the worker growing its own opinion about persistence.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, JobDescriptor] = {}

    def save(self, descriptor: JobDescriptor) -> None:
        with self._lock:
            self._jobs[descriptor.job_id] = descriptor.model_copy(deep=True)

    def get(self, job_id: str) -> JobDescriptor | None:
        with self._lock:
            found = self._jobs.get(job_id)
            return found.model_copy(deep=True) if found else None

    def clear(self) -> None:
        with self._lock:
            self._jobs.clear()


#: Default store used by the Phase 0 task stubs.
JOB_STORE = InMemoryJobStore()


@dataclass
class JobRuntime:
    """Drives one job run and keeps its published descriptor current."""

    job_id: str
    job_type: JobType
    surface: Surface
    input_hash: str
    machine: JobStateMachine
    tracker: ProgressTracker
    token: CancellationToken
    partial: PartialResultAccumulator
    store: JobStore
    registry: CancellationRegistry
    idempotency_key: str | None = None
    organization_id: str | None = None
    project_id: str | None = None
    requested_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    next_retry_at: datetime | None = None
    safe_error: SafeError | None = None

    # -- construction --------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        job_id: str,
        job_type: JobType,
        surface: Surface,
        input_hash: str,
        stages: list[StageDefinition],
        unit_label: str = "unit",
        idempotency_key: str | None = None,
        organization_id: str | None = None,
        project_id: str | None = None,
        requested_by: str | None = None,
        policy: RetryPolicy | None = None,
        store: JobStore | None = None,
        registry: CancellationRegistry | None = None,
        rng: random.Random | None = None,
    ) -> JobRuntime:
        resolved_registry = registry or CANCELLATION_REGISTRY
        runtime = cls(
            job_id=job_id,
            job_type=job_type,
            surface=surface,
            input_hash=input_hash,
            machine=JobStateMachine(policy=policy or RetryPolicy(), rng=rng),
            tracker=ProgressTracker(stages),
            token=resolved_registry.issue(job_id),
            partial=PartialResultAccumulator(unit_label=unit_label),
            store=store or JOB_STORE,
            registry=resolved_registry,
            idempotency_key=idempotency_key,
            organization_id=organization_id,
            project_id=project_id,
            requested_by=requested_by,
        )
        runtime.publish()
        return runtime

    # -- descriptor ----------------------------------------------------------

    def descriptor(self) -> JobDescriptor:
        snapshot = self.tracker.snapshot()
        return JobDescriptor(
            job_id=self.job_id,
            type=self.job_type,
            surface=self.surface,
            status=self.machine.status,
            progress=snapshot.progress,
            current_stage=snapshot.current_stage,
            stages=snapshot.stages,
            organization_id=self.organization_id,
            project_id=self.project_id,
            requested_by=self.requested_by,
            idempotency_key=self.idempotency_key,
            input_hash=self.input_hash,
            created_at=self.created_at,
            started_at=self.started_at,
            finished_at=self.finished_at,
            attempts=self.machine.attempts,
            max_attempts=self.machine.policy.max_attempts,
            next_retry_at=self.next_retry_at,
            error_code=self.safe_error.code if self.safe_error else None,
            safe_error_message=self.safe_error.message if self.safe_error else None,
            internal_error_ref=self.safe_error.internal_error_ref if self.safe_error else None,
            # Phase 0 runs no collectors, so there is never a result to point at.
            result_run_id=None,
            partial_result_available=False,
        )

    def publish(self) -> JobDescriptor:
        descriptor = self.descriptor()
        self.store.save(descriptor)
        return descriptor

    # -- lifecycle -----------------------------------------------------------

    def begin(self) -> None:
        """QUEUED -> RUNNING."""
        self.machine.transition_to(JobStatus.RUNNING)
        self.started_at = datetime.now(UTC)
        self.publish()

    def checkpoint(self, stage_key: str | None = None) -> None:
        """Cooperative cancellation point. Raises :class:`JobCancelledError` when asked."""
        self.token.checkpoint(stage_key)

    def begin_stage(self, key: str) -> None:
        self.tracker.begin(key)
        self.publish()

    def advance_stage(self, key: str, *, items_done: int, items_total: int | None = None) -> None:
        self.tracker.advance(key, items_done=items_done, items_total=items_total)
        self.publish()

    def complete_stage(self, key: str, *, status: JobStatus = JobStatus.SUCCEEDED) -> None:
        self.tracker.complete(key, status=status)
        self.publish()

    def finish(self) -> JobDescriptor:
        """Close the job with the status the collected counts actually justify."""
        outcome = self.partial.resolve()
        self.machine.transition_to(outcome.status)
        self.finished_at = datetime.now(UTC)
        return self.publish()

    def _close_running_stage(self, status: JobStatus) -> None:
        """Stop an in-flight stage from outliving the job it belongs to.

        A terminal job whose stage still reads ``RUNNING`` makes the console show a
        spinner forever, so the stage is closed with the same verdict as the job.
        """
        key = self.tracker.current_stage
        if key is None:
            return
        stage = next((s for s in self.tracker.stages if s.key == key), None)
        if stage is not None and stage.status is JobStatus.RUNNING:
            self.tracker.complete(key, status=status)

    def cancelled(self, exc: JobCancelledError) -> JobDescriptor:
        """Land a cooperative cancellation as ``CANCELLED``."""
        if self.machine.status is not JobStatus.CANCEL_REQUESTED:
            self.machine.transition_to(JobStatus.CANCEL_REQUESTED)
        self._close_running_stage(JobStatus.CANCELLED)
        self.machine.transition_to(JobStatus.CANCELLED)
        self.safe_error = to_safe_error(exc)
        self.finished_at = datetime.now(UTC)
        return self.publish()

    def fail(self, exc: BaseException) -> JobDescriptor:
        """Record a failure and let the retry policy decide what happens next."""
        safe = to_safe_error(exc)
        self.safe_error = safe
        outcome = self.machine.record_failure(safe.code, retryable=safe.retryable)
        self.next_retry_at = outcome.next_retry_at
        if outcome.status is JobStatus.FAILED_FINAL:
            self._close_running_stage(JobStatus.FAILED_FINAL)
            self.finished_at = datetime.now(UTC)
        return self.publish()

    def release(self) -> None:
        """Drop the cancellation token once the run is over."""
        self.registry.release(self.job_id)
