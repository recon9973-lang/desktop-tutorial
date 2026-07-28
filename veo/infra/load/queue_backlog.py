"""Queue backlog and recovery: push more work than the workers can take, then stop.

The question is not "how fast is the queue". It is: **when the producers stop, does the
backlog drain, or does the system wedge?** A queue that wedges under overload does not
recover when traffic subsides — it needs a human, at whatever hour the backlog peaked.

What this measures, given a broker:

* peak backlog depth reached while producing,
* whether depth is still falling after production stops,
* time from "last message produced" to "queue empty",
* the drain rate, and the ratio of drain rate to produce rate, which is what tells you
  how long an overload of a given size will take to clear.

------------------------------------------------------------------------------
This cannot be run without a broker, and it will not pretend otherwise.
------------------------------------------------------------------------------

VEO's Celery app falls back to eager mode when ``VEO_BROKER_URL`` is unset (see
``veo_worker.runtime.app``). Eager mode executes tasks inline in the caller: nothing is
enqueued, nothing is consumed, and there is no backlog to drain. Measuring "drain time"
there would produce a number that describes a for-loop.

Kombu's in-process ``memory://`` transport was tried as a stand-in and rejected on
measurement, not on principle. With a real Celery worker (2 threads, 5 ms tasks,
``acks_late`` on and off, ``polling_interval`` lowered to 5 ms) it consumed 16–18 of 60
enqueued messages in 15 seconds and then stopped making progress while 42–44 messages
remained queued. A transport that stalls under exactly the condition being tested cannot
be used to make claims about behaviour under that condition.

So: set ``VEO_LOAD_BROKER_URL`` to a real broker (Redis) and this runs. Leave it unset
and it refuses, prints why, and prints the command to run once you have one. That refusal
is the honest output, and it is the finding.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

__all__ = ["BacklogResult", "BrokerUnavailable", "broker_url", "run_backlog_experiment"]


class BrokerUnavailable(Exception):
    """No broker to queue against. Not a failure of the system under test."""


def broker_url() -> str | None:
    """The broker this harness may use, or ``None``.

    Deliberately a *separate* variable from ``VEO_BROKER_URL``. Reusing the application's
    variable would mean that anyone with a local worker configured could kick off a
    flood against the same broker their real jobs are on.
    """
    raw = os.environ.get("VEO_LOAD_BROKER_URL", "").strip()
    return raw or None


@dataclass(frozen=True, slots=True)
class BacklogResult:
    queue: str
    produced: int
    produce_seconds: float
    peak_depth: int
    depth_at_stop: int
    drained: bool
    drain_seconds: float
    final_depth: int
    samples: list[tuple[float, int]]

    @property
    def produce_rate(self) -> float:
        return self.produced / self.produce_seconds if self.produce_seconds > 0 else 0.0

    @property
    def drain_rate(self) -> float:
        if self.drain_seconds <= 0:
            return 0.0
        return (self.depth_at_stop - self.final_depth) / self.drain_seconds

    def render(self) -> str:
        lines = [
            f"  queue          : {self.queue}",
            (
                f"  produced       : {self.produced} in {self.produce_seconds:.2f}s "
                f"({self.produce_rate:.1f}/s)"
            ),
            f"  peak backlog   : {self.peak_depth}",
            f"  depth at stop  : {self.depth_at_stop}",
        ]
        if self.drained:
            lines += [
                (
                    f"  drained in     : {self.drain_seconds:.2f}s "
                    f"({self.drain_rate:.1f}/s)"
                ),
                "  verdict        : DRAINED — the backlog cleared without intervention",
            ]
        else:
            lines += [
                (
                    f"  after {self.drain_seconds:.0f}s   : {self.final_depth} still "
                    f"queued ({self.drain_rate:.1f}/s drain)"
                ),
                (
                    "  verdict        : DID NOT DRAIN — treat as a wedge and investigate"
                    " before shipping. See runbook-incident-response.md §2."
                ),
            ]
        return "\n".join(lines)


def _queue_depth(app: object, queue: str) -> int:
    """Messages sitting in ``queue``, asked of the broker itself.

    Not derived from what the producer sent: the whole point is to observe the queue,
    and a counter maintained by the producer would happily report a drain that never
    happened.
    """
    with app.connection_or_acquire() as connection:  # type: ignore[attr-defined]
        declared = connection.default_channel.queue_declare(queue=queue, passive=True)
        return int(declared.message_count)


def run_backlog_experiment(
    *,
    job_type_name: str = "SEO_SCAN",
    produce: int = 2_000,
    drain_timeout_seconds: float = 120.0,
    poll_seconds: float = 0.25,
) -> BacklogResult:
    """Flood one VEO queue, stop, and watch whether it empties.

    Raises :class:`BrokerUnavailable` when ``VEO_LOAD_BROKER_URL`` is not set. The tasks
    submitted are VEO's own registered tasks with a synthetic job id; in Phase 0 they
    raise ``NotImplementedError`` inside the worker, which is fine and is in fact the
    cleaner measurement — a task that fails fast still has to be delivered, executed,
    acknowledged and (per ``task_acks_on_failure_or_timeout``) removed, so this measures
    the queue machinery rather than the analysis code that happens to sit behind it.
    """
    url = broker_url()
    if url is None:
        raise BrokerUnavailable(
            "VEO_LOAD_BROKER_URL is not set, so there is no queue to build a backlog in.\n"
            "Without a broker the worker runs eagerly: tasks execute inline in the caller, "
            "nothing is enqueued and nothing drains.\n"
            "Run this against a real broker:\n"
            "    VEO_LOAD_BROKER_URL=redis://localhost:6379/1 \\\n"
            "        .venv/bin/python infra/load/run.py --only queue\n"
            "Reporting a drain time from eager mode would be reporting the speed of a "
            "for-loop and calling it queue recovery."
        )

    import uuid

    from veo.contracts import JobType
    from veo_worker.runtime.app import (
        WorkerSettings,
        create_celery_app,
        queue_for_job_type,
    )
    from veo_worker.runtime.tasks import TASK_NAME_BY_JOB_TYPE

    job_type = JobType[job_type_name]
    queue = queue_for_job_type(job_type)
    task_name = TASK_NAME_BY_JOB_TYPE[job_type]

    app = create_celery_app(WorkerSettings(broker_url=url))

    starting_depth = _queue_depth(app, queue)
    if starting_depth:
        raise RuntimeError(
            f"queue {queue!r} already holds {starting_depth} messages. Refusing to add "
            "load on top of somebody else's backlog — point VEO_LOAD_BROKER_URL at a "
            "broker and database index nobody is using."
        )

    samples: list[tuple[float, int]] = []
    peak = 0
    started = time.perf_counter()

    for _ in range(produce):
        app.send_task(task_name, kwargs={"job_id": str(uuid.uuid4())}, queue=queue)
        depth = _queue_depth(app, queue)
        peak = max(peak, depth)

    produce_seconds = time.perf_counter() - started
    depth_at_stop = _queue_depth(app, queue)
    peak = max(peak, depth_at_stop)

    # Production has stopped. Everything from here is recovery.
    drain_started = time.perf_counter()
    depth = depth_at_stop
    while depth > 0 and (time.perf_counter() - drain_started) < drain_timeout_seconds:
        time.sleep(poll_seconds)
        depth = _queue_depth(app, queue)
        samples.append((time.perf_counter() - drain_started, depth))

    drain_seconds = time.perf_counter() - drain_started

    return BacklogResult(
        queue=queue,
        produced=produce,
        produce_seconds=produce_seconds,
        peak_depth=peak,
        depth_at_stop=depth_at_stop,
        drained=depth == 0,
        drain_seconds=drain_seconds,
        final_depth=depth,
        samples=samples,
    )
