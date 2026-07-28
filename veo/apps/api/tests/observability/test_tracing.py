"""One scan, followed from the API edge into the worker and out to a provider.

The correlation id already exists at the HTTP edge. What these tests pin down is that it
keeps existing three frames deep, in a background task, and after the span that created
it has ended — because a trace that loses its thread at the first nesting is a trace an
operator cannot use during an incident.
"""

from __future__ import annotations

import pytest

from veo.observability.logging import REDACTED
from veo.observability.tracing import (
    InMemoryTracer,
    NoOpTracer,
    current_correlation_id,
    current_span_context,
    new_correlation_id,
)

CORRELATION = "0123456789abcdef"


# --------------------------------------------------------------------------- #
# Correlation
# --------------------------------------------------------------------------- #


def test_a_correlation_id_flows_through_nested_spans() -> None:
    tracer = InMemoryTracer()

    with tracer.start_span("api.scan.request", correlation_id=CORRELATION):  # noqa: SIM117
        with tracer.start_span("worker.scan.run"):
            with tracer.start_span("provider.naver.call"):
                pass

    names = [span.name for span in tracer.spans]
    assert names == ["provider.naver.call", "worker.scan.run", "api.scan.request"]
    assert {span.context.correlation_id for span in tracer.spans} == {CORRELATION}


def test_nested_spans_share_one_trace_and_chain_their_parents() -> None:
    tracer = InMemoryTracer()

    with tracer.start_span("api.scan.request", correlation_id=CORRELATION) as root:  # noqa: SIM117
        with tracer.start_span("worker.scan.run") as middle:
            with tracer.start_span("provider.naver.call") as leaf:
                leaf_id = leaf.context.span_id
                middle_id = middle.context.span_id
                root_id = root.context.span_id
                trace_ids = {
                    root.context.trace_id,
                    middle.context.trace_id,
                    leaf.context.trace_id,
                }

    assert len(trace_ids) == 1
    assert root.context.parent_span_id is None
    assert middle.context.parent_span_id == root_id
    assert leaf.context.parent_span_id == middle_id
    assert len({root_id, middle_id, leaf_id}) == 3


def test_the_ambient_context_is_readable_inside_a_span_and_gone_after_it() -> None:
    tracer = InMemoryTracer()
    assert current_correlation_id() is None

    with tracer.start_span("api.scan.request", correlation_id=CORRELATION):
        assert current_correlation_id() == CORRELATION
        context = current_span_context()
        assert context is not None
        assert context.name == "api.scan.request"

    assert current_correlation_id() is None
    assert current_span_context() is None


def test_the_ambient_context_is_restored_after_a_nested_span_ends() -> None:
    tracer = InMemoryTracer()

    with tracer.start_span("outer", correlation_id=CORRELATION) as outer:
        with tracer.start_span("inner"):
            assert current_span_context() is not None
            assert current_span_context().span_id != outer.context.span_id  # type: ignore[union-attr]
        restored = current_span_context()
        assert restored is not None
        assert restored.span_id == outer.context.span_id


def test_a_span_started_without_a_correlation_id_invents_one_and_keeps_it() -> None:
    tracer = InMemoryTracer()

    with tracer.start_span("worker.scan.run"):
        generated = current_correlation_id()
        assert generated is not None
        with tracer.start_span("provider.naver.call"):
            assert current_correlation_id() == generated


def test_a_correlation_id_can_be_adopted_from_the_edge_header_shape() -> None:
    generated = new_correlation_id()
    assert len(generated) == 32
    assert generated.isalnum()
    assert generated != new_correlation_id()


def test_an_exception_ends_the_span_and_restores_the_parent_context() -> None:
    tracer = InMemoryTracer()

    with tracer.start_span("outer", correlation_id=CORRELATION):
        with pytest.raises(RuntimeError):  # noqa: SIM117 - the nesting is the subject
            with tracer.start_span("inner"):
                raise RuntimeError("provider refused")
        assert current_correlation_id() == CORRELATION

    inner = next(span for span in tracer.spans if span.name == "inner")
    assert inner.error is not None
    assert "RuntimeError" in inner.error


# --------------------------------------------------------------------------- #
# Attributes are log surface too
# --------------------------------------------------------------------------- #


def test_span_attributes_are_scrubbed_like_log_fields() -> None:
    tracer = InMemoryTracer()

    with tracer.start_span("provider.naver.call", correlation_id=CORRELATION) as span:
        span.set_attribute("provider", "NAVER")
        span.set_attribute("client_ip_hash", "203.0.113.42")
        span.set_attribute("password", "correct-horse-battery-staple")

    recorded = tracer.spans[0]
    assert recorded.attributes["provider"] == "NAVER"
    assert recorded.attributes["client_ip_hash"] == REDACTED
    assert "password" not in recorded.attributes


def test_a_recorded_error_is_scrubbed() -> None:
    tracer = InMemoryTracer()
    token = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ2ZW5vbSJ9.Zm9vYmFyYmF6cXV4"

    with tracer.start_span("provider.naver.call", correlation_id=CORRELATION) as span:
        span.record_error(RuntimeError(f"refused Authorization: {token}"))

    assert "Zm9vYmFyYmF6cXV4" not in tracer.spans[0].error  # type: ignore[operator]


# --------------------------------------------------------------------------- #
# The default costs nothing and breaks nothing
# --------------------------------------------------------------------------- #


def test_the_no_op_tracer_still_carries_the_correlation_id() -> None:
    tracer = NoOpTracer()

    with tracer.start_span("api.scan.request", correlation_id=CORRELATION) as span:
        span.set_attribute("provider", "NAVER")
        span.record_error(RuntimeError("boom"))
        assert span.context.correlation_id == CORRELATION
        assert current_correlation_id() == CORRELATION

    assert current_correlation_id() is None


def test_a_tracer_that_fails_to_record_does_not_raise_into_the_caller() -> None:
    class BrokenTracer(InMemoryTracer):
        def _record(self, span: object) -> None:
            raise RuntimeError("tracing backend unreachable")

    tracer = BrokenTracer()
    with tracer.start_span("api.scan.request", correlation_id=CORRELATION):
        pass

    assert tracer.failures == 1
