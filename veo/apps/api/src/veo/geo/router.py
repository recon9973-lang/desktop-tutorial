"""``/geo`` — GEO readiness endpoints. **Not mounted.**

``veo.api.app`` belongs to the integration maintainer, so this router is defined and
tested here and included there when the integrator is ready. See ``INTEGRATION_REQUEST.md``.

The analysis endpoint takes material that has already been fetched rather than a URL to
fetch. Crawling belongs to the collection pipeline, which owns the SSRF guard and the
fetch budget; a diagnostic endpoint that dials arbitrary hosts on request would be a
second, unguarded way out of the network.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal
from veo.collect.contract import CollectionContext, EvidenceRecord, IssueDraft
from veo.collect.from_crawl import context_from_crawl
from veo.common.security.fetcher import FetchedDocument
from veo.contracts.enums import ProviderState
from veo.contracts.envelope import ApiResponse
from veo.geo.schemas import (
    GeoAnalysisRequest,
    GeoCategoryPayload,
    GeoCheckPayload,
    GeoDocumentInput,
    GeoEvidencePayload,
    GeoExposureBlock,
    GeoGatePayload,
    GeoIssuePayload,
    GeoReadinessBlock,
    GeoReadinessPayload,
    GeoScanRequest,
    GeoSpecCategoryPayload,
    GeoSpecPayload,
)
from veo.geo.service import GEO_SPEC_ID, GeoReadinessReport, run_geo_readiness
from veo.organizations.http import guard
from veo.scoring import ScoringSpec, latest_published
from veo.seo.crawl import ConsoleCrawler, CrawlOutcome, CrawlRefusal

router = APIRouter(prefix="/geo", tags=["geo"])

Reader = Annotated[Principal, Depends(guard(Permission.SCAN_READ))]
Runner = Annotated[Principal, Depends(guard(Permission.SCAN_RUN))]

#: Repeated verbatim on every readiness response. Readiness is not AI exposure, and a
#: report that does not say so invites exactly the conflation ADR 0003 forbids.
SCOPE_NOTICE_KO = (
    "이 점수는 AI 답변 엔진이 페이지에 접근·추출·검증할 수 있는 구조적 준비도입니다. "
    "실제 AI 답변에서의 노출 결과는 별도의 관측 엔진이 따로 보고합니다."
)


@router.get(
    "/readiness/spec",
    response_model=ApiResponse[GeoSpecPayload],
    summary="GEO 준비도 채점 명세",
    description=(
        "현재 발행된 `veo.geo.readiness` 명세의 영역·검사·게이트 구성을 반환합니다. "
        "점수의 근거가 되는 배점은 명세 파일에만 있으며 서비스 코드에는 없습니다."
    ),
)
def read_spec(principal: Reader, request_id: RequestId) -> ApiResponse[GeoSpecPayload]:
    spec = latest_published(GEO_SPEC_ID)
    payload = GeoSpecPayload(
        spec_id=spec.spec_id,
        version=spec.version,
        checksum=spec.checksum,
        status=str(spec.status),
        score_meaning_ko=spec.score_meaning.ko,
        check_count=len(spec.check_ids),
        categories=[
            GeoSpecCategoryPayload(
                id=category.id,
                name_ko=category.name_ko,
                weight=category.weight,
                check_ids=[check.id for check in category.checks],
            )
            for category in spec.categories
        ],
        gate_status_codes=sorted({gate.status_code for gate in spec.gates}),
    )
    return ok(
        payload,
        request_id,
        spec_id=spec.spec_id,
        spec_version=spec.version,
        spec_checksum=spec.checksum,
    )


@router.post(
    "/readiness/analyses",
    response_model=ApiResponse[GeoReadinessPayload],
    summary="GEO 준비도 진단",
    description=(
        "이미 수집된 문서를 받아 GEO 준비도를 산출합니다. 응답은 준비도 점수와 노출 차단 "
        "상태를 **분리된 두 블록**으로 돌려줍니다. 95점이면서 동시에 노출 차단일 수 있고, "
        "화면은 그 두 가지를 함께 보여줄 수 있어야 합니다."
    ),
)
def run_analysis(
    payload: GeoAnalysisRequest,
    principal: Runner,
    request_id: RequestId,
) -> ApiResponse[GeoReadinessPayload]:
    spec = latest_published(GEO_SPEC_ID)
    report = run_geo_readiness(_context_from(payload, spec), spec=spec)
    return ok(
        _payload_from(payload.target_url, report),
        request_id,
        spec_id=report.score.spec_id,
        spec_version=report.score.spec_version,
        spec_checksum=report.score.spec_checksum,
    )



@router.post(
    "/readiness/scans",
    response_model=ApiResponse[GeoReadinessPayload],
    summary="주소만으로 GEO 준비도 진단",
    description=(
        "주소를 주면 VEO 가 직접 가져와 채점합니다. `/readiness/analyses` 는 이미 수집된 "
        "문서를 받는 계약이고, 이쪽은 사람이 콘솔에서 주소 하나를 넣는 경우를 위한 "
        "것입니다.\n\n"
        "**SEO 진단과 같은 수집 경로를 씁니다.** 같은 가드, 같은 예산, 같은 중요도 분류를 "
        "지납니다 — 두 진단이 서로 다른 규칙으로 사이트를 돌면 두 결과를 나란히 놓을 수 "
        "없습니다.\n\n"
        "그렇더라도 **SEO 점수와 GEO 점수는 합치지 않습니다.** 재는 재료가 같다는 것과 "
        "뜻이 같다는 것은 다른 이야기입니다."
    ),
)
def scan_readiness(
    payload: GeoScanRequest,
    principal: Runner,
    request_id: RequestId,
) -> ApiResponse[GeoReadinessPayload]:
    spec = latest_published(GEO_SPEC_ID)
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
    report = run_geo_readiness(context, spec=spec)
    return ok(
        _payload_from(payload.target_url, report),
        request_id,
        spec_id=report.score.spec_id,
        spec_version=report.score.spec_version,
        spec_checksum=report.score.spec_checksum,
    )


# --------------------------------------------------------------------------- #
# Translation
# --------------------------------------------------------------------------- #


def _context_from(payload: GeoAnalysisRequest, spec: ScoringSpec) -> CollectionContext:
    collected_at = payload.collected_at or datetime.now(UTC)
    documents = {
        item.url: _document_from(item, collected_at) for item in payload.documents
    }
    primary = next(
        (documents[item.url] for item in payload.documents if item.primary),
        documents.get(payload.target_url) or next(iter(documents.values())),
    )
    return CollectionContext(
        target_url=payload.target_url,
        spec=spec,
        documents=documents,
        primary_document=primary,
        robots_txt=payload.robots_txt,
        sitemap_documents=dict(payload.sitemap_documents),
        rendered_dom=dict(payload.rendered_dom),
        provider_states={
            name: ProviderState(value) for name, value in payload.provider_states.items()
        },
        provider_payloads=dict(payload.provider_payloads),
        url_importance=dict(payload.url_importance),
        collected_at=collected_at,
    )


def _document_from(item: GeoDocumentInput, collected_at: datetime) -> FetchedDocument:
    body = item.html.encode("utf-8")
    headers = {key.lower(): value for key, value in item.headers.items()}
    return FetchedDocument(
        requested_url=item.url,
        final_url=item.url,
        status=item.status,
        headers=headers,
        body=body,
        content_hash=hashlib.sha256(body).hexdigest(),
        content_type=headers.get("content-type", "text/html").split(";", 1)[0].strip(),
        charset="utf-8",
        hops=(),
        resolved_ips=(),
        fetched_at=collected_at,
        elapsed_ms=0,
    )


def _payload_from(target_url: str, report: GeoReadinessReport) -> GeoReadinessPayload:
    result = report.score
    band = (
        report.spec.band_for(result.overall_score) if result.overall_score is not None else None
    )
    titles = {
        check.id: check.title_ko
        for category in report.spec.categories
        for check in category.checks
    }

    readiness = GeoReadinessBlock(
        spec_id=result.spec_id,
        spec_version=result.spec_version,
        spec_checksum=result.spec_checksum,
        status=result.status,
        score=result.overall_score,
        band_id=result.band_id,
        band_label_ko=band.label_ko if band else None,
        coverage=result.coverage,
        confidence=result.confidence,
        categories=[
            GeoCategoryPayload(
                category_id=category.category_id,
                name_ko=category.name_ko,
                weight=category.weight,
                status=category.status,
                score=category.score,
                coverage=category.coverage,
                confidence=category.confidence,
                failing_check_ids=list(category.failing_check_ids),
                unknown_check_ids=list(category.unknown_check_ids),
                not_applicable_check_ids=list(category.not_applicable_check_ids),
            )
            for category in result.categories
        ],
    )

    exposure = GeoExposureBlock(
        blocked=report.is_exposure_blocked,
        status_codes=list(report.gate_status_codes),
        gates=[
            GeoGatePayload(
                gate_id=gate.gate_id,
                status_code=gate.status_code,
                label_ko=gate.label_ko,
                description_ko=gate.description_ko,
                triggered_by=list(gate.triggered_by),
            )
            for gate in report.gates
        ],
    )

    return GeoReadinessPayload(
        target_url=target_url,
        readiness=readiness,
        exposure=exposure,
        summary_ko=report.summary_ko(),
        scope_notice_ko=SCOPE_NOTICE_KO,
        checks=[
            GeoCheckPayload(
                check_id=outcome.check_id,
                title_ko=titles.get(outcome.check_id, outcome.check_id),
                status=str(outcome.status),
                confidence_level=outcome.confidence_level,
                note_ko=outcome.note,
                evidence_ids=list(outcome.evidence_ids),
            )
            for outcome in result.outcomes
        ],
        issues=[_issue_payload(issue) for issue in report.issues],
        evidence=[_evidence_payload(record) for record in report.evidence],
        notes_ko=list(report.notes_ko),
    )


def _issue_payload(issue: IssueDraft) -> GeoIssuePayload:
    return GeoIssuePayload(
        check_id=issue.check_id,
        title_ko=issue.title_ko,
        summary_ko=issue.summary_ko,
        remediation_ko=issue.remediation_ko,
        remediation_owner=issue.remediation_owner,
        business_impact_ko=issue.business_impact_ko,
        affected_urls=list(issue.affected_urls),
        evidence_ids=list(issue.evidence_ids),
        fix_example=issue.fix_example,
        reverification_note_ko=issue.reverification_note_ko,
    )


def _evidence_payload(record: EvidenceRecord) -> GeoEvidencePayload:
    return GeoEvidencePayload(
        evidence_id=record.evidence_id,
        kind=record.kind,
        url=record.url,
        content_hash=record.content_hash,
        collected_at=record.collected_at,
        excerpt=record.excerpt[:400],
    )


__all__ = ["SCOPE_NOTICE_KO", "router"]
