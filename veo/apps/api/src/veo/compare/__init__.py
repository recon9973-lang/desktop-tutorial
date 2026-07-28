"""Comparison: same-condition measurement, or no comparison at all.

Owned by the integration maintainer. The competitor engine consumes these guards; it
does not relax them.
"""

from veo.compare.conditions import (
    DEFAULT_MAX_AGE_GAP_DAYS,
    DEFAULT_MAX_PAGE_RATIO,
    ComparabilityError,
    ConditionDifference,
    MeasurementConditions,
    assert_comparable,
    describe_differences,
    is_comparable,
)

__all__ = [
    "DEFAULT_MAX_AGE_GAP_DAYS",
    "DEFAULT_MAX_PAGE_RATIO",
    "ComparabilityError",
    "ConditionDifference",
    "MeasurementConditions",
    "assert_comparable",
    "describe_differences",
    "is_comparable",
]
