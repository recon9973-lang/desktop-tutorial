"""How VEO watches itself, under four rules.

1. **A log line is a place customer data leaks.** Passwords, tokens, provider
   credentials, raw email addresses, raw IPs, raw AI answers and customer contact details
   never reach a log — not at DEBUG, not inside a traceback. What must be correlated is
   hashed. See :mod:`veo.observability.logging`.
2. **Unmeasurable cost is not zero cost.** A run whose price table was stale has an
   unknown cost, reported as its own state rather than folded into a total. See
   :mod:`veo.observability.cost`.
3. **A metric nobody can act on is noise.** Every series in
   :mod:`veo.observability.metrics` answers a question an operator asks at 3am.
4. **Instrumentation must not change behaviour.** A failing metrics backend, a failing
   tracer and an unreachable health probe all degrade quietly; none of them can turn a
   working request into an error.

Layout:

* ``logging`` — structlog configuration and the redaction processor every event passes
  through before it is rendered.
* ``metrics`` — the :class:`~veo.observability.metrics.MetricSink` protocol, an in-memory
  sink, and recorders that name the series so no call site has to.
* ``tracing`` — span propagation for following one scan across API and worker, with a
  no-op default and no OpenTelemetry.
* ``cost`` — per-organization, per-month budget accumulation that keeps "unpriced" apart
  from "free".
* ``health`` — a readiness view written on the assumption that its output is public.

Nothing here is wired into the application; ``INTEGRATION_REQUEST.md`` records what the
owners of ``veo/api/app.py`` and the worker need to do.
"""

from veo.observability.cost import (
    BudgetReport,
    BudgetStatus,
    BudgetTracker,
    CostMeasurement,
    UnmeasurableReason,
    month_key,
)
from veo.observability.health import (
    ComponentHealth,
    ComponentStatus,
    PriceTableView,
    ReadinessProbe,
    ReadinessReport,
)
from veo.observability.logging import (
    ALLOWED_EVENT_KEYS,
    REDACTED,
    bind_log_context,
    clear_log_context,
    configure_logging,
    get_logger,
    hash_identifier,
    log_request_completed,
)
from veo.observability.metrics import (
    InMemoryMetricSink,
    MetricName,
    MetricSink,
    MetricsSnapshot,
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
from veo.observability.tracing import (
    InMemoryTracer,
    NoOpTracer,
    Span,
    SpanContext,
    Tracer,
    current_correlation_id,
    current_span_context,
    new_correlation_id,
)

__all__ = [
    "ALLOWED_EVENT_KEYS",
    "REDACTED",
    "BudgetReport",
    "BudgetStatus",
    "BudgetTracker",
    "ComponentHealth",
    "ComponentStatus",
    "CostMeasurement",
    "InMemoryMetricSink",
    "InMemoryTracer",
    "MetricName",
    "MetricSink",
    "MetricsSnapshot",
    "NoOpTracer",
    "NullMetricSink",
    "PriceTableView",
    "ReadinessProbe",
    "ReadinessReport",
    "SafeMetricSink",
    "Span",
    "SpanContext",
    "Tracer",
    "UnmeasurableReason",
    "bind_log_context",
    "clear_log_context",
    "configure_logging",
    "current_correlation_id",
    "current_span_context",
    "get_logger",
    "get_metric_sink",
    "hash_identifier",
    "log_request_completed",
    "month_key",
    "new_correlation_id",
    "record_cost",
    "record_crawl_response",
    "record_http_request",
    "record_llm_usage",
    "record_provider_call",
    "record_queue_state",
    "record_report_generated",
    "set_metric_sink",
]
