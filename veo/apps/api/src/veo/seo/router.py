"""``/seo`` — the SEO readiness check catalogue and the scan endpoint.

This router is **not mounted here**. ``veo.api.app`` belongs to the integrator; see
``INTEGRATION_REQUEST.md``. Everything below is a plain :class:`~fastapi.APIRouter` that
can be included under the API prefix without further wiring.

Permissions follow the platform matrix exactly: ``scan:read`` to read the catalogue,
``scan:run`` to run a scan. Both are declared as route dependencies so the check runs
before the request body is parsed.
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal, tenant_select
from veo.brands.service import list_brands
from veo.collect.from_crawl import context_from_crawl
from veo.contracts.enums import JobType
from veo.contracts.envelope import ApiResponse
from veo.db.models.identity import Site
from veo.db.session import get_db
from veo.geo.companion import score_and_save_geo_companion
from veo.jobs import service as jobs_service
from veo.jobs.dispatch import dispatch
from veo.jobs.router import job_payload
from veo.jobs.schemas import JobPayload
from veo.organizations.http import guard
from veo.scoring import ScoreResult
from veo.scoring.improvements import rank_improvements
from veo.scoring.page import PageScore
from veo.seo.captures import read_captures
from veo.seo.collectors import CATEGORY_COLLECTORS, PROVIDER_BACKED_CHECKS
from veo.seo.crawl import ConsoleCrawler, CrawlOutcome, CrawlRefusal
from veo.seo.fix_examples import code_example_for, with_brand
from veo.seo.history import (
    SEO_KIND,
    read_scan_history,
    read_scan_report,
    save_scan_run,
)
from veo.seo.jobs import SCAN_STAGES, scan_work
from veo.seo.measure_performance import prewarm, with_performance
from veo.seo.pages import page_breakdown
from veo.seo.perf_cache import PerformanceCache
from veo.seo.regression import maybe_alert_regression
from veo.seo.schemas import (
    CapSummary,
    CategorySummary,
    CheckCatalogueEntry,
    CheckCataloguePayload,
    EvidenceSummary,
    FetchCaptureSummary,
    GeoCompanionSummary,
    ImprovementSummary,
    IssueSummary,
    OutcomeSummary,
    PageChecksSummary,
    PageDetailPayload,
    PageLossSummary,
    PageScoreSummary,
    PageStageSummary,
    ScanCapturesPayload,
    ScanHistoryEntry,
    ScanHistoryPayload,
    ScanPagesPayload,
    ScanPayload,
    ScoreSummary,
    SiteCheckSummary,
    SiteScanRequest,
    UnknownCheckSummary,
)
from veo.seo.service import SeoScanResult, load_seo_spec, run_seo_scan
from veo.seo.timing import ScanTimings, stage
from veo.usage import record_pagespeed_calls

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/seo", tags=["seo"])

ScanReader = Annotated[Principal, Depends(guard(Permission.SCAN_READ))]
ScanRunner = Annotated[Principal, Depends(guard(Permission.SCAN_RUN))]

_COLLECTOR_BY_CHECK = {
    check_id: factory.__name__
    for factory in CATEGORY_COLLECTORS.values()
    for check_id in factory().check_ids
}


@router.get(
    "/checks",
    response_model=ApiResponse[CheckCataloguePayload],
    summary="SEO 준비도 검사 항목 전체",
    description=(
        "발행된 명세가 정의한 47개 검사 항목과 각 항목을 담당하는 수집기를 그대로 보여 줍니다. "
        "`requires_provider`가 true인 항목은 외부 연동이 없으면 측정할 수 없으며, 그 경우 "
        "점수를 깎는 대신 UNKNOWN으로 기록되어 측정 범위만 낮아집니다."
    ),
)
def list_checks(
    principal: ScanReader, request_id: RequestId
) -> ApiResponse[CheckCataloguePayload]:
    spec = load_seo_spec()
    entries = [
        CheckCatalogueEntry(
            id=check.id,
            title_ko=check.title_ko,
            title_en=check.title_en,
            category_id=category.id,
            category_name_ko=category.name_ko,
            severity=str(check.severity),
            scope=check.scope,
            remediation_owner=check.remediation_owner,
            applicability_ko=check.applicability_ko,
            evidence_required=list(check.evidence_required),
            engine_scope=list(check.engine_scope),
            collector=_COLLECTOR_BY_CHECK.get(check.id, "미구현"),
            requires_provider=check.id in PROVIDER_BACKED_CHECKS,
        )
        for category in spec.categories
        for check in category.checks
    ]
    payload = CheckCataloguePayload(
        spec_id=spec.spec_id,
        spec_version=spec.version,
        spec_checksum=spec.checksum,
        checks=entries,
    )
    return ok(
        payload,
        request_id,
        spec_id=spec.spec_id,
        spec_version=spec.version,
        spec_checksum=spec.checksum,
    )


@router.post(
    "/scans",
    response_model=ApiResponse[ScanPayload],
    summary="주소를 받아 직접 수집하고 SEO 준비도 채점",
    description=(
        "대표 주소를 받아 VEO 가 직접 페이지를 가져온 뒤 47개 항목을 판정하고 "
        "발행된 명세로 채점합니다. 수집은 SSRF 차단·대상 호스트 예산·응답 크기와 시간 "
        "상한이 걸린 크롤러가 담당하며, 무료 공개 진단과 같은 안전장치를 씁니다. "
        "다른 점은 보는 페이지 수뿐입니다 — 공개 진단은 한 장만 보므로 사이트 전체를 "
        "봐야 판정되는 항목이 측정 불가로 남습니다."
    ),
)
def run_site_scan(
    payload: SiteScanRequest,
    principal: ScanRunner,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
) -> ApiResponse[ScanPayload]:
    spec = load_seo_spec()
    try:
        report, _saved_run_id = run_console_scan(
            db, principal=principal, payload=payload, request_id=str(request_id)
        )
    except CrawlRefusal as refusal:
        raise HTTPException(
            status_code=refusal.status_code, detail=refusal.error.model_dump(mode="json")
        ) from refusal
    return ok(
        report,
        request_id,
        spec_id=spec.spec_id,
        spec_version=spec.version,
        spec_checksum=spec.checksum,
    )


@router.post(
    "/scan-jobs",
    response_model=ApiResponse[JobPayload],
    status_code=202,
    summary="진단을 작업으로 등록하고 즉시 돌아온다",
    description=(
        "동기 진단(`POST /seo/scans`)과 같은 파이프라인을 배경 작업으로 돌립니다. "
        "응답은 작업 표이며, 진행은 `GET /jobs/{id}` 로 물어봅니다. 끝나면 "
        "`result_run_id` 로 저장된 실행을 엽니다. 결과가 남아야 하므로 `site_id` 없이는 "
        "받지 않습니다 — 등록 없이 잠깐 재보는 간편 진단은 동기 경로를 쓰십시오."
    ),
)
def submit_scan_job(
    payload: SiteScanRequest,
    principal: ScanRunner,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description="같은 키로 다시 부르면 원래 작업을 돌려줍니다.",
        ),
    ] = None,
) -> ApiResponse[JobPayload]:
    if payload.site_id is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "site_id 없이는 작업으로 돌릴 수 없습니다 — 저장할 자리가 없어 "
                "결과가 사라집니다."
            ),
        )
    # 잘못된 요청 때문에 실패할 작업을 만들어 두지 않는다 — 등록 전에 거른다.
    _assert_site_exists(db, principal=principal, site_id=payload.site_id)
    project_id = db.execute(
        tenant_select(Site, principal).where(Site.id == payload.site_id)
    ).scalar_one().project_id

    job, created = jobs_service.submit(
        db,
        principal,
        job_type=JobType.SEO_SCAN,
        project_id=project_id,
        # 관측 실행(`observations/router.py`)이 진작 받던 것을 여기만 안 받고 있었다.
        # 열쇠가 없어도 `submit` 이 "같은 입력으로 돌고 있는 작업" 을 돌려주지만,
        # 부르는 쪽이 명시할 길은 열어 둔다 — 그쪽이 더 정확하다.
        idempotency_key=idempotency_key,
        stages=list(SCAN_STAGES),
        parameters={
            "target_url": payload.target_url,
            "site_id": str(payload.site_id),
            "urls": list(payload.urls),
            "discover": payload.discover,
            "max_urls": payload.max_urls,
            "locale": payload.locale,
        },
    )
    job_id = job.id
    db.commit()
    db.refresh(job)

    if created:
        # 큐가 설정돼 있으면 워커로, 없으면 예전처럼 배경 스레드로. 설정하지 않은
        # 배포는 오늘과 똑같이 동작한다 — 워커가 아직 안 떴는데 큐에만 넣으면 작업이
        # 아무도 집어가지 않은 채 대기하고, 그것은 지금보다 나쁘다.
        dispatch(
            job_id,
            scan_work(
                organization_id=principal.organization_id,
                user_id=principal.user_id,
                roles=principal.roles,
                session_id=principal.session_id,
                target_url=payload.target_url,
                site_id=payload.site_id,
                urls=tuple(payload.urls),
                discover=payload.discover,
                max_urls=payload.max_urls,
                locale=payload.locale,
            ),
            job_type=JobType.SEO_SCAN,
            # 큐로 갈 때 건너가는 값들. 함수는 프로세스를 못 건너므로, 워커가 이 값으로
            # 같은 작업을 다시 만든다. 실행자 정보가 빠지면 워커가 **엉뚱한 조직의 일을
            # 엉뚱한 권한으로** 돌리게 되므로 여기 전부 실린다.
            parameters={
                "organization_id": str(principal.organization_id),
                "user_id": str(principal.user_id),
                "roles": [str(role) for role in principal.roles],
                "session_id": principal.session_id,
                "target_url": payload.target_url,
                "site_id": str(payload.site_id),
                "urls": list(payload.urls),
                "discover": payload.discover,
                "max_urls": payload.max_urls,
                "locale": payload.locale,
            },
        )

    return ok(job_payload(job), request_id)


def run_console_scan(
    db: Session,
    *,
    principal: Principal,
    payload: SiteScanRequest,
    request_id: str,
    job_id: uuid.UUID | None = None,
) -> tuple[ScanPayload, uuid.UUID | None]:
    """콘솔 진단 파이프라인 — 수집→채점→(동반 GEO)→저장→하락 경보.

    동기 엔드포인트(위)와 배경 작업(:mod:`veo.seo.jobs`)이 **같은 이 함수를** 쓴다.
    두 벌로 갈라지는 순간 한쪽만 고쳐지는 날이 온다. 수집 거절은
    :class:`CrawlRefusal` 로, 없는 사이트는 404 :class:`HTTPException` 으로 올린다 —
    HTTP 로 옮길지 작업 실패로 옮길지는 호출자가 정한다.

    반환은 (응답 본문, 저장된 실행 id). 사이트를 지정하지 않은 진단은 저장하지
    않으므로 id 가 ``None`` 이다.
    """
    # 어느 단계가 시간을 쓰는지, 그리고 **언제 시작했는지** 남긴다. 남기지 않으면
    # "느려졌다" 는 말에 답할 수 없고, 고친 뒤 빨라졌는지도 확인할 수 없다(2026-08-03 에
    # 이 내역을 알아내려고 크롤러를 따로 돌려야 했다).
    #
    # 파이프라인 **맨 앞**에서 만든다. 예전에는 크롤 직전에 만들었는데, 그러면 명세를
    # 읽고 성능 측정을 미리 띄우는 시간이 진단 시간에서 빠진다. 그 시간도 고객이 기다리는
    # 시간이다.
    timings = ScanTimings()

    spec = load_seo_spec()
    # 사이트를 지정했다면 **가져오기 전에** 존재를 확인한다. 없는 사이트를 위해 남의
    # 서버에 요청을 보내고 나서 404 를 돌려주는 것은 순서가 틀렸다.
    if payload.site_id is not None:
        _assert_site_exists(db, principal=principal, site_id=payload.site_id)
    # 대표 주소가 목록의 맨 앞에 오도록 맞춘다. 중복은 제거하되 순서는 유지한다 —
    # 첫 문서가 primary 가 되고, 그것이 canonical·robots 판정의 기준점이다.
    requested = [payload.target_url, *payload.urls]
    targets = list(dict.fromkeys(url for url in requested if url.strip()))

    # 성능 측정을 **크롤과 동시에** 시작한다. 대표 주소는 지금 이미 알고 있고, 구글에
    # 한 번 묻는 데 20~60초가 걸린다 — 크롤이 끝나기를 기다릴 이유가 없다.
    # 결과는 캐시로 가고 아래 with_performance 가 집어 간다. 실패하면 원래대로 나중에
    # 잰다(덤이라 진단을 멈추지 않는다).
    # 캐시는 **이 진단 하나**가 만들어 쓰고 버린다. 전역에 두면 고치고 다시 재는 사람이
    # 옛 값을 보게 되고, 그 순간 이 도구는 "고쳐도 안 바뀐다" 는 거짓을 말한다.
    perf_cache = PerformanceCache()
    prewarm(payload.target_url, cache=perf_cache)

    crawler = ConsoleCrawler()
    with stage("수집", timings):
        if payload.discover:
            outcome = crawler.crawl(
                payload.target_url, extra_urls=targets[1:], max_urls=payload.max_urls
            )
        else:
            documents, robots_txt = crawler.collect(targets)
            outcome = CrawlOutcome(documents=documents, robots_txt=robots_txt)

    context = context_from_crawl(
        target_url=payload.target_url,
        spec=spec,
        outcome=outcome,
        locale=payload.locale,
    )
    # 성능은 크롤로 알 수 없다. 구글에 따로 물어야 하고, 그래서 여기서 한 번 더 나간다.
    # 자격증명이 없으면 문맥을 손대지 않고 그대로 돌려주므로, 키가 없는 배포에서는
    # 이 줄이 아무 일도 하지 않는다 — 소켓도 열리지 않는다.
    with stage("성능 측정", timings):
        context, performance = with_performance(context, cache=perf_cache)
    with stage("채점", timings):
        result = run_seo_scan(context)
    # 한 번만 조회해서 SEO·GEO 양쪽에 **같은 값**을 쓴다. 두 번 조회하면 언젠가
    # 한쪽만 바뀌고, 같은 진단의 두 화면이 다른 상호를 붙여넣으라고 말하게 된다.
    brand_name = _registered_brand_name(db, principal, site_id=payload.site_id)
    report = _scan_payload(result, brand_name=brand_name)

    # 유료 한도를 쓴 것은 사실이므로 사이트를 지정하지 않은 진단에서도 남긴다.
    # PageSpeed 는 하루 25,000회이고 진단 한 번에 최대 5회가 나간다. 기록이 없으면
    # 어느 날 갑자기 모든 고객의 성능이 측정 불가가 되고 이유를 알 수 없다.
    if performance is not None and performance.calls:
        record_pagespeed_calls(
            db,
            performance.calls,
            organization_id=principal.organization_id,
            request_id=request_id,
        )

    if payload.site_id is not None:
        # 같은 크롤로 GEO 도 채점해 별도 실행으로 저장한다 — 페이지를 두 번 가져올
        # 이유가 없다(콘솔 재설계 ①). 실패해도 SEO 결과는 그대로이고, 실패 사실이
        # 응답에 실린다. **SEO 저장보다 먼저** 하는 이유: 아래 스냅샷에 동반 실행의
        # 식별자가 실려야, 지난 SEO 결과를 다시 열 때 화면(SEO|GEO 전환기)이 짝이
        # 되는 GEO 실행을 찾을 수 있다(재설계 ②).
        companion = score_and_save_geo_companion(
            db,
            principal=principal,
            site_id=payload.site_id,
            target_url=payload.target_url,
            outcome=outcome,
            locale=payload.locale,
            urls_attempted=outcome.attempted,
            urls_collected=len(outcome.documents),
            # 같은 크롤을 나눠 쓰므로 시작 시각도 같다. GEO 는 SEO 보다 **먼저** 저장되니
            # 종료 시각만 더 이르다 — 두 실행이 한 요청 안에서 겹쳐 돌았다는 사실이
            # 그대로 남는다.
            started_at=timings.started_at,
            brand_name=brand_name,
        )
        report = report.model_copy(
            update={
                "geo": GeoCompanionSummary(
                    scan_run_id=companion.scan_run_id,
                    score=companion.score,
                    band_id=companion.band_id,
                    spec_version=companion.spec_version,
                    failure_note_ko=companion.failure_note_ko,
                )
            }
        )
        # 보여준 것을 그대로 남긴다. 조치 문구는 수집기가 발견한 값을 넣어 만들어 내므로
        # 명세로부터 되살릴 수 없다 — 스냅샷이 없으면 다시 열었을 때 문장이 달라진다.
        # 저장까지가 진단이다. 여기서 끝내야 "180초" 의 마지막 조각이 빠지지 않는다.
        with stage("저장", timings):
            saved = save_scan_run(
                db,
                principal=principal,
                site_id=payload.site_id,
                result=result,
                # 맥락째 넘긴다. 어떤 조건에서 쟀는지는 여기서만 알 수 있고, 저장하는
                # 쪽에서 추측하면 상수가 사실 자리에 앉는다.
                context=context,
                urls_attempted=outcome.attempted,
                urls_collected=len(outcome.documents),
                report_snapshot=report.model_dump(mode="json"),
                started_at=timings.started_at,
                job_id=job_id,
            )
        # 저장이 끝난 뒤에만 비교한다 — 이 진단이 '직전' 과 비교 가능한 최신이
        # 되는 시점이 지금이다. 실패해도 저장·응답은 그대로다.
        maybe_alert_regression(
            db,
            principal=principal,
            site_id=payload.site_id,
            origin=payload.target_url,
            scan_run_id=saved.scan_run_id,
        )
        _log.info(
            "seo.scan.timings total=%dms %s",
            round(timings.total_ms),
            timings.summary_ko(),
            extra={"stages_ms": {k: round(v) for k, v in timings.elapsed_ms.items()}},
        )
        return report, saved.scan_run_id

    _log.info(
        "seo.scan.timings total=%dms %s",
        round(timings.total_ms),
        timings.summary_ko(),
        extra={"stages_ms": {k: round(v) for k, v in timings.elapsed_ms.items()}},
    )
    return report, None


@router.get(
    "/scans/history",
    response_model=ApiResponse[ScanHistoryPayload],
    summary="한 사이트의 진단 이력",
    description=(
        "최신순으로 돌려줍니다. 각 줄에는 그때 적용된 채점 명세의 버전과 체크섬이 함께 "
        "들어 있습니다 — 명세가 개정되면 같은 사이트라도 다른 규칙으로 채점되므로, "
        "버전이 다른 두 점수를 그대로 비교하면 안 됩니다."
    ),
)
def read_site_scan_history(
    principal: ScanReader,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
    site_id: Annotated[uuid.UUID, Query(description="이력을 볼 사이트입니다.")],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    kind: Annotated[
        str,
        Query(
            description=(
                "어느 눈금의 이력인가 — `SEO` 또는 `GEO`. 한 번의 진단이 두 눈금을 각각 "
                "저장하므로 이력도 눈금마다 따로 있습니다. 기본값은 `SEO` 입니다."
            ),
            pattern="^(SEO|GEO)$",
        ),
    ] = SEO_KIND,
) -> ApiResponse[ScanHistoryPayload]:
    _assert_site_exists(db, principal=principal, site_id=site_id)
    # 저장은 처음부터 눈금별로 하고 있었는데(companion 이 kind=GEO 로 남긴다) 꺼낼 길이
    # 없었다. 그래서 GEO 탭이 SEO 이력과 SEO 증감을 그렸다 — 화면은 GEO 라고 말하면서
    # SEO 숫자를 보여주는 상태였다(사용자 지적).
    entries = read_scan_history(
        db, principal=principal, site_id=site_id, limit=limit, kind=kind
    )
    return ok(
        ScanHistoryPayload(
            site_id=site_id,
            entries=[
                ScanHistoryEntry(
                    scan_run_id=entry.scan_run_id,
                    started_at=entry.started_at,
                    finished_at=entry.finished_at,
                    status=entry.status,
                    urls_collected=entry.urls_collected,
                    score=entry.score,
                    band_id=entry.band_id,
                    coverage=entry.coverage,
                    confidence=entry.confidence,
                    spec_version=entry.spec_version,
                    spec_checksum=entry.spec_checksum,
                    requested_by_name=entry.requested_by_name,
                    comparable_with_latest=entry.comparable_with_latest,
                    incomparable_reason_ko=entry.incomparable_reason_ko,
                )
                for entry in entries
            ],
        ),
        request_id,
    )


@router.get(
    "/scans/{scan_run_id}",
    response_model=ApiResponse[ScanPayload],
    summary="지난 진단 결과를 그대로 다시 보기",
    description=(
        "저장된 보고서를 그대로 돌려줍니다. 다시 수집하지 않으므로 대상 사이트에 요청이 "
        "가지 않습니다. 같은 주소를 하루에 여러 번 다시 재지 않아도 되도록, 변경을 "
        "확인하려고 **일부러** 재측정할 때만 새로 수집합니다."
    ),
)
def read_saved_scan(
    scan_run_id: uuid.UUID,
    principal: ScanReader,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
) -> ApiResponse[ScanPayload]:
    # 축을 말한다 — 동반 저장(companion)으로 같은 조직에 GEO 실행이 쌓이기 시작했고,
    # 이 문은 SEO 모양의 스냅샷만 돌려줄 수 있다. GEO 는 /geo/readiness/scans/{id} 로.
    report = read_scan_report(
        db, principal=principal, scan_run_id=scan_run_id, kind=SEO_KIND
    )
    if report is None:
        raise HTTPException(status_code=404, detail="scan run not found")
    return ok(ScanPayload.model_validate(report), request_id)


@router.get(
    "/scans/{scan_run_id}/captures",
    response_model=ApiResponse[ScanCapturesPayload],
    summary="이 진단이 실제로 받은 응답 — 판정이 아니라 원자료",
    description=(
        "진단이 서버로부터 **받은 그대로**를 돌려줍니다. 다시 수집하지 않습니다.\n\n"
        "점수가 이해되지 않을 때 여기부터 보십시오. 판정은 이 바이트에서 나왔으므로, "
        "판정이 틀렸다면 둘 중 하나입니다 — 이 바이트가 그 페이지가 아니거나(수집 문제), "
        "이 바이트를 잘못 읽었거나(채점 문제). 어느 쪽인지는 이 화면에서만 갈립니다.\n\n"
        "**못 읽은 응답이 앞에 옵니다.** 잘 읽은 페이지는 점수가 설명해 주지만, 못 읽은 "
        "응답은 아무것도 말해 주지 않기 때문입니다.\n\n"
        "보관은 대상마다 **가장 최근 진단 한 번분**입니다. 본문은 응답당 64KB 까지이며, "
        "넘으면 앞부분만 담고 `truncated` 로 그 사실을 알립니다."
    ),
)
def read_scan_captures(
    scan_run_id: uuid.UUID,
    principal: ScanReader,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
) -> ApiResponse[ScanCapturesPayload]:
    rows = read_captures(
        db, organization_id=principal.organization_id, run_id=scan_run_id
    )
    unread = sum(1 for row in rows if row.read_failure_ko)
    if not rows:
        note = (
            "이 실행의 보관본이 없습니다. 보관은 대상마다 가장 최근 진단 한 번분이므로, "
            "그 뒤에 다시 진단했거나 보관 기능이 생기기 전의 실행입니다."
        )
    elif unread:
        note = f"{len(rows)}건 중 {unread}건은 문서로 읽지 못한 응답입니다. 그것이 앞에 옵니다."
    else:
        note = f"{len(rows)}건 모두 문서로 읽었습니다."
    return ok(
        ScanCapturesPayload(
            scan_run_id=scan_run_id,
            captures=[
                FetchCaptureSummary(
                    url=row.url,
                    final_url=row.final_url,
                    status=row.status,
                    headers=dict(row.headers or {}),
                    request_headers=dict(row.request_headers or {}),
                    # 바이트를 그대로 보여 준다. 못 읽은 응답일수록 원문이 중요하므로
                    # 깨진 글자도 지우지 않고 대체 문자로 남긴다.
                    body=bytes(row.body).decode("utf-8", errors="replace"),
                    byte_size=row.byte_size,
                    truncated=row.truncated,
                    content_hash=row.content_hash,
                    fetched_at=row.fetched_at,
                    read_failure_ko=row.read_failure_ko,
                )
                for row in rows
            ],
            note_ko=note,
        ),
        request_id,
    )


@router.get(
    "/scans/{scan_run_id}/pages",
    response_model=ApiResponse[ScanPagesPayload],
    summary="지난 진단을 페이지 축으로 — 어느 페이지에 무엇이 걸렸나",
    description=(
        "저장된 판정을 페이지별로 뒤집어 돌려줍니다. 다시 수집하지 않습니다.\n\n"
        "명세 1.9.0 이후 실행에는 **페이지 점수**가 함께 옵니다(그 페이지의 URL 범위 "
        "검사만, 페이지 관문 곱셈, 표본 밖 성능은 감점 없이 별도 표기). 1.9.0 이전 "
        "실행은 판정 사실만 내보냅니다 — 그 판의 규칙에 없던 산수를 그 판의 이름으로 "
        "하지 않습니다.\n\n"
        "`site_checks` 는 페이지가 아니라 **사이트 전체**의 판정입니다. 화면에 실을 "
        "때는 반드시 `measured_at` 날짜와 함께 표기하십시오 — 날짜 없이 페이지 화면에 "
        "섞으면 '이 페이지의 문제' 로 잘못 읽힙니다."
    ),
)
def read_scan_pages(
    scan_run_id: uuid.UUID,
    principal: ScanReader,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
) -> ApiResponse[ScanPagesPayload]:
    breakdown = page_breakdown(db, principal=principal, scan_run_id=scan_run_id)
    if breakdown is None:
        raise HTTPException(status_code=404, detail="scan run not found")
    return ok(
        ScanPagesPayload(
            scan_run_id=breakdown.scan_run_id,
            measured_at=breakdown.measured_at,
            pages=[
                PageChecksSummary(
                    url=page.url,
                    failed=list(page.failed),
                    warned=list(page.warned),
                    passed_count=len(page.passed),
                    problem_count=page.problem_count,
                    score=None if page.score is None else page.score.score,
                    score_status=None if page.score is None else page.score.status,
                )
                for page in breakdown.pages
            ],
            site_checks=[
                SiteCheckSummary(
                    check_id=check.check_id, status=check.status, reason_ko=check.reason_ko
                )
                for check in breakdown.site_checks
            ],
            recorded_before_page_lists=breakdown.recorded_before_page_lists,
            notes_ko=list(breakdown.notes_ko),
        ),
        request_id,
    )


@router.get(
    "/scans/{scan_run_id}/pages/detail",
    response_model=ApiResponse[PageDetailPayload],
    summary="페이지 하나의 전체 판정 — 통과 목록까지",
    description=(
        "주소는 쿼리로 받습니다(경로에 넣으면 한글·쿼리스트링 주소가 부서집니다). "
        "이 페이지에서 잰 적 없는 검사는 응답에 나오지 않습니다 — '통과' 와 '안 쟀다' "
        "를 섞으면 페이지가 실제보다 건강해 보입니다."
    ),
)
def read_scan_page_detail(
    scan_run_id: uuid.UUID,
    principal: ScanReader,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
    url: Annotated[str, Query(min_length=1, description="살펴볼 페이지의 최종 URL입니다.")],
) -> ApiResponse[PageDetailPayload]:
    breakdown = page_breakdown(db, principal=principal, scan_run_id=scan_run_id)
    if breakdown is None:
        raise HTTPException(status_code=404, detail="scan run not found")
    page = next((p for p in breakdown.pages if p.url == url), None)
    if page is None:
        raise HTTPException(status_code=404, detail="page not found in this scan run")
    return ok(
        PageDetailPayload(
            url=page.url,
            failed=list(page.failed),
            warned=list(page.warned),
            passed=list(page.passed),
            score=_page_score_summary(page.score),
        ),
        request_id,
    )


def _page_score_summary(score: PageScore | None) -> PageScoreSummary | None:
    if score is None:
        return None
    return PageScoreSummary(
        spec_id=score.spec_id,
        spec_version=score.spec_version,
        status=score.status,
        score=score.score,
        reach=score.reach,
        quality=score.quality,
        stages=[
            PageStageSummary(
                category_id=stage.category_id,
                name_ko=stage.name_ko,
                weight=stage.weight,
                is_gate=stage.is_gate,
                score=stage.score,
            )
            for stage in score.stages
        ],
        losses=[
            PageLossSummary(
                check_id=loss.check_id,
                category_id=loss.category_id,
                status=loss.status,
                lost=loss.lost,
            )
            for loss in score.losses
        ],
        gate_unverified=list(score.gate_unverified),
        unmeasured=list(score.unmeasured),
        not_sampled=list(score.not_sampled),
        not_applicable=list(score.not_applicable),
        not_sampled_note_ko=score.not_sampled_note_ko,
    )


def _assert_site_exists(db: Session, *, principal: Principal, site_id: uuid.UUID) -> None:
    """다른 조직의 사이트는 **없는 것으로** 답한다.

    403 은 "그 사이트가 존재한다" 는 사실을 확인해 주는 답이 된다. 조직 경계 밖에서는
    존재 여부 자체가 알려줄 것이 아니다.
    """
    from veo.seo.history import site_exists

    if not site_exists(db, principal=principal, site_id=site_id):
        raise HTTPException(status_code=404, detail="site not found")


def _registered_brand_name(
    db: Session, principal: Principal, *, site_id: uuid.UUID | None
) -> str | None:
    """이 사이트를 가진 프로젝트에 **등록된** 우리 브랜드 이름.

    예시 코드의 상호 자리를 채우는 데 쓴다. 사람이 직접 등록한 값만 쓴다 — 도메인이나
    페이지 제목에서 상호를 뽑아내면 그럴듯하게 틀린 이름이 나오고, 담당자는 그것을
    그대로 사이트에 붙여넣는다. 자리표시자가 남는 편이 낫다.

    사이트를 지정하지 않은 간편 진단, 브랜드를 아직 등록하지 않은 프로젝트, 조회 중
    생기는 어떤 문제든 ``None`` 이다 — 이름을 못 채우는 것이 진단을 실패시킬 이유는 없다.
    """
    if site_id is None:
        return None
    site = db.execute(tenant_select(Site, principal).where(Site.id == site_id)).scalar_one_or_none()
    if site is None:
        return None
    brands = list_brands(db, principal, site.project_id)
    if brands.ours is None:
        return None
    return brands.ours.row.display_name


# --------------------------------------------------------------------------- #
# Result to payload
# --------------------------------------------------------------------------- #


def _scan_payload(result: SeoScanResult, *, brand_name: str | None = None) -> ScanPayload:
    """판정을 응답 본문으로.

    ``brand_name`` 은 **등록된 업체명이 있을 때만** 넘어온다. 예시 코드의 상호 자리를
    실제 이름으로 채워, 담당자가 그대로 복사해 붙여넣을 수 있게 한다. 없으면 자리표시자가
    남는다 — 도메인에서 상호를 추측해 넣으면 틀린 이름을 확신 있게 붙여넣게 만든다.
    """
    spec = load_seo_spec()
    titles = {
        check.id: (check.title_ko, str(check.severity), check.remediation_owner)
        for category in spec.categories
        for check in category.checks
    }
    return ScanPayload(
        summary_ko=result.summary_ko,
        improvements=[
            ImprovementSummary(
                check_id=entry.check_id,
                category_id=entry.category_id,
                title_ko=titles.get(entry.check_id, ("", "MINOR", "DEVELOPER"))[0],
                gain_points=entry.gain_points,
                blocked_by_cap=entry.blocked_by_cap,
                severity=titles.get(entry.check_id, ("", "MINOR", "DEVELOPER"))[1],
                remediation_owner=titles.get(entry.check_id, ("", "MINOR", "DEVELOPER"))[2],
            )
            for entry in rank_improvements(result.score)
        ],
        score=_score_summary(result.score),
        outcomes=[
            OutcomeSummary(
                check_id=item.check_id,
                title_ko=spec.check(item.check_id).title_ko,
                category_id=spec.category_of(item.check_id).id,
                category_name_ko=spec.category_of(item.check_id).name_ko,
                severity=str(spec.check(item.check_id).severity),
                remediation_owner=spec.check(item.check_id).remediation_owner,
                availability=spec.check(item.check_id).availability,
                reference_ko=spec.check(item.check_id).reference_ko,
                status=str(item.status),
                confidence=item.confidence,
                confidence_level=item.confidence_level,
                affected_weight=item.affected_weight,
                evaluated_weight=item.evaluated_weight,
                evidence_ids=list(item.evidence_ids),
                note=item.note,
                observed=item.observed_value,
            )
            for item in result.score.outcomes
        ],
        unknown_checks=[
            UnknownCheckSummary(
                check_id=item.check_id,
                category_id=item.category_id,
                title_ko=item.title_ko,
                reason_ko=item.reason_ko,
            )
            for item in result.unknown_checks
        ],
        issues=[
            IssueSummary(
                check_id=item.check_id,
                title_ko=item.title_ko,
                summary_ko=item.summary_ko,
                affected_urls=list(item.affected_urls),
                evidence_ids=list(item.evidence_ids),
                remediation_ko=item.remediation_ko,
                remediation_owner=item.remediation_owner,
                business_impact_ko=item.business_impact_ko,
                # 수집기가 현장 코드를 만들었으면 그것(실측값 포함)이 우선,
                # 없으면 등록부의 표준 예시 — 무료 화면과 같은 폴백이다. 콘솔이
                # 무료 화면보다 정보가 적던 반쪽 연결의 수선(2026-08-03 감사).
                fix_example=with_brand(
                    item.fix_example or code_example_for(item.check_id), brand_name
                ),
                reverification_note_ko=item.reverification_note_ko,
            )
            for item in result.issues
        ],
        evidence=[
            EvidenceSummary(
                evidence_id=record.evidence_id,
                kind=record.kind,
                url=record.url,
                collected_at=record.collected_at.isoformat(),
                content_hash=record.content_hash,
                excerpt=record.excerpt,
            )
            for record in result.evidence
        ],
        notes_ko=list(result.notes_ko),
    )


def _score_summary(result: ScoreResult) -> ScoreSummary:
    return ScoreSummary(
        spec_id=result.spec_id,
        spec_version=result.spec_version,
        spec_checksum=result.spec_checksum,
        status=result.status,
        score=result.overall_score,
        score_before_caps=result.overall_score_before_caps,
        band_id=result.band_id,
        coverage=result.coverage,
        confidence=result.confidence,
        reach=result.reach,
        gate_unverified=list(result.gate_unverified),
        is_rank_prediction=False,
        categories=[
            CategorySummary(
                category_id=category.category_id,
                name_ko=category.name_ko,
                weight=category.weight,
                status=category.status,
                score=category.score,
                coverage=category.coverage,
                confidence=category.confidence,
                not_applicable_check_ids=category.not_applicable_check_ids,
                unknown_check_ids=category.unknown_check_ids,
                failing_check_ids=category.failing_check_ids,
            )
            for category in result.categories
        ],
        applied_caps=[
            CapSummary(
                cap_id=cap.cap_id,
                max_overall_score=cap.max_overall_score,
                reason_ko=cap.reason_ko,
                release_condition_ko=cap.release_condition_ko,
                triggered_by=list(cap.triggered_by),
            )
            for cap in result.applied_caps
        ],
        calculation_trace=result.trace,
    )


__all__ = ["router"]
