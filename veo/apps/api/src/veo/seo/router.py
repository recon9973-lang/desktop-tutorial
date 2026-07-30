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
from veo.common.security.fetcher import FetchedDocument, FetchHop
from veo.contracts.enums import ProviderState
from veo.contracts.envelope import ApiResponse
from veo.core.settings import get_provider_credentials
from veo.db.session import get_db
from veo.organizations.http import guard
from veo.scoring import ScoreResult, ScoringSpec
from veo.scoring.improvements import rank_improvements
from veo.seo.collectors import CATEGORY_COLLECTORS, PROVIDER_BACKED_CHECKS
from veo.seo.crawl import ConsoleCrawler, CrawlOutcome, CrawlRefusal
from veo.seo.history import (
    read_scan_history,
    read_scan_report,
    save_scan_run,
)
from veo.seo.importance import classify_urls
from veo.seo.schemas import (
    CapSummary,
    CategorySummary,
    CheckCatalogueEntry,
    CheckCataloguePayload,
    EvidenceSummary,
    ImprovementSummary,
    IssueSummary,
    OutcomeSummary,
    PagePayload,
    ScanHistoryEntry,
    ScanHistoryPayload,
    ScanPayload,
    ScanRequest,
    ScoreSummary,
    SiteScanRequest,
    UnknownCheckSummary,
)
from veo.seo.service import SeoScanResult, load_seo_spec, run_seo_scan

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

    context = _context_from_crawl(
        target_url=payload.target_url,
        spec=spec,
        outcome=outcome,
        locale=payload.locale,
    )
    result = run_seo_scan(context)
    report = _scan_payload(result)

    if payload.site_id is not None:
        # 보여준 것을 그대로 남긴다. 조치 문구는 수집기가 발견한 값을 넣어 만들어 내므로
        # 명세로부터 되살릴 수 없다 — 스냅샷이 없으면 다시 열었을 때 문장이 달라진다.
        save_scan_run(
            db,
            principal=principal,
            site_id=payload.site_id,
            result=result,
            urls_attempted=outcome.attempted,
            urls_collected=len(outcome.documents),
            report_snapshot=report.model_dump(mode="json"),
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


def _assert_site_exists(db: Session, *, principal: Principal, site_id: uuid.UUID) -> None:
    """다른 조직의 사이트는 **없는 것으로** 답한다.

    403 은 "그 사이트가 존재한다" 는 사실을 확인해 주는 답이 된다. 조직 경계 밖에서는
    존재 여부 자체가 알려줄 것이 아니다.
    """
    from veo.seo.history import site_exists

    if not site_exists(db, principal=principal, site_id=site_id):
        raise HTTPException(status_code=404, detail="site not found")


def _context_from_crawl(
    *,
    target_url: str,
    spec: ScoringSpec,
    outcome: CrawlOutcome,
    locale: str,
) -> CollectionContext:
    """수집 결과를 채점기가 읽는 형태로 옮긴다.

    provider 상태는 설정에서 그대로 가져온다. 자격증명이 없는 provider 는 DISABLED 로
    들어가고, 그 항목은 UNKNOWN 이 되어 측정 범위를 낮춘다 — 감점되지도, 지어내지도
    않는다. 이 값을 ENABLED 로 위장하면 없는 데이터를 있는 것처럼 만들게 된다.

    사이트맵도 같은 이유로 여기서 넘긴다. 예전에는 이 자리에 빈 값이 들어가 있어서,
    사이트맵을 제대로 갖춘 사이트조차 사이트맵 두 항목이 **언제나** 측정 불가로
    나왔다. 그 배점은 분모에 남으므로 모든 고객의 점수가 우리가 수집을 안 만든 만큼
    내려가고 있었다 — 대상 사이트의 문제로 보이는 형태로.
    """
    documents = outcome.documents
    by_url = {document.final_url: document for document in documents}
    primary = documents[0] if documents else None
    return CollectionContext(
        target_url=target_url,
        spec=spec,
        documents=by_url,
        primary_document=primary,
        robots_txt=outcome.robots_txt,
        sitemap_documents=dict(outcome.sitemaps),
        # 렌더링 후 DOM 은 아직 수집하지 않는다. 비워 두면 렌더 비교 항목이 UNKNOWN 이
        # 되고, 원본 HTML 과 같다고 **가정하지 않는다**.
        rendered_dom={},
        provider_states=dict(get_provider_credentials().states()),
        provider_payloads={},
        # 예전에는 수집한 **모든** 페이지가 `CONVERSION_OR_HOME`(3.0) 이었다. 측정 범위는
        # 중요도로 가중되므로, 그 상태에서는 태그 페이지 한 장의 결함이 홈페이지 결함과
        # 같은 무게였다 — 가중치라는 개념이 사실상 없었다.
        url_importance=dict(
            classify_urls(
                (document.final_url for document in documents), entry_url=target_url
            )
        ),
        crawl_is_exhaustive=outcome.discovery_exhausted,
        locale=locale,
        collected_at=datetime.now(UTC),
    )


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
                fix_example=item.fix_example,
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
