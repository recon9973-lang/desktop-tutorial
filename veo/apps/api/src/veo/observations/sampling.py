"""Proportions, and the honesty required to publish one.

Observed AI visibility is a set of rates: how often a brand was mentioned, how often it
was cited. Rates from small samples are the most confidently wrong numbers this product
can produce. Two mentions in three runs is "66.7%", and it is also consistent with a true
rate anywhere from about 20% to 94% — printed to one decimal beside a competitor's
"50.0%", it invents a ranking out of noise.

Three rules, from the VEO-LAB sampling methodology:

* Every proportion carries a **Wilson 95% interval**. The normal approximation is not
  usable here: at n=3 it produces intervals that leave [0, 1] entirely.
* Below the exploration minimum of 3 runs there is **no percentage at all**. Between 3
  and 5 the rate is directional — rounded to whole numbers, labelled as a direction
  rather than a measurement.
* **No observations is not 0%.** "We never saw it" and "we never looked" are different
  facts and are never rendered the same way.

There is a fourth rule that the first three quietly depend on, and it is about *time*
rather than count — see :class:`RepetitionSpread`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from itertools import pairwise
from typing import Any

#: Exploration diagnosis: at least this many runs per prompt x engine.
MIN_RUNS_FOR_EXPLORATION = 3

#: Comparative reporting: the methodology asks for five or more.
MIN_RUNS_FOR_COMPARISON = 5

#: 같은 질문의 반복 사이에 이만큼은 벌어져 있어야 "서로 다른 시점" 으로 친다.
#:
#: **이 값은 측정해서 얻은 것이 아니라 우리가 정한 운영 기준이다.** 방법론이 말하는
#: 것은 "같은 날 한꺼번에 몰지 말고 시간대를 분산" 이고, 그것은 시간 단위를 뜻한다.
#: 한 번의 실행 안에서 시간 단위로 벌릴 수는 없으므로, 여기서 고른 값은 **타협**이다 —
#: 상관을 없애지 못하고 줄일 뿐이다. 그래서 이 기준을 넘겨도 캐비엇은 사라지지 않고
#: 문장만 바뀐다(:meth:`RepetitionSpread.caveat_ko`).
MIN_SPREAD_BETWEEN_REPETITIONS = timedelta(minutes=2)

#: Two-sided 95% normal quantile, used for the Wilson score interval.
Z_95 = 1.959963984540054


class SampleAdequacy(StrEnum):
    """How much weight the sample can bear."""

    NO_DATA = "NO_DATA"
    TOO_SMALL = "TOO_SMALL"
    DIRECTIONAL = "DIRECTIONAL"
    ADEQUATE = "ADEQUATE"


class InsufficientSampleError(ValueError):
    """The caller asked for a claim the sample cannot support."""


def wilson_interval(*, successes: int, trials: int, z: float = Z_95) -> tuple[float, float]:
    """The Wilson score interval for a binomial proportion.

    Chosen over the textbook normal approximation because that one breaks exactly where
    this product needs an interval most: at n=3, ``p ± z·sqrt(p(1-p)/n)`` runs past 1.0
    and past 0.0, and at p=0 it collapses to a spurious zero-width interval implying
    certainty from a handful of observations.
    """
    if trials <= 0:
        raise ValueError("trials must be positive; a rate over zero runs is not a rate")
    if successes < 0:
        raise ValueError("successes cannot be negative")
    if successes > trials:
        raise ValueError("successes cannot exceed trials")

    proportion = successes / trials
    denominator = 1 + z**2 / trials
    centre = proportion + z**2 / (2 * trials)
    spread = z * math.sqrt(proportion * (1 - proportion) / trials + z**2 / (4 * trials**2))

    low = (centre - spread) / denominator
    high = (centre + spread) / denominator
    return max(0.0, low), min(1.0, high)


@dataclass(frozen=True, slots=True)
class ObservedRate:
    """A measured proportion, together with everything needed to read it correctly."""

    label_ko: str
    successes: int
    trials: int
    value: float | None
    confidence_low: float | None
    confidence_high: float | None
    adequacy: SampleAdequacy
    #: An extra caveat from the caller, appended to the one the sample size earns.
    #: Used when runs from different engines were deliberately pooled.
    extra_qualifier_ko: str = ""

    @classmethod
    def build(cls, *, successes: int, trials: int, label_ko: str) -> ObservedRate:
        if trials < 0 or successes < 0:
            raise ValueError("counts cannot be negative")
        if successes > trials:
            raise ValueError("successes cannot exceed trials")

        if trials == 0:
            return cls(
                label_ko=label_ko,
                successes=0,
                trials=0,
                value=None,
                confidence_low=None,
                confidence_high=None,
                adequacy=SampleAdequacy.NO_DATA,
            )

        low, high = wilson_interval(successes=successes, trials=trials)

        if trials < MIN_RUNS_FOR_EXPLORATION:
            # Deliberately no value. A proportion this thin reads as a measurement and
            # is not one; withholding it is more informative than publishing it.
            adequacy = SampleAdequacy.TOO_SMALL
            value: float | None = None
        elif trials < MIN_RUNS_FOR_COMPARISON:
            adequacy = SampleAdequacy.DIRECTIONAL
            value = successes / trials
        else:
            adequacy = SampleAdequacy.ADEQUATE
            value = successes / trials

        return cls(
            label_ko=label_ko,
            successes=successes,
            trials=trials,
            value=value,
            confidence_low=low,
            confidence_high=high,
            adequacy=adequacy,
        )

    # ----------------------------------------------------------------- #
    # Rendering
    # ----------------------------------------------------------------- #

    @property
    def percentage_text_ko(self) -> str:
        if self.value is None:
            return "표본 부족" if self.adequacy is SampleAdequacy.TOO_SMALL else "데이터 없음"
        if self.adequacy is SampleAdequacy.DIRECTIONAL:
            # Whole numbers only: a decimal place claims precision the sample lacks.
            return f"{round(self.value * 100)}%"
        return f"{self.value * 100:.1f}%"

    @property
    def qualifier_ko(self) -> str:
        return f"{self._sample_qualifier_ko} {self.extra_qualifier_ko}".strip()

    @property
    def _sample_qualifier_ko(self) -> str:
        return {
            SampleAdequacy.NO_DATA: "관측 실행이 없어 값이 없습니다.",
            SampleAdequacy.TOO_SMALL: (
                f"실행 {self.trials}회로는 비율을 말할 수 없습니다 "
                f"(최소 {MIN_RUNS_FOR_EXPLORATION}회)."
            ),
            SampleAdequacy.DIRECTIONAL: (
                "표본이 작아 방향성만 나타냅니다. 정확한 비율로 읽지 마세요."
            ),
            SampleAdequacy.ADEQUATE: "",
        }[self.adequacy]

    @property
    def interval_text_ko(self) -> str:
        if self.confidence_low is None or self.confidence_high is None:
            return "신뢰구간 없음"
        return f"95% 신뢰구간 {self.confidence_low * 100:.1f}% ~ {self.confidence_high * 100:.1f}%"

    @property
    def summary_ko(self) -> str:
        """One line carrying the rate, the denominator, the interval and the caveat.

        The denominator is not optional. A percentage without "of how many" is the shape
        the misleading number always takes.
        """
        if self.adequacy is SampleAdequacy.NO_DATA:
            return f"{self.label_ko}: 데이터 없음 (관측 실행 0회)"
        head = (
            f"{self.label_ko}: {self.percentage_text_ko} "
            f"({self.trials}회 중 {self.successes}회, {self.interval_text_ko})"
        )
        return f"{head} — {self.qualifier_ko}" if self.qualifier_ko else head

    # ----------------------------------------------------------------- #
    # Comparison
    # ----------------------------------------------------------------- #

    def is_distinguishable_from(self, other: ObservedRate) -> bool:
        """Whether the two rates differ by more than their uncertainty.

        Non-overlapping 95% intervals is a conservative test — it is stricter than a
        formal two-proportion test, so it will occasionally call a real difference
        indistinguishable. In a report handed to a customer that is the right direction
        to be wrong in.
        """
        if self.value is None or other.value is None:
            return False
        if None in (self.confidence_low, self.confidence_high):
            return False
        if None in (other.confidence_low, other.confidence_high):
            return False
        assert self.confidence_high is not None and other.confidence_low is not None
        assert self.confidence_low is not None and other.confidence_high is not None
        return (
            self.confidence_low > other.confidence_high
            or other.confidence_low > self.confidence_high
        )

    def require_comparison_grade(self) -> None:
        """Raise unless this sample is large enough to put in a competitive report."""
        if self.trials < MIN_RUNS_FOR_COMPARISON:
            raise InsufficientSampleError(
                f"{self.label_ko}: 비교 보고에는 실행 {MIN_RUNS_FOR_COMPARISON}회 이상이 "
                f"필요합니다. 현재 {self.trials}회입니다."
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "label_ko": self.label_ko,
            "successes": self.successes,
            "trials": self.trials,
            "value": self.value,
            "confidence_low": self.confidence_low,
            "confidence_high": self.confidence_high,
            "adequacy": str(self.adequacy),
            "percentage_text_ko": self.percentage_text_ko,
            "interval_text_ko": self.interval_text_ko,
            "qualifier_ko": self.qualifier_ko,
            "summary_ko": self.summary_ko,
        }


# --------------------------------------------------------------------------- #
# 네 번째 규칙 — 반복이 **언제** 일어났는가
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class RepetitionSpread:
    """같은 질문의 반복이 시간적으로 얼마나 벌어져 있었나.

    ## 왜 개수만으로는 부족한가

    위의 세 규칙은 전부 **횟수**에 관한 것이고, 셋 다 조용한 가정 하나에 기대고 있다 —
    반복이 서로 독립이라는 것. Wilson 구간은 그 가정 위에서만 성립한다.

    그런데 3회를 같은 순간에 몰아 던지면 독립이 아니다. 그 시각에 그 모델이 어떤
    상태였는지, 검색 색인이 무엇을 들고 있었는지가 **세 번에 똑같이 묻어난다.** 사실상
    한 번 본 것을 세 번 센 것에 가깝고, 그런데도 구간은 세 번이 독립이라고 계산되므로
    **실제보다 좁게 나온다.** 좁은 구간은 넓은 구간보다 위험하다 — 더 확신에 차 보이기
    때문이다.

    ## 그래서 여기서 하는 일

    구간을 **다시 계산하지 않는다.** 상관을 얼마나 먹었는지 우리는 모르고, 모르는 값으로
    보정하면 그것도 지어낸 숫자다(0-A). 대신 **실제로 얼마나 벌어졌는지를 그대로 적고**,
    그 구간을 좁게 읽지 말라고 말한다.

    캐비엇은 기준을 넘겨도 **사라지지 않는다.** 한 번의 실행 안에서 벌릴 수 있는 것은
    분 단위인데 방법론이 요구하는 것은 시간대 분산이라, 어느 쪽이든 완전한 독립은
    아니기 때문이다. 문장만 바뀐다.
    """

    #: 같은 (질문·조건)의 연속한 두 반복 사이 간격 가운데 **가장 짧은 것**.
    #: 평균이 아니라 최솟값을 쓴다 — 하나라도 붙어 있으면 그 쌍이 약한 고리다.
    shortest_gap: timedelta | None
    #: 간격을 잴 수 있었던 쌍의 수. 0 이면 반복이 하나뿐이라 잴 것이 없다.
    measured_pairs: int

    @classmethod
    def of(cls, moments_by_group: dict[str, list[datetime]]) -> RepetitionSpread:
        """(질문·조건)별 실행 시각들에서 가장 짧은 간격을 찾는다."""
        shortest: timedelta | None = None
        pairs = 0
        for moments in moments_by_group.values():
            ordered = sorted(moments)
            for earlier, later in pairwise(ordered):
                pairs += 1
                gap = later - earlier
                if shortest is None or gap < shortest:
                    shortest = gap
        return cls(shortest_gap=shortest, measured_pairs=pairs)

    @property
    def is_spread_out(self) -> bool:
        """운영 기준을 넘겼는가. 넘겨도 '독립' 이라는 뜻은 아니다."""
        return self.shortest_gap is not None and self.shortest_gap >= MIN_SPREAD_BETWEEN_REPETITIONS

    @property
    def caveat_ko(self) -> str | None:
        """비율 옆에 함께 나가야 하는 문장. 반복이 없으면 `None`."""
        if self.shortest_gap is None:
            return None
        gap = _duration_ko(self.shortest_gap)
        if self.is_spread_out:
            return (
                f"같은 질문의 반복은 최소 {gap} 간격으로 실행했습니다. 다만 한 번의 실행 "
                "안에서 벌린 것이라 날짜·시간대가 다른 측정만큼 독립적이지는 않습니다 — "
                "신뢰구간을 실제보다 좁게 읽지 마십시오."
            )
        return (
            f"같은 질문의 반복이 {gap} 만에 연달아 실행됐습니다. 그 순간 엔진의 상태가 "
            "반복 전체에 똑같이 묻어나므로 **서로 독립적인 표본이 아닙니다.** "
            "신뢰구간은 실제보다 좁습니다 — 이 구간을 근거로 경쟁사와 순위를 매기지 "
            "마십시오."
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "shortest_gap_seconds": (
                None if self.shortest_gap is None else int(self.shortest_gap.total_seconds())
            ),
            "measured_pairs": self.measured_pairs,
            "is_spread_out": self.is_spread_out,
            "caveat_ko": self.caveat_ko,
        }


def _duration_ko(value: timedelta) -> str:
    seconds = int(value.total_seconds())
    if seconds < 60:
        return f"{seconds}초"
    if seconds < 3600:
        return f"{seconds // 60}분"
    return f"{seconds // 3600}시간 {(seconds % 3600) // 60}분".removesuffix(" 0분")
