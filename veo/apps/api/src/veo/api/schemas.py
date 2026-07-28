"""Public request and response schemas for the Phase 0 API surface."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from veo.contracts.enums import (
    DataSource,
    JobType,
    ProviderState,
    ScanScope,
    Surface,
)

_STRICT = ConfigDict(extra="forbid")


class HealthPayload(BaseModel):
    model_config = _STRICT

    status: str
    app_name: str
    tagline: str
    developed_by: str
    methodology_by: str
    environment: str
    version: str


class ProviderStatus(BaseModel):
    """Honest availability reporting.

    When a provider is disabled VEO says so here and returns UNKNOWN for the checks that
    depend on it. It does not substitute an estimate that looks like a measurement.
    """

    model_config = _STRICT

    provider: str
    state: ProviderState
    reason_ko: str


class ProviderStatusPayload(BaseModel):
    model_config = _STRICT

    providers: list[ProviderStatus]


class SpecSummary(BaseModel):
    model_config = _STRICT

    spec_id: str
    domain: str
    version: str
    status: str
    checksum: str
    effective_at: str
    methodology_owner: str
    implementation_owner: str
    score_meaning_ko: str
    is_rank_prediction: bool
    category_weights: dict[str, float]


class SpecListPayload(BaseModel):
    model_config = _STRICT

    specs: list[SpecSummary]


class SpecCheckDetail(BaseModel):
    model_config = _STRICT

    id: str
    title_ko: str
    severity: str
    scope: str
    remediation_owner: str
    applicability_ko: str | None
    evidence_required: list[str]
    engine_scope: list[str]


class SpecCategoryDetail(BaseModel):
    model_config = _STRICT

    id: str
    name_ko: str
    weight: float
    description_ko: str | None
    checks: list[SpecCheckDetail]


class SpecCapDetail(BaseModel):
    model_config = _STRICT

    id: str
    max_overall_score: float
    reason_ko: str
    release_condition_ko: str


class SpecGateDetail(BaseModel):
    model_config = _STRICT

    id: str
    status_code: str
    label_ko: str
    description_ko: str | None


class SpecDetail(SpecSummary):
    model_config = _STRICT

    categories: list[SpecCategoryDetail]
    caps: list[SpecCapDetail]
    gates: list[SpecGateDetail]
    severity_coefficients: dict[str, float]
    url_importance: dict[str, float]
    changelog: list[dict[str, str]]


class ScanRequest(BaseModel):
    model_config = _STRICT

    url: str = Field(
        max_length=2048,
        description="Target URL. Validated against the SSRF guard before any fetch.",
    )
    scope: ScanScope = ScanScope.SINGLE_URL
    idempotency_key: str | None = Field(default=None, max_length=200)


class KeywordLookupRequest(BaseModel):
    model_config = _STRICT

    keywords: list[str] = Field(min_length=1, max_length=5)
    idempotency_key: str | None = Field(default=None, max_length=200)


class JobAccepted(BaseModel):
    model_config = _STRICT

    job_id: str
    type: JobType
    surface: Surface
    status: str
    poll_url: str
    estimated_seconds: int | None = None


class CategoryScorePayload(BaseModel):
    model_config = _STRICT

    category_id: str
    name_ko: str
    weight: float
    status: str
    score: float | None
    budget: float
    penalty_total: float
    coverage: float
    confidence: float
    not_applicable_check_ids: list[str]
    unknown_check_ids: list[str]
    failing_check_ids: list[str]


class AppliedCapPayload(BaseModel):
    model_config = _STRICT

    cap_id: str
    max_overall_score: float
    reason_ko: str
    release_condition_ko: str
    triggered_by: list[str]


class GatePayload(BaseModel):
    model_config = _STRICT

    gate_id: str
    status_code: str
    label_ko: str
    description_ko: str | None
    triggered_by: list[str]


class ScorePayload(BaseModel):
    """A score is never returned alone.

    Version, checksum, applicable denominator, coverage, confidence and the full
    calculation trace travel with every number.
    """

    model_config = _STRICT

    spec_id: str
    spec_version: str
    spec_checksum: str
    domain: str
    status: str
    score: float | None
    score_before_caps: float | None
    band_id: str | None
    coverage: float
    confidence: float
    effective_weight_total: float
    is_rank_prediction: bool = False
    categories: list[CategoryScorePayload]
    applied_caps: list[AppliedCapPayload]
    gates: list[GatePayload]
    calculation_trace: dict[str, Any]


class EvaluateScoreRequest(BaseModel):
    """Evaluate raw check outcomes against a published specification.

    Exists so a customer, an analyst or a test can reproduce any VEO score from its
    published inputs. There is one evaluator, and this is it.
    """

    model_config = _STRICT

    spec_id: str
    spec_version: str
    outcomes: list[CheckOutcomeInput] = Field(min_length=1)


class CheckOutcomeInput(BaseModel):
    model_config = _STRICT

    check_id: str
    status: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_level: str | None = None
    affected_weight: float = Field(default=1.0, ge=0.0)
    evaluated_weight: float = Field(default=1.0, ge=0.0)
    evidence_ids: list[str] = Field(default_factory=list)


class ValueWithSource(BaseModel):
    """Any externally sourced number, with where it came from and when."""

    model_config = _STRICT

    value: float | None
    quality: str
    source: DataSource
    collected_at: datetime | None = None
    source_period: str | None = None
    note_ko: str | None = None


EvaluateScoreRequest.model_rebuild()
