"""저장된 진단에서 리포트 입력을 되살린다.

리포트는 고객에게 나가는 문서이고, 발행되면 고칠 수 없고, 내용 해시가 붙는다. 그
불변성 장치 전체가 **아무도 재지 않은 숫자** 를 지키고 있었다:

``DiagnosisInput`` 을 만드는 코드는 ``veo/reports/schemas.py`` 한 곳뿐이었고, 그것은
HTTP 요청 본문에서 만든다. 저장된 진단에서 만드는 코드는 0건이었다. 즉 리포트를
발행하려면 점수·판정·근거·측정 조건을 **호출자가 전부 타이핑해 넣어야** 했다.
``reports`` 테이블에 0줄이 있던 이유가 그것이다 — 정직하게 채울 방법이 없었다.

여기서 되살리는 값은 전부 이미 저장돼 있던 것이다.

======================  ==============================================
``score_results``       점수·구간·측정범위·신뢰도·명세 버전·계산 과정
``check_results``       항목별 판정과 못 잰 이유
``evidence``            판정의 근거 (이름으로 부를 수 있게 된 뒤부터)
``issues``              조치 대상과 담당 직군
``scan_runs``           측정 조건 — 무엇으로 어떻게 쟀는지
======================  ==============================================

비어 있는 것은 비워 둔다. 특히 **키워드 수요와 경쟁사 관측은 여기서 만들지 않는다** —
이 진단 실행이 잰 것이 아니기 때문이다. 리포트에 그 칸이 필요하면 각자의 측정에서
와야 하고, 없으면 없는 채로 나가는 것이 맞다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.collect.contract import EvidenceRecord, IssueDraft
from veo.db.models.analysis import CheckResult, Evidence, Issue, Scan, ScanRun, ScoreResult
from veo.reports.snapshot import DiagnosisInput, DomainDiagnosis
from veo.scoring.models import (
    AppliedCap,
    CategoryScore,
    CheckOutcome,
    RaisedGate,
    ScoringSpec,
)
from veo.scoring.models import ScoreResult as ScoredResult
from veo.seo.conditions import conditions_from_stored
from veo.seo.service import load_seo_spec

#: 화면과 문서에서 이 영역을 부르는 이름.
SEO_DOMAIN_KEY = "seo"
SEO_DOMAIN_NAME_KO = "SEO 준비도"


class ScanNotReportable(Exception):
    """이 실행으로는 리포트를 만들 수 없다. **이유를 한국어로 들고 다닌다.**

    조용히 빈 리포트를 만드는 선택지는 없다. 빈 리포트는 "잴 것이 없었다" 로 읽히는데,
    실제로는 "쟀지만 그 기록으로는 문서를 만들 수 없다" 이다.
    """

    def __init__(self, message_ko: str) -> None:
        self.message_ko = message_ko
        super().__init__(message_ko)


@dataclass(frozen=True, slots=True)
class ReportableScan:
    """리포트로 만들 수 있는 한 번의 진단."""

    scan_run: ScanRun
    project_id: uuid.UUID
    diagnosis: DiagnosisInput


def _outcome_from(row: CheckResult) -> CheckOutcome:
    """저장된 판정 한 줄을 채점기가 쓰던 모양으로 되돌린다.

    ``note`` 를 못 잰 이유에서 되살리는 것이 요점이다. 그 문장이 없으면 리포트는
    측정 불가 항목을 이유 없이 나열하게 되고, 읽는 사람은 그것을 **점수 0** 으로 읽는다.
    """
    return CheckOutcome(
        check_id=row.check_id,
        status=row.status,  # type: ignore[arg-type]
        confidence=row.confidence,
        affected_weight=row.affected_weight,
        evaluated_weight=row.evaluated_weight,
        evidence_ids=tuple(str(value) for value in (row.evidence_ids or [])),
        observed_value=row.observed_value or None,
        note=row.unknown_reason or row.not_applicable_reason,
    )


def _score_from(row: ScoreResult, outcomes: list[CheckOutcome]) -> ScoredResult:
    """저장된 점수를 그대로 되돌린다. 어느 값도 다시 계산하지 않는다.

    다시 계산하면 **오늘의 명세로 어제의 자료를 채점한** 숫자가 나오고, 그것은 그때
    고객에게 보여준 점수와 다른 숫자다.
    """
    return ScoredResult(
        spec_id=row.spec_id,
        spec_version=row.spec_version,
        spec_checksum=row.spec_checksum,
        domain=row.domain,  # type: ignore[arg-type]
        status=row.status,  # type: ignore[arg-type]
        overall_score=row.score,
        overall_score_before_caps=row.score_before_caps,
        band_id=row.band_id,
        coverage=row.coverage,
        confidence=row.confidence,
        effective_weight_total=row.effective_weight_total,
        categories=[CategoryScore.model_validate(item) for item in (row.category_scores or [])],
        applied_caps=[AppliedCap.model_validate(item) for item in (row.applied_caps or [])],
        gates=[RaisedGate.model_validate(item) for item in (row.gates or [])],
        outcomes=outcomes,
        trace=dict(row.calculation_trace or {}),
    )


def _evidence_from(row: Evidence) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=row.evidence_id,
        kind=row.kind,
        url=row.url,
        collected_at=row.collected_at,
        content_hash=row.content_hash,
        excerpt=row.excerpt or "",
        storage_key=row.storage_key,
        detail=dict(row.detail or {}),
    )


def _issue_from(row: Issue) -> IssueDraft:
    """이슈 행을 리포트가 읽는 모양으로.

    ``remediation_ko`` 는 여기서 지어내지 않는다. 조치 문구는 ``fix_recommendations``
    소관이고, 없으면 빈 문자열로 남긴다 — 리포트가 "이렇게 고치세요" 를 창작하면
    고객은 그 문장을 우리가 검증한 처방으로 읽는다.
    """
    return IssueDraft(
        check_id=row.check_id,
        title_ko=row.title_ko,
        summary_ko="",
        affected_urls=tuple(str(value) for value in (row.sample_urls or [])),
        evidence_ids=tuple(str(value) for value in (row.evidence_ids or [])),
        remediation_ko="",
        remediation_owner=row.remediation_owner,
        business_impact_ko=row.business_impact_ko or "",
    )


def _band_label(spec: ScoringSpec, score: float | None, band_id: str | None) -> str | None:
    """저장된 구간 id 에 해당하는 이름. 없으면 ``None`` — 점수에서 다시 계산하지 않는다.

    구간 경계는 명세 개정으로 움직인다. 오늘의 경계로 어제의 점수에 이름을 붙이면
    그때 고객이 본 등급과 다른 등급이 문서에 실린다.
    """
    if band_id is None:
        return None
    for band in spec.bands:
        if band.id == band_id:
            return band.label_ko
    return None


def diagnosis_from_scan(
    db: Session, *, principal: Principal, scan_run_id: uuid.UUID, title_ko: str
) -> ReportableScan:
    """저장된 진단 한 번을 리포트 입력으로 되살린다.

    실측에만 근거한다. 요청 본문에서 오는 숫자는 하나도 없다.
    """
    runs = tenant_select(ScanRun, principal).where(ScanRun.id == scan_run_id)
    assert_tenant_scoped(runs, principal.organization_id)
    run = db.execute(runs).scalar_one_or_none()
    if run is None:
        raise ScanNotReportable("진단 실행 기록을 찾을 수 없습니다.")

    scans = tenant_select(Scan, principal).where(Scan.id == run.scan_id)
    assert_tenant_scoped(scans, principal.organization_id)
    scan = db.execute(scans).scalar_one_or_none()
    if scan is None:
        raise ScanNotReportable("진단 실행 기록을 찾을 수 없습니다.")

    scores = tenant_select(ScoreResult, principal).where(ScoreResult.scan_run_id == run.id)
    assert_tenant_scoped(scores, principal.organization_id)
    score_row = db.execute(scores).scalars().first()
    if score_row is None:
        raise ScanNotReportable(
            "이 실행에는 채점 결과가 없습니다. 점수 없이 리포트를 발행하면 "
            "'측정하지 못했다'가 '문제가 없다'로 읽힙니다."
        )

    conditions = conditions_from_stored(run.measurement_conditions)
    if conditions is None:
        raise ScanNotReportable(
            "이 실행은 측정 조건이 기록되기 전에 저장되어, 어떤 조건에서 쟀는지 문서에 "
            "적을 수 없습니다. 다시 진단하면 리포트를 만들 수 있습니다."
        )

    checks = tenant_select(CheckResult, principal).where(CheckResult.scan_run_id == run.id)
    assert_tenant_scoped(checks, principal.organization_id)
    outcomes = [_outcome_from(row) for row in db.execute(checks).scalars()]

    evidence_rows = tenant_select(Evidence, principal).where(Evidence.scan_run_id == run.id)
    assert_tenant_scoped(evidence_rows, principal.organization_id)
    evidence = [_evidence_from(row) for row in db.execute(evidence_rows).scalars()]

    issue_rows = (
        tenant_select(Issue, principal)
        .where(Issue.project_id == scan.project_id, Issue.last_seen_run_id == run.id)
        .order_by(Issue.created_at)
    )
    assert_tenant_scoped(issue_rows, principal.organization_id)
    issues = [_issue_from(row) for row in db.execute(issue_rows).scalars()]

    spec = load_seo_spec()
    score = _score_from(score_row, outcomes)

    domain = DomainDiagnosis(
        key=SEO_DOMAIN_KEY,
        name_ko=SEO_DOMAIN_NAME_KO,
        score=score,
        conditions=conditions,
        # 요약을 지어내지 않는다. 리포트 렌더러가 저장된 값에서 문장을 만든다.
        summary_ko="",
        issues=tuple(issues),
        evidence=tuple(evidence),
        # 명세를 함께 넘긴다. 요청 본문 경로는 이걸 실을 방법이 없어서 항목 제목과
        # 심각도가 대체 문구로 떨어졌다.
        spec=spec,
        band_label_ko=_band_label(spec, score_row.score, score_row.band_id),
        run_ids=(str(run.id),),
        # 실제로 응답한 공급자만. 흔들린(DEGRADED) 공급자는 여기 들어가지 않는다.
        data_sources=conditions.enabled_providers,
    )

    return ReportableScan(
        scan_run=run,
        project_id=scan.project_id,
        diagnosis=DiagnosisInput(
            title_ko=title_ko,
            audience="BUSINESS",
            generated_at=datetime.now(conditions.measured_at.tzinfo),
            measurement_window_start=run.started_at,
            measurement_window_end=run.finished_at,
            domains=(domain,),
            # 이 진단이 잰 것이 아니다. 비운다.
            keywords=(),
            competitors=(),
        ),
    )


def reportable_runs(
    db: Session, *, principal: Principal, project_id: uuid.UUID, limit: int = 20
) -> list[ScanRun]:
    """이 프로젝트에서 리포트로 만들 수 있는 실행들, 최신순.

    측정 조건이 없는 실행은 목록에서 뺀다. 골랐다가 거절당하는 것보다 애초에 고를 수
    없는 편이 낫다.
    """
    statement = (
        select(ScanRun)
        .join(Scan, Scan.id == ScanRun.scan_id)
        .where(
            ScanRun.organization_id == principal.organization_id,
            Scan.organization_id == principal.organization_id,
            Scan.project_id == project_id,
            # `isnot(None)` 으로는 부족하다. JSONB 칸에 파이썬 None 을 넣으면 SQL NULL 이
            # 아니라 **JSON null** 이 저장되고, 그 행은 조건이 없는데도 고를 수 있는 것처럼
            # 목록에 남는다. 실제로 그렇게 새어 나갔다. 객체인 행만 남긴다.
            func.jsonb_typeof(ScanRun.measurement_conditions) == "object",
        )
        .order_by(ScanRun.started_at.desc())
        .limit(limit)
    )
    assert_tenant_scoped(statement, principal.organization_id)
    return list(db.execute(statement).scalars())


__all__ = [
    "SEO_DOMAIN_KEY",
    "SEO_DOMAIN_NAME_KO",
    "ReportableScan",
    "ScanNotReportable",
    "diagnosis_from_scan",
    "reportable_runs",
]
