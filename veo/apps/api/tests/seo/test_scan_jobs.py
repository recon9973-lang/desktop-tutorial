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

    def test_the_finished_job_records_which_specification_scored_it(
        self, db_session, principal, site, monkeypatch  # noqa: F811
    ):
        """명세가 바뀌면 점수가 바뀐다. 어느 판으로 매겼는지 없으면 지난 결과를 설명할 수 없다.

        2026-08-06 실측: 운영 `jobs` 17건이 전부 `scoring_spec_id` ·
        `scoring_spec_version` 이 NULL 이었다. 표에 칸은 처음부터 있었고 채우는
        코드가 없었다(0-E).
        """
        import veo.seo.router as router_module
        from veo.jobs import service as jobs_service
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
        # 잡을 실제로 닫아 본다 — 닫는 자리가 기록하는 자리이므로, 여기까지 와야
        # "기록된다" 를 확인한 것이 된다(0-E).
        jobs_service.succeed(
            db_session,
            job.id,
            result_run_id=result.result_run_id,
            partial=result.is_partial,
            scoring_spec_id=result.scoring_spec_id,
            scoring_spec_version=result.scoring_spec_version,
        )
        db_session.flush()

        assert job.scoring_spec_id, "어느 명세로 채점했는지 잡에 남지 않았다"
        assert job.scoring_spec_version, "명세 판이 잡에 남지 않았다"

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


class TestTheJobAndItsResultStayConnected:
    """작업과 그 작업이 만든 진단 실행이 서로를 가리켜야 한다.

    2026-08-06 실측: `scan_runs.job_id` 운영 41행이 **전부 NULL** 이었다. 칸은
    처음부터 있었고 넘기는 코드가 없었다(0-E). 그 상태에서는 작업이 실패했을 때
    "어디까지 갔는가" 를 되짚을 방법이 없다.
    """

    def test_a_background_scan_records_the_job_that_made_it(
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
        run = db_session.get(ScanRun, result.result_run_id)

        assert run is not None
        assert run.job_id == job.id, "작업이 만든 실행인데 어느 작업인지 남지 않았다"


class TestPressingTwiceDoesNotCrawlTwice:
    """진단 버튼을 실수로 두 번 누르면 **거래처 사이트를 두 번 긁는다.**

    2026-08-06 실측: 운영 `jobs` 17건 전부 `idempotency_key` 가 NULL 이었다 —
    콘솔 진단이 열쇠를 한 번도 넘기지 않았고, 넘기지 않으면 중복 방지가 아예
    동작하지 않는다. 부담을 지는 쪽은 우리가 아니라 남의 서버다.
    """

    def test_the_same_input_while_still_running_returns_the_first_job(
        self, db_session, principal, site  # noqa: F811
    ):
        from veo.contracts.enums import JobType
        from veo.jobs import service as jobs_service

        parameters = {"target_url": site.origin, "site_id": str(site.id)}
        first, created_first = jobs_service.submit(
            db_session, principal, job_type=JobType.SEO_SCAN, parameters=parameters
        )
        second, created_second = jobs_service.submit(
            db_session, principal, job_type=JobType.SEO_SCAN, parameters=parameters
        )

        assert created_first is True
        assert created_second is False, "같은 입력이 아직 도는데 두 번째 작업이 만들어졌다"
        assert second.id == first.id

    def test_a_different_target_still_starts_its_own_job(
        self, db_session, principal, site  # noqa: F811
    ):
        """막는 것은 **같은 입력**뿐이다. 다른 사이트 진단까지 막으면 제품이 멈춘다."""
        from veo.contracts.enums import JobType
        from veo.jobs import service as jobs_service

        jobs_service.submit(
            db_session,
            principal,
            job_type=JobType.SEO_SCAN,
            parameters={"target_url": "https://a.example/", "site_id": str(site.id)},
        )
        _, created = jobs_service.submit(
            db_session,
            principal,
            job_type=JobType.SEO_SCAN,
            parameters={"target_url": "https://b.example/", "site_id": str(site.id)},
        )

        assert created is True

    def test_a_finished_job_does_not_block_a_re_scan(
        self, db_session, principal, site  # noqa: F811
    ):
        """"고쳤으니 다시 재 주세요" 는 막으면 안 되는 일이다."""
        from veo.contracts.enums import JobType
        from veo.jobs import service as jobs_service

        parameters = {"target_url": site.origin, "site_id": str(site.id)}
        first, _ = jobs_service.submit(
            db_session, principal, job_type=JobType.SEO_SCAN, parameters=parameters
        )
        jobs_service.succeed(db_session, first.id)
        db_session.flush()

        second, created = jobs_service.submit(
            db_session, principal, job_type=JobType.SEO_SCAN, parameters=parameters
        )

        assert created is True, "끝난 작업이 재진단을 막고 있다"
        assert second.id != first.id

    def test_a_dead_job_does_not_block_a_re_scan_forever(
        self, db_session, principal, site  # noqa: F811
    ):
        """**이 중복 방지가 덫이 됐던 자리다** (운영 실측 2026-08-07 00:18).

        워커가 태스크를 등록하지 못해 버린 잡 하나가 `QUEUED` 인 채 남았다. 그 뒤로
        그 사이트는 진단할 방법이 없어졌다 — 버튼을 누를 때마다 죽은 잡을 돌려받았고,
        화면은 매번 "20분 넘게 소식이 끊겼습니다" 를 띄웠다. 죽은 잡을 되살릴 사람은
        아무도 없으므로 그 상태는 영원하다.
        """
        import datetime as _dt

        from veo.contracts.enums import JobType
        from veo.jobs import service as jobs_service

        parameters = {"target_url": site.origin, "site_id": str(site.id)}
        dead, _ = jobs_service.submit(
            db_session, principal, job_type=JobType.SEO_SCAN, parameters=parameters
        )
        db_session.flush()
        # 소식이 끊긴 지 오래됐다 — `is_stale` 이 참이 되는 그 상태 그대로.
        dead.updated_at = _dt.datetime.now(_dt.UTC) - jobs_service.STALE_AFTER * 2
        db_session.flush()
        assert jobs_service.is_stale(dead) is True, "시험이 만들려던 상태가 아니다"

        second, created = jobs_service.submit(
            db_session, principal, job_type=JobType.SEO_SCAN, parameters=parameters
        )

        assert created is True, "죽은 작업이 재진단을 영원히 막고 있다"
        assert second.id != dead.id

    def test_a_live_job_still_blocks(self, db_session, principal, site):  # noqa: F811
        """완화가 지나쳐서 원래 막던 것까지 뚫리면 안 된다 — 방금 시작한 것은 막는다."""
        from veo.contracts.enums import JobType
        from veo.jobs import service as jobs_service

        parameters = {"target_url": site.origin, "site_id": str(site.id)}
        first, _ = jobs_service.submit(
            db_session, principal, job_type=JobType.SEO_SCAN, parameters=parameters
        )
        db_session.flush()

        second, created = jobs_service.submit(
            db_session, principal, job_type=JobType.SEO_SCAN, parameters=parameters
        )

        assert created is False
        assert second.id == first.id
