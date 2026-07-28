"""Request and response models for the VEO-LAB workflow.

Everything a reviewer needs to make a decision is rendered in Korean on the way out:
the status label, the diff lines, the golden-fixture verdict, the aggregate effect of a
re-score. The raw specification document travels alongside them, unmodified, so the
prose and the bytes can always be checked against each other.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from veo.db.models.analysis import ScoringVersion
from veo.lab import rescore as rescore_module
from veo.lab import validation, versions
from veo.lab.golden import GoldenRun
from veo.organizations.fields import STRICT


class ScoringVersionSummary(BaseModel):
    model_config = STRICT

    id: uuid.UUID
    spec_id: str
    domain: str
    semantic_version: str
    status: str
    status_label_ko: str
    checksum: str
    changelog: str | None
    compatible_collector_versions: list[str]
    effective_at: datetime | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    created_at: datetime
    golden_passed: bool | None = Field(
        default=None,
        description="골든 픽스처 검증 결과. 아직 실행하지 않았으면 null입니다.",
    )
    golden_summary_ko: str | None = None

    @classmethod
    def of(cls, row: ScoringVersion) -> ScoringVersionSummary:
        status = versions.parse_status(row.status)
        recorded = row.golden_fixture_results or {}
        return cls(
            id=row.id,
            spec_id=row.spec_id,
            domain=row.domain,
            semantic_version=row.semantic_version,
            status=status.value,
            status_label_ko=versions.label_ko(status),
            checksum=row.checksum,
            changelog=row.changelog,
            compatible_collector_versions=[
                str(item) for item in (row.compatible_collector_versions or [])
            ],
            effective_at=row.effective_at,
            approved_by=row.approved_by,
            approved_at=row.approved_at,
            created_at=row.created_at,
            golden_passed=bool(recorded["all_passed"]) if "all_passed" in recorded else None,
            golden_summary_ko=recorded.get("summary_ko"),
        )


class WeightChangePayload(BaseModel):
    model_config = STRICT

    category_id: str
    name_ko: str
    before: float
    after: float
    delta: float


class SeverityChangePayload(BaseModel):
    model_config = STRICT

    check_id: str
    title_ko: str
    before: str
    after: str


class CapChangePayload(BaseModel):
    model_config = STRICT

    cap_id: str
    before_max: float
    after_max: float


class DiffPayload(BaseModel):
    """이전 발행본 대비 무엇이 바뀌었는지. `lines_ko`만 읽어도 충분하도록 구성합니다."""

    model_config = STRICT

    baseline_version: str | None
    baseline_checksum: str | None
    baseline_source_ko: str
    candidate_version: str
    has_changes: bool
    summary_ko: str
    lines_ko: list[str]
    weight_changes: list[WeightChangePayload]
    checks_added: list[str]
    checks_removed: list[str]
    severity_changes: list[SeverityChangePayload]
    cap_changes: list[CapChangePayload]
    caps_added: list[str]
    caps_removed: list[str]
    gates_added: list[str]
    gates_removed: list[str]

    @classmethod
    def of(cls, diff: validation.SpecDiff, *, baseline_source_ko: str) -> DiffPayload:
        return cls(
            baseline_version=diff.baseline_version,
            baseline_checksum=diff.baseline_checksum,
            baseline_source_ko=baseline_source_ko,
            candidate_version=diff.candidate_version,
            has_changes=diff.has_changes,
            summary_ko=diff.summary_ko(),
            lines_ko=list(diff.lines_ko()),
            weight_changes=[
                WeightChangePayload(
                    category_id=change.category_id,
                    name_ko=change.name_ko,
                    before=change.before,
                    after=change.after,
                    delta=round(change.delta, 6),
                )
                for change in diff.weight_changes
            ],
            checks_added=[change.check_id for change in diff.checks_added],
            checks_removed=[change.check_id for change in diff.checks_removed],
            severity_changes=[
                SeverityChangePayload(
                    check_id=change.check_id,
                    title_ko=change.title_ko,
                    before=change.before,
                    after=change.after,
                )
                for change in diff.severity_changes
            ],
            cap_changes=[
                CapChangePayload(
                    cap_id=change.cap_id,
                    before_max=change.before_max,
                    after_max=change.after_max,
                )
                for change in diff.cap_changes
            ],
            caps_added=[change.cap_id for change in diff.caps_added],
            caps_removed=[change.cap_id for change in diff.caps_removed],
            gates_added=list(diff.gates_added),
            gates_removed=list(diff.gates_removed),
        )


class ValidationPayload(BaseModel):
    model_config = STRICT

    ok: bool
    errors_ko: list[str]
    warnings_ko: list[str]
    category_weight_total: float

    @classmethod
    def of(cls, report: validation.ValidationReport) -> ValidationPayload:
        return cls(
            ok=report.ok,
            errors_ko=list(report.errors_ko),
            warnings_ko=list(report.warnings_ko),
            category_weight_total=round(report.category_weight_total, 6),
        )


class GoldenFixturePayload(BaseModel):
    model_config = STRICT

    name: str
    fixture_spec_version: str
    passed: bool
    failures_ko: list[str]


class GoldenPayload(BaseModel):
    """골든 픽스처 실행 결과. 이 결과가 통과하지 않으면 발행할 수 없습니다."""

    model_config = STRICT

    spec_version: str
    spec_checksum: str
    ran_at: str
    total: int
    passed: int
    failed: int
    all_passed: bool
    failed_names: list[str]
    summary_ko: str
    fixtures: list[GoldenFixturePayload]

    @classmethod
    def of_run(cls, run: GoldenRun) -> GoldenPayload:
        return cls.of_record(run.to_record())

    @classmethod
    def of_record(cls, record: dict[str, Any]) -> GoldenPayload:
        return cls(
            spec_version=str(record.get("spec_version", "")),
            spec_checksum=str(record.get("spec_checksum", "")),
            ran_at=str(record.get("ran_at", "")),
            total=int(record.get("total", 0)),
            passed=int(record.get("passed", 0)),
            failed=int(record.get("failed", 0)),
            all_passed=bool(record.get("all_passed", False)),
            failed_names=[str(name) for name in record.get("failed_names", [])],
            summary_ko=str(record.get("summary_ko", "")),
            fixtures=[
                GoldenFixturePayload(
                    name=str(item.get("name", "")),
                    fixture_spec_version=str(item.get("fixture_spec_version", "")),
                    passed=bool(item.get("passed", False)),
                    failures_ko=[str(line) for line in item.get("failures_ko", [])],
                )
                for item in record.get("fixtures", [])
            ],
        )


class ScoringVersionDetail(ScoringVersionSummary):
    model_config = STRICT

    specification: dict[str, Any]
    diff: DiffPayload
    validation: ValidationPayload
    golden: GoldenPayload | None
    allowed_transitions: list[str]


class ScoreShiftPayload(BaseModel):
    """한 건의 점수 이동. 원본과 재계산본이 각각 버전·체크섬과 함께 남습니다."""

    model_config = STRICT

    score_result_id: uuid.UUID
    scan_run_id: uuid.UUID
    recomputed_score_result_id: uuid.UUID | None
    before_score: float | None
    after_score: float | None
    delta: float | None
    before_spec_version: str
    before_spec_checksum: str
    after_spec_version: str
    after_spec_checksum: str
    direction: str


class RescoreSummaryPayload(BaseModel):
    model_config = STRICT

    spec_id: str
    to_version: str
    to_checksum: str
    total: int
    risen: int
    fallen: int
    unchanged: int
    incomparable: int
    skipped: int
    mean_delta: float
    max_rise: float
    max_fall: float
    summary_ko: str
    shifts: list[ScoreShiftPayload]

    @classmethod
    def of(cls, summary: rescore_module.RescoreSummary) -> RescoreSummaryPayload:
        return cls(
            spec_id=summary.spec_id,
            to_version=summary.to_version,
            to_checksum=summary.to_checksum,
            total=summary.total,
            risen=summary.risen,
            fallen=summary.fallen,
            unchanged=summary.unchanged,
            incomparable=summary.incomparable,
            skipped=summary.skipped,
            mean_delta=summary.mean_delta,
            max_rise=summary.max_rise,
            max_fall=summary.max_fall,
            summary_ko=summary.summary_ko(),
            shifts=[
                ScoreShiftPayload(
                    score_result_id=shift.score_result_id,
                    scan_run_id=shift.scan_run_id,
                    recomputed_score_result_id=shift.recomputed_score_result_id,
                    before_score=shift.before_score,
                    after_score=shift.after_score,
                    delta=shift.delta,
                    before_spec_version=shift.before_spec_version,
                    before_spec_checksum=shift.before_spec_checksum,
                    after_spec_version=shift.after_spec_version,
                    after_spec_checksum=shift.after_spec_checksum,
                    direction=shift.direction,
                )
                for shift in summary.shifts
            ],
        )


class CreateDraftRequest(BaseModel):
    """새 점수 명세 초안 등록 요청.

    `specification`은 `packages/scoring-specs/schema/scoring-spec.schema.json`을 만족하는
    문서여야 합니다. 저장된 문서는 이후 어떤 경로로도 고쳐 쓰이지 않으므로, 발행할
    문서라면 `status: PUBLISHED`로 작성해 두세요.
    """

    model_config = STRICT

    specification: dict[str, Any]
    changelog: str | None = Field(
        default=None, max_length=4000, description="무엇을 왜 바꿨는지 남기는 메모입니다."
    )
    compatible_collector_versions: list[str] | None = Field(
        default=None,
        description="비우면 명세 문서의 compatible_collector_versions를 그대로 씁니다.",
    )


class UpdateDraftRequest(BaseModel):
    """초안 수정 요청. 발행되었거나 폐기된 버전에는 적용할 수 없습니다."""

    model_config = STRICT

    specification: dict[str, Any] | None = None
    changelog: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def _reject_empty_body(self) -> UpdateDraftRequest:
        if self.specification is None and self.changelog is None:
            raise ValueError("수정할 항목을 하나 이상 지정해야 합니다.")
        return self


class RescoreRequest(BaseModel):
    """과거 점수 재계산 요청. 원본 행은 그대로 두고 새 행을 추가합니다."""

    model_config = STRICT

    scan_run_ids: list[uuid.UUID] | None = Field(
        default=None, description="비우면 이 조직의 해당 명세 계열 결과 전체가 대상입니다."
    )
    limit: int = Field(default=200, ge=1, le=1000)
