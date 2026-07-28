"""VEO's opportunity score.

This number is VEO's own arithmetic, not a Naver figure, and the tests hold it to the
standard that implies: the weights are the published ones, every component comes back
separately with its own contribution, the version travels with the result, and a missing
input produces a missing component — never a quietly substituted zero passed off as a
measurement.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from veo.contracts.enums import DataSource, ValueQuality
from veo.keywords.opportunity import (
    COMPETITION_LABEL_INVERSE,
    FORMULA_VERSION,
    WEIGHTS,
    OpportunityInputs,
    score,
    trend_component,
)
from veo.providers.naver.datalab import RelativeIndex, TrendPoint
from veo.providers.naver.searchad import SearchCount

NOW = datetime(2026, 7, 28, 3, 0, tzinfo=UTC)


def complete_inputs(**overrides: object) -> OpportunityInputs:
    base: dict[str, object] = {
        "monthly_total_searches": SearchCount(value=1111, quality=ValueQuality.EXACT),
        "trend": 0.5,
        "intent_fit": 0.5,
        "competition_label": "중간",
        "content_gap": 0.5,
        "collected_at": NOW,
        "now": NOW,
    }
    base.update(overrides)
    return OpportunityInputs(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# The published formula
# --------------------------------------------------------------------------- #


def test_weights_are_the_published_ones() -> None:
    assert WEIGHTS == {
        "demand": 0.30,
        "trend": 0.20,
        "intent_fit": 0.20,
        "competition_inverse": 0.15,
        "content_gap": 0.15,
    }
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_the_version_travels_with_the_result() -> None:
    result = score(complete_inputs())
    assert result.formula_version == FORMULA_VERSION
    assert result.source is DataSource.CALCULATED
    assert "VEO" in result.disclosure_ko


def test_components_are_returned_separately_and_sum_as_documented() -> None:
    result = score(complete_inputs())
    assert {component.name for component in result.components} == set(WEIGHTS)

    contributions = sum(
        component.contribution or 0.0 for component in result.components
    )
    assert result.weighted_sum == pytest.approx(contributions)
    assert result.score == pytest.approx(100.0 * result.confidence * result.weighted_sum)


def test_each_component_records_its_own_weight_and_contribution() -> None:
    result = score(complete_inputs())
    by_name = {component.name: component for component in result.components}
    for name, weight in WEIGHTS.items():
        component = by_name[name]
        assert component.weight == pytest.approx(weight)
        assert component.value is not None
        assert component.contribution == pytest.approx(weight * component.value)
        assert component.note_ko


def test_a_perfect_input_with_full_confidence_scores_one_hundred() -> None:
    result = score(
        complete_inputs(
            monthly_total_searches=SearchCount(value=10_000_000, quality=ValueQuality.EXACT),
            trend=1.0,
            intent_fit=1.0,
            competition_label="낮음",
            content_gap=1.0,
        )
    )
    assert result.confidence == pytest.approx(1.0)
    assert result.score == pytest.approx(100.0)


def test_the_trace_records_every_constant_used() -> None:
    trace = score(complete_inputs()).trace
    assert trace["formula_version"] == FORMULA_VERSION
    assert trace["weights"] == WEIGHTS
    assert "demand_reference_monthly_searches" in trace
    assert "competition_label_inverse" in trace
    assert "freshness" in trace


# --------------------------------------------------------------------------- #
# Demand
# --------------------------------------------------------------------------- #


def test_demand_is_a_normalised_log_of_the_total() -> None:
    smaller = score(
        complete_inputs(monthly_total_searches=SearchCount(value=100, quality=ValueQuality.EXACT))
    )
    larger = score(
        complete_inputs(
            monthly_total_searches=SearchCount(value=100_000, quality=ValueQuality.EXACT)
        )
    )
    small_demand = next(c for c in smaller.components if c.name == "demand").value
    large_demand = next(c for c in larger.components if c.name == "demand").value
    assert small_demand is not None
    assert large_demand is not None
    assert 0.0 <= small_demand < large_demand <= 1.0


def test_demand_of_zero_searches_is_zero_and_that_is_a_measurement() -> None:
    result = score(
        complete_inputs(monthly_total_searches=SearchCount(value=0, quality=ValueQuality.EXACT))
    )
    demand = next(c for c in result.components if c.name == "demand")
    assert demand.value == pytest.approx(0.0)
    assert demand.unavailable_reason_ko is None
    assert result.score is not None


def test_a_suppressed_total_does_not_become_a_demand_of_zero() -> None:
    """The distinction that matters most: "below 10" is not "nobody searches this"."""
    result = score(
        complete_inputs(
            monthly_total_searches=SearchCount(
                value=None,
                quality=ValueQuality.BELOW_PROVIDER_THRESHOLD,
                upper_bound_exclusive=10,
            )
        )
    )
    demand = next(c for c in result.components if c.name == "demand")
    assert demand.value is None
    assert demand.contribution is None
    assert demand.unavailable_reason_ko
    assert result.score is None


def test_without_demand_there_is_no_score_at_all() -> None:
    result = score(complete_inputs(monthly_total_searches=None))
    assert result.score is None
    assert "demand" in result.missing_components
    assert result.unavailable_reason_ko


# --------------------------------------------------------------------------- #
# Missing components lower confidence rather than being invented
# --------------------------------------------------------------------------- #


def test_a_missing_component_is_reported_missing_not_zeroed() -> None:
    result = score(complete_inputs(content_gap=None))
    gap = next(c for c in result.components if c.name == "content_gap")
    assert gap.value is None
    assert gap.contribution is None
    assert gap.unavailable_reason_ko
    assert "content_gap" in result.missing_components


def test_missing_components_reduce_confidence_by_their_weight() -> None:
    full = score(complete_inputs())
    without_gap = score(complete_inputs(content_gap=None))
    assert without_gap.coverage == pytest.approx(full.coverage - WEIGHTS["content_gap"])
    assert without_gap.confidence < full.confidence


def test_a_missing_component_contributes_nothing_to_the_weighted_sum() -> None:
    result = score(complete_inputs(content_gap=None))
    assert result.weighted_sum == pytest.approx(
        sum(c.contribution or 0.0 for c in result.components)
    )
    assert result.score == pytest.approx(100.0 * result.confidence * result.weighted_sum)


def test_stale_data_lowers_confidence_without_changing_the_components() -> None:
    fresh = score(complete_inputs())
    stale = score(complete_inputs(collected_at=NOW - timedelta(days=120)))
    assert stale.freshness < fresh.freshness
    assert stale.confidence < fresh.confidence
    assert stale.weighted_sum == pytest.approx(fresh.weighted_sum)


def test_confidence_is_coverage_times_freshness() -> None:
    result = score(complete_inputs(content_gap=None, collected_at=NOW - timedelta(days=30)))
    assert result.confidence == pytest.approx(result.coverage * result.freshness)


# --------------------------------------------------------------------------- #
# Competition
# --------------------------------------------------------------------------- #


def test_competition_label_maps_through_a_published_table() -> None:
    for label, expected in COMPETITION_LABEL_INVERSE.items():
        result = score(complete_inputs(competition_label=label))
        component = next(c for c in result.components if c.name == "competition_inverse")
        assert component.value == pytest.approx(expected)


def test_an_unrecognised_competition_label_is_missing_not_guessed() -> None:
    result = score(complete_inputs(competition_label="처음 보는 값"))
    component = next(c for c in result.components if c.name == "competition_inverse")
    assert component.value is None
    assert component.unavailable_reason_ko


def test_competition_component_is_labelled_as_advertising_competition() -> None:
    result = score(complete_inputs())
    component = next(c for c in result.components if c.name == "competition_inverse")
    assert "광고" in component.note_ko


# --------------------------------------------------------------------------- #
# The trend component, and the wall it must not breach
# --------------------------------------------------------------------------- #


def points(*values: float) -> tuple[TrendPoint, ...]:
    from datetime import date

    return tuple(
        TrendPoint(period_start=date(2026, index + 1, 1), relative_index=RelativeIndex(value))
        for index, value in enumerate(values)
    )


def test_a_rising_series_scores_higher_than_a_falling_one() -> None:
    rising = trend_component(points(10.0, 20.0, 30.0, 40.0, 50.0, 60.0))
    falling = trend_component(points(60.0, 50.0, 40.0, 30.0, 20.0, 10.0))
    assert rising is not None
    assert falling is not None
    assert rising > 0.5 > falling


def test_a_flat_series_is_neutral() -> None:
    flat = trend_component(points(50.0, 50.0, 50.0, 50.0, 50.0, 50.0))
    assert flat == pytest.approx(0.5)


def test_too_few_points_yield_no_trend_rather_than_a_guess() -> None:
    assert trend_component(points(50.0)) is None
    assert trend_component(()) is None


def test_the_trend_component_is_a_ratio_and_carries_no_unit_of_searches() -> None:
    value = trend_component(points(10.0, 20.0, 30.0, 40.0, 50.0, 60.0))
    assert value is not None
    assert 0.0 <= value <= 1.0


def test_the_score_refuses_a_relative_index_where_a_count_belongs() -> None:
    """A structural guard, not a convention: the wrong type raises rather than scores."""
    with pytest.raises(TypeError, match="RelativeIndex"):
        complete_inputs(monthly_total_searches=RelativeIndex(50.0))


def test_the_score_refuses_a_bare_integer_where_a_count_belongs() -> None:
    """A bare ``int`` has lost its quality flag; accepting one would erase suppression."""
    with pytest.raises(TypeError, match="SearchCount"):
        complete_inputs(monthly_total_searches=1111)
