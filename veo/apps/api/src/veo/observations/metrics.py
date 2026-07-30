"""관측 지표 — 무엇을 몇 번 보았고, 그 값을 얼마나 믿을 수 있는가.

## 이 모듈이 하는 일은 분모를 고르는 것뿐이다

비율을 **만드는** 규칙은 여기 없다. Wilson 구간, 표본 하한(탐색 3회·비교 5회),
`value=None` 과 `0.0` 의 구분, 신뢰구간 겹침 판정은 전부
:mod:`veo.observations.sampling` 에 있고 이 모듈은 그것을 쓴다.

한 번 그러지 않았다가 값을 치렀다. 2026-07-30 에 `sampling.py` 를 모른 채 같은
계산을 여기에 다시 썼는데, **새로 쓴 쪽이 규칙을 더 느슨하게 어겼다** — 1~2회
표본에도 퍼센트를 내주고(0-C 는 아예 내지 말라고 한다), 비교 보고 5회 기준이
아예 없었다. 중복은 낭비로 끝나지 않는다. 나중에 만든 쪽이 원본의 제약을 모른 채
더 관대해진다. 지침서 0-D 가 그래서 생겼다.

## 남는 것: 어떤 응답이 분모에 들어가는가

세 비율의 분모가 서로 다르고, 그 차이가 정직성의 전부다.

``언급률`` = 브랜드가 언급된 응답 / **유효한 응답**
    실행이 실패했으면(오류 코드가 있거나 원문이 없으면) 언급이 없었던 것이 아니라
    **재지 못한 것**이다. 분모에서 뺀다.

``인용률`` = 브랜드가 인용된 응답 / **인용을 볼 수 있었던 응답**
    엔진이 출처를 밝히지 않은 응답은 "우리를 인용하지 않았다" 가 아니라 "누구를
    인용했는지 알 수 없다" 이다. 그것을 분모에 넣으면 인용률이 낮게 나오고, **그 낮은
    값은 사이트 탓처럼 읽힌다.** 실제로는 검색을 껐거나, 켰어도 인용을 돌려주지 않는
    모델을 골랐거나다(`CITATION_CAPABLE_MODEL_PREFIXES` 참조).

``질문 도달률`` = 언급이 확인된 질문 / **응답을 받은 질문**
    한 질문을 세 번 물어 세 번 언급됐다고 질문 셋을 덮은 것이 아니다. 응답이 아니라
    질문을 센다.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any, final

from veo.observations.sampling import (
    MIN_RUNS_FOR_COMPARISON,
    ObservedRate,
    SampleAdequacy,
)

#: 인용을 구조적으로 볼 수 있었던 응답에만 붙는 값.
STRUCTURED = "STRUCTURED"


def rate_payload(rate: ObservedRate) -> dict[str, Any]:
    """비율 하나를 화면·API 가 오해할 수 없는 모양으로 편다.

    숫자 퍼센트를 그대로 내보내지 않고 ``percent_text_ko`` 를 함께 준다. 표본이
    3~5회인 값은 소수점 없이 정수로 표시되어야 하는데, 원시 숫자만 주면 화면이
    습관적으로 소수점 한 자리를 붙이고 그 순간 표본이 감당 못 하는 정밀도를
    주장하게 된다.
    """
    return {
        "label_ko": rate.label_ko,
        "numerator": rate.successes,
        "denominator": rate.trials,
        "value": rate.value,
        "percent_text_ko": rate.percentage_text_ko,
        "low": rate.confidence_low,
        "high": rate.confidence_high,
        "adequacy": str(rate.adequacy),
        "is_comparison_grade": rate.trials >= MIN_RUNS_FOR_COMPARISON,
        "note_ko": rate.qualifier_ko,
        "summary_ko": rate.summary_ko,
    }


@final
@dataclass(frozen=True, slots=True)
class AnswerFact:
    """지표를 내는 데 필요한, 답변 한 건의 사실.

    DB 행을 그대로 받지 않는 것은 이 계산을 DB 없이 시험할 수 있게 하기 위해서다.
    """

    prompt_id: str
    is_valid: bool
    mentioned: bool
    cited: bool
    citation_support: str | None


@final
@dataclass(frozen=True, slots=True)
class VisibilityMetrics:
    """한 번의 관측이 말할 수 있는 것과, 말할 수 없는 것."""

    answers_recorded: int
    answers_valid: int
    answers_with_visible_citations: int
    mention_rate: ObservedRate
    citation_rate: ObservedRate
    prompt_coverage: ObservedRate
    is_partial_measurement: bool
    caveats_ko: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "answers_recorded": self.answers_recorded,
            "answers_valid": self.answers_valid,
            "answers_with_visible_citations": self.answers_with_visible_citations,
            "mention_rate": rate_payload(self.mention_rate),
            "citation_rate": rate_payload(self.citation_rate),
            "prompt_coverage": rate_payload(self.prompt_coverage),
            "is_partial_measurement": self.is_partial_measurement,
            "caveats_ko": list(self.caveats_ko),
        }


def _with_denominator_note(rate: ObservedRate, note_ko: str) -> ObservedRate:
    """분모가 비었을 때 "왜 비었는지" 를 붙인다.

    ``sampling`` 이 붙이는 "관측 실행이 없어 값이 없습니다" 는 세 비율에 모두 같은
    문장이라 도움이 안 된다. 인용률의 분모가 0 인 것은 실행이 없어서가 아니라 **엔진이
    출처를 안 알려줘서**일 수 있고, 화면에서 그 둘은 완전히 다른 조치로 이어진다.
    """
    if rate.adequacy is not SampleAdequacy.NO_DATA:
        return rate
    return replace(rate, extra_qualifier_ko=note_ko)


def visibility_metrics(
    answers: Sequence[AnswerFact],
    *,
    prompts_planned: int,
    run_is_complete: bool,
) -> VisibilityMetrics:
    """한 관측 실행의 지표.

    `run_is_complete` 가 거짓이면 모든 값에 **부분 측정** 표시가 붙는다. 계획한 질문의
    일부를 못 던진 실행의 비율은 그 자체로 틀린 값은 아니지만, 계획 전체에 대한 답이
    아니다. 그 차이가 표시되지 않으면 읽는 사람이 구분할 방법이 없다.
    """
    valid = [answer for answer in answers if answer.is_valid]
    visible = [answer for answer in valid if answer.citation_support == STRUCTURED]

    mentioned_prompts = {answer.prompt_id for answer in valid if answer.mentioned}
    prompts_seen = {answer.prompt_id for answer in valid}

    caveats: list[str] = []
    if not run_is_complete:
        caveats.append(
            "계획한 실행 가운데 일부가 수행되지 않았습니다. 아래 비율은 실제로 던진 "
            "질문에 대한 값이며, 계획 전체에 대한 답이 아닙니다."
        )
    if valid and not visible:
        caveats.append(
            "이번 실행의 어떤 응답에서도 출처를 확인할 수 없었습니다. 인용률은 0%가 "
            "아니라 **측정 불가**입니다. 검색을 켰는지, 그리고 고른 모델이 인용을 "
            "돌려주는 모델인지 확인해 주십시오."
        )
    if len(valid) < len(answers):
        caveats.append(
            f"실행 {len(answers)}건 가운데 {len(answers) - len(valid)}건은 응답을 받지 "
            "못했습니다. 그 건들은 '언급 없음' 이 아니라 분모에서 빠집니다."
        )

    mention_rate = ObservedRate.build(
        successes=sum(1 for answer in valid if answer.mentioned),
        trials=len(valid),
        label_ko="언급률",
    )
    citation_rate = _with_denominator_note(
        ObservedRate.build(
            successes=sum(1 for answer in visible if answer.cited),
            trials=len(visible),
            label_ko="인용률",
        ),
        "출처를 확인할 수 있었던 응답이 없습니다. 0%가 아니라 측정 불가입니다 — "
        "엔진이 어느 출처를 썼는지 알려주지 않았습니다.",
    )
    prompt_coverage = ObservedRate.build(
        successes=len(mentioned_prompts),
        trials=len(prompts_seen) or prompts_planned,
        label_ko="질문 도달률",
    )

    return VisibilityMetrics(
        answers_recorded=len(answers),
        answers_valid=len(valid),
        answers_with_visible_citations=len(visible),
        mention_rate=mention_rate,
        citation_rate=citation_rate,
        prompt_coverage=prompt_coverage,
        is_partial_measurement=not run_is_complete,
        caveats_ko=tuple(caveats),
    )


__all__ = [
    "STRUCTURED",
    "AnswerFact",
    "VisibilityMetrics",
    "rate_payload",
    "visibility_metrics",
]
