"""Budget tracking, and the one arithmetic mistake that would make it useless.

A month of AI answer runs has a bill attached. VEO wants to warn before that bill becomes
a surprise, which means adding up what each call cost. Some calls have no cost: the price
table expired, nobody configured a price for the model, the provider reported no usage.
:class:`~veo.observations.providers.base.CostBasis` already says which.

The mistake is to add those in as zero. Do that and a month in which the price table
silently expired reports ``$0.00``, the alert stays green, and the actual spend is
whatever it happened to be. The opposite mistake — calling an unpriced call infinitely
expensive — fires every night until somebody mutes the alert, at which point it is worth
less than nothing.

So unmeasurable is neither. It is a third state, counted separately, carried into the
report, and printed in the alert text. The sentence an operator should read is:

    이번 달 지출은 $40.00입니다. 가격을 알 수 없어 비용을 계산하지 못한 호출이 120건 있습니다.

That sentence is honest and actionable. ``$40.00`` alone is neither.

The store is in memory, per process. Persistence belongs to whoever owns the database
schema; :meth:`BudgetTracker.record` is the API that survives that move.
"""

from __future__ import annotations

import math
import threading
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from veo.observations.providers.base import CostBasis

__all__ = [
    "BudgetReport",
    "BudgetStatus",
    "BudgetTracker",
    "CostMeasurement",
    "UnmeasurableReason",
    "month_key",
]


class BudgetStatus(StrEnum):
    """How this month's *measured* spend stands against the limit."""

    OK = "OK"
    WARNING = "WARNING"
    EXCEEDED = "EXCEEDED"


class CostMeasurement(StrEnum):
    """How much of the month's spend VEO was able to price at all.

    Read alongside :class:`BudgetStatus`, never instead of it. ``OK`` with ``NONE`` means
    "under budget as far as we can tell, and we cannot tell at all".
    """

    #: Every call had a price.
    COMPLETE = "COMPLETE"
    #: Some calls had a price and some did not.
    PARTIAL = "PARTIAL"
    #: Nothing could be priced. The total is zero because it is empty, not because the
    #: month was free.
    NONE = "NONE"


class UnmeasurableReason(StrEnum):
    """Why a call has no cost. Every one of these is a different remedy."""

    #: The price table is past its expiry — add a new dated table.
    PRICE_TABLE_STALE = "PRICE_TABLE_STALE"
    #: Nobody has told VEO what this model costs — add the model to the table.
    NO_PRICE_CONFIGURED = "NO_PRICE_CONFIGURED"
    #: The provider reported no token usage, typically because the call failed.
    NO_USAGE_REPORTED = "NO_USAGE_REPORTED"
    #: A figure arrived that is not a cost: negative, NaN, infinite, or a basis claiming
    #: a calculation with no number attached. A caller bug, recorded rather than raised —
    #: instrumentation does not get to fail a customer's scan.
    INVALID_COST_REPORTED = "INVALID_COST_REPORTED"
    #: No cost and no basis. The caller said nothing, so neither does the report.
    UNSPECIFIED = "UNSPECIFIED"


_BASIS_TO_REASON: Mapping[CostBasis, UnmeasurableReason] = {
    CostBasis.PRICE_TABLE_STALE: UnmeasurableReason.PRICE_TABLE_STALE,
    CostBasis.NO_PRICE_CONFIGURED: UnmeasurableReason.NO_PRICE_CONFIGURED,
    CostBasis.NO_USAGE_REPORTED: UnmeasurableReason.NO_USAGE_REPORTED,
    # A basis of CALCULATED_FROM_USAGE with no figure attached contradicts itself.
    CostBasis.CALCULATED_FROM_USAGE: UnmeasurableReason.INVALID_COST_REPORTED,
}


def month_key(when: datetime) -> str:
    """The ``YYYY-MM`` bucket a timestamp belongs to, in UTC.

    A naive datetime is refused rather than assumed to be UTC. Billing periods turn over
    at a boundary, and a call recorded at 23:59 Seoul time belongs to a different month
    depending on that assumption — which is exactly the kind of quiet nine-hour error
    that makes a budget report impossible to reconcile against an invoice.
    """
    if when.tzinfo is None or when.tzinfo.utcoffset(when) is None:
        raise ValueError("시간대가 없는 시각은 사용할 수 없습니다. tz-aware datetime을 주십시오.")
    utc = when.astimezone(UTC)
    return f"{utc.year:04d}-{utc.month:02d}"


@dataclass(frozen=True, slots=True)
class BudgetReport:
    """What one organization spent in one month, and what could not be priced."""

    organization_id: uuid.UUID
    month: str
    limit_usd: float | None
    warn_at_ratio: float
    spent_usd: float
    measured_calls: int
    unmeasurable_calls: int
    unmeasurable_by_reason: Mapping[UnmeasurableReason, int]
    status: BudgetStatus
    measurement: CostMeasurement

    @property
    def ratio(self) -> float | None:
        """Fraction of the limit consumed, or ``None`` when that would be a fiction.

        ``None`` where there is no limit, and ``None`` where nothing could be priced —
        because ``0.0`` there would read as "comfortably under budget", which is the one
        conclusion the data does not support.
        """
        if self.limit_usd is None or self.limit_usd <= 0:
            return None
        if self.measurement is CostMeasurement.NONE and self.unmeasurable_calls:
            return None
        return self.spent_usd / self.limit_usd

    def alert_line_ko(self) -> str:
        """The sentence that goes into the alert. Both halves, always."""
        parts = [
            f"조직 {self.organization_id} / {self.month}: "
            f"측정된 지출은 ${self.spent_usd:.2f}입니다"
        ]
        if self.limit_usd is not None:
            ratio = self.ratio
            share = "" if ratio is None else f", 예산 ${self.limit_usd:.2f}의 {ratio * 100:.1f}%"
            parts.append(f"(한도 ${self.limit_usd:.2f}{share}; 상태 {self.status.value})")
        else:
            parts.append("(예산 한도가 설정되어 있지 않습니다)")

        if self.unmeasurable_calls:
            reasons = ", ".join(
                f"{reason.value} {count}건"
                for reason, count in sorted(
                    self.unmeasurable_by_reason.items(), key=lambda item: item[0].value
                )
            )
            parts.append(
                f". 다만 가격을 알 수 없어 '측정 불가'로 남은 호출이 "
                f"{self.unmeasurable_calls}건 있습니다 ({reasons}). "
                "실제 지출은 위 금액보다 클 수 있으며, VEO는 이 호출들을 0원으로 계산하지 "
                "않습니다."
            )
        else:
            parts.append(". 이 기간의 모든 호출에 가격이 적용되었습니다.")
        return "".join(parts)


@dataclass(slots=True)
class _Bucket:
    spent_usd: float = 0.0
    measured_calls: int = 0
    unmeasurable: dict[UnmeasurableReason, int] = field(default_factory=dict)


class BudgetTracker:
    """Accumulates spend per organization per month, and says when to worry.

    Thread-safe, because a worker pool records into one of these from several threads and
    a lost increment is an under-report — the direction of error a budget alert must never
    make.
    """

    def __init__(
        self,
        *,
        default_limit_usd: float | None = None,
        warn_at_ratio: float = 0.8,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if default_limit_usd is not None and (
            not math.isfinite(default_limit_usd) or default_limit_usd < 0
        ):
            raise ValueError("default limit must be a non-negative finite number of USD")
        if not math.isfinite(warn_at_ratio) or not 0.0 < warn_at_ratio <= 1.0:
            raise ValueError("warn_at_ratio must be greater than 0 and at most 1")

        self._default_limit = default_limit_usd
        self._warn_at_ratio = warn_at_ratio
        self._clock = clock
        self._lock = threading.Lock()
        self._buckets: dict[tuple[uuid.UUID, str], _Bucket] = {}
        self._limits: dict[uuid.UUID, float] = {}

    # -- configuration ------------------------------------------------------ #

    def set_limit(self, organization_id: uuid.UUID, limit_usd: float) -> None:
        """Override the default monthly ceiling for one organization."""
        if not math.isfinite(limit_usd) or limit_usd < 0:
            raise ValueError("limit must be a non-negative finite number of USD")
        with self._lock:
            self._limits[organization_id] = limit_usd

    def limit_for(self, organization_id: uuid.UUID) -> float | None:
        with self._lock:
            return self._limits.get(organization_id, self._default_limit)

    # -- accumulation ------------------------------------------------------- #

    def record(
        self,
        *,
        organization_id: uuid.UUID,
        cost_usd: float | None,
        basis: CostBasis | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        """Record one call.

        ``cost_usd=None`` is the honest shape the provider adapters produce and is
        recorded as unmeasurable under the reason its ``basis`` gives. A figure that is
        not a cost — negative, NaN, infinite — is recorded the same way rather than
        raising: this is instrumentation, and it does not get to fail the work it is
        measuring.
        """
        when = occurred_at if occurred_at is not None else self._clock()
        key = (organization_id, month_key(when))

        with self._lock:
            bucket = self._buckets.setdefault(key, _Bucket())
            if cost_usd is None:
                reason = (
                    _BASIS_TO_REASON.get(basis, UnmeasurableReason.UNSPECIFIED)
                    if basis is not None
                    else UnmeasurableReason.UNSPECIFIED
                )
                bucket.unmeasurable[reason] = bucket.unmeasurable.get(reason, 0) + 1
                return
            if not math.isfinite(cost_usd) or cost_usd < 0:
                bucket.unmeasurable[UnmeasurableReason.INVALID_COST_REPORTED] = (
                    bucket.unmeasurable.get(UnmeasurableReason.INVALID_COST_REPORTED, 0) + 1
                )
                return
            bucket.spent_usd += cost_usd
            bucket.measured_calls += 1

    # -- reading ------------------------------------------------------------ #

    def months(self, organization_id: uuid.UUID) -> list[str]:
        """Every month this organization has records for, oldest first."""
        with self._lock:
            return sorted(month for org, month in self._buckets if org == organization_id)

    def report(self, organization_id: uuid.UUID, *, month: str | None = None) -> BudgetReport:
        """The month's position. Defaults to the month in progress."""
        period = month if month is not None else month_key(self._clock())
        with self._lock:
            bucket = self._buckets.get((organization_id, period), _Bucket())
            limit = self._limits.get(organization_id, self._default_limit)
            spent = bucket.spent_usd
            measured = bucket.measured_calls
            unmeasurable = dict(bucket.unmeasurable)

        unmeasurable_calls = sum(unmeasurable.values())
        return BudgetReport(
            organization_id=organization_id,
            month=period,
            limit_usd=limit,
            warn_at_ratio=self._warn_at_ratio,
            spent_usd=spent,
            measured_calls=measured,
            unmeasurable_calls=unmeasurable_calls,
            unmeasurable_by_reason=unmeasurable,
            status=self._status(spent, limit),
            measurement=_measurement(measured, unmeasurable_calls),
        )

    def _status(self, spent: float, limit: float | None) -> BudgetStatus:
        """The threshold fires *at* the ratio, not past it.

        ``>=`` rather than ``>``: an operator who sets 80% expects to hear about it when
        spend reaches 80%, and a warning that arrives one call later is a warning that
        arrived after the thing it was meant to precede.
        """
        if limit is None or limit <= 0:
            return BudgetStatus.OK
        if spent > limit:
            return BudgetStatus.EXCEEDED
        if spent >= limit * self._warn_at_ratio:
            return BudgetStatus.WARNING
        return BudgetStatus.OK


def _measurement(measured_calls: int, unmeasurable_calls: int) -> CostMeasurement:
    if unmeasurable_calls == 0:
        return CostMeasurement.COMPLETE
    if measured_calls == 0:
        return CostMeasurement.NONE
    return CostMeasurement.PARTIAL
