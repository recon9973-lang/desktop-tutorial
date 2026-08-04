"""정기 재진단 (P1-7b) — 방치된 사이트를 스케줄이 다시 잰다.

지키는 성질:

1. 대상 선정이 정직하다 — 기한을 넘긴 사이트만, 진단이 한 번도 없는 사이트는 제외
   (스케줄이 부르지 않은 크롤을 시작하면 안 된다).
2. 하루 한 번 — 청소가 여러 번 돌아도 같은 날의 같은 사이트는 한 작업이다(멱등키).
3. 예약 실행의 실행자 칸은 비어 있다 — 자리표시 id 가 기록되면 FK 위반이자 거짓
   기록이다("예약 실행이면 NULL" 이라는 스키마의 약속).
4. 설정이 꺼져 있으면(기본) 아무것도 하지 않는다.
"""

from __future__ import annotations

import datetime as dt
from datetime import UTC, datetime

import pytest

pytest.importorskip("pydantic")

from tests.seo.test_regression_alert import project, site  # noqa: F401  (지역 픽스처 재사용)

#: 진단이 시작한 시각. 저장되는 종료 시각보다 앞서야 소요 시간이 0 이 아니다 —
#: 근거는 tests/seo/test_scan_history.py 의 TestHowLongTheScanTook 에 적혀 있다.
SCAN_STARTED_AT = datetime(2026, 8, 4, 0, 0, tzinfo=UTC)


def _age_latest_run(db_session, site_row, *, days: int) -> None:
    """이 사이트의 최신 실행을 지정한 일수만큼 과거로 옮긴다."""
    from veo.db.models.analysis import Scan, ScanRun

    run = (
        db_session.query(ScanRun)
        .join(Scan, Scan.id == ScanRun.scan_id)
        .filter(Scan.site_id == site_row.id)
        .order_by(ScanRun.started_at.desc())
        .first()
    )
    assert run is not None
    run.started_at = dt.datetime.now(dt.UTC) - dt.timedelta(days=days)
    db_session.flush()


def _save_run(db_session, principal, site_row, scan_result, scan_context):  # type: ignore[no-untyped-def]
    from veo.seo.history import save_scan_run

    return save_scan_run(
        db_session, principal=principal, site_id=site_row.id,
        result=scan_result, context=scan_context,
        urls_attempted=1, urls_collected=1, started_at=SCAN_STARTED_AT,
    )


@pytest.fixture
def rescan_on(monkeypatch):  # type: ignore[no-untyped-def]
    """청소를 켠 설정 — 시험 안에서만."""
    from types import SimpleNamespace

    import veo.seo.rescan as rescan_module

    monkeypatch.setattr(
        rescan_module,
        "get_settings",
        lambda: SimpleNamespace(
            rescan_after_days=7,
            rescan_sweep_interval_seconds=3600,
            rescan_max_sites_per_sweep=3,
        ),
    )


class TestWhoIsDue:
    def test_only_overdue_sites_are_picked_and_never_unscanned_ones(
        self, db_session, principal, site, scan_result, scan_context, rescan_on  # noqa: F811
    ):
        from veo.db.models.identity import Site
        from veo.seo.rescan import sweep_once

        # 진단이 한 번도 없는 사이트 — 대상이 아니어야 한다.
        untouched = Site(
            organization_id=site.organization_id,
            project_id=site.project_id,
            origin="https://untouched.example",
            display_name="한 번도 안 잰 곳",
            is_primary=False,
            crawl_settings={},
        )
        db_session.add(untouched)
        _save_run(db_session, principal, site, scan_result, scan_context)
        _age_latest_run(db_session, site, days=30)

        launched: list[object] = []
        started = sweep_once(
            db_session, launch=lambda job_id, work: launched.append(job_id)
        )

        assert started == 1, "기한을 넘긴 사이트 하나만 시작해야 한다"
        assert len(launched) == 1

    def test_a_fresh_site_is_left_alone(
        self, db_session, principal, site, scan_result, scan_context, rescan_on  # noqa: F811
    ):
        from veo.seo.rescan import sweep_once

        _save_run(db_session, principal, site, scan_result, scan_context)  # 방금 잼

        started = sweep_once(db_session, launch=lambda job_id, work: None)

        assert started == 0


class TestOncePerDay:
    def test_a_second_sweep_the_same_day_starts_nothing(
        self, db_session, principal, site, scan_result, scan_context, rescan_on  # noqa: F811
    ):
        from veo.seo.rescan import sweep_once

        _save_run(db_session, principal, site, scan_result, scan_context)
        _age_latest_run(db_session, site, days=30)

        first = sweep_once(db_session, launch=lambda job_id, work: None)
        second = sweep_once(db_session, launch=lambda job_id, work: None)

        assert first == 1
        assert second == 0, "같은 날의 같은 사이트가 두 번 등록되면 대상에 크롤이 두 배로 간다"


class TestTheSystemActor:
    def test_a_service_account_save_leaves_the_operator_column_empty(
        self, db_session, site, scan_result, scan_context  # noqa: F811
    ):
        """예약 실행이면 NULL — 스키마의 약속을 저장 경로가 지킨다."""
        from veo.authz import system_principal
        from veo.db.models.analysis import ScanRun
        from veo.seo.history import save_scan_run

        actor = system_principal(site.organization_id, session_id="scheduled-rescan")
        saved = save_scan_run(
            db_session, principal=actor, site_id=site.id,
            result=scan_result, context=scan_context,
            urls_attempted=1, urls_collected=1, started_at=SCAN_STARTED_AT,
        )

        run = db_session.get(ScanRun, saved.scan_run_id)
        assert run.requested_by_user_id is None

    def test_a_scheduled_job_row_has_no_requester(
        self, db_session, site  # noqa: F811
    ):
        from veo.authz import system_principal
        from veo.contracts.enums import JobType
        from veo.jobs import service as jobs_service

        actor = system_principal(site.organization_id, session_id="scheduled-rescan")
        job, created = jobs_service.submit(
            db_session, actor,
            job_type=JobType.SEO_SCAN,
            project_id=site.project_id,
            parameters={"target_url": site.origin},
        )

        assert created
        assert job.requested_by is None


class TestTheSwitch:
    def test_disabled_by_default_means_no_thread_and_no_sweep(
        self, db_session, monkeypatch
    ):
        from types import SimpleNamespace

        import veo.seo.rescan as rescan_module
        from veo.seo.rescan import start_rescan_scheduler, sweep_once

        monkeypatch.setattr(
            rescan_module,
            "get_settings",
            lambda: SimpleNamespace(
                rescan_after_days=0,
                rescan_sweep_interval_seconds=3600,
                rescan_max_sites_per_sweep=3,
            ),
        )

        assert start_rescan_scheduler() is None
        assert sweep_once(db_session, launch=lambda job_id, work: None) == 0
