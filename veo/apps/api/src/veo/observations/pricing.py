"""Dated model price tables, and what happens when one goes stale.

The provider adapters ship an empty price table on purpose: a hard-coded price list is
correct the week it is written and quietly wrong afterwards, and a wrong figure rendered
as "this study cost $4.20" is precisely the plausible fabrication this product refuses to
produce. That is right, but it leaves budget ceilings unusable, because a run cannot be
held to a limit it cannot measure.

This module supplies the missing half: a price table is a **dated file with an expiry**.
Inside its window it prices what it knows. Past the window it stops pricing and reports
``PRICE_TABLE_STALE`` — never zero, because "we do not know what this cost" and "this was
free" are different facts and a budget report must not confuse them.

Updating prices means adding a new dated file, never editing an old one. The cost of a
run from three months ago has to stay reproducible.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from veo.observations.providers.base import CostBasis, ModelPrice, priced_call

_PRICES_DIR_ENV = "VEO_MODEL_PRICES_DIR"
_PACKAGE_RELATIVE = Path("packages") / "model-prices"


class PriceTableStaleError(ValueError):
    """The table is too old to price anything with."""


@dataclass(frozen=True, slots=True)
class DatedPriceTable:
    """Model prices that know how old they are."""

    version: str
    as_of: date
    stale_after_days: int
    currency: str
    prices: Mapping[str, ModelPrice]
    today: date

    @property
    def age_days(self) -> int:
        return (self.today - self.as_of).days

    @property
    def is_stale(self) -> bool:
        return self.age_days > self.stale_after_days

    def require_fresh(self) -> None:
        """Raise if this table may not be used — call before authorising a budgeted run."""
        if self.is_stale:
            raise PriceTableStaleError(
                f"가격표 {self.version}는 기준일 {self.as_of.isoformat()}로부터 "
                f"{self.age_days}일 지나 만료되었습니다 (허용 {self.stale_after_days}일). "
                "새 날짜의 가격표를 추가하십시오. 만료된 표로 계산한 비용은 실제와 "
                "다를 수 있어 금액으로 제시하지 않습니다."
            )

    def cost(
        self,
        *,
        model: str,
        model_version: str,
        input_tokens: int | None,
        output_tokens: int | None,
        search_calls: int | None = None,
    ) -> tuple[float | None, CostBasis]:
        """The cost of one call, or the reason there isn't one.

        Signature-compatible with the adapters' own ``PriceTable`` so it drops in.
        만료 확인만 여기서 하고, 산식은 :func:`priced_call` 하나를 함께 쓴다 — 두 벌이
        되면 언젠가 한쪽만 고쳐진다(0-D).
        """
        if input_tokens is None and output_tokens is None:
            return None, CostBasis.NO_USAGE_REPORTED
        if self.is_stale:
            return None, CostBasis.PRICE_TABLE_STALE

        price = self.prices.get(model_version) or self.prices.get(model)
        if price is None:
            return None, CostBasis.NO_PRICE_CONFIGURED

        return priced_call(price, input_tokens, output_tokens, search_calls)


def price_table_from_document(
    document: Mapping[str, Any], *, today: date | None = None
) -> DatedPriceTable:
    """Validate a price document into a table."""
    if "as_of" not in document:
        raise ValueError(
            "가격표에 as_of(기준일)가 없습니다. 기준일이 없으면 만료 여부를 알 수 없고, "
            "만료를 모르는 표는 만료된 표보다 위험합니다"
        )

    prices: dict[str, ModelPrice] = {}
    for key, entry in (document.get("prices") or {}).items():
        if not isinstance(entry, Mapping):
            raise ValueError(f"가격 항목 {key}의 형식이 올바르지 않습니다")
        try:
            input_price = float(entry["input_usd_per_million"])
            output_price = float(entry["output_usd_per_million"])
        except KeyError as exc:
            raise ValueError(
                f"가격 항목 {key}에 {exc.args[0]}가 없습니다. 입력·출력 단가를 모두 "
                "적어야 합니다 — 한쪽만 있으면 비용이 조용히 낮게 계산됩니다"
            ) from exc
        if input_price < 0 or output_price < 0:
            raise ValueError(f"가격 항목 {key}에 음수 단가가 있습니다")
        # 검색 요금은 없어도 된다 — 검색을 안 쓰는 모델이 있고, 아직 확인 못 한
        # 제공자도 있다. 다만 **적지 않은 것과 0은 다르다.** 적지 않으면 0으로 두되,
        # `search_content_tokens_free` 가 참이면 그 모델의 검색 호출은 금액을 못 낸다.
        search_fee = float(entry.get("search_usd_per_1k_calls", 0.0) or 0.0)
        if search_fee < 0:
            raise ValueError(f"가격 항목 {key}에 음수 검색 요금이 있습니다")
        prices[str(key)] = ModelPrice(
            input_usd_per_million=input_price,
            output_usd_per_million=output_price,
            search_usd_per_1k_calls=search_fee,
            search_content_tokens_free=bool(entry.get("search_content_tokens_free", False)),
        )

    stale_after = int(document.get("stale_after_days", 90))
    if stale_after <= 0:
        raise ValueError("stale_after_days는 양수여야 합니다")

    return DatedPriceTable(
        version=str(document.get("version", "model-prices/unversioned")),
        as_of=date.fromisoformat(str(document["as_of"])),
        stale_after_days=stale_after,
        currency=str(document.get("currency", "USD")),
        prices=prices,
        today=today or date.today(),
    )


def find_prices_root() -> Path:
    override = os.environ.get(_PRICES_DIR_ENV)
    if override:
        root = Path(override).expanduser().resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"{_PRICES_DIR_ENV}={override} is not a directory")
        return root

    for parent in Path(__file__).resolve().parents:
        candidate = parent / _PACKAGE_RELATIVE
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        "could not locate packages/model-prices; set "
        f"{_PRICES_DIR_ENV} to the price table directory"
    )


def load_price_table(*, today: date | None = None) -> DatedPriceTable:
    """Load the newest dated price table on disk."""
    root = find_prices_root()
    candidates = sorted(
        (p for p in root.iterdir() if p.suffix in {".yaml", ".yml"}),
        key=lambda p: p.stem,
    )
    if not candidates:
        raise FileNotFoundError(f"no price tables found under {root}")

    document = yaml.safe_load(candidates[-1].read_text(encoding="utf-8"))
    return price_table_from_document(document, today=today)


__all__ = [
    "DatedPriceTable",
    "PriceTableStaleError",
    "find_prices_root",
    "load_price_table",
    "price_table_from_document",
]
