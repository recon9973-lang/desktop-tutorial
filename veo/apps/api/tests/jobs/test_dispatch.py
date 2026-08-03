"""작업을 어디서 돌릴지 — 그리고 **바꿔도 오늘이 깨지지 않는가**.

진단은 지금 API 프로세스의 배경 스레드에서 돈다. 데몬 스레드라 재배포하면 진행 중인
작업이 사라진다(기획서 E5). 워커를 띄우면 그 일이 워커에서 돈다.

**바꾸는 순간 되돌릴 수 없으면 안 된다.** 브로커가 없거나 워커가 아직 안 떴는데 큐에만
넣으면 작업은 아무도 집어가지 않은 채 영원히 대기한다 — 지금보다 나쁘다. 그래서 여기서
지키는 것은 하나다: **설정하지 않은 배포는 오늘과 똑같이 동작한다.**
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from veo.contracts.enums import JobType
from veo.jobs import dispatch as module


def _work(_session: Any, _job_id: uuid.UUID) -> Any:  # pragma: no cover - 부르지 않는다
    raise AssertionError("이 시험은 작업을 실제로 돌리지 않는다")


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> list[uuid.UUID]:
    """배경 스레드로 떨어졌는지만 본다 — 진짜 스레드를 띄우지 않는다."""
    started: list[uuid.UUID] = []
    monkeypatch.setattr(module, "run_detached", lambda job_id, work: started.append(job_id))
    return started


def _no_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "queue_is_configured", lambda: False)


def _with_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "queue_is_configured", lambda: True)


class TestWithoutAQueueNothingChanges:
    def test_it_runs_in_process(self, monkeypatch: pytest.MonkeyPatch, spy: list) -> None:
        _no_queue(monkeypatch)
        job_id = uuid.uuid4()

        where = module.dispatch(job_id, _work, job_type=JobType.SEO_SCAN, parameters={})

        assert where == "in-process"
        assert spy == [job_id]

    def test_an_unknown_job_type_also_runs_in_process(
        self, monkeypatch: pytest.MonkeyPatch, spy: list
    ) -> None:
        """큐에 태스크가 없는 종류는 보내면 안 된다 — 아무도 집어가지 않는다."""
        _with_queue(monkeypatch)

        where = module.dispatch(
            uuid.uuid4(), _work, job_type=JobType.REPORT_EXPORT, parameters={}
        )

        assert where == "in-process"
        assert len(spy) == 1


class TestWithAQueueItGoesToTheWorker:
    def test_it_sends_the_task(self, monkeypatch: pytest.MonkeyPatch, spy: list) -> None:
        _with_queue(monkeypatch)
        sent: list[dict[str, Any]] = []

        class _App:
            def send_task(self, name: str, **kwargs: Any) -> None:
                sent.append({"name": name, **kwargs})

        monkeypatch.setattr("celery.current_app", _App(), raising=False)
        job_id = uuid.uuid4()

        where = module.dispatch(
            job_id, _work, job_type=JobType.SEO_SCAN, parameters={"target_url": "https://a/"}
        )

        assert where == "queue"
        # 배경 스레드로는 가지 않았다 — 두 곳에서 같은 작업이 돌면 두 번 크롤한다.
        assert spy == []
        assert sent[0]["name"] == "veo.jobs.seo_scan"
        assert sent[0]["kwargs"]["job_id"] == str(job_id)
        assert sent[0]["kwargs"]["target_url"] == "https://a/"


class TestWhenSendingFailsItStillRuns:
    """못 보낸 대가는 "작업이 아무 데서도 안 돈다" 이다. 예전 방식으로라도 도는 편이 낫다 —
    리미터에서 반대로 판단한 것과 다른 이유다. 거기서 통과시키면 남의 서버를 때리는 문이
    열리지만, 여기서 떨어지는 것은 우리 일이 우리 프로세스에서 도는 것뿐이다."""

    def test_a_broken_broker_falls_back(
        self, monkeypatch: pytest.MonkeyPatch, spy: list
    ) -> None:
        _with_queue(monkeypatch)

        class _Broken:
            def send_task(self, *_args: Any, **_kwargs: Any) -> None:
                raise ConnectionError("broker down")

        monkeypatch.setattr("celery.current_app", _Broken(), raising=False)
        job_id = uuid.uuid4()

        where = module.dispatch(job_id, _work, job_type=JobType.SEO_SCAN, parameters={})

        assert where == "in-process"
        assert spy == [job_id]
