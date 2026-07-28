"""Deterministic input hashing and idempotent job reservation.

Delivery is at-least-once, so the same submission can arrive twice. Two facts make that
safe: a canonical hash of the inputs, and a store that hands the original job back
instead of starting a second one.

A repeat of the *same* key with *different* inputs is never a silent overwrite. It is a
conflict, because the caller almost certainly reused a key by mistake and quietly
discarding one of the two requests would lose work without telling anyone.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

__all__ = [
    "IdempotencyConflictError",
    "IdempotencyRecord",
    "IdempotencyStore",
    "InMemoryIdempotencyStore",
    "Reservation",
    "canonical_json",
    "compute_input_hash",
]


def _canonicalise(value: Any) -> Any:
    """Reduce ``value`` to a JSON-safe shape with a single stable representation.

    Unknown types raise :class:`TypeError` rather than being coerced with ``str()``:
    a hash that silently depends on an object's memory address is worse than no hash.
    """
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, Enum):
        return _canonicalise(value.value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"Input values must be finite numbers; got {value!r}.")
        return value + 0.0  # normalises -0.0 to 0.0
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError(f"Input values must be finite numbers; got {value!r}.")
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Mapping):
        items = sorted(value.items(), key=lambda kv: str(kv[0]))
        return {str(k): _canonicalise(v) for k, v in items}
    if isinstance(value, (set, frozenset)):
        # Sets have no order, so canonicalise members and sort their serialised form.
        return sorted(json.dumps(_canonicalise(v), sort_keys=True) for v in value)
    if isinstance(value, (list, tuple)):
        # Sequence order is meaningful and is preserved.
        return [_canonicalise(v) for v in value]
    raise TypeError(
        f"{type(value).__name__} cannot be hashed deterministically. "
        "Convert it to a primitive before submitting the job."
    )


def canonical_json(payload: Mapping[str, Any]) -> str:
    """Serialise ``payload`` so that logically equal inputs produce identical text."""
    return json.dumps(
        _canonicalise(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def compute_input_hash(payload: Mapping[str, Any]) -> str:
    """SHA-256 of the canonical JSON form of ``payload``."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


class IdempotencyConflictError(Exception):
    """The same idempotency key was reused with a different input.

    Carries hashes and ids only. The submitted payload may contain credentials, so it
    never appears in the message.
    """

    def __init__(
        self,
        *,
        job_type: str,
        idempotency_key: str,
        existing_job_id: str,
        existing_input_hash: str,
        submitted_input_hash: str,
    ) -> None:
        self.job_type = job_type
        self.idempotency_key = idempotency_key
        self.existing_job_id = existing_job_id
        self.existing_input_hash = existing_input_hash
        self.submitted_input_hash = submitted_input_hash
        super().__init__(
            f"Idempotency key already used for {job_type} job {existing_job_id} with a "
            f"different input (stored input_hash {existing_input_hash[:12]}…, "
            f"submitted {submitted_input_hash[:12]}…)."
        )


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    job_type: str
    idempotency_key: str
    input_hash: str
    job_id: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Reservation:
    """Result of a reservation attempt.

    ``created`` is ``False`` when an existing job was returned instead of a new one.
    """

    job_id: str
    created: bool
    record: IdempotencyRecord | None = None


@runtime_checkable
class IdempotencyStore(Protocol):
    """Storage for idempotency reservations.

    Phase 0 ships an in-memory implementation. A database-backed one must make
    :meth:`reserve` atomic — the check and the insert cannot be two separate round trips.
    """

    def reserve(
        self,
        *,
        job_type: str,
        idempotency_key: str | None,
        input_hash: str,
        job_id: str,
    ) -> Reservation:
        """Claim ``idempotency_key`` for ``job_id``, or return the existing claim.

        Raises :class:`IdempotencyConflictError` when the key is already held by a job
        submitted with a different ``input_hash``.
        """

    def get(self, job_type: str, idempotency_key: str) -> IdempotencyRecord | None: ...


class InMemoryIdempotencyStore:
    """Process-local :class:`IdempotencyStore`, safe across threads.

    Suitable for tests and single-process runs. It does not survive a restart and does
    not coordinate across workers, so production must swap in a shared store.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[tuple[str, str], IdempotencyRecord] = {}

    @staticmethod
    def _key(job_type: str, idempotency_key: str) -> tuple[str, str]:
        return (str(job_type), idempotency_key)

    def reserve(
        self,
        *,
        job_type: str,
        idempotency_key: str | None,
        input_hash: str,
        job_id: str,
    ) -> Reservation:
        if idempotency_key is None:
            # No key means the caller accepts a fresh job for every submission.
            return Reservation(job_id=job_id, created=True, record=None)

        slot = self._key(job_type, idempotency_key)
        with self._lock:
            existing = self._records.get(slot)
            if existing is None:
                record = IdempotencyRecord(
                    job_type=str(job_type),
                    idempotency_key=idempotency_key,
                    input_hash=input_hash,
                    job_id=job_id,
                    created_at=datetime.now(UTC),
                )
                self._records[slot] = record
                return Reservation(job_id=job_id, created=True, record=record)

            if existing.input_hash != input_hash:
                raise IdempotencyConflictError(
                    job_type=str(job_type),
                    idempotency_key=idempotency_key,
                    existing_job_id=existing.job_id,
                    existing_input_hash=existing.input_hash,
                    submitted_input_hash=input_hash,
                )
            return Reservation(job_id=existing.job_id, created=False, record=existing)

    def get(self, job_type: str, idempotency_key: str) -> IdempotencyRecord | None:
        with self._lock:
            return self._records.get(self._key(job_type, idempotency_key))

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
