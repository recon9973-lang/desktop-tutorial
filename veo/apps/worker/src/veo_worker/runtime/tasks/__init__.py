"""Registered task stubs — one per :class:`~veo.contracts.JobType`.

Phase 0 delivers the *runtime*, not the analysis. Each task here drives the real state
machine, the real progress tracker and the real cancellation checkpoints, and then
raises :class:`NotImplementedError` naming the phase that delivers the collector.

That refusal is the point. A stub that returned a plausible-looking score would be
indistinguishable from a real result to every caller downstream — the API, the console,
a customer's report — and would be believed. An honest ``NotImplementedError`` is
strictly more useful than fabricated data.
"""

from __future__ import annotations

import logging
from typing import Any

from veo.contracts import JobType, Surface

# 태스크 이름은 **보내는 쪽과 같은 표**에서 읽는다. 이름이 갈리면 메시지가 아무도 듣지
# 않는 큐로 간다 — 그때 잡은 `QUEUED` 인 채 남고 화면은 계속 "대기 중" 이라고 말한다.
from veo.jobs.queues import TASK_NAME_BY_JOB_TYPE

from veo_worker.runtime.app import celery_app, queue_for_job_type, register_task_queue
from veo_worker.runtime.cancellation import JobCancelledError
from veo_worker.runtime.errors import redact
from veo_worker.runtime.execution import JobRuntime
from veo_worker.runtime.progress import StageDefinition

__all__ = [
    "DEAD_LETTER_TASK_NAME",
    "TASK_NAME_BY_JOB_TYPE",
    "competitor_comparison",
    "geo_observation_run",
    "geo_readiness_scan",
    "keyword_lookup",
    "record_dead_letter",
    "report_export",
    "reverification",
    "seo_scan",
    "site_crawl",
]

logger = logging.getLogger(__name__)

STAGE_PREPARE = "prepare"
STAGE_COLLECT = "collect"
STAGE_ANALYSE = "analyse"
STAGE_FINALISE = "finalise"

#: The skeleton every job walks. Phases 2+ subdivide ``collect`` and ``analyse`` per type.
DEFAULT_STAGES: list[StageDefinition] = [
    StageDefinition(key=STAGE_PREPARE, label_ko="준비", weight=1.0),
    StageDefinition(key=STAGE_COLLECT, label_ko="수집", weight=3.0),
    StageDefinition(key=STAGE_ANALYSE, label_ko="분석", weight=1.0),
    StageDefinition(key=STAGE_FINALISE, label_ko="마무리", weight=1.0),
]

#: Which phase delivers each collector. Only the SEO entry is fixed by the Phase 0 brief;
#: the rest are this package's provisional reading of the roadmap and should be corrected
#: by the integration maintainer if the plan differs. See INTEGRATION_REQUEST.md.
PHASE_NOTES: dict[JobType, str] = {
    JobType.SEO_SCAN: "SEO collector lands in Phase 2",
    JobType.SITE_CRAWL: "Site crawler lands in Phase 2",
    JobType.REVERIFICATION: "Re-verification collector lands in Phase 2",
    JobType.GEO_READINESS_SCAN: "GEO readiness collector lands in Phase 3",
    JobType.GEO_OBSERVATION_RUN: "GEO observation runner lands in Phase 3",
    JobType.KEYWORD_LOOKUP: "Naver keyword collector lands in Phase 4",
    JobType.COMPETITOR_COMPARISON: "Competitor comparison collector lands in Phase 4",
    JobType.REPORT_EXPORT: "Report exporter lands in Phase 5",
}

DEAD_LETTER_TASK_NAME = "veo.dead_letter.record"

_UNROUTED = set(JobType) - set(TASK_NAME_BY_JOB_TYPE)
if _UNROUTED:  # pragma: no cover - guards a developer mistake at import time
    raise RuntimeError(f"JobTypes without a task: {sorted(t.value for t in _UNROUTED)}")

for _job_type, _task_name in TASK_NAME_BY_JOB_TYPE.items():
    register_task_queue(_task_name, queue_for_job_type(_job_type))
register_task_queue(DEAD_LETTER_TASK_NAME, "dead_letter")


def _run_phase_zero_skeleton(
    expected_type: JobType,
    *,
    job_id: str,
    surface: str,
    input_hash: str,
    job_type: str | None = None,
    parameters: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    organization_id: str | None = None,
    project_id: str | None = None,
    requested_by: str | None = None,
) -> dict[str, Any]:
    """Drive the runtime end to end, then refuse to invent an analysis result."""
    if job_type is not None and JobType(job_type) is not expected_type:
        # A message on the wrong queue would silently produce the wrong analysis later.
        raise ValueError(
            f"Message declares job_type {job_type!r} but was delivered to the "
            f"{expected_type.value} task."
        )
    runtime = JobRuntime.create(
        job_id=job_id,
        job_type=expected_type,
        surface=Surface(surface),
        input_hash=input_hash,
        stages=list(DEFAULT_STAGES),
        idempotency_key=idempotency_key,
        organization_id=organization_id,
        project_id=project_id,
        requested_by=requested_by,
    )
    try:
        runtime.begin()

        runtime.begin_stage(STAGE_PREPARE)
        runtime.checkpoint(STAGE_PREPARE)
        runtime.advance_stage(STAGE_PREPARE, items_done=1, items_total=1)
        runtime.complete_stage(STAGE_PREPARE)

        runtime.begin_stage(STAGE_COLLECT)
        runtime.checkpoint(STAGE_COLLECT)

        # Phase 0 stops here on purpose. There is no collector yet, and returning a
        # fabricated score would be worse than returning nothing.
        raise NotImplementedError(PHASE_NOTES[expected_type])

    except JobCancelledError as exc:
        logger.info("Job %s cancelled at stage %s.", job_id, exc.stage_key)
        payload: dict[str, Any] = runtime.cancelled(exc).model_dump(mode="json")
        return payload
    except Exception as exc:
        descriptor = runtime.fail(exc)
        logger.warning(
            "Job %s finished as %s (ref %s).",
            job_id,
            descriptor.status.value,
            descriptor.internal_error_ref,
        )
        raise
    finally:
        runtime.release()


# --------------------------------------------------------------------------------------
def _run_scan(execute: Any, scan_work: Any, **kwargs: Any) -> dict[str, Any]:
    """큐로 건너온 값을 파이프라인이 받는 모양으로 되돌리고 돌린다.

    **함수는 프로세스를 건너지 못한다.** 그래서 API 는 값만 보내고, 여기서 그 값으로
    작업을 다시 만든다 — `scan_work` 가 처음부터 값만 받도록 만들어져 있어서 가능하다
    (요청 객체의 수명이 요청보다 길어지면 안 된다는 규칙의 부수 효과다).

    모르는 값이 오면 여기서 멈춘다. 빠진 자리를 기본값으로 채우면 **엉뚱한 조직의 일을
    엉뚱한 권한으로** 돌리게 된다.
    """
    import uuid as _uuid

    from veo.contracts.enums import Role

    job_id = _uuid.UUID(str(kwargs["job_id"]))
    work = scan_work(
        organization_id=_uuid.UUID(str(kwargs["organization_id"])),
        user_id=_uuid.UUID(str(kwargs["user_id"])),
        roles=frozenset(Role(one) for one in kwargs["roles"]),
        session_id=str(kwargs["session_id"]),
        target_url=str(kwargs["target_url"]),
        site_id=_uuid.UUID(str(kwargs["site_id"])),
        urls=tuple(kwargs.get("urls") or ()),
        discover=bool(kwargs["discover"]),
        max_urls=kwargs.get("max_urls"),
        locale=str(kwargs.get("locale") or "ko-KR"),
        is_service_account=bool(kwargs.get("is_service_account", False)),
    )
    outcome = execute(job_id, work)
    return {"job_id": str(job_id), "status": getattr(outcome, "status", None)}


# Registered tasks. Thin on purpose: each one names its job type and delegates.
# --------------------------------------------------------------------------------------


@celery_app.task(name=TASK_NAME_BY_JOB_TYPE[JobType.SITE_CRAWL], bind=False)
def site_crawl(**kwargs: Any) -> dict[str, Any]:
    return _run_phase_zero_skeleton(JobType.SITE_CRAWL, **kwargs)


@celery_app.task(name=TASK_NAME_BY_JOB_TYPE[JobType.SEO_SCAN], bind=False)
def seo_scan(**kwargs: Any) -> dict[str, Any]:
    """진단을 실제로 돈다 — **API 가 쓰는 그 파이프라인 그대로**.

    Phase 0 에서 여기는 `NotImplementedError` 였다. 수집기가 없어서였는데, 그 사이
    API 쪽에 파이프라인이 생겼고 지금은 API 프로세스의 배경 스레드가 그것을 돌린다.
    데몬 스레드라 재배포하면 진행 중인 작업이 사라진다(기획서 E5).

    그래서 여기서 **같은 함수를 부른다.** 파이프라인을 워커용으로 다시 쓰지 않는다 —
    두 벌이 되면 한쪽만 고쳐지는 날이 오고, 그날 두 경로가 다른 점수를 낸다(0-D).

    임포트를 함수 안에서 하는 이유는 API 쪽과 같다: 모듈 상단에서 당기면 `veo.api` 를
    거쳐 돌아오는 임포트 고리를 밟는다.
    """
    from veo.jobs.execution import execute
    from veo.seo.jobs import scan_work

    return _run_scan(execute, scan_work, **kwargs)


@celery_app.task(name=TASK_NAME_BY_JOB_TYPE[JobType.REVERIFICATION], bind=False)
def reverification(**kwargs: Any) -> dict[str, Any]:
    return _run_phase_zero_skeleton(JobType.REVERIFICATION, **kwargs)


@celery_app.task(name=TASK_NAME_BY_JOB_TYPE[JobType.COMPETITOR_COMPARISON], bind=False)
def competitor_comparison(**kwargs: Any) -> dict[str, Any]:
    return _run_phase_zero_skeleton(JobType.COMPETITOR_COMPARISON, **kwargs)


@celery_app.task(name=TASK_NAME_BY_JOB_TYPE[JobType.GEO_READINESS_SCAN], bind=False)
def geo_readiness_scan(**kwargs: Any) -> dict[str, Any]:
    return _run_phase_zero_skeleton(JobType.GEO_READINESS_SCAN, **kwargs)


@celery_app.task(name=TASK_NAME_BY_JOB_TYPE[JobType.GEO_OBSERVATION_RUN], bind=False)
def geo_observation_run(**kwargs: Any) -> dict[str, Any]:
    return _run_phase_zero_skeleton(JobType.GEO_OBSERVATION_RUN, **kwargs)


@celery_app.task(name=TASK_NAME_BY_JOB_TYPE[JobType.KEYWORD_LOOKUP], bind=False)
def keyword_lookup(**kwargs: Any) -> dict[str, Any]:
    return _run_phase_zero_skeleton(JobType.KEYWORD_LOOKUP, **kwargs)


@celery_app.task(name=TASK_NAME_BY_JOB_TYPE[JobType.REPORT_EXPORT], bind=False)
def report_export(**kwargs: Any) -> dict[str, Any]:
    return _run_phase_zero_skeleton(JobType.REPORT_EXPORT, **kwargs)


@celery_app.task(name=DEAD_LETTER_TASK_NAME, bind=False)
def record_dead_letter(
    *,
    job_id: str | None = None,
    task_name: str | None = None,
    reason: str = "",
) -> dict[str, Any]:
    """Terminal sink for messages nothing else will handle.

    The reason is redacted before it is logged or returned: a dead-lettered message is
    often a failed provider call, and those carry credentials in their error text.
    """
    safe_reason = redact(reason)
    logger.error(
        "Dead-lettered message: job_id=%s task=%s reason=%s", job_id, task_name, safe_reason
    )
    return {"job_id": job_id, "task_name": task_name, "reason": safe_reason}
