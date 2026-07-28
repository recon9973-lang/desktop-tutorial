"""Readiness, written on the assumption that its output is public.

A readiness view gets polled by a load balancer, cached by a proxy, screenshotted into an
incident channel and pasted into a ticket. Whatever reaches it has effectively been
published, and the usual way that goes wrong is a connection error: ``could not connect
to postgresql://veo_app:s3cr3t@db.internal:5432/veo`` is a perfectly ordinary exception
message and a complete set of database credentials.

So every string that leaves this module is scrubbed twice — once by the codebase's
credential scrubber, once more to remove whole URLs, because even with the password
redacted a DSN still discloses internal hostnames, ports and account names.

The second rule is that a probe may not raise. A readiness endpoint that 500s when the
credential vault is briefly unavailable turns a degraded dependency into an outage, which
is the exact failure mode an observability layer exists to prevent. A check that cannot
answer produces a component in the report, not an exception.

What blocks readiness and what does not:

* **Database and queue** are required. Without them a request cannot be served or a scan
  cannot be enqueued, so the instance should leave the load balancer.
* **Providers and the price table** are advisory. A provider without a credential makes
  VEO report 측정 불가 with a reason — a documented product state, not a reason to stop
  serving the ninety per cent of the product that does not need it.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Final, Protocol, runtime_checkable

from veo.contracts.enums import ProviderState
from veo.credentials.redaction import REDACTED, redact_exception
from veo.observability.logging import scrub_text

__all__ = [
    "ComponentHealth",
    "ComponentStatus",
    "PriceTableView",
    "ReadinessProbe",
    "ReadinessReport",
    "scrub_detail",
]

#: Any ``scheme://...`` run, removed whole. The credential scrubber already replaces the
#: password inside a DSN, but the remainder still names an internal host and account, and
#: an attacker reading a public readiness page should not be handed the topology.
_URL = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.\-]*://\S*")

#: Longer than this and a detail line is not a diagnosis, it is a payload.
MAX_DETAIL_LENGTH: Final = 200

#: Provider states that mean the provider is usable right now.
_HEALTHY_PROVIDER_STATES: Final = frozenset({ProviderState.ENABLED})


class ComponentStatus(StrEnum):
    """What is known about one dependency."""

    UP = "UP"
    #: Working, but not fully — a provider without a credential, an expired price table.
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    #: The probe could not answer. Distinct from ``DOWN``: "we cannot tell" and "it is
    #: broken" call for different responses, and collapsing them produces false pages.
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    """One dependency's state and a scrubbed sentence about it."""

    name: str
    status: ComponentStatus
    detail_ko: str
    required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "detail_ko": self.detail_ko,
            "required": self.required,
        }


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """The whole view. Safe to serve, safe to log, safe to paste into a ticket."""

    ready: bool
    checked_at: datetime
    components: tuple[ComponentHealth, ...]

    def to_dict(self) -> dict[str, Any]:
        """A JSON-serializable document. Contains no secret and no connection string."""
        return {
            "ready": self.ready,
            "checked_at": self.checked_at.isoformat(),
            "components": [component.to_dict() for component in self.components],
        }

    def component(self, name: str) -> ComponentHealth | None:
        return next((item for item in self.components if item.name == name), None)


@runtime_checkable
class PriceTableView(Protocol):
    """The part of a dated price table readiness needs.

    Structural, so :class:`veo.observations.pricing.DatedPriceTable` satisfies it without
    this module importing YAML loading and a filesystem search into the health path.
    """

    @property
    def version(self) -> str: ...

    @property
    def as_of(self) -> date: ...

    @property
    def age_days(self) -> int: ...

    @property
    def stale_after_days(self) -> int: ...

    @property
    def is_stale(self) -> bool: ...


def scrub_detail(text: str) -> str:
    """Make one sentence safe to publish.

    URLs go first and go whole: after the credential scrubber has removed the password
    from a DSN, what is left still names the host, the port and the account, and that is
    an internal topology map served to anybody who can reach ``/readyz``.
    """
    without_urls = _URL.sub(REDACTED, text)
    scrubbed = scrub_text(without_urls)
    if len(scrubbed) > MAX_DETAIL_LENGTH:
        scrubbed = scrubbed[:MAX_DETAIL_LENGTH] + "…"
    return scrubbed


#: A check returns ``None`` when the dependency is fine, or a short Korean sentence
#: describing a degradation. Raising means the dependency is down.
HealthCheck = Callable[[], str | None]


class ReadinessProbe:
    """Runs every check and assembles a report. Never raises, whatever the checks do."""

    def __init__(
        self,
        checks: Mapping[str, HealthCheck],
        *,
        provider_states: Callable[[], Mapping[str, ProviderState]] | None = None,
        price_table: Callable[[], PriceTableView | None] | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._checks = dict(checks)
        self._provider_states = provider_states
        self._price_table = price_table
        self._clock = clock

    def run(self) -> ReadinessReport:
        components: list[ComponentHealth] = [
            self._run_check(name, check) for name, check in self._checks.items()
        ]
        components.extend(self._provider_components())
        components.extend(self._price_table_components())

        ready = not any(
            item.required and item.status is ComponentStatus.DOWN for item in components
        )
        return ReadinessReport(
            ready=ready, checked_at=self._clock(), components=tuple(components)
        )

    # -- required dependencies --------------------------------------------- #

    def _run_check(self, name: str, check: HealthCheck) -> ComponentHealth:
        try:
            reason = check()
        except Exception as exc:  # the probe reports failure, it does not propagate it
            return ComponentHealth(
                name=name,
                status=ComponentStatus.DOWN,
                detail_ko=scrub_detail(redact_exception(exc)),
                required=True,
            )
        if reason is None:
            return ComponentHealth(
                name=name, status=ComponentStatus.UP, detail_ko="정상", required=True
            )
        return ComponentHealth(
            name=name,
            status=ComponentStatus.DEGRADED,
            detail_ko=scrub_detail(str(reason)),
            required=True,
        )

    # -- advisory dependencies --------------------------------------------- #

    def _provider_components(self) -> list[ComponentHealth]:
        if self._provider_states is None:
            return []
        try:
            states = self._provider_states()
        except Exception as exc:  # a vault hiccup is not an API outage
            return [
                ComponentHealth(
                    name="providers",
                    status=ComponentStatus.UNKNOWN,
                    detail_ko=scrub_detail(
                        f"제공자 상태를 확인하지 못했습니다: {redact_exception(exc)}"
                    ),
                )
            ]

        components: list[ComponentHealth] = []
        for provider, state in sorted(states.items()):
            healthy = state in _HEALTHY_PROVIDER_STATES
            components.append(
                ComponentHealth(
                    name=f"provider.{provider}",
                    status=ComponentStatus.UP if healthy else ComponentStatus.DEGRADED,
                    detail_ko=(
                        "정상"
                        if healthy
                        else f"상태 {state.value} — 관련 항목은 '측정 불가'로 보고됩니다"
                    ),
                )
            )
        return components

    def _price_table_components(self) -> list[ComponentHealth]:
        if self._price_table is None:
            return []
        try:
            table = self._price_table()
        except Exception as exc:
            return [
                ComponentHealth(
                    name="price_table",
                    status=ComponentStatus.UNKNOWN,
                    detail_ko=scrub_detail(
                        f"가격표를 읽지 못했습니다: {redact_exception(exc)}"
                    ),
                )
            ]

        if table is None:
            return [
                ComponentHealth(
                    name="price_table",
                    status=ComponentStatus.UNKNOWN,
                    detail_ko=(
                        "가격표가 없습니다. 비용은 '측정 불가'로 보고되며 0원으로 계산되지 "
                        "않습니다."
                    ),
                )
            ]

        if table.is_stale:
            return [
                ComponentHealth(
                    name="price_table",
                    status=ComponentStatus.DEGRADED,
                    detail_ko=scrub_detail(
                        f"가격표 {table.version}는 기준일 {table.as_of.isoformat()}로부터 "
                        f"{table.age_days}일 지나 만료되었습니다 "
                        f"(허용 {table.stale_after_days}일). 비용은 '측정 불가'입니다."
                    ),
                )
            ]

        return [
            ComponentHealth(
                name="price_table",
                status=ComponentStatus.UP,
                detail_ko=scrub_detail(
                    f"가격표 {table.version} 사용 중 (기준일 {table.as_of.isoformat()}, "
                    f"{table.age_days}일 경과)"
                ),
            )
        ]
