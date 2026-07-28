"""Response-budget enforcement for :mod:`veo.common.security.limits`.

A URL guard that only checks the URL is half a guard: an allowed host can still return
a 40 GB body, a 1000:1 gzip bomb, or a stream that never ends. Every limit here must
bite *during* the stream, not after it has already been buffered.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator

import pytest

from veo.common.security.limits import (
    ContentTypeNotAllowedError,
    DecompressionLimitError,
    FetchLimitError,
    FetchLimits,
    FetchTimeoutError,
    ResponseBudget,
    ResponseTooLargeError,
    enforce_async_stream,
    enforce_stream,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


TINY = FetchLimits(
    max_response_bytes=100,
    max_total_seconds=5.0,
    max_decompressed_bytes=400,
    max_decompression_ratio=4.0,
    decompression_ratio_floor_bytes=50,
)


def test_defaults_are_conservative() -> None:
    limits = FetchLimits()
    assert 0 < limits.max_response_bytes <= 32 * 1024 * 1024
    assert 0 < limits.max_total_seconds <= 120
    assert limits.max_decompressed_bytes >= limits.max_response_bytes
    assert limits.max_decompression_ratio > 1
    assert "text/html" in limits.allowed_content_types


def test_limits_are_frozen() -> None:
    limits = FetchLimits()
    with pytest.raises((AttributeError, TypeError)):
        limits.max_response_bytes = 1 << 40  # type: ignore[misc]


@pytest.mark.parametrize("field", ["max_response_bytes", "max_decompressed_bytes"])
def test_non_positive_limits_are_rejected(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        FetchLimits(**{field: 0})


# ---------------------------------------------------------------------------
# content type
# ---------------------------------------------------------------------------

ALLOWED_TYPES = [
    "text/html",
    "text/html; charset=utf-8",
    "TEXT/HTML;charset=UTF-8",
    "  application/xhtml+xml  ",
    "application/json",
]

BLOCKED_TYPES = [
    "application/pdf",
    "application/octet-stream",
    "image/png",
    "video/mp4",
    "application/zip",
    "",
    "   ",
    ";charset=utf-8",
]


@pytest.mark.parametrize("header", ALLOWED_TYPES)
def test_allowed_content_types(header: str) -> None:
    ResponseBudget(FetchLimits()).check_content_type(header)


@pytest.mark.parametrize("header", BLOCKED_TYPES)
def test_blocked_content_types(header: str) -> None:
    with pytest.raises(ContentTypeNotAllowedError):
        ResponseBudget(FetchLimits()).check_content_type(header)


def test_missing_content_type_is_denied_by_default() -> None:
    with pytest.raises(ContentTypeNotAllowedError):
        ResponseBudget(FetchLimits()).check_content_type(None)


def test_missing_content_type_can_be_permitted() -> None:
    limits = FetchLimits(allow_missing_content_type=True)
    ResponseBudget(limits).check_content_type(None)


def test_content_type_error_does_not_echo_the_header() -> None:
    """Headers are attacker-controlled; they never reach a customer-facing message."""
    header = "application/x-<script>alert(1)</script>"
    with pytest.raises(ContentTypeNotAllowedError) as excinfo:
        ResponseBudget(FetchLimits()).check_content_type(header)
    assert "<script>" not in excinfo.value.message_ko


# ---------------------------------------------------------------------------
# declared length
# ---------------------------------------------------------------------------


def test_declared_length_over_budget_is_refused_before_reading() -> None:
    budget = ResponseBudget(TINY)
    with pytest.raises(ResponseTooLargeError):
        budget.check_declared_length("101")
    assert budget.wire_bytes == 0


def test_declared_length_within_budget_passes() -> None:
    ResponseBudget(TINY).check_declared_length("100")


@pytest.mark.parametrize("header", [None, "", "not-a-number", "-5"])
def test_unusable_declared_length_is_ignored(header: str | None) -> None:
    """A missing or junk Content-Length is normal; the streaming counter is the real guard."""
    ResponseBudget(TINY).check_declared_length(header)


# ---------------------------------------------------------------------------
# wire bytes, mid-stream
# ---------------------------------------------------------------------------


def test_wire_bytes_accumulate() -> None:
    budget = ResponseBudget(TINY)
    budget.add_wire_bytes(40)
    budget.add_wire_bytes(40)
    assert budget.wire_bytes == 80


def test_wire_bytes_over_budget_raise() -> None:
    budget = ResponseBudget(TINY)
    budget.add_wire_bytes(100)
    with pytest.raises(ResponseTooLargeError):
        budget.add_wire_bytes(1)


def test_stream_is_cut_off_mid_body_not_after_it() -> None:
    """The generator must not be drained before the limit is enforced."""
    produced = 0

    def source() -> Iterator[bytes]:
        nonlocal produced
        for _ in range(1000):
            produced += 1
            yield b"x" * 32

    budget = ResponseBudget(TINY)
    seen = 0
    with pytest.raises(ResponseTooLargeError):
        for chunk in enforce_stream(source(), budget):
            seen += len(chunk)

    assert seen <= TINY.max_response_bytes
    assert produced <= 5, "the whole 32 KB body was buffered before the limit fired"


def test_stream_under_budget_passes_through_unchanged() -> None:
    chunks = [b"abc", b"de", b"f"]
    budget = ResponseBudget(TINY)
    assert b"".join(enforce_stream(iter(chunks), budget)) == b"abcdef"
    assert budget.wire_bytes == 6


def test_async_stream_is_cut_off_mid_body() -> None:
    """Same guarantee on the async path the worker actually uses with httpx."""
    produced = 0

    async def source() -> AsyncIterator[bytes]:
        nonlocal produced
        for _ in range(1000):
            produced += 1
            yield b"x" * 32

    budget = ResponseBudget(TINY)
    delivered = 0

    async def drain() -> None:
        nonlocal delivered
        async for chunk in enforce_async_stream(source(), budget):
            delivered += len(chunk)

    with pytest.raises(ResponseTooLargeError):
        asyncio.run(drain())
    assert produced <= 5
    assert delivered <= TINY.max_response_bytes


# ---------------------------------------------------------------------------
# decompression / zip bombs
# ---------------------------------------------------------------------------


def test_absolute_decompressed_cap() -> None:
    budget = ResponseBudget(TINY)
    budget.add_wire_bytes(100)
    budget.add_decompressed_bytes(400)
    with pytest.raises(DecompressionLimitError):
        budget.add_decompressed_bytes(1)


def test_decompression_ratio_cap() -> None:
    """10 bytes on the wire must not be allowed to inflate into 300."""
    budget = ResponseBudget(TINY)
    budget.add_wire_bytes(10)
    with pytest.raises(DecompressionLimitError):
        budget.add_decompressed_bytes(300)


def test_ratio_is_not_applied_below_the_floor() -> None:
    """A 12-byte gzip header expanding to 40 bytes is normal, not an attack."""
    budget = ResponseBudget(TINY)
    budget.add_wire_bytes(2)
    budget.add_decompressed_bytes(40)
    assert budget.decompressed_bytes == 40


def test_ratio_within_limit_passes() -> None:
    budget = ResponseBudget(TINY)
    budget.add_wire_bytes(50)
    budget.add_decompressed_bytes(200)
    assert budget.decompressed_bytes == 200


# ---------------------------------------------------------------------------
# wall clock
# ---------------------------------------------------------------------------


def test_deadline_is_enforced() -> None:
    clock = FakeClock()
    budget = ResponseBudget(TINY, clock=clock)
    clock.advance(4.9)
    budget.check_deadline()
    clock.advance(0.2)
    with pytest.raises(FetchTimeoutError):
        budget.check_deadline()


def test_deadline_is_checked_while_streaming() -> None:
    clock = FakeClock()
    budget = ResponseBudget(TINY, clock=clock)

    def slow_source() -> Iterator[bytes]:
        for _ in range(100):
            clock.advance(1.0)
            yield b"ab"

    with pytest.raises(FetchTimeoutError):
        for _chunk in enforce_stream(slow_source(), budget):
            pass
    assert budget.wire_bytes < TINY.max_response_bytes


def test_remaining_bytes_and_elapsed_are_reported() -> None:
    clock = FakeClock()
    budget = ResponseBudget(TINY, clock=clock)
    budget.add_wire_bytes(30)
    clock.advance(2.0)
    assert budget.remaining_bytes == 70
    assert budget.elapsed_seconds == 2.0


# ---------------------------------------------------------------------------
# error surface
# ---------------------------------------------------------------------------

ERRORS = [
    ResponseTooLargeError,
    DecompressionLimitError,
    FetchTimeoutError,
    ContentTypeNotAllowedError,
]


@pytest.mark.parametrize("error_type", ERRORS)
def test_every_limit_error_is_a_fetch_limit_error(error_type: type[FetchLimitError]) -> None:
    error = error_type()
    assert isinstance(error, FetchLimitError)
    assert error.message_ko
    assert any("가" <= ch <= "힣" for ch in error.message_ko)
    assert error.reason
