"""``/seo`` — the SEO readiness check catalogue and the scan endpoint.

This router is **not mounted here**. ``veo.api.app`` belongs to the integrator; see
``INTEGRATION_REQUEST.md``. Everything below is a plain :class:`~fastapi.APIRouter` that
can be included under the API prefix without further wiring.

Permissions follow the platform matrix exactly: ``scan:read`` to read the catalogue,
``scan:run`` to run a scan. Both are declared as route dependencies so the check runs
before the request body is parsed.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal
from veo.collect.contract import CollectionContext
from veo.collect.from_crawl import context_from_crawl
from veo.common.security.fetcher import FetchedDocument, FetchHop
from veo.contracts.enums import ProviderState
from veo.contracts.envelope import ApiResponse
from veo.db.session import get_db
from veo.organizations.http import guard
from veo.scoring import ScoreResult, ScoringSpec
from veo.scoring.improvements import rank_improvements
from veo.scoring.page import PageScore
from veo.seo.collectors import CATEGORY_COLLECTORS, PROVIDER_BACKED_CHECKS
from veo.seo.crawl import ConsoleCrawler, CrawlOutcome, CrawlRefusal
from veo.seo.fix_examples import code_example_for
from veo.seo.history import (
    read_scan_history,
    read_scan_report,
    save_scan_run,
)
from veo.seo.measure_performance import with_performance
from veo.seo.pages import page_breakdown
from veo.seo.regression import maybe_alert_score_drop
from veo.seo.schemas import (
    CapSummary,
    CategorySummary,
    CheckCatalogueEntry,
    CheckCataloguePayload,
    EvidenceSummary,
    ImprovementSummary,
    IssueSummary,
    OutcomeSummary,
    PageChecksSummary,
    PageDetailPayload,
    PageLossSummary,
    PagePayload,
    PageScoreSummary,
    PageStageSummary,
    ScanHistoryEntry,
    ScanHistoryPayload,
    ScanPagesPayload,
    ScanPayload,
    ScanRequest,
    ScoreSummary,
    SiteCheckSummary,
    SiteScanRequest,
    UnknownCheckSummary,
)
from veo.seo.service import SeoScanResult, load_seo_spec, run_seo_scan
from veo.usage import record_pagespeed_calls

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
    "/scan",
    response_model=ApiResponse[ScanPayload],
    summary="수집된 크롤 자료로 SEO 준비도 채점",
    description=(
        "이미 수집이 끝난 자료를 받아 47개 항목을 판정하고 발행된 명세로 채점합니다. "
        "이 엔드포인트는 외부에 요청을 보내지 않습니다. 수집은 SSRF 방어와 크기 제한이 "
        "들어 있는 크롤러가 한 곳에서 담당합니다. `rendered_dom`을 비워 두면 렌더링 비교 "
        "항목은 UNKNOWN이 되며, 원본 HTML과 일치한다고 가정하지 않습니다."
    ),
)
def run_scan(
    payload: ScanRequest, principal: ScanRunner, request_id: RequestId
) -> ApiResponse[ScanPayload]:
    spec = load_seo_spec()
    context = _context_from(payload, spec)
    result = run_seo_scan(context)
    return ok(
        _scan_payload(result),
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
    # 사이트를 지정했다면 **가져오기 전에** 존재를 확인한다. 없는 사이트를 위해 남의
    # 서버에 요청을 보내고 나서 404 를 돌려주는 것은 순서가 틀렸다.
    if payload.site_id is not None:
        _assert_site_exists(db, principal=principal, site_id=payload.site_id)
    # 대표 주소가 목록의 맨 앞에 오도록 맞춘다. 중복은 제거하되 순서는 유지한다 —
    # 첫 문서가 primary 가 되고, 그것이 canonical·robots 판정의 기준점이다.
    requested = [payload.target_url, *payload.urls]
    targets = list(dict.fromkeys(url for url in requested if url.strip()))

    crawler = ConsoleCrawler()
    try:
        if payload.discover:
            outcome = crawler.crawl(
                payload.target_url, extra_urls=targets[1:], max_urls=payload.max_urls
            )
        else:
            documents, robots_txt = crawler.collect(targets)
            outcome = CrawlOutcome(documents=documents, robots_txt=robots_txt)
    except CrawlRefusal as refusal:
        raise HTTPException(
            status_code=refusal.status_code, detail=refusal.error.model_dump(mode="json")
        ) from refusal

    context = context_from_crawl(
        target_url=payload.target_url,
        spec=spec,
        outcome=outcome,
        locale=payload.locale,
    )
    # 성능은 크롤로 알 수 없다. 구글에 따로 물어야 하고, 그래서 여기서 한 번 더 나간다.
    # 자격증명이 없으면 문맥을 손대지 않고 그대로 돌려주므로, 키가 없는 배포에서는
    # 이 줄이 아무 일도 하지 않는다 — 소켓도 열리지 않는다.
    context, performance = with_performance(context)
    result = run_seo_scan(context)
    report = _scan_payload(result)

    # 유료 한도를 쓴 것은 사실이므로 사이트를 지정하지 않은 진단에서도 남긴다.
    # PageSpeed 는 하루 25,000회이고 진단 한 번에 최대 5회가 나간다. 기록이 없으면
    # 어느 날 갑자기 모든 고객의 성능이 측정 불가가 되고 이유를 알 수 없다.
    if performance is not None and performance.calls:
        record_pagespeed_calls(
            db,
            performance.calls,
            organization_id=principal.organization_id,
            request_id=str(request_id),
        )

    if payload.site_id is not None:
        # 보여준 것을 그대로 남긴다. 조치 문구는 수집기가 발견한 값을 넣어 만들어 내므로
        # 명세로부터 되살릴 수 없다 — 스냅샷이 없으면 다시 열었을 때 문장이 달라진다.
        saved = save_scan_run(
            db,
            principal=principal,
            site_id=payload.site_id,
            result=result,
            # 맥락째 넘긴다. 어떤 조건에서 쟀는지는 여기서만 알 수 있고, 저장하는 쪽에서
            # 추측하면 상수가 사실 자리에 앉는다.
            context=context,
            urls_attempted=outcome.attempted,
            urls_collected=len(outcome.documents),
            report_snapshot=report.model_dump(mode="json"),
        )
        # 저장이 끝난 뒤에만 비교한다 — 이 진단이 '직전' 과 비교 가능한 최신이
        # 되는 시점이 지금이다. 실패해도 저장·응답은 그대로다.
        maybe_alert_score_drop(
            db,
            principal=principal,
            site_id=payload.site_id,
            origin=payload.target_url,
            scan_run_id=saved.scan_run_id,
        )

    return ok(
        report,
        request_id,
        spec_id=spec.spec_id,
        spec_version=spec.version,
        spec_checksum=spec.checksum,
    )


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
) -> ApiResponse[ScanHistoryPayload]:
    _assert_site_exists(db, principal=principal, site_id=site_id)
    entries = read_scan_history(db, principal=principal, site_id=site_id, limit=limit)
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
    report = read_scan_report(db, principal=principal, scan_run_id=scan_run_id)
    if report is None:
        raise HTTPException(status_code=404, detail="scan run not found")
    return ok(ScanPayload.model_validate(report), request_id)


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


# --------------------------------------------------------------------------- #
# Request to context
# --------------------------------------------------------------------------- #


def _context_from(payload: ScanRequest, spec: ScoringSpec) -> CollectionContext:
    collected_at = datetime.now(UTC)

    documents = {page.url: _document(page, collected_at) for page in payload.pages}
    rendered = {
        page.url: page.rendered_dom for page in payload.pages if page.rendered_dom is not None
    }
    importance = {page.url: page.importance for page in payload.pages}
    primary = payload.primary_url or payload.target_url

    states = {
        name: ProviderState(value)
        for name, value in payload.provider_states.items()
        if value in set(ProviderState)
    }

    return CollectionContext(
        target_url=payload.target_url,
        spec=spec,
        documents=documents,
        primary_document=documents.get(primary),
        robots_txt=payload.robots_txt,
        sitemap_documents=dict(payload.sitemaps),
        rendered_dom=rendered,
        provider_states=states,
        provider_payloads=dict(payload.provider_payloads),
        url_importance=importance,
        locale=payload.locale,
        collected_at=collected_at,
    )


def _document(page: PagePayload, collected_at: datetime) -> FetchedDocument:
    body = page.html.encode("utf-8")
    hops = (
        tuple(
            FetchHop(
                url=hop.url,
                status=hop.status,
                resolved_ip="",
                location=hop.location,
                elapsed_ms=0,
            )
            for hop in page.hops
        )
        if page.hops
        else (
            FetchHop(
                url=page.url, status=page.status, resolved_ip="", location=None, elapsed_ms=0
            ),
        )
    )
    return FetchedDocument(
        requested_url=hops[0].url,
        final_url=page.url,
        status=page.status,
        headers={key.lower(): value for key, value in page.headers.items()},
        body=body,
        content_hash=hashlib.sha256(body).hexdigest(),
        content_type="text/html",
        charset="utf-8",
        hops=hops,
        resolved_ips=(),
        fetched_at=collected_at,
        elapsed_ms=0,
        tls_expires_at=page.tls_expires_at,
    )


# --------------------------------------------------------------------------- #
# Result to payload
# --------------------------------------------------------------------------- #


def _scan_payload(result: SeoScanResult) -> ScanPayload:
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
                fix_example=item.fix_example or code_example_for(item.check_id),
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
