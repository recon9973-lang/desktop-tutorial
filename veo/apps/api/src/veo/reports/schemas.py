"""Request and response models for ``/reports``.

Every value that crosses the wire is an **object**, never a bare number:

.. code-block:: json

    "SEO_READINESS.category.indexing": {
      "value": null,
      "display": "측정 불가",
      "status": "UNMEASURED",
      "status_ko": "측정 불가",
      "reason_ko": "Search Console 자격증명이 없어 색인 상태를 확인하지 못했습니다.",
      "source": "veo.seo.readiness 1.0.0"
    }

A client physically cannot render the figure without also holding the reason it is or is
not there. A bare ``0`` in JSON is indistinguishable from a suppressed value; this is not.
``display`` is the string every VEO surface prints — the HTML, the CSV and the XLSX carry
the same one, so a screenshot and a spreadsheet cannot disagree.

The creation request carries the finished diagnosis rather than a run id, because scan
runs are not persisted yet (see ``INTEGRATION_REQUEST.md`` #1). It converts to the same
:class:`~veo.reports.snapshot.DiagnosisInput` the service takes in process, so the wire
format and the in-process path freeze byte-identical snapshots.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from veo.collect.contract import EvidenceRecord, IssueDraft
from veo.compare.conditions import MeasurementConditions
from veo.db.models.analysis import ScanRun
from veo.db.models.observation import Report
from veo.reports.repository import StoredVersion
from veo.reports.service import CreatedVersion, LoadedReport
from veo.reports.snapshot import (
    ChangeSnapshot,
    CompetitorObservation,
    DiagnosisInput,
    DomainDiagnosis,
    KeywordDemand,
    MeasuredValue,
    MetricRow,
    ReportSnapshot,
    ValueStatus,
)
from veo.reports.views import BaseAudienceView, DisclosureBlock, ReportViews
from veo.scoring.models import ScoreResult

__all__ = [
    "ChangePayload",
    "CreateFromScanRequest",
    "CreateReportRequest",
    "CreateVersionRequest",
    "CreatedVersionPayload",
    "ReportSummaryPayload",
    "ReportVersionPayload",
    "ReportableRunPayload",
    "ValuePayload",
    "VersionSummaryPayload",
    "created_payload",
    "read_payload",
    "summary_payload",
]

_STRICT = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- #
# Shared value shape
# --------------------------------------------------------------------------- #


class ValuePayload(BaseModel):
    """A number, or an explicit statement that there is none."""

    model_config = _STRICT

    value: float | None = Field(
        default=None,
        description="측정된 숫자입니다. 측정하지 못했거나 해당 없는 항목은 null이며, 0이 아닙니다.",
    )
    display: str = Field(description="모든 화면·내보내기가 동일하게 출력하는 표기입니다.")
    status: ValueStatus
    status_ko: str
    unit: str = ""
    reason_ko: str | None = None
    source: str

    @classmethod
    def of(cls, value: MeasuredValue) -> ValuePayload:
        return cls(
            value=value.value,
            display=value.display(),
            status=value.status,
            status_ko=value.status_ko,
            unit=value.unit,
            reason_ko=value.reason_ko,
            source=value.source,
        )

    def to_measured_value(self) -> MeasuredValue:
        return MeasuredValue(
            status=self.status,
            value=self.value,
            unit=self.unit,
            reason_ko=self.reason_ko,
            source=self.source,
        )


class MetricPayload(BaseModel):
    model_config = _STRICT

    metric_key: str
    label_ko: str
    section: str
    domain: str | None = None
    value: ValuePayload
    provenance_ref: str
    note_ko: str = ""
    evidence_ids: list[str] = Field(default_factory=list)

    @classmethod
    def of(cls, row: MetricRow) -> MetricPayload:
        return cls(
            metric_key=row.metric_key,
            label_ko=row.label_ko,
            section=row.section,
            domain=row.domain,
            value=ValuePayload.of(row.value),
            provenance_ref=row.provenance_ref,
            note_ko=row.note_ko,
            evidence_ids=list(row.evidence_ids),
        )


class ChangePayload(BaseModel):
    model_config = _STRICT

    metric_key: str
    label_ko: str
    domain: str | None = None
    previous: ValuePayload
    current: ValuePayload
    delta: ValuePayload
    direction: str

    @classmethod
    def of(cls, change: ChangeSnapshot) -> ChangePayload:
        return cls(
            metric_key=change.metric_key,
            label_ko=change.label_ko,
            domain=change.domain,
            previous=ValuePayload.of(change.previous),
            current=ValuePayload.of(change.current),
            delta=ValuePayload.of(change.delta),
            direction=change.direction,
        )


class DisclosurePayload(BaseModel):
    model_config = _STRICT

    scope_ko: str
    measured_at_ko: str
    methodology_ko: str
    coverage_ko: str
    confidence_ko: str
    rank_prediction_notice_ko: str
    lines_ko: list[str] = Field(default_factory=list)

    @classmethod
    def of(cls, block: DisclosureBlock) -> DisclosurePayload:
        return cls(
            scope_ko=block.scope_ko,
            measured_at_ko=block.measured_at_ko,
            methodology_ko=block.methodology_ko,
            coverage_ko=block.coverage_ko,
            confidence_ko=block.confidence_ko,
            rank_prediction_notice_ko=block.rank_prediction_notice_ko,
            lines_ko=list(block.lines_ko),
        )


# --------------------------------------------------------------------------- #
# View payloads
# --------------------------------------------------------------------------- #


class ActionPayload(BaseModel):
    model_config = _STRICT

    rank: int
    title_ko: str
    why_ko: str
    owner_ko: str
    severity: str
    domain: str


class CategoryRowPayload(BaseModel):
    model_config = _STRICT

    category_id: str
    name_ko: str
    weight: float
    metric_key: str
    value: ValuePayload
    coverage: ValuePayload
    confidence: ValuePayload
    change: ValuePayload | None = None


class CategoryTablePayload(BaseModel):
    model_config = _STRICT

    domain: str
    name_ko: str
    overall_metric_key: str
    overall: ValuePayload
    rows: list[CategoryRowPayload] = Field(default_factory=list)


class KeywordRowPayload(BaseModel):
    model_config = _STRICT

    keyword: str
    monthly_searches: ValuePayload
    opportunity: ValuePayload
    note_ko: str = ""


class CompetitorRowPayload(BaseModel):
    model_config = _STRICT

    slug: str
    label_ko: str
    domain: str
    ours: ValuePayload
    theirs: ValuePayload
    gap: ValuePayload
    is_comparable: bool
    conditions_note_ko: str


class WorkItemPayload(BaseModel):
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


class CheckPayload(BaseModel):
    model_config = _STRICT

    check_id: str
    title_ko: str
    domain: str
    category_id: str | None = None
    status: str
    status_ko: str
    reason_ko: str | None = None


class EvidenceRefPayload(BaseModel):
    """A reference to raw material. ``excerpt`` is null without ``evidence:read``."""

    model_config = _STRICT

    evidence_id: str
    kind: str
    domain: str
    url: str | None = None
    collected_at: datetime
    content_hash: str
    excerpt: str | None = None
    excerpt_redacted: bool = False


class AudienceViewPayload(BaseModel):
    """One reading of the snapshot. The three share a shape so a client can diff them."""

    model_config = _STRICT

    audience: str
    audience_ko: str
    title_ko: str
    summary_ko: str
    numbers: dict[str, ValuePayload] = Field(default_factory=dict)
    metrics: list[MetricPayload] = Field(default_factory=list)
    disclosure: DisclosurePayload
    status_ko: str | None = None
    top_actions: list[ActionPayload] = Field(default_factory=list)
    changes_ko: list[str] = Field(default_factory=list)
    category_tables: list[CategoryTablePayload] = Field(default_factory=list)
    keyword_rows: list[KeywordRowPayload] = Field(default_factory=list)
    competitor_rows: list[CompetitorRowPayload] = Field(default_factory=list)
    work_items: list[WorkItemPayload] = Field(default_factory=list)
    unmeasured_checks: list[CheckPayload] = Field(default_factory=list)
    evidence: list[EvidenceRefPayload] = Field(default_factory=list)
    reverification_ko: list[str] = Field(default_factory=list)


class ViewsPayload(BaseModel):
    model_config = _STRICT

    executive: AudienceViewPayload
    marketing: AudienceViewPayload
    developer: AudienceViewPayload


def _base_view_payload(view: BaseAudienceView) -> dict[str, Any]:
    return {
        "audience": view.audience,
        "audience_ko": view.audience_ko,
        "title_ko": view.title_ko,
        "summary_ko": view.summary_ko,
        "numbers": {key: ValuePayload.of(value) for key, value in view.numbers.items()},
        "metrics": [MetricPayload.of(row) for row in view.metrics],
        "disclosure": DisclosurePayload.of(view.disclosure),
    }


def _views_payload(views: ReportViews) -> ViewsPayload:
    executive = AudienceViewPayload(
        **_base_view_payload(views.executive),
        status_ko=views.executive.status_ko,
        top_actions=[
            ActionPayload(
                rank=action.rank,
                title_ko=action.title_ko,
                why_ko=action.why_ko,
                owner_ko=action.owner_ko,
                severity=action.severity,
                domain=action.domain,
            )
            for action in views.executive.top_actions
        ],
        changes_ko=list(views.executive.changes_ko),
    )

    marketing = AudienceViewPayload(
        **_base_view_payload(views.marketing),
        category_tables=[
            CategoryTablePayload(
                domain=table.domain,
                name_ko=table.name_ko,
                overall_metric_key=table.overall_metric_key,
                overall=ValuePayload.of(table.overall),
                rows=[
                    CategoryRowPayload(
                        category_id=row.category_id,
                        name_ko=row.name_ko,
                        weight=row.weight,
                        metric_key=row.metric_key,
                        value=ValuePayload.of(row.value),
                        coverage=ValuePayload.of(row.coverage),
                        confidence=ValuePayload.of(row.confidence),
                        change=None if row.change is None else ValuePayload.of(row.change),
                    )
                    for row in table.rows
                ],
            )
            for table in views.marketing.category_tables
        ],
        keyword_rows=[
            KeywordRowPayload(
                keyword=row.keyword,
                monthly_searches=ValuePayload.of(row.monthly_searches),
                opportunity=ValuePayload.of(row.opportunity),
                note_ko=row.note_ko,
            )
            for row in views.marketing.keyword_rows
        ],
        competitor_rows=[
            CompetitorRowPayload(
                slug=row.slug,
                label_ko=row.label_ko,
                domain=row.domain,
                ours=ValuePayload.of(row.ours),
                theirs=ValuePayload.of(row.theirs),
                gap=ValuePayload.of(row.gap),
                is_comparable=row.is_comparable,
                conditions_note_ko=row.conditions_note_ko,
            )
            for row in views.marketing.competitor_rows
        ],
    )

    developer = AudienceViewPayload(
        **_base_view_payload(views.developer),
        work_items=[
            WorkItemPayload(
                check_id=item.check_id,
                domain=item.domain,
                title_ko=item.title_ko,
                summary_ko=item.summary_ko,
                severity=item.severity,
                owner_ko=item.owner_ko,
                affected_urls=list(item.affected_urls),
                evidence_ids=list(item.evidence_ids),
                remediation_ko=item.remediation_ko,
                fix_example=item.fix_example,
                reverification_ko=item.reverification_ko,
            )
            for item in views.developer.work_items
        ],
        unmeasured_checks=[
            CheckPayload(
                check_id=check.check_id,
                title_ko=check.title_ko,
                domain=check.domain,
                category_id=check.category_id,
                status=check.status,
                status_ko=check.status_ko,
                reason_ko=check.reason_ko,
            )
            for check in views.developer.unmeasured_checks
        ],
        evidence=[
            EvidenceRefPayload(
                evidence_id=record.evidence_id,
                kind=record.kind,
                domain=record.domain,
                url=record.url,
                collected_at=record.collected_at,
                content_hash=record.content_hash,
                excerpt=record.excerpt,
                excerpt_redacted=record.excerpt_redacted,
            )
            for record in views.developer.evidence
        ],
        reverification_ko=list(views.developer.reverification_ko),
    )

    return ViewsPayload(executive=executive, marketing=marketing, developer=developer)


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #


class ConditionsPayload(BaseModel):
    """What a measurement was measured under. Without it a score has no unit."""

    model_config = _STRICT

    spec_id: str
    spec_version: str
    spec_checksum: str
    collector_version: str
    pages_examined: int = Field(ge=0)
    locale: str
    device: str
    renderer: str
    enabled_providers: list[str] = Field(default_factory=list)
    measured_at: datetime

    @classmethod
    def of(cls, conditions: MeasurementConditions) -> ConditionsPayload:
        return cls.model_validate(conditions.as_dict())

    def to_conditions(self) -> MeasurementConditions:
        return MeasurementConditions(
            spec_id=self.spec_id,
            spec_version=self.spec_version,
            spec_checksum=self.spec_checksum,
            collector_version=self.collector_version,
            pages_examined=self.pages_examined,
            locale=self.locale,
            device=self.device,
            renderer=self.renderer,
            enabled_providers=tuple(self.enabled_providers),
            measured_at=self.measured_at,
        )


class IssuePayload(BaseModel):
    model_config = _STRICT

    check_id: str
    title_ko: str
    summary_ko: str
    affected_urls: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    remediation_ko: str
    remediation_owner: str
    business_impact_ko: str = ""
    fix_example: str | None = None
    reverification_note_ko: str = ""

    @classmethod
    def of(cls, issue: IssueDraft) -> IssuePayload:
        return cls(
            check_id=issue.check_id,
            title_ko=issue.title_ko,
            summary_ko=issue.summary_ko,
            affected_urls=list(issue.affected_urls),
            evidence_ids=list(issue.evidence_ids),
            remediation_ko=issue.remediation_ko,
            remediation_owner=issue.remediation_owner,
            business_impact_ko=issue.business_impact_ko,
            fix_example=issue.fix_example,
            reverification_note_ko=issue.reverification_note_ko,
        )

    def to_issue(self) -> IssueDraft:
        return IssueDraft(
            check_id=self.check_id,
            title_ko=self.title_ko,
            summary_ko=self.summary_ko,
            affected_urls=tuple(self.affected_urls),
            evidence_ids=tuple(self.evidence_ids),
            remediation_ko=self.remediation_ko,
            remediation_owner=self.remediation_owner,
            business_impact_ko=self.business_impact_ko,
            fix_example=self.fix_example,
            reverification_note_ko=self.reverification_note_ko,
        )


class EvidencePayload(BaseModel):
    model_config = _STRICT

    evidence_id: str
    kind: str
    url: str | None = None
    collected_at: datetime
    content_hash: str
    excerpt: str = ""
    storage_key: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def of(cls, record: EvidenceRecord) -> EvidencePayload:
        return cls(
            evidence_id=record.evidence_id,
            kind=record.kind,
            url=record.url,
            collected_at=record.collected_at,
            content_hash=record.content_hash,
            excerpt=record.excerpt,
            storage_key=record.storage_key,
            detail=dict(record.detail),
        )

    def to_record(self) -> EvidenceRecord:
        return EvidenceRecord(
            evidence_id=self.evidence_id,
            kind=self.kind,
            url=self.url,
            collected_at=self.collected_at,
            content_hash=self.content_hash,
            excerpt=self.excerpt,
            storage_key=self.storage_key,
            detail=dict(self.detail),
        )


class DomainPayload(BaseModel):
    model_config = _STRICT

    key: str
    name_ko: str
    score: ScoreResult
    conditions: ConditionsPayload
    summary_ko: str = ""
    band_label_ko: str | None = None
    issues: list[IssuePayload] = Field(default_factory=list)
    evidence: list[EvidencePayload] = Field(default_factory=list)
    run_ids: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)

    @classmethod
    def of(cls, domain: DomainDiagnosis) -> DomainPayload:
        return cls(
            key=domain.key,
            name_ko=domain.name_ko,
            score=domain.score,
            conditions=ConditionsPayload.of(domain.conditions),
            summary_ko=domain.summary_ko,
            band_label_ko=domain.band_label_ko,
            issues=[IssuePayload.of(issue) for issue in domain.issues],
            evidence=[EvidencePayload.of(record) for record in domain.evidence],
            run_ids=list(domain.run_ids),
            data_sources=list(domain.data_sources),
        )

    def to_domain(self) -> DomainDiagnosis:
        return DomainDiagnosis(
            key=self.key,
            name_ko=self.name_ko,
            score=self.score,
            conditions=self.conditions.to_conditions(),
            summary_ko=self.summary_ko,
            issues=tuple(issue.to_issue() for issue in self.issues),
            evidence=tuple(record.to_record() for record in self.evidence),
            band_label_ko=self.band_label_ko,
            run_ids=tuple(self.run_ids),
            data_sources=tuple(self.data_sources),
        )


class KeywordPayload(BaseModel):
    model_config = _STRICT

    keyword: str
    monthly_searches: ValuePayload
    opportunity: ValuePayload
    note_ko: str = ""

    @classmethod
    def of(cls, demand: KeywordDemand) -> KeywordPayload:
        return cls(
            keyword=demand.keyword,
            monthly_searches=ValuePayload.of(demand.monthly_searches),
            opportunity=ValuePayload.of(demand.opportunity),
            note_ko=demand.note_ko,
        )

    def to_demand(self) -> KeywordDemand:
        return KeywordDemand(
            keyword=self.keyword,
            monthly_searches=self.monthly_searches.to_measured_value(),
            opportunity=self.opportunity.to_measured_value(),
            note_ko=self.note_ko,
        )


class CompetitorPayload(BaseModel):
    model_config = _STRICT

    label: str
    slug: str
    domain_key: str
    theirs: ValuePayload
    their_conditions: ConditionsPayload
    note_ko: str = ""

    @classmethod
    def of(cls, observation: CompetitorObservation) -> CompetitorPayload:
        return cls(
            label=observation.label,
            slug=observation.slug,
            domain_key=observation.domain_key,
            theirs=ValuePayload.of(observation.theirs),
            their_conditions=ConditionsPayload.of(observation.their_conditions),
            note_ko=observation.note_ko,
        )

    def to_observation(self) -> CompetitorObservation:
        return CompetitorObservation(
            label=self.label,
            slug=self.slug,
            domain_key=self.domain_key,
            theirs=self.theirs.to_measured_value(),
            their_conditions=self.their_conditions.to_conditions(),
            note_ko=self.note_ko,
        )


class CreateVersionRequest(BaseModel):
    """A completed diagnosis, ready to be frozen."""

    model_config = _STRICT

    title: str = Field(min_length=1, max_length=255)
    audience: Literal["BUSINESS", "MARKETING", "DEVELOPER"] = "BUSINESS"
    generated_at: datetime | None = None
    measurement_window_start: datetime | None = None
    measurement_window_end: datetime | None = None
    domains: list[DomainPayload] = Field(min_length=1)
    keywords: list[KeywordPayload] = Field(default_factory=list)
    competitors: list[CompetitorPayload] = Field(default_factory=list)
    extra_disclosures_ko: list[str] = Field(default_factory=list)

    def to_diagnosis(self) -> DiagnosisInput:
        return DiagnosisInput(
            title_ko=self.title,
            audience=self.audience,
            generated_at=self.generated_at or datetime.now(UTC),
            measurement_window_start=self.measurement_window_start,
            measurement_window_end=self.measurement_window_end,
            domains=tuple(domain.to_domain() for domain in self.domains),
            keywords=tuple(keyword.to_demand() for keyword in self.keywords),
            competitors=tuple(row.to_observation() for row in self.competitors),
            extra_disclosures_ko=tuple(self.extra_disclosures_ko),
        )

    @classmethod
    def from_diagnosis(cls, diagnosis: DiagnosisInput) -> CreateVersionRequest:
        return cls(
            title=diagnosis.title_ko,
            audience=diagnosis.audience,  # type: ignore[arg-type]
            generated_at=diagnosis.generated_at,
            measurement_window_start=diagnosis.measurement_window_start,
            measurement_window_end=diagnosis.measurement_window_end,
            domains=[DomainPayload.of(domain) for domain in diagnosis.domains],
            keywords=[KeywordPayload.of(demand) for demand in diagnosis.keywords],
            competitors=[
                CompetitorPayload.of(observation) for observation in diagnosis.competitors
            ],
            extra_disclosures_ko=list(diagnosis.extra_disclosures_ko),
        )


class CreateReportRequest(CreateVersionRequest):
    """The same diagnosis, plus the project the new report belongs to."""

    project_id: uuid.UUID

    @classmethod
    def from_diagnosis(  # type: ignore[override]
        cls, project_id: uuid.UUID, diagnosis: DiagnosisInput
    ) -> CreateReportRequest:
        base = CreateVersionRequest.from_diagnosis(diagnosis)
        return cls(project_id=project_id, **base.model_dump())


# --------------------------------------------------------------------------- #
# Responses
# --------------------------------------------------------------------------- #


class CreateFromScanRequest(BaseModel):
    """저장된 진단에서 리포트를 만든다.

    **여기에 숫자가 없는 것이 요점이다.** 제목과 어느 실행인지만 받는다. 점수·판정·
    근거·측정 조건은 그 실행이 남긴 것을 읽는다. `CreateReportRequest` 는 진단 전체를
    본문으로 받는데, 그 경로로 들어온 값은 아무도 재지 않은 숫자일 수 있다.
    """

    model_config = _STRICT

    scan_run_id: uuid.UUID = Field(description="리포트로 만들 진단 실행 ID입니다.")
    title: str = Field(min_length=1, max_length=255)


class ReportSummaryPayload(BaseModel):
    """목록 한 줄."""

    model_config = _STRICT

    report_id: uuid.UUID
    project_id: uuid.UUID
    title: str
    audience: str
    created_at: datetime
    #: 최신 버전. 아직 한 번도 발행되지 않았으면 비어 있다 — 감추지 않는다.
    latest_version_number: int | None = None
    latest_content_hash: str | None = None
    latest_generated_at: datetime | None = None

    @classmethod
    def of(cls, report: Report, latest: StoredVersion | None) -> ReportSummaryPayload:
        return cls(
            report_id=report.id,
            project_id=report.project_id,
            title=report.title,
            audience=report.audience,
            created_at=report.created_at,
            latest_version_number=None if latest is None else latest.version_number,
            latest_content_hash=None if latest is None else latest.content_hash,
            latest_generated_at=None if latest is None else latest.generated_at,
        )


class ReportableRunPayload(BaseModel):
    """리포트로 만들 수 있는 진단 실행 하나."""

    model_config = _STRICT

    scan_run_id: uuid.UUID
    started_at: datetime | None = None
    status: str
    urls_collected: int

    @classmethod
    def of(cls, run: ScanRun) -> ReportableRunPayload:
        return cls(
            scan_run_id=run.id,
            started_at=run.started_at,
            status=run.status,
            urls_collected=run.urls_collected,
        )


class CreatedVersionPayload(BaseModel):
    model_config = _STRICT

    report_id: uuid.UUID
    project_id: uuid.UUID
    version_number: int
    content_hash: str
    title_ko: str
    audience: str
    generated_at: datetime
    spec_versions: dict[str, dict[str, str]]
    export_formats: list[str]


class VersionSummaryPayload(BaseModel):
    model_config = _STRICT

    report_id: uuid.UUID
    version_number: int
    content_hash: str
    title_ko: str
    audience: str
    generated_at: datetime
    measurement_window_start: datetime | None = None
    measurement_window_end: datetime | None = None
    spec_versions: dict[str, Any] = Field(default_factory=dict)
    export_formats: list[str] = Field(default_factory=list)


class ReportVersionPayload(BaseModel):
    model_config = _STRICT

    report_id: uuid.UUID
    project_id: uuid.UUID
    version_number: int
    content_hash: str
    title_ko: str
    audience: str
    generated_at: datetime
    measurement_window_start: datetime | None = None
    measurement_window_end: datetime | None = None
    evidence_included: bool
    spec_versions: dict[str, dict[str, str]]
    disclosures_ko: list[str] = Field(default_factory=list)
    metrics: list[MetricPayload] = Field(default_factory=list)
    changes: list[ChangePayload] = Field(default_factory=list)
    views: ViewsPayload


def created_payload(created: CreatedVersion) -> CreatedVersionPayload:
    return CreatedVersionPayload(
        report_id=created.report_id,
        project_id=created.project_id,
        version_number=created.version_number,
        content_hash=created.content_hash,
        title_ko=created.title_ko,
        audience=created.audience,
        generated_at=created.generated_at,
        spec_versions=created.scoring_versions,
        export_formats=list(created.export_formats),
    )


def summary_payload(stored: StoredVersion) -> VersionSummaryPayload:
    return VersionSummaryPayload(
        report_id=stored.report_id,
        version_number=stored.version_number,
        content_hash=stored.content_hash,
        title_ko=stored.title_ko,
        audience=stored.audience,
        generated_at=stored.generated_at,
        measurement_window_start=stored.measurement_window_start,
        measurement_window_end=stored.measurement_window_end,
        spec_versions=dict(stored.scoring_versions),
        export_formats=[str(item) for item in stored.export_formats],
    )


def read_payload(loaded: LoadedReport) -> ReportVersionPayload:
    snapshot: ReportSnapshot = loaded.snapshot
    return ReportVersionPayload(
        report_id=loaded.stored.report_id,
        project_id=loaded.stored.project_id,
        version_number=loaded.stored.version_number,
        content_hash=loaded.content_hash,
        title_ko=snapshot.report_title_ko,
        audience=loaded.stored.audience,
        generated_at=snapshot.generated_at,
        measurement_window_start=snapshot.measurement_window_start,
        measurement_window_end=snapshot.measurement_window_end,
        evidence_included=loaded.evidence_included,
        spec_versions=snapshot.scoring_versions(),
        disclosures_ko=list(snapshot.disclosures_ko),
        metrics=[MetricPayload.of(row) for row in snapshot.metrics],
        changes=[ChangePayload.of(change) for change in snapshot.changes],
        views=_views_payload(loaded.views),
    )
