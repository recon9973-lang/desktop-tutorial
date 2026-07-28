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
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

#: Exploration diagnosis: at least this many runs per prompt x engine.
MIN_RUNS_FOR_EXPLORATION = 3

#: Comparative reporting: the methodology asks for five or more.
MIN_RUNS_FOR_COMPARISON = 5

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
