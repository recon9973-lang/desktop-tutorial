from __future__ import annotations

import logging

import pytest
from celery import Celery
from veo.contracts import JobType

from veo_worker.runtime.app import (
    DEAD_LETTER_QUEUE,
    JOB_TYPE_QUEUES,
    QUEUE_NAMES,
    WorkerSettings,
    create_celery_app,
    queue_for_job_type,
    route_task,
)


class TestQueueTopology:
    def test_the_five_named_queues_exist(self) -> None:
        assert QUEUE_NAMES == ("crawl", "seo", "geo", "keyword", "report")

    def test_every_job_type_is_routed(self) -> None:
        assert set(JOB_TYPE_QUEUES) == set(JobType)
        for job_type, queue in JOB_TYPE_QUEUES.items():
            assert queue in QUEUE_NAMES, f"{job_type} routed to unknown queue {queue}"

    def test_queue_lookup_is_exhaustive(self) -> None:
        for job_type in JobType:
            assert queue_for_job_type(job_type) in QUEUE_NAMES

    def test_declared_queues_include_the_dead_letter_queue(self) -> None:
        app = create_celery_app(WorkerSettings())
        declared = {q.name for q in app.conf.task_queues}
        assert declared == {*QUEUE_NAMES, DEAD_LETTER_QUEUE}

    def test_unknown_task_names_route_to_the_dead_letter_queue(self) -> None:
        assert route_task("some.unregistered.task") == {"queue": DEAD_LETTER_QUEUE}

    def test_known_task_names_route_to_their_family_queue(self) -> None:
        import veo_worker.runtime.tasks as tasks  # noqa: F401  (registers task names)

        assert route_task("veo.jobs.site_crawl") == {"queue": "crawl"}
        assert route_task("veo.jobs.seo_scan") == {"queue": "seo"}
        assert route_task("veo.jobs.geo_readiness_scan") == {"queue": "geo"}
        assert route_task("veo.jobs.keyword_lookup") == {"queue": "keyword"}
        assert route_task("veo.jobs.report_export") == {"queue": "report"}


class TestSafetyConfiguration:
    @pytest.fixture
    def app(self) -> Celery:
        return create_celery_app(WorkerSettings(broker_url="redis://localhost:6379/0"))

    def test_at_least_once_delivery_settings(self, app: Celery) -> None:
        assert app.conf.task_acks_late is True
        assert app.conf.task_reject_on_worker_lost is True
        assert app.conf.worker_prefetch_multiplier == 1

    def test_serialisation_is_json_only_and_never_pickle(self, app: Celery) -> None:
        assert app.conf.task_serializer == "json"
        assert app.conf.result_serializer == "json"
        assert list(app.conf.accept_content) == ["json"]
        assert list(app.conf.result_accept_content) == ["json"]
        assert "pickle" not in str(app.conf.accept_content).lower()

    def test_time_limits_are_set_and_soft_precedes_hard(self, app: Celery) -> None:
        assert app.conf.task_soft_time_limit > 0
        assert app.conf.task_time_limit > app.conf.task_soft_time_limit

    def test_results_expire_and_workers_recycle(self, app: Celery) -> None:
        assert app.conf.result_expires is not None
        assert app.conf.worker_max_tasks_per_child > 0

    def test_broker_url_is_read_from_settings(self, app: Celery) -> None:
        assert app.conf.broker_url == "redis://localhost:6379/0"
        assert app.conf.task_always_eager is False


class TestEagerFallback:
    def test_without_a_broker_url_the_app_falls_back_to_eager(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="veo_worker.runtime.app"):
            app = create_celery_app(WorkerSettings())

        assert app.conf.task_always_eager is True
        assert app.conf.task_eager_propagates is True
        assert app.conf.broker_url.startswith("memory://")
        assert any(
            "eager" in record.getMessage().lower() for record in caplog.records
        ), "the eager fallback must announce itself, not fail silently"

    def test_settings_read_the_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VEO_BROKER_URL", "redis://example:6379/2")
        monkeypatch.setenv("VEO_RESULT_BACKEND_URL", "redis://example:6379/3")
        monkeypatch.setenv("VEO_WORKER_TASK_TIME_LIMIT", "900")
        monkeypatch.setenv("VEO_WORKER_TASK_SOFT_TIME_LIMIT", "600")

        settings = WorkerSettings.from_env()
        assert settings.broker_url == "redis://example:6379/2"
        assert settings.result_backend_url == "redis://example:6379/3"
        assert settings.task_time_limit == 900
        assert settings.task_soft_time_limit == 600
        assert settings.is_eager is False

    def test_soft_limit_above_hard_limit_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="soft"):
            WorkerSettings(task_time_limit=100, task_soft_time_limit=200)

    def test_blank_broker_url_counts_as_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VEO_BROKER_URL", "   ")
        assert WorkerSettings.from_env().is_eager is True


@pytest.mark.requires_redis
def test_live_broker_round_trip(live_redis_url: str) -> None:
    """Only meaningful against a real broker; skipped when VEO_TEST_REDIS_URL is unset."""
    app = create_celery_app(WorkerSettings(broker_url=live_redis_url))
    connection = app.connection()
    connection.ensure_connection(max_retries=1)
    connection.release()
