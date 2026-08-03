"""콘솔 진단의 작업 이행 (P1-6) — 요청이 크롤을 붙들지 않는다.

지키는 성질:

1. 작업 본문은 동기 경로와 **같은 파이프라인**을 돌리고, 저장된 실행 id 를 결과로
   남긴다 — 화면은 그 id 로 저장된 결과를 연다.
2. 수집 거절은 예외가 아니라 **작업 실패**가 되고, 사용자에게 보여도 되는 문장
   (동기 경로가 쓰던 그 문장)이 실린다.
3. `site_id` 없는 작업 등록은 거절된다 — 저장할 자리가 없으면 결과가 사라진다.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic")

from tests.seo.test_geo_companion import _crawl_outcome
from tests.seo.test_regression_alert import project, site  # noqa: F401  (지역 픽스처 재사용)


def _submit(db_session, principal, site_row):  # type: ignore[no-untyped-def]
    from veo.contracts.enums import JobType
    from veo.jobs import service as jobs_service
    from veo.seo.jobs import SCAN_STAGES

    job, created = jobs_service.submit(
        db_session,
        principal,
        job_type=JobType.SEO_SCAN,
        project_id=site_row.project_id,
        stages=list(SCAN_STAGES),
        parameters={"target_url": site_row.origin, "site_id": str(site_row.id)},
    )
    assert created
    db_session.flush()
    return job


class TestTheWork:
    def test_the_work_runs_the_shared_pipeline_and_names_the_saved_run(
        self, db_session, principal, site, monkeypatch  # noqa: F811
    ):
        import veo.seo.router as router_module
        from veo.db.models.analysis import ScanRun
        from veo.seo.jobs import scan_work

        outcome = _crawl_outcome()

        class StubCrawler:
            def crawl(self, target_url, *, extra_urls=(), max_urls=None):  # type: ignore[no-untyped-def]
                return outcome

            def collect(self, targets):  # type: ignore[no-untyped-def]
                return outcome.documents, outcome.robots_txt

        monkeypatch.setattr(router_module, "ConsoleCrawler", StubCrawler)

        job = _submit(db_session, principal, site)
        work = scan_work(
            organization_id=principal.organization_id,
            user_id=principal.user_id,
            roles=principal.roles,
            session_id=principal.session_id,
            target_url=site.origin,
            site_id=site.id,
            urls=(),
            discover=False,
            max_urls=None,
            locale="ko-KR",
        )

        result = work(db_session, job.id)

        assert result.result_run_id is not None, "저장된 실행 없이 끝난 작업은 열 결과가 없다"
        run = db_session.get(ScanRun, result.result_run_id)
        assert run is not None and run.report_snapshot is not None

    def test_a_crawl_refusal_becomes_a_job_failure_with_the_same_sentence(
        self, db_session, principal, site, monkeypatch  # noqa: F811
    ):
        import veo.seo.router as router_module
        from veo.contracts.enums import ErrorCode
        from veo.contracts.envelope import ApiError
        from veo.jobs.execution import JobFailure
        from veo.seo.crawl import CrawlRefusal
        from veo.seo.jobs import scan_work

        refusal_ko = "대상 사이트가 수집을 거부했습니다."

        class RefusingCrawler:
            def collect(self, targets):  # type: ignore[no-untyped-def]
                raise CrawlRefusal(
                    422, ApiError.of(ErrorCode.VALIDATION_FAILED, refusal_ko)
                )

        monkeypatch.setattr(router_module, "ConsoleCrawler", RefusingCrawler)

        job = _submit(db_session, principal, site)
        work = scan_work(
            organization_id=principal.organization_id,
            user_id=principal.user_id,
            roles=principal.roles,
            session_id=principal.session_id,
            target_url=site.origin,
            site_id=site.id,
            urls=(),
            discover=False,
            max_urls=None,
            locale="ko-KR",
        )

        with pytest.raises(JobFailure) as failure:
            work(db_session, job.id)

        assert failure.value.message_ko == refusal_ko, "동기 경로가 쓰던 문장이 사라지면 안 된다"


class TestTheSubmitGate:
    def test_a_job_without_a_site_is_refused_before_it_exists(
        self, db_session, principal
    ):
        import uuid as uuid_module

        from fastapi import HTTPException

        from veo.seo.router import submit_scan_job
        from veo.seo.schemas import SiteScanRequest

        with pytest.raises(HTTPException) as refused:
            submit_scan_job(
                SiteScanRequest(target_url="https://clinic.example", site_id=None),
                principal,
                str(uuid_module.uuid4()),
                db_session,
            )

        assert refused.value.status_code == 422
