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

# 큐 지형도는 **보내는 쪽과 나눠 갖는다**. 원래 이 파일에만 있었는데, 메시지를 보내는
# 것은 API 다. 보내는 쪽이 이 표를 못 보면 이름을 손으로 옮겨 적게 되고, 한쪽만
# 고쳐지는 날 메시지는 아무도 듣지 않는 큐에 쌓인다(0-D). `veo_worker` 가 `veo` 에
# 의존하므로 공용 표는 아래쪽에 둔다.
from veo.jobs.queues import (
    DEAD_LETTER_QUEUE,
    JOB_TYPE_QUEUES,
    QUEUE_NAMES,
    queue_for_job_type,
)

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

#: Task name -> queue, populated by :func:`register_task_queue` as tasks are declared.
TASK_QUEUE_OVERRIDES: dict[str, str] = {}


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


def _shared_broker_url() -> str | None:
    """API 가 쓰는 것과 같은 브로커 주소. 읽을 수 없으면 ``None``.

    설정을 읽다 터지는 것만으로 워커가 못 뜨게 만들지는 않는다 — 그때는 예전처럼
    ``VEO_BROKER_URL`` 만 보고 판단하고, eager 모드라는 사실은 아래에서 크게 알린다.
    """
    try:
        from veo.core.settings import get_settings

        return get_settings().resolved_broker_url() or None
    except Exception:  # pragma: no cover - 설정이 깨진 환경에서만
        logger.warning("Could not read shared settings for the broker URL.", exc_info=True)
        return None


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
        """환경에서 읽는다. 브로커 주소는 **API 와 같은 규칙**으로 정한다.

        예전에는 여기만 ``VEO_BROKER_URL`` 을 읽었다. API 는 ``VEO_CELERY_BROKER_URL``
        이나 ``VEO_REDIS_URL`` 을 읽는다. 그래서 후자만 채운 배포에서는 **API 는 큐로
        보내는데 워커는 eager 모드**가 됐다 — 워커가 떠 있는데 아무것도 안 듣는다.
        운영 로그에는 "워커 정상" 으로 보이고, 잡은 `QUEUED` 인 채 남는다.

        ``VEO_BROKER_URL`` 은 계속 받는다. 이미 그 이름으로 설정한 곳(부하 시험·
        런북)을 깨지 않기 위해서고, 명시한 값이 있으면 그쪽이 우선이다.
        """
        return cls(
            broker_url=_env_str("VEO_BROKER_URL") or _shared_broker_url(),
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
        # --- 작업 등록 -------------------------------------------------------
        # **이 줄이 없으면 워커는 아무 일도 할 줄 모른다.**
        #
        # 배포는 `celery --app veo_worker.runtime.app:celery_app` 로 뜬다. 그 명령은
        # 이 모듈만 불러온다 — 태스크는 `veo_worker.runtime.tasks` 에서 데코레이터로
        # 등록되는데, 아무도 그 모듈을 부르지 않으니 등록이 일어나지 않았다.
        #
        # 증상이 고약했다(운영 실측 2026-08-06 23:31). 워커는 `ready.` 를 찍고,
        # 큐 여섯 개를 듣는다고 배너에 적고, `Online` 으로 보였다. 큐 목록은 이 설정
        # 에서 오니까 태스크가 하나도 없어도 그대로 나온다. 그러다 메시지가 오면
        # `Received unregistered task of type 'veo.jobs.seo_scan'` 로 버렸다.
        include=["veo_worker.runtime.tasks"],
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
