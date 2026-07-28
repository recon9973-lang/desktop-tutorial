"""Metrics an operator can act on, from a layer that cannot take the product down.

Two things are being proven here. First, that the recorded series answer the questions
somebody asks at 3am — is the queue draining, is a provider down, are we about to blow
the budget. Second, and more important, that none of it can ever raise into a request:
an observability layer with the power to return a 500 is worse than no observability.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from veo.observability.metrics import (
    CIRCUIT_STATE_VALUES,
    InMemoryMetricSink,
    MetricName,
    MetricSink,
    NullMetricSink,
    SafeMetricSink,
    get_metric_sink,
    record_cost,
    record_crawl_response,
    record_http_request,
    record_llm_usage,
    record_provider_call,
    record_queue_state,
    record_report_generated,
    set_metric_sink,
)
from veo.observations.providers.base import CostBasis
from veo.providers.naver.errors import CircuitState


class ExplodingSink:
    """A backend having a bad day. Every method fails, in the rudest way available."""

    def increment(
        self, name: str, value: float = 1.0, labels: Mapping[str, str] | None = None
    ) -> None:
        raise RuntimeError("metrics backend unreachable")

    def gauge(
        self, name: str, value: float, labels: Mapping[str, str] | None = None
    ) -> None:
        raise RuntimeError("metrics backend unreachable")

    def observe(
        self, name: str, value: float, labels: Mapping[str, str] | None = None
    ) -> None:
        raise RuntimeError("metrics backend unreachable")


@pytest.fixture(autouse=True)
def _restore_global_sink() -> object:
    original = get_metric_sink()
    yield
    set_metric_sink(original)


# --------------------------------------------------------------------------- #
# The in-memory sink
# --------------------------------------------------------------------------- #


def test_counters_accumulate_per_label_set() -> None:
    sink = InMemoryMetricSink()
    sink.increment("veo_calls_total", labels={"provider": "NAVER"})
    sink.increment("veo_calls_total", labels={"provider": "NAVER"})
    sink.increment("veo_calls_total", labels={"provider": "OPENAI"})

    assert sink.counter_value("veo_calls_total", provider="NAVER") == 2.0
    assert sink.counter_value("veo_calls_total", provider="OPENAI") == 1.0
    assert sink.counter_value("veo_calls_total", provider="CLAUDE") == 0.0


def test_label_order_does_not_create_a_second_series() -> None:
    sink = InMemoryMetricSink()
    sink.increment("veo_calls_total", labels={"a": "1", "b": "2"})
    sink.increment("veo_calls_total", labels={"b": "2", "a": "1"})

    assert sink.counter_value("veo_calls_total", a="1", b="2") == 2.0


def test_a_gauge_holds_the_last_value_not_a_sum() -> None:
    sink = InMemoryMetricSink()
    sink.gauge(MetricName.QUEUE_DEPTH, 12, labels={"queue": "scans"})
    sink.gauge(MetricName.QUEUE_DEPTH, 3, labels={"queue": "scans"})

    assert sink.gauge_value(MetricName.QUEUE_DEPTH, queue="scans") == 3.0


def test_a_histogram_keeps_every_observation() -> None:
    sink = InMemoryMetricSink()
    for value in (10.0, 20.0, 30.0):
        sink.observe(MetricName.HTTP_REQUEST_DURATION_MS, value, labels={"route": "/x"})

    summary = sink.histogram_summary(MetricName.HTTP_REQUEST_DURATION_MS, route="/x")
    assert summary is not None
    assert summary.count == 3
    assert summary.total == pytest.approx(60.0)
    assert summary.maximum == pytest.approx(30.0)


def test_series_cardinality_is_capped_so_a_hostile_label_cannot_exhaust_memory() -> None:
    sink = InMemoryMetricSink(max_series=4)
    for index in range(50):
        sink.increment("veo_calls_total", labels={"tenant": str(index)})

    assert sink.series_count == 4
    assert sink.dropped_series >= 46


def test_a_counter_rejects_a_negative_step_without_raising() -> None:
    sink = InMemoryMetricSink()
    sink.increment("veo_calls_total", -5.0)

    assert sink.counter_value("veo_calls_total") == 0.0
    assert sink.rejected_samples == 1


def test_a_non_finite_observation_is_rejected_without_raising() -> None:
    sink = InMemoryMetricSink()
    sink.observe("veo_latency_ms", float("nan"))
    sink.gauge("veo_depth", float("inf"))

    assert sink.histogram_summary("veo_latency_ms") is None
    assert sink.gauge_value("veo_depth") is None
    assert sink.rejected_samples == 2


# --------------------------------------------------------------------------- #
# Instrumentation must not change behaviour
# --------------------------------------------------------------------------- #


def test_a_failing_sink_does_not_raise_into_the_caller() -> None:
    sink = SafeMetricSink(ExplodingSink())

    sink.increment("veo_calls_total")
    sink.gauge("veo_depth", 1.0)
    sink.observe("veo_latency_ms", 1.0)

    assert sink.failures == 3


def test_a_failing_sink_is_reported_once_and_then_stays_quiet() -> None:
    sink = SafeMetricSink(ExplodingSink())
    for _ in range(10):
        sink.increment("veo_calls_total")

    # Every failure is counted, but only the first is worth a log line; the rest would
    # simply move the outage from the metrics backend to the log pipeline.
    assert sink.failures == 10
    assert sink.reported_failures == 1


def test_the_global_sink_is_safe_even_when_something_unsafe_is_installed() -> None:
    set_metric_sink(ExplodingSink())

    record_http_request(
        get_metric_sink(), route="/api/v1/seo/scan", method="POST", status_code=200,
        duration_ms=12.0,
    )
    record_provider_call(
        get_metric_sink(), provider="NAVER", outcome="OK", duration_ms=5.0
    )


def test_the_recorder_helpers_accept_the_null_sink() -> None:
    sink: MetricSink = NullMetricSink()
    record_http_request(
        sink, route="/x", method="GET", status_code=200, duration_ms=1.0
    )
    record_queue_state(sink, queue="scans", depth=0)
    record_report_generated(sink, report_kind="seo", duration_ms=1.0)


# --------------------------------------------------------------------------- #
# The questions an operator actually asks
# --------------------------------------------------------------------------- #


def test_request_latency_and_error_rate_are_recorded_by_status_class() -> None:
    sink = InMemoryMetricSink()
    record_http_request(
        sink, route="/api/v1/seo/scan", method="POST", status_code=200, duration_ms=42.0
    )
    record_http_request(
        sink, route="/api/v1/seo/scan", method="POST", status_code=503, duration_ms=91.0
    )

    labels = {"route": "/api/v1/seo/scan", "method": "POST"}
    assert sink.counter_value(MetricName.HTTP_REQUESTS_TOTAL, **labels, status_class="2xx") == 1.0
    assert sink.counter_value(MetricName.HTTP_REQUESTS_TOTAL, **labels, status_class="5xx") == 1.0
    assert sink.counter_value(MetricName.HTTP_ERRORS_TOTAL, **labels, status_class="5xx") == 1.0
    summary = sink.histogram_summary(MetricName.HTTP_REQUEST_DURATION_MS, **labels)
    assert summary is not None and summary.count == 2


def test_queue_depth_wait_retries_and_dead_letters_are_all_visible() -> None:
    sink = InMemoryMetricSink()
    record_queue_state(
        sink, queue="scans", depth=17, wait_ms=4200.0, retries=2, dead_lettered=1
    )

    assert sink.gauge_value(MetricName.QUEUE_DEPTH, queue="scans") == 17.0
    summary = sink.histogram_summary(MetricName.QUEUE_WAIT_MS, queue="scans")
    assert summary is not None and summary.total == pytest.approx(4200.0)
    assert sink.counter_value(MetricName.JOB_RETRIES_TOTAL, queue="scans") == 2.0
    assert sink.counter_value(MetricName.JOB_DEAD_LETTERED_TOTAL, queue="scans") == 1.0


def test_crawl_pages_bytes_and_status_distribution_are_recorded() -> None:
    sink = InMemoryMetricSink()
    record_crawl_response(sink, status_code=200, bytes_read=51_200)
    record_crawl_response(sink, status_code=404, bytes_read=512)

    assert sink.counter_value(MetricName.CRAWL_PAGES_TOTAL, status_class="2xx") == 1.0
    assert sink.counter_value(MetricName.CRAWL_PAGES_TOTAL, status_class="4xx") == 1.0
    assert sink.counter_value(MetricName.CRAWL_BYTES_TOTAL) == pytest.approx(51_712.0)


def test_provider_rate_limits_server_errors_and_cache_hits_are_separable() -> None:
    sink = InMemoryMetricSink()
    record_provider_call(sink, provider="NAVER", outcome="OK", duration_ms=5.0, cache_hit=True)
    record_provider_call(sink, provider="NAVER", outcome="RATE_LIMITED", duration_ms=5.0)
    record_provider_call(sink, provider="NAVER", outcome="SERVER_ERROR", duration_ms=5.0)

    calls = MetricName.PROVIDER_CALLS_TOTAL
    assert sink.counter_value(calls, provider="NAVER", outcome="OK") == 1.0
    assert sink.counter_value(MetricName.PROVIDER_RATE_LIMITED_TOTAL, provider="NAVER") == 1.0
    assert sink.counter_value(MetricName.PROVIDER_SERVER_ERRORS_TOTAL, provider="NAVER") == 1.0
    assert sink.counter_value(MetricName.PROVIDER_CACHE_HITS_TOTAL, provider="NAVER") == 1.0


def test_circuit_state_is_a_gauge_an_alert_can_threshold_on() -> None:
    sink = InMemoryMetricSink()
    record_provider_call(
        sink,
        provider="NAVER",
        outcome="SERVER_ERROR",
        duration_ms=5.0,
        circuit_state=CircuitState.OPEN,
    )

    assert sink.gauge_value(MetricName.PROVIDER_CIRCUIT_STATE, provider="NAVER") == float(
        CIRCUIT_STATE_VALUES[CircuitState.OPEN]
    )
    assert CIRCUIT_STATE_VALUES[CircuitState.CLOSED] == 0


def test_llm_tokens_are_split_by_direction() -> None:
    sink = InMemoryMetricSink()
    record_llm_usage(sink, engine="OPENAI", model="gpt-5", input_tokens=1_000, output_tokens=250)

    labels = {"engine": "OPENAI", "model": "gpt-5"}
    assert sink.counter_value(MetricName.LLM_TOKENS_TOTAL, **labels, direction="input") == 1_000.0
    assert sink.counter_value(MetricName.LLM_TOKENS_TOTAL, **labels, direction="output") == 250.0


def test_an_unpriced_call_increments_its_own_counter_and_not_the_cost_total() -> None:
    sink = InMemoryMetricSink()
    record_cost(sink, engine="OPENAI", cost_usd=None, basis=CostBasis.PRICE_TABLE_STALE)

    assert sink.counter_value(MetricName.LLM_COST_USD_TOTAL, engine="OPENAI") == 0.0
    assert (
        sink.counter_value(
            MetricName.LLM_COST_UNMEASURABLE_TOTAL,
            engine="OPENAI",
            basis=CostBasis.PRICE_TABLE_STALE.value,
        )
        == 1.0
    )


def test_a_priced_call_adds_to_the_cost_total() -> None:
    sink = InMemoryMetricSink()
    record_cost(
        sink, engine="OPENAI", cost_usd=0.25, basis=CostBasis.CALCULATED_FROM_USAGE
    )

    assert sink.counter_value(MetricName.LLM_COST_USD_TOTAL, engine="OPENAI") == pytest.approx(0.25)
    assert sink.counter_value(MetricName.LLM_COST_UNMEASURABLE_TOTAL, engine="OPENAI") == 0.0


def test_report_generation_time_is_recorded_per_kind() -> None:
    sink = InMemoryMetricSink()
    record_report_generated(sink, report_kind="seo", duration_ms=1_820.0)

    summary = sink.histogram_summary(MetricName.REPORT_GENERATION_MS, report_kind="seo")
    assert summary is not None and summary.maximum == pytest.approx(1_820.0)


def test_tenant_pressure_is_attributable_without_naming_the_tenant() -> None:
    sink = InMemoryMetricSink()
    record_http_request(
        sink,
        route="/api/v1/seo/scan",
        method="POST",
        status_code=200,
        duration_ms=10.0,
        organization_hash="a1b2c3d4e5f60718",
    )

    assert (
        sink.counter_value(
            MetricName.HTTP_REQUESTS_BY_TENANT_TOTAL, organization_hash="a1b2c3d4e5f60718"
        )
        == 1.0
    )
