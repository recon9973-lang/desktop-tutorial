"""작업을 **어디서** 돌릴지 한 곳에서 정한다.

지금 진단은 API 프로세스의 배경 스레드에서 돈다(:func:`veo.jobs.execution.run_detached`).
데몬 스레드라 재배포하면 진행 중인 작업이 사라진다 — 죽은 작업이 "실행 중" 으로 남지는
않지만(`STALE_AFTER`), 사라지는 것은 사실이다(기획서 E5).

워커를 띄우면 그 일이 워커에서 돈다. 그런데 **바꾸는 순간 되돌릴 수 없으면 안 된다.**
브로커가 없거나 워커가 아직 안 떴는데 큐에만 넣으면, 작업은 아무도 집어가지 않은 채
영원히 대기한다 — 지금보다 나쁘다.

그래서 여기서 고른다: **브로커가 설정돼 있으면 큐로, 없으면 예전처럼 배경 스레드로.**
설정하지 않은 배포는 오늘과 똑같이 동작한다.

**보내지 못하면 배경 스레드로 떨어진다.** 리미터에서는 반대로 했다(닿지 못하면 거절) —
거기서는 통과시키는 것이 남의 서버를 때리는 문이 되기 때문이다. 여기서는 못 보낸 대가가
"작업이 아무 데서도 안 돈다" 이고, 그것보다는 예전 방식으로라도 도는 편이 낫다. 다만
조용히 떨어지지 않는다 — 로그가 남는다.
"""

from __future__ import annotations

import logging
import uuid
from typing import Final

from veo.contracts.enums import JobType
from veo.core.settings import get_settings
from veo.jobs.execution import JobWork, run_detached

__all__ = ["dispatch", "queue_is_configured"]

_log = logging.getLogger(__name__)

#: 작업 종류별 큐의 태스크 이름. 워커가 같은 이름으로 등록한다 — 이름이 갈리면 메시지가
#: 아무도 듣지 않는 큐에 쌓인다.
TASK_NAMES: Final[dict[JobType, str]] = {
    JobType.SEO_SCAN: "veo.jobs.seo_scan",
}


def queue_is_configured() -> bool:
    """브로커 주소가 있는가. 없으면 큐가 없는 배포다."""
    settings = get_settings()
    broker = (settings.celery_broker_url or settings.redis_url or "").strip()
    return broker != ""


def dispatch(
    job_id: uuid.UUID,
    work: JobWork,
    *,
    job_type: JobType,
    parameters: dict[str, object],
) -> str:
    """이 작업을 돌릴 곳으로 보낸다. 돌아오는 값은 어디로 갔는지의 기록이다.

    ``work`` 는 배경 스레드로 떨어질 때 쓴다. 큐로 갈 때는 ``parameters`` 만 건너간다 —
    함수는 프로세스를 건너지 못하고, 값만 건널 수 있다.
    """
    task_name = TASK_NAMES.get(job_type)

    if task_name is not None and queue_is_configured():
        try:
            from celery import current_app

            current_app.send_task(task_name, kwargs={"job_id": str(job_id), **parameters})
        except Exception:
            # 못 보낸 대가는 "작업이 아무 데서도 안 돈다" 이다. 예전 방식으로라도 도는
            # 편이 낫다 — 다만 조용히 떨어지지는 않는다.
            _log.warning(
                "could not enqueue job %s; running in-process instead", job_id, exc_info=True
            )
        else:
            return "queue"

    run_detached(job_id, work)
    return "in-process"
