"""월간 리포트 자동 발행 — 리테이너 문서가 사람 손을 기다리지 않는다 (P2-10b).

설정한 날(``report_auto_publish_day``, 기본 0=꺼짐)이 오면, 리포트가 있는 프로젝트마다
**가장 최근의 실측 진단**으로 새 버전을 발행한다. 숫자는 전부 저장된 실행에서 온다 —
`diagnosis_from_scan` 그대로이므로, 자동이라고 해서 손으로 만든 문서와 다른 규칙으로
만들어지지 않는다.

발행하지 않는 경우가 발행하는 경우만큼 중요하다:

* **이번 달에 이미 버전이 있으면** 건너뛴다 — 사람이 먼저 발행했으면 자동이 겹쳐
  두 번째 문서를 만들지 않는다.
* **지난 버전 이후 새 진단이 없으면** 건너뛴다 — 같은 실행을 다시 굳힌 문서는 새
  측정처럼 읽히는 복사본이다. 정기 재진단(P1-7b)을 켜 두면 새 실행이 먼저 쌓이고,
  이 발행이 그 뒤를 따른다: 재고 → 발행의 월간 순환.

실행 주체는 :func:`~veo.authz.system_principal` — 실행자 칸은 비고, 조직 경계는
리포트마다 그 조직의 주체로 다시 갇힌다(정기 재진단과 같은 규칙). 스케줄 방식도
같다: 브로커도 크론도 없는 배포이므로 프로세스 안의 배경 스레드가 주기적으로
확인하고, 프로세스가 여러 대일 때의 중복은 이달-발행-존재 검사와 버전 번호 유니크
제약이 함께 막는다.
"""

from __future__ import annotations

import datetime as dt
import logging
import threading
import time
from typing import Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from veo.authz import system_principal
from veo.core.settings import get_settings
from veo.db.models.analysis import Scan, ScanRun, ScoreResult
from veo.db.models.identity import Site
from veo.db.models.observation import Report, ReportVersion
from veo.db.session import session_scope
from veo.reports.from_scan import ScanNotReportable, diagnosis_from_scan
from veo.reports.repository import SqlReportRepository
from veo.reports.service import ReportService, ReportVersionConflictError
from veo.seo.history import SEO_KIND

__all__ = ["start_report_scheduler", "sweep_reports_once"]

_log = logging.getLogger(__name__)

SESSION_ID: Final = "scheduled-report"

#: 한 청소에서 발행할 최대 수 — 발행은 DB 작업뿐이라 크롤보다 싸지만, 밀린 것을
#: 한 번에 다 만들면 실패 하나가 전부를 물고 넘어진다.
MAX_PER_SWEEP: Final = 20


def _latest_version_at(session: Session, report_id: object) -> dt.datetime | None:
    return session.execute(
        select(func.max(ReportVersion.created_at)).where(ReportVersion.report_id == report_id)
    ).scalar_one_or_none()


def _latest_scored_run(session: Session, project_id: object) -> ScanRun | None:
    statement = (
        select(ScanRun)
        .join(Scan, Scan.id == ScanRun.scan_id)
        .join(Site, Site.id == Scan.site_id)
        .join(ScoreResult, ScoreResult.scan_run_id == ScanRun.id)
        .where(
            Site.project_id == project_id,
            Scan.kind == SEO_KIND,
            ScoreResult.status == "SCORED",
        )
        # 결과가 나온 순서다. 시작 시각으로 고르면 오래 걸린 진단이 나중에 시작해 먼저
        # 끝난 진단보다 최신으로 뽑힌다 — 발행되는 것은 결과이므로 결과가 늦게 나온 쪽이
        # 최신이다. 동점은 저장 순서로 가른다.
        .order_by(ScanRun.finished_at.desc(), ScanRun.created_at.desc())
        .limit(1)
    )
    return session.execute(statement).scalars().first()


def sweep_reports_once(session: Session, *, now: dt.datetime | None = None) -> int:
    """발행한 수를 돌려준다. 오늘이 발행일이 아니면 아무것도 하지 않는다."""
    settings = get_settings()
    day = settings.report_auto_publish_day
    if day <= 0:
        return 0

    moment = now or dt.datetime.now(dt.UTC)
    if moment.day != day:
        return 0

    published = 0
    # **오래 안 나간 것부터.** 정렬 없이 읽고 MAX_PER_SWEEP 에서 끊으면 DB 가
    # 돌려주는 순서에 따라 매달 같은 일부만 발행되고 나머지는 영영 밀린다 —
    # 리포트가 상한을 넘는 순간부터 조용히 그렇게 된다(2026-08-06 감사).
    #
    # 마지막 발행이 없는 리포트(한 번도 안 나간 것)가 가장 앞이다.
    last_published = (
        select(
            ReportVersion.report_id.label("report_id"),
            func.max(ReportVersion.created_at).label("last_at"),
        )
        .group_by(ReportVersion.report_id)
        .subquery()
    )
    reports = (
        session.execute(
            select(Report)
            .outerjoin(last_published, last_published.c.report_id == Report.id)
            .order_by(last_published.c.last_at.asc().nulls_first(), Report.id)
        )
        .scalars()
        .all()
    )
    for report in reports:
        if published >= MAX_PER_SWEEP:
            # **말없이 자르지 않는다.** 이 줄이 없으면 "전부 발행했다" 와 "상한에
            # 걸려 일부만 했다" 가 화면에서 똑같이 보인다.
            _log.warning(
                "월간 자동 발행이 이번 회차 상한(%d건)에 걸렸습니다. 남은 리포트는 "
                "다음 회차로 밀립니다 — 오래 안 나간 것부터 처리하므로 순서는 돌아옵니다.",
                MAX_PER_SWEEP,
            )
            break

        last_at = _latest_version_at(session, report.id)
        if (
            last_at is not None
            and last_at.year == moment.year
            and last_at.month == moment.month
        ):
            # 사람이 먼저 발행했든 다른 프로세스의 청소가 먼저 지나갔든 — 이달 문서는
            # 이미 있다.
            continue

        run = _latest_scored_run(session, report.project_id)
        if run is None:
            continue
        if last_at is not None and run.finished_at is not None and run.finished_at <= last_at:
            # 새 측정이 없다 — 같은 실행을 다시 굳히면 복사본이 새 측정처럼 읽힌다.
            #
            # **끝난 시각**으로 본다. 예전에는 `started_at` 을 봤는데, 그때는 그 칸에
            # 저장 시각이 들어 있어서 둘이 같은 값이었다(2026-08-04 에 고친 결함). 이제
            # `started_at` 은 진단이 시작한 시각이라, 지난 발행 **전에 시작해 후에 끝난**
            # 진단이 "새 측정이 없다" 로 걸러진다. 그 진단의 결과는 분명히 새것이다.
            continue

        principal = system_principal(report.organization_id, session_id=SESSION_ID)
        try:
            reportable = diagnosis_from_scan(
                session, principal=principal, scan_run_id=run.id, title_ko=report.title
            )
            ReportService(SqlReportRepository(session)).create_version(
                principal=principal, report_id=report.id, diagnosis=reportable.diagnosis
            )
            session.commit()
            published += 1
        except (ScanNotReportable, ReportVersionConflictError) as refused:
            # 이 리포트 하나의 사정이 나머지 발행을 막으면 안 된다. 원문은 로그로만.
            session.rollback()
            _log.warning("자동 발행 건너뜀 (report=%s): %s", report.id, refused)
        except Exception:
            session.rollback()
            _log.exception("자동 발행 실패 (report=%s). 다음 달에 다시 시도합니다.", report.id)

    return published


def start_report_scheduler() -> threading.Thread | None:
    """설정이 켜져 있으면 발행 청소부 스레드를 시작한다. 꺼져 있으면 아무것도 안 한다."""
    settings = get_settings()
    if settings.report_auto_publish_day <= 0:
        return None

    interval = max(60, settings.rescan_sweep_interval_seconds)

    def loop() -> None:
        _log.info(
            "월간 리포트 자동 발행 대기: 매월 %s일, 확인 주기 %s초",
            settings.report_auto_publish_day,
            interval,
        )
        while True:
            time.sleep(interval)
            try:
                with session_scope() as session:
                    published = sweep_reports_once(session)
                if published:
                    _log.info("월간 리포트 자동 발행: %s건", published)
            except Exception:
                _log.exception("자동 발행 청소에 실패했습니다. 다음 주기에 다시 시도합니다.")

    thread = threading.Thread(target=loop, name="veo-report-scheduler", daemon=True)
    thread.start()
    return thread
