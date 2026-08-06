"""작업을 **어디서** 돌릴지 한 곳에서 정한다.

지금 진단은 API 프로세스의 배경 스레드에서 돈다(:func:`veo.jobs.execution.run_detached`).
데몬 스레드라 재배포하면 진행 중인 작업이 사라진다 — 죽은 작업이 "실행 중" 으로 남지는
않지만(`STALE_AFTER`), 사라지는 것은 사실이다(기획서 E5).

워커를 띄우면 그 일이 워커에서 돈다. 그런데 **바꾸는 순간 되돌릴 수 없으면 안 된다.**
브로커가 없거나 워커가 아직 안 떴는데 큐에만 넣으면, 작업은 아무도 집어가지 않은 채
영원히 대기한다 — 지금보다 나쁘다.

그래서 여기서 고른다: **브로커가 설정돼 있으면 큐로, 없으면 예전처럼 배경 스레드로.**
설정하지 않은 배포는 오늘과 똑같이 동작한다.

보내는 일 자체는 :mod:`veo.jobs.producer` 가 한다 — 예전에는 여기서 `current_app` 을
바로 썼는데, 그것이 우리 앱이 아니라 Celery 의 기본 앱이라 큐 경로가 애초에 동작할 수
없었다. 그 이야기는 그 모듈에 적었다.

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

__all__ = ["QUEUEABLE", "dispatch", "queue_is_configured"]

_log = logging.getLogger(__name__)

#: 큐로 **보내도 되는** 작업 종류.
#:
#: 이름은 여덟 종류가 다 있지만(:mod:`veo.jobs.queues`), 워커에서 실제로 일을 하는 것은
#: SEO 진단 하나다. 나머지는 Phase 0 의 뼈대라 `NotImplementedError` 를 던진다. 이름이
#: 있다는 것과 받는 사람이 있다는 것은 다른 이야기다(0-E) — 그래서 목록을 따로 둔다.
QUEUEABLE: Final[frozenset[JobType]] = frozenset({JobType.SEO_SCAN})


def queue_is_configured() -> bool:
    """브로커 주소가 있는가. 없으면 큐가 없는 배포다.

    **워커도 같은 함수로 같은 답을 얻는다**(:meth:`Settings.resolved_broker_url`).
    보내는 쪽과 받는 쪽이 다른 환경변수를 읽으면, 한쪽만 채운 배포에서 잡이 아무도
    집어가지 않은 채 `QUEUED` 로 남는다.
    """
    return get_settings().resolved_broker_url() != ""


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
    if job_type in QUEUEABLE and queue_is_configured():
        try:
            # 모듈 상단에서 당기면 celery·kombu 를 큐 없는 배포에서도 매번 읽는다.
            from veo.jobs.producer import publish

            queue = publish(job_id, job_type=job_type, parameters=parameters)
        except Exception:
            # 못 보낸 대가는 "작업이 아무 데서도 안 돈다" 이다. 예전 방식으로라도 도는
            # 편이 낫다 — 다만 조용히 떨어지지는 않는다.
            _log.warning(
                "could not enqueue job %s; running in-process instead", job_id, exc_info=True
            )
        else:
            _log.info("job %s queued on %s", job_id, queue)
            return "queue"

    run_detached(job_id, work)
    return "in-process"
