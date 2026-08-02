"""Scoring specification transparency and the shared evaluator endpoint.

VEO-LAB authors the specifications and VEO publishes them here in full: weights,
severities, caps, gates and changelog. A customer can read exactly how a number was
produced, and reproduce it from the same inputs.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from veo.api.deps import RequestId, ok
from veo.api.schemas import (
    AppliedCapPayload,
    CategoryScorePayload,
    EvaluateScoreRequest,
    GatePayload,
    ScorePayload,
    SpecBandDetail,
    SpecCapDetail,
    SpecCategoryDetail,
    SpecCheckDetail,
    SpecDetail,
    SpecGateDetail,
    SpecListPayload,
    SpecSamplingDetail,
    SpecScopeDetail,
    SpecStatusPolicyDetail,
    SpecSummary,
)
from veo.contracts.enums import ErrorCode
from veo.contracts.envelope import ApiError, ApiResponse
from veo.scoring import (
    CheckOutcome,
    CheckStatus,
    ScoreResult,
    ScoringSpec,
    ScoringSpecError,
    SpecNotFoundError,
    available_specs,
    evaluate,
    load_spec,
)

router = APIRouter(prefix="/scoring", tags=["scoring"])


def _summary(spec: ScoringSpec) -> SpecSummary:
    return SpecSummary(
        spec_id=spec.spec_id,
        domain=str(spec.domain),
        version=spec.version,
        status=str(spec.status),
        checksum=spec.checksum,
        effective_at=spec.effective_at,
        methodology_owner=spec.methodology_owner,
        implementation_owner=spec.implementation_owner,
        score_meaning_ko=spec.score_meaning.ko,
        is_rank_prediction=spec.score_meaning.is_rank_prediction,
        category_weights={c.id: c.weight for c in spec.categories},
    )


@router.get(
    "/specs",
    response_model=ApiResponse[SpecListPayload],
    summary="발행된 점수 명세 목록",
)
def list_specs(request_id: RequestId) -> ApiResponse[SpecListPayload]:
    summaries = []
    for spec_id, versions in available_specs().items():
        for version in versions:
            summaries.append(_summary(load_spec(spec_id, version)))
    return ok(SpecListPayload(specs=summaries), request_id)


@router.get(
    "/specs/{spec_id}/{version}",
    response_model=ApiResponse[SpecDetail],
    summary="점수 명세 상세 — 배점·심각도·상한·게이트 전문",
)
def get_spec(spec_id: str, version: str, request_id: RequestId) -> ApiResponse[SpecDetail]:
    spec = _load_or_404(spec_id, version)
    detail = SpecDetail(
        **_summary(spec).model_dump(),
        bands=[
            SpecBandDetail(
                id=band.id,
                min=band.min,
                max=band.max,
                label_ko=band.label_ko,
                description_ko=band.description_ko,
            )
            for band in spec.bands
        ],
        categories=[
            SpecCategoryDetail(
                id=category.id,
                name_ko=category.name_ko,
                weight=category.weight,
                description_ko=category.description_ko,
                is_gate=category.is_gate,
                raw_budget=category.raw_budget,
                contributes_to_score=category.contributes_to_score,
                checks=[
                    SpecCheckDetail(
                        id=check.id,
                        title_ko=check.title_ko,
                        severity=str(check.severity),
                        scope=check.scope,
                        remediation_owner=check.remediation_owner,
                        applicability_ko=check.applicability_ko,
                        evidence_required=list(check.evidence_required),
                        engine_scope=list(check.engine_scope),
                        points=check.points,
                    )
                    for check in category.checks
                ],
            )
            for category in spec.categories
        ],
        caps=[
            SpecCapDetail(
                id=cap.id,
                max_overall_score=cap.max_overall_score,
                reason_ko=cap.reason_ko,
                release_condition_ko=cap.release_condition_ko,
            )
            for cap in spec.caps
        ],
        gates=[
            SpecGateDetail(
                id=gate.id,
                status_code=gate.status_code,
                label_ko=gate.label_ko,
                description_ko=gate.description_ko,
            )
            for gate in spec.gates
        ],
        severity_coefficients={str(k): v for k, v in spec.severity_coefficients.items()},
        url_importance=dict(spec.url_importance),
        status_policy=SpecStatusPolicyDetail(
            fail_penalty_multiplier=spec.status_policy.fail_penalty_multiplier,
            warning_penalty_multiplier=spec.status_policy.warning_penalty_multiplier,
            pass_penalty_multiplier=spec.status_policy.pass_penalty_multiplier,
            breadth_exponent=spec.status_policy.breadth_exponent,
            not_applicable=spec.status_policy.not_applicable,
            unknown=spec.status_policy.unknown,
            not_sampled=spec.status_policy.not_sampled,
        ),
        measurement_scope=(
            None
            if spec.measurement_scope is None
            else SpecScopeDetail(
                max_pages=spec.measurement_scope.max_pages,
                max_depth=spec.measurement_scope.max_depth,
                template_group_sample=spec.measurement_scope.template_group_sample,
                truncated_absence=spec.measurement_scope.truncated_absence,
                rationale_ko=spec.measurement_scope.rationale_ko,
            )
        ),
        sampling=(
            None
            if spec.sampling is None
            else SpecSamplingDetail(
                perf_lab_max_urls=(
                    None if spec.sampling.perf_lab is None else spec.sampling.perf_lab.max_urls
                ),
                perf_lab_min_measured_ratio=(
                    None
                    if spec.sampling.perf_lab is None
                    else spec.sampling.perf_lab.min_measured_ratio
                ),
                perf_lab_check_ids=(
                    []
                    if spec.sampling.perf_lab is None
                    else list(spec.sampling.perf_lab.check_ids)
                ),
                perf_lab_rationale_ko=(
                    None
                    if spec.sampling.perf_lab is None
                    else spec.sampling.perf_lab.rationale_ko
                ),
                perf_field_check_ids=(
                    []
                    if spec.sampling.perf_field is None
                    else list(spec.sampling.perf_field.check_ids)
                ),
                perf_field_rationale_ko=(
                    None
                    if spec.sampling.perf_field is None
                    else spec.sampling.perf_field.rationale_ko
                ),
            )
        ),
        changelog=[entry.model_dump() for entry in spec.changelog],
    )
    return ok(
        detail,
        request_id,
        spec_id=spec.spec_id,
        spec_version=spec.version,
        spec_checksum=spec.checksum,
    )


@router.post(
    "/evaluate",
    response_model=ApiResponse[ScorePayload],
    summary="검사 결과를 명세에 대입해 점수를 재현",
    description=(
        "동일한 입력과 동일한 명세로 언제든 같은 점수가 나오는지 확인할 수 있는 "
        "재현용 엔드포인트입니다. 제품 전체가 이 evaluator 하나만 사용합니다."
    ),
)
def evaluate_score(
    payload: EvaluateScoreRequest, request_id: RequestId
) -> ApiResponse[ScorePayload]:
    spec = _load_or_404(payload.spec_id, payload.spec_version)

    try:
        outcomes = [
            CheckOutcome(
                check_id=item.check_id,
                status=CheckStatus(item.status),
                confidence=item.confidence,
                confidence_level=item.confidence_level,
                affected_weight=item.affected_weight,
                evaluated_weight=item.evaluated_weight,
                evidence_ids=tuple(item.evidence_ids),
            )
            for item in payload.outcomes
        ]
        result = evaluate(spec, outcomes)
    except ScoringSpecError as exc:
        raise HTTPException(
            status_code=422,
            detail=ApiError.of(ErrorCode.VALIDATION_FAILED, str(exc)).model_dump(mode="json"),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=ApiError.of(
                ErrorCode.VALIDATION_FAILED, "검사 결과 입력이 올바르지 않습니다."
            ).model_dump(mode="json"),
        ) from exc

    return ok(
        _score_payload(result, spec),
        request_id,
        spec_id=spec.spec_id,
        spec_version=spec.version,
        spec_checksum=spec.checksum,
    )


def _score_payload(result: ScoreResult, spec: ScoringSpec) -> ScorePayload:
    return ScorePayload(
        spec_id=result.spec_id,
        spec_version=result.spec_version,
        spec_checksum=result.spec_checksum,
        domain=str(result.domain),
        status=result.status,
        score=result.overall_score,
        score_before_caps=result.overall_score_before_caps,
        band_id=result.band_id,
        coverage=result.coverage,
        confidence=result.confidence,
        effective_weight_total=result.effective_weight_total,
        is_rank_prediction=spec.score_meaning.is_rank_prediction,
        categories=[
            CategoryScorePayload(
                category_id=category.category_id,
                name_ko=category.name_ko,
                weight=category.weight,
                status=category.status,
                score=category.score,
                budget=category.budget,
                penalty_total=category.penalty_total,
                coverage=category.coverage,
                confidence=category.confidence,
                not_applicable_check_ids=category.not_applicable_check_ids,
                unknown_check_ids=category.unknown_check_ids,
                failing_check_ids=category.failing_check_ids,
            )
            for category in result.categories
        ],
        applied_caps=[
            AppliedCapPayload(
                cap_id=cap.cap_id,
                max_overall_score=cap.max_overall_score,
                reason_ko=cap.reason_ko,
                release_condition_ko=cap.release_condition_ko,
                triggered_by=cap.triggered_by,
            )
            for cap in result.applied_caps
        ],
        gates=[
            GatePayload(
                gate_id=gate.gate_id,
                status_code=gate.status_code,
                label_ko=gate.label_ko,
                description_ko=gate.description_ko,
                triggered_by=gate.triggered_by,
            )
            for gate in result.gates
        ],
        calculation_trace=result.trace,
    )


def _load_or_404(spec_id: str, version: str) -> ScoringSpec:
    try:
        return load_spec(spec_id, version)
    except SpecNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ApiError.of(
                ErrorCode.NOT_FOUND, f"점수 명세를 찾을 수 없습니다: {spec_id}@{version}"
            ).model_dump(mode="json"),
        ) from exc
