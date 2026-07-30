"""관측 지표 — 무엇을 몇 번 보았고, 그 값을 얼마나 믿을 수 있는가.

## 분모가 이 모듈의 전부다

비율은 분자보다 분모에서 거짓말한다. 여기서 다루는 두 비율은 분모가 서로 다르고, 그
차이가 정직성의 전부다.

``언급률`` = 브랜드가 언급된 응답 / **유효한 응답**
    실행이 실패했으면(오류 코드가 있거나 원문이 없으면) 언급이 없었던 것이 아니라
    **재지 못한 것**이다. 분모에서 뺀다.

``인용률`` = 브랜드가 인용된 응답 / **인용을 볼 수 있었던 응답**
    엔진이 출처를 밝히지 않은 응답은 "우리를 인용하지 않았다" 가 아니라 "누구를
    인용했는지 알 수 없다" 이다. 그것을 분모에 넣으면 인용률이 낮게 나오고, **그 낮은
    값은 사이트 탓처럼 읽힌다.** 실제로는 검색을 껐거나, 켰어도 인용을 돌려주지 않는
    모델을 골랐거나다(`CITATION_CAPABLE_MODEL_PREFIXES` 참조).

같은 부류의 결함을 어댑터 층에서 한 번 고쳤다. 이 모듈은 그것이 지표까지 살아남게 한다.

## 한 번은 비율이 아니다

AI 답변은 같은 질문에도 매번 달라진다. 그래서 실행 횟수와 함께 **신뢰구간**을 낸다.
표본이 적으면 구간이 넓어지고, 넓은 구간은 "이 숫자로 결론 내지 마라" 는 뜻이다.
Wilson 구간을 쓴다 — 정규 근사는 0%나 100% 근처에서 구간이 0으로 붕괴해, 세 번 다
언급된 브랜드에 "100%, 오차 없음" 이라고 말하게 된다.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import final

#: 인용을 구조적으로 볼 수 있었던 응답에만 붙는 값.
STRUCTURED = "STRUCTURED"

#: 표본이 이보다 적으면 비율을 숫자로 제시하지 않는다.
MIN_SAMPLE_FOR_A_RATE = 3


@final
@dataclass(frozen=True, slots=True)
class Rate:
    """비율 하나 — 분자, 분모, 그리고 그 값을 얼마나 믿을 수 있는가.

    분모를 함께 들고 다니는 것이 요점이다. `0.0` 만 돌려주면 "한 번도 안 됐다" 와
    "잴 수 없었다" 가 같은 모양이 된다.
    """

    numerator: int
    denominator: int
    #: 분모가 0 이면 `None`. 0.0 이 아니다 — 0.0 은 "쟀는데 없었다" 는 뜻이다.
    value: float | None
    low: float | None
    high: float | None
    is_reportable: bool
    note_ko: str

    @property
    def percent(self) -> float | None:
        return None if self.value is None else round(self.value * 100, 1)

    def as_dict(self) -> dict[str, object]:
        return {
            "numerator": self.numerator,
            "denominator": self.denominator,
            "value": self.value,
            "percent": self.percent,
            "low": self.low,
            "high": self.high,
            "is_reportable": self.is_reportable,
            "note_ko": self.note_ko,
        }


def wilson_interval(successes: int, trials: int, *, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson 점수 구간.

    정규 근사를 쓰지 않는 이유는 경계다. 세 번 모두 언급된 브랜드에 정규 근사는
    "100%, 오차 0" 을 준다 — 세 번 본 것으로 확신을 주장하는 셈이고, 그것이 이 제품이
    만들지 않기로 한 종류의 그럴듯한 숫자다.
    """
    if trials <= 0:
        return (0.0, 0.0)
    phat = successes / trials
    denominator = 1 + z**2 / trials
    centre = phat + z**2 / (2 * trials)
    spread = z * math.sqrt((phat * (1 - phat) + z**2 / (4 * trials)) / trials)
    low = (centre - spread) / denominator
    high = (centre + spread) / denominator
    return (max(0.0, round(low, 4)), min(1.0, round(high, 4)))


def rate(
    numerator: int,
    denominator: int,
    *,
    empty_note_ko: str,
    thin_note_ko: str,
    ok_note_ko: str = "",
) -> Rate:
    """분자와 분모로 비율 하나를 만든다. 분모가 없으면 값도 없다."""
    if denominator <= 0:
        return Rate(
            numerator=0,
            denominator=0,
            value=None,
            low=None,
            high=None,
            is_reportable=False,
            note_ko=empty_note_ko,
        )

    low, high = wilson_interval(numerator, denominator)
    thin = denominator < MIN_SAMPLE_FOR_A_RATE
    return Rate(
        numerator=numerator,
        denominator=denominator,
        value=round(numerator / denominator, 4),
        low=low,
        high=high,
        is_reportable=not thin,
        note_ko=thin_note_ko if thin else ok_note_ko,
    )


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
    mention_rate: Rate
    citation_rate: Rate
    prompt_coverage: Rate
    is_partial_measurement: bool
    caveats_ko: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "answers_recorded": self.answers_recorded,
            "answers_valid": self.answers_valid,
            "answers_with_visible_citations": self.answers_with_visible_citations,
            "mention_rate": self.mention_rate.as_dict(),
            "citation_rate": self.citation_rate.as_dict(),
            "prompt_coverage": self.prompt_coverage.as_dict(),
            "is_partial_measurement": self.is_partial_measurement,
            "caveats_ko": list(self.caveats_ko),
        }


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

    return VisibilityMetrics(
        answers_recorded=len(answers),
        answers_valid=len(valid),
        answers_with_visible_citations=len(visible),
        mention_rate=rate(
            sum(1 for answer in valid if answer.mentioned),
            len(valid),
            empty_note_ko=(
                "응답을 하나도 받지 못해 언급률을 낼 수 없습니다. 0%가 아니라 측정 "
                "불가입니다."
            ),
            thin_note_ko=(
                f"응답이 {len(valid)}건뿐입니다. 최소 {MIN_SAMPLE_FOR_A_RATE}건은 되어야 "
                "비율로 말할 수 있습니다."
            ),
        ),
        citation_rate=rate(
            sum(1 for answer in visible if answer.cited),
            len(visible),
            empty_note_ko=(
                "출처를 확인할 수 있었던 응답이 없어 인용률을 낼 수 없습니다. 0%가 "
                "아니라 측정 불가입니다 — 엔진이 어느 출처를 썼는지 알려주지 않았습니다."
            ),
            thin_note_ko=(
                f"출처를 확인할 수 있었던 응답이 {len(visible)}건뿐입니다. 최소 "
                f"{MIN_SAMPLE_FOR_A_RATE}건은 되어야 비율로 말할 수 있습니다."
            ),
        ),
        prompt_coverage=rate(
            len(mentioned_prompts),
            len(prompts_seen) or prompts_planned,
            empty_note_ko="던진 질문이 없어 질문 도달률을 낼 수 없습니다.",
            thin_note_ko=(
                f"응답을 받은 질문이 {len(prompts_seen)}개뿐입니다. 최소 "
                f"{MIN_SAMPLE_FOR_A_RATE}개는 되어야 비율로 말할 수 있습니다."
            ),
        ),
        is_partial_measurement=not run_is_complete,
        caveats_ko=tuple(caveats),
    )


__all__ = [
    "MIN_SAMPLE_FOR_A_RATE",
    "STRUCTURED",
    "AnswerFact",
    "Rate",
    "VisibilityMetrics",
    "rate",
    "visibility_metrics",
    "wilson_interval",
]
