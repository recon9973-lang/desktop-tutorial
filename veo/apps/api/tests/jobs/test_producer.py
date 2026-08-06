"""보내는 쪽이 **우리 브로커의 우리 큐**로 보내는가.

2026-08-06 실측. API 프로세스 안에서 `celery.current_app` 을 찍어 보니::

    current_app broker : None
    current_app name   : 'default'

`veo_worker.runtime.app` 을 API 가 한 번도 import 하지 않으니 당연한 결과다. 즉
`dispatch` 가 쓰던 앱은 **우리 앱이 아니라 Celery 의 기본 앱**이었고, 설정에 넣은
브로커 주소는 아무 데도 쓰이지 않았다. 어쩌다 접속이 되더라도 메시지는 기본 큐
(`celery`)로 가는데 워커는 그 큐를 듣지 않는다 — 잡은 `QUEUED` 인 채 남고 화면은
계속 "대기 중" 이라고 말한다.

그런데 `test_dispatch.py` 는 초록이었다. `celery.current_app` 을 통째로 가짜로
바꿔치기하고 "보냈는가" 만 봤기 때문이다(0-F). 그래서 여기서는 **바꿔치기하지 않고**
진짜 앱의 설정을 본다.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from veo.contracts.enums import JobType
from veo.core.settings import get_settings
from veo.jobs import dispatch as dispatch_module
from veo.jobs import producer as module
from veo.jobs.queues import (
    DEAD_LETTER_QUEUE,
    JOB_TYPE_QUEUES,
    QUEUE_NAMES,
    TASK_NAME_BY_JOB_TYPE,
)

BROKER = "redis://broker.invalid:6379/0"


@pytest.fixture(autouse=True)
def _fresh_app() -> Any:
    """앱은 한 번만 만들어 캐시한다 — 시험끼리 그 캐시를 물려받으면 안 된다."""
    module.producer_app.cache_clear()
    yield
    module.producer_app.cache_clear()


@pytest.fixture
def with_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "celery_broker_url", BROKER, raising=False)
    get_settings.cache_clear()  # type: ignore[attr-defined]
    monkeypatch.setattr(module, "get_settings", lambda: settings)


class TestItIsOurAppNotCelerysDefault:
    def test_the_broker_comes_from_our_settings(self, with_broker: None) -> None:
        assert module.producer_app().conf.broker_url == BROKER

    def test_it_is_not_the_default_app(self, with_broker: None) -> None:
        """이것이 깨진 자리였다. 기본 앱은 우리 설정을 하나도 모른다."""
        import celery

        app = module.producer_app()

        assert app is not celery.current_app
        assert app.main != "default"

    def test_it_refuses_to_invent_a_queue(self, with_broker: None) -> None:
        """오타 난 큐가 조용히 생기면 메시지는 거기 쌓이고 아무도 듣지 않는다."""
        assert module.producer_app().conf.task_create_missing_queues is False

    def test_it_declares_every_queue_the_worker_listens_on(self, with_broker: None) -> None:
        declared = {queue.name for queue in module.producer_app().conf.task_queues}

        assert declared == {*QUEUE_NAMES, DEAD_LETTER_QUEUE}

    def test_it_gives_up_quickly(self, with_broker: None) -> None:
        """요청 안에서 부른다. 브로커가 죽어 있을 때 사용자를 붙잡아 두면 안 된다."""
        options = module.producer_app().conf.broker_transport_options

        assert options["socket_connect_timeout"] == module.BROKER_CONNECT_TIMEOUT_SECONDS
        assert module.producer_app().conf.broker_connection_retry_on_startup is False


class TestItGoesToTheQueueTheWorkerListensOn:
    def test_seo_scan_goes_to_the_seo_queue(
        self, with_broker: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sent: list[dict[str, Any]] = []
        monkeypatch.setattr(
            module.producer_app(),
            "send_task",
            lambda name, **kwargs: sent.append({"name": name, **kwargs}),
        )
        job_id = uuid.uuid4()

        queue = module.publish(
            job_id, job_type=JobType.SEO_SCAN, parameters={"target_url": "https://a/"}
        )

        assert queue == "seo"
        assert sent[0]["name"] == "veo.jobs.seo_scan"
        assert sent[0]["queue"] == "seo"
        assert sent[0]["routing_key"] == "seo"
        assert sent[0]["retry"] is False
        assert sent[0]["kwargs"] == {"job_id": str(job_id), "target_url": "https://a/"}

    def test_it_never_uses_celerys_default_queue(
        self, with_broker: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """기본 큐(`celery`)로 가면 워커가 듣지 않는다 — 그것이 원래 결함이었다."""
        sent: list[str] = []
        monkeypatch.setattr(
            module.producer_app(),
            "send_task",
            lambda _name, **kwargs: sent.append(kwargs["queue"]),
        )

        for job_type in dispatch_module.QUEUEABLE:
            module.publish(job_id=uuid.uuid4(), job_type=job_type, parameters={})

        assert sent
        assert "celery" not in sent

    def test_a_failed_send_is_not_swallowed(
        self, with_broker: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """여기서 삼키면 부르는 쪽이 배경 스레드로 떨어뜨릴 판단을 못 한다."""

        def _boom(*_args: Any, **_kwargs: Any) -> None:
            raise ConnectionError("broker down")

        monkeypatch.setattr(module.producer_app(), "send_task", _boom)

        with pytest.raises(ConnectionError):
            module.publish(uuid.uuid4(), job_type=JobType.SEO_SCAN, parameters={})


class TestTheTableIsComplete:
    def test_every_job_type_has_a_queue(self) -> None:
        assert set(JOB_TYPE_QUEUES) == set(JobType)

    def test_every_job_type_has_a_task_name(self) -> None:
        assert set(TASK_NAME_BY_JOB_TYPE) == set(JobType)

    def test_every_queue_is_declared(self) -> None:
        assert set(JOB_TYPE_QUEUES.values()) <= set(QUEUE_NAMES)

    def test_what_we_send_is_a_subset_of_what_is_named(self) -> None:
        """이름이 있다는 것과 받는 사람이 있다는 것은 다르다(0-E)."""
        assert set(TASK_NAME_BY_JOB_TYPE) >= dispatch_module.QUEUEABLE


class TestSenderAndReceiverReadTheSameAddress:
    """API 는 ``VEO_CELERY_BROKER_URL``, 워커는 ``VEO_BROKER_URL`` 을 읽고 있었다.
    후자만 비운 배포에서는 API 가 큐로 보내는데 워커는 eager 모드로 돌았다."""

    def test_the_broker_falls_back_to_redis_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = get_settings()
        monkeypatch.setattr(settings, "celery_broker_url", "", raising=False)
        monkeypatch.setattr(settings, "redis_url", BROKER, raising=False)

        assert settings.resolved_broker_url() == BROKER

    def test_no_broker_means_no_queue(self, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = get_settings()
        monkeypatch.setattr(settings, "celery_broker_url", "", raising=False)
        monkeypatch.setattr(settings, "redis_url", "", raising=False)

        assert settings.resolved_broker_url() == ""
        assert dispatch_module.queue_is_configured() is False
