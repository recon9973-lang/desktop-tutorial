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
    #: 결함이 퍼진 **범위**를 감점에 반영하는 지수. 기본값 1.0 은 선형이다.
    #:
    #: 선형이 실제와 다른 이유: 웹사이트의 결함은 대개 **템플릿 단위로 생긴다.**
    #: 100장 중 40장의 title 이 깨졌다면 그것은 40개의 개별 실수가 아니라 템플릿
    #: 하나의 문제이고, **나머지 60장도 같은 위험 위에 있다.** 40% 실패를 40% 감점으로
    #: 세면 "절반 이상 멀쩡하다" 는 그림이 되는데, 고쳐야 할 것은 페이지 40개가 아니라
    #: 템플릿 하나다.
    #:
    #: 0.7 승은 40% 를 53% 로 올려 그 구조를 반영한다. 1.0(선형)과 0(범위 무시) 사이
    #: 어디쯤이 옳은지는 표본이 더 쌓여야 정해지므로, 숫자를 코드에 박지 않고 명세가
    #: 선언하게 둔다. 선언하지 않은 명세는 지금까지처럼 선형이다.
    breadth_exponent: float = Field(default=1.0, gt=0.0, le=1.0)
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


class PerfLabSampling(BaseModel):
    """실험실 성능을 몇 장까지 잴 것인가, 그리고 못 잰 것을 어떻게 셀 것인가."""

    model_config = _FROZEN

    #: 잴 페이지 수의 상한. 중요도가 높은 순으로 고른다.
    max_urls: int = Field(gt=0)
    #: 계획한 표본 중 **실제로 값을 받은** 최소 비율. 이 아래면 검사는 측정 불가다.
    #:
    #: 이 문턱이 없으면 **너무 느려서 로드에 실패한 페이지가 분모에서 빠져 사이트가
    #: 더 빨라 보인다.** 2026-08-01 실측에서 Lighthouse 가 FAILED_DOCUMENT_REQUEST 로
    #: 페이지를 못 연 사례가 실제로 나왔고, 느린 페이지일수록 그렇게 될 확률이 높다 —
    #: 즉 편향이 우리에게 유리한 방향으로 걸린다.
    min_measured_ratio: float = Field(gt=0.0, le=1.0)
    rationale_ko: str | None = None


class PerfFieldSampling(BaseModel):
    """실사용자 성능은 표본을 고를 필요가 없다."""

    model_config = _FROZEN

    #: 사이트 전체(origin) 값을 우선 쓴다.
    #:
    #: 구글이 크롬 사용자에게서 이미 모아 둔 값이라 한 번 물으면 사이트 전체 값이 함께
    #: 온다. 페이지마다 부를 이유가 없고, 따라서 이 지표에는 표본 문제 자체가 없다.
    prefer_origin_scope: bool = True
    rationale_ko: str | None = None


class SamplingPolicy(BaseModel):
    model_config = _FROZEN

    perf_lab: PerfLabSampling | None = None
    perf_field: PerfFieldSampling | None = None


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
    #: 이 검사가 자기 영역 안에서 갖는 **명시적 배점**.
    #:
    #: 이것이 없으면 배점은 심각도 다섯 단계(BLOCKER 1.0 … INFO 0.0)에서 나온다.
    #: 다섯 칸으로는 "title 이 없다" 와 "canonical 이 없다" 를 구분할 수 없고, 실제로
    #: 두 검사는 검색 성과에 미치는 영향이 배 이상 다르다.
    #:
    #: 배점을 쓰는 영역은 `SpecCategory.raw_budget` 을 함께 선언해야 하고, 그 영역
    #: 검사들의 배점 합은 그 값과 정확히 같아야 한다(모델이 검사한다). **그래야 검사를
    #: 추가할 때 형제에서 덜어내게 되고, 무엇을 덜어낼지가 근거를 대야 하는 판단으로
    #: 드러난다.** 나눗셈이 조용히 대신 결정하지 않는다.
    #:
    #: 이 규칙이 없던 판에서 실측한 값: 같은 사이트, 같은 결함인데 검사를 두 개 더한
    #: 것만으로 점수가 66.7 → 72.7 이 됐다. 아무도 거짓말을 하지 않았고 배점도 정확히
    #: 매겼다. 분모가 조용히 늘어났을 뿐이다.
    points: float | None = Field(default=None, gt=0.0)


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
    #: 이 영역이 **관문**인가.
    #:
    #: 관문은 점수를 더하지 않고 **곱한다.** 색인이 막힌 페이지의 완벽한 구조화
    #: 데이터는 아무 일도 하지 않으므로, 앞 단계의 차단은 뒤 단계의 점수를 배점만큼
    #: 깎는 것이 아니라 통째로 무효로 만든다.
    #:
    #: 가산 방식만 쓰던 판에서 실측한 값이 이 필드를 만들게 했다 — **색인이 전면
    #: 차단된 사이트가 74점을 받았다.** 검색에 존재하지 않는 사이트가 "양호" 등급을
    #: 받은 것이다. 차단 검사들의 배점만큼만 잃었기 때문이다.
    #:
    #: 기본값은 `False` 다. 선언하지 않은 명세는 그대로 가산 방식으로 동작한다 —
    #: 발행본은 불변이고(ADR 0012), 1.7.0 이하로 매긴 과거 점수는 앞으로도 그때의
    #: 규칙으로 설명되어야 한다.
    is_gate: bool = False
    #: 이 영역의 **고정 분모**. 검사를 추가해도 변하지 않는다.
    #:
    #: 선언하지 않으면 분모는 지금까지처럼 "채점된 검사들의 심각도 계수 합" 이고,
    #: 그것은 **검사를 더할 때마다 자란다.** 그래서 같은 사이트의 같은 결함이 점점
    #: 싸졌다(1.2.0 66.7 → 1.6.0 72.7, 실측).
    #:
    #: 선언하면 분모는 이 상수다. 해당 없음(N/A) 검사의 배점만 형제들에게 비례
    #: 배분된다 — 그것은 "이 사이트에 그 항목이 없다" 는 사실을 반영하는 것이고,
    #: "명세에 검사가 하나 늘었다" 와는 다른 일이다(ADR 0002).
    raw_budget: float | None = Field(default=None, gt=0.0)
    checks: tuple[SpecCheck, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _points_must_sum_to_the_declared_budget(self) -> SpecCategory:
        """배점을 쓰는 영역은 합이 고정값과 맞아야 한다.

        이 검사가 자물쇠다. 없으면 검사를 추가하는 사람이 배점만 적고 형제를 건드리지
        않게 되고, 그 순간 분모가 다시 늘어난다.
        """
        if self.raw_budget is None:
            if any(check.points is not None for check in self.checks):
                raise ValueError(
                    f"영역 {self.id} 의 검사가 배점(points)을 갖는데 raw_budget 이 없다. "
                    "배점을 쓰려면 고정 분모를 함께 선언해야 한다 — 그러지 않으면 "
                    "검사를 더할 때마다 분모가 자란다."
                )
            return self

        missing = [check.id for check in self.checks if check.points is None]
        if missing:
            raise ValueError(
                f"영역 {self.id} 가 raw_budget 을 선언했는데 배점이 없는 검사가 있다: "
                f"{', '.join(missing)}"
            )

        total = sum(check.points or 0.0 for check in self.checks)
        if abs(total - self.raw_budget) > 1e-9:
            raise ValueError(
                f"영역 {self.id} 의 배점 합이 {total} 인데 고정 분모는 {self.raw_budget} "
                "이다. 검사를 추가했다면 형제 검사에서 그만큼 덜어내야 한다 — "
                "무엇을 덜어낼지가 이 개정의 판단이고, 나눗셈이 대신 해 줄 일이 아니다."
            )
        return self


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
    #: 비싸거나 느린 측정을 어디까지 할 것인가.
    #:
    #: 코드가 정하면 그 숫자를 나중에 아무도 변호하지 못한다. "왜 5장이냐" 에 답할 수
    #: 있어야 하고, 그 답은 명세의 `rationale_ko` 에 실측과 함께 적혀 있다.
    #:
    #: 선언하지 않은 명세는 표본을 쓰지 않는다 — 있는 것을 다 잰다는 뜻이고, 그것이
    #: 기존 명세들의 동작이다(ADR 0012).
    sampling: SamplingPolicy | None = None
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
    def scoring_categories(self) -> tuple[SpecCategory, ...]:
        """가중 평균에 실제로 참여하는 영역들.

        두 가지가 빠진다.

        `contributes_to_score: false` — 연동이 있어야만 잴 수 있는 영역. 판정하고
        표시하되 점수와 분모 양쪽에서 빠진다. 그렇지 않으면 서치콘솔을 연결하지 않은
        고객이 영영 그 몫을 얻지 못한다.

        `is_gate: true` — 관문. **점수에 영향을 주지만 더해지지 않고 곱해진다.**
        가중치 합에 넣으면 100 이 130 이 되고, 그 130 은 아무 뜻도 없는 숫자다.
        관문의 `weight` 는 그 단계가 얼마짜리 관문인지 읽기 위한 표시일 뿐이다.

        이 속성이 있는 이유는 **합을 세는 곳이 여럿이었기 때문**이다. 평가기와 시험
        셋이 각자 `sum(c.weight for c in ...)` 을 다시 썼고, 관문이 생기자 넷 중
        하나만 고쳐도 나머지가 조용히 틀린 답을 냈다.
        """
        return tuple(c for c in self.categories if c.contributes_to_score and not c.is_gate)

    @property
    def scoring_weight_total(self) -> float:
        return sum(category.weight for category in self.scoring_categories)

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
    #: 이 검사에 걸린 / 판정한 페이지 URL. 평가기는 읽지 않는다 — 무게(affected/
    #: evaluated_weight)가 점수를 정하고, 이 목록은 **어느 페이지였는지**를 기억해
    #: 페이지별 재집계를 가능하게 한다. 목록 없이 무게만 저장하면 "103장" 은 남고
    #: "어느 103장" 은 사라진다 — 그것이 실제로 일어나고 있던 유실이다.
    affected_urls: tuple[str, ...] = ()
    evaluated_urls: tuple[str, ...] = ()

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
    #: 검색에 들어갈 수 있는 비율. 관문 영역이 없는 명세에서는 언제나 1.0 이다.
    #:
    #: 이 값이 응답에 실리는 이유: **관문 때문에 0점이 된 사이트가 화면에서 왜 0점인지
    #: 읽을 수 없으면 그 계산은 없는 것과 같다.** "0점" 만 보고 무엇을 고쳐야 할지
    #: 모르는 고객에게 점수는 판결문일 뿐이다. 도달률 0.4 와 품질 85 를 나란히 보여야
    #: "고칠 것은 품질이 아니라 차단이다" 를 읽을 수 있다.
    reach: float = 1.0
    #: 확인하지 못한 관문 검사의 id.
    #:
    #: 못 잰 차단은 곱하지 않는다(0-A). 그러나 **조용히 넘어가면 "확인했고 문제없음"
    #: 과 구분되지 않는다.** 이름을 실어 화면이 "색인 가능 여부를 확인하지 못했습니다"
    #: 라고 말할 수 있게 한다.
    gate_unverified: list[str] = []
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
