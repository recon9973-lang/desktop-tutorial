"""Three audiences, one snapshot.

An executive asks "are we alright, and what do we do first". A marketer asks "which
category, which keyword, which competitor". A developer asks "which URL, which evidence,
what do I change and how do I prove it worked". Those are three readings of the same
measurement, and the moment they become three *calculations* the product starts shipping
three different truths.

So no view computes anything. Each one selects :class:`~veo.reports.snapshot.MetricRow`
objects out of the frozen snapshot and arranges them; the number it prints is the number
the snapshot holds, byte for byte. ``ReportView.number`` exists so that a test — and a
reviewer — can check that claim directly.
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from veo.reports.snapshot import (
    SECTION_CATEGORY,
    SECTION_COMPETITOR,
    SECTION_KEYWORD,
    SECTION_OVERALL,
    ChangeSnapshot,
    CheckSnapshot,
    EvidenceSnapshot,
    MeasuredValue,
    MetricRow,
    Provenance,
    ReportSnapshot,
    ValueStatus,
)

__all__ = [
    "ActionItem",
    "BaseAudienceView",
    "CategoryTable",
    "CategoryTableRow",
    "CompetitorRow",
    "DeveloperView",
    "DisclosureBlock",
    "ExecutiveView",
    "KeywordRow",
    "MarketingView",
    "ReportViews",
    "WorkItem",
    "build_views",
]

_STRICT = ConfigDict(frozen=True, extra="forbid")

AUDIENCE_KO: Final[dict[str, str]] = {
    "BUSINESS": "경영진",
    "MARKETING": "마케팅",
    "DEVELOPER": "개발자",
}

#: Order used when there is no spec to ask. Highest first.
_SEVERITY_ORDER: Final[dict[str, int]] = {
    "BLOCKER": 0,
    "CRITICAL": 1,
    "MAJOR": 2,
    "MINOR": 3,
    "INFO": 4,
    "UNKNOWN": 5,
}

_OWNER_KO: Final[dict[str, str]] = {
    "DEVELOPER": "개발",
    "MARKETER": "마케팅",
    "BUSINESS_OWNER": "경영",
    "OPERATIONS": "운영",
}


class DisclosureBlock(BaseModel):
    """What was measured, when, with which methodology, and what the score is not."""

    model_config = _STRICT

    scope_ko: str
    measured_at_ko: str
    methodology_ko: str
    confidence_ko: str
    coverage_ko: str
    rank_prediction_notice_ko: str
    lines_ko: list[str] = Field(default_factory=list)


class ActionItem(BaseModel):
    model_config = _STRICT

    rank: int
    title_ko: str
    why_ko: str
    owner_ko: str
    severity: str
    domain: str


class CategoryTableRow(BaseModel):
    model_config = _STRICT

    category_id: str
    name_ko: str
    weight: float
    metric_key: str
    value: MeasuredValue
    coverage: MeasuredValue
    confidence: MeasuredValue
    change: MeasuredValue | None = None


class CategoryTable(BaseModel):
    model_config = _STRICT

    domain: str
    name_ko: str
    overall_metric_key: str
    overall: MeasuredValue
    rows: list[CategoryTableRow] = Field(default_factory=list)


class KeywordRow(BaseModel):
    model_config = _STRICT

    keyword: str
    monthly_searches: MeasuredValue
    opportunity: MeasuredValue
    note_ko: str = ""


class CompetitorRow(BaseModel):
    model_config = _STRICT

    slug: str
    label_ko: str
    domain: str
    ours: MeasuredValue
    theirs: MeasuredValue
    gap: MeasuredValue
    is_comparable: bool
    conditions_note_ko: str


class WorkItem(BaseModel):
    model_config = _STRICT

    check_id: str
    domain: str
    title_ko: str
    summary_ko: str
    severity: str
    owner_ko: str
    affected_urls: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    remediation_ko: str
    fix_example: str | None = None
    reverification_ko: str


class BaseAudienceView(BaseModel):
    model_config = _STRICT

    audience: Literal["BUSINESS", "MARKETING", "DEVELOPER"]
    audience_ko: str
    title_ko: str
    summary_ko: str
    metrics: list[MetricRow] = Field(default_factory=list)
    disclosure: DisclosureBlock

    def number(self, metric_key: str) -> MeasuredValue:
        for row in self.metrics:
            if row.metric_key == metric_key:
                return row.value
        raise KeyError(metric_key)

    @property
    def numbers(self) -> dict[str, MeasuredValue]:
        return {row.metric_key: row.value for row in self.metrics}


class ExecutiveView(BaseAudienceView):
    status_ko: str
    headline: list[MetricRow] = Field(default_factory=list)
    competitive_gap: list[MetricRow] = Field(default_factory=list)
    top_actions: list[ActionItem] = Field(default_factory=list)
    changes_ko: list[str] = Field(default_factory=list)
    changes: list[ChangeSnapshot] = Field(default_factory=list)


class MarketingView(BaseAudienceView):
    category_tables: list[CategoryTable] = Field(default_factory=list)
    trends: list[ChangeSnapshot] = Field(default_factory=list)
    keyword_rows: list[KeywordRow] = Field(default_factory=list)
    competitor_rows: list[CompetitorRow] = Field(default_factory=list)


class DeveloperView(BaseAudienceView):
    work_items: list[WorkItem] = Field(default_factory=list)
    unmeasured_checks: list[CheckSnapshot] = Field(default_factory=list)
    evidence: list[EvidenceSnapshot] = Field(default_factory=list)
    reverification_ko: list[str] = Field(default_factory=list)


class ReportViews(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    snapshot: ReportSnapshot
    executive: ExecutiveView
    marketing: MarketingView
    developer: DeveloperView


# --------------------------------------------------------------------------- #
# Disclosure
# --------------------------------------------------------------------------- #


def _scored_provenance(snapshot: ReportSnapshot) -> list[Provenance]:
    domain_keys = {domain.key for domain in snapshot.domains}
    return [entry for key, entry in snapshot.provenance.items() if key in domain_keys]


def _disclosure(snapshot: ReportSnapshot) -> DisclosureBlock:
    entries = _scored_provenance(snapshot)

    scope_parts = [
        f"{entry.label_ko} {entry.pages_examined}개 페이지 "
        f"({entry.locale} / {entry.device} / {entry.renderer})"
        for entry in entries
        if entry.pages_examined is not None
    ]
    measured_parts = [
        f"{entry.label_ko} {entry.measured_at.isoformat()}"
        for entry in entries
        if entry.measured_at is not None
    ]
    coverage_parts = [
        f"{entry.label_ko} {entry.coverage.display_with_unit()}"
        for entry in entries
        if entry.coverage is not None
    ]
    confidence_parts = [
        f"{entry.label_ko} {entry.confidence.display_with_unit()}"
        for entry in entries
        if entry.confidence is not None
    ]

    window = ""
    if snapshot.measurement_window_start and snapshot.measurement_window_end:
        window = (
            f" 측정 기간 {snapshot.measurement_window_start.isoformat()}"
            f" ~ {snapshot.measurement_window_end.isoformat()}."
        )

    return DisclosureBlock(
        scope_ko=("; ".join(scope_parts) or "측정 범위가 기록되지 않았습니다.") + window,
        measured_at_ko="; ".join(measured_parts) or "측정 시점이 기록되지 않았습니다.",
        methodology_ko=snapshot.methodology_summary_ko()
        or "채점 명세가 기록되지 않았습니다.",
        coverage_ko="; ".join(coverage_parts) or "측정 범위 값이 없습니다.",
        confidence_ko="; ".join(confidence_parts) or "신뢰도 값이 없습니다.",
        rank_prediction_notice_ko=snapshot.disclosures_ko[0]
        if snapshot.disclosures_ko
        else "",
        lines_ko=list(snapshot.disclosures_ko),
    )


# --------------------------------------------------------------------------- #
# Executive
# --------------------------------------------------------------------------- #


def _status_ko(snapshot: ReportSnapshot) -> str:
    parts: list[str] = []
    for domain in snapshot.domains:
        value = snapshot.metric(domain.overall_metric_key).value
        band = f" ({domain.band_label_ko})" if domain.band_label_ko else ""
        parts.append(f"{domain.name_ko} {value.display_with_unit()}{band}")
    blocked = [
        gate.label_ko for domain in snapshot.domains for gate in domain.gates
    ]
    line = ", ".join(parts) if parts else "채점된 영역이 없습니다."
    if blocked:
        line += ". 노출 상태: " + ", ".join(dict.fromkeys(blocked))
    return line


def _top_actions(snapshot: ReportSnapshot, limit: int = 5) -> list[ActionItem]:
    ordered = sorted(
        snapshot.issues,
        key=lambda issue: (_SEVERITY_ORDER.get(issue.severity, 9), issue.check_id),
    )
    return [
        ActionItem(
            rank=index,
            title_ko=issue.title_ko,
            why_ko=issue.business_impact_ko or issue.summary_ko,
            owner_ko=_OWNER_KO.get(issue.remediation_owner, issue.remediation_owner),
            severity=issue.severity,
            domain=issue.domain,
        )
        for index, issue in enumerate(ordered[:limit], start=1)
    ]


def _changes_ko(snapshot: ReportSnapshot) -> list[str]:
    if snapshot.previous is None:
        return [
            "이전 버전이 없어 비교할 변화가 없습니다. 이번이 최초 발행본입니다."
        ]
    if not snapshot.changes:
        return ["이전 버전과 같은 지표가 없어 변화를 계산하지 못했습니다."]

    lines: list[str] = []
    for change in snapshot.changes:
        if change.delta.status is not ValueStatus.MEASURED:
            lines.append(f"{change.label_ko}: {change.delta.display_with_reason()}")
            continue
        arrow = {"UP": "상승", "DOWN": "하락", "FLAT": "변화 없음"}[change.direction]
        lines.append(
            f"{change.label_ko}: {change.previous.display_with_unit()} → "
            f"{change.current.display_with_unit()} ({change.delta.display_with_unit()}, {arrow})"
        )
    return lines


def executive_view(snapshot: ReportSnapshot) -> ExecutiveView:
    headline = [row for row in snapshot.metrics if row.section == SECTION_OVERALL]
    gaps = [
        snapshot.metric(comparison.gap_metric_key) for comparison in snapshot.competitors
    ]
    disclosure = _disclosure(snapshot)
    return ExecutiveView(
        audience="BUSINESS",
        audience_ko=AUDIENCE_KO["BUSINESS"],
        title_ko=f"{snapshot.report_title_ko} — 경영진 요약",
        summary_ko=" ".join(
            domain.summary_ko for domain in snapshot.domains if domain.summary_ko
        ),
        status_ko=_status_ko(snapshot),
        headline=headline,
        competitive_gap=gaps,
        top_actions=_top_actions(snapshot),
        changes_ko=_changes_ko(snapshot),
        changes=list(snapshot.changes),
        metrics=[*headline, *gaps],
        disclosure=disclosure,
    )


# --------------------------------------------------------------------------- #
# Marketing
# --------------------------------------------------------------------------- #


def marketing_view(snapshot: ReportSnapshot) -> MarketingView:
    change_by_key = {change.metric_key: change for change in snapshot.changes}

    tables: list[CategoryTable] = []
    for domain in snapshot.domains:
        rows = [
            CategoryTableRow(
                category_id=category.category_id,
                name_ko=category.name_ko,
                weight=category.weight,
                metric_key=category.metric_key,
                value=snapshot.metric(category.metric_key).value,
                coverage=category.coverage,
                confidence=category.confidence,
                change=(
                    change_by_key[category.metric_key].delta
                    if category.metric_key in change_by_key
                    else None
                ),
            )
            for category in domain.categories
        ]
        tables.append(
            CategoryTable(
                domain=domain.key,
                name_ko=domain.name_ko,
                overall_metric_key=domain.overall_metric_key,
                overall=snapshot.metric(domain.overall_metric_key).value,
                rows=rows,
            )
        )

    keyword_rows = [
        KeywordRow(
            keyword=keyword.keyword,
            monthly_searches=snapshot.metric(keyword.demand_metric_key).value,
            opportunity=snapshot.metric(keyword.opportunity_metric_key).value,
            note_ko=keyword.note_ko,
        )
        for keyword in snapshot.keywords
    ]

    competitor_rows = [
        CompetitorRow(
            slug=comparison.slug,
            label_ko=comparison.label_ko,
            domain=comparison.domain,
            ours=snapshot.metric(comparison.ours_metric_key).value,
            theirs=snapshot.metric(comparison.theirs_metric_key).value,
            gap=snapshot.metric(comparison.gap_metric_key).value,
            is_comparable=comparison.is_comparable,
            conditions_note_ko=_conditions_note_ko(
                comparison.is_comparable, comparison.differences
            ),
        )
        for comparison in snapshot.competitors
    ]

    shown = [
        row
        for row in snapshot.metrics
        if row.section
        in {SECTION_OVERALL, SECTION_CATEGORY, SECTION_KEYWORD, SECTION_COMPETITOR}
    ]

    return MarketingView(
        audience="MARKETING",
        audience_ko=AUDIENCE_KO["MARKETING"],
        title_ko=f"{snapshot.report_title_ko} — 마케팅 상세",
        summary_ko="카테고리별 점수, 변화, 키워드 수요, 경쟁사 격차입니다.",
        category_tables=tables,
        trends=list(snapshot.changes),
        keyword_rows=keyword_rows,
        competitor_rows=competitor_rows,
        metrics=shown,
        disclosure=_disclosure(snapshot),
    )


def _conditions_note_ko(is_comparable: bool, differences: list[dict[str, object]]) -> str:
    if not differences:
        return "두 측정의 조건이 동일합니다."
    lines = [str(difference.get("explanation_ko", "")) for difference in differences]
    prefix = (
        "조건 차이가 있으나 비교 가능 범위입니다: "
        if is_comparable
        else "측정 조건이 달라 직접 비교할 수 없습니다: "
    )
    return prefix + " ".join(line for line in lines if line)


# --------------------------------------------------------------------------- #
# Developer
# --------------------------------------------------------------------------- #


def developer_view(snapshot: ReportSnapshot) -> DeveloperView:
    ordered = sorted(
        snapshot.issues,
        key=lambda issue: (_SEVERITY_ORDER.get(issue.severity, 9), issue.check_id),
    )
    work_items = [
        WorkItem(
            check_id=issue.check_id,
            domain=issue.domain,
            title_ko=issue.title_ko,
            summary_ko=issue.summary_ko,
            severity=issue.severity,
            owner_ko=_OWNER_KO.get(issue.remediation_owner, issue.remediation_owner),
            affected_urls=list(issue.affected_urls),
            evidence_ids=list(issue.evidence_ids),
            remediation_ko=issue.remediation_ko,
            fix_example=issue.fix_example,
            reverification_ko=issue.reverification_note_ko
            or "수정 후 같은 검사를 다시 실행해 결과를 대조하십시오.",
        )
        for issue in ordered
    ]

    unmeasured = [
        check
        for domain in snapshot.domains
        for check in domain.checks
        if check.status == "UNKNOWN"
    ]

    reverification = [item.reverification_ko for item in work_items]
    reverification.append(
        "재검증은 이 버전을 수정하지 않습니다. 재측정 결과는 새 리포트 버전으로 발행되며, "
        "이 버전의 숫자는 그대로 남습니다."
    )

    shown = [
        row for row in snapshot.metrics if row.section in {SECTION_OVERALL, SECTION_CATEGORY}
    ]

    return DeveloperView(
        audience="DEVELOPER",
        audience_ko=AUDIENCE_KO["DEVELOPER"],
        title_ko=f"{snapshot.report_title_ko} — 개발자 작업 목록",
        summary_ko="영향 URL, 근거 참조, 수정 예시, 재검증 절차입니다.",
        work_items=work_items,
        unmeasured_checks=unmeasured,
        evidence=list(snapshot.evidence),
        reverification_ko=reverification,
        metrics=shown,
        disclosure=_disclosure(snapshot),
    )


def build_views(snapshot: ReportSnapshot) -> ReportViews:
    """All three readings of one snapshot, built together so they cannot drift apart."""
    return ReportViews(
        snapshot=snapshot,
        executive=executive_view(snapshot),
        marketing=marketing_view(snapshot),
        developer=developer_view(snapshot),
    )
