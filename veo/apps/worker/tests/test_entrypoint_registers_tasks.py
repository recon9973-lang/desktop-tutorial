"""배포가 띄우는 그 명령으로 띄웠을 때, 워커가 일할 줄 아는가.

## 왜 이 파일이 따로 있나

다른 시험들은 `from veo_worker.runtime.tasks import ...` 로 시작한다. 그 순간 태스크
데코레이터가 돌아서 등록이 끝난다. 그래서 **시험은 전부 초록인데 운영은 죽었다**
(실측 2026-08-06 23:31)::

    ERROR/MainProcess] Received unregistered task of type 'veo.jobs.seo_scan'.
    KeyError: 'veo.jobs.seo_scan'

배포 명령은 ``celery --app veo_worker.runtime.app:celery_app worker`` 다. 이 명령은
`app` 모듈만 불러온다. `tasks` 를 부르는 사람이 없으면 등록은 일어나지 않는다.

증상이 조용했다는 점이 더 나쁘다. 워커는 `ready.` 를 찍고, 큐 여섯 개를 듣는다고
배너에 적고, 화면에는 `Online` 으로 보였다 — 큐 목록은 설정에서 오니까 태스크가
하나도 없어도 그대로 나온다. 잡은 `QUEUED` 인 채 8분 넘게 남았다.

## 그래서 여기서는 **미리 불러오지 않는다**

별도 프로세스를 띄워서 `veo_worker.runtime.app` 만 import 하고, Celery 가 워커를
시작할 때 하는 일(`import_default_modules`)을 그대로 시킨 뒤 등록 여부를 본다.
이 파일에서 `veo_worker.runtime.tasks` 를 import 하면 시험의 의미가 사라진다.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
from veo.contracts import JobType
from veo.jobs.queues import TASK_NAME_BY_JOB_TYPE

#: 배포 명령이 하는 일을 그대로 흉내낸다 — `app` 만 부르고, 워커 시작 절차를 밟는다.
_AS_THE_WORKER_STARTS = """
import json, sys
from veo_worker.runtime.app import celery_app

assert "veo_worker.runtime.tasks" not in sys.modules, (
    "app 모듈이 tasks 를 직접 당기고 있습니다. 그러면 이 시험이 아무것도 지키지 못합니다."
)

# Celery 워커가 뜰 때 하는 일. `include` 에 적힌 모듈을 여기서 불러온다.
celery_app.loader.import_default_modules()

print(json.dumps(sorted(celery_app.tasks)))
"""


@pytest.fixture(scope="module")
def registered_task_names() -> frozenset[str]:
    finished = subprocess.run(  # noqa: S603 - 우리가 만든 문자열을 우리 인터프리터로 돈다
        [sys.executable, "-c", _AS_THE_WORKER_STARTS],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if finished.returncode != 0:
        pytest.fail(f"워커 시작 절차가 실패했습니다:\n{finished.stderr}")
    import json

    return frozenset(json.loads(finished.stdout))


class TestTheDeployedCommandCanActuallyWork:
    def test_the_seo_scan_task_is_registered(self, registered_task_names: frozenset) -> None:
        """이것이 깨졌던 자리다. 이 하나만 다시 깨져도 진단이 영원히 대기한다."""
        assert TASK_NAME_BY_JOB_TYPE[JobType.SEO_SCAN] in registered_task_names

    def test_every_named_task_is_registered(self, registered_task_names: frozenset) -> None:
        missing = {
            name for name in TASK_NAME_BY_JOB_TYPE.values() if name not in registered_task_names
        }

        assert not missing, f"이름표만 있고 등록되지 않은 태스크: {sorted(missing)}"

    def test_the_dead_letter_sink_is_registered(self, registered_task_names: frozenset) -> None:
        """아무도 못 받는 메시지를 받아 줄 곳까지 있어야 조용히 사라지지 않는다."""
        assert "veo.dead_letter.record" in registered_task_names
