"""Freezing a diagnosis into something that can still be cited in six months.

A VEO report is a **snapshot**, not a query. The number a client reads in a delivered
PDF and the number an analyst sees when they reopen "the report" have to be the same
number, and the only way to guarantee that is to stop recomputing: the diagnosis is
frozen once, hashed, and every later reading — three audiences, three file formats — is a
projection of that one frozen object. Re-running the analysis produces a *new version*.

Three rules are enforced here rather than left to the renderers:

**A value that was not measured says so.** :class:`MeasuredValue` cannot hold a number
and a "no data" status at the same time, and it cannot be built without a Korean reason
when there is no number. ``측정 불가`` and ``해당 없음`` are separate facts and both are
separate from ``0``.

**Every number carries its provenance.** Each :class:`MetricRow` points at a
:class:`Provenance` entry, and the provenance for a scored domain carries the
specification id, version and checksum plus the measurement conditions. A score rendered
without its methodology version is not defensible, so the model makes it impossible to
render one.

**A comparison shows the conditions it was measured under.** Two scores are only
subtracted when :mod:`veo.compare.conditions` says they may be. When they may not, the
gap is ``측정 불가`` with the blocking differences quoted — never a subtraction that looks
authoritative and means nothing.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from veo.collect.contract import EvidenceRecord, IssueDraft
from veo.compare.conditions import MeasurementConditions, describe_differences
from veo.scoring.models import CheckOutcome, CheckStatus, ScoreResult, ScoringSpec

__all__ = [
    "MEASURED_KO",
    "NOT_APPLICABLE_KO",
    "SNAPSHOT_FORMAT_VERSION",
    "UNMEASURED_KO",
    "CategorySnapshot",
    "ChangeSnapshot",
    "CheckSnapshot",
    "CompetitorObservation",
    "CompetitorSnapshot",
    "DiagnosisInput",
    "DomainDiagnosis",
    "DomainSnapshot",
    "EvidenceSnapshot",
    "IssueSnapshot",
    "KeywordDemand",
    "KeywordSnapshot",
    "MeasuredValue",
    "MetricRow",
    "PreviousVersionRef",
    "Provenance",
    "ReportSnapshot",
    "ReportTamperedError",
    "ValueStatus",
    "compute_content_hash",
    "freeze",
    "from_payload",
    "redact_evidence",
    "to_payload",
]

SNAPSHOT_FORMAT_VERSION: Final = "1.0.0"

UNMEASURED_KO: Final = "측정 불가"
NOT_APPLICABLE_KO: Final = "해당 없음"
MEASURED_KO: Final = "측정됨"

#: Provenance keys that are not a scoring domain.
KEYWORD_PROVENANCE: Final = "KEYWORD_DEMAND"

SECTION_OVERALL: Final = "종합"
SECTION_CATEGORY: Final = "카테고리"
SECTION_KEYWORD: Final = "키워드 수요"
SECTION_COMPETITOR: Final = "경쟁사 비교"

RANK_PREDICTION_NOTICE_KO: Final = (
    "준비도 점수는 검색 순위 예측이 아닙니다. 검색엔진과 답변엔진이 이 사이트를 "
    "발견·해석·인용할 수 있는 상태인지를 나타내는 값입니다."
)

_STRICT = ConfigDict(frozen=True, extra="forbid")


class ReportTamperedError(ValueError):
    """A stored payload does not match the content hash written with it."""


# --------------------------------------------------------------------------- #
# A single value
# --------------------------------------------------------------------------- #


class ValueStatus(StrEnum):
    """Why a number is, or is not, present.

    ``UNMEASURED`` and ``NOT_APPLICABLE`` are not degrees of the same thing. One says the
    check applied and VEO could not run it; the other says the check never applied. They
    are shown differently because the work they imply is different: chase a credential,
    or nothing at all.
    """

    MEASURED = "MEASURED"
    UNMEASURED = "UNMEASURED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


_STATUS_KO: Final[dict[ValueStatus, str]] = {
    ValueStatus.MEASURED: MEASURED_KO,
    ValueStatus.UNMEASURED: UNMEASURED_KO,
    ValueStatus.NOT_APPLICABLE: NOT_APPLICABLE_KO,
}


def _format_number(value: float, decimals: int) -> str:
    """Render a number without ever quietly losing part of it.

    ``decimals`` is a *preference*, not a truncation: if rounding to it would change the
    stored value the exact value is printed instead. A report that silently turned 61.25
    into 61.2 would make the export and the database disagree, which is the whole failure
    this module exists to prevent.
    """
    if round(value, decimals) == value:
        return f"{value:.{decimals}f}"
    return repr(value)


class MeasuredValue(BaseModel):
    """One number, or one honest statement that there is none."""

    model_config = _STRICT

    status: ValueStatus
    value: float | None = None
    unit: str = ""
    reason_ko: str | None = None
    source: str
    decimals: int = Field(default=1, ge=0, le=6)

    @model_validator(mode="after")
    def _validate(self) -> MeasuredValue:
        if self.status is ValueStatus.MEASURED:
            if self.value is None:
                raise ValueError("측정된 값에는 숫자가 있어야 합니다.")
            return self
        if self.value is not None:
            raise ValueError(
                f"{self.status.value} 상태에는 숫자를 담을 수 없습니다. 0으로 보이게 됩니다."
            )
        if not (self.reason_ko or "").strip():
            raise ValueError(
                "측정하지 못한 값에는 사유가 함께 있어야 합니다. 사유 없는 공백은 0과 "
                "구분되지 않습니다."
            )
        return self

    @classmethod
    def measured(
        cls, value: float, *, source: str, unit: str = "점", decimals: int = 1
    ) -> MeasuredValue:
        return cls(
            status=ValueStatus.MEASURED,
            value=float(value),
            unit=unit,
            source=source,
            decimals=decimals,
        )

    @classmethod
    def unmeasured(
        cls, reason_ko: str, *, source: str, unit: str = "점", decimals: int = 1
    ) -> MeasuredValue:
        return cls(
            status=ValueStatus.UNMEASURED,
            reason_ko=reason_ko,
            unit=unit,
            source=source,
            decimals=decimals,
        )

    @classmethod
    def not_applicable(
        cls, reason_ko: str, *, source: str, unit: str = "점", decimals: int = 1
    ) -> MeasuredValue:
        return cls(
            status=ValueStatus.NOT_APPLICABLE,
            reason_ko=reason_ko,
            unit=unit,
            source=source,
            decimals=decimals,
        )

    @property
    def status_ko(self) -> str:
        return _STATUS_KO[self.status]

    def display(self) -> str:
        """The one string every audience and every format prints for this value."""
        if self.status is not ValueStatus.MEASURED or self.value is None:
            return _STATUS_KO[self.status]
        return _format_number(self.value, self.decimals)

    def display_with_unit(self) -> str:
        if self.status is not ValueStatus.MEASURED:
            return self.display()
        return f"{self.display()}{self.unit}" if self.unit else self.display()

    def display_with_reason(self) -> str:
        if self.status is ValueStatus.MEASURED:
            return self.display_with_unit()
        return f"{self.display()} — {self.reason_ko}"


# --------------------------------------------------------------------------- #
# Provenance
# --------------------------------------------------------------------------- #


class Provenance(BaseModel):
    """Where a family of numbers came from, and under what conditions."""

    model_config = _STRICT

    key: str
    label_ko: str
    methodology_ko: str
    data_sources: list[str] = Field(default_factory=list)
    spec_id: str | None = None
    spec_version: str | None = None
    spec_checksum: str | None = None
    collector_version: str | None = None
    measured_at: datetime | None = None
    pages_examined: int | None = None
    locale: str | None = None
    device: str | None = None
    renderer: str | None = None
    enabled_providers: list[str] = Field(default_factory=list)
    coverage: MeasuredValue | None = None
    confidence: MeasuredValue | None = None
    conditions: dict[str, Any] | None = None

    @property
    def has_spec(self) -> bool:
        return bool(self.spec_id and self.spec_version and self.spec_checksum)

    def methodology_line_ko(self) -> str:
        if not self.has_spec:
            return f"{self.label_ko}: {self.methodology_ko}"
        return (
            f"{self.label_ko}: {self.spec_id} {self.spec_version} "
            f"(체크섬 {self.spec_checksum})"
        )

    def measurement_conditions(self) -> MeasurementConditions | None:
        if self.conditions is None:
            return None
        return MeasurementConditions.from_dict(self.conditions)


# --------------------------------------------------------------------------- #
# The flat metric index — the single copy of every number
# --------------------------------------------------------------------------- #


class MetricRow(BaseModel):
    """One number in the report, held exactly once.

    Views and renderers select from this list; none of them holds a second copy. That is
    the mechanism behind "the same number appears identically everywhere" — there is only
    one number to appear.
    """

    model_config = _STRICT

    metric_key: str
    label_ko: str
    section: str
    domain: str | None = None
    value: MeasuredValue
    provenance_ref: str
    note_ko: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Structure around the numbers
# --------------------------------------------------------------------------- #


class CategorySnapshot(BaseModel):
    model_config = _STRICT

    category_id: str
    name_ko: str
    name_en: str
    weight: float
    status: str
    metric_key: str
    coverage: MeasuredValue
    confidence: MeasuredValue
    failing_check_ids: list[str] = Field(default_factory=list)
    unknown_check_ids: list[str] = Field(default_factory=list)
    not_applicable_check_ids: list[str] = Field(default_factory=list)


class CheckSnapshot(BaseModel):
    model_config = _STRICT

    check_id: str
    title_ko: str
    domain: str
    category_id: str | None
    status: str
    status_ko: str
    reason_ko: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class IssueSnapshot(BaseModel):
    model_config = _STRICT

    check_id: str
    domain: str
    title_ko: str
    summary_ko: str
    severity: str
    affected_urls: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    remediation_ko: str
    remediation_owner: str
    business_impact_ko: str = ""
    fix_example: str | None = None
    reverification_note_ko: str = ""


class EvidenceSnapshot(BaseModel):
    """A reference to raw material. The excerpt is the gated part, never the reference."""

    model_config = _STRICT

    evidence_id: str
    kind: str
    domain: str
    url: str | None = None
    collected_at: datetime
    content_hash: str
    excerpt: str | None = None
    excerpt_redacted: bool = False
    storage_key: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


class GateSnapshot(BaseModel):
    model_config = _STRICT

    gate_id: str
    status_code: str
    label_ko: str
    description_ko: str | None = None
    triggered_by: list[str] = Field(default_factory=list)


class CapSnapshot(BaseModel):
    model_config = _STRICT

    cap_id: str
    max_overall_score: float
    reason_ko: str
    release_condition_ko: str
    triggered_by: list[str] = Field(default_factory=list)


class DomainSnapshot(BaseModel):
    model_config = _STRICT

    key: str
    name_ko: str
    status: str
    band_id: str | None = None
    band_label_ko: str | None = None
    summary_ko: str = ""
    overall_metric_key: str
    coverage_metric_key: str
    confidence_metric_key: str
    categories: list[CategorySnapshot] = Field(default_factory=list)
    checks: list[CheckSnapshot] = Field(default_factory=list)
    gates: list[GateSnapshot] = Field(default_factory=list)
    applied_caps: list[CapSnapshot] = Field(default_factory=list)
    trace: dict[str, Any] = Field(default_factory=dict)
    run_ids: list[str] = Field(default_factory=list)


class KeywordSnapshot(BaseModel):
    model_config = _STRICT

    keyword: str
    demand_metric_key: str
    opportunity_metric_key: str
    note_ko: str = ""


class CompetitorSnapshot(BaseModel):
    """One side-by-side comparison, with the conditions that made it legal or not."""

    model_config = _STRICT

    slug: str
    label_ko: str
    domain: str
    ours_metric_key: str
    theirs_metric_key: str
    gap_metric_key: str
    is_comparable: bool
    our_conditions: dict[str, Any]
    their_conditions: dict[str, Any]
    differences: list[dict[str, Any]] = Field(default_factory=list)
    note_ko: str = ""


class ChangeSnapshot(BaseModel):
    model_config = _STRICT

    metric_key: str
    label_ko: str
    domain: str | None
    previous: MeasuredValue
    current: MeasuredValue
    delta: MeasuredValue
    direction: Literal["UP", "DOWN", "FLAT", "UNKNOWN"]
    note_ko: str = ""


class PreviousVersionRef(BaseModel):
    model_config = _STRICT

    version_number: int | None = None
    generated_at: datetime
    content_hash: str | None = None


# --------------------------------------------------------------------------- #
# The snapshot
# --------------------------------------------------------------------------- #


class ReportSnapshot(BaseModel):
    """The frozen document. Everything downstream is a projection of this."""

    model_config = _STRICT

    format_version: str = SNAPSHOT_FORMAT_VERSION
    report_title_ko: str
    audience: str
    generated_at: datetime
    measurement_window_start: datetime | None = None
    measurement_window_end: datetime | None = None
    included_run_ids: list[str] = Field(default_factory=list)
    provenance: dict[str, Provenance] = Field(default_factory=dict)
    domains: list[DomainSnapshot] = Field(default_factory=list)
    metrics: list[MetricRow] = Field(default_factory=list)
    issues: list[IssueSnapshot] = Field(default_factory=list)
    evidence: list[EvidenceSnapshot] = Field(default_factory=list)
    keywords: list[KeywordSnapshot] = Field(default_factory=list)
    competitors: list[CompetitorSnapshot] = Field(default_factory=list)
    changes: list[ChangeSnapshot] = Field(default_factory=list)
    previous: PreviousVersionRef | None = None
    disclosures_ko: list[str] = Field(default_factory=list)

    def metric(self, metric_key: str) -> MetricRow:
        for row in self.metrics:
            if row.metric_key == metric_key:
                return row
        raise KeyError(metric_key)

    def metric_or_none(self, metric_key: str) -> MetricRow | None:
        try:
            return self.metric(metric_key)
        except KeyError:
            return None

    def metrics_in(self, *metric_keys: str) -> list[MetricRow]:
        wanted = set(metric_keys)
        return [row for row in self.metrics if row.metric_key in wanted]

    def domain(self, key: str) -> DomainSnapshot:
        for item in self.domains:
            if item.key == key:
                return item
        raise KeyError(key)

    def evidence_for(self, evidence_ids: Sequence[str]) -> list[EvidenceSnapshot]:
        wanted = set(evidence_ids)
        return [record for record in self.evidence if record.evidence_id in wanted]

    def methodology_summary_ko(self) -> str:
        """Every methodology this report used, named with its checksum.

        Written onto every exported row so that a spreadsheet cell lifted out of context
        still says which measurement produced it.
        """
        lines = [
            entry.methodology_line_ko()
            for entry in self.provenance.values()
            if entry.has_spec
        ]
        return " / ".join(sorted(set(lines)))

    def scoring_versions(self) -> dict[str, dict[str, str]]:
        return {
            key: {
                "spec_id": entry.spec_id or "",
                "version": entry.spec_version or "",
                "checksum": entry.spec_checksum or "",
            }
            for key, entry in self.provenance.items()
            if entry.has_spec
        }


# --------------------------------------------------------------------------- #
# Input
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class DomainDiagnosis:
    """One scored domain of a completed run.

    ``score``, ``issues`` and ``evidence`` are exactly what ``veo.seo.service`` and
    ``veo.geo.service`` return; ``conditions`` is what ``veo.compare.conditions`` needs to
    decide whether this measurement may sit beside another one.
    """

    key: str
    name_ko: str
    score: ScoreResult
    conditions: MeasurementConditions
    summary_ko: str = ""
    issues: tuple[IssueDraft, ...] = ()
    evidence: tuple[EvidenceRecord, ...] = ()
    spec: ScoringSpec | None = None
    band_label_ko: str | None = None
    run_ids: tuple[str, ...] = ()
    data_sources: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class KeywordDemand:
    keyword: str
    monthly_searches: MeasuredValue
    opportunity: MeasuredValue
    note_ko: str = ""


@dataclass(frozen=True, slots=True)
class CompetitorObservation:
    """A competitor's score and the conditions it was produced under.

    Only ``theirs`` is supplied. "Ours" is read from the domain that is already in this
    report, so a comparison can never quote a figure for us that the report itself does
    not contain.
    """

    label: str
    slug: str
    domain_key: str
    theirs: MeasuredValue
    their_conditions: MeasurementConditions
    note_ko: str = ""


@dataclass(frozen=True, slots=True)
class DiagnosisInput:
    title_ko: str
    audience: str
    generated_at: datetime
    measurement_window_start: datetime | None = None
    measurement_window_end: datetime | None = None
    domains: tuple[DomainDiagnosis, ...] = ()
    keywords: tuple[KeywordDemand, ...] = ()
    competitors: tuple[CompetitorObservation, ...] = ()
    extra_disclosures_ko: tuple[str, ...] = field(default_factory=tuple)


# --------------------------------------------------------------------------- #
# Freezing
# --------------------------------------------------------------------------- #


def _percent(ratio: float) -> float:
    """Ratio to percentage, without the floating-point tail that ``* 100`` leaves."""
    return round(ratio * 100.0, 6)


def _reasons_for(outcomes: Mapping[str, CheckOutcome], check_ids: Sequence[str]) -> str:
    notes = [
        outcomes[check_id].note
        for check_id in check_ids
        if check_id in outcomes and outcomes[check_id].note
    ]
    if not notes:
        return "사유가 기록되지 않았습니다."
    seen: list[str] = []
    for note in notes:
        assert note is not None
        if note not in seen:
            seen.append(note)
    return " ".join(seen)


def _check_title(domain: DomainDiagnosis, check_id: str) -> str:
    if domain.spec is None:
        return check_id
    try:
        return domain.spec.check(check_id).title_ko
    except KeyError:
        return check_id


def _check_severity(domain: DomainDiagnosis, check_id: str) -> str:
    if domain.spec is None:
        return "UNKNOWN"
    try:
        return str(domain.spec.check(check_id).severity)
    except KeyError:
        return "UNKNOWN"


def _category_of(domain: DomainDiagnosis, check_id: str) -> str | None:
    for category in domain.score.categories:
        if check_id in (
            *category.applicable_check_ids,
            *category.not_applicable_check_ids,
            *category.unknown_check_ids,
        ):
            return category.category_id
    return None


_CHECK_STATUS_KO: Final[dict[str, str]] = {
    CheckStatus.PASS.value: "통과",
    CheckStatus.WARNING.value: "주의",
    CheckStatus.FAIL.value: "실패",
    CheckStatus.NOT_APPLICABLE.value: NOT_APPLICABLE_KO,
    CheckStatus.UNKNOWN.value: UNMEASURED_KO,
}


def _domain_provenance(domain: DomainDiagnosis) -> Provenance:
    conditions = domain.conditions
    source = f"{domain.score.spec_id} {domain.score.spec_version}"
    return Provenance(
        key=domain.key,
        label_ko=domain.name_ko,
        methodology_ko=(
            f"VEO-LAB이 발행한 {domain.score.spec_id} {domain.score.spec_version} 명세로 "
            "채점했습니다."
        ),
        data_sources=list(domain.data_sources),
        spec_id=domain.score.spec_id,
        spec_version=domain.score.spec_version,
        spec_checksum=domain.score.spec_checksum,
        collector_version=conditions.collector_version,
        measured_at=conditions.measured_at,
        pages_examined=conditions.pages_examined,
        locale=conditions.locale,
        device=conditions.device,
        renderer=conditions.renderer,
        enabled_providers=list(conditions.enabled_providers),
        coverage=MeasuredValue.measured(
            _percent(domain.score.coverage), source=source, unit="%", decimals=1
        ),
        confidence=MeasuredValue.measured(
            _percent(domain.score.confidence), source=source, unit="%", decimals=1
        ),
        conditions=conditions.as_dict(),
    )


def _competitor_provenance(observation: CompetitorObservation) -> Provenance:
    conditions = observation.their_conditions
    return Provenance(
        key=f"competitor:{observation.slug}",
        label_ko=f"{observation.label} 측정",
        methodology_ko=(
            f"{conditions.spec_id} {conditions.spec_version} 명세로 경쟁사를 별도 측정한 "
            "결과입니다."
        ),
        data_sources=["VEO_CRAWLER"],
        spec_id=conditions.spec_id,
        spec_version=conditions.spec_version,
        spec_checksum=conditions.spec_checksum,
        collector_version=conditions.collector_version,
        measured_at=conditions.measured_at,
        pages_examined=conditions.pages_examined,
        locale=conditions.locale,
        device=conditions.device,
        renderer=conditions.renderer,
        enabled_providers=list(conditions.enabled_providers),
        conditions=conditions.as_dict(),
    )


def _keyword_provenance() -> Provenance:
    return Provenance(
        key=KEYWORD_PROVENANCE,
        label_ko="키워드 수요",
        methodology_ko=(
            "외부 키워드 제공자가 보고한 값과 VEO가 계산한 기회 점수입니다. 준비도 채점 "
            "명세와는 별개의 출처이므로 점수와 같은 단위로 읽어서는 안 됩니다."
        ),
        data_sources=["NAVER_SEARCH_AD", "CALCULATED"],
    )


def _freeze_domain(
    domain: DomainDiagnosis, metrics: list[MetricRow]
) -> tuple[DomainSnapshot, list[IssueSnapshot], list[EvidenceSnapshot]]:
    score = domain.score
    source = f"{score.spec_id} {score.spec_version}"
    outcomes = {outcome.check_id: outcome for outcome in score.outcomes}

    overall_key = f"{domain.key}.overall"
    if score.overall_score is None:
        overall = MeasuredValue.unmeasured(
            "채점 가능한 검사 항목이 없어 종합 점수를 산출하지 못했습니다.",
            source=source,
        )
    else:
        overall = MeasuredValue.measured(score.overall_score, source=source)
    metrics.append(
        MetricRow(
            metric_key=overall_key,
            label_ko=f"{domain.name_ko} 종합 점수",
            section=SECTION_OVERALL,
            domain=domain.key,
            value=overall,
            provenance_ref=domain.key,
            note_ko=domain.summary_ko,
        )
    )

    before_key = f"{domain.key}.overall_before_caps"
    if score.overall_score_before_caps is None:
        before = MeasuredValue.unmeasured(
            "종합 점수를 산출하지 못해 상한 적용 전 값도 없습니다.", source=source
        )
    else:
        before = MeasuredValue.measured(score.overall_score_before_caps, source=source)
    metrics.append(
        MetricRow(
            metric_key=before_key,
            label_ko=f"{domain.name_ko} 상한 적용 전 점수",
            section=SECTION_OVERALL,
            domain=domain.key,
            value=before,
            provenance_ref=domain.key,
            note_ko=(
                "상한이 적용된 경우 종합 점수와 다릅니다."
                if score.applied_caps
                else "적용된 상한이 없어 종합 점수와 같습니다."
            ),
        )
    )

    coverage_key = f"{domain.key}.coverage"
    metrics.append(
        MetricRow(
            metric_key=coverage_key,
            label_ko=f"{domain.name_ko} 측정 범위",
            section=SECTION_OVERALL,
            domain=domain.key,
            value=MeasuredValue.measured(
                _percent(score.coverage), source=source, unit="%"
            ),
            provenance_ref=domain.key,
            note_ko="측정하지 못한 항목이 있으면 이 값이 낮아집니다. 점수는 깎이지 않습니다.",
        )
    )

    confidence_key = f"{domain.key}.confidence"
    metrics.append(
        MetricRow(
            metric_key=confidence_key,
            label_ko=f"{domain.name_ko} 신뢰도",
            section=SECTION_OVERALL,
            domain=domain.key,
            value=MeasuredValue.measured(
                _percent(score.confidence), source=source, unit="%"
            ),
            provenance_ref=domain.key,
            note_ko="근거의 직접성에 따라 결정됩니다.",
        )
    )

    categories: list[CategorySnapshot] = []
    for category in score.categories:
        metric_key = f"{domain.key}.category.{category.category_id}"
        if category.status == "SCORED" and category.score is not None:
            value = MeasuredValue.measured(category.score, source=source)
        elif category.status == "NOT_APPLICABLE":
            value = MeasuredValue.not_applicable(
                _reasons_for(outcomes, category.not_applicable_check_ids), source=source
            )
        else:
            value = MeasuredValue.unmeasured(
                _reasons_for(outcomes, category.unknown_check_ids), source=source
            )
        metrics.append(
            MetricRow(
                metric_key=metric_key,
                label_ko=f"{domain.name_ko} · {category.name_ko}",
                section=SECTION_CATEGORY,
                domain=domain.key,
                value=value,
                provenance_ref=domain.key,
                note_ko=f"가중치 {_format_number(category.weight, 1)}",
            )
        )
        categories.append(
            CategorySnapshot(
                category_id=category.category_id,
                name_ko=category.name_ko,
                name_en=category.name_en,
                weight=category.weight,
                status=category.status,
                metric_key=metric_key,
                coverage=MeasuredValue.measured(
                    _percent(category.coverage), source=source, unit="%"
                ),
                confidence=MeasuredValue.measured(
                    _percent(category.confidence), source=source, unit="%"
                ),
                failing_check_ids=list(category.failing_check_ids),
                unknown_check_ids=list(category.unknown_check_ids),
                not_applicable_check_ids=list(category.not_applicable_check_ids),
            )
        )

    checks = [
        CheckSnapshot(
            check_id=outcome.check_id,
            title_ko=_check_title(domain, outcome.check_id),
            domain=domain.key,
            category_id=_category_of(domain, outcome.check_id),
            status=outcome.status.value,
            status_ko=_CHECK_STATUS_KO[outcome.status.value],
            reason_ko=outcome.note,
            evidence_ids=list(outcome.evidence_ids),
        )
        for outcome in score.outcomes
    ]

    issues = [
        IssueSnapshot(
            check_id=issue.check_id,
            domain=domain.key,
            title_ko=issue.title_ko,
            summary_ko=issue.summary_ko,
            severity=_check_severity(domain, issue.check_id),
            affected_urls=list(issue.affected_urls),
            evidence_ids=list(issue.evidence_ids),
            remediation_ko=issue.remediation_ko,
            remediation_owner=issue.remediation_owner,
            business_impact_ko=issue.business_impact_ko,
            fix_example=issue.fix_example,
            reverification_note_ko=issue.reverification_note_ko,
        )
        for issue in domain.issues
    ]

    evidence = [
        EvidenceSnapshot(
            evidence_id=record.evidence_id,
            kind=record.kind,
            domain=domain.key,
            url=record.url,
            collected_at=record.collected_at,
            content_hash=record.content_hash,
            excerpt=record.excerpt,
            excerpt_redacted=False,
            storage_key=record.storage_key,
            detail=dict(record.detail),
        )
        for record in domain.evidence
    ]

    snapshot = DomainSnapshot(
        key=domain.key,
        name_ko=domain.name_ko,
        status=score.status,
        band_id=score.band_id,
        band_label_ko=domain.band_label_ko,
        summary_ko=domain.summary_ko,
        overall_metric_key=overall_key,
        coverage_metric_key=coverage_key,
        confidence_metric_key=confidence_key,
        categories=categories,
        checks=checks,
        gates=[
            GateSnapshot(
                gate_id=gate.gate_id,
                status_code=gate.status_code,
                label_ko=gate.label_ko,
                description_ko=gate.description_ko,
                triggered_by=list(gate.triggered_by),
            )
            for gate in score.gates
        ],
        applied_caps=[
            CapSnapshot(
                cap_id=cap.cap_id,
                max_overall_score=cap.max_overall_score,
                reason_ko=cap.reason_ko,
                release_condition_ko=cap.release_condition_ko,
                triggered_by=list(cap.triggered_by),
            )
            for cap in score.applied_caps
        ],
        trace=dict(score.trace),
        run_ids=list(domain.run_ids),
    )
    return snapshot, issues, evidence


def _freeze_competitor(
    observation: CompetitorObservation,
    domains: Mapping[str, DomainDiagnosis],
    metrics: list[MetricRow],
) -> CompetitorSnapshot | None:
    domain = domains.get(observation.domain_key)
    if domain is None:
        return None

    ours_key = f"{observation.domain_key}.overall"
    ours = next(row for row in metrics if row.metric_key == ours_key).value

    prefix = f"competitor.{observation.slug}.{observation.domain_key}"
    theirs_key = f"{prefix}.theirs"
    gap_key = f"{prefix}.gap"

    differences = describe_differences(domain.conditions, observation.their_conditions)
    blocking = [difference for difference in differences if difference.blocking]
    comparable = not blocking

    metrics.append(
        MetricRow(
            metric_key=theirs_key,
            label_ko=f"{observation.label} · {domain.name_ko} 점수",
            section=SECTION_COMPETITOR,
            domain=observation.domain_key,
            value=observation.theirs,
            provenance_ref=f"competitor:{observation.slug}",
            note_ko=observation.note_ko,
        )
    )

    source = "CALCULATED"
    if not comparable:
        reason = "측정 조건이 달라 두 점수를 뺄 수 없습니다. " + " ".join(
            difference.explanation_ko for difference in blocking
        )
        gap = MeasuredValue.unmeasured(reason, source=source)
    elif ours.status is not ValueStatus.MEASURED or observation.theirs.status is not (
        ValueStatus.MEASURED
    ):
        gap = MeasuredValue.unmeasured(
            "양쪽 중 한쪽의 점수가 측정되지 않아 격차를 계산할 수 없습니다.", source=source
        )
    else:
        assert ours.value is not None and observation.theirs.value is not None
        gap = MeasuredValue.measured(ours.value - observation.theirs.value, source=source)

    metrics.append(
        MetricRow(
            metric_key=gap_key,
            label_ko=f"{observation.label} 대비 격차 ({domain.name_ko})",
            section=SECTION_COMPETITOR,
            domain=observation.domain_key,
            value=gap,
            provenance_ref=observation.domain_key,
            note_ko="양수이면 우리가 높고, 음수이면 경쟁사가 높습니다.",
        )
    )

    return CompetitorSnapshot(
        slug=observation.slug,
        label_ko=observation.label,
        domain=observation.domain_key,
        ours_metric_key=ours_key,
        theirs_metric_key=theirs_key,
        gap_metric_key=gap_key,
        is_comparable=comparable,
        our_conditions=domain.conditions.as_dict(),
        their_conditions=observation.their_conditions.as_dict(),
        differences=[difference.as_dict() for difference in differences],
        note_ko=observation.note_ko,
    )


def _freeze_changes(
    current_metrics: Sequence[MetricRow],
    current_provenance: Mapping[str, Provenance],
    previous: ReportSnapshot,
) -> list[ChangeSnapshot]:
    """What moved since the previous version, and where the question is not askable."""
    changes: list[ChangeSnapshot] = []
    previous_by_key = {row.metric_key: row for row in previous.metrics}

    for row in current_metrics:
        if row.section not in {SECTION_OVERALL, SECTION_CATEGORY}:
            continue
        earlier = previous_by_key.get(row.metric_key)
        if earlier is None:
            continue

        blocking = _blocking_condition_differences(
            current_provenance.get(row.provenance_ref),
            previous.provenance.get(earlier.provenance_ref),
        )
        if blocking:
            delta = MeasuredValue.unmeasured(
                "이전 버전과 측정 조건이 달라 변화량을 계산할 수 없습니다. "
                + " ".join(blocking),
                source="CALCULATED",
                unit=row.value.unit,
            )
            direction: Literal["UP", "DOWN", "FLAT", "UNKNOWN"] = "UNKNOWN"
        elif (
            row.value.status is not ValueStatus.MEASURED
            or earlier.value.status is not ValueStatus.MEASURED
        ):
            delta = MeasuredValue.unmeasured(
                "두 버전 중 한쪽이 측정되지 않아 변화량을 계산할 수 없습니다.",
                source="CALCULATED",
                unit=row.value.unit,
            )
            direction = "UNKNOWN"
        else:
            assert row.value.value is not None and earlier.value.value is not None
            difference = round(row.value.value - earlier.value.value, 6)
            delta = MeasuredValue.measured(
                difference,
                source="CALCULATED",
                unit=row.value.unit,
                decimals=row.value.decimals,
            )
            direction = "FLAT" if difference == 0 else ("UP" if difference > 0 else "DOWN")

        changes.append(
            ChangeSnapshot(
                metric_key=row.metric_key,
                label_ko=row.label_ko,
                domain=row.domain,
                previous=earlier.value,
                current=row.value,
                delta=delta,
                direction=direction,
                note_ko="",
            )
        )
    return changes


def _blocking_condition_differences(
    current: Provenance | None, earlier: Provenance | None
) -> list[str]:
    if current is None or earlier is None:
        return []
    left = current.measurement_conditions()
    right = earlier.measurement_conditions()
    if left is None or right is None:
        return []
    return [
        difference.explanation_ko
        for difference in describe_differences(left, right)
        if difference.blocking
    ]


def _disclosures(
    diagnosis: DiagnosisInput, provenance: Mapping[str, Provenance]
) -> list[str]:
    lines = [RANK_PREDICTION_NOTICE_KO]
    for entry in provenance.values():
        if entry.has_spec:
            lines.append(f"측정 방법론 — {entry.methodology_line_ko()}")
    for entry in provenance.values():
        if entry.pages_examined is not None:
            lines.append(
                f"측정 범위 — {entry.label_ko}: {entry.pages_examined}개 페이지, "
                f"{entry.locale} / {entry.device} / {entry.renderer}"
            )
    lines.append(
        "'해당 없음'은 0점이 아니라 분모에서 제외한 항목이고, '측정 불가'는 실패가 아니라 "
        "측정 범위와 신뢰도에 반영한 항목입니다. 두 값 모두 0으로 표시하지 않습니다."
    )
    lines.append(
        "이 문서는 특정 시점의 고정 스냅샷입니다. 재측정 결과는 이 버전을 수정하지 않고 "
        "새 버전으로 발행됩니다."
    )
    lines.extend(diagnosis.extra_disclosures_ko)
    return lines


def freeze(
    diagnosis: DiagnosisInput, *, previous: ReportSnapshot | None = None
) -> ReportSnapshot:
    """Turn a completed diagnosis into an immutable, self-describing snapshot."""
    metrics: list[MetricRow] = []
    provenance: dict[str, Provenance] = {}
    domain_snapshots: list[DomainSnapshot] = []
    issues: list[IssueSnapshot] = []
    evidence: list[EvidenceSnapshot] = []
    run_ids: list[str] = []

    for domain in diagnosis.domains:
        provenance[domain.key] = _domain_provenance(domain)
        snapshot, domain_issues, domain_evidence = _freeze_domain(domain, metrics)
        domain_snapshots.append(snapshot)
        issues.extend(domain_issues)
        evidence.extend(domain_evidence)
        run_ids.extend(domain.run_ids)

    keywords: list[KeywordSnapshot] = []
    if diagnosis.keywords:
        provenance[KEYWORD_PROVENANCE] = _keyword_provenance()
    for demand in diagnosis.keywords:
        demand_key = f"keyword.{demand.keyword}.monthly_searches"
        opportunity_key = f"keyword.{demand.keyword}.opportunity"
        metrics.append(
            MetricRow(
                metric_key=demand_key,
                label_ko=f"{demand.keyword} 월간 검색량",
                section=SECTION_KEYWORD,
                value=demand.monthly_searches,
                provenance_ref=KEYWORD_PROVENANCE,
                note_ko=demand.note_ko,
            )
        )
        metrics.append(
            MetricRow(
                metric_key=opportunity_key,
                label_ko=f"{demand.keyword} 기회 점수",
                section=SECTION_KEYWORD,
                value=demand.opportunity,
                provenance_ref=KEYWORD_PROVENANCE,
                note_ko="검색량과 경쟁도로 VEO가 계산한 값입니다.",
            )
        )
        keywords.append(
            KeywordSnapshot(
                keyword=demand.keyword,
                demand_metric_key=demand_key,
                opportunity_metric_key=opportunity_key,
                note_ko=demand.note_ko,
            )
        )

    domains_by_key = {domain.key: domain for domain in diagnosis.domains}
    competitors: list[CompetitorSnapshot] = []
    for observation in diagnosis.competitors:
        if observation.domain_key not in domains_by_key:
            continue
        provenance[f"competitor:{observation.slug}"] = _competitor_provenance(observation)
        frozen = _freeze_competitor(observation, domains_by_key, metrics)
        if frozen is not None:
            competitors.append(frozen)

    changes = (
        _freeze_changes(metrics, provenance, previous) if previous is not None else []
    )
    previous_ref = (
        PreviousVersionRef(generated_at=previous.generated_at) if previous is not None else None
    )

    return ReportSnapshot(
        report_title_ko=diagnosis.title_ko,
        audience=diagnosis.audience,
        generated_at=diagnosis.generated_at,
        measurement_window_start=diagnosis.measurement_window_start,
        measurement_window_end=diagnosis.measurement_window_end,
        included_run_ids=run_ids,
        provenance=provenance,
        domains=domain_snapshots,
        metrics=metrics,
        issues=issues,
        evidence=evidence,
        keywords=keywords,
        competitors=competitors,
        changes=changes,
        previous=previous_ref,
        disclosures_ko=_disclosures(diagnosis, provenance),
    )


# --------------------------------------------------------------------------- #
# Persistence, hashing, gating
# --------------------------------------------------------------------------- #


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def compute_content_hash(snapshot: ReportSnapshot) -> str:
    """A hash over the whole frozen document, so a later edit is detectable."""
    body = _canonical(snapshot.model_dump(mode="json"))
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def to_payload(snapshot: ReportSnapshot) -> dict[str, Any]:
    """The JSONB payload written to ``report_versions.content``."""
    return {
        "format_version": SNAPSHOT_FORMAT_VERSION,
        "snapshot": snapshot.model_dump(mode="json"),
        "content_hash": compute_content_hash(snapshot),
    }


def from_payload(payload: Mapping[str, Any]) -> ReportSnapshot:
    """Read a stored payload back, refusing one whose numbers have been altered."""
    try:
        body = payload["snapshot"]
        stored_hash = payload["content_hash"]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ReportTamperedError(f"저장된 리포트 payload에 {exc} 항목이 없습니다.") from None

    snapshot = ReportSnapshot.model_validate(body)
    if compute_content_hash(snapshot) != stored_hash:
        raise ReportTamperedError(
            "저장된 리포트 내용이 발행 당시의 체크섬과 일치하지 않습니다. "
            "이 버전은 신뢰할 수 없습니다."
        )
    return snapshot


def redact_evidence(snapshot: ReportSnapshot) -> ReportSnapshot:
    """The same report, with raw excerpts removed and every score intact.

    A caller without ``EVIDENCE_READ`` is not refused the report — they are given it
    without the raw material. The reference, its kind, its URL and its content hash stay,
    so the reader can see that evidence exists and ask someone who may read it.
    """
    if not snapshot.evidence:
        return snapshot
    redacted = [
        record.model_copy(
            update={
                "excerpt": None,
                "excerpt_redacted": True,
                "storage_key": None,
                "detail": {},
            }
        )
        for record in snapshot.evidence
    ]
    return snapshot.model_copy(update={"evidence": redacted})
