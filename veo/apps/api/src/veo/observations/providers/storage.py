"""Where the raw AI answer lives, so the run row does not have to carry it.

An :class:`~veo.observations.runs.ObservationRun` may claim a mention only if the answer
that produced it was stored. That is the whole point of this module: the claim stays
checkable, while the text — long, sometimes naming a real clinic or a real patient
review, always reproducible verbatim — stays behind the evidence permission instead of
sitting in a row that every report query selects.

**The S3 adapter is out of scope for this module and is not implemented here.** The only
implementation shipped is :class:`InMemoryAnswerStore`, which is for tests and local
development; it holds everything in a process dictionary and loses it on restart. A
durable implementation of :class:`RecordedAnswerStore` (object storage, server-side
encryption, lifecycle expiry matching the evidence retention policy) is requested in
``INTEGRATION_REQUEST.md`` item 3.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final, Protocol, runtime_checkable

from veo.observations.providers.base import CitationSupport, CostBasis

__all__ = [
    "REF_SCHEME",
    "AnswerRecordKey",
    "InMemoryAnswerStore",
    "RecordedAnswer",
    "RecordedAnswerStore",
    "StoredAnswer",
]

REF_SCHEME: Final = "storage://answers/"

#: Bumped when the stored envelope changes shape, so an old record can still be read back
#: with the rules that wrote it.
RECORD_FORMAT: Final = "veo.observations.answer.v1"


@dataclass(frozen=True, slots=True)
class AnswerRecordKey:
    """What identifies one unit of observation work.

    The same triple identifies the run, which is what makes a pass idempotent: asking the
    same question under the same conditions for the same attempt number resolves to one
    stored object, not two.
    """

    prompt_id: str
    conditions_fingerprint: str
    attempt: int

    def __post_init__(self) -> None:
        if self.attempt < 1:
            raise ValueError("attempt is 1-based; 0 is not an attempt")
        if not self.prompt_id.strip() or not self.conditions_fingerprint.strip():
            raise ValueError("prompt_id and conditions_fingerprint are required")

    @property
    def object_key(self) -> str:
        return f"{self.conditions_fingerprint}/{self.prompt_id}/{self.attempt:04d}.json"

    @property
    def ref(self) -> str:
        return f"{REF_SCHEME}{self.object_key}"


@dataclass(frozen=True, slots=True)
class RecordedAnswer:
    """The evidence envelope: the answer, and everything needed to read it back.

    The meter travels with the answer rather than only on the run, so a pass that skips
    already-recorded work can reconstruct exactly what the original call cost instead of
    reporting a second pass as free.
    """

    engine: str
    model: str
    model_version: str
    text: str
    citations: tuple[str, ...]
    citation_support: CitationSupport
    latency_ms: int
    cost_usd: float | None
    cost_basis: CostBasis
    input_tokens: int | None
    output_tokens: int | None
    executed_at: datetime

    def to_bytes(self) -> bytes:
        """Canonical JSON — sorted keys, so the hash is stable across processes."""
        payload = {
            "format": RECORD_FORMAT,
            "engine": self.engine,
            "model": self.model,
            "model_version": self.model_version,
            "text": self.text,
            "citations": list(self.citations),
            "citation_support": str(self.citation_support),
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "cost_basis": str(self.cost_basis),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "executed_at": self.executed_at.isoformat(),
        }
        return json.dumps(
            payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")

    @classmethod
    def from_bytes(cls, raw: bytes) -> RecordedAnswer:
        payload: dict[str, Any] = json.loads(raw.decode("utf-8"))
        if payload.get("format") != RECORD_FORMAT:
            raise ValueError(f"unknown answer record format: {payload.get('format')!r}")
        executed_at = datetime.fromisoformat(payload["executed_at"])
        if executed_at.tzinfo is None:
            executed_at = executed_at.replace(tzinfo=UTC)
        return cls(
            engine=payload["engine"],
            model=payload["model"],
            model_version=payload["model_version"],
            text=payload["text"],
            citations=tuple(payload["citations"]),
            citation_support=CitationSupport(payload["citation_support"]),
            latency_ms=payload["latency_ms"],
            cost_usd=payload["cost_usd"],
            cost_basis=CostBasis(payload["cost_basis"]),
            input_tokens=payload["input_tokens"],
            output_tokens=payload["output_tokens"],
            executed_at=executed_at,
        )


@dataclass(frozen=True, slots=True)
class StoredAnswer:
    """A pointer and a hash — the only two things the run row is allowed to keep."""

    ref: str
    sha256: str


@runtime_checkable
class RecordedAnswerStore(Protocol):
    """Durable custody of raw AI answers."""

    def put(self, key: AnswerRecordKey, record: RecordedAnswer) -> StoredAnswer:
        """Store one answer and return its pointer and hash."""

    def find(self, key: AnswerRecordKey) -> StoredAnswer | None:
        """The pointer for work already recorded, or ``None``."""

    def read(self, ref: str) -> RecordedAnswer:
        """Read an answer back. Raises :class:`KeyError` for an unknown pointer."""


class InMemoryAnswerStore:
    """A process-local store for tests and local development.

    Not durable and not a stand-in for object storage — a restart loses every answer, and
    with it the evidence behind every mention claimed from it.
    """

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}
        self._lock = threading.Lock()

    def put(self, key: AnswerRecordKey, record: RecordedAnswer) -> StoredAnswer:
        raw = record.to_bytes()
        with self._lock:
            self._objects[key.ref] = raw
        return StoredAnswer(ref=key.ref, sha256=hashlib.sha256(raw).hexdigest())

    def find(self, key: AnswerRecordKey) -> StoredAnswer | None:
        with self._lock:
            raw = self._objects.get(key.ref)
        if raw is None:
            return None
        return StoredAnswer(ref=key.ref, sha256=hashlib.sha256(raw).hexdigest())

    def read(self, ref: str) -> RecordedAnswer:
        return RecordedAnswer.from_bytes(self.raw(ref))

    def raw(self, ref: str) -> bytes:
        """The stored bytes, for checking that a run's hash is of what was stored."""
        with self._lock:
            try:
                return self._objects[ref]
            except KeyError:
                raise KeyError(f"보관된 답변이 없습니다: {ref}") from None
