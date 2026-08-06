"""큐 지형도 — **보내는 쪽과 받는 쪽이 같은 표를 본다.**

여기 있는 것은 세 가지다: 큐 이름, 작업 종류별 큐, 작업 종류별 태스크 이름.

## 왜 API 쪽에 있나

이 표는 원래 `veo_worker.runtime.app` 에만 있었다. 그런데 메시지를 **보내는 쪽은 API**
다. 보내는 쪽이 표를 못 보면 이름을 손으로 옮겨 적게 되고, 한쪽만 고쳐지는 날이 온다.
그날 메시지는 아무도 듣지 않는 큐에 쌓이고, 잡은 `QUEUED` 인 채 영원히 남는다 — 화면은
"대기 중" 이라고 계속 말한다(0-D).

`veo_worker` 는 `veo` 에 의존하고 그 반대는 아니다. 그래서 공용 표는 **아래쪽**,
즉 여기에 둔다. 워커는 여기서 읽어 간다.

## 태스크 이름을 안다고 보내도 되는 것은 아니다

이 표에는 여덟 종류가 다 있지만, 워커에서 **실제로 일을 하는 것은 SEO 진단 하나**다.
나머지는 Phase 0 의 뼈대라 `NotImplementedError` 를 던진다. 그래서 "보내도 되는가" 는
:data:`veo.jobs.dispatch.QUEUEABLE` 이 따로 정한다 — 이름이 있다는 것과 받는 사람이
있다는 것은 다른 이야기다(0-E).
"""

from __future__ import annotations

from typing import Final

from veo.contracts.enums import JobType

__all__ = [
    "DEAD_LETTER_QUEUE",
    "JOB_TYPE_QUEUES",
    "QUEUE_NAMES",
    "TASK_NAME_BY_JOB_TYPE",
    "queue_for_job_type",
    "task_name_for",
]

#: 작업 종류 갈래마다 큐를 하나씩 둔다. 느린 사이트 크롤이 키워드 조회를 굶기지 않게,
#: 그리고 갈래별로 따로 늘릴 수 있게.
QUEUE_NAMES: Final[tuple[str, ...]] = ("crawl", "seo", "geo", "keyword", "report")

#: 아무도 가져가지 않는 메시지가 가는 곳. 조용히 버리지 않는다.
DEAD_LETTER_QUEUE: Final = "dead_letter"

#: 작업 종류 → 큐. 빠짐없이 적는다 — 새 종류가 기본 큐로 슬쩍 흘러들지 않도록
#: 시험이 전수를 확인한다.
JOB_TYPE_QUEUES: Final[dict[JobType, str]] = {
    JobType.SITE_CRAWL: "crawl",
    JobType.SEO_SCAN: "seo",
    JobType.REVERIFICATION: "seo",
    JobType.COMPETITOR_COMPARISON: "seo",
    JobType.GEO_READINESS_SCAN: "geo",
    JobType.GEO_OBSERVATION_RUN: "geo",
    JobType.KEYWORD_LOOKUP: "keyword",
    JobType.REPORT_EXPORT: "report",
}

#: 작업 종류 → 태스크 이름. 워커가 **같은 이름으로** 등록한다.
TASK_NAME_BY_JOB_TYPE: Final[dict[JobType, str]] = {
    JobType.SITE_CRAWL: "veo.jobs.site_crawl",
    JobType.SEO_SCAN: "veo.jobs.seo_scan",
    JobType.REVERIFICATION: "veo.jobs.reverification",
    JobType.COMPETITOR_COMPARISON: "veo.jobs.competitor_comparison",
    JobType.GEO_READINESS_SCAN: "veo.jobs.geo_readiness_scan",
    JobType.GEO_OBSERVATION_RUN: "veo.jobs.geo_observation_run",
    JobType.KEYWORD_LOOKUP: "veo.jobs.keyword_lookup",
    JobType.REPORT_EXPORT: "veo.jobs.report_export",
}


def queue_for_job_type(job_type: JobType) -> str:
    try:
        return JOB_TYPE_QUEUES[job_type]
    except KeyError:  # pragma: no cover - 전수 시험이 먼저 잡는다
        raise KeyError(
            f"{job_type} 에 큐가 없습니다. 기본 큐로 흘려보내지 말고 JOB_TYPE_QUEUES 에 "
            "추가하십시오."
        ) from None


def task_name_for(job_type: JobType) -> str:
    try:
        return TASK_NAME_BY_JOB_TYPE[job_type]
    except KeyError:  # pragma: no cover - 전수 시험이 먼저 잡는다
        raise KeyError(
            f"{job_type} 에 태스크 이름이 없습니다. TASK_NAME_BY_JOB_TYPE 에 추가하십시오."
        ) from None
