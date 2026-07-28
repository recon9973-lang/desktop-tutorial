"""The Celery application factory and queue topology.

Job families get their own queues so a slow site crawl cannot starve a keyword lookup,
and so each family can be scaled independently.

Delivery settings are deliberately pessimistic: ``acks_late`` plus
``task_reject_on_worker_lost`` mean a job survives a worker being killed, and a prefetch
of 1 stops a single worker from hoarding messages it will not get to. That combination
makes delivery at-least-once, which is exactly why :mod:`veo_worker.runtime.idempotency`
exists.

Serialisation is JSON only. Pickle is never accepted: a broker that can be written to
would otherwise be remote code execution.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from celery import Celery
from kombu import Queue
from veo.contracts import JobType

__all__ = [
    "DEAD_LETTER_QUEUE",
    "JOB_TYPE_QUEUES",
    "QUEUE_NAMES",
    "TASK_QUEUE_OVERRIDES",
    "WorkerSettings",
    "celery_app",
    "create_celery_app",
    "queue_for_job_type",
    "register_task_queue",
    "route_task",
]

logger = logging.getLogger(__name__)

#: One queue per job-type family.
QUEUE_NAMES: tuple[str, ...] = ("crawl", "seo", "geo", "keyword", "report")

#: Where messages go when nothing claims them. Nothing is silently dropped.
DEAD_LETTER_QUEUE = "dead_letter"

#: Exhaustive map from job type to queue. A new JobType without an entry fails the
#: contract test in ``tests/test_app.py`` rather than quietly landing in a default queue.
JOB_TYPE_QUEUES: dict[JobType, str] = {
    JobType.SITE_CRAWL: "crawl",
    JobType.SEO_SCAN: "seo",
    JobType.REVERIFICATION: "seo",
    JobType.COMPETITOR_COMPARISON: "seo",
    JobType.GEO_READINESS_SCAN: "geo",
    JobType.GEO_OBSERVATION_RUN: "geo",
    JobType.KEYWORD_LOOKUP: "keyword",
    JobType.REPORT_EXPORT: "report",
}

#: Task name -> queue, populated by :func:`register_task_queue` as tasks are declared.
TASK_QUEUE_OVERRIDES: dict[str, str] = {}


def queue_for_job_type(job_type: JobType) -> str:
    try:
        return JOB_TYPE_QUEUES[job_type]
    except KeyError:  # pragma: no cover - guarded by an exhaustiveness test
        raise KeyError(
            f"{job_type} has no queue. Add it to JOB_TYPE_QUEUES rather than relying on a default."
        ) from None


def register_task_queue(task_name: str, queue: str) -> None:
    if queue not in (*QUEUE_NAMES, DEAD_LETTER_QUEUE):
        raise ValueError(f"Unknown queue {queue!r}; declared queues are {QUEUE_NAMES}.")
    TASK_QUEUE_OVERRIDES[task_name] = queue


def route_task(name: str, *_args: object, **_kwargs: object) -> dict[str, str]:
    """Celery ``task_routes`` callable.

    An unrecognised task name goes to the dead-letter queue instead of a real one. A
    message nobody can handle should be visible and inspectable, not mixed into the
    stream of work a live queue is trying to get through.
    """
    queue = TASK_QUEUE_OVERRIDES.get(name)
    if queue is None:
        logger.warning(
            "No queue registered for task %r; routing to the %s queue.", name, DEAD_LETTER_QUEUE
        )
        return {"queue": DEAD_LETTER_QUEUE}
    return {"queue": queue}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer; got {raw!r}.") from None


def _env_str(name: str) -> str | None:
    raw = os.environ.get(name)
    return raw.strip() if raw and raw.strip() else None


@dataclass(frozen=True, slots=True)
class WorkerSettings:
    """Runtime configuration, read from the environment.

    With no broker URL the app configures itself eagerly and says so. That keeps tests
    and local exploration working without Redis, and — because it is loud — nobody
    mistakes an eager process for a real worker consuming a real queue.
    """

    broker_url: str | None = None
    result_backend_url: str | None = None
    task_time_limit: int = 1800
    task_soft_time_limit: int = 1500
    result_expires: int = 86_400
    worker_max_tasks_per_child: int = 200
    max_attempts: int = 3
    queues: tuple[str, ...] = field(default=QUEUE_NAMES)

    def __post_init__(self) -> None:
        if self.task_soft_time_limit >= self.task_time_limit:
            raise ValueError(
                "task_soft_time_limit must be below task_time_limit so the task gets a "
                "chance to clean up before it is killed."
            )
        if self.task_soft_time_limit <= 0:
            raise ValueError("task_soft_time_limit must be positive.")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")

    @property
    def is_eager(self) -> bool:
        return self.broker_url is None

    @classmethod
    def from_env(cls) -> WorkerSettings:
        return cls(
            broker_url=_env_str("VEO_BROKER_URL"),
            result_backend_url=_env_str("VEO_RESULT_BACKEND_URL"),
            task_time_limit=_env_int("VEO_WORKER_TASK_TIME_LIMIT", 1800),
            task_soft_time_limit=_env_int("VEO_WORKER_TASK_SOFT_TIME_LIMIT", 1500),
            result_expires=_env_int("VEO_WORKER_RESULT_EXPIRES", 86_400),
            worker_max_tasks_per_child=_env_int("VEO_WORKER_MAX_TASKS_PER_CHILD", 200),
            max_attempts=_env_int("VEO_WORKER_MAX_ATTEMPTS", 3),
        )


def create_celery_app(settings: WorkerSettings | None = None) -> Celery:
    """Build a configured Celery application."""
    settings = settings or WorkerSettings.from_env()
    app = Celery("veo_worker")

    queues = [Queue(name, routing_key=name) for name in settings.queues]
    queues.append(Queue(DEAD_LETTER_QUEUE, routing_key=DEAD_LETTER_QUEUE))

    app.conf.update(
        # --- transport -------------------------------------------------------
        broker_url=settings.broker_url or "memory://localhost/",
        result_backend=settings.result_backend_url or "cache+memory://",
        broker_connection_retry_on_startup=True,
        # --- serialisation: JSON only, never pickle --------------------------
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        result_accept_content=["json"],
        # --- delivery guarantees --------------------------------------------
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_acks_on_failure_or_timeout=True,
        worker_prefetch_multiplier=1,
        # --- limits ----------------------------------------------------------
        task_time_limit=settings.task_time_limit,
        task_soft_time_limit=settings.task_soft_time_limit,
        result_expires=settings.result_expires,
        worker_max_tasks_per_child=settings.worker_max_tasks_per_child,
        # --- routing ---------------------------------------------------------
        task_queues=queues,
        task_routes=(route_task,),
        task_default_queue=DEAD_LETTER_QUEUE,
        task_default_routing_key=DEAD_LETTER_QUEUE,
        task_create_missing_queues=False,
        # --- misc ------------------------------------------------------------
        timezone="Asia/Seoul",
        enable_utc=True,
        task_track_started=True,
        task_always_eager=settings.is_eager,
        task_eager_propagates=settings.is_eager,
    )

    if settings.is_eager:
        logger.warning(
            "VEO_BROKER_URL is not set. Running Celery in EAGER mode: tasks execute "
            "in-process and synchronously, nothing is queued, and no worker is consuming. "
            "This is fine for tests and local exploration and is NOT a production setup."
        )

    return app


#: Module-level app for the Celery CLI: ``celery -A veo_worker.runtime.app:celery_app worker``.
celery_app = create_celery_app()
