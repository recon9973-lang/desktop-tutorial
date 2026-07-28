"""A rate is not a number. It is a number with an interval, and sometimes it is neither.

This is the most dangerous arithmetic in the product. Ask an AI engine three times, see
the brand mentioned twice, and "66.7% 언급률" is technically the sample proportion and
practically a lie — the true rate is somewhere between roughly 20% and 94%, which is to
say unknown. Printed to one decimal place beside a competitor's "50.0%", it manufactures
a ranking out of noise.

So a proportion in VEO always carries its Wilson interval, and below the methodology's
minimum sample it refuses to be a percentage at all and reports direction instead.
"""

from __future__ import annotations

import pytest

from veo.observations.sampling import (
    MIN_RUNS_FOR_COMPARISON,
    MIN_RUNS_FOR_EXPLORATION,
    InsufficientSampleError,
    ObservedRate,
    SampleAdequacy,
    wilson_interval,
)

# --------------------------------------------------------------------------- #
# The interval itself
# --------------------------------------------------------------------------- #


def test_wilson_interval_brackets_the_point_estimate() -> None:
    low, high = wilson_interval(successes=2, trials=3)
    assert low < 2 / 3 < high


def test_a_tiny_sample_produces_a_useless_interval_and_says_so() -> None:
    """2 of 3 spans most of the range. The number is not evidence of anything."""
    low, high = wilson_interval(successes=2, trials=3)
    assert low < 0.25
    assert high > 0.90
    assert high - low > 0.6


def test_a_larger_sample_narrows_the_interval() -> None:
    narrow = wilson_interval(successes=40, trials=60)
    wide = wilson_interval(successes=2, trials=3)
    assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])


def test_the_interval_never_leaves_zero_to_one() -> None:
    for successes, trials in ((0, 1), (1, 1), (0, 5), (5, 5), (1, 100), (99, 100)):
        low, high = wilson_interval(successes=successes, trials=trials)
        assert 0.0 <= low <= high <= 1.0, (successes, trials)


def test_all_successes_still_leaves_uncertainty_below_one() -> None:
    """Three for three is not proof of 100%."""
    low, high = wilson_interval(successes=3, trials=3)
    assert low < 1.0
    assert high == pytest.approx(1.0, abs=1e-9) or high < 1.0
    assert low < 0.5


def test_zero_successes_does_not_collapse_to_zero() -> None:
    """Never seen is not the same as never happens."""
    low, high = wilson_interval(successes=0, trials=3)
    assert low == pytest.approx(0.0, abs=1e-9)
    assert high > 0.3, "with 3 runs the true rate could easily be a third"


def test_zero_trials_is_refused_rather_than_dividing_by_zero() -> None:
    with pytest.raises(ValueError):
        wilson_interval(successes=0, trials=0)


def test_more_successes_than_trials_is_refused() -> None:
    with pytest.raises(ValueError):
        wilson_interval(successes=5, trials=3)


def test_negative_counts_are_refused() -> None:
    with pytest.raises(ValueError):
        wilson_interval(successes=-1, trials=3)


# --------------------------------------------------------------------------- #
# What VEO is willing to publish
# --------------------------------------------------------------------------- #


def test_a_sample_below_the_exploration_minimum_is_not_a_rate() -> None:
    rate = ObservedRate.build(successes=1, trials=2, label_ko="언급률")
    assert rate.adequacy is SampleAdequacy.TOO_SMALL
    assert rate.percentage_text_ko != "50.0%"
    assert rate.value is None, "a proportion this thin must not be published as a number"


def test_the_exploration_minimum_matches_the_methodology() -> None:
    assert MIN_RUNS_FOR_EXPLORATION == 3
    assert MIN_RUNS_FOR_COMPARISON == 5


def test_at_the_exploration_minimum_the_rate_is_directional_only() -> None:
    rate = ObservedRate.build(successes=2, trials=3, label_ko="언급률")
    assert rate.adequacy is SampleAdequacy.DIRECTIONAL
    assert rate.value is not None
    assert "방향" in rate.qualifier_ko
    # Direction, not precision: no decimal places at this sample size.
    assert "." not in rate.percentage_text_ko


def test_a_comparison_grade_sample_may_be_reported_precisely() -> None:
    rate = ObservedRate.build(successes=30, trials=50, label_ko="언급률")
    assert rate.adequacy is SampleAdequacy.ADEQUATE
    assert rate.percentage_text_ko.startswith("60")


def test_every_rate_carries_its_interval_in_korean() -> None:
    rate = ObservedRate.build(successes=30, trials=50, label_ko="언급률")
    assert "95%" in rate.interval_text_ko
    assert rate.confidence_low is not None and rate.confidence_high is not None


def test_a_rate_states_its_own_denominator() -> None:
    """'60%' without 'of how many' is the number that misleads."""
    rate = ObservedRate.build(successes=30, trials=50, label_ko="언급률")
    assert "50" in rate.summary_ko
    assert "30" in rate.summary_ko


def test_no_observations_at_all_is_data_absent_not_zero_percent() -> None:
    rate = ObservedRate.build(successes=0, trials=0, label_ko="인용률")
    assert rate.adequacy is SampleAdequacy.NO_DATA
    assert rate.value is None
    assert "데이터 없음" in rate.summary_ko
    assert "0%" not in rate.summary_ko


def test_zero_successes_with_real_trials_is_a_measured_zero() -> None:
    """Different from no data: we looked, and did not find it."""
    rate = ObservedRate.build(successes=0, trials=20, label_ko="인용률")
    assert rate.adequacy is not SampleAdequacy.NO_DATA
    assert rate.value == pytest.approx(0.0)
    assert "데이터 없음" not in rate.summary_ko


# --------------------------------------------------------------------------- #
# Comparing two rates
# --------------------------------------------------------------------------- #


def test_overlapping_intervals_are_not_a_difference() -> None:
    """The headline claim a competitive report wants to make, and usually cannot."""
    ours = ObservedRate.build(successes=2, trials=3, label_ko="언급률")
    theirs = ObservedRate.build(successes=1, trials=3, label_ko="언급률")
    assert not ours.is_distinguishable_from(theirs)


def test_separated_intervals_are_a_difference() -> None:
    ours = ObservedRate.build(successes=48, trials=50, label_ko="언급률")
    theirs = ObservedRate.build(successes=5, trials=50, label_ko="언급률")
    assert ours.is_distinguishable_from(theirs)


def test_a_rate_without_data_is_never_distinguishable() -> None:
    ours = ObservedRate.build(successes=30, trials=50, label_ko="언급률")
    nothing = ObservedRate.build(successes=0, trials=0, label_ko="언급률")
    assert not ours.is_distinguishable_from(nothing)
    assert not nothing.is_distinguishable_from(ours)


def test_comparison_demands_the_larger_minimum() -> None:
    ours = ObservedRate.build(successes=2, trials=3, label_ko="언급률")
    with pytest.raises(InsufficientSampleError, match="비교"):
        ours.require_comparison_grade()


def test_comparison_grade_passes_at_five_runs() -> None:
    ObservedRate.build(successes=3, trials=5, label_ko="언급률").require_comparison_grade()


# --------------------------------------------------------------------------- #
# Serialisation
# --------------------------------------------------------------------------- #


def test_a_rate_is_json_serialisable_with_everything_a_reader_needs() -> None:
    import json

    payload = ObservedRate.build(successes=30, trials=50, label_ko="언급률").as_dict()
    encoded = json.loads(json.dumps(payload, ensure_ascii=False))

    for key in (
        "value",
        "successes",
        "trials",
        "confidence_low",
        "confidence_high",
        "adequacy",
        "summary_ko",
    ):
        assert key in encoded, key


def test_a_rate_never_reports_a_bare_number_without_adequacy() -> None:
    for successes, trials in ((0, 0), (1, 2), (2, 3), (30, 50)):
        payload = ObservedRate.build(
            successes=successes, trials=trials, label_ko="언급률"
        ).as_dict()
        assert payload["adequacy"]
        if payload["value"] is not None:
            assert payload["confidence_low"] is not None
