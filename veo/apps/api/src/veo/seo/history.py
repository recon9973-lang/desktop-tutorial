"""진단 결과를 남기고 다시 읽는다.

지금까지 진단은 채점하고 버렸다. 그래서 "지난달보다 나아졌나" 에 답할 수 없었다. 기획서
§10 은 방법론 버전이 바뀌어도 과거 점수를 보존하라 하고, 구현계획 3단계는 이슈의 재발
추적을 요구한다 — 둘 다 결과가 남아 있어야 성립하는 요구다.

무엇을 남기는지가 중요하다. **점수만 남기면 "왜 35점이었는지" 를 설명할 수 없다.** 명세는
개정되고, 반년 뒤 같은 사이트를 다시 재면 다른 규칙으로 채점된다. 그래서 항목별 판정과
근거, 그리고 그때 적용된 명세의 버전·체크섬을 함께 남긴다.

이슈는 실행마다 새로 만들지 않는다. 같은 검사 항목의 문제는 하나의 이슈로 이어 붙인다 —
매번 새로 만들면 담당자 배정과 재검증 이력이 진단할 때마다 끊기고, 목록은 진단 횟수만큼
불어난다. 고쳤다가 다시 깨진 것은 `RECURRED` 로 구분한다. 한 번도 못 고친 것과 다른
사건이기 때문이다.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.contracts.enums import IssueState, ScanScope, Surface
from veo.db.models.analysis import CheckResult, Evidence, Issue, Scan, ScanRun, ScoreResult
from veo.db.models.identity import Site, User
from veo.scoring.models import CheckStatus
from veo.seo.service import SeoScanResult, load_seo_spec

#: 이 코드가 만든 결과임을 나중에 알아볼 수 있게 하는 표식. 수집 방식이 바뀌면 올린다.
COLLECTOR_VERSION: Final = "console-crawl/1"

SEO_KIND: Final = "SEO"

#: 이슈로 올릴 판정. 통과·해당없음·측정불가는 조치 대상이 아니다 — 측정불가를 이슈로
#: 만들면 "우리가 못 잰 것" 이 "고객이 고칠 것" 으로 둔갑한다.
_ACTIONABLE: Final = frozenset({CheckStatus.FAIL, CheckStatus.WARNING})


class SiteNotFound(Exception):
    """그 사이트가 없거나, 다른 조직의 것이다. 둘을 구분해 알려주지 않는다."""


@dataclass(frozen=True, slots=True)
class SavedScan:
    """방금 남긴 한 번의 진단."""

    scan_run_id: uuid.UUID
    score: float | None
    band_id: str | None
    coverage: float
    confidence: float
    spec_version: str
    started_at: datetime
    finished_at: datetime


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """이력 한 줄. 추이 그래프의 점 하나가 된다."""

    scan_run_id: uuid.UUID
    started_at: datetime
    finished_at: datetime | None
    status: str
    urls_collected: int
    score: float | None
    band_id: str | None
    coverage: float
    confidence: float
    spec_version: str
    spec_checksum: str
    #: 실행한 사람. 계정이 지워졌거나 예약 실행이면 ``None`` — 기록 자체는 남는다.
    requested_by_name: str | None


def _severity_index() -> dict[str, str]:
    """검사 항목별 심각도. **명세에서만** 읽는다.

    수집기도 채점 결과도 심각도를 정하지 않는다 — 심각도는 발행된 명세의 소관이고,
    저장할 때 다른 곳에서 가져오면 화면과 DB 가 서로 다른 값을 말하게 된다.
    """
    spec = load_seo_spec()
    return {
        check.id: str(check.severity)
        for category in spec.categories
        for check in category.checks
    }


def _site_for(db: Session, *, principal: Principal, site_id: uuid.UUID) -> Site:
    statement = tenant_select(Site, principal).where(Site.id == site_id)
    assert_tenant_scoped(statement, principal.organization_id)
    site = db.execute(statement).scalar_one_or_none()
    if site is None:
        raise SiteNotFound(str(site_id))
    return site


def site_exists(db: Session, *, principal: Principal, site_id: uuid.UUID) -> bool:
    """이 조직에 그 사이트가 있는가. 다른 조직의 것은 없는 것과 같다."""
    try:
        _site_for(db, principal=principal, site_id=site_id)
    except SiteNotFound:
        return False
    return True


def _scan_for(db: Session, *, principal: Principal, site: Site) -> Scan:
    """이 사이트의 SEO 진단 묶음. 없으면 만든다 — 이력이 매달리는 축이다."""
    statement = (
        tenant_select(Scan, principal)
        .where(Scan.site_id == site.id, Scan.kind == SEO_KIND, Scan.is_active.is_(True))
        .limit(1)
    )
    assert_tenant_scoped(statement, principal.organization_id)
    existing = db.execute(statement).scalar_one_or_none()
    if existing is not None:
        return existing

    created = Scan(
        organization_id=principal.organization_id,
        project_id=site.project_id,
        site_id=site.id,
        kind=SEO_KIND,
        scope=ScanScope.SITE.value,
        target_url=site.origin,
        configuration={},
        is_active=True,
    )
    db.add(created)
    db.flush()
    return created


def save_scan_run(
    db: Session,
    *,
    principal: Principal,
    site_id: uuid.UUID,
    result: SeoScanResult,
    urls_attempted: int,
    urls_collected: int,
    started_at: datetime | None = None,
    report_snapshot: dict[str, object] | None = None,
) -> SavedScan:
    """한 번의 진단을 남긴다 — 실행·점수·항목별 판정·근거·이슈까지."""
    site = _site_for(db, principal=principal, site_id=site_id)
    scan = _scan_for(db, principal=principal, site=site)

    finished = datetime.now(UTC)
    run = ScanRun(
        organization_id=principal.organization_id,
        scan_id=scan.id,
        surface=Surface.CONSOLE.value,
        # 측정하지 못한 항목이 있어도 실행 자체는 성공이다. 부분 성공은 수집을 **못 한**
        # 경우를 위한 상태이지, 자격증명이 없어 UNKNOWN 이 난 경우가 아니다.
        status="SUCCEEDED" if urls_collected == urls_attempted else "PARTIAL_SUCCESS",
        started_at=started_at or finished,
        finished_at=finished,
        collector_version=COLLECTOR_VERSION,
        device_profile="DESKTOP",
        urls_attempted=urls_attempted,
        urls_collected=urls_collected,
        provider_states={},
        partial_reasons=[],
        requested_by_user_id=principal.user_id,
        report_snapshot=report_snapshot,
    )
    db.add(run)
    db.flush()

    score = result.score
    db.add(
        ScoreResult(
            organization_id=principal.organization_id,
            scan_run_id=run.id,
            spec_id=score.spec_id,
            spec_version=score.spec_version,
            # 채점 당시의 명세를 못 박는다. 명세가 개정되면 같은 사이트라도 다른 규칙으로
            # 채점되므로, 체크섬 없이는 과거 점수를 비교할 수 없다.
            spec_checksum=score.spec_checksum,
            domain=str(score.domain),
            status=score.status,
            score=score.overall_score,
            score_before_caps=score.overall_score_before_caps,
            band_id=score.band_id,
            coverage=score.coverage,
            confidence=score.confidence,
            effective_weight_total=score.effective_weight_total,
            category_scores=[item.model_dump(mode="json") for item in score.categories],
            applied_caps=[item.model_dump(mode="json") for item in score.applied_caps],
            gates=[item.model_dump(mode="json") for item in score.gates],
            # 계산 과정을 남긴다. 기획서 §5 — 점수마다 원자료와 계산 과정을 연결한다.
            # 이것이 없으면 반년 뒤 "왜 이 점수였는지" 를 재현할 수 없다.
            calculation_trace=dict(score.trace),
        )
    )

    _save_outcomes(db, principal=principal, run=run, result=result)
    _save_evidence(db, principal=principal, run=run, result=result)
    _upsert_issues(db, principal=principal, run=run, site=site, result=result)
    db.flush()

    return SavedScan(
        scan_run_id=run.id,
        score=score.overall_score,
        band_id=score.band_id,
        coverage=score.coverage,
        confidence=score.confidence,
        spec_version=score.spec_version,
        started_at=run.started_at or finished,
        finished_at=finished,
    )


def _save_outcomes(
    db: Session, *, principal: Principal, run: ScanRun, result: SeoScanResult
) -> None:
    """항목별 판정. 못 잰 항목은 **이유와 함께** 남긴다."""
    category_of = {
        check_id: category.category_id
        for category in result.score.categories
        for check_id in category.applicable_check_ids
        + category.not_applicable_check_ids
        + category.unknown_check_ids
    }
    unknown_reason_of = {item.check_id: item.reason_ko for item in result.unknown_checks}
    severity_of = _severity_index()

    for outcome in result.score.outcomes:
        db.add(
            CheckResult(
                organization_id=principal.organization_id,
                scan_run_id=run.id,
                check_id=outcome.check_id,
                category_id=category_of.get(outcome.check_id, ""),
                status=str(outcome.status),
                severity=severity_of.get(outcome.check_id, "INFO"),
                confidence=outcome.confidence or 0.0,
                affected_weight=outcome.affected_weight,
                evaluated_weight=outcome.evaluated_weight,
                not_applicable_reason=(
                    outcome.note if outcome.status is CheckStatus.NOT_APPLICABLE else None
                ),
                unknown_reason=(
                    unknown_reason_of.get(outcome.check_id) or outcome.note
                    if outcome.status is CheckStatus.UNKNOWN
                    else None
                ),
                observed_value={},
                evidence_ids=list(outcome.evidence_ids),
            )
        )


def _save_evidence(
    db: Session, *, principal: Principal, run: ScanRun, result: SeoScanResult
) -> None:
    """판정의 근거. 감사할 수 없는 지적은 소문이다."""
    for record in result.evidence:
        db.add(
            Evidence(
                organization_id=principal.organization_id,
                scan_run_id=run.id,
                kind=record.kind,
                url=record.url,
                collected_at=record.collected_at,
                content_hash=record.content_hash,
                storage_key=record.storage_key,
                excerpt=record.excerpt or None,
                byte_size=None,
                source="COLLECTED",
                detail=dict(record.detail),
            )
        )


def _upsert_issues(
    db: Session, *, principal: Principal, run: ScanRun, site: Site, result: SeoScanResult
) -> None:
    """같은 검사 항목의 문제는 하나의 이슈로 이어 붙인다."""
    actionable = {
        outcome.check_id for outcome in result.score.outcomes if outcome.status in _ACTIONABLE
    }
    severity_of = _severity_index()

    statement = tenant_select(Issue, principal).where(Issue.project_id == site.project_id)
    assert_tenant_scoped(statement, principal.organization_id)
    existing = {issue.check_id: issue for issue in db.execute(statement).scalars()}

    for draft in result.issues:
        if draft.check_id not in actionable:
            continue

        issue = existing.get(draft.check_id)
        if issue is None:
            db.add(
                Issue(
                    organization_id=principal.organization_id,
                    project_id=site.project_id,
                    first_seen_run_id=run.id,
                    last_seen_run_id=run.id,
                    check_id=draft.check_id,
                    severity=severity_of.get(draft.check_id, "MINOR"),
                    state=IssueState.OPEN.value,
                    title_ko=draft.title_ko,
                    business_impact_ko=draft.business_impact_ko or None,
                    affected_url_count=len(draft.affected_urls),
                    sample_urls=list(draft.affected_urls[:10]),
                    evidence_ids=list(draft.evidence_ids),
                    remediation_owner=draft.remediation_owner,
                    regression_count=0,
                )
            )
            continue

        # 고쳤다고 확인된 문제가 다시 잡혔다면 재발이다. 진행 중이던 이슈의 상태는
        # 건드리지 않는다 — 담당자가 손대고 있는 것을 진단이 되돌리면 안 된다.
        if issue.state == IssueState.VERIFIED_RESOLVED.value:
            issue.state = IssueState.RECURRED.value
            issue.regression_count += 1

        issue.last_seen_run_id = run.id
        issue.affected_url_count = len(draft.affected_urls)
        issue.sample_urls = list(draft.affected_urls[:10])
        issue.evidence_ids = list(draft.evidence_ids)


def read_scan_history(
    db: Session, *, principal: Principal, site_id: uuid.UUID, limit: int = 50
) -> Sequence[HistoryEntry]:
    """이 사이트의 진단 이력을 최신순으로. 다른 조직의 것은 보이지 않는다."""
    statement = (
        select(ScanRun, ScoreResult, User.display_name)
        .join(Scan, Scan.id == ScanRun.scan_id)
        .join(ScoreResult, ScoreResult.scan_run_id == ScanRun.id)
        # 실행자는 지워졌을 수 있다. outer join 이어야 그 경우에도 이력이 사라지지 않는다.
        .outerjoin(User, User.id == ScanRun.requested_by_user_id)
        .where(
            # 조인한 세 테이블 **모두** 조직으로 거른다. 하나라도 빠지면 다른 조직의
            # 행과 맞물릴 수 있고, `assert_tenant_scoped` 는 그것을 거부한다.
            ScanRun.organization_id == principal.organization_id,
            Scan.organization_id == principal.organization_id,
            ScoreResult.organization_id == principal.organization_id,
            Scan.site_id == site_id,
            Scan.kind == SEO_KIND,
        )
        .order_by(ScanRun.started_at.desc())
        .limit(limit)
    )
    assert_tenant_scoped(statement, principal.organization_id)

    return [
        HistoryEntry(
            scan_run_id=run.id,
            started_at=run.started_at or run.created_at,
            finished_at=run.finished_at,
            status=run.status,
            urls_collected=run.urls_collected,
            score=score.score,
            band_id=score.band_id,
            coverage=score.coverage,
            confidence=score.confidence,
            spec_version=score.spec_version,
            spec_checksum=score.spec_checksum,
            requested_by_name=display_name,
        )
        for run, score, display_name in db.execute(statement).all()
    ]


def read_scan_report(
    db: Session, *, principal: Principal, scan_run_id: uuid.UUID
) -> dict[str, object] | None:
    """그때 보여준 보고서를 그대로 돌려준다. 없거나 남의 것이면 ``None``.

    다시 재지 않고 지난 결과를 여는 길이다. 같은 도메인을 하루에 몇 번씩 다시 재는 것은
    대상 사이트에도 우리 비용에도 부담이고, 변경을 확인하려는 것이 아니면 다시 잴 이유가
    없다.
    """
    statement = tenant_select(ScanRun, principal).where(ScanRun.id == scan_run_id)
    assert_tenant_scoped(statement, principal.organization_id)
    run = db.execute(statement).scalar_one_or_none()
    if run is None or run.report_snapshot is None:
        return None
    return dict(run.report_snapshot)
