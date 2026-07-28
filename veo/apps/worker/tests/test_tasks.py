from __future__ import annotations

import pytest
from veo.contracts import ErrorCode, JobDescriptor, JobStatus, JobType, Surface

from veo_worker.runtime import tasks
from veo_worker.runtime.app import celery_app
from veo_worker.runtime.cancellation import CANCELLATION_REGISTRY
from veo_worker.runtime.execution import JOB_STORE
from veo_worker.runtime.idempotency import compute_input_hash


@pytest.fixture(autouse=True)
def _clean_runtime_state() -> None:
    JOB_STORE.clear()
    CANCELLATION_REGISTRY.clear()


def submit(job_id: str, job_type: JobType, **parameters: object) -> dict[str, object]:
    return {
        "job_id": job_id,
        "job_type": job_type.value,
        "surface": Surface.CONSOLE.value,
        "input_hash": compute_input_hash(parameters),
        "parameters": parameters,
    }


class TestRegistration:
    def test_the_app_runs_eagerly_in_tests(self) -> None:
        assert celery_app.conf.task_always_eager is True

    def test_every_job_type_has_a_registered_task(self) -> None:
        for job_type in JobType:
            name = tasks.TASK_NAME_BY_JOB_TYPE[job_type]
            assert name in celery_app.tasks, f"{job_type} has no registered task"
        assert set(tasks.TASK_NAME_BY_JOB_TYPE) == set(JobType)

    def test_task_names_are_namespaced(self) -> None:
        assert all(n.startswith("veo.jobs.") for n in tasks.TASK_NAME_BY_JOB_TYPE.values())

    def test_a_dead_letter_sink_task_exists(self) -> None:
        assert tasks.DEAD_LETTER_TASK_NAME in celery_app.tasks


class TestPhaseZeroStubs:
    @pytest.mark.parametrize("job_type", list(JobType))
    def test_analysis_is_an_honest_not_implemented(self, job_type: JobType) -> None:
        payload = submit(f"job-{job_type.value}", job_type, url="https://example.kr")
        task = celery_app.tasks[tasks.TASK_NAME_BY_JOB_TYPE[job_type]]

        with pytest.raises(NotImplementedError) as excinfo:
            task.apply(kwargs=payload, throw=True)

        message = str(excinfo.value)
        assert "Phase" in message, "the stub must say which phase delivers the real work"
        assert message.strip(), "an empty NotImplementedError tells nobody anything"

    def test_seo_scan_names_phase_two(self) -> None:
        payload = submit("job-seo", JobType.SEO_SCAN, url="https://example.kr")
        task = celery_app.tasks[tasks.TASK_NAME_BY_JOB_TYPE[JobType.SEO_SCAN]]
        with pytest.raises(NotImplementedError, match="SEO collector lands in Phase 2"):
            task.apply(kwargs=payload, throw=True)

    def test_no_fabricated_result_is_written(self) -> None:
        payload = submit("job-seo", JobType.SEO_SCAN, url="https://example.kr")
        task = celery_app.tasks[tasks.TASK_NAME_BY_JOB_TYPE[JobType.SEO_SCAN]]
        with pytest.raises(NotImplementedError):
            task.apply(kwargs=payload, throw=True)

        descriptor = JOB_STORE.get("job-seo")
        assert descriptor is not None
        assert descriptor.result_run_id is None
        assert descriptor.partial_result_available is False


class TestPlumbingRunsEndToEnd:
    def _run_seo(self, job_id: str = "job-1") -> JobDescriptor:
        payload = submit(job_id, JobType.SEO_SCAN, url="https://example.kr")
        task = celery_app.tasks[tasks.TASK_NAME_BY_JOB_TYPE[JobType.SEO_SCAN]]
        with pytest.raises(NotImplementedError):
            task.apply(kwargs=payload, throw=True)
        descriptor = JOB_STORE.get(job_id)
        assert descriptor is not None
        return descriptor

    def test_state_machine_reached_a_terminal_state(self) -> None:
        descriptor = self._run_seo()
        assert descriptor.status is JobStatus.FAILED_FINAL
        assert descriptor.is_terminal() is True

    def test_a_missing_implementation_is_not_retried(self) -> None:
        descriptor = self._run_seo()
        assert descriptor.error_code is ErrorCode.INTERNAL_ERROR
        assert descriptor.attempts == 1
        assert descriptor.next_retry_at is None

    def test_the_failure_carries_a_safe_message_and_a_ref(self) -> None:
        descriptor = self._run_seo()
        assert descriptor.safe_error_message
        assert descriptor.internal_error_ref
        assert "Traceback" not in descriptor.safe_error_message

    def test_progress_and_stages_are_observable_by_the_api(self) -> None:
        descriptor = self._run_seo()
        assert descriptor.stages, "the API must be able to render stages"
        assert descriptor.current_stage is not None
        assert 0.0 <= descriptor.progress <= 1.0
        assert descriptor.stages[0].status is JobStatus.SUCCEEDED
        assert descriptor.input_hash

    def test_a_terminal_job_leaves_no_stage_claiming_to_be_running(self) -> None:
        descriptor = self._run_seo()
        assert descriptor.is_terminal()
        running = [s.key for s in descriptor.stages if s.status is JobStatus.RUNNING]
        assert not running, f"job is terminal but stages {running} still report RUNNING"
        collect = next(s for s in descriptor.stages if s.key == "collect")
        assert collect.status is JobStatus.FAILED_FINAL
        assert collect.finished_at is not None

    def test_descriptor_round_trips_through_json(self) -> None:
        descriptor = self._run_seo()
        restored = JobDescriptor.model_validate_json(descriptor.model_dump_json())
        assert restored.job_id == descriptor.job_id
        assert restored.status is descriptor.status


class TestCooperativeCancellation:
    def test_a_cancel_requested_before_the_run_lands_as_cancelled(self) -> None:
        CANCELLATION_REGISTRY.request_cancel_ahead_of_time("job-c", reason="user stopped it")
        payload = submit("job-c", JobType.SEO_SCAN, url="https://example.kr")
        task = celery_app.tasks[tasks.TASK_NAME_BY_JOB_TYPE[JobType.SEO_SCAN]]

        result = task.apply(kwargs=payload, throw=True)

        assert result.successful()
        descriptor = JOB_STORE.get("job-c")
        assert descriptor is not None
        assert descriptor.status is JobStatus.CANCELLED
        assert descriptor.error_code is ErrorCode.JOB_CANCELLED
        assert descriptor.finished_at is not None

    def test_cancellation_preempts_the_not_implemented_stub(self) -> None:
        CANCELLATION_REGISTRY.request_cancel_ahead_of_time("job-c2")
        payload = submit("job-c2", JobType.GEO_OBSERVATION_RUN, brand="베놈")
        task = celery_app.tasks[tasks.TASK_NAME_BY_JOB_TYPE[JobType.GEO_OBSERVATION_RUN]]
        task.apply(kwargs=payload, throw=True)
        descriptor = JOB_STORE.get("job-c2")
        assert descriptor is not None
        assert descriptor.status is JobStatus.CANCELLED

    def test_the_token_is_released_after_the_run(self) -> None:
        CANCELLATION_REGISTRY.request_cancel_ahead_of_time("job-c3")
        payload = submit("job-c3", JobType.SEO_SCAN, url="https://example.kr")
        task = celery_app.tasks[tasks.TASK_NAME_BY_JOB_TYPE[JobType.SEO_SCAN]]
        task.apply(kwargs=payload, throw=True)
        assert CANCELLATION_REGISTRY.get("job-c3") is None


class TestDeadLetterSink:
    def test_dead_letter_records_a_redacted_payload(self) -> None:
        sink = celery_app.tasks[tasks.DEAD_LETTER_TASK_NAME]
        result = sink.apply(
            kwargs={
                "job_id": "job-dl",
                "task_name": "veo.jobs.seo_scan",
                "reason": "Authorization: Bearer sk-live-SECRET",
            },
            throw=True,
        )
        assert result.successful()
        assert "sk-live-SECRET" not in str(result.result)
