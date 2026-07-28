"""A price that has gone stale must stop being a price.

Model pricing changes every few months. A table baked into code is correct the week it
is written and quietly wrong afterwards, and a wrong figure printed as "this study cost
$4.20" is exactly the plausible fabrication this product refuses to produce.

So the table is a dated file with an expiry. Past the expiry the cost becomes 측정 불가 —
never zero, because "we do not know" and "it was free" are different facts.
"""

from __future__ import annotations

from datetime import date

import pytest

from veo.observations.pricing import (
    PriceTableStaleError,
    load_price_table,
    price_table_from_document,
)

TODAY = date(2026, 7, 28)


def document(**overrides: object) -> dict:
    base: dict = {
        "version": "model-prices/2026-07-28",
        "as_of": "2026-07-28",
        "stale_after_days": 90,
        "currency": "USD",
        "prices": {
            "gpt-5": {"input_usd_per_million": 1.25, "output_usd_per_million": 10.0},
        },
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# A fresh table prices what it knows
# --------------------------------------------------------------------------- #


def test_a_fresh_table_calculates_a_cost() -> None:
    table = price_table_from_document(document(), today=TODAY)
    cost, basis = table.cost(
        model="gpt-5", model_version="gpt-5", input_tokens=1_000_000, output_tokens=0
    )
    assert cost == pytest.approx(1.25)
    assert str(basis) == "CALCULATED_FROM_USAGE"


def test_an_unpriced_model_is_not_free() -> None:
    table = price_table_from_document(document(), today=TODAY)
    cost, basis = table.cost(
        model="some-other-model",
        model_version="v1",
        input_tokens=1000,
        output_tokens=1000,
    )
    assert cost is None
    assert str(basis) == "NO_PRICE_CONFIGURED"


def test_no_usage_reported_is_not_zero_cost() -> None:
    table = price_table_from_document(document(), today=TODAY)
    cost, basis = table.cost(
        model="gpt-5", model_version="gpt-5", input_tokens=None, output_tokens=None
    )
    assert cost is None
    assert str(basis) == "NO_USAGE_REPORTED"


# --------------------------------------------------------------------------- #
# Staleness
# --------------------------------------------------------------------------- #


def test_a_table_inside_its_window_is_usable() -> None:
    table = price_table_from_document(document(), today=date(2026, 9, 1))
    assert not table.is_stale
    cost, _ = table.cost(
        model="gpt-5", model_version="gpt-5", input_tokens=1_000_000, output_tokens=0
    )
    assert cost is not None


def test_a_stale_table_stops_pricing_rather_than_pricing_wrongly() -> None:
    """91 days on, the numbers are no longer evidence of anything."""
    table = price_table_from_document(document(), today=date(2026, 11, 1))
    assert table.is_stale

    cost, basis = table.cost(
        model="gpt-5", model_version="gpt-5", input_tokens=1_000_000, output_tokens=0
    )
    assert cost is None, "a stale table must not produce a confident figure"
    assert str(basis) == "PRICE_TABLE_STALE"


def test_a_stale_table_never_reports_zero() -> None:
    table = price_table_from_document(document(), today=date(2027, 1, 1))
    cost, _ = table.cost(
        model="gpt-5", model_version="gpt-5", input_tokens=5_000_000, output_tokens=5_000_000
    )
    assert cost is None
    assert cost != 0.0


def test_staleness_can_be_demanded_up_front() -> None:
    """A caller about to authorise a budgeted study wants to know before it starts."""
    table = price_table_from_document(document(), today=date(2026, 11, 1))
    with pytest.raises(PriceTableStaleError, match=r"만료|기준일"):
        table.require_fresh()


def test_a_fresh_table_passes_the_up_front_check() -> None:
    price_table_from_document(document(), today=TODAY).require_fresh()


# --------------------------------------------------------------------------- #
# The shipped file
# --------------------------------------------------------------------------- #


def test_the_shipped_table_loads() -> None:
    table = load_price_table(today=TODAY)
    assert table.version.startswith("model-prices/")


def test_the_shipped_table_ships_empty_and_says_so() -> None:
    """Nobody verified these prices, so none are claimed. Empty beats wrong."""
    table = load_price_table(today=TODAY)
    cost, basis = table.cost(
        model="gpt-5", model_version="gpt-5", input_tokens=1000, output_tokens=1000
    )
    assert cost is None
    assert str(basis) == "NO_PRICE_CONFIGURED"


def test_a_price_entry_must_carry_both_directions() -> None:
    bad = document(prices={"gpt-5": {"input_usd_per_million": 1.25}})
    with pytest.raises(ValueError):
        price_table_from_document(bad, today=TODAY)


def test_a_negative_price_is_refused() -> None:
    bad = document(prices={"gpt-5": {"input_usd_per_million": -1.0, "output_usd_per_million": 1.0}})
    with pytest.raises(ValueError):
        price_table_from_document(bad, today=TODAY)


def test_a_table_without_an_as_of_date_is_refused() -> None:
    """An undated price table cannot be known to be stale, which is worse than stale."""
    bad = document()
    del bad["as_of"]
    with pytest.raises(ValueError, match=r"as_of|기준일"):
        price_table_from_document(bad, today=TODAY)
