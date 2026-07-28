"""VEO's opportunity score — a versioned, fully decomposed calculation.

This number is **VEO's own arithmetic**, not a figure Naver publishes. Everything about
this module is arranged so a customer can be shown why the number is what it is:

* every component is returned separately, with its weight and its contribution;
* every constant used is written into the trace;
* the formula version is recorded with the result, so a score from six months ago can
  still be explained by the rules that produced it;
* a component VEO could not compute comes back as ``None`` with a Korean reason, never as
  ``0`` — a zeroed component reads as "measured, and it is bad".

The formula, per ``docs/research/VEO_CLAUDE_DEVELOPMENT_MASTER_PROMPT.md`` §8.4::

    opportunity_score = 100 * confidence * (
        0.30*demand + 0.20*trend + 0.20*intent_fit
        + 0.15*competition_inverse + 0.15*content_gap
    )

Two decisions worth stating plainly, because they are judgement calls rather than
transcriptions of the specification:

**A missing component contributes nothing to the weighted sum, and lowers confidence by
its weight.** The alternative — renormalising the remaining weights — makes a score built
from two components look exactly as authoritative as one built from five.

**Without demand there is no score at all.** Demand is the only component sourced from an
official measurement; the rest are estimates and inputs. A "keyword opportunity" computed
without knowing whether anyone searches for the keyword is not a weaker answer, it is a
different and misleading one. With no Naver credential this is the path every lookup
takes, which is exactly as it should be.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final, Protocol, final

from veo.contracts.enums import DataSource, ValueQuality
from veo.providers.naver.datalab import TrendPoint
from veo.providers.naver.searchad import SearchCount

__all__ = [
    "COMPETITION_LABEL_INVERSE",
    "DEMAND_REFERENCE_MONTHLY_SEARCHES",
    "DISCLOSURE_KO",
    "FORMULA_VERSION",
    "FRESHNESS_DECAY_DAYS",
    "FRESHNESS_FLOOR",
    "FRESHNESS_FULL_DAYS",
    "WEIGHTS",
    "OpportunityComponent",
    "OpportunityInputs",
    "OpportunityResult",
    "StoredOpportunityLike",
    "rebuild_result",
    "score",
    "trend_component",
]

#: Bump this whenever any constant or rule below changes. It is stored with every score.
FORMULA_VERSION: Final = "veo.keyword.opportunity.v1"

WEIGHTS: Final[dict[str, float]] = {
    "demand": 0.30,
    "trend": 0.20,
    "intent_fit": 0.20,
    "competition_inverse": 0.15,
    "content_gap": 0.15,
}

#: The monthly volume at which ``demand`` reaches 1.0. A VEO constant chosen so that the
#: mid-tail keywords an agency actually works on occupy the middle of the range, not so
#: that the largest keyword in Korea scores 1.0 and everything else rounds to nothing.
DEMAND_REFERENCE_MONTHLY_SEARCHES: Final = 100_000

#: Naver publishes an advertising competition *label*. This table is VEO's reading of it,
#: not a Naver figure, and it is written into every trace for that reason. It describes
#: **advertising** competition; organic difficulty is a separate estimate VEO does not
#: derive from this field.
COMPETITION_LABEL_INVERSE: Final[dict[str, float]] = {
    "낮음": 1.0,
    "중간": 0.5,
    "높음": 0.0,
    "LOW": 1.0,
    "MID": 0.5,
    "HIGH": 0.0,
}

#: Data collected within this many days is treated as current.
FRESHNESS_FULL_DAYS: Final = 7
#: Beyond this many days the freshness factor stops falling.
FRESHNESS_DECAY_DAYS: Final = 90
#: Old data is still data. Confidence drops; it does not vanish.
FRESHNESS_FLOOR: Final = 0.5

DISCLOSURE_KO: Final = (
    "기회 점수는 네이버가 제공하는 수치가 아니라 VEO가 자체 산식으로 계산한 값입니다. "
    "구성요소·가중치·산식 버전을 모두 공개하며, 계산에 쓰이지 못한 항목은 0이 아니라 "
    "'측정 불가'로 표시하고 신뢰도에 반영합니다."
)

_COMPONENT_NOTES_KO: Final[Mapping[str, str]] = {
    "demand": "월간 총 검색량(네이버 검색광고)을 로그 정규화한 수요 지표입니다.",
    "trend": "네이버 데이터랩 상대 관심도의 상승·하락 추세입니다. 검색량이 아닙니다.",
    "intent_fit": "입력된 사업·페이지 목적 적합도입니다. VEO 외부에서 지정하는 값입니다.",
    "competition_inverse": (
        "광고 경쟁 정도(compIdx 라벨)를 뒤집은 값입니다. 자연검색 경쟁 난이도가 아닙니다."
    ),
    "content_gap": "자사 미보유·경쟁사 보유 콘텐츠 격차입니다. VEO 외부에서 지정하는 값입니다.",
}

#: Where each component's input comes from. Reported per component so a customer can see
#: which parts of the score are official measurements and which are VEO's or their own.
_COMPONENT_SOURCES: Final[Mapping[str, DataSource]] = {
    "demand": DataSource.NAVER_SEARCH_AD,
    "trend": DataSource.NAVER_DATALAB,
    "intent_fit": DataSource.VEO_INTERNAL,
    "competition_inverse": DataSource.NAVER_SEARCH_AD,
    "content_gap": DataSource.VEO_INTERNAL,
}

_UNAVAILABLE_KO: Final = "이 구성요소를 계산할 자료가 없어 점수에 반영하지 않았습니다."
_DEMAND_UNMEASURED_KO: Final = (
    "월간 검색량이 정확한 수치로 제공되지 않아(억제·구간·결측) 수요를 계산할 수 없습니다. "
    "0회가 아니라 '측정 불가'입니다."
)
_NO_SCORE_KO: Final = (
    "수요(demand)를 계산할 수 없어 기회 점수를 산출하지 않았습니다. 다른 구성요소만으로 점수를 "
    "만들면 검색 수요를 모른 채 '기회'를 주장하는 셈이 됩니다."
)


@final
@dataclass(frozen=True, slots=True)
class OpportunityComponent:
    """One term of the formula, with everything needed to explain it."""

    name: str
    weight: float
    value: float | None
    contribution: float | None
    note_ko: str
    source: DataSource
    unavailable_reason_ko: str | None = None


@final
@dataclass(frozen=True, slots=True)
class OpportunityResult:
    """A score, or a stated reason there is none — plus the whole calculation."""

    formula_version: str
    score: float | None
    weighted_sum: float
    coverage: float
    freshness: float
    confidence: float
    components: tuple[OpportunityComponent, ...]
    missing_components: tuple[str, ...]
    trace: Mapping[str, Any]
    source: DataSource = DataSource.CALCULATED
    disclosure_ko: str = DISCLOSURE_KO
    unavailable_reason_ko: str | None = None


@final
@dataclass(frozen=True, slots=True)
class OpportunityInputs:
    """Everything the formula reads, with the types it insists on.

    ``monthly_total_searches`` is a :class:`~veo.providers.naver.searchad.SearchCount`
    rather than an ``int`` on purpose. A bare integer has lost the quality flag that says
    whether it is a measurement, a suppressed value, or a bound — and once that is gone,
    a suppressed keyword scores as one with zero demand.
    """

    monthly_total_searches: SearchCount | None
    trend: float | None
    intent_fit: float | None
    competition_label: str | None
    collected_at: datetime | None
    now: datetime
    content_gap: float | None = None
    extra_trace: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.monthly_total_searches is not None and not isinstance(
            self.monthly_total_searches, SearchCount
        ):
            raise TypeError(
                "monthly_total_searches must be a SearchCount carrying its own quality "
                f"flag; got {type(self.monthly_total_searches).__name__}"
            )
        for name in ("trend", "intent_fit", "content_gap"):
            value = getattr(self, name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise TypeError(f"{name} must be a ratio between 0 and 1, or None")
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")


def trend_component(points: Sequence[TrendPoint]) -> float | None:
    """A 0-1 trend from a DataLab series, or ``None`` when there is not enough series.

    The output is a **unitless ratio**, never a count: it compares the later half of the
    window against the earlier half and maps the log of that ratio onto 0-1 with a
    saturating curve, so a doubling and a tenfold rise are both "rising" without one
    swamping the score. A flat series lands on exactly 0.5.

    Fewer than two points cannot describe a direction, so the answer is "no trend" rather
    than a neutral 0.5 that would be indistinguishable from a measured flat line.
    """
    count = len(points)
    if count < 2:
        return None

    half = count // 2
    earlier = [point.relative_index.value for point in points[:half]]
    later = [point.relative_index.value for point in points[-half:]]

    early_mean = sum(earlier) / len(earlier)
    late_mean = sum(later) / len(later)

    epsilon = 1e-9
    ratio = (late_mean + epsilon) / (early_mean + epsilon)
    return 0.5 * (1.0 + math.tanh(math.log(ratio) / 2.0))


def _demand(total: SearchCount | None) -> tuple[float | None, str | None]:
    if total is None:
        return None, _UNAVAILABLE_KO
    if total.value is None:
        return None, _DEMAND_UNMEASURED_KO
    if total.quality not in {ValueQuality.EXACT, ValueQuality.ROUNDED}:
        return None, _DEMAND_UNMEASURED_KO
    normalised = math.log1p(total.value) / math.log1p(DEMAND_REFERENCE_MONTHLY_SEARCHES)
    return min(1.0, max(0.0, normalised)), None


def _competition_inverse(label: str | None) -> tuple[float | None, str | None]:
    if label is None:
        return None, _UNAVAILABLE_KO
    value = COMPETITION_LABEL_INVERSE.get(label.strip())
    if value is None:
        return None, (
            f"경쟁도 라벨 '{label}'은 VEO가 아는 값이 아닙니다. 임의로 해석하지 않고 "
            "점수에서 제외했습니다."
        )
    return value, None


def _freshness(collected_at: datetime | None, now: datetime) -> float:
    if collected_at is None:
        return FRESHNESS_FLOOR
    age_days = max(0.0, (now - collected_at).total_seconds() / 86_400.0)
    if age_days <= FRESHNESS_FULL_DAYS:
        return 1.0
    if age_days >= FRESHNESS_DECAY_DAYS:
        return FRESHNESS_FLOOR
    span = FRESHNESS_DECAY_DAYS - FRESHNESS_FULL_DAYS
    travelled = (age_days - FRESHNESS_FULL_DAYS) / span
    return 1.0 - (1.0 - FRESHNESS_FLOOR) * travelled


def score(inputs: OpportunityInputs) -> OpportunityResult:
    """Compute the score, or explain why there is none."""
    demand_value, demand_reason = _demand(inputs.monthly_total_searches)
    competition_value, competition_reason = _competition_inverse(inputs.competition_label)

    raw: dict[str, tuple[float | None, str | None]] = {
        "demand": (demand_value, demand_reason),
        "trend": (inputs.trend, None if inputs.trend is not None else _UNAVAILABLE_KO),
        "intent_fit": (
            inputs.intent_fit,
            None if inputs.intent_fit is not None else _UNAVAILABLE_KO,
        ),
        "competition_inverse": (competition_value, competition_reason),
        "content_gap": (
            inputs.content_gap,
            None if inputs.content_gap is not None else _UNAVAILABLE_KO,
        ),
    }

    components: list[OpportunityComponent] = []
    missing: list[str] = []
    weighted_sum = 0.0
    coverage = 0.0

    for name, weight in WEIGHTS.items():
        value, reason = raw[name]
        contribution = None if value is None else weight * float(value)
        if value is None:
            missing.append(name)
        else:
            weighted_sum += float(contribution or 0.0)
            coverage += weight
        components.append(
            OpportunityComponent(
                name=name,
                weight=weight,
                value=None if value is None else float(value),
                contribution=contribution,
                note_ko=_COMPONENT_NOTES_KO[name],
                source=_COMPONENT_SOURCES[name],
                unavailable_reason_ko=reason,
            )
        )

    freshness = _freshness(inputs.collected_at, inputs.now)
    confidence = coverage * freshness

    has_demand = demand_value is not None
    final_score = 100.0 * confidence * weighted_sum if has_demand else None
    unavailable = None if has_demand else _NO_SCORE_KO

    trace: dict[str, Any] = {
        "formula_version": FORMULA_VERSION,
        "weights": dict(WEIGHTS),
        "demand_reference_monthly_searches": DEMAND_REFERENCE_MONTHLY_SEARCHES,
        "competition_label_inverse": dict(COMPETITION_LABEL_INVERSE),
        "freshness": {
            "value": freshness,
            "full_days": FRESHNESS_FULL_DAYS,
            "decay_days": FRESHNESS_DECAY_DAYS,
            "floor": FRESHNESS_FLOOR,
            "collected_at": inputs.collected_at.isoformat() if inputs.collected_at else None,
            "evaluated_at": inputs.now.isoformat(),
        },
        "coverage": coverage,
        "confidence": confidence,
        "weighted_sum": weighted_sum,
        "components": {
            component.name: {
                "value": component.value,
                "weight": component.weight,
                "contribution": component.contribution,
            }
            for component in components
        },
        "rule_ko": (
            "score = 100 * confidence * sum(weight * value), "
            "confidence = coverage * freshness"
        ),
        **dict(inputs.extra_trace),
    }

    return OpportunityResult(
        formula_version=FORMULA_VERSION,
        score=final_score,
        weighted_sum=weighted_sum,
        coverage=coverage,
        freshness=freshness,
        confidence=confidence,
        components=tuple(components),
        missing_components=tuple(missing),
        trace=trace,
        unavailable_reason_ko=unavailable,
    )


class StoredOpportunityLike(Protocol):
    """The shape :func:`rebuild_result` reads back — satisfied by the stored row.

    Declared structurally so ``opportunity.py`` does not import the repository. The
    calculation and its storage stay independent of each other.
    """

    # Read-only properties, so a frozen dataclass satisfies the protocol. Declaring them
    # as plain attributes would demand a settable member and reject exactly the immutable
    # record this is meant to accept.
    @property
    def formula_version(self) -> str: ...
    @property
    def demand(self) -> float | None: ...
    @property
    def trend(self) -> float | None: ...
    @property
    def intent_fit(self) -> float | None: ...
    @property
    def competition_inverse(self) -> float | None: ...
    @property
    def content_gap(self) -> float | None: ...
    @property
    def confidence(self) -> float: ...
    @property
    def opportunity_score(self) -> float | None: ...
    @property
    def calculation_trace(self) -> Mapping[str, Any]: ...
    @property
    def missing_components(self) -> tuple[str, ...]: ...


def rebuild_result(stored: StoredOpportunityLike) -> OpportunityResult:
    """Reassemble a stored score into the same shape a fresh calculation returns.

    A score read back from the database explains itself exactly as a fresh one does — the
    components, the weights and the trace are all recovered — which is what makes an old
    report auditable rather than merely re-displayable. Values come from the stored
    columns; the notes and weights come from the constants named by the stored
    ``formula_version``.
    """
    values: Mapping[str, float | None] = {
        "demand": stored.demand,
        "trend": stored.trend,
        "intent_fit": stored.intent_fit,
        "competition_inverse": stored.competition_inverse,
        "content_gap": stored.content_gap,
    }
    trace = dict(stored.calculation_trace)
    weighted_sum = float(trace.get("weighted_sum") or 0.0)
    coverage = float(trace.get("coverage") or 0.0)
    freshness_block = trace.get("freshness")
    freshness = (
        float(freshness_block.get("value", 0.0))
        if isinstance(freshness_block, dict)
        else 0.0
    )

    components = tuple(
        OpportunityComponent(
            name=name,
            weight=weight,
            value=values.get(name),
            contribution=None if values.get(name) is None else weight * float(values[name] or 0.0),
            note_ko=_COMPONENT_NOTES_KO[name],
            source=_COMPONENT_SOURCES[name],
            unavailable_reason_ko=None if values.get(name) is not None else _UNAVAILABLE_KO,
        )
        for name, weight in WEIGHTS.items()
    )

    return OpportunityResult(
        formula_version=stored.formula_version,
        score=stored.opportunity_score,
        weighted_sum=weighted_sum,
        coverage=coverage,
        freshness=freshness,
        confidence=stored.confidence,
        components=components,
        missing_components=tuple(stored.missing_components),
        trace=trace,
        unavailable_reason_ko=None if stored.opportunity_score is not None else _NO_SCORE_KO,
    )
