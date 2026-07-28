"""Following one scan from the API edge, through the queue, out to a provider.

A VEO scan is not one process. A request arrives, a job is enqueued, a worker picks it
up, and that worker makes a dozen provider calls. When one of those calls is the reason a
customer's report is late, the only useful question is "show me everything that happened
under that scan" — and answering it needs a correlation id that survives every one of
those hops.

The correlation id already exists at the HTTP edge (``veo.api.deps.get_request_id``).
This module carries it inward: a span inherits its parent's correlation id and trace id
through a :class:`~contextvars.ContextVar`, so a function four frames down can name the
scan it belongs to without any of the frames in between passing it along.

Deliberately not OpenTelemetry. The protocol here is three methods wide and the default
implementation does nothing, which is what an unfinished tracing story should cost. When
there is a collector to export to, an adapter implements :class:`Tracer` and no call site
changes. Pulling in the SDK now would mean a global tracer provider, a shutdown hook and
a batch exporter thread in every worker, in exchange for spans nobody is reading yet.

Span attributes go through the same scrubber as log fields. A span is log surface with a
different name: exported, retained, and read by the same people.
"""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from typing import Any, Protocol

from veo.credentials.redaction import redact_exception
from veo.observability.logging import scrub_fields, scrub_text

__all__ = [
    "InMemoryTracer",
    "NoOpTracer",
    "RecordedSpan",
    "Span",
    "SpanContext",
    "Tracer",
    "current_correlation_id",
    "current_span_context",
    "new_correlation_id",
    "new_span_id",
    "new_trace_id",
]


def new_correlation_id() -> str:
    """A fresh correlation id, in the shape ``veo.api.deps`` accepts from a header."""
    return uuid.uuid4().hex


def new_trace_id() -> str:
    return uuid.uuid4().hex


def new_span_id() -> str:
    return uuid.uuid4().hex[:16]


@dataclass(frozen=True, slots=True)
class SpanContext:
    """Where in the story of one scan a piece of work sits."""

    name: str
    correlation_id: str
    trace_id: str
    span_id: str
    parent_span_id: str | None = None


_current_span: contextvars.ContextVar[SpanContext | None] = contextvars.ContextVar(
    "veo_current_span", default=None
)


def current_span_context() -> SpanContext | None:
    """The span this code is running inside, if any."""
    return _current_span.get()


def current_correlation_id() -> str | None:
    """The correlation id of the work in progress, for a log line or an outbound header."""
    context = _current_span.get()
    return context.correlation_id if context is not None else None


class Span(Protocol):
    """One unit of work inside a trace."""

    @property
    def context(self) -> SpanContext:
        """Its place in the trace. Stable for the life of the span."""

    def set_attribute(self, key: str, value: Any) -> None:
        """Attach one allowlisted field. Refused keys are dropped, not scrubbed."""

    def record_error(self, exc: BaseException) -> None:
        """Note that this span failed, without importing the exception's text verbatim."""


@dataclass(slots=True)
class RecordedSpan:
    """A span that keeps what it was told. Also the :class:`Span` implementation."""

    span_context: SpanContext
    recording: bool = True
    attributes: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def context(self) -> SpanContext:
        return self.span_context

    @property
    def name(self) -> str:
        return self.span_context.name

    def set_attribute(self, key: str, value: Any) -> None:
        if not self.recording:
            return
        kept, _ = scrub_fields({key: value})
        self.attributes.update(kept)

    def record_error(self, exc: BaseException) -> None:
        if not self.recording:
            return
        # ``redact_exception`` keeps the type names and the cause chain and scrubs every
        # message; ``scrub_text`` then removes the personal-data shapes it does not look
        # for. A provider that echoes the credential back inside its error body is the
        # normal case, not the exotic one.
        self.error = scrub_text(redact_exception(exc))


class Tracer(Protocol):
    """Somewhere to send spans. Implement this to export; do not change call sites."""

    def start_span(
        self,
        name: str,
        *,
        correlation_id: str | None = None,
        attributes: Mapping[str, Any] | None = None,
    ) -> AbstractContextManager[Span]:
        """Open a span, make it the ambient one, and close it on exit."""


class _BaseTracer:
    """The context propagation every tracer needs, and none should reimplement."""

    def __init__(self) -> None:
        self._failures = 0

    @property
    def failures(self) -> int:
        """Spans this tracer could not record. Never raised, always counted."""
        return self._failures

    @contextmanager
    def start_span(
        self,
        name: str,
        *,
        correlation_id: str | None = None,
        attributes: Mapping[str, Any] | None = None,
    ) -> Iterator[RecordedSpan]:
        parent = _current_span.get()
        context = _build_context(name, parent=parent, correlation_id=correlation_id)
        span = RecordedSpan(span_context=context, recording=self._recording)

        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        token = _current_span.set(context)
        try:
            yield span
        except BaseException as exc:
            span.record_error(exc)
            raise
        finally:
            _current_span.reset(token)
            self._finish(span)

    @property
    def _recording(self) -> bool:
        return True

    def _finish(self, span: RecordedSpan) -> None:
        """Hand the finished span to the backend, absorbing whatever it does about it."""
        try:
            self._record(span)
        except Exception:  # a tracing backend may not break the caller
            self._failures += 1

    def _record(self, span: RecordedSpan) -> None:
        """Where a subclass keeps or exports the span. Called once, never re-entered.

        Abstract on purpose: a base class that silently discarded spans would make a
        misconfigured tracer indistinguishable from a working one.
        """
        raise NotImplementedError(f"{type(self).__name__} must implement _record")


def _build_context(
    name: str, *, parent: SpanContext | None, correlation_id: str | None
) -> SpanContext:
    """Inherit from the parent unless the caller is starting a different story.

    An explicit correlation id that disagrees with the parent's begins a new trace. That
    happens when a worker adopts the id off a queued message while some outer span is
    still open; grafting it onto the enclosing trace would merge two customers' work into
    one waterfall.
    """
    if parent is None:
        return SpanContext(
            name=name,
            correlation_id=correlation_id or new_correlation_id(),
            trace_id=new_trace_id(),
            span_id=new_span_id(),
            parent_span_id=None,
        )
    if correlation_id is not None and correlation_id != parent.correlation_id:
        return SpanContext(
            name=name,
            correlation_id=correlation_id,
            trace_id=new_trace_id(),
            span_id=new_span_id(),
            parent_span_id=None,
        )
    return SpanContext(
        name=name,
        correlation_id=parent.correlation_id,
        trace_id=parent.trace_id,
        span_id=new_span_id(),
        parent_span_id=parent.span_id,
    )


class NoOpTracer(_BaseTracer):
    """The default. Propagates correlation, stores nothing, exports nothing.

    Still worth having installed everywhere: :func:`current_correlation_id` works under
    it, so log lines correlate correctly in a deployment with no tracing backend at all.
    """

    @property
    def _recording(self) -> bool:
        return False

    def _record(self, span: RecordedSpan) -> None:
        return None


class InMemoryTracer(_BaseTracer):
    """Keeps finished spans, innermost first. For tests, and for a local waterfall."""

    def __init__(self, *, max_spans: int = 10_000) -> None:
        super().__init__()
        if max_spans < 1:
            raise ValueError("max_spans must be at least 1")
        self._max_spans = max_spans
        self._spans: list[RecordedSpan] = []

    @property
    def spans(self) -> list[RecordedSpan]:
        return list(self._spans)

    def _record(self, span: RecordedSpan) -> None:
        if len(self._spans) >= self._max_spans:
            # Drop the oldest rather than grow without bound. A tracer that outlives its
            # usefulness must not be the reason a worker is killed.
            del self._spans[0]
        self._spans.append(span)
