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
from veo.geo.fix_examples import code_example_for
from veo.geo.schemas import (
    GeoCategoryPayload,
    GeoCheckPayload,
    GeoEvidencePayload,
    GeoExposureBlock,
    GeoGatePayload,
    GeoImprovementPayload,
    GeoIssuePayload,
    GeoLookupPayload,
    GeoReadinessBlock,
    GeoReadinessPayload,
)
from veo.geo.service import GeoReadinessReport
from veo.scoring.improvements import rank_improvements
from veo.seo.fix_examples import with_brand

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
    brand_name: str | None = None,
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
    # 영역·심각도·담당은 결과 행이 아니라 **명세**가 정한다. 화면이 항목을 영역별로
    # 묶고 무게를 세우려면 이 셋이 함께 가야 한다(SEO 응답과 같은 이름).
    declared_by_check = {
        check.id: (category, check)
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
        checks=[_check_payload(outcome, declared_by_check) for outcome in result.outcomes],
        # 순위 산식은 명세와 무관한 일반 계산이고, 이 패키지는 이미 채점기(evaluate)를
        # 불러 점수를 받는다 — 그 결과를 옮길 뿐 여기서 무게를 정하지 않는다.
        improvements=[
            GeoImprovementPayload(
                check_id=item.check_id,
                category_id=item.category_id,
                title_ko=titles.get(item.check_id, item.check_id),
                gain_points=item.gain_points,
                blocked_by_cap=item.blocked_by_cap,
            )
            for item in rank_improvements(result)
        ],
        issues=[_issue_payload(issue, brand_name) for issue in report.issues],
        evidence=[_evidence_payload(record) for record in report.evidence],
        # 참고 조회를 왜 못 했는지 같은, 보고서 밖에서 온 안내도 여기에 실린다.
        # 조용히 빼면 '외부 출처가 없다' 로 읽히는데 그것은 사이트 탓이 아니다.
        notes_ko=[*report.notes_ko, *extra_notes_ko],
        lookup=None if lookup is None else GeoLookupPayload.model_validate(lookup),
    )


def _issue_payload(issue: IssueDraft, brand_name: str | None = None) -> GeoIssuePayload:
    return GeoIssuePayload(
        check_id=issue.check_id,
        title_ko=issue.title_ko,
        summary_ko=issue.summary_ko,
        remediation_ko=issue.remediation_ko,
        remediation_owner=issue.remediation_owner,
        business_impact_ko=issue.business_impact_ko,
        affected_urls=list(issue.affected_urls),
        evidence_ids=list(issue.evidence_ids),
        # 수집기가 현장 코드를 만들었으면 그것(실측값 포함)이 우선, 없으면 등록부의
        # 표준 예시 — SEO 쪽과 같은 폴백이다(`seo/router.py`). 실측 2026-08-07:
        # GEO 는 37개 검사 중 하나만 예시가 있었고, SEO 는 30개가 있었다. 두 화면이
        # 나란히 놓이는데 한쪽만 코드가 나오면 GEO 는 고칠 방법이 없어 보인다.
        fix_example=with_brand(
            issue.fix_example or code_example_for(issue.check_id), brand_name
        ),
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


def _check_payload(outcome: Any, declared: dict[str, tuple[Any, Any]]) -> GeoCheckPayload:
    """판정 한 줄 — 근거까지 함께.

    명세에 없는 검사가 결과에 있으면(수집기가 앞서 나간 경우) 이름 대신 식별자를 쓰고
    영역은 비운다. 지어낸 영역에 끼워 넣으면 화면의 묶음이 조용히 틀린다.
    """
    entry = declared.get(outcome.check_id)
    category = None if entry is None else entry[0]
    check = None if entry is None else entry[1]
    return GeoCheckPayload(
        check_id=outcome.check_id,
        title_ko=outcome.check_id if check is None else check.title_ko,
        category_id="" if category is None else category.id,
        category_name_ko="" if category is None else category.name_ko,
        remediation_owner="DEVELOPER" if check is None else str(check.remediation_owner),
        status=str(outcome.status),
        confidence_level=outcome.confidence_level,
        note_ko=outcome.note,
        evidence_ids=list(outcome.evidence_ids),
        observed=outcome.observed_value,
    )
