"""저장된 AI 호출에서 이번 달 지출을 읽는다.

:mod:`veo.observability.cost` 는 예산과 '측정 불가' 를 다루는 어휘를 전부 갖고 있었고
—— :class:`~veo.observability.cost.BudgetReport`,
:class:`~veo.observability.cost.UnmeasurableReason` 다섯 종 —— **호출자가 없었다.**
:class:`~veo.observability.cost.BudgetTracker` 는 메모리 누산기라서 실행이 끝나면
사라지고, 저장된 행에서 같은 답을 만드는 코드는 어디에도 없었다.

그래서 "이번 달 얼마 썼나" 를 물을 데가 없었다. 값은 한 줄씩 `ai_answers` 에 있었는데
합계를 내는 질의가 없었다.

**가격표가 비어 있어도 이 보고는 쓸모가 있다.** 금액은 '측정 불가'로 남지만 호출 수와
토큰 수는 실측이고, 왜 못 쟀는지도 이유별로 나온다 — 그 이유가 곧 고쳐야 할 일이다.
0원으로 반올림하지 않는다. 모르는 것과 공짜인 것은 다르다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped
from veo.db.models.observation import AIAnswer, AIEngine
from veo.observability.cost import (
    BudgetReport,
    BudgetStatus,
    CostMeasurement,
    UnmeasurableReason,
    month_key,
)

#: 저장된 문자열을 이유로 옮기는 표. 모르는 값은 `UNSPECIFIED` 로 떨어진다 —
#: 지어낸 이유를 보이는 것보다 "말해 주지 않았다" 가 정확하다.
_BASIS_TO_REASON: dict[str, UnmeasurableReason] = {
    "PRICE_TABLE_STALE": UnmeasurableReason.PRICE_TABLE_STALE,
    "NO_PRICE_CONFIGURED": UnmeasurableReason.NO_PRICE_CONFIGURED,
    "NO_USAGE_REPORTED": UnmeasurableReason.NO_USAGE_REPORTED,
    "CALCULATED_FROM_USAGE": UnmeasurableReason.INVALID_COST_REPORTED,
}

#: 고칠 일을 이유별로 한 문장씩. 화면이 지어내지 않도록 여기서 정한다.
REMEDY_KO: dict[UnmeasurableReason, str] = {
    UnmeasurableReason.NO_PRICE_CONFIGURED: (
        "가격표에 이 모델이 없습니다. `packages/model-prices/` 에 오늘 날짜로 새 파일을 "
        "만들고 제공자 공식 가격을 넣으면 다음 실행부터 금액이 계산됩니다."
    ),
    UnmeasurableReason.PRICE_TABLE_STALE: (
        "가격표가 기준일에서 너무 오래 지났습니다. 새 날짜의 가격표를 추가해 주십시오 — "
        "옛 파일은 고치지 않습니다. 과거 실행의 비용이 재현되어야 합니다."
    ),
    UnmeasurableReason.NO_USAGE_REPORTED: (
        "제공자가 토큰 사용량을 알려주지 않았습니다. 대개 호출이 실패한 경우입니다. "
        "실패한 호출도 과금될 수 있어 0원으로 세지 않습니다."
    ),
    UnmeasurableReason.INVALID_COST_REPORTED: (
        "계산했다고 하면서 금액이 붙어 있지 않습니다. VEO 쪽 결함이므로 로그를 확인해 "
        "주십시오."
    ),
    UnmeasurableReason.SEARCH_USAGE_UNKNOWN: (
        "이 모델은 웹 검색에 호출당 요금을 따로 받는데(2026-08-08 기준 제공자별 "
        "1,000회당 $10~25), 검색이 몇 번 돌았는지를 어댑터가 세지 않았습니다. "
        "토큰만 더하면 실제 청구서보다 싸게 나오므로 금액을 내지 않았습니다. "
        "해당 제공자 어댑터가 응답에서 검색 횟수를 읽도록 고쳐야 합니다."
    ),
    UnmeasurableReason.SEARCH_CONTENT_NOT_SEPARABLE: (
        "이 모델은 검색으로 딸려온 토큰을 공짜로 처리하는데, 제공자가 프롬프트 토큰과 "
        "검색 토큰을 **합친 하나의 값**으로만 알려줍니다. 둘을 가를 수 없어 정확한 "
        "금액을 만들 수 없습니다 — 전부 과금으로 치면 과대, 전부 공짜로 치면 과소입니다. "
        "고칠 곳은 코드가 아니라 모델 선택입니다: 검색 토큰이 함께 과금되는 모델"
        "(예: gpt-5)로 바꾸면 금액이 정확히 나옵니다."
    ),
    UnmeasurableReason.UNSPECIFIED: (
        "이유가 기록되지 않았습니다. 이 칸이 생기기 전에 저장된 호출입니다."
    ),
}


@dataclass(frozen=True, slots=True)
class EngineUsage:
    """엔진 하나가 이 기간에 쓴 만큼."""

    engine: str
    calls: int
    input_tokens: int
    output_tokens: int
    #: 금액을 낼 수 있었던 호출의 합. 낼 수 없었던 호출은 여기 들어가지 않는다.
    measured_cost_usd: float
    unmeasurable_calls: int


@dataclass(frozen=True, slots=True)
class SpendReport:
    """이번 달 지출 — 잰 것과 못 잰 것을 나눠서."""

    budget: BudgetReport
    engines: tuple[EngineUsage, ...]
    input_tokens: int
    output_tokens: int

    @property
    def total_calls(self) -> int:
        return self.budget.measured_calls + self.budget.unmeasurable_calls

    def remedies_ko(self) -> tuple[str, ...]:
        """지금 무엇을 하면 금액을 알 수 있게 되는지. 해당하는 것만."""
        return tuple(
            REMEDY_KO[reason]
            for reason in sorted(
                self.budget.unmeasurable_by_reason, key=lambda item: item.value
            )
            if self.budget.unmeasurable_by_reason[reason]
        )


def _month_bounds(month: str) -> tuple[datetime, datetime]:
    year, number = (int(part) for part in month.split("-"))
    start = datetime(year, number, 1, tzinfo=UTC)
    end = (
        datetime(year + 1, 1, 1, tzinfo=UTC)
        if number == 12
        else datetime(year, number + 1, 1, tzinfo=UTC)
    )
    return start, end


def spend_for_month(
    db: Session,
    *,
    principal: Principal,
    month: str | None = None,
    limit_usd: float | None = None,
    warn_at_ratio: float = 0.8,
    now: datetime | None = None,
) -> SpendReport:
    """저장된 답변에서 한 달치 지출을 센다.

    호출 수와 토큰은 언제나 실측이다. 금액은 가격이 붙은 호출에서만 더하고, 나머지는
    이유별로 센다. 못 잰 호출을 0원으로 더하면 합계가 "예산 안" 처럼 보이는데, 그건
    자료가 뒷받침하지 않는 결론이다.
    """
    when = now or datetime.now(UTC)
    key = month or month_key(when)
    start, end = _month_bounds(key)

    statement = (
        select(
            AIEngine.provider,
            func.count(AIAnswer.id),
            func.coalesce(func.sum(AIAnswer.input_tokens), 0),
            func.coalesce(func.sum(AIAnswer.output_tokens), 0),
            func.coalesce(
                func.sum(func.coalesce(AIAnswer.cost_usd, 0.0)),
                0.0,
            ),
            func.count(AIAnswer.cost_usd),
            AIAnswer.cost_basis,
        )
        .join(AIEngine, AIEngine.id == AIAnswer.ai_engine_id)
        .where(
            AIAnswer.organization_id == principal.organization_id,
            AIAnswer.executed_at >= start,
            AIAnswer.executed_at < end,
        )
        .group_by(AIEngine.provider, AIAnswer.cost_basis)
    )
    assert_tenant_scoped(statement, principal.organization_id)

    by_engine: dict[str, list[float]] = {}
    reasons: dict[UnmeasurableReason, int] = {}
    spent = 0.0
    measured = 0
    unmeasurable = 0
    inputs = 0
    outputs = 0

    for name, calls, in_tokens, out_tokens, cost, priced, basis in db.execute(statement):
        bucket = by_engine.setdefault(name, [0.0, 0.0, 0.0, 0.0, 0.0])
        bucket[0] += calls
        bucket[1] += in_tokens
        bucket[2] += out_tokens
        bucket[3] += cost
        inputs += in_tokens
        outputs += out_tokens
        spent += cost
        measured += priced
        missing = calls - priced
        if missing:
            unmeasurable += missing
            bucket[4] += missing
            reason = _BASIS_TO_REASON.get(basis or "", UnmeasurableReason.UNSPECIFIED)
            reasons[reason] = reasons.get(reason, 0) + missing

    engines = tuple(
        EngineUsage(
            engine=name,
            calls=int(values[0]),
            input_tokens=int(values[1]),
            output_tokens=int(values[2]),
            measured_cost_usd=values[3],
            unmeasurable_calls=int(values[4]),
        )
        for name, values in sorted(by_engine.items())
    )

    budget = BudgetReport(
        organization_id=principal.organization_id,
        month=key,
        limit_usd=limit_usd,
        warn_at_ratio=warn_at_ratio,
        spent_usd=spent,
        measured_calls=measured,
        unmeasurable_calls=unmeasurable,
        unmeasurable_by_reason=reasons,
        status=_status(spent, limit_usd, warn_at_ratio),
        measurement=_measurement(measured, unmeasurable),
    )
    return SpendReport(
        budget=budget, engines=engines, input_tokens=inputs, output_tokens=outputs
    )


def _status(spent: float, limit: float | None, warn_at: float) -> BudgetStatus:
    if limit is None or limit <= 0:
        # 한도가 없으면 넘을 수도 없다. `OK` 는 "한도 안" 이 아니라 "경고할 일 없음" 이다.
        return BudgetStatus.OK
    if spent >= limit:
        return BudgetStatus.EXCEEDED
    if spent >= limit * warn_at:
        return BudgetStatus.WARNING
    return BudgetStatus.OK


def _measurement(measured: int, unmeasurable: int) -> CostMeasurement:
    """금액이 얼마나 실측인지. 하나도 못 쟀는데 `COMPLETE` 로 두면 0달러가 사실이 된다."""
    if measured and not unmeasurable:
        return CostMeasurement.COMPLETE
    if measured:
        return CostMeasurement.PARTIAL
    return CostMeasurement.NONE


__all__ = ["REMEDY_KO", "EngineUsage", "SpendReport", "spend_for_month"]
