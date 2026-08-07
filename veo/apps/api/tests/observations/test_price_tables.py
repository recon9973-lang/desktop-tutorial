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
import yaml

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


def _shipped():  # type: ignore[no-untyped-def]
    """가장 최신 가격표를, **그 표의 기준일에** 읽는다.

    고정 날짜를 쓰면 90일 뒤 이 시험이 "만료됐다" 며 깨진다. 그것은 가격표를 갱신하라는
    신호로는 옳지만, 여기서 확인하려는 것(값이 실려 있는가·출처가 붙어 있는가)과는
    상관이 없다. 만료 자체는 위의 시험들이 이미 지킨다.
    """
    from veo.observations.pricing import find_prices_root

    newest = sorted(
        (p for p in find_prices_root().iterdir() if p.suffix in {".yaml", ".yml"}),
        key=lambda p: p.stem,
    )[-1]
    document = yaml.safe_load(newest.read_text(encoding="utf-8"))
    return document, load_price_table(today=date.fromisoformat(str(document["as_of"])))


def test_the_shipped_table_loads() -> None:
    table = load_price_table(today=TODAY)
    assert table.version.startswith("model-prices/")


def test_the_shipped_table_prices_the_models_observation_actually_calls() -> None:
    """빈 표는 안전한 기본값이 아니라 **자물쇠**였다.

    실측 2026-08-08: `runner.py` 는 예산 상한이 걸린 실행에서 비용을 못 재면 그 자리에서
    멈춘다(``StopReason.COST_UNMEASURABLE``). 표가 비어 있으면 모든 호출의 비용이 None
    이므로 **첫 호출에서 중단**된다 — 상한을 걸면 아무것도 못 돌고, 안 걸면 얼마 나가는지
    모르는 채로 돈을 쓴다. 둘 다 쓸 수 없었다.

    인용을 돌려주는 계열만 지킨다. 그것이 관측이 실제로 부르는 모델이다.
    """
    _, table = _shipped()

    for model in ("gpt-5", "gpt-4o"):
        # 검색이 안 돈 호출로 잰다 — 여기서 확인하려는 것은 **토큰 단가가 실려 있는가**
        # 하나다. 검색이 돈 호출의 셈은 TestTheSearchFeeIsCounted 가 따로 지킨다.
        cost, basis = table.cost(
            model=model,
            model_version=model,
            input_tokens=1_000_000,
            output_tokens=0,
            search_calls=0,
        )
        assert cost is not None, f"{model} 단가가 없어 예산 상한을 걸 수 없습니다"
        assert str(basis) == "CALCULATED_FROM_USAGE"


def test_a_dated_build_falls_back_to_its_model_price() -> None:
    """관측 기록의 `model_version` 은 `gpt-4o-mini-2024-07-18` 처럼 날짜가 붙은 실제
    빌드다. 그 키가 표에 없다고 비용을 포기하면, 실제로 부르는 모든 호출이 측정 불가가
    된다 — 표를 채운 의미가 사라진다."""
    _, table = _shipped()

    cost, basis = table.cost(
        model="gpt-4o-mini",
        model_version="gpt-4o-mini-2024-07-18",
        input_tokens=1_000_000,
        output_tokens=0,
        search_calls=0,
    )

    assert cost == pytest.approx(0.15)
    assert str(basis) == "CALCULATED_FROM_USAGE"


def test_an_unknown_model_is_still_not_free() -> None:
    """표를 채웠다고 해서 모르는 모델까지 0원이 되어서는 안 된다."""
    _, table = _shipped()

    cost, basis = table.cost(
        model="some-model-nobody-priced",
        model_version="v1",
        input_tokens=1000,
        output_tokens=1000,
    )

    assert cost is None
    assert str(basis) == "NO_PRICE_CONFIGURED"


def test_every_shipped_price_carries_where_it_came_from() -> None:
    """출처 없는 단가는 다음 사람이 확인할 방법이 없다.

    파서는 `source_url`·`verified_on` 을 요구하지 않는다 — 시험 문서까지 그것을 달아야
    하면 시험이 무거워진다. 대신 **실제로 발행되는 표**에만 이 관문을 건다. 값을 지어내
    넣으면 여기서 걸린다.
    """
    document, _ = _shipped()

    for key, entry in (document.get("prices") or {}).items():
        assert entry.get("source_url"), f"{key} 에 출처(source_url)가 없습니다"
        assert entry.get("verified_on"), f"{key} 에 확인 날짜(verified_on)가 없습니다"


class TestTheSearchFeeIsCounted:
    """토큰만 세면 청구서와 다르다.

    실측 2026-08-08 공식 문서: 주요 제공자 다섯 곳 중 넷이 웹 검색에 **호출당** 요금을
    따로 받는다(OpenAI $10~25/1k · Anthropic $10/1k · Gemini $14/1k · Perplexity
    $5~14/1k). 우리 계산은 입력·출력 토큰만 더하고 있었다 — 검색을 돌린 호출마다
    그만큼 적게 잡히고, **예산 상한이 실제보다 늦게 걸린다.** 늦게 걸리는 상한은
    없는 것과 같다.
    """

    def _table(self, **overrides):  # type: ignore[no-untyped-def]
        entry = {"input_usd_per_million": 1.25, "output_usd_per_million": 10.0}
        entry.update(overrides)
        return price_table_from_document(document(prices={"gpt-5": entry}), today=TODAY)

    def test_the_fee_is_added_per_search(self) -> None:
        table = self._table(search_usd_per_1k_calls=10.0)

        cost, basis = table.cost(
            model="gpt-5",
            model_version="gpt-5",
            input_tokens=1_000_000,
            output_tokens=0,
            search_calls=2,
        )

        # 토큰 $1.25 + 검색 2회 x $0.01
        assert cost == pytest.approx(1.27)
        assert str(basis) == "CALCULATED_FROM_USAGE"

    def test_no_search_means_no_fee(self) -> None:
        """검색을 켠 채 물어도 모델이 건너뛸 수 있다(2026-08-08 실측). 안 돌았으면
        요금도 없다 — 있지도 않은 비용을 세면 그것도 지어낸 값이다."""
        table = self._table(search_usd_per_1k_calls=10.0)

        cost, _ = table.cost(
            model="gpt-5",
            model_version="gpt-5",
            input_tokens=1_000_000,
            output_tokens=0,
            search_calls=0,
        )

        assert cost == pytest.approx(1.25)

    def test_an_unknown_search_count_is_not_zero(self) -> None:
        """검색 요금을 받는 모델인데 몇 번 돌았는지 모르면 **금액을 낼 수 없다.**

        0으로 두면 청구서보다 싼 값이 '측정된 금액' 으로 화면에 뜬다. 그것이 이
        제품이 만들지 않기로 한 종류의 숫자다.
        """
        table = self._table(search_usd_per_1k_calls=10.0)

        cost, basis = table.cost(
            model="gpt-5", model_version="gpt-5", input_tokens=1000, output_tokens=500
        )

        assert cost is None
        assert str(basis) == "SEARCH_USAGE_UNKNOWN"

    def test_a_model_with_no_search_fee_is_unaffected(self) -> None:
        """검색 요금이 없는 모델은 예전과 똑같이 계산된다. 검색 횟수를 안 넘겨도 된다."""
        table = self._table()

        cost, basis = table.cost(
            model="gpt-5", model_version="gpt-5", input_tokens=1_000_000, output_tokens=0
        )

        assert cost == pytest.approx(1.25)
        assert str(basis) == "CALCULATED_FROM_USAGE"

    def test_free_search_content_cannot_be_priced(self) -> None:
        """OpenAI 비추론 모델은 검색으로 딸려온 토큰이 무료다. 그런데 제공자는
        프롬프트와 검색 결과를 **합친** input_tokens 하나만 준다(실측: 17,264).

        가를 방법이 없다. 전부 과금으로 치면 과대, 전부 공짜로 치면 과소다.
        어느 쪽으로도 지어내지 않고 못 낸다고 말한다.
        """
        table = self._table(search_usd_per_1k_calls=25.0, search_content_tokens_free=True)

        cost, basis = table.cost(
            model="gpt-5",
            model_version="gpt-5",
            input_tokens=17_264,
            output_tokens=1_119,
            search_calls=1,
        )

        assert cost is None
        assert str(basis) == "SEARCH_CONTENT_NOT_SEPARABLE"

    def test_the_same_model_is_priceable_when_it_did_not_search(self) -> None:
        """검색을 안 한 호출에는 섞인 토큰이 없다. 그때는 정확히 낼 수 있다."""
        table = self._table(search_usd_per_1k_calls=25.0, search_content_tokens_free=True)

        cost, basis = table.cost(
            model="gpt-5",
            model_version="gpt-5",
            input_tokens=319,
            output_tokens=130,
            search_calls=0,
        )

        assert cost is not None
        assert str(basis) == "CALCULATED_FROM_USAGE"

    def test_a_negative_search_fee_is_refused(self) -> None:
        with pytest.raises(ValueError):
            self._table(search_usd_per_1k_calls=-1.0)


class TestTheShippedTableCarriesSearchFees:
    def test_the_models_we_observe_with_declare_a_search_fee(self) -> None:
        """실제로 관측에 쓰는 모델에 검색 요금이 없으면, 그 모델로 돈 실행은
        조용히 싸게 집계된다."""
        document_, _ = _shipped()

        for model in ("gpt-5", "gpt-4o"):
            entry = document_["prices"][model]
            assert entry.get("search_usd_per_1k_calls"), f"{model} 에 검색 요금이 없습니다"

    def test_the_shipped_gpt5_prices_a_searching_call(self) -> None:
        """gpt-5 를 고른 이유가 이것이다 — 검색 호출의 금액이 정확히 나온다."""
        _, table = _shipped()

        cost, basis = table.cost(
            model="gpt-5",
            model_version="gpt-5",
            input_tokens=17_264,
            output_tokens=1_119,
            search_calls=1,
        )

        # 17,264 x $1.25/M + 1,119 x $10/M + $10/1k
        assert cost == pytest.approx(0.042770, rel=1e-4)
        assert str(basis) == "CALCULATED_FROM_USAGE"


def test_output_is_never_cheaper_than_input() -> None:
    """뒤집힌 값을 걸러낸다.

    실측 2026-08-08: 검색 요약이 gpt-5 를 입력 $2.50 / 출력 $0.25 로 알려 왔다. 실제는
    입력 $1.25 / 출력 $10.00 이었다 — 출력이 입력의 8배인데 10분의 1로 적혀 있었다.
    그대로 넣었으면 **실제 비용의 40분의 1**을 예산으로 세고 상한을 넘겨 썼을 것이다.

    현재 주요 제공자는 전부 출력이 입력보다 비싸다. 이것은 물리 법칙이 아니라 관측된
    시장 관행이므로, 언젠가 뒤집힌 값이 진짜가 되면 이 시험을 근거와 함께 고친다 —
    그때는 고치는 사람이 근거를 대야 한다는 것이 이 관문의 값어치다.
    """
    document, _ = _shipped()

    for key, entry in (document.get("prices") or {}).items():
        assert entry["output_usd_per_million"] >= entry["input_usd_per_million"], (
            f"{key} 의 출력 단가가 입력보다 쌉니다 — 입·출력이 뒤바뀐 값일 수 있습니다"
        )


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
