"""이슈를 닫는 재측정 — **이 파일이 없어서 이슈가 하나도 안 닫혔다.**

## 무엇이 비어 있었나

이슈의 상태 기계는 처음부터 규칙이 분명했다(`veo/issues/lifecycle.py`):

> "An issue is closed by a **re-measurement**, not by someone clicking 'done'."

그리고 그 규칙을 지키는 조각도 다 있었다 —

* `build_verification_request(issue)` : 무엇을 다시 재야 하는지(검사 하나, 그 이슈의 URL)
* `record_verification_outcome(...)`  : 저장된 판정에서 결론을 **도출**한다
* `derive_outcome(...)`               : WARNING 은 통과가 아니고, 일부만 통과면 미결

**정작 그 재측정을 실행하는 것이 없었다.** `request_verification` 은 상태를
`VERIFYING` 으로 옮기고 요청서를 만들어 돌려줄 뿐 작업을 걸지 않았고, 워커의
`reverification` 태스크는 *"Phase 2 에 온다"* 라고 적힌 빈 껍데기였다.

**[실측] 2026-08-09 운영 DB — 이슈 165건이 전부 `OPEN`.** 다른 상태가 하나도 없다.
같은 프로젝트를 16번 재측정한 곳도 그렇다. `verification_runs` 는 0행이다.

## 이 작업이 하는 일

진단 파이프라인을 **그대로** 쓴다. 새 채점 경로를 만들지 않는다 — 두 벌이 되는 순간
한쪽만 고쳐지는 날이 온다(`seo/jobs.py` 와 같은 이유).

```
이슈의 URL 만 수집한다(discover=False)  ->  저장  ->  저장된 판정에서 결론 도출
```

**범위를 좁히는 것이 핵심이다.** "canonical 하나 고쳤나" 를 묻자고 사이트 200장을 다시
기어가면 거래처 서버를 몇 시간 두드리고 크롤 예산을 태운다. 그래서 이 작업은
`VerificationRequest` 가 적어 준 URL 만 본다.

**결론은 우리가 정하지 않는다.** 스캔이 끝나면 `record_verification_outcome` 에
저장된 실행 번호만 넘긴다. 그 함수가 `check_results` 를 읽어 판정하고, 그 판정만이
`VERIFIED_RESOLVED` 로 가는 문을 연다. 이 파일 어디에도 "해결됨" 이라고 쓸 수 있는
인자가 없다.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from veo.authz import Principal
from veo.contracts.enums import Role
from veo.jobs import service as jobs_service
from veo.jobs.execution import JobFailure, JobOutcome, JobWork
from veo.seo.crawl import CrawlRefusal
from veo.seo.schemas import SiteScanRequest

__all__ = ["REVERIFY_STAGES", "reverification_work"]

_log = logging.getLogger(__name__)

#: 화면 진행 표시가 읽는 단계. 표적 재측정은 한 장~몇 장이라 수집이 짧다.
REVERIFY_STAGES: tuple[str, ...] = ("재측정", "판정")


def reverification_work(
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    roles: frozenset[Role],
    session_id: str,
    is_service_account: bool = False,
    issue_id: uuid.UUID,
    site_id: uuid.UUID,
    target_url: str,
    urls: tuple[str, ...],
    locale: str = "ko-KR",
) -> JobWork:
    """이 이슈의 URL 만 다시 재고, 그 결과로 이슈를 판정하는 작업을 만든다.

    요청의 :class:`Principal` 을 그대로 넘기지 않고 **값으로 풀어서 다시 만든다** —
    요청 객체의 수명이 요청보다 길어지면 안 된다(진단 작업과 같은 규칙).
    """

    def work(session: Session, job_id: uuid.UUID) -> JobOutcome:
        # 순환 고리 밖에서 당긴다. 작업이 도는 시점에는 앱이 이미 조립돼 있다.
        from veo.issues import service as issues_service
        from veo.seo.router import run_console_scan

        principal = Principal(
            user_id=user_id,
            organization_id=organization_id,
            roles=roles,
            session_id=session_id,
            is_service_account=is_service_account,
        )
        jobs_service.advance(session, job_id, progress=0.1, stage=REVERIFY_STAGES[0])

        try:
            _report, saved_run_id = run_console_scan(
                session,
                principal=principal,
                payload=SiteScanRequest(
                    target_url=target_url,
                    site_id=site_id,
                    # **좁힌다.** 스스로 찾아 돌지 않고, 이 이슈가 가리키는 주소만 본다.
                    urls=list(urls),
                    discover=False,
                    max_urls=len(urls) or None,
                    locale=locale,
                ),
                request_id=str(job_id),
                job_id=job_id,
            )
        except CrawlRefusal as refusal:
            raise JobFailure(
                "CRAWL_REFUSED", refusal.error.message, retryable=refusal.error.retryable
            ) from refusal
        except HTTPException as exc:
            if exc.status_code == 404:
                raise JobFailure(
                    "SITE_NOT_FOUND",
                    "사이트를 찾을 수 없습니다. 재검사를 요청한 뒤 지워졌을 수 있습니다.",
                ) from exc
            raise

        if saved_run_id is None:
            # 저장이 없으면 판정할 근거가 없다. 이슈는 `VERIFYING` 인 채로 남는다 —
            # 근거 없이 상태를 옮기는 것보다 낫다.
            raise JobFailure(
                "RUN_NOT_SAVED",
                "재측정 결과가 저장되지 않아 판정할 수 없습니다. 다시 요청해 주십시오.",
                retryable=True,
            )

        jobs_service.advance(session, job_id, progress=0.9, stage=REVERIFY_STAGES[1])

        # **결론은 여기서 정하지 않는다.** 저장된 실행 번호만 넘기면, 그쪽이
        # `check_results` 를 읽어 판정한다. 이 파일에는 "해결됨" 을 쓸 인자가 없다.
        issue, run = issues_service.record_verification_outcome(
            session,
            principal,
            issue_id,
            scan_run_id=saved_run_id,
            request_id=str(job_id),
        )
        _log.info(
            "issue.reverified issue=%s outcome=%s state=%s",
            issue_id,
            run.outcome,
            issue.state,
        )

        return JobOutcome(result_run_id=saved_run_id)

    return work
