"""Cooperative cancellation.

Killing a worker mid-write leaves half-written rows and a job whose status nobody can
trust. Instead, a cancel request only sets a flag. The task body polls that flag at
checkpoints — between stages, between batches — and stops at the next safe point.

So a cancel is not instantaneous, and it is not supposed to be. It is *bounded*: the
task reaches ``CANCELLED`` at its next checkpoint, with its data consistent.
"""

from __future__ import annotations

import threading

__all__ = [
    "CANCELLATION_REGISTRY",
    "CancellationRegistry",
    "CancellationToken",
    "InMemoryCancellationRegistry",
    "JobCancelledError",
]


class JobCancelledError(Exception):
    """Raised at a checkpoint when cancellation has been requested."""

    def __init__(self, *, job_id: str, stage_key: str | None = None, reason: str | None = None):
        self.job_id = job_id
        self.stage_key = stage_key
        self.reason = reason
        where = f" at stage {stage_key!r}" if stage_key else ""
        super().__init__(f"Job {job_id} was cancelled{where}.")


class CancellationToken:
    """A thread-safe flag shared between the requester and the running task."""

    __slots__ = ("_job_id", "_lock", "_reason", "_requested")

    def __init__(self, job_id: str) -> None:
        self._job_id = job_id
        self._lock = threading.Lock()
        self._requested = False
        self._reason: str | None = None

    @property
    def job_id(self) -> str:
        return self._job_id

    @property
    def is_cancellation_requested(self) -> bool:
        with self._lock:
            return self._requested

    @property
    def reason(self) -> str | None:
        with self._lock:
            return self._reason

    def request(self, reason: str | None = None) -> bool:
        """Ask the task to stop. Idempotent; the first reason given is kept.

        Returns ``True`` if this call was the one that flipped the flag.
        """
        with self._lock:
            if self._requested:
                return False
            self._requested = True
            self._reason = reason
            return True

    def checkpoint(self, stage_key: str | None = None) -> None:
        """Stop here if cancellation was requested. Call between units of work."""
        with self._lock:
            requested, reason = self._requested, self._reason
        if requested:
            raise JobCancelledError(job_id=self._job_id, stage_key=stage_key, reason=reason)


class CancellationRegistry:
    """Protocol-shaped base: maps job ids to tokens so the API can reach a running task."""

    def issue(self, job_id: str) -> CancellationToken:  # pragma: no cover - interface
        raise NotImplementedError

    def get(self, job_id: str) -> CancellationToken | None:  # pragma: no cover - interface
        raise NotImplementedError

    def request_cancel(self, job_id: str, reason: str | None = None) -> bool:  # pragma: no cover
        raise NotImplementedError

    def release(self, job_id: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class InMemoryCancellationRegistry(CancellationRegistry):
    """Process-local registry.

    Real deployments run many worker processes, so a cancel arriving at the API must be
    published to the process that owns the job (a Redis key the token polls, for example).
    The protocol above is what that implementation has to satisfy; Phase 0 ships the
    in-process version so the semantics are pinned down and tested first.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tokens: dict[str, CancellationToken] = {}
        self._pending: dict[str, str | None] = {}

    def issue(self, job_id: str) -> CancellationToken:
        """Hand out the token for ``job_id``, applying any cancel that arrived early."""
        with self._lock:
            token = self._tokens.get(job_id)
            if token is None:
                token = CancellationToken(job_id)
                self._tokens[job_id] = token
                if job_id in self._pending:
                    token.request(self._pending.pop(job_id))
            return token

    def get(self, job_id: str) -> CancellationToken | None:
        with self._lock:
            return self._tokens.get(job_id)

    def request_cancel(self, job_id: str, reason: str | None = None) -> bool:
        """Request cancellation of a job that is already running.

        Returns ``False`` when no token exists, so the caller can tell the difference
        between "asked" and "there was nothing to ask".
        """
        token = self.get(job_id)
        if token is None:
            return False
        token.request(reason)
        return True

    def request_cancel_ahead_of_time(self, job_id: str, reason: str | None = None) -> None:
        """Record a cancel for a job whose worker has not started yet.

        Without this, a cancel that races the dequeue would be lost and the job would run
        to completion after the user asked it to stop.
        """
        with self._lock:
            token = self._tokens.get(job_id)
            if token is not None:
                token.request(reason)
                return
            self._pending.setdefault(job_id, reason)

    def release(self, job_id: str) -> None:
        with self._lock:
            self._tokens.pop(job_id, None)
            self._pending.pop(job_id, None)

    def clear(self) -> None:
        with self._lock:
            self._tokens.clear()
            self._pending.clear()


#: Default process-local registry used by the Phase 0 task stubs.
CANCELLATION_REGISTRY = InMemoryCancellationRegistry()
