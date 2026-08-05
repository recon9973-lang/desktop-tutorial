"""Response budgets for outbound fetches.

A validated URL only guarantees *where* we connect. It says nothing about what comes
back, and a hostile — or merely broken — server can still take a worker down with:

* a body that never ends, or ends at 40 GB;
* a 12 KB gzip stream that decompresses to 10 GB (a decompression bomb);
* a socket that trickles one byte a minute until the pool is exhausted;
* ``Content-Type: application/octet-stream`` pointing at 2 GB of video we will
  never parse.

:class:`FetchLimits` declares the budget; :class:`ResponseBudget` enforces it. The
enforcement is *incremental* on purpose: every limit is checked as bytes arrive, so
nothing over budget is ever buffered. Checking ``len(response.content)`` after the fact
means the damage is already done.

The clock is injected so the deadline is testable without sleeping.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import ClassVar

__all__ = [
    "ContentTypeNotAllowedError",
    "DecompressionLimitError",
    "FetchLimitError",
    "FetchLimits",
    "FetchTimeoutError",
    "ResponseBudget",
    "ResponseTooLargeError",
    "enforce_async_stream",
    "enforce_stream",
]

DEFAULT_ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "text/html",
        "application/xhtml+xml",
        "text/plain",
        "text/xml",
        "application/xml",
        "application/json",
        "application/ld+json",
        "application/rss+xml",
        "application/atom+xml",
    }
)


class FetchLimitError(Exception):
    """Base class for every budget violation.

    ``message_ko`` is safe to show a customer; it never quotes a response header or a
    byte count that would tell an attacker exactly where the cut-off sits.
    """

    reason: ClassVar[str] = "FETCH_LIMIT_EXCEEDED"
    message_ko: ClassVar[str] = "응답을 가져오는 중 허용 한도를 초과했습니다."

    def __init__(self, detail: str = "") -> None:
        self.detail = detail
        super().__init__(f"{self.reason}: {detail}" if detail else self.reason)


class ResponseTooLargeError(FetchLimitError):
    reason: ClassVar[str] = "RESPONSE_TOO_LARGE"
    message_ko: ClassVar[str] = "응답 크기가 허용 한도를 초과하여 분석을 중단했습니다."


class DecompressionLimitError(FetchLimitError):
    reason: ClassVar[str] = "DECOMPRESSION_LIMIT_EXCEEDED"
    message_ko: ClassVar[str] = "압축 해제 크기가 허용 한도를 초과하여 분석을 중단했습니다."


class FetchTimeoutError(FetchLimitError):
    reason: ClassVar[str] = "FETCH_TIMEOUT"
    message_ko: ClassVar[str] = "응답이 제한 시간을 초과하여 분석을 중단했습니다."


class ContentTypeNotAllowedError(FetchLimitError):
    reason: ClassVar[str] = "CONTENT_TYPE_NOT_ALLOWED"
    message_ko: ClassVar[str] = "분석할 수 없는 형식의 응답입니다."


@dataclass(frozen=True, slots=True)
class FetchLimits:
    """The budget for a single outbound fetch."""

    max_response_bytes: int = 2 * 1024 * 1024
    """Bytes on the wire, compressed. Enforced continuously while streaming.

    작업의뢰서 §5.2: **HTML 최대 2MB**. 예전 값은 8MB 였다 — 우리가 감당할 수 있는
    크기였지 상대 서버가 우리에게 내주기로 한 크기가 아니었다. 진단에 필요한 것은
    문서의 머리와 본문이지, 남의 대역폭을 8MB 씩 쓸 이유가 없다.

    실측(2026-08-06): 거래처 4곳에서 받은 문서는 51KB·64KB·240KB·298KB 로 전부 2MB
    아래다. 이 문턱이 정상 진단을 자르지 않는다.
    """

    max_total_seconds: float = 30.0
    """Wall clock for the whole response, not per-read — slow-drip defence.

    작업의뢰서 §5.2 의 "전체 30초" 와 같다.
    """

    connect_seconds: float = 10.0
    """연결이 열릴 때까지. 의뢰서 §5.2 는 연결 10초 / 전체 30초로 나눠 정한다.

    예전에는 전체 30초만 있었다. 죽은 호스트에 30초를 매달려 있으면 그만큼 진단이
    느려지고, 배치에서는 한 도메인이 창을 먹는다.
    """

    max_decompressed_bytes: int = 32 * 1024 * 1024
    """Absolute ceiling after decompression."""

    max_decompression_ratio: float = 25.0
    """Ceiling on decompressed ÷ wire. Real HTML tops out around 8:1; a bomb is 1000:1."""

    decompression_ratio_floor_bytes: int = 64 * 1024
    """The ratio is only meaningful once enough has arrived — a gzip header alone looks
    like a 20:1 expansion. Below this many decompressed bytes only the absolute cap
    applies."""

    allowed_content_types: frozenset[str] = DEFAULT_ALLOWED_CONTENT_TYPES
    allow_missing_content_type: bool = False
    """Default deny: a response that will not say what it is does not get parsed."""

    def __post_init__(self) -> None:
        for name in (
            "max_response_bytes",
            "max_decompressed_bytes",
            "decompression_ratio_floor_bytes",
            "max_total_seconds",
        ):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.max_decompression_ratio < 1:
            raise ValueError("max_decompression_ratio must be at least 1")
        if not self.allowed_content_types:
            raise ValueError("allowed_content_types must not be empty")


class ResponseBudget:
    """Tracks one response against a :class:`FetchLimits` and raises the moment it busts.

    Usage mirrors the shape of a streaming HTTP client::

        budget = ResponseBudget(limits)
        budget.check_content_type(response.headers.get("content-type"))
        budget.check_declared_length(response.headers.get("content-length"))
        async for chunk in enforce_async_stream(response.aiter_raw(), budget):
            budget.add_decompressed_bytes(len(decoder.decompress(chunk)))
    """

    __slots__ = ("_clock", "_decompressed", "_limits", "_started", "_wire")

    def __init__(
        self,
        limits: FetchLimits,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limits = limits
        self._clock = clock
        self._started = clock()
        self._wire = 0
        self._decompressed = 0

    @property
    def limits(self) -> FetchLimits:
        return self._limits

    @property
    def wire_bytes(self) -> int:
        return self._wire

    @property
    def decompressed_bytes(self) -> int:
        return self._decompressed

    @property
    def remaining_bytes(self) -> int:
        return max(0, self._limits.max_response_bytes - self._wire)

    @property
    def elapsed_seconds(self) -> float:
        return self._clock() - self._started

    def check_content_type(self, header: str | None) -> None:
        """Reject a response whose media type we would not parse anyway."""
        media_type = (header or "").split(";", 1)[0].strip().lower()
        if not media_type:
            if self._limits.allow_missing_content_type:
                return
            raise ContentTypeNotAllowedError("missing content-type")
        if media_type not in self._limits.allowed_content_types:
            # The header is attacker-controlled, so it goes in `detail` (logs) only.
            raise ContentTypeNotAllowedError(f"content-type {media_type!r}")

    def check_declared_length(self, header: str | int | None) -> None:
        """Refuse an over-budget body before reading a single byte of it.

        A missing or nonsensical ``Content-Length`` is ignored rather than trusted —
        it is a hint, and :meth:`add_wire_bytes` is the real limit.
        """
        if header is None:
            return
        try:
            declared = int(header)
        except (TypeError, ValueError):
            return
        if declared < 0:
            return
        if declared > self._limits.max_response_bytes:
            raise ResponseTooLargeError("declared content-length over budget")

    def add_wire_bytes(self, count: int) -> None:
        self._wire += count
        if self._wire > self._limits.max_response_bytes:
            raise ResponseTooLargeError("response body over budget")

    def add_decompressed_bytes(self, count: int) -> None:
        self._decompressed += count
        if self._decompressed > self._limits.max_decompressed_bytes:
            raise DecompressionLimitError("decompressed body over budget")
        if self._decompressed >= self._limits.decompression_ratio_floor_bytes:
            ratio = self._decompressed / max(self._wire, 1)
            if ratio > self._limits.max_decompression_ratio:
                raise DecompressionLimitError("decompression ratio over budget")

    def check_deadline(self) -> None:
        if self.elapsed_seconds > self._limits.max_total_seconds:
            raise FetchTimeoutError("response exceeded the total time budget")


def enforce_stream(chunks: Iterable[bytes], budget: ResponseBudget) -> Iterator[bytes]:
    """Yield ``chunks`` while holding them to ``budget``.

    The budget is charged *before* each chunk is handed on, so the chunk that busts the
    limit is never delivered and the source is never drained past the cut-off.
    """
    for chunk in chunks:
        budget.check_deadline()
        budget.add_wire_bytes(len(chunk))
        yield chunk


async def enforce_async_stream(
    chunks: AsyncIterator[bytes], budget: ResponseBudget
) -> AsyncIterator[bytes]:
    """Async twin of :func:`enforce_stream`, for ``httpx.Response.aiter_raw()``."""
    async for chunk in chunks:
        budget.check_deadline()
        budget.add_wire_bytes(len(chunk))
        yield chunk
