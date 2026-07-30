"""보고서를 HTTP 응답 모양으로 옮긴다.

라우터가 아니라 여기에 두는 이유는 :mod:`veo.observations.jobs` 와 같다 — 라우터 모듈은
`veo.api` 를 거쳐 자기 자신으로 돌아오는 순환 고리 위에 있어서, 테스트가 응답 모양을
직접 확인하려고 열면 깨진다. 응답 번역은 그 고리 밖에 있어야 시험할 수 있다.

여기서 반드시 지키는 것: **점수 밖 영역인지 아닌지를 응답에 담는다.** 그 사실은
채점 결과가 아니라 **명세**에 있고, 붙여 주지 않으면 화면은 "참고 항목" 과 "우리가 못
잰 항목" 을 구분할 방법이 없다. 둘 다 점수가 비어 있기 때문이다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from veo.collect.contract import EvidenceRecord, IssueDraft
from veo.geo.schemas import (
    GeoCategoryPayload,
    GeoCheckPayload,
    GeoEvidencePayload,
    GeoExposureBlock,
    GeoGatePayload,
    GeoIssuePayload,
    GeoLookupPayload,
    GeoReadinessBlock,
    GeoReadinessPayload,
)
from veo.geo.service import GeoReadinessReport

#: 준비도 응답마다 그대로 되풀이한다. 준비도는 AI 노출이 아니며, 그렇게 적지 않은
#: 보고서는 ADR 0003 이 금지한 혼동을 부른다.
SCOPE_NOTICE_KO = (
    "이 점수는 AI 답변 엔진이 페이지에 접근·추출·검증할 수 있는 구조적 준비도입니다. "
    "실제 AI 답변에서의 노출 결과는 별도의 관측 엔진이 따로 보고합니다."
)


def payload_from(
    target_url: str,
    report: GeoReadinessReport,
    *,
    extra_notes_ko: Sequence[str] = (),
    lookup: Mapping[str, Any] | None = None,
) -> GeoReadinessPayload:
    result = report.score
    band = (
        report.spec.band_for(result.overall_score) if result.overall_score is not None else None
    )
    # 점수 밖 영역인지는 **명세**가 정한다. 결과 행에는 그 사실이 없다 — 여기서 붙이지
    # 않으면 화면은 "참고 항목" 과 "못 잰 항목" 을 구분할 방법이 없다.
    _declared = {category.id: category for category in report.spec.categories}
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
                contributes_to_score=_declared[category.category_id].contributes_to_score,
                outside_score_reason_ko=(
                    None
                    if _declared[category.category_id].contributes_to_score
                    else _declared[category.category_id].description_ko
                ),
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
        # 참고 조회를 왜 못 했는지 같은, 보고서 밖에서 온 안내도 여기에 실린다.
        # 조용히 빼면 '외부 출처가 없다' 로 읽히는데 그것은 사이트 탓이 아니다.
        notes_ko=[*report.notes_ko, *extra_notes_ko],
        lookup=None if lookup is None else GeoLookupPayload.model_validate(lookup),
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


__all__ = ["SCOPE_NOTICE_KO", "payload_from"]
