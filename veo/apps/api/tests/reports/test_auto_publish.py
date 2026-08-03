"""월간 리포트 자동 발행 (P2-10b) — 재고 → 발행의 월간 순환.

지키는 성질:

1. 발행일이 아니면·꺼져 있으면 아무것도 하지 않는다.
2. 지난 버전 이후 **새 진단이 있어야** 발행한다 — 같은 실행을 다시 굳힌 문서는
   새 측정처럼 읽히는 복사본이다.
3. 이번 달에 이미 버전이 있으면 건너뛴다 — 사람 발행과 자동 발행이 겹치지 않는다.
4. 자동 발행도 손 발행과 같은 경로(diagnosis_from_scan)를 지난다 — 숫자는 실측뿐.
"""

from __future__ import annotations

import datetime as dt
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from tests.reports.report_support import Tenant
from tests.reports.test_report_from_scan import measured_run  # noqa: F401  (지역 픽스처 재사용)

from veo.db.models.observation import Report, ReportVersion


@pytest.fixture
def publish_on_day_one(monkeypatch):  # type: ignore[no-untyped-def]
    import veo.reports.auto_publish as module

    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: SimpleNamespace(report_auto_publish_day=1, rescan_sweep_interval_seconds=3600),
    )


def _report_with_v1(db, org: Tenant, measured) -> Report:  # type: ignore[no-untyped-def]
    """손으로 발행한 리포트 v1 — 자동 발행이 이어 갈 출발점."""
    from veo.reports.from_scan import diagnosis_from_scan
    from veo.reports.repository import SqlReportRepository
    from veo.reports.service import ReportService

    saved, _ = measured
    reportable = diagnosis_from_scan(
        db, principal=org.analyst, scan_run_id=saved.scan_run_id, title_ko="온담 월간 보고"
    )
    created = ReportService(SqlReportRepository(db)).create_report(
        principal=org.analyst, project_id=reportable.project_id, diagnosis=reportable.diagnosis
    )
    db.commit()
    report = db.get(Report, created.report_id)
    assert report is not None
    return report


def _next_month_day_one() -> dt.datetime:
    """다음 달 1일 — 버전은 불변이라 과거로 옮길 수 없으므로, 시계를 앞으로 돌린다."""
    today = dt.datetime.now(dt.UTC)
    rolled = (today.replace(day=1) + dt.timedelta(days=40)).replace(
        day=1, hour=9, minute=0, second=0, microsecond=0
    )
    return rolled


def _second_run(db, org: Tenant, measured) -> Any:  # type: ignore[no-untyped-def]
    """같은 사이트의 더 새로운 실측 실행."""
    from tests.seo.support import build_context

    from veo.seo.history import save_scan_run
    from veo.seo.service import run_seo_scan

    saved, _ = measured
    context = build_context("broken_jsonld")
    result = run_seo_scan(context)
    second = save_scan_run(
        db,
        principal=org.analyst,
        site_id=_site_of(db, saved.scan_run_id),
        result=result,
        context=context,
        urls_attempted=len(context.documents),
        urls_collected=len(context.documents),
    )
    db.commit()
    return second


def _site_of(db, scan_run_id: uuid.UUID) -> uuid.UUID:  # type: ignore[no-untyped-def]
    from veo.db.models.analysis import Scan, ScanRun

    run = db.get(ScanRun, scan_run_id)
    return db.get(Scan, run.scan_id).site_id


class TestTheGate:
    def test_disabled_or_wrong_day_publishes_nothing(self, db, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import veo.reports.auto_publish as module
        from veo.reports.auto_publish import start_report_scheduler, sweep_reports_once

        monkeypatch.setattr(
            module,
            "get_settings",
            lambda: SimpleNamespace(
                report_auto_publish_day=0, rescan_sweep_interval_seconds=3600
            ),
        )
        assert sweep_reports_once(db) == 0
        assert start_report_scheduler() is None

        monkeypatch.setattr(
            module,
            "get_settings",
            lambda: SimpleNamespace(
                report_auto_publish_day=1, rescan_sweep_interval_seconds=3600
            ),
        )
        the_second = dt.datetime(2026, 8, 2, tzinfo=dt.UTC)
        assert sweep_reports_once(db, now=the_second) == 0


class TestTheCycle:
    def test_a_new_run_since_the_last_version_becomes_this_months_document(
        self, db, org_a: Tenant, measured_run, publish_on_day_one  # noqa: F811
    ) -> None:  # type: ignore[no-untyped-def]
        from veo.reports.auto_publish import sweep_reports_once
        from veo.reports.repository import SqlReportRepository

        report = _report_with_v1(db, org_a, measured_run)
        _second_run(db, org_a, measured_run)  # v1 이후의 더 새로운 실측

        published = sweep_reports_once(db, now=_next_month_day_one())

        # 시험 DB 에는 다른 시험이 커밋한 리포트도 남아 있을 수 있다 — 전역 발행 수가
        # 아니라 **우리 리포트에 v2 가 생겼는가**가 이 시험이 지키는 성질이다.
        assert published >= 1
        versions = SqlReportRepository(db).list_versions(org_a.analyst, report.id)
        assert sorted(one.version_number for one in versions) == [1, 2]

        # 자동 발행의 실행자 칸은 비어 있다 — 자리표시 id 를 기록하면 FK 위반이자
        # 거짓 기록이다(정기 재진단과 같은 규칙). 처음엔 이 FK 위반이
        # IntegrityError → "버전 충돌" 로 뭉뚱그려져 원인이 숨었다.
        v2 = (
            db.query(ReportVersion)
            .filter_by(report_id=report.id, version_number=2)
            .one()
        )
        assert v2.generated_by is None

    def test_no_new_measurement_means_no_new_document(
        self, db, org_a: Tenant, measured_run, publish_on_day_one  # noqa: F811
    ) -> None:  # type: ignore[no-untyped-def]
        """같은 실행을 다시 굳힌 문서는 새 측정처럼 읽히는 복사본이다."""
        from veo.reports.auto_publish import sweep_reports_once

        report = _report_with_v1(db, org_a, measured_run)
        # 새 실행 없음 — v1 은 그 실행 뒤에 발행됐으므로 run.started_at <= v1.created_at
        # 이 자연스럽게 성립한다. 다음 달 1일이 와도 굳힐 새 측정이 없다.
        from veo.reports.repository import SqlReportRepository

        sweep_reports_once(db, now=_next_month_day_one())
        versions = SqlReportRepository(db).list_versions(org_a.analyst, report.id)
        assert [one.version_number for one in versions] == [1]

    def test_a_version_already_published_this_month_blocks_the_robot(
        self, db, org_a: Tenant, measured_run, publish_on_day_one  # noqa: F811
    ) -> None:  # type: ignore[no-untyped-def]
        from veo.reports.auto_publish import sweep_reports_once

        report = _report_with_v1(db, org_a, measured_run)  # v1 은 지금(이달) 발행됨
        _second_run(db, org_a, measured_run)
        from veo.reports.repository import SqlReportRepository

        this_month_day_one = dt.datetime.now(dt.UTC).replace(day=1, hour=9)
        sweep_reports_once(db, now=this_month_day_one)
        versions = SqlReportRepository(db).list_versions(org_a.analyst, report.id)
        assert [one.version_number for one in versions] == [1]
