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
from datetime import datetime
from typing import Any, Literal

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
    "CitedDomainPayload",
    "EngineChoiceInput",
    "EnginePayload",
    "EngineSpendPayload",
    "EngineStatus",
    "ExclusionInput",
    "ObservationRunDetailPayload",
    "ObservationRunListPayload",
    "ObservationRunPayload",
    "ObservationRunRequest",
    "PromptInput",
    "PromptSetCreateRequest",
    "PromptSetListPayload",
    "PromptSetPayload",
    "PromptSummary",
    "RatePayload",
    "SourceDiversityPayload",
    "SpendPayload",
    "StabilityPayload",
    "VisibilityMetricsPayload",
]


# --------------------------------------------------------------------------- #
# 관측 실행
# --------------------------------------------------------------------------- #


class EngineChoiceInput(BaseModel):
    """어느 엔진을 어떤 모델로 돌릴지.

    모델을 서버가 고르지 않는다. 모델마다 인용을 돌려주는지가 다르고(실측: `gpt-5`·
    `gpt-4o` 는 돌려주고 `gpt-4.1`·`gpt-4o-mini` 는 돌려주지 않는다), 그 선택이 곧
    무엇을 측정할 수 있는지를 정한다. 기본값을 숨겨 두면 부르는 쪽이 그 사실을 모른 채
    "인용 0회" 를 받아 간다.
    """

    model_config = _FROZEN

    engine: str = Field(description="OPENAI | ANTHROPIC | GOOGLE_GEMINI | PERPLEXITY")
    model: str = Field(min_length=1, description="그 엔진의 모델 이름입니다.")
    search_mode: str = Field(
        default="BROWSING",
        description=(
            "BROWSING 이면 검색을 켭니다. 인용을 재려면 켜야 하지만, 켠다고 모든 모델이 "
            "인용을 돌려주지는 않습니다."
        ),
    )
    account_state: str = Field(default="ANONYMOUS", description="ANONYMOUS | SIGNED_IN | UNKNOWN")


class ObservationRunRequest(BaseModel):
    model_config = _FROZEN

    prompt_set_id: uuid.UUID
    engines: list[EngineChoiceInput] = Field(min_length=1)
    repetitions: int = Field(
        default=3,
        ge=1,
        le=50,
        description=(
            "프롬프트 하나를 엔진 하나에 던지는 횟수입니다. AI 답변은 같은 질문에도 "
            "매번 달라지므로 한 번의 결과를 노출률이라고 부를 수 없습니다. 최소 3회이며, "
            "그 아래로 돌리려면 `allow_below_floor` 를 명시해야 합니다."
        ),
    )
    allow_below_floor: bool = Field(
        default=False,
        description=(
            "최소 반복 횟수 아래로 돌리는 것을 허용합니다. 결과에 '이 값으로 노출률을 "
            "말하지 마세요' 가 함께 기록됩니다. 시험용입니다."
        ),
    )


class ObservationRunPayload(BaseModel):
    """한 번의 관측이 **무엇을 했고 무엇을 못 했는가.**

    `executions_valid` 만 보면 절반만 실행된 관측이 완전한 측정처럼 읽힙니다. 그래서
    계획·건너뜀·중단 사유를 같은 자리에 둡니다.
    """

    model_config = _FROZEN

    id: uuid.UUID
    project_id: uuid.UUID
    prompt_set_id: uuid.UUID
    status: str
    is_complete: bool = Field(
        description="계획한 것을 다 했고 반복 최소치를 넘겼는가. 거짓이면 부분 측정입니다."
    )
    engines: list[str]
    repetitions_per_prompt: int
    executions_planned: int
    executions_attempted: int
    executions_valid: int
    executions_skipped: int
    stopped_reason: str | None
    summary_ko: str = Field(description="이 실행을 한 문장으로. 못 한 일이 있으면 거기 적힙니다.")
    unpriced_calls: int = Field(
        description="비용을 알 수 없는 호출 수입니다. 0원이라는 뜻이 아니라 모른다는 뜻입니다."
    )
    total_cost_usd: float = Field(
        description=(
            "알 수 있었던 비용의 합(USD)입니다. `unpriced_calls` 가 있으면 이 값은 "
            "전체가 아니라 일부입니다."
        )
    )
    started_at: datetime | None
    finished_at: datetime | None


class RatePayload(BaseModel):
    """비율 하나 — 그리고 그 값을 얼마나 믿을 수 있는가.

    `value` 가 `null` 인 것과 `0.0` 인 것은 **정반대의 뜻**입니다. `null` 은 잴 수
    없었다는 뜻이고, `0.0` 은 쟀는데 한 번도 없었다는 뜻입니다. 화면에서 둘을 같게
    그리면 우리가 못 잰 것이 고객 탓으로 보입니다.

    표시할 때는 **`percent_text_ko` 를 그대로 쓰십시오.** `value` 를 직접 퍼센트로
    포맷하면 표본이 3~5회인 값에도 소수점이 붙고, 그 순간 표본이 감당하지 못하는
    정밀도를 주장하게 됩니다.
    """

    model_config = _FROZEN

    label_ko: str
    numerator: int
    denominator: int = Field(description="이 비율이 무엇에 대한 값인지. 0이면 잴 수 없었습니다.")
    value: float | None = Field(
        description=(
            "실행이 3회 미만이면 `null` 입니다. 경고를 붙여 숫자를 내보내지 않습니다 — "
            "화면에 뜬 숫자는 읽히고 주석은 읽히지 않기 때문입니다."
        )
    )
    percent_text_ko: str = Field(description="화면에 그대로 쓰는 표시 문자열입니다.")
    low: float | None = Field(description="95% 신뢰구간 하한입니다.")
    high: float | None
    adequacy: Literal["NO_DATA", "TOO_SMALL", "DIRECTIONAL", "ADEQUATE"] = Field(
        description=(
            "표본이 감당하는 무게입니다. `NO_DATA` 못 쟀음 · `TOO_SMALL` 3회 미만이라 "
            "값 없음 · `DIRECTIONAL` 방향만 · `ADEQUATE` 비율로 읽어도 됨."
        )
    )
    is_comparison_grade: bool = Field(
        description=(
            "경쟁사 비교 보고에 실을 수 있는가. 실행 5회 이상이어야 참입니다 "
            "(VEO-LAB 표본 방법론)."
        )
    )
    note_ko: str
    summary_ko: str = Field(
        description="비율·분모·신뢰구간·주의를 한 줄에 담은 문장입니다. 분모가 빠지지 않습니다."
    )


class RepetitionSpreadPayload(BaseModel):
    """반복이 실제로 얼마나 벌어져 있었나.

    `caveat_ko` 는 **기준을 넘겨도 사라지지 않습니다.** 한 번의 실행 안에서 벌릴 수 있는
    것은 분 단위인데 방법론이 요구하는 것은 날짜·시간대 분산이라, 어느 쪽이든 완전한
    독립은 아니기 때문입니다. 문장만 바뀝니다.
    """

    model_config = _FROZEN

    shortest_gap_seconds: int | None = Field(
        default=None,
        description="같은 질문의 연속한 두 반복 사이 간격 중 **가장 짧은 것**. 평균이 아닙니다.",
    )
    measured_pairs: int = 0
    is_spread_out: bool = False
    caveat_ko: str | None = None


class CitedDomainPayload(BaseModel):
    model_config = _FROZEN

    domain: str
    citations: int


class SourceDiversityPayload(BaseModel):
    """엔진이 인용한 곳의 넓이."""

    model_config = _FROZEN

    answers_with_visible_citations: int
    distinct_domains: int
    total_citations: int
    top_domains: list[CitedDomainPayload] = Field(default_factory=list)
    #: 거짓이면 위 숫자는 0이 아니라 **측정 불가**입니다.
    is_measurable: bool


class StabilityPayload(BaseModel):
    """같은 질문을 다시 물었을 때 답이 같았나."""

    model_config = _FROZEN

    repeated_groups: int
    consistent_groups: int
    unstable_group_count: int
    #: 2회 이상 물은 조합이 없으면 거짓입니다. 한 번 물은 답은 흔들렸는지 알 수 없습니다.
    is_measurable: bool
    rate: RatePayload


class VisibilityMetricsPayload(BaseModel):
    """이 관측이 말할 수 있는 것과, 말할 수 없는 것."""

    model_config = _FROZEN

    answers_recorded: int
    answers_valid: int = Field(description="응답을 실제로 받은 건수입니다. 언급률의 분모입니다.")
    answers_with_visible_citations: int = Field(
        description=(
            "출처를 확인할 수 있었던 건수입니다. **인용률의 분모**이며, 여기 들어가지 "
            "않은 응답은 '인용 안 됨'이 아니라 '알 수 없음'입니다."
        )
    )
    answers_pending_disambiguation: int = Field(
        default=0,
        description=(
            "상호가 나왔지만 같은 이름의 다른 업체와 갈리지 않아 판정을 보류한 건수입니다. "
            "**'언급 없음'이 아닙니다** — 언급률은 이 건들을 분자에서 뺀 확정 하한이며, "
            "소재지·대표번호를 등록하면 대부분 자동으로 갈립니다."
        ),
    )
    repetition_spread: RepetitionSpreadPayload = Field(
        default_factory=lambda: RepetitionSpreadPayload(),
        description=(
            "같은 질문의 반복이 **시간적으로** 얼마나 벌어져 있었는지입니다.\n\n"
            "위 신뢰구간은 반복이 서로 독립이라는 가정 위에서만 성립합니다. 같은 순간에 "
            "몰아 던진 반복은 그 시각의 엔진 상태가 전부에 똑같이 묻어나므로 독립이 "
            "아니고, **구간이 실제보다 좁게 나옵니다.** VEO는 구간을 다시 계산하지 "
            "않습니다 — 상관을 얼마나 먹었는지 알 수 없고, 모르는 값으로 보정하면 그것도 "
            "지어낸 숫자이기 때문입니다. 대신 잰 그대로 적습니다."
        ),
    )
    mention_rate: RatePayload
    citation_rate: RatePayload
    prompt_coverage: RatePayload
    recommendation_prompt_mention_rate: RatePayload = Field(
        description=(
            "추천을 묻는 질문에서 상호가 나온 비율입니다. **AI 가 우리를 추천했는지가 "
            "아닙니다** — 그건 답변 문장을 읽어야 알 수 있고 아직 재지 않습니다."
        ),
    )
    source_diversity: SourceDiversityPayload = Field(
        description=(
            "엔진이 이번 실행에서 몇 곳을 인용했는지입니다. 인용률을 읽는 방법을 "
            "바꿉니다 — 두 곳만 인용하는 엔진에서의 20%와 마흔 곳을 인용하는 엔진에서의 "
            "20%는 같은 뜻이 아닙니다."
        ),
    )
    stability: StabilityPayload = Field(
        description=(
            "같은 질문을 같은 엔진에 다시 물었을 때 답이 같았는지입니다. 언급률 50%는 "
            "'질문의 절반은 늘 나온다'일 수도 '모든 질문이 물을 때마다 뒤집힌다'일 "
            "수도 있고, 고쳐야 할 것이 전혀 다릅니다."
        ),
    )
    is_partial_measurement: bool
    caveats_ko: list[str] = Field(
        description="이 숫자를 읽을 때 함께 알아야 하는 것들입니다. 비어 있어야 정상입니다."
    )


class ObservationRunDetailPayload(BaseModel):
    """실행 하나와 그 지표."""

    model_config = _FROZEN

    run: ObservationRunPayload
    metrics: VisibilityMetricsPayload


class RiskFindingsPayload(BaseModel):
    """이 실행이 남긴 위험 판정 — **공개 게이트를 지난 뒤의 모습**입니다.

    `customer` 는 고객 문서에 실어도 되는 것만 담습니다. 검수되지 않은 치명·높음 지적의
    **문장은 들어 있지 않고**, 건수와 심각도, 그리고 왜 보류되었는지만 들어 있습니다.
    `internal` 은 내부 화면 전용이며 보류된 지적의 원문을 포함하므로, 공개 리포트 토큰
    경로에 연결하면 안 됩니다.

    `kinds_not_yet_produced` 를 빼고 "위험 0건" 만 보여주면 **위험이 없다**로 읽힙니다.
    실제로는 방법론 8종 가운데 규칙으로 낼 수 있는 1종만 재고 있습니다.
    """

    model_config = _FROZEN

    customer: dict[str, Any]
    internal: dict[str, Any]
    kinds_not_yet_produced: list[dict[str, str]]


class ObservationRunListPayload(BaseModel):
    model_config = _FROZEN

    items: list[ObservationRunPayload]
    total: int


class ReviewQueueItem(BaseModel):
    """검수 대기 한 건 — 기계가 **실제로 본 글자**와 함께."""

    model_config = _FROZEN

    assessment_id: uuid.UUID
    kind: str
    band_label_ko: str
    severity: str
    claim_text: str = Field(
        description=(
            "기계가 답변에서 잘라낸 그 문장입니다. 요약이 아닙니다 — 검수자가 판단하려면 "
            "'백세온담한의원'과 '온담한의원'의 차이를 직접 봐야 합니다."
        )
    )
    automated_verdict: str
    automated_rationale_ko: str
    stage: str
    stage_label_ko: str
    is_held_by_someone: bool = Field(
        description=(
            "다른 검수자가 맡고 있는지. **누가 맡았는지는 알려주지 않습니다** — 검수 "
            "화면이 조직원 명단을 흘리는 자리가 되면 안 됩니다."
        )
    )
    is_mine: bool


class ReviewQueuePayload(BaseModel):
    """검수 대기 목록 — 심각한 것부터.

    결론이 난 건은 빠지지만 **근거 보강 대기는 남습니다.** 그것은 끝난 것이 아니라 멈춰
    있는 것이고, 목록에서 빠지면 영영 아무도 다시 보지 않습니다.
    """

    model_config = _FROZEN

    items: list[ReviewQueueItem]
    total: int
    rejection_reasons: list[dict[str, str]] = Field(
        description=(
            "기각 사유는 닫힌 목록입니다. 자유 서술은 셀 수 없고, 기각을 기록하는 이유가 "
            "**자동 판정이 어디서 빗나가는지 세기 위해서**입니다."
        )
    )


class ReviewDecisionRequest(BaseModel):
    """검수자의 결론.

    **자동 판정은 이 요청으로 바뀌지 않습니다.** 사람의 결론은 별도 칸에 쌓이고, 두 기록이
    어긋나는 경우까지 나란히 남습니다. 사람이 옳다고 해서 기계가 뭐라고 했는지를 지우면
    자동 판정이 어디서 빗나가는지 셀 수 없게 됩니다.
    """

    model_config = _FROZEN

    decision: Literal["CONFIRMED", "REJECTED", "NEEDS_MORE_EVIDENCE"]
    rejection_reason: (
        Literal[
            "CLAIM_IS_ACCURATE",
            "EVIDENCE_INSUFFICIENT",
            "WRONG_ENTITY",
            "SPAN_MISREAD",
            "DUPLICATE",
            "OUT_OF_SCOPE",
        ]
        | None
    ) = Field(default=None, description="기각할 때는 필수입니다.")
    note_ko: str | None = Field(default=None, max_length=2000)


class ReviewedItemPayload(BaseModel):
    """한 건의 검수 결과 — 기계가 뭐라고 했는지와 함께."""

    model_config = _FROZEN

    assessment_id: uuid.UUID
    stage: str
    stage_label_ko: str
    stored_as: str
    is_reviewed: bool
    disagrees_with_automation: bool = Field(
        description=(
            "사람의 결론이 자동 판정과 어긋나는가. 이 값이 쌓이는 곳이 곧 자동 판정을 "
            "고쳐야 하는 자리입니다."
        )
    )

class EngineSpendPayload(BaseModel):
    """엔진 하나가 이 달에 쓴 만큼."""

    model_config = ConfigDict(extra="forbid")

    engine: str
    calls: int
    input_tokens: int
    output_tokens: int
    measured_cost_usd: float
    #: 이 엔진에서 금액을 낼 수 없었던 호출 수.
    unmeasurable_calls: int


class SpendPayload(BaseModel):
    """이번 달 지출 — 잰 것과 못 잰 것을 나눠서.

    `measured_cost_usd` 에 못 잰 호출을 0으로 더하지 않는다. 더하면 합계가 "예산 안"
    처럼 보이는데 자료가 그걸 뒷받침하지 않는다. 그래서 `unmeasurable_calls` 와
    `remedies_ko` 가 같은 무게로 함께 나간다.
    """

    model_config = ConfigDict(extra="forbid")

    month: str
    total_calls: int
    measured_calls: int
    unmeasurable_calls: int
    measured_cost_usd: float
    input_tokens: int
    output_tokens: int
    #: COMPLETE | PARTIAL | NONE — 금액이 얼마나 실측인지.
    measurement: str
    engines: list[EngineSpendPayload] = Field(default_factory=list)
    #: 금액을 알 수 있게 하려면 지금 무엇을 해야 하는지. 해당하는 것만.
    remedies_ko: list[str] = Field(default_factory=list)
    summary_ko: str

