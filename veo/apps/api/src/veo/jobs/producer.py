"""큐로 **보내는** 쪽. 받는 쪽은 `veo_worker` 다.

## 이 파일이 왜 생겼나

`dispatch` 는 `celery.current_app.send_task(...)` 를 썼다. 그런데 API 프로세스는
`veo_worker.runtime.app` 을 한 번도 import 하지 않는다 — 그래서 `current_app` 은
**우리 앱이 아니라 Celery 의 기본 앱**이었다(실측 2026-08-06: `main='default'`,
`broker_url=None`).

결과가 둘이다.

1. 설정에 넣은 브로커 주소가 **아무 데도 쓰이지 않는다.** 기본 앱은 브로커를
   `amqp://guest@localhost` 로 가정하고 접속을 시도한다.
2. 어쩌다 접속이 되더라도 메시지는 기본 큐(`celery`)로 간다. 우리 워커는
   `crawl · seo · geo · keyword · report · dead_letter` 만 듣는다. 아무도 안 듣는
   큐에 쌓이고, 잡은 `QUEUED` 인 채 남는다.

`dispatch` 의 시험은 `celery.current_app` 을 통째로 가짜로 바꿔치기해서 통과하고
있었다. 초록이 도는 것을 뜻하지 않는 전형이다(0-F).

## 못 보내면 빨리 실패해야 한다

이 호출은 **HTTP 요청 안에서** 일어난다. 브로커가 죽어 있을 때 kombu 의 기본 재시도
정책은 백오프를 두고 몇 번이나 다시 붙는다. 그동안 사용자의 요청은 그냥 멈춰 있다.

그래서 여기서는 재시도를 끄고 접속 시간제한을 짧게 준다. 못 보내면 `dispatch` 가
배경 스레드로 떨어뜨린다 — 예전 방식으로라도 도는 편이 낫기 때문이다.
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Any, Final

from celery import Celery
from kombu import Queue

from veo.contracts.enums import JobType
from veo.core.settings import get_settings
from veo.jobs.queues import (
    DEAD_LETTER_QUEUE,
    QUEUE_NAMES,
    queue_for_job_type,
    task_name_for,
)

__all__ = ["BROKER_CONNECT_TIMEOUT_SECONDS", "producer_app", "publish"]

#: 브로커에 붙는 데 이만큼 넘게 걸리면 포기한다. 요청 하나를 붙잡는 시간이므로 짧다.
BROKER_CONNECT_TIMEOUT_SECONDS: Final = 3.0


@lru_cache(maxsize=1)
def producer_app() -> Celery:
    """보내기 전용 Celery 앱. 큐 지형도는 워커와 **같은 표**에서 읽는다.

    한 번만 만든다. 매 요청마다 앱을 만들면 접속을 매번 새로 연다.
    """
    settings = get_settings()
    app = Celery("veo_producer")

    queues = [Queue(name, routing_key=name) for name in QUEUE_NAMES]
    queues.append(Queue(DEAD_LETTER_QUEUE, routing_key=DEAD_LETTER_QUEUE))

    app.conf.update(
        broker_url=settings.resolved_broker_url() or None,
        # 결과는 `jobs` 표에 적는다. Celery 의 결과 저장소는 쓰지 않는다 — 같은 사실을
        # 두 곳에 적으면 어긋나는 날이 온다(0-D).
        result_backend=settings.celery_result_backend or None,
        task_serializer="json",
        accept_content=["json"],
        task_queues=queues,
        # 없는 큐를 만들어 주지 않는다. 오타 난 큐가 조용히 생기면 메시지는 거기 쌓이고
        # 아무도 듣지 않는다 — 워커 쪽과 같은 설정이다.
        task_create_missing_queues=False,
        task_default_queue=DEAD_LETTER_QUEUE,
        task_default_routing_key=DEAD_LETTER_QUEUE,
        broker_transport_options={
            "socket_connect_timeout": BROKER_CONNECT_TIMEOUT_SECONDS,
            "socket_timeout": BROKER_CONNECT_TIMEOUT_SECONDS,
        },
        broker_connection_retry_on_startup=False,
    )
    return app


def publish(job_id: uuid.UUID, *, job_type: JobType, parameters: dict[str, Any]) -> str:
    """메시지를 그 종류의 큐로 보낸다. 돌아오는 값은 어느 큐로 갔는지다.

    실패하면 예외를 그대로 올린다. **여기서 삼키면 안 된다** — 부르는 쪽이 배경 스레드로
    떨어뜨릴지 판단해야 하는데, 성공한 것처럼 돌려주면 그 일은 아무 데서도 안 돈다.
    """
    queue = queue_for_job_type(job_type)
    producer_app().send_task(
        task_name_for(job_type),
        kwargs={"job_id": str(job_id), **parameters},
        queue=queue,
        routing_key=queue,
        # 요청 안에서 부른다. 못 붙으면 기다리지 말고 바로 실패해야 한다.
        retry=False,
    )
    return queue
