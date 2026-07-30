"""Data model for VEO scoring specifications, inputs and results.

Nothing in this module decides a score. It only describes what a score is made of,
so that every number VEO shows can be traced back to a versioned specification,
the raw outcomes that fed it, and the arithmetic in between.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CheckStatus(StrEnum):
    """Outcome of a single check.

    ``NOT_APPLICABLE`` and ``UNKNOWN`` are deliberately distinct from ``FAIL``:

    * ``NOT_APPLICABLE`` — the check does not apply to this target. It leaves both the
      numerator and the denominator. It is never worth zero points.
    * ``UNKNOWN`` — the check applies but could not be measured (no credential, provider
      outage, collector limit). It scores nothing and instead lowers coverage and
      confidence, so the gap stays visible.
    """

    PASS = "PASS"  # noqa: S105 - a check status, not a credential
    WARNING = "WARNING"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class Severity(StrEnum):
    BLOCKER = "BLOCKER"
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"


class ScoringDomain(StrEnum):
    SEO_READINESS = "SEO_READINESS"
    GEO_READINESS = "GEO_READINESS"


class SpecStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    RETIRED = "RETIRED"


CategoryStatus = Literal["SCORED", "NOT_APPLICABLE", "UNKNOWN"]

_FROZEN = ConfigDict(frozen=True, extra="forbid")


# --------------------------------------------------------------------------- #
# Specification
# --------------------------------------------------------------------------- #


class ScoreMeaning(BaseModel):
    model_config = _FROZEN

    ko: str
    en: str
    is_rank_prediction: Literal[False]


class StatusPolicy(BaseModel):
    model_config = _FROZEN

    fail_penalty_multiplier: float = Field(ge=0.0, le=1.0)
    warning_penalty_multiplier: float = Field(ge=0.0, le=1.0)
    pass_penalty_multiplier: float = Field(ge=0.0, le=1.0)
    #: N/A 는 언제나 분모에서 빠진다. "적용되지 않는 항목" 은 "없는 것" 이 아니므로,
    #: 0점으로 매기면 없는 결함을 만들어 내게 된다.
    not_applicable: Literal["EXCLUDE_FROM_DENOMINATOR"]
    #: 재지 못한 항목을 어떻게 셀 것인가.
    #:
    #: `EXCLUDE_FROM_SCORE_REDUCE_COVERAGE` — 예산에서 빼고 측정 범위만 낮춘다. 점수는
    #: **잰 것 안에서의 상대값**이 된다. 8개 영역 중 3개를 못 잰 사이트가 남은 80점어치
    #: 안에서 91.8점을 받고 화면에는 "91.8점 양호" 로만 뜨던 이유다.
    #:
    #: `SCORE_AS_ZERO_KEEP_IN_DENOMINATOR` — 배점을 분모에 남기고 점수를 주지 않는다.
    #: 100점이 고정된 만점이 된다. 20점짜리 영역이 0점이면 나머지가 만점이라도 80점이다.
    #: 어느 쪽이든 측정 불가를 **사이트의 실패로 보고하지는 않는다.**
    unknown: Literal[
        "EXCLUDE_FROM_SCORE_REDUCE_COVERAGE", "SCORE_AS_ZERO_KEEP_IN_DENOMINATOR"
    ]


class SpecCheck(BaseModel):
    model_config = _FROZEN

    id: str
    title_ko: str
    title_en: str
    severity: Severity
    scope: Literal["URL", "SITE"]
    remediation_owner: Literal["DEVELOPER", "MARKETER", "BUSINESS_OWNER", "OPERATIONS"]
    #: 이 검사를 재려면 누가 움직여야 하는가.
    #:
    #: `SELF_SERVICE` — VEO 가 스스로 잰다. 우리 크롤이든 우리 API 키든, 고객에게 무엇도
    #: 요청하지 않고 측정할 수 있다. 언제나 배점에 포함된다: 못 쟀다면 우리가 안 한 것이다.
    #:
    #: `CUSTOMER_GRANTED` — 사이트 소유자가 권한을 줘야 한다(서치콘솔, 네이버 서치어드바이저).
    #: `PAID_PROVIDER` — 유료·별도 구성이 필요한 데이터원.
    #:
    #: `REFERENCE_ONLY` — **조회는 되는데 점수로 확정할 수 없다.** 보이는 범위가 일부이거나
    #: (검색 한 곳만 본다), 우리 고객의 것이라고 단정하기 어렵다(이름이 비슷한 다른 업체).
    #: 결과는 보여주되 "별도 확인 필요" 로 표시한다.
    #:
    #: 이 값이 따로 필요한 이유는 0-A 다. 우리 쪽 한계를 `PAID_PROVIDER` 로 적으면
    #: **고객이 돈으로 풀어야 할 일처럼** 넘기게 된다. 우리가 못 잰 것과 고객이 권한을
    #: 안 준 것은 다른 사실이고, 다르게 적혀야 한다.
    #:
    #: `SELF_SERVICE` 를 뺀 나머지는 전부 **진단 범위 밖**이라 분모에서 빠진다. 아직
    #: 요청하지도 않은 권한 때문에, 또 우리 스스로 믿지 못하는 조회 때문에 고객의 점수가
    #: 낮아지면 안 된다. 대신 이름과 "무엇을 하면 확실해지는지" 를 결과에 남긴다 —
    #: 빠졌다는 사실 자체는 숨기지 않는다.
    availability: Literal[
        "SELF_SERVICE", "CUSTOMER_GRANTED", "PAID_PROVIDER", "REFERENCE_ONLY"
    ] = "SELF_SERVICE"
    applicability_ko: str | None = None
    evidence_required: tuple[str, ...] = ()
    engine_scope: tuple[str, ...] = ("GENERIC",)
    reference_ko: str | None = None


class SpecCategory(BaseModel):
    model_config = _FROZEN

    id: str
    weight: float = Field(gt=0.0)
    name_ko: str
    name_en: str
    description_ko: str | None = None
    #: 이 영역이 준비도 점수를 이루는가.
    #:
    #: `False` 인 영역은 그대로 판정하고 보고하되 **점수에는 넣지 않는다.** 연동이
    #: 있어야만 잴 수 있는 영역이 그렇다: 서치콘솔·서치어드바이저는 사이트 소유자가
    #: 권한을 줘야 하고, 백링크·브랜드 언급은 유료 데이터원이 필요하다.
    #:
    #: 점수에 넣으면 분모가 고객마다 달라진다. 연동이 없는 고객은 그 영역이 통째로
    #: 해당 없음이 되어 가중치 합에서 빠지고, 연결한 고객만 더 큰 분모로 채점된다 —
    #: 연결할수록 불리해지는 셈이라, 진단 도구가 만들면 안 되는 유인이 생긴다.
    #: 준비도는 VEO 가 스스로 잴 수 있는 것만으로 100점을 이루고, 연동 지표는 그
    #: 옆에 따로 표시한다.
    contributes_to_score: bool = True
    checks: tuple[SpecCheck, ...] = Field(min_length=1)


class TriggerCondition(BaseModel):
    model_config = _FROZEN

    check_id: str
    status: CheckStatus
    min_coverage: float | None = Field(default=None, ge=0.0, le=1.0)


class Trigger(BaseModel):
    model_config = _FROZEN

    any_of: tuple[TriggerCondition, ...] = Field(min_length=1)


class SpecCap(BaseModel):
    """An upper bound on the overall score, so a catastrophic fault cannot average away."""

    model_config = _FROZEN

    id: str
    max_overall_score: float = Field(ge=0.0, le=100.0)
    reason_ko: str
    release_condition_ko: str
    trigger: Trigger


class SpecGate(BaseModel):
    """A separate status shown beside the score. A gate never changes the number."""

    model_config = _FROZEN

    id: str
    status_code: str
    label_ko: str
    label_en: str
    description_ko: str | None = None
    trigger: Trigger


class SpecBand(BaseModel):
    model_config = _FROZEN

    id: str
    min: float = Field(ge=0.0, le=100.0)
    max: float = Field(ge=0.0, le=100.0)
    label_ko: str
    label_en: str
    description_ko: str | None = None


class ChangelogEntry(BaseModel):
    model_config = _FROZEN

    version: str
    date: str
    summary: str


class ScoringSpec(BaseModel):
    """A published, checksummed measurement specification authored by VEO-LAB."""

    model_config = _FROZEN

    spec_id: str
    domain: ScoringDomain
    version: str
    status: SpecStatus
    effective_at: str
    methodology_owner: str
    implementation_owner: str
    approved_by: str | None = None
    compatible_collector_versions: tuple[str, ...] = ()
    score_meaning: ScoreMeaning
    changelog: tuple[ChangelogEntry, ...] = ()
    severity_coefficients: dict[Severity, float]
    confidence_levels: dict[str, float]
    status_policy: StatusPolicy
    url_importance: dict[str, float]
    categories: tuple[SpecCategory, ...] = Field(min_length=1)
    caps: tuple[SpecCap, ...] = ()
    gates: tuple[SpecGate, ...] = ()
    bands: tuple[SpecBand, ...] = Field(min_length=1)
    checksum: str

    def check(self, check_id: str) -> SpecCheck:
        return self._check_index[check_id]

    def category_of(self, check_id: str) -> SpecCategory:
        return self._category_index[check_id]

    @property
    def check_ids(self) -> tuple[str, ...]:
        return tuple(self._check_index)

    @property
    def _check_index(self) -> dict[str, SpecCheck]:
        return {c.id: c for cat in self.categories for c in cat.checks}

    @property
    def _category_index(self) -> dict[str, SpecCategory]:
        return {c.id: cat for cat in self.categories for c in cat.checks}

    def severity_coefficient(self, severity: Severity) -> float:
        return self.severity_coefficients[severity]

    def band_for(self, score: float) -> SpecBand | None:
        for band in self.bands:
            if band.min <= score <= band.max:
                return band
        return None


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #


class CheckOutcome(BaseModel):
    """What a collector observed for one check on one target.

    ``affected_weight`` / ``evaluated_weight`` carry the importance-weighted URL counts
    for site-scope checks. For a single-URL check both default to 1.0, which makes the
    coverage ratio 1.0 — a failure on one page costs that page's full severity.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    check_id: str
    status: CheckStatus
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_level: str | None = None
    affected_weight: float = Field(default=1.0, ge=0.0)
    evaluated_weight: float = Field(default=1.0, ge=0.0)
    evidence_ids: tuple[str, ...] = ()
    observed_value: Any = None
    note: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> CheckOutcome:
        if self.affected_weight > self.evaluated_weight:
            raise ValueError(
                f"{self.check_id}: affected_weight ({self.affected_weight}) cannot exceed "
                f"evaluated_weight ({self.evaluated_weight})"
            )
        if self.confidence is None and self.confidence_level is None:
            raise ValueError(
                f"{self.check_id}: provide either confidence or confidence_level so the "
                "evidence strength behind this outcome stays explicit"
            )
        return self

    @property
    def coverage_ratio(self) -> float:
        if self.evaluated_weight <= 0.0:
            return 0.0
        return self.affected_weight / self.evaluated_weight


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #


class AppliedCap(BaseModel):
    model_config = _FROZEN

    cap_id: str
    max_overall_score: float
    reason_ko: str
    release_condition_ko: str
    triggered_by: list[str]


class RaisedGate(BaseModel):
    model_config = _FROZEN

    gate_id: str
    status_code: str
    label_ko: str
    label_en: str
    description_ko: str | None
    triggered_by: list[str]


class CategoryScore(BaseModel):
    model_config = _FROZEN

    category_id: str
    name_ko: str
    name_en: str
    weight: float
    status: CategoryStatus
    score: float | None
    budget: float
    penalty_total: float
    coverage: float
    confidence: float
    applicable_check_ids: list[str]
    scored_check_ids: list[str]
    not_applicable_check_ids: list[str]
    unknown_check_ids: list[str]
    failing_check_ids: list[str]


class ScoreResult(BaseModel):
    """A complete, self-describing score.

    Carries the methodology version, the raw outcomes, the applicable denominator,
    the calculation trace and the confidence — as required for every VEO number.
    """

    model_config = _FROZEN

    spec_id: str
    spec_version: str
    spec_checksum: str
    domain: ScoringDomain
    status: Literal["SCORED", "NOT_APPLICABLE", "UNKNOWN"]
    overall_score: float | None
    overall_score_before_caps: float | None
    band_id: str | None
    coverage: float
    confidence: float
    effective_weight_total: float
    categories: list[CategoryScore]
    applied_caps: list[AppliedCap]
    gates: list[RaisedGate]
    outcomes: list[CheckOutcome]
    trace: dict[str, Any]

    def category(self, category_id: str) -> CategoryScore:
        for category in self.categories:
            if category.category_id == category_id:
                return category
        raise KeyError(category_id)
