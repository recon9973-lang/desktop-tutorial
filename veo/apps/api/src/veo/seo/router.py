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
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal
from veo.collect.contract import CollectionContext
from veo.common.security.fetcher import FetchedDocument, FetchHop
from veo.contracts.enums import ProviderState
from veo.contracts.envelope import ApiResponse
from veo.organizations.http import guard
from veo.scoring import ScoreResult, ScoringSpec
from veo.seo.collectors import CATEGORY_COLLECTORS, PROVIDER_BACKED_CHECKS
from veo.seo.schemas import (
    CapSummary,
    CategorySummary,
    CheckCatalogueEntry,
    CheckCataloguePayload,
    EvidenceSummary,
    IssueSummary,
    OutcomeSummary,
    PagePayload,
    ScanPayload,
    ScanRequest,
    ScoreSummary,
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
    )


# --------------------------------------------------------------------------- #
# Result to payload
# --------------------------------------------------------------------------- #


def _scan_payload(result: SeoScanResult) -> ScanPayload:
    return ScanPayload(
        summary_ko=result.summary_ko,
        score=_score_summary(result.score),
        outcomes=[
            OutcomeSummary(
                check_id=item.check_id,
                status=str(item.status),
                confidence=item.confidence,
                confidence_level=item.confidence_level,
                affected_weight=item.affected_weight,
                evaluated_weight=item.evaluated_weight,
                evidence_ids=list(item.evidence_ids),
                note=item.note,
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
