"""콘솔 진단을 요청 밖에서 돌린다 (P1-6 — 기획서 E4).

지금까지 콘솔 진단은 HTTP 요청 하나가 크롤(최대 200장)·성능 실측·채점·저장을 전부
붙들고 있었다 — 240초 타임아웃에 기대는 구조라, 느린 사이트는 완주 직전에 끊기고
재배포는 돌던 진단을 소리 없이 죽였다. 여기서는 그 파이프라인을 **작업**으로 옮긴다:
요청은 작업 표를 받고 즉시 돌아가고, 화면은 진행을 물어보고, 끝나면 저장된 실행을
연다. 재배포로 죽은 작업은 STALE 로 **드러난다** — "실행 중" 인 척하지 않는다.

파이프라인 자체는 :func:`veo.seo.router.run_console_scan` 하나다. 동기 엔드포인트와
이 작업이 같은 함수를 쓴다 — 두 벌로 갈라지는 순간 한쪽만 고쳐지는 날이 온다.

실행 방식은 :mod:`veo.jobs.execution` 의 배경 스레드다(Celery 아님 — 그 문서 참조).
"""

from __future__ import annotations

import uuid
from typing import Final

from fastapi import HTTPException
from sqlalchemy.orm import Session

from veo.authz import Principal
from veo.contracts.enums import Role
from veo.jobs import service as jobs_service
from veo.jobs.execution import JobFailure, JobOutcome, JobWork
from veo.seo.crawl import CrawlRefusal
from veo.seo.schemas import SiteScanRequest

__all__ = ["SCAN_STAGES", "scan_work"]

#: 화면 진행 표시가 읽는 단계 이름. 수집·채점이 시간의 대부분을 쓴다.
SCAN_STAGES: Final = ("수집·채점", "저장")


def scan_work(
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    roles: frozenset[Role],
    session_id: str,
    target_url: str,
    site_id: uuid.UUID,
    urls: tuple[str, ...],
    discover: bool,
    max_urls: int | None,
    locale: str,
    is_service_account: bool = False,
) -> JobWork:
    """배경에서 돌 진단 작업을 만든다.

    요청의 :class:`Principal` 객체를 그대로 넘기지 않고 **값으로 풀어서 다시 만든다** —
    요청 객체의 수명이 요청보다 길어지면 안 된다(관측 작업과 같은 규칙).
    ``is_service_account`` 도 값의 일부다: 이것이 빠지면 예약 실행(정기 재진단)의
    자리표시 user_id 가 실행자 칸에 기록되려다 FK 에서 터진다.
    """

    def work(session: Session, job_id: uuid.UUID) -> JobOutcome:
        # 순환 고리 밖에서 완성된 앱을 쓴다 — 라우터 모듈은 veo.api 를 거쳐 자기
        # 자신으로 돌아오는 고리 위에 있어, 모듈 상단에서 당기면 임포트 순서에 따라
        # 깨진다. 작업이 도는 시점에는 앱이 이미 조립돼 있다.
        from veo.seo.router import run_console_scan

        principal = Principal(
            user_id=user_id,
            organization_id=organization_id,
            roles=roles,
            session_id=session_id,
            is_service_account=is_service_account,
        )
        jobs_service.advance(session, job_id, progress=0.1, stage=SCAN_STAGES[0])

        try:
            _report, saved_run_id = run_console_scan(
                session,
                principal=principal,
                payload=SiteScanRequest(
                    target_url=target_url,
                    site_id=site_id,
                    urls=list(urls),
                    discover=discover,
                    max_urls=max_urls,
                    locale=locale,
                ),
                request_id=str(job_id),
            )
        except CrawlRefusal as refusal:
            # 수집 거절의 문장은 원래 사용자에게 그대로 가는 값이다(동기 경로와 동일).
            raise JobFailure(
                "CRAWL_REFUSED", refusal.error.message, retryable=refusal.error.retryable
            ) from refusal
        except HTTPException as exc:
            if exc.status_code == 404:
                raise JobFailure(
                    "SITE_NOT_FOUND",
                    "사이트를 찾을 수 없습니다. 작업을 시작한 뒤 지워졌을 수 있습니다.",
                ) from exc
            raise

        jobs_service.advance(session, job_id, progress=0.95, stage=SCAN_STAGES[1])
        return JobOutcome(result_run_id=saved_run_id)

    return work
