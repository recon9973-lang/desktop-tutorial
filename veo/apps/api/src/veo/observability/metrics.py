"""Metrics an operator can act on, behind a seam that keeps Prometheus out of here.

Every series in :class:`MetricName` exists to answer a question somebody asks at 3am:

* *Is the API healthy?* — request latency and error rate, by route and status class.
* *Is the queue draining?* — depth, wait time, retries, dead letters.
* *Is a crawl making progress or being blocked?* — pages, bytes, status distribution.
* *Is a provider down or throttling us?* — calls, 429s, 5xx, circuit state, cache hits.
* *Are we about to exceed the month's budget?* — tokens, priced cost, and — separately —
  the calls that could not be priced at all.
* *Which tenant is hammering us?* — request counts against a hashed organization id.

Nothing else is here. A series nobody would page on is a series that costs storage and
attention and pays back neither.

Two structural decisions:

**The protocol is the seam.** :class:`MetricSink` is three methods. An exporter — for
Prometheus, OTLP, StatsD, whatever this eventually runs on — implements it without this
package taking a dependency on any of them, and without a client library's global
registry becoming part of VEO's import graph.

**Instrumentation may not change behaviour.** :class:`SafeMetricSink` swallows everything
a backend can throw, and :func:`set_metric_sink` wraps whatever it is given so the global
path is safe by construction. An observability layer that can return a 500 is worse than
no observability layer.
"""

from __future__ import annotations

import math
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Protocol

from veo.observations.providers.base import CostBasis
from veo.providers.naver.errors import CircuitState

__all__ = [
    "CIRCUIT_STATE_VALUES",
    "HistogramSummary",
    "InMemoryMetricSink",
    "MetricName",
    "MetricSink",
    "MetricsSnapshot",
    "NullMetricSink",
    "SafeMetricSink",
    "get_metric_sink",
    "record_cost",
    "record_crawl_response",
    "record_http_request",
    "record_llm_usage",
    "record_provider_call",
    "record_queue_state",
    "record_report_generated",
    "set_metric_sink",
    "status_class",
]


class MetricName(StrEnum):
    """Every series VEO emits, named once so no call site can misspell one."""

    # Is the API healthy?
    HTTP_REQUESTS_TOTAL = "veo_http_requests_total"
    HTTP_ERRORS_TOTAL = "veo_http_errors_total"
    HTTP_REQUEST_DURATION_MS = "veo_http_request_duration_ms"
    HTTP_REQUESTS_BY_TENANT_TOTAL = "veo_http_requests_by_tenant_total"

    # Is the queue draining?
    QUEUE_DEPTH = "veo_queue_depth"
    QUEUE_WAIT_MS = "veo_queue_wait_ms"
    JOB_RETRIES_TOTAL = "veo_job_retries_total"
    JOB_DEAD_LETTERED_TOTAL = "veo_job_dead_lettered_total"

    # Is the crawl getting anywhere?
    CRAWL_PAGES_TOTAL = "veo_crawl_pages_total"
    CRAWL_BYTES_TOTAL = "veo_crawl_bytes_total"

    # Is a provider down?
    PROVIDER_CALLS_TOTAL = "veo_provider_calls_total"
    PROVIDER_CALL_DURATION_MS = "veo_provider_call_duration_ms"
    PROVIDER_RATE_LIMITED_TOTAL = "veo_provider_rate_limited_total"
    PROVIDER_SERVER_ERRORS_TOTAL = "veo_provider_server_errors_total"
    PROVIDER_CIRCUIT_STATE = "veo_provider_circuit_state"
    PROVIDER_CACHE_HITS_TOTAL = "veo_provider_cache_hits_total"

    # What is this costing?
    LLM_TOKENS_TOTAL = "veo_llm_tokens_total"
    LLM_COST_USD_TOTAL = "veo_llm_cost_usd_total"
    #: Calls whose price is unknown. Deliberately *not* folded into the cost total: see
    #: :mod:`veo.observability.cost`. An alert that reads the cost total alone will
    #: under-report, which is why this counter sits beside it and should be on the same
    #: dashboard panel.
    LLM_COST_UNMEASURABLE_TOTAL = "veo_llm_cost_unmeasurable_total"

    # How long does a report take?
    REPORT_GENERATION_MS = "veo_report_generation_ms"


#: Circuit state as a number an alert rule can threshold on. Ordered by badness, so
#: ``> 0`` means "not serving normally" and ``>= 2`` means "not calling the provider at
#: all" without the rule having to know the enum.
CIRCUIT_STATE_VALUES: Final[Mapping[CircuitState, int]] = {
    CircuitState.CLOSED: 0,
    CircuitState.HALF_OPEN: 1,
    CircuitState.OPEN: 2,
}

#: Beyond this many distinct label combinations the in-memory sink stops creating series.
#: One unbounded label — a raw URL, a customer id — is the standard way a metrics client
#: becomes a memory leak.
DEFAULT_MAX_SERIES: Final = 10_000


def status_class(status_code: int) -> str:
    """``503`` becomes ``5xx``. The status itself is too high-cardinality to group on."""
    return f"{status_code // 100}xx"


# --------------------------------------------------------------------------- #
# The seam
# --------------------------------------------------------------------------- #


class MetricSink(Protocol):
    """Where a measurement goes. Three methods, no lifecycle, no registry.

    Implementations must not raise. Callers that cannot guarantee that about a backend
    should wrap it in :class:`SafeMetricSink` — which :func:`set_metric_sink` does for
    the global sink automatically.
    """

    def increment(
        self, name: str, value: float = 1.0, labels: Mapping[str, str] | None = None
    ) -> None:
        """Add to a monotonic counter."""

    def gauge(self, name: str, value: float, labels: Mapping[str, str] | None = None) -> None:
        """Set a value that can go up and down."""

    def observe(self, name: str, value: float, labels: Mapping[str, str] | None = None) -> None:
        """Record one sample in a distribution."""


class NullMetricSink:
    """The default. Costs nothing and cannot fail."""

    def increment(
        self, name: str, value: float = 1.0, labels: Mapping[str, str] | None = None
    ) -> None:
        return None

    def gauge(self, name: str, value: float, labels: Mapping[str, str] | None = None) -> None:
        return None

    def observe(self, name: str, value: float, labels: Mapping[str, str] | None = None) -> None:
        return None


@dataclass(frozen=True, slots=True)
class HistogramSummary:
    """What an in-memory distribution can say about itself without buckets."""

    count: int
    total: float
    minimum: float
    maximum: float

    @property
    def mean(self) -> float:
        return self.total / self.count if self.count else 0.0


_Series = tuple[str, tuple[tuple[str, str], ...]]

#: 시리즈 하나의 라벨 묶음 — 정렬돼 있어 순서가 두 번째 시리즈를 만들지 못한다.
SeriesLabels = tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class MetricsSnapshot:
    """한 순간의 모든 시리즈 — 익스포터가 읽는 형태."""

    counters: tuple[tuple[str, SeriesLabels, float], ...]
    gauges: tuple[tuple[str, SeriesLabels, float], ...]
    histograms: tuple[tuple[str, SeriesLabels, HistogramSummary], ...]
    dropped_series: int
    rejected_samples: int


def _series_key(name: str, labels: Mapping[str, str] | None) -> _Series:
    """Label order must not create a second series, so the key is sorted."""
    if not labels:
        return (str(name), ())
    return (str(name), tuple(sorted((str(k), str(v)) for k, v in labels.items())))


class InMemoryMetricSink:
    """A sink that keeps its numbers, for tests and for a future exporter to read.

    Bounded on purpose. A metrics store that grows with traffic is an outage waiting for
    the right label, so past ``max_series`` new label combinations are counted and
    discarded rather than allocated.
    """

    def __init__(self, *, max_series: int = DEFAULT_MAX_SERIES) -> None:
        if max_series < 1:
            raise ValueError("max_series must be at least 1")
        self._max_series = max_series
        self._lock = threading.Lock()
        self._counters: dict[_Series, float] = {}
        self._gauges: dict[_Series, float] = {}
        self._histograms: dict[_Series, list[float]] = {}
        self._dropped_series = 0
        self._rejected_samples = 0

    # -- reading ------------------------------------------------------------ #

    @property
    def series_count(self) -> int:
        with self._lock:
            return len(self._counters) + len(self._gauges) + len(self._histograms)

    @property
    def dropped_series(self) -> int:
        """Label combinations refused because the cardinality cap was reached."""
        with self._lock:
            return self._dropped_series

    @property
    def rejected_samples(self) -> int:
        """Samples refused as nonsense — negative counter steps, NaN, infinity."""
        with self._lock:
            return self._rejected_samples

    def snapshot(self) -> MetricsSnapshot:
        """모든 시리즈의 일관된 사본 — 익스포터가 읽는 문.

        잠금 아래에서 통째로 복사한다. 시리즈별로 따로 읽으면 카운터와 분포가 서로
        다른 순간을 말하게 되고, 그 불일치는 그래프에서 원인 불명의 튐으로 나타난다.
        """
        with self._lock:
            return MetricsSnapshot(
                counters=tuple(
                    (name, labels, value)
                    for (name, labels), value in sorted(self._counters.items())
                ),
                gauges=tuple(
                    (name, labels, value)
                    for (name, labels), value in sorted(self._gauges.items())
                ),
                histograms=tuple(
                    (
                        name,
                        labels,
                        HistogramSummary(
                            count=len(samples),
                            total=math.fsum(samples),
                            minimum=min(samples),
                            maximum=max(samples),
                        ),
                    )
                    for (name, labels), samples in sorted(self._histograms.items())
                    if samples
                ),
                dropped_series=self._dropped_series,
                rejected_samples=self._rejected_samples,
            )

    def counter_value(self, name: str, **labels: str) -> float:
        """A counter that was never incremented reads as ``0``, which is true of it."""
        with self._lock:
            return self._counters.get(_series_key(name, labels), 0.0)

    def gauge_value(self, name: str, **labels: str) -> float | None:
        """``None`` where a gauge was never set — which is not the same as zero."""
        with self._lock:
            return self._gauges.get(_series_key(name, labels))

    def histogram_summary(self, name: str, **labels: str) -> HistogramSummary | None:
        with self._lock:
            samples = self._histograms.get(_series_key(name, labels))
            if not samples:
                return None
            return HistogramSummary(
                count=len(samples),
                total=math.fsum(samples),
                minimum=min(samples),
                maximum=max(samples),
            )

    # -- writing ------------------------------------------------------------ #

    def increment(
        self, name: str, value: float = 1.0, labels: Mapping[str, str] | None = None
    ) -> None:
        key = _series_key(name, labels)
        with self._lock:
            # A counter must be monotonic. A negative step is a caller bug, and applying
            # it would make every rate() computed downstream wrong in a way nobody would
            # trace back to here.
            if not math.isfinite(value) or value < 0:
                self._rejected_samples += 1
                return
            if key not in self._counters and self._at_capacity():
                self._dropped_series += 1
                return
            self._counters[key] = self._counters.get(key, 0.0) + value

    def gauge(self, name: str, value: float, labels: Mapping[str, str] | None = None) -> None:
        key = _series_key(name, labels)
        with self._lock:
            if not math.isfinite(value):
                self._rejected_samples += 1
                return
            if key not in self._gauges and self._at_capacity():
                self._dropped_series += 1
                return
            self._gauges[key] = value

    def observe(self, name: str, value: float, labels: Mapping[str, str] | None = None) -> None:
        key = _series_key(name, labels)
        with self._lock:
            if not math.isfinite(value):
                self._rejected_samples += 1
                return
            if key not in self._histograms and self._at_capacity():
                self._dropped_series += 1
                return
            self._histograms.setdefault(key, []).append(value)

    def _at_capacity(self) -> bool:
        return (
            len(self._counters) + len(self._gauges) + len(self._histograms) >= self._max_series
        )


class SafeMetricSink:
    """Wraps a sink so that a failing metrics backend stays a metrics problem.

    Every failure is counted, because silently dropping them would make a dead exporter
    indistinguishable from a quiet system. Only the first is logged: a backend that is
    down is down for every request, and a log line per request moves the outage from the
    metrics pipeline into the logging one.
    """

    def __init__(self, delegate: MetricSink) -> None:
        self._delegate = delegate
        self._lock = threading.Lock()
        self._failures = 0
        self._reported_failures = 0

    @property
    def delegate(self) -> MetricSink:
        return self._delegate

    @property
    def failures(self) -> int:
        with self._lock:
            return self._failures

    @property
    def reported_failures(self) -> int:
        with self._lock:
            return self._reported_failures

    def increment(
        self, name: str, value: float = 1.0, labels: Mapping[str, str] | None = None
    ) -> None:
        try:
            self._delegate.increment(name, value, labels)
        except Exception as exc:  # the whole point is to catch everything
            self._note_failure(exc)

    def gauge(self, name: str, value: float, labels: Mapping[str, str] | None = None) -> None:
        try:
            self._delegate.gauge(name, value, labels)
        except Exception as exc:  # the whole point is to catch everything
            self._note_failure(exc)

    def observe(self, name: str, value: float, labels: Mapping[str, str] | None = None) -> None:
        try:
            self._delegate.observe(name, value, labels)
        except Exception as exc:  # the whole point is to catch everything
            self._note_failure(exc)

    def _note_failure(self, exc: BaseException) -> None:
        with self._lock:
            self._failures += 1
            first = self._reported_failures == 0
            if first:
                self._reported_failures = 1
        if not first:
            return
        try:
            from veo.observability.logging import get_logger

            get_logger("veo.observability.metrics").warning(
                "metrics.sink.failed", outcome=type(exc).__name__
            )
        except Exception:  # a broken logger must not break the request
            return


_default_sink: MetricSink = SafeMetricSink(NullMetricSink())
_default_sink_lock = threading.Lock()


def get_metric_sink() -> MetricSink:
    """The process-wide sink. Always safe to call, whatever is installed behind it."""
    with _default_sink_lock:
        return _default_sink


def set_metric_sink(sink: MetricSink) -> None:
    """Install the process-wide sink, wrapped so it cannot raise into a request."""
    global _default_sink  # one process-wide sink, set at startup
    wrapped = sink if isinstance(sink, SafeMetricSink) else SafeMetricSink(sink)
    with _default_sink_lock:
        _default_sink = wrapped


# --------------------------------------------------------------------------- #
# Recorders — so no call site has to remember a metric name or a label set
# --------------------------------------------------------------------------- #


def record_http_request(
    sink: MetricSink,
    *,
    route: str,
    method: str,
    status_code: int,
    duration_ms: float,
    organization_hash: str | None = None,
) -> None:
    """One finished request.

    ``route`` must be the path *template*. A resolved path carries customer identifiers,
    which would both explode cardinality and put those identifiers in a metrics store
    that has none of the database's access controls.
    """
    labels = {"route": route, "method": method}
    classed = {**labels, "status_class": status_class(status_code)}

    sink.observe(MetricName.HTTP_REQUEST_DURATION_MS, duration_ms, labels)
    sink.increment(MetricName.HTTP_REQUESTS_TOTAL, 1.0, classed)
    if status_code >= 500:
        sink.increment(MetricName.HTTP_ERRORS_TOTAL, 1.0, classed)
    if organization_hash is not None:
        # Hashed, so "which tenant is hammering us" is answerable without the metrics
        # store learning who the tenants are.
        sink.increment(
            MetricName.HTTP_REQUESTS_BY_TENANT_TOTAL,
            1.0,
            {"organization_hash": organization_hash},
        )


def record_queue_state(
    sink: MetricSink,
    *,
    queue: str,
    depth: int,
    wait_ms: float | None = None,
    retries: int = 0,
    dead_lettered: int = 0,
) -> None:
    """Whether the queue is draining, and what it is losing on the way."""
    labels = {"queue": queue}
    sink.gauge(MetricName.QUEUE_DEPTH, float(depth), labels)
    if wait_ms is not None:
        sink.observe(MetricName.QUEUE_WAIT_MS, wait_ms, labels)
    if retries:
        sink.increment(MetricName.JOB_RETRIES_TOTAL, float(retries), labels)
    if dead_lettered:
        sink.increment(MetricName.JOB_DEAD_LETTERED_TOTAL, float(dead_lettered), labels)


def record_crawl_response(sink: MetricSink, *, status_code: int, bytes_read: int) -> None:
    """One fetched page. The status distribution is what says "we are being blocked"."""
    sink.increment(
        MetricName.CRAWL_PAGES_TOTAL, 1.0, {"status_class": status_class(status_code)}
    )
    sink.increment(MetricName.CRAWL_BYTES_TOTAL, float(bytes_read))


def record_provider_call(
    sink: MetricSink,
    *,
    provider: str,
    outcome: str,
    duration_ms: float,
    cache_hit: bool = False,
    circuit_state: CircuitState | None = None,
) -> None:
    """One call to an external provider, successful or not.

    ``RATE_LIMITED`` and ``SERVER_ERROR`` get their own counters as well as an ``outcome``
    label, because the two demand different responses — back off versus escalate — and an
    alert should not have to parse a label to tell them apart.
    """
    labels = {"provider": provider}
    sink.observe(MetricName.PROVIDER_CALL_DURATION_MS, duration_ms, labels)
    sink.increment(MetricName.PROVIDER_CALLS_TOTAL, 1.0, {**labels, "outcome": outcome})
    if outcome == "RATE_LIMITED":
        sink.increment(MetricName.PROVIDER_RATE_LIMITED_TOTAL, 1.0, labels)
    if outcome == "SERVER_ERROR":
        sink.increment(MetricName.PROVIDER_SERVER_ERRORS_TOTAL, 1.0, labels)
    if cache_hit:
        sink.increment(MetricName.PROVIDER_CACHE_HITS_TOTAL, 1.0, labels)
    if circuit_state is not None:
        sink.gauge(
            MetricName.PROVIDER_CIRCUIT_STATE,
            float(CIRCUIT_STATE_VALUES[circuit_state]),
            labels,
        )


def record_llm_usage(
    sink: MetricSink,
    *,
    engine: str,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> None:
    """Tokens, split by direction because they are priced differently.

    ``None`` means the provider reported nothing, which is not the same as zero and so
    increments nothing at all.
    """
    labels = {"engine": engine, "model": model}
    if input_tokens is not None:
        sink.increment(
            MetricName.LLM_TOKENS_TOTAL, float(input_tokens), {**labels, "direction": "input"}
        )
    if output_tokens is not None:
        sink.increment(
            MetricName.LLM_TOKENS_TOTAL, float(output_tokens), {**labels, "direction": "output"}
        )


def record_cost(
    sink: MetricSink,
    *,
    engine: str,
    cost_usd: float | None,
    basis: CostBasis,
) -> None:
    """What a call cost, or the fact that nobody can say.

    An unpriced call adds ``0`` to no total. It increments its own counter, labelled with
    the reason, so a dashboard shows "$40 spent, 120 calls unpriced" rather than "$40
    spent" — the second sentence is the one that lets a month's overspend go unnoticed.
    """
    if cost_usd is None or not math.isfinite(cost_usd) or cost_usd < 0:
        sink.increment(
            MetricName.LLM_COST_UNMEASURABLE_TOTAL,
            1.0,
            {"engine": engine, "basis": str(basis)},
        )
        return
    sink.increment(MetricName.LLM_COST_USD_TOTAL, cost_usd, {"engine": engine})


def record_report_generated(sink: MetricSink, *, report_kind: str, duration_ms: float) -> None:
    """How long a report took to build, per kind."""
    sink.observe(MetricName.REPORT_GENERATION_MS, duration_ms, {"report_kind": report_kind})
