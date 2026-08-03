"""정기 재진단 — 방치된 사이트를 스케줄이 다시 잰다 (P1-7b).

담당자가 잊어도 이력은 이어져야 한다: 마지막 SEO 진단이 설정한 일수보다 오래된
사이트를 골라, 콘솔 진단과 **같은 작업 경로**(:mod:`veo.seo.jobs`)로 다시 잰다.
새 코드가 하는 일은 "언제·누구를" 뿐이고, "어떻게" 는 전부 기존 파이프라인이다 —
그래서 diff 경보(P1-7a)도 스케줄 실행에서 똑같이 울린다.

## 이것은 스케줄러 인프라가 아니다

:mod:`veo.jobs.execution` 과 같은 정직성 규칙: 배포 환경에 브로커도 크론도 없다.
그래서 **API 프로세스 안의 배경 스레드**가 주기적으로 청소한다. 프로세스가 여러 대면
청소도 여러 번 돌지만, 작업 등록의 **일별 멱등키**가 같은 사이트를 하루 두 번 재지
않게 막는다. 기본은 꺼짐(``rescan_after_days = 0``) — 켜는 것은 운영 판단이다.

## 조직 경계

청소부는 조직 경계를 **넘어서** 본다 — 어느 조직의 사이트가 밀렸는지 시스템이 알아야
하기 때문이다. 사람이 부를 수 있는 경로가 아니며(router 없음), 찾은 사이트마다
그 조직의 :func:`~veo.authz.system_principal` 로 다시 갇힌 뒤에야 작업이 등록된다.
"""

from __future__ import annotations

import datetime as dt
import logging
import threading
import time
import uuid
from collections.abc import Callable, Sequence
from typing import Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from veo.authz import system_principal
from veo.contracts.enums import JobType
from veo.core.settings import get_settings
from veo.db.models.analysis import Scan, ScanRun
from veo.db.models.identity import Site
from veo.db.session import session_scope
from veo.jobs import service as jobs_service
from veo.jobs.execution import JobWork, run_detached
from veo.seo.history import SEO_KIND
from veo.seo.jobs import SCAN_STAGES, scan_work

__all__ = ["start_rescan_scheduler", "sweep_once"]

_log = logging.getLogger(__name__)

SESSION_ID: Final = "scheduled-rescan"


def _due_sites(
    session: Session, *, older_than_days: int, limit: int, now: dt.datetime
) -> Sequence[tuple[Site, dt.datetime]]:
    """마지막 SEO 진단이 기한을 넘긴 사이트, 오래 방치된 순.

    진단이 한 번도 없는 사이트는 **대상이 아니다** — 첫 진단은 사람이 등록하며 시작하는
    행위이고, 스케줄이 임의의 등록 사이트를 먼저 재기 시작하면 대상 사이트 입장에서는
    부르지 않은 크롤이다.
    """
    cutoff = now - dt.timedelta(days=older_than_days)
    latest = (
        select(
            Scan.site_id.label("site_id"),
            func.max(ScanRun.started_at).label("last_started_at"),
        )
        .join(ScanRun, ScanRun.scan_id == Scan.id)
        .where(Scan.kind == SEO_KIND)
        .group_by(Scan.site_id)
        .subquery()
    )
    statement = (
        select(Site, latest.c.last_started_at)
        .join(latest, latest.c.site_id == Site.id)
        .where(latest.c.last_started_at < cutoff)
        .order_by(latest.c.last_started_at.asc())
        .limit(limit)
    )
    return [(row[0], row[1]) for row in session.execute(statement).all()]


def sweep_once(
    session: Session,
    *,
    now: dt.datetime | None = None,
    launch: Callable[[uuid.UUID, JobWork], object] = run_detached,
) -> int:
    """밀린 사이트를 찾아 작업을 등록하고, 시작한 수를 돌려준다.

    ``launch`` 를 갈아끼울 수 있는 것은 시험을 위해서다 — 성질은 "무엇을 등록했는가"
    이지 스레드가 실제로 돌았는가가 아니다.
    """
    settings = get_settings()
    if settings.rescan_after_days <= 0:
        return 0

    moment = now or dt.datetime.now(dt.UTC)
    started = 0
    for site, _last in _due_sites(
        session,
        older_than_days=settings.rescan_after_days,
        limit=settings.rescan_max_sites_per_sweep,
        now=moment,
    ):
        principal = system_principal(site.organization_id, session_id=SESSION_ID)
        job, created = jobs_service.submit(
            session,
            principal,
            job_type=JobType.SEO_SCAN,
            project_id=site.project_id,
            stages=list(SCAN_STAGES),
            # 하루 한 번 — 프로세스가 여러 대라도, 청소가 여러 번 돌아도 같은 날의
            # 같은 사이트는 한 작업이다.
            idempotency_key=f"{SESSION_ID}:{site.id}:{moment.date().isoformat()}",
            parameters={"target_url": site.origin, "site_id": str(site.id)},
        )
        session.commit()
        if not created:
            continue
        launch(
            job.id,
            scan_work(
                organization_id=principal.organization_id,
                user_id=principal.user_id,
                roles=principal.roles,
                session_id=principal.session_id,
                is_service_account=True,
                target_url=site.origin,
                site_id=site.id,
                urls=(),
                discover=True,
                max_urls=None,
                locale="ko-KR",
            ),
        )
        started += 1
    return started


def start_rescan_scheduler() -> threading.Thread | None:
    """설정이 켜져 있으면 청소부 스레드를 시작한다. 꺼져 있으면 아무것도 안 한다."""
    settings = get_settings()
    if settings.rescan_after_days <= 0:
        return None

    interval = max(60, settings.rescan_sweep_interval_seconds)

    def loop() -> None:
        _log.info(
            "정기 재진단 시작: %s일 경과 사이트, %s초 주기",
            settings.rescan_after_days,
            interval,
        )
        while True:
            time.sleep(interval)
            try:
                with session_scope() as session:
                    started = sweep_once(session)
                if started:
                    _log.info("정기 재진단: 작업 %s건 시작", started)
            except Exception:
                # 청소 한 번의 실패가 다음 청소를 막으면 안 된다. 원문은 로그로만.
                _log.exception("정기 재진단 청소에 실패했습니다. 다음 주기에 다시 시도합니다.")

    thread = threading.Thread(target=loop, name="veo-rescan-scheduler", daemon=True)
    thread.start()
    return thread
