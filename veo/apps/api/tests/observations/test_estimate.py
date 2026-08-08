"""누르기 전 예상치 — 셀 수 있는 것만 세는가.

여기서 지키려는 것은 하나다. **호출 수는 언제나 나오고, 금액은 근거가 있을 때만
나온다.** 근거 없이 나온 금액은 예산을 그 값에 맞춰 잡게 만들고, 그때 틀린 값은
"조금 틀린 값" 이 아니라 **잘못된 결정**이 된다.
"""

from __future__ import annotations

from datetime import date

import pytest

from veo.observations.estimate import (
    EstimateBasis,
    TokenBaseline,
    estimate_work,
    median_baseline,
    plan_slots,
)
from veo.observations.pricing import price_table_from_document
from veo.observations.runs import SearchMode

TODAY = date(2026, 8, 8)


def fresh_table(**prices: dict[str, float]) -> object:
    return price_table_from_document(
        {
            "version": "model-prices/2026-08-01",
            "as_of": "2026-08-01",
            "stale_after_days": 90,
            "currency": "USD",
            "prices": prices
            or {"gpt-5": {"input_usd_per_million": 1.25, "output_usd_per_million": 10.0}},
        },
        today=TODAY,
    )


def stale_table() -> object:
    return price_table_from_document(
        {
            "version": "model-prices/2026-01-01",
            "as_of": "2026-01-01",
            "stale_after_days": 90,
            "currency": "USD",
            "prices": {"gpt-5": {"input_usd_per_million": 1.25, "output_usd_per_million": 10.0}},
        },
        today=TODAY,
    )


# --------------------------------------------------------------------------- #
# 호출 수 — 곱셈이고, 언제나 정확하다
# --------------------------------------------------------------------------- #


def test_call_count_is_prompts_times_repetitions_per_slot() -> None:
    plans = plan_slots(
        prompt_count=5,
        slots=[
            ("openai", "gpt-5", SearchMode.BROWSING),
            ("openai", "gpt-5", SearchMode.NO_BROWSING),
        ],
        repetitions=3,
    )
    assert [plan.calls for plan in plans] == [15, 15]
    assert plans[0].slot == "OPENAI:gpt-5:BROWSING"
    assert plans[1].slot == "OPENAI:gpt-5:NO_BROWSING"


def test_search_on_and_off_are_separate_slots_so_neither_overwrites_the_other() -> None:
    """`RunConditions.slot` 과 같은 축이어야 한다 — v0.3.71 이 고친 결함과 같은 자리."""
    plans = plan_slots(
        prompt_count=1,
        slots=[
            ("openai", "gpt-5", SearchMode.BROWSING),
            ("openai", "gpt-5", SearchMode.NO_BROWSING),
        ],
        repetitions=1,
    )
    assert len({plan.slot for plan in plans}) == 2


def test_negative_input_is_refused_rather_than_producing_a_nonsense_plan() -> None:
    with pytest.raises(ValueError):
        plan_slots(prompt_count=-1, slots=[], repetitions=3)


# --------------------------------------------------------------------------- #
# 금액 — 근거가 있을 때만
# --------------------------------------------------------------------------- #


def test_without_a_measured_baseline_there_is_no_amount_but_the_call_count_stands() -> None:
    plans = plan_slots(
        prompt_count=5, slots=[("openai", "gpt-5", SearchMode.NO_BROWSING)], repetitions=3
    )
    result = estimate_work(plans, prices=fresh_table(), baselines={})

    assert result.total_calls == 15
    assert result.amount_usd is None
    assert result.measurement == "NONE"
    assert result.slots[0].basis == EstimateBasis.NO_TOKEN_BASELINE
    assert result.slots[0].baseline_samples == 0
    assert "15" in result.summary_ko


def test_a_measured_baseline_produces_an_amount_from_the_dated_price_table() -> None:
    plans = plan_slots(
        prompt_count=2, slots=[("openai", "gpt-5", SearchMode.NO_BROWSING)], repetitions=1
    )
    baseline = TokenBaseline(input_tokens=1_000_000, output_tokens=0, samples=7)

    result = estimate_work(
        plans, prices=fresh_table(), baselines={"OPENAI:gpt-5:NO_BROWSING": baseline}
    )

    # 1M 입력 토큰 x $1.25 x 2회
    assert result.amount_usd == pytest.approx(2.50)
    assert result.measurement == "COMPLETE"
    assert result.slots[0].basis == EstimateBasis.MEASURED
    assert result.slots[0].baseline_samples == 7


def test_a_stale_price_table_yields_no_amount_rather_than_a_stale_one() -> None:
    plans = plan_slots(
        prompt_count=1, slots=[("openai", "gpt-5", SearchMode.NO_BROWSING)], repetitions=1
    )
    result = estimate_work(
        plans,
        prices=stale_table(),
        baselines={"OPENAI:gpt-5:NO_BROWSING": TokenBaseline(1000, 1000, 5)},
    )

    assert result.amount_usd is None
    assert result.slots[0].basis == EstimateBasis.PRICE_TABLE_STALE
    assert any("가격표" in remedy for remedy in result.remedies_ko)


def test_a_model_missing_from_the_price_table_is_named_rather_than_priced_at_zero() -> None:
    plans = plan_slots(
        prompt_count=1, slots=[("xai", "grok-4", SearchMode.NO_BROWSING)], repetitions=1
    )
    result = estimate_work(
        plans,
        prices=fresh_table(),
        baselines={"XAI:grok-4:NO_BROWSING": TokenBaseline(1000, 1000, 3)},
    )

    assert result.amount_usd is None
    assert result.slots[0].basis == EstimateBasis.NO_PRICE_CONFIGURED


def test_a_partly_priceable_plan_refuses_to_publish_a_partial_total() -> None:
    """부분 합계는 전체처럼 읽힌다. 그래서 내지 않는다."""
    plans = plan_slots(
        prompt_count=1,
        slots=[
            ("openai", "gpt-5", SearchMode.NO_BROWSING),
            ("xai", "grok-4", SearchMode.NO_BROWSING),
        ],
        repetitions=1,
    )
    result = estimate_work(
        plans,
        prices=fresh_table(),
        baselines={
            "OPENAI:gpt-5:NO_BROWSING": TokenBaseline(1_000_000, 0, 4),
            "XAI:grok-4:NO_BROWSING": TokenBaseline(1_000_000, 0, 4),
        },
    )

    assert result.measurement == "PARTIAL"
    assert result.amount_usd is None
    assert result.total_calls == 2
    assert "합계를 내지 않습니다" in result.summary_ko


def test_search_call_fees_are_added_only_when_search_is_on() -> None:
    prices = {
        "gpt-5": {
            "input_usd_per_million": 0.0,
            "output_usd_per_million": 0.0,
            "search_usd_per_1k_calls": 10.0,
        }
    }
    baseline = TokenBaseline(input_tokens=100, output_tokens=100, samples=9)

    with_search = estimate_work(
        plan_slots(prompt_count=1, slots=[("openai", "gpt-5", SearchMode.BROWSING)], repetitions=1),
        prices=fresh_table(**prices),
        baselines={"OPENAI:gpt-5:BROWSING": baseline},
    )
    without_search = estimate_work(
        plan_slots(
            prompt_count=1, slots=[("openai", "gpt-5", SearchMode.NO_BROWSING)], repetitions=1
        ),
        prices=fresh_table(**prices),
        baselines={"OPENAI:gpt-5:NO_BROWSING": baseline},
    )

    assert with_search.amount_usd == pytest.approx(0.01)
    assert without_search.amount_usd == pytest.approx(0.0)


# --------------------------------------------------------------------------- #
# 기준선 — 중앙값, 그리고 반쪽 표본은 안 센다
# --------------------------------------------------------------------------- #


def test_baseline_uses_the_median_so_one_long_answer_does_not_move_it() -> None:
    baseline = median_baseline([(100, 200), (110, 210), (120, 220), (130, 20_000)])
    assert baseline is not None
    assert baseline.input_tokens == 115
    assert baseline.output_tokens == 215
    assert baseline.samples == 4


def test_samples_missing_either_side_are_not_counted() -> None:
    assert median_baseline([(100, None), (None, 200)]) is None

    baseline = median_baseline([(100, None), (300, 400)])
    assert baseline is not None
    assert baseline.samples == 1
    assert baseline.input_tokens == 300


def test_no_samples_means_no_baseline_rather_than_zero_tokens() -> None:
    assert median_baseline([]) is None
