"""A readiness view that a load balancer may poll and a stranger may read.

Readiness endpoints get scraped, cached, screenshotted into incident channels and pasted
into tickets. Anything that reaches this output has effectively been published, so the
tests below take the serialized document and search it for the exact secrets the probes
were handed. The other half of the file is the inverse rule: a probe that cannot answer
must degrade the report, never raise into whoever called it.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

from veo.contracts.enums import ProviderState
from veo.observability.health import (
    ComponentHealth,
    ComponentStatus,
    ReadinessProbe,
    ReadinessReport,
)
from veo.observations.pricing import DatedPriceTable, price_table_from_document

# The exact strings that must never reappear in the output.
DB_DSN = "postgresql+psycopg://veo_app:s3cr3t-pa55word@db.internal.venom:5432/veo"
REDIS_DSN = "redis://:tOpS3cr3tBrokerPass@cache.internal.venom:6379/0"
PROVIDER_KEY = "sk-live-9f3a2b7c1d8e4f6a0b5c7d9e1f3a5b7c"
SECRET_FRAGMENTS = (
    "s3cr3t-pa55word",
    "tOpS3cr3tBrokerPass",
    "9f3a2b7c1d8e4f6a0b5c7d9e1f3a5b7c",
    "db.internal.venom",
    "cache.internal.venom",
    "veo_app",
)

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)


def ok() -> None:
    return None


def price_table(as_of: str) -> DatedPriceTable:
    return price_table_from_document(
        {
            "version": f"model-prices/{as_of}",
            "as_of": as_of,
            "stale_after_days": 90,
            "currency": "USD",
            "prices": {"gpt-5": {"input_usd_per_million": 1.25, "output_usd_per_million": 10.0}},
        },
        today=date(2026, 7, 28),
    )


def fresh_price_table() -> DatedPriceTable:
    return price_table("2026-07-01")


def stale_price_table() -> DatedPriceTable:
    return price_table("2026-01-01")


def component(report: ReadinessReport, name: str) -> ComponentHealth:
    return next(item for item in report.components if item.name == name)


# --------------------------------------------------------------------------- #
# Readiness
# --------------------------------------------------------------------------- #


def test_everything_up_is_ready() -> None:
    probe = ReadinessProbe(
        checks={"database": ok, "queue": ok},
        provider_states=lambda: {"NAVER": ProviderState.ENABLED},
        price_table=fresh_price_table,
        clock=lambda: NOW,
    )
    report = probe.run()

    assert report.ready is True
    assert report.checked_at == NOW
    assert component(report, "database").status is ComponentStatus.UP
    assert component(report, "price_table").status is ComponentStatus.UP


def test_an_unreachable_database_makes_the_service_not_ready() -> None:
    def database() -> None:
        raise ConnectionError(f"could not connect to {DB_DSN}")

    probe = ReadinessProbe(checks={"database": database, "queue": ok}, clock=lambda: NOW)
    report = probe.run()

    assert report.ready is False
    assert component(report, "database").status is ComponentStatus.DOWN
    assert component(report, "queue").status is ComponentStatus.UP


def test_an_unreachable_queue_makes_the_service_not_ready() -> None:
    def queue() -> None:
        raise ConnectionError(f"broker down: {REDIS_DSN}")

    probe = ReadinessProbe(checks={"database": ok, "queue": queue}, clock=lambda: NOW)

    assert probe.run().ready is False


def test_a_disabled_provider_degrades_the_report_without_blocking_readiness() -> None:
    probe = ReadinessProbe(
        checks={"database": ok, "queue": ok},
        provider_states=lambda: {
            "NAVER": ProviderState.ENABLED,
            "OPENAI": ProviderState.DISABLED_NO_CREDENTIAL,
        },
        clock=lambda: NOW,
    )
    report = probe.run()

    # VEO reports 측정 불가 for a provider it cannot reach; that is a product state, not
    # a reason to take the API out of the load balancer.
    assert report.ready is True
    assert component(report, "provider.OPENAI").status is ComponentStatus.DEGRADED
    assert component(report, "provider.NAVER").status is ComponentStatus.UP


def test_a_stale_price_table_is_degraded_and_dated() -> None:
    probe = ReadinessProbe(
        checks={"database": ok, "queue": ok},
        price_table=stale_price_table,
        clock=lambda: NOW,
    )
    report = probe.run()

    table = component(report, "price_table")
    assert table.status is ComponentStatus.DEGRADED
    assert "2026-01-01" in table.detail_ko
    assert report.ready is True


def test_an_absent_price_table_is_unknown_rather_than_fine() -> None:
    probe = ReadinessProbe(
        checks={"database": ok, "queue": ok},
        price_table=lambda: None,
        clock=lambda: NOW,
    )

    assert component(probe.run(), "price_table").status is ComponentStatus.UNKNOWN


def test_a_probe_that_itself_explodes_degrades_instead_of_raising() -> None:
    def providers() -> dict[str, ProviderState]:
        raise RuntimeError(f"credential vault unavailable: {PROVIDER_KEY}")

    probe = ReadinessProbe(
        checks={"database": ok, "queue": ok},
        provider_states=providers,
        clock=lambda: NOW,
    )
    report = probe.run()

    assert report.ready is True
    assert component(report, "providers").status is ComponentStatus.UNKNOWN


def test_a_check_that_returns_a_reason_string_is_reported_as_degraded() -> None:
    probe = ReadinessProbe(
        checks={"database": ok, "queue": lambda: "브로커 지연이 큽니다"},
        clock=lambda: NOW,
    )
    report = probe.run()

    queue = component(report, "queue")
    assert queue.status is ComponentStatus.DEGRADED
    assert "브로커 지연" in queue.detail_ko
    assert report.ready is True


# --------------------------------------------------------------------------- #
# Nothing in here may be published
# --------------------------------------------------------------------------- #


def build_leaky_report() -> ReadinessReport:
    def database() -> None:
        raise ConnectionError(f"could not connect to {DB_DSN}")

    def queue() -> None:
        raise ConnectionError(f"broker refused: {REDIS_DSN}")

    def providers() -> dict[str, ProviderState]:
        raise RuntimeError(f"vault error with api_key={PROVIDER_KEY}")

    probe = ReadinessProbe(
        checks={"database": database, "queue": queue},
        provider_states=providers,
        price_table=stale_price_table,
        clock=lambda: NOW,
    )
    return probe.run()


def test_the_serialized_readiness_view_contains_no_secret() -> None:
    serialized = json.dumps(build_leaky_report().to_dict(), ensure_ascii=False)

    for fragment in SECRET_FRAGMENTS:
        assert fragment not in serialized, f"{fragment} leaked into the readiness view"


def test_the_serialized_readiness_view_contains_no_connection_string() -> None:
    serialized = json.dumps(build_leaky_report().to_dict(), ensure_ascii=False)

    assert "://" not in serialized
    assert "postgresql" not in serialized
    assert "redis" not in serialized


def test_the_view_still_says_what_is_wrong() -> None:
    report = build_leaky_report()
    serialized = json.dumps(report.to_dict(), ensure_ascii=False)

    assert report.ready is False
    assert "ConnectionError" in serialized
    assert "DOWN" in serialized


def test_the_serialized_view_round_trips_through_json_unchanged() -> None:
    document = build_leaky_report().to_dict()

    assert json.loads(json.dumps(document, ensure_ascii=False)) == document
    assert document["checked_at"] == NOW.isoformat()
