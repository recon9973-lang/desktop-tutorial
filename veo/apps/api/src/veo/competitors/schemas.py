"""Request and response shapes for ``/competitors``.

The request carries *finished measurements*. This package does not crawl and does not
score — a single crawl feeds every engine and the SSRF guard lives in one place — so a
caller hands over what was already measured, plus the conditions it was measured under.

Two things are deliberately not accepted from the caller:

* ``spec_id`` / ``spec_version`` / ``spec_checksum`` are part of the *score*, not part of
  a separate conditions block, and the checksum is verified against the published
  specification on disk. A score that does not match a published document is refused.
* ``allow_scope_variance`` has no default of ``True`` anywhere and cannot be set per
  competitor. It is one explicit, request-wide decision an analyst makes and signs for.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_STRICT = ConfigDict(extra="forbid")

NonBlank = Annotated[str, Field(min_length=1, max_length=120)]


class DeclaredConditions(BaseModel):
    """The parts of a measurement's setup VEO cannot read off the payload itself."""

    model_config = _STRICT

    collector_version: NonBlank = Field(
        description="측정을 수행한 수집기 버전입니다. 버전이 다르면 비교가 거부됩니다."
    )
    device: NonBlank = Field(description="MOBILE · DESKTOP 등 측정 기기 프로필입니다.")
    renderer: NonBlank = Field(
        description="렌더링 방식입니다. 자바스크립트 실행 여부가 다르면 같은 측정이 아닙니다."
    )
    pages_examined: int = Field(
        ge=0, description="실제로 수집에 성공한 페이지 수입니다. 요청한 수가 아닙니다."
    )
    locale: NonBlank = Field(description="측정 언어·지역입니다. 예: ko-KR")
    enabled_providers: list[str] = Field(
        default_factory=list,
        description="측정 시점에 실제로 사용 가능했던 외부 제공자입니다. 한쪽에만 있으면 "
        "비교가 거부됩니다.",
    )
    measured_at: datetime = Field(description="측정 시점입니다. 시차가 크면 비교가 거부됩니다.")

    @field_validator("collector_version", "device", "renderer", "locale")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                "공백만으로는 측정 조건을 지정할 수 없습니다. 비워 두면 서로 다른 조건의 "
                "측정이 같은 조건처럼 비교됩니다."
            )
        return value.strip()


class CategoryScoreInput(BaseModel):
    model_config = _STRICT

    category_id: NonBlank
    score: float | None = Field(default=None, ge=0.0, le=100.0)
    coverage: float = Field(ge=0.0, le=1.0)
    scored_check_ids: list[str] = Field(
        default_factory=list,
        description="이 카테고리에서 실제로 채점된 검사 항목입니다. 두 측정의 교집합이 "
        "비교의 분모가 됩니다.",
    )


class ScoreInput(BaseModel):
    """A finished readiness score, as produced by the SEO or GEO engine."""

    model_config = _STRICT

    spec_id: NonBlank
    spec_version: NonBlank
    spec_checksum: str = Field(min_length=64, max_length=64)
    overall_score: float | None = Field(default=None, ge=0.0, le=100.0)
    coverage: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    categories: list[CategoryScoreInput] = Field(default_factory=list)
    check_statuses: dict[str, str] = Field(
        default_factory=dict,
        description="검사 항목별 판정입니다. PASS · WARNING · FAIL · NOT_APPLICABLE · UNKNOWN.",
    )


class MeasurementInput(BaseModel):
    model_config = _STRICT

    conditions: DeclaredConditions
    score: ScoreInput


class BaselineInput(BaseModel):
    """Our own site."""

    model_config = _STRICT

    label_ko: NonBlank = Field(description="보고서에 표시할 자사 사이트 이름입니다.")
    measurement: MeasurementInput


class CompetitorMeasurementInput(BaseModel):
    model_config = _STRICT

    competitor_id: uuid.UUID
    measurement: MeasurementInput


class ParticipantVisibilityInput(BaseModel):
    model_config = _STRICT

    key: NonBlank
    label_ko: NonBlank
    is_own_brand: bool = False
    cited_answer_count: int = Field(ge=0)
    mentioned_answer_count: int = Field(ge=0)
    won_prompt_count: int = Field(ge=0)


class ObservedVisibilityInput(BaseModel):
    """Optional: what the answer engines actually said, kept apart from the score."""

    model_config = _STRICT

    prompt_set_label: NonBlank
    engine_labels: list[str] = Field(default_factory=list)
    observed_answer_count: int = Field(ge=0)
    decided_prompt_count: int = Field(ge=0)
    participants: list[ParticipantVisibilityInput] = Field(min_length=1)


class ComparisonCreateRequest(BaseModel):
    model_config = _STRICT

    project_id: uuid.UUID
    baseline: BaselineInput
    competitors: list[CompetitorMeasurementInput] = Field(min_length=1)
    allow_scope_variance: bool = Field(
        default=False,
        description="검사 페이지 수 차이만 예외로 허용합니다. 방법론·기기·렌더러·로케일·"
        "제공자·측정 시점 차이는 이 옵션으로도 통과하지 않습니다. 허용해도 그 차이는 "
        "결과에 그대로 남습니다.",
    )
    observed_visibility: ObservedVisibilityInput | None = Field(
        default=None,
        description="관측된 AI 가시성입니다. 준비도 점수와 합산되지 않고 별도 블록으로 "
        "반환됩니다.",
    )

    @model_validator(mode="after")
    def _reject_repeated_competitors(self) -> ComparisonCreateRequest:
        ids = [entry.competitor_id for entry in self.competitors]
        if len(set(ids)) != len(ids):
            raise ValueError(
                "같은 경쟁사를 두 번 지정할 수 없습니다. 한 대상을 두 번 세면 점유율과 "
                "집계가 조용히 어긋납니다."
            )
        return self


# --------------------------------------------------------------------------- #
# Responses
# --------------------------------------------------------------------------- #


class ComparisonPayload(BaseModel):
    """The whole comparison. Deltas when comparable, refusals with reasons when not."""

    model_config = _STRICT

    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    allow_scope_variance: bool
    summary_ko: str
    confidence: float | None
    confidence_level_ko: str | None
    confidence_basis_ko: str
    comparable_count: int
    refused_count: int
    baseline: dict[str, Any]
    comparison_set: list[dict[str, Any]]
    pairs: list[dict[str, Any]]
    share_of_voice: dict[str, Any] | None = Field(
        default=None,
        description="관측된 AI 가시성입니다. 준비도 점수와 별개이며 절대 합산하지 마십시오.",
    )
    separation_note_ko: str


class ComparisonSummaryPayload(BaseModel):
    """One row of the list. Enough to choose a comparison, not enough to misread one."""

    model_config = _STRICT

    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    summary_ko: str
    comparable_count: int
    refused_count: int
    confidence: float | None
    allow_scope_variance: bool


__all__ = [
    "BaselineInput",
    "CategoryScoreInput",
    "ComparisonCreateRequest",
    "ComparisonPayload",
    "ComparisonSummaryPayload",
    "CompetitorMeasurementInput",
    "DeclaredConditions",
    "MeasurementInput",
    "ObservedVisibilityInput",
    "ParticipantVisibilityInput",
    "ScoreInput",
]
