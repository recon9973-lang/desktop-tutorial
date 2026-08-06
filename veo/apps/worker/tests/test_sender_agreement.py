"""보내는 쪽(API)과 받는 쪽(워커)이 **같은 것을 보고 있는가**.

이 둘이 갈리면 증상이 조용하다. 메시지는 잘 나가고, 워커는 잘 떠 있고, 로그에는
오류가 없다. 그런데 잡은 `QUEUED` 인 채 남는다 — 화면은 계속 "대기 중" 이라고 한다.
2026-08-06 실측 기준으로 갈려 있던 자리가 둘이었다:

* **주소**: API 는 ``VEO_CELERY_BROKER_URL`` / ``VEO_REDIS_URL`` 을, 워커는
  ``VEO_BROKER_URL`` 을 읽었다. 앞의 것만 채운 배포에서 워커는 eager 모드였다 —
  브로커에 붙지 않고, 아무 큐도 듣지 않으면서, 정상으로 보인다.
* **이름표**: 태스크 이름과 큐 지형도가 양쪽에 따로 적혀 있었다.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from veo.contracts import JobType
from veo.core.settings import get_settings
from veo.jobs.queues import JOB_TYPE_QUEUES as SHARED_QUEUES
from veo.jobs.queues import QUEUE_NAMES as SHARED_QUEUE_NAMES
from veo.jobs.queues import TASK_NAME_BY_JOB_TYPE as SHARED_TASK_NAMES

from veo_worker.runtime.app import JOB_TYPE_QUEUES, QUEUE_NAMES, WorkerSettings
from veo_worker.runtime.tasks import TASK_NAME_BY_JOB_TYPE

BROKER = "redis://broker.invalid:6379/0"


class TestTheyReadTheSameTable:
    def test_the_queue_names_are_one_object(self) -> None:
        """같은 값이 아니라 **같은 물건**이어야 한다 — 베껴 쓰면 한쪽만 고쳐진다(0-D)."""
        assert QUEUE_NAMES is SHARED_QUEUE_NAMES
        assert JOB_TYPE_QUEUES is SHARED_QUEUES
        assert TASK_NAME_BY_JOB_TYPE is SHARED_TASK_NAMES

    def test_every_registered_task_matches_the_shared_name(self) -> None:
        """워커가 실제로 등록한 이름이 표와 같은가. 여기가 갈리면 메시지를 아무도 안 듣는다."""
        from veo_worker.runtime import tasks as module

        registered = set(module.celery_app.tasks)

        for job_type in JobType:
            assert SHARED_TASK_NAMES[job_type] in registered, job_type


@pytest.fixture
def api_broker(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], None]:
    """API 쪽 설정이 이 주소라고 해 두는 장치.

    환경변수가 아니라 **설정 객체**를 통해 심는다. 개발자 컴퓨터의 `.env` 에 Redis 가
    적혀 있어도 결과가 달라지지 않아야 한다(worker conftest 와 같은 이유).
    """

    def _set(url: str) -> None:
        settings = get_settings()
        monkeypatch.setattr(settings, "celery_broker_url", url, raising=False)
        monkeypatch.setattr(settings, "redis_url", "", raising=False)
        monkeypatch.setattr("veo.core.settings.get_settings", lambda: settings)

    return _set


class TestTheyResolveTheSameBroker:
    def test_the_worker_accepts_the_address_the_api_reads(
        self, api_broker: Callable[[str], None]
    ) -> None:
        """이것이 깨진 자리였다. ``VEO_BROKER_URL`` 만 보던 시절엔 여기서 eager 였다."""
        api_broker(BROKER)

        settings = WorkerSettings.from_env()

        assert settings.broker_url == BROKER
        assert settings.is_eager is False

    def test_its_own_variable_still_wins(
        self, api_broker: Callable[[str], None], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """부하 시험과 런북이 ``VEO_BROKER_URL`` 을 쓴다. 명시한 값이 우선이다."""
        api_broker(BROKER)
        monkeypatch.setenv("VEO_BROKER_URL", "redis://explicit.invalid:6379/0")

        assert WorkerSettings.from_env().broker_url == "redis://explicit.invalid:6379/0"

    def test_nothing_configured_stays_eager(self, api_broker: Callable[[str], None]) -> None:
        """설정하지 않은 배포는 오늘과 똑같이 동작한다 — 그리고 그 사실을 크게 말한다."""
        api_broker("")

        settings = WorkerSettings.from_env()

        assert settings.broker_url is None
        assert settings.is_eager is True
