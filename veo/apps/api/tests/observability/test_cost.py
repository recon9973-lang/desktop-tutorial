"""Unmeasurable cost is not zero cost.

The failure this file exists to prevent: a month in which the price table expired, every
call returned ``cost_usd = None``, the tracker folded those into the total as zeros, and
the budget alert stayed green while the bill ran away. The opposite failure — treating an
unpriced call as infinitely expensive — pages somebody every night and gets muted within
a week. So it is neither. It is its own state, and it is in the alert text.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from veo.observability.cost import (
    BudgetStatus,
    BudgetTracker,
    CostMeasurement,
    UnmeasurableReason,
    month_key,
)
from veo.observations.pricing import price_table_from_document
from veo.observations.providers.base import CostBasis

ORG = uuid.UUID("11111111-1111-4111-8111-111111111111")
OTHER_ORG = uuid.UUID("22222222-2222-4222-8222-222222222222")
JULY = datetime(2026, 7, 15, 9, 0, tzinfo=UTC)
AUGUST = datetime(2026, 8, 2, 9, 0, tzinfo=UTC)


def tracker(**kwargs: object) -> BudgetTracker:
    defaults: dict = {"default_limit_usd": 100.0, "warn_at_ratio": 0.5}
    defaults.update(kwargs)
    return BudgetTracker(**defaults)


# --------------------------------------------------------------------------- #
# Accumulation
# --------------------------------------------------------------------------- #


def test_measured_spend_accumulates_per_organization_and_month() -> None:
    budget = tracker()
    budget.record(organization_id=ORG, cost_usd=10.0, occurred_at=JULY)
    budget.record(organization_id=ORG, cost_usd=5.5, occurred_at=JULY)
    budget.record(organization_id=ORG, cost_usd=1.0, occurred_at=AUGUST)
    budget.record(organization_id=OTHER_ORG, cost_usd=99.0, occurred_at=JULY)

    july = budget.report(ORG, month=month_key(JULY))
    assert july.spent_usd == pytest.approx(15.5)
    assert july.measured_calls == 2
    assert budget.report(ORG, month=month_key(AUGUST)).spent_usd == pytest.approx(1.0)
    assert budget.report(OTHER_ORG, month=month_key(JULY)).spent_usd == pytest.approx(99.0)


def test_a_month_with_nothing_in_it_reports_zero_rather_than_failing() -> None:
    report = tracker().report(ORG, month="2026-07")

    assert report.spent_usd == 0.0
    assert report.measured_calls == 0
    assert report.unmeasurable_calls == 0
    assert report.status is BudgetStatus.OK
    assert report.measurement is CostMeasurement.COMPLETE


# --------------------------------------------------------------------------- #
# Unmeasurable is its own state
# --------------------------------------------------------------------------- #


def test_an_unpriced_call_is_not_folded_into_the_total_as_zero() -> None:
    budget = tracker()
    budget.record(organization_id=ORG, cost_usd=40.0, occurred_at=JULY)
    for _ in range(120):
        budget.record(
            organization_id=ORG,
            cost_usd=None,
            basis=CostBasis.PRICE_TABLE_STALE,
            occurred_at=JULY,
        )

    report = budget.report(ORG, month=month_key(JULY))
    assert report.spent_usd == pytest.approx(40.0)
    assert report.measured_calls == 1
    assert report.unmeasurable_calls == 120
    assert report.unmeasurable_by_reason[UnmeasurableReason.PRICE_TABLE_STALE] == 120
    assert report.measurement is CostMeasurement.PARTIAL


def test_the_alert_says_what_we_spent_and_what_we_could_not_price() -> None:
    budget = tracker()
    budget.record(organization_id=ORG, cost_usd=40.0, occurred_at=JULY)
    for _ in range(120):
        budget.record(
            organization_id=ORG,
            cost_usd=None,
            basis=CostBasis.PRICE_TABLE_STALE,
            occurred_at=JULY,
        )

    line = budget.report(ORG, month=month_key(JULY)).alert_line_ko()
    assert "$40.00" in line
    assert "120" in line
    assert "PRICE_TABLE_STALE" in line
    assert "측정 불가" in line


def test_a_month_where_nothing_could_be_priced_says_so() -> None:
    budget = tracker()
    for _ in range(5):
        budget.record(
            organization_id=ORG,
            cost_usd=None,
            basis=CostBasis.NO_PRICE_CONFIGURED,
            occurred_at=JULY,
        )

    report = budget.report(ORG, month=month_key(JULY))
    assert report.measurement is CostMeasurement.NONE
    assert report.spent_usd == 0.0
    # Zero spend with zero measurements must never read as "we are well under budget".
    assert "측정 불가" in report.alert_line_ko()
    assert report.ratio is None


def test_every_basis_maps_to_a_stated_reason() -> None:
    budget = tracker()
    for basis in CostBasis:
        budget.record(
            organization_id=ORG, cost_usd=None, basis=basis, occurred_at=JULY
        )

    report = budget.report(ORG, month=month_key(JULY))
    assert report.unmeasurable_calls == len(CostBasis)
    assert UnmeasurableReason.UNSPECIFIED not in report.unmeasurable_by_reason


def test_a_missing_basis_is_recorded_as_unspecified_rather_than_guessed() -> None:
    budget = tracker()
    budget.record(organization_id=ORG, cost_usd=None, occurred_at=JULY)

    report = budget.report(ORG, month=month_key(JULY))
    assert report.unmeasurable_by_reason[UnmeasurableReason.UNSPECIFIED] == 1


def test_a_nonsense_cost_becomes_unmeasurable_rather_than_raising_or_counting_as_zero() -> None:
    budget = tracker()
    budget.record(organization_id=ORG, cost_usd=-1.0, occurred_at=JULY)
    budget.record(organization_id=ORG, cost_usd=float("nan"), occurred_at=JULY)
    budget.record(organization_id=ORG, cost_usd=float("inf"), occurred_at=JULY)

    report = budget.report(ORG, month=month_key(JULY))
    assert report.spent_usd == 0.0
    assert report.measured_calls == 0
    assert report.unmeasurable_by_reason[UnmeasurableReason.INVALID_COST_REPORTED] == 3


# --------------------------------------------------------------------------- #
# The stale price table, end to end
# --------------------------------------------------------------------------- #


def test_a_stale_price_table_makes_the_cost_unmeasurable_and_the_report_says_so() -> None:
    table = price_table_from_document(
        {
            "version": "model-prices/2026-01-01",
            "as_of": "2026-01-01",
            "stale_after_days": 90,
            "currency": "USD",
            "prices": {
                "gpt-5": {"input_usd_per_million": 1.25, "output_usd_per_million": 10.0}
            },
        },
        today=date(2026, 7, 28),
    )
    assert table.is_stale

    cost, basis = table.cost(
        model="gpt-5", model_version="gpt-5", input_tokens=1_000_000, output_tokens=0
    )
    assert cost is None
    assert basis is CostBasis.PRICE_TABLE_STALE

    budget = tracker()
    budget.record(organization_id=ORG, cost_usd=cost, basis=basis, occurred_at=JULY)

    report = budget.report(ORG, month=month_key(JULY))
    assert report.spent_usd == 0.0
    assert report.unmeasurable_calls == 1
    assert report.unmeasurable_by_reason[UnmeasurableReason.PRICE_TABLE_STALE] == 1
    assert "PRICE_TABLE_STALE" in report.alert_line_ko()


def test_a_fresh_price_table_produces_spend_that_the_budget_can_hold_to_a_limit() -> None:
    table = price_table_from_document(
        {
            "version": "model-prices/2026-07-01",
            "as_of": "2026-07-01",
            "stale_after_days": 90,
            "currency": "USD",
            "prices": {
                "gpt-5": {"input_usd_per_million": 1.25, "output_usd_per_million": 10.0}
            },
        },
        today=date(2026, 7, 28),
    )
    cost, basis = table.cost(
        model="gpt-5", model_version="gpt-5", input_tokens=1_000_000, output_tokens=0
    )

    budget = tracker()
    budget.record(organization_id=ORG, cost_usd=cost, basis=basis, occurred_at=JULY)

    report = budget.report(ORG, month=month_key(JULY))
    assert report.spent_usd == pytest.approx(1.25)
    assert report.measurement is CostMeasurement.COMPLETE


# --------------------------------------------------------------------------- #
# The threshold
# --------------------------------------------------------------------------- #


def test_the_warning_does_not_fire_below_the_threshold() -> None:
    budget = tracker()
    budget.record(organization_id=ORG, cost_usd=49.0, occurred_at=JULY)

    report = budget.report(ORG, month=month_key(JULY))
    assert report.ratio == pytest.approx(0.49)
    assert report.status is BudgetStatus.OK


def test_the_warning_fires_exactly_at_the_threshold() -> None:
    budget = tracker()
    budget.record(organization_id=ORG, cost_usd=50.0, occurred_at=JULY)

    assert budget.report(ORG, month=month_key(JULY)).status is BudgetStatus.WARNING


def test_the_budget_is_exceeded_only_once_the_limit_is_passed() -> None:
    budget = tracker()
    budget.record(organization_id=ORG, cost_usd=100.0, occurred_at=JULY)
    assert budget.report(ORG, month=month_key(JULY)).status is BudgetStatus.WARNING

    budget.record(organization_id=ORG, cost_usd=0.01, occurred_at=JULY)
    assert budget.report(ORG, month=month_key(JULY)).status is BudgetStatus.EXCEEDED


def test_a_per_organization_limit_overrides_the_default() -> None:
    budget = tracker()
    budget.set_limit(ORG, 10.0)
    budget.record(organization_id=ORG, cost_usd=6.0, occurred_at=JULY)

    assert budget.report(ORG, month=month_key(JULY)).status is BudgetStatus.WARNING
    assert budget.report(OTHER_ORG, month=month_key(JULY)).limit_usd == pytest.approx(100.0)


def test_without_a_limit_there_is_no_status_to_claim() -> None:
    budget = BudgetTracker(default_limit_usd=None)
    budget.record(organization_id=ORG, cost_usd=1_000.0, occurred_at=JULY)

    report = budget.report(ORG, month=month_key(JULY))
    assert report.limit_usd is None
    assert report.ratio is None
    assert report.status is BudgetStatus.OK
    assert "$1000.00" in report.alert_line_ko()


def test_an_invalid_threshold_is_refused_at_construction() -> None:
    with pytest.raises(ValueError, match="warn_at_ratio"):
        BudgetTracker(default_limit_usd=10.0, warn_at_ratio=1.5)


def test_a_negative_limit_is_refused() -> None:
    with pytest.raises(ValueError, match="limit"):
        BudgetTracker(default_limit_usd=-1.0)


# --------------------------------------------------------------------------- #
# Month boundaries
# --------------------------------------------------------------------------- #


def test_month_key_is_utc_so_a_late_night_call_lands_in_the_right_month() -> None:
    assert month_key(datetime(2026, 7, 31, 23, 59, tzinfo=UTC)) == "2026-07"
    assert month_key(datetime(2026, 8, 1, 0, 1, tzinfo=UTC)) == "2026-08"


def test_a_naive_timestamp_is_refused_rather_than_assumed_to_be_utc() -> None:
    with pytest.raises(ValueError, match="시간대"):
        month_key(datetime(2026, 7, 31, 23, 59))


def test_the_current_month_is_used_when_none_is_asked_for() -> None:
    budget = BudgetTracker(default_limit_usd=100.0, clock=lambda: JULY)
    budget.record(organization_id=ORG, cost_usd=3.0)

    assert budget.report(ORG).month == "2026-07"
    assert budget.report(ORG).spent_usd == pytest.approx(3.0)


def test_the_months_seen_for_an_organization_are_listable() -> None:
    budget = tracker()
    budget.record(organization_id=ORG, cost_usd=1.0, occurred_at=AUGUST)
    budget.record(organization_id=ORG, cost_usd=1.0, occurred_at=JULY)

    assert budget.months(ORG) == ["2026-07", "2026-08"]


def test_the_report_never_names_the_organization_beyond_its_uuid() -> None:
    budget = tracker()
    budget.record(organization_id=ORG, cost_usd=1.0, occurred_at=JULY)

    report = budget.report(ORG, month=month_key(JULY))
    assert report.organization_id == ORG
    assert str(ORG) in report.alert_line_ko()
