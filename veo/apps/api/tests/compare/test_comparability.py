"""Two numbers may only be set beside each other when they were measured the same way.

This is the failure mode competitive reporting invites. Crawl four pages of our own site
and two hundred of a competitor's, put the two scores in a bar chart, and the chart is a
lie — but a lie that renders beautifully and that nobody in the meeting can see.

So comparability is a precondition, enforced structurally, exactly like tenant scoping:
a comparison either declares that its sides were measured alike, or it refuses to be a
comparison at all.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from veo.compare import (
    ComparabilityError,
    ConditionDifference,
    MeasurementConditions,
    assert_comparable,
    describe_differences,
    is_comparable,
)

NOW = datetime(2026, 7, 28, 3, 0, tzinfo=UTC)


def conditions(**overrides: object) -> MeasurementConditions:
    base: dict[str, object] = {
        "spec_id": "veo.seo.readiness",
        "spec_version": "1.0.0",
        "spec_checksum": "a" * 64,
        "collector_version": "seo-collector/1.0.0",
        "pages_examined": 20,
        "locale": "ko-KR",
        "device": "MOBILE",
        "renderer": "HTTP_ONLY",
        "enabled_providers": ("NAVER_DATALAB",),
        "measured_at": NOW,
    }
    base.update(overrides)
    return MeasurementConditions(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# The happy path is narrow on purpose
# --------------------------------------------------------------------------- #


def test_identical_conditions_are_comparable() -> None:
    assert is_comparable(conditions(), conditions())
    assert_comparable(conditions(), conditions())
    assert describe_differences(conditions(), conditions()) == []


def test_a_measurement_is_comparable_with_itself() -> None:
    one = conditions()
    assert_comparable(one, one)


# --------------------------------------------------------------------------- #
# Anything that changes what the number means blocks the comparison
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("spec_id", "veo.geo.readiness"),
        ("spec_version", "1.1.0"),
        ("spec_checksum", "b" * 64),
        ("collector_version", "seo-collector/2.0.0"),
        ("locale", "en-US"),
        ("device", "DESKTOP"),
        ("renderer", "HEADLESS_BROWSER"),
    ],
)
def test_a_differing_condition_is_refused(field: str, value: object) -> None:
    with pytest.raises(ComparabilityError):
        assert_comparable(conditions(), conditions(**{field: value}))


def test_a_different_methodology_version_is_never_waivable() -> None:
    """Scores from two specifications are different units, not different values."""
    with pytest.raises(ComparabilityError, match=r"[Mm]ethodolog|spec"):
        assert_comparable(
            conditions(), conditions(spec_version="2.0.0"), allow_scope_variance=True
        )


def test_a_different_provider_set_is_refused() -> None:
    """One side with Search Console data and one without is not a like-for-like score."""
    with pytest.raises(ComparabilityError):
        assert_comparable(
            conditions(),
            conditions(enabled_providers=("NAVER_DATALAB", "GOOGLE_SEARCH_CONSOLE")),
        )


def test_provider_order_does_not_matter() -> None:
    assert_comparable(
        conditions(enabled_providers=("A", "B")),
        conditions(enabled_providers=("B", "A")),
    )


# --------------------------------------------------------------------------- #
# Crawl scope: the difference that hides best
# --------------------------------------------------------------------------- #


def test_a_wildly_different_page_count_is_refused() -> None:
    with pytest.raises(ComparabilityError, match=r"페이지|pages"):
        assert_comparable(conditions(pages_examined=4), conditions(pages_examined=200))


def test_a_small_difference_in_page_count_is_tolerated_but_reported() -> None:
    """Crawls never land on exactly the same number; the point is proportion."""
    left, right = conditions(pages_examined=20), conditions(pages_examined=22)
    assert_comparable(left, right)

    differences = describe_differences(left, right)
    assert any(d.field == "pages_examined" for d in differences)
    assert all(not d.blocking for d in differences)


def test_scope_variance_can_be_waived_explicitly_and_is_still_reported() -> None:
    """An analyst may accept an uneven crawl — but the report must still say so."""
    left, right = conditions(pages_examined=4), conditions(pages_examined=200)

    with pytest.raises(ComparabilityError):
        assert_comparable(left, right)

    assert_comparable(left, right, allow_scope_variance=True)
    differences = describe_differences(left, right)
    scope = next(d for d in differences if d.field == "pages_examined")
    assert scope.blocking
    assert scope.explanation_ko


def test_zero_pages_is_not_comparable_with_anything() -> None:
    with pytest.raises(ComparabilityError):
        assert_comparable(conditions(pages_examined=0), conditions(pages_examined=20))


# --------------------------------------------------------------------------- #
# Time
# --------------------------------------------------------------------------- #


def test_measurements_far_apart_are_refused() -> None:
    with pytest.raises(ComparabilityError, match=r"기간|시점|days"):
        assert_comparable(conditions(), conditions(measured_at=NOW - timedelta(days=45)))


def test_measurements_within_the_window_are_comparable() -> None:
    assert_comparable(conditions(), conditions(measured_at=NOW - timedelta(days=3)))


def test_the_staleness_window_is_configurable() -> None:
    left, right = conditions(), conditions(measured_at=NOW - timedelta(days=10))
    assert_comparable(left, right)
    with pytest.raises(ComparabilityError):
        assert_comparable(left, right, max_age_gap_days=2)


# --------------------------------------------------------------------------- #
# What the report has to be able to say
# --------------------------------------------------------------------------- #


def test_differences_carry_both_sides_and_a_korean_explanation() -> None:
    differences = describe_differences(conditions(), conditions(device="DESKTOP"))
    difference = next(d for d in differences if d.field == "device")

    assert isinstance(difference, ConditionDifference)
    assert difference.left == "MOBILE"
    assert difference.right == "DESKTOP"
    assert difference.explanation_ko
    assert difference.blocking


def test_every_difference_is_json_serialisable() -> None:
    import json

    differences = describe_differences(
        conditions(), conditions(device="DESKTOP", pages_examined=25)
    )
    encoded = json.dumps([d.as_dict() for d in differences], ensure_ascii=False)
    assert json.loads(encoded)


def test_the_error_names_every_blocking_difference_not_just_the_first() -> None:
    with pytest.raises(ComparabilityError) as exc:
        assert_comparable(
            conditions(), conditions(device="DESKTOP", renderer="HEADLESS_BROWSER")
        )
    message = str(exc.value)
    assert "device" in message
    assert "renderer" in message


def test_conditions_are_frozen() -> None:
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        conditions().pages_examined = 1  # type: ignore[misc]


def test_conditions_round_trip_through_a_dict() -> None:
    original = conditions()
    assert MeasurementConditions.from_dict(original.as_dict()) == original


def test_fingerprint_is_stable_and_ignores_non_semantic_fields() -> None:
    """Two crawls minutes apart with the same setup share a fingerprint."""
    left = conditions(measured_at=NOW)
    right = conditions(measured_at=NOW - timedelta(minutes=5))
    assert left.fingerprint == right.fingerprint

    assert conditions(device="DESKTOP").fingerprint != left.fingerprint
