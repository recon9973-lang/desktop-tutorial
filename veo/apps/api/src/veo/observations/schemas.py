"""``/observations`` 의 요청·응답 계약.

관측 엔진은 이미 완성되어 있었는데 **HTTP 로 닿을 길이 없었다** — `src/` 안에서
`ObservationRunner` 를 부르는 코드가 하나도 없었고 테스트만 그것을 돌렸다. 이 모듈과
`service.py`·`router.py` 가 그 다리다.

여기서 지키는 것 하나: **엔진 목록은 쓸 수 있는 것만 돌려주지 않는다.** VEO 가 아는
엔진을 전부 돌려주고 각각의 상태와 그 이유를 함께 준다. 못 쓰는 엔진을 조용히 빼면
목록이 "여기 있는 게 전부" 로 읽히고, 그러면 자격증명을 넣으면 잴 수 있었던 것을
아무도 모른 채 지나간다.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class EngineStatus(BaseModel):
    """엔진 하나와, 지금 쓸 수 있는지."""

    model_config = _FROZEN

    engine: str
    state: str = Field(
        description=(
            "ENABLED 이면 호출합니다. 그 밖의 값은 호출하지 않으며 결과가 "
            "'측정 불가'로 남습니다."
        )
    )
    state_label_ko: str = Field(description="상태를 사람이 읽는 한 문장으로 풀어 쓴 것입니다.")
    usable: bool


class EnginePayload(BaseModel):
    """VEO 가 아는 모든 엔진. 못 쓰는 것도 이유와 함께 들어 있습니다."""

    model_config = _FROZEN

    engines: list[EngineStatus]
    usable_count: int
    note_ko: str


class PromptInput(BaseModel):
    """질문 하나. 분류는 집합의 균형을 재기 위한 것이지 장식이 아닙니다."""

    model_config = _FROZEN

    text: str = Field(min_length=1, description="AI 엔진에 그대로 던질 질문입니다.")
    intent: str = Field(description="검색 의도입니다.")
    funnel: str = Field(description="퍼널 단계입니다.")
    subject: str = Field(
        description="BRANDED | NON_BRAND | COMPETITOR | CATEGORY — 질문이 무엇을 향하는지입니다."
    )
    business_importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "이 질문이 사업에 얼마나 중요한지에 대한 **담당자의 판단**입니다. "
            "검색량이 아닙니다 — 추정과 실측이 한 칸에 들어가면 추정이 데이터로 읽힙니다."
        ),
    )
    persona: str | None = None
    locale: str = "ko-KR"


class ExclusionInput(BaseModel):
    """일부러 뺀 질문과 그 이유.

    뺀 것을 기록하지 않으면 집합이 처음부터 그랬던 것처럼 보인다. 불리한 질문을 빼고
    잰 노출률은 실제보다 높다.
    """

    model_config = _FROZEN

    text: str = Field(min_length=1)
    reason_ko: str = Field(min_length=1, description="왜 뺐는지 적습니다. 빈 값은 받지 않습니다.")


class PromptSetCreateRequest(BaseModel):
    model_config = _FROZEN

    project_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=32, description="같은 이름의 다음 판입니다.")
    locale: str = "ko-KR"
    generation_rule_ko: str | None = Field(
        default=None,
        description="질문을 어떻게 골랐고 무엇을 왜 뺐는지. 나중에 이 집합을 검증할 근거입니다.",
    )
    prompts: list[PromptInput] = Field(min_length=1)
    exclusions: list[ExclusionInput] = Field(default_factory=list)


class PromptSummary(BaseModel):
    model_config = _FROZEN

    prompt_id: str = Field(
        description="질문 내용에서 나온 안정된 식별자입니다. 판이 달라도 같은 질문이면 같습니다."
    )
    text: str
    intent: str
    funnel: str
    subject: str
    business_importance: float
    persona: str | None
    locale: str


class PromptSetPayload(BaseModel):
    model_config = _FROZEN

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    version: str
    locale: str
    generation_rule_ko: str | None
    is_locked: bool
    checksum: str = Field(
        description=(
            "이 집합의 지문입니다. 비교 두 건이 같은 질문으로 잰 것인지 "
            "이 값으로 확인합니다."
        )
    )
    prompts: list[PromptSummary]
    balance_warnings_ko: list[str] = Field(
        default_factory=list,
        description="공정한 비교를 어렵게 만드는 점들입니다. 비어 있어야 정상입니다.",
    )


class PromptSetListPayload(BaseModel):
    model_config = _FROZEN

    items: list[PromptSetPayload]
    total: int


__all__ = [
    "EnginePayload",
    "EngineStatus",
    "ExclusionInput",
    "PromptInput",
    "PromptSetCreateRequest",
    "PromptSetListPayload",
    "PromptSetPayload",
    "PromptSummary",
]
