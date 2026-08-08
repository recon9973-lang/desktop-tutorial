"""누르기 전에 얼마나 드는지 — 셀 수 있는 것만 세고, 나머지는 못 낸다고 말한다.

관측은 누르는 순간 외부 AI 에 돈을 쓴다. 그래서 누르기 전에 규모를 보여줘야 한다.
그런데 "얼마"는 두 조각으로 되어 있고 **한 조각만 지금 확실하다.**

* **호출 수** — 질문 수 x 칸 수 x 반복 수. 곱셈이고, 정확하다.
* **금액** — 단가(1M 토큰당) x 토큰 수. 단가는 가격표에 있다. 토큰 수는 **재 봐야
  안다.** 질문 하나가 몇 토큰짜리 답을 부를지는 모델과 질문에 달렸다.

그래서 이 모듈은 토큰을 **지어내지 않는다.** 같은 칸(엔진·모델·검색모드)에서 이미 잰
답변이 있으면 그 중앙값을 쓰고, 없으면 금액을 내지 않고 왜 못 내는지를 남긴다.

    "a wrong figure rendered as 'this study cost $4.20' is precisely the plausible
    fabrication this product refuses to produce" (pricing.py:4)

평균이 아니라 **중앙값**을 쓰는 이유: 답변 길이는 한쪽으로 길게 끌리는 분포라, 유난히
긴 답 하나가 평균을 끌어올린다. 예산을 재는 데 쓰는 값이므로 가운데 값이 낫다.

합계 규칙은 지출 보고서와 같다 — **금액을 못 낸 칸을 0원으로 더하지 않는다.** 더하면
합계가 '이 정도면 되겠다' 처럼 보이는데 자료가 그것을 뒷받침하지 않는다.
"""

from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from veo.observations.pricing import DatedPriceTable
from veo.observations.providers.base import CostBasis
from veo.observations.runs import SearchMode

__all__ = [
    "EstimateBasis",
    "SlotEstimate",
    "SlotPlan",
    "TokenBaseline",
    "WorkEstimate",
    "estimate_work",
    "median_baseline",
    "plan_slots",
]


class EstimateBasis:
    """왜 이 칸의 금액을 냈는지, 또는 왜 못 냈는지."""

    #: 같은 칸에서 실제로 잰 토큰이 있어 금액을 냈다.
    MEASURED = "MEASURED"
    #: 이 칸을 아직 한 번도 안 재 봤다. 토큰을 모르므로 금액을 못 낸다.
    #:
    #: `noqa: S105` — 이름에 `TOKEN` 이 들어가 린터가 비밀값으로 오인한다. 여기서 말하는
    #: 토큰은 **LLM 입력·출력 토큰 수**이고 자격증명이 아니다. 이름을 바꿔 린터를 피하면
    #: 읽는 사람이 무슨 토큰인지 알 수 없게 된다.
    NO_TOKEN_BASELINE = "NO_TOKEN_BASELINE"  # noqa: S105
    #: 가격표가 만료됐다.
    PRICE_TABLE_STALE = "PRICE_TABLE_STALE"
    #: 가격표에 이 모델이 없다.
    NO_PRICE_CONFIGURED = "NO_PRICE_CONFIGURED"
    #: 가격표 파일 자체가 없다. 모델이 빠진 것과 처방이 다르다.
    PRICE_TABLE_MISSING = "PRICE_TABLE_MISSING"
    #: 검색으로 딸려온 토큰을 가를 수 없어 이 모델의 검색 호출은 금액을 못 낸다.
    SEARCH_CONTENT_NOT_SEPARABLE = "SEARCH_CONTENT_NOT_SEPARABLE"
    #: 가격표가 금액을 안 냈는데 그 사유를 여기서 아직 옮기지 않았다.
    #:
    #: 지금 경로로는 나올 수 없다 — 토큰은 정수로 넣고 검색 횟수도 정해서 넣는다.
    #: 그래도 남겨 둔다. 가격표에 새 사유가 생겼을 때 **엉뚱한 이유를 붙이는 것보다
    #: 모른다고 하는 것이 낫다.**
    UNMAPPED_REASON = "UNMAPPED_REASON"


_BASIS_REASON_KO: Mapping[str, str] = {
    EstimateBasis.MEASURED: "같은 조건에서 이미 잰 토큰으로 계산했습니다",
    EstimateBasis.NO_TOKEN_BASELINE: (
        "이 조건으로 아직 한 번도 재지 않아 토큰을 모릅니다. 한 번 재고 나면 그다음부터 "
        "금액이 나옵니다"
    ),
    EstimateBasis.PRICE_TABLE_STALE: "가격표가 만료되었습니다. 새 날짜의 가격표가 필요합니다",
    EstimateBasis.NO_PRICE_CONFIGURED: "가격표에 이 모델의 단가가 없습니다",
    EstimateBasis.PRICE_TABLE_MISSING: (
        "가격표 파일을 읽지 못했습니다. `packages/model-prices/` 에 날짜가 붙은 표가 필요합니다"
    ),
    EstimateBasis.SEARCH_CONTENT_NOT_SEPARABLE: (
        "이 모델은 검색으로 딸려온 토큰을 가를 수 없어 검색 호출의 금액을 낼 수 없습니다"
    ),
    EstimateBasis.UNMAPPED_REASON: "가격표가 금액을 내지 않았고, 그 사유를 아직 옮기지 못했습니다",
}

_COST_BASIS_TO_ESTIMATE: Mapping[CostBasis, str] = {
    CostBasis.PRICE_TABLE_STALE: EstimateBasis.PRICE_TABLE_STALE,
    CostBasis.NO_PRICE_CONFIGURED: EstimateBasis.NO_PRICE_CONFIGURED,
    CostBasis.SEARCH_CONTENT_NOT_SEPARABLE: EstimateBasis.SEARCH_CONTENT_NOT_SEPARABLE,
}


@dataclass(frozen=True, slots=True)
class SlotPlan:
    """한 칸(엔진·모델·검색모드)에서 몇 번 부를 것인가."""

    engine: str
    model: str
    search_mode: SearchMode
    calls: int

    @property
    def slot(self) -> str:
        """`RunConditions.slot` 과 같은 축이어야 한다 — 다르면 짝이 안 맞는다."""
        return f"{self.engine.upper()}:{self.model}:{self.search_mode}"


@dataclass(frozen=True, slots=True)
class TokenBaseline:
    """같은 칸에서 이미 잰 토큰. `samples` 가 0이면 기준선이 없다는 뜻이다."""

    input_tokens: int
    output_tokens: int
    samples: int


@dataclass(frozen=True, slots=True)
class SlotEstimate:
    slot: str
    engine: str
    model: str
    search_mode: str
    calls: int
    amount_usd: float | None
    basis: str
    baseline_samples: int
    reason_ko: str


@dataclass(frozen=True, slots=True)
class WorkEstimate:
    """예상 규모. 호출 수는 언제나 정확하고, 금액은 낼 수 있을 때만 있다."""

    total_calls: int
    slots: tuple[SlotEstimate, ...]
    amount_usd: float | None
    #: COMPLETE | PARTIAL | NONE — 금액이 얼마나 실측에 근거하는가.
    measurement: str
    summary_ko: str
    remedies_ko: tuple[str, ...]


def plan_slots(
    *,
    prompt_count: int,
    slots: Sequence[tuple[str, str, SearchMode]],
    repetitions: int,
) -> tuple[SlotPlan, ...]:
    """칸마다 몇 번 부를지. 이 곱셈이 예상치의 유일한 확실한 부분이다."""
    if prompt_count < 0 or repetitions < 0:
        raise ValueError("질문 수와 반복 수는 음수일 수 없습니다")
    calls = prompt_count * repetitions
    return tuple(
        SlotPlan(engine=engine, model=model, search_mode=mode, calls=calls)
        for engine, model, mode in slots
    )


def estimate_work(
    plans: Sequence[SlotPlan],
    *,
    prices: DatedPriceTable | None,
    baselines: Mapping[str, TokenBaseline],
) -> WorkEstimate:
    """계획을 금액으로 옮긴다 — 옮길 수 있는 칸만.

    ``baselines`` 의 열쇠는 :attr:`SlotPlan.slot` 이다. 없는 칸은 기준선이 없는 칸이고,
    그 칸의 금액은 ``None`` 이 된다.

    ``prices`` 가 ``None`` 이면 가격표 파일을 못 읽었다는 뜻이다. 호출 수는 그래도 낸다 —
    규모를 아는 것과 금액을 아는 것은 별개이고, 앞의 것만으로도 누르기 전에 쓸모가 있다.
    """
    estimates: list[SlotEstimate] = []
    for plan in plans:
        baseline = baselines.get(plan.slot)
        estimates.append(_estimate_slot(plan, prices=prices, baseline=baseline))

    total_calls = sum(plan.calls for plan in plans)
    priced = [item for item in estimates if item.amount_usd is not None]
    unpriced = [item for item in estimates if item.amount_usd is None]

    if not estimates:
        measurement = "NONE"
        amount: float | None = None
    elif not unpriced:
        measurement = "COMPLETE"
        amount = round(sum(item.amount_usd or 0.0 for item in priced), 4)
    elif priced:
        # 일부만 낼 수 있으면 합계를 내지 않는다. 부분 합계는 전체처럼 읽히고,
        # 그렇게 읽히면 예산을 그 값에 맞춰 잡게 된다.
        measurement = "PARTIAL"
        amount = None
    else:
        measurement = "NONE"
        amount = None

    remedies = tuple(
        dict.fromkeys(
            _BASIS_REASON_KO[item.basis]
            for item in unpriced
            if item.basis in _BASIS_REASON_KO
        )
    )
    return WorkEstimate(
        total_calls=total_calls,
        slots=tuple(estimates),
        amount_usd=amount,
        measurement=measurement,
        summary_ko=_summary_ko(total_calls, len(plans), measurement, amount, len(unpriced)),
        remedies_ko=remedies,
    )


def _estimate_slot(
    plan: SlotPlan,
    *,
    prices: DatedPriceTable | None,
    baseline: TokenBaseline | None,
) -> SlotEstimate:
    def build(amount: float | None, basis: str, samples: int) -> SlotEstimate:
        return SlotEstimate(
            slot=plan.slot,
            engine=plan.engine,
            model=plan.model,
            search_mode=str(plan.search_mode),
            calls=plan.calls,
            amount_usd=amount,
            basis=basis,
            baseline_samples=samples,
            reason_ko=_BASIS_REASON_KO[basis],
        )

    if prices is None:
        return build(None, EstimateBasis.PRICE_TABLE_MISSING, baseline.samples if baseline else 0)

    if baseline is None or baseline.samples == 0:
        return build(None, EstimateBasis.NO_TOKEN_BASELINE, 0)

    # 검색 호출 요금은 켜져 있을 때만 붙는다 — 한 호출에 한 번으로 센다.
    search_calls = 1 if plan.search_mode is SearchMode.BROWSING else 0
    per_call, cost_basis = prices.cost(
        model=plan.model,
        model_version=plan.model,
        input_tokens=baseline.input_tokens,
        output_tokens=baseline.output_tokens,
        search_calls=search_calls,
    )
    if per_call is None:
        basis = _COST_BASIS_TO_ESTIMATE.get(cost_basis, EstimateBasis.UNMAPPED_REASON)
        return build(None, basis, baseline.samples)

    return build(round(per_call * plan.calls, 4), EstimateBasis.MEASURED, baseline.samples)


def _summary_ko(
    total_calls: int,
    slot_count: int,
    measurement: str,
    amount: float | None,
    unpriced: int,
) -> str:
    head = f"외부 AI 를 {total_calls:,}번 부릅니다 (조건 {slot_count}종)."
    if measurement == "COMPLETE" and amount is not None:
        return f"{head} 예상 비용 약 ${amount:,.2f} — 같은 조건에서 이미 잰 토큰으로 계산했습니다."
    if measurement == "PARTIAL":
        return (
            f"{head} 조건 {unpriced}종의 금액을 낼 수 없어 **합계를 내지 않습니다.** "
            "일부만 더한 값은 전체처럼 읽힙니다."
        )
    return f"{head} 아직 금액을 낼 수 없습니다 — 호출 수는 정확합니다."


def median_baseline(
    samples: Sequence[tuple[int | None, int | None]],
) -> TokenBaseline | None:
    """잰 토큰들에서 기준선 하나를 만든다. 입력·출력 둘 다 있는 표본만 센다."""
    pairs = [(inp, out) for inp, out in samples if inp is not None and out is not None]
    if not pairs:
        return None
    return TokenBaseline(
        input_tokens=int(statistics.median(inp for inp, _ in pairs)),
        output_tokens=int(statistics.median(out for _, out in pairs)),
        samples=len(pairs),
    )
