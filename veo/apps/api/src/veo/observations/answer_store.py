"""Durable custody of raw AI answers.

Every mention VEO reports is backed by the answer it came from. The adapters shipped with
an in-memory store only, which meant a restart erased the evidence behind every claim
already recorded — leaving rows asserting a mention with nothing left to check them
against. A number nobody can defend is not a measurement.

This is a filesystem implementation of the existing
:class:`~veo.observations.providers.storage.RecordedAnswerStore` protocol. Object storage
is the production adapter and is not built here; because the protocol is unchanged,
swapping it is a constructor argument rather than a rewrite.

Two properties matter beyond persistence:

* **Integrity.** Every read verifies the hash recorded at write time. Evidence that has
  changed since it was gathered is refused, not returned — a silently edited answer would
  be worse than a missing one, because it would still look like proof.
* **Confinement.** A store is bound to one organization, and a pointer that resolves
  outside that organization's directory is refused. Pointers come out of the database and
  are therefore untrusted input; a stolen one must not cross a tenant boundary, and
  ``..`` must not walk out of the root.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from veo.observations.providers.base import CitationSupport, CostBasis
from veo.observations.providers.storage import (
    AnswerRecordKey,
    RecordedAnswer,
    StoredAnswer,
)

_FILE_SCHEME = "file://"
#: Directory names are built from caller-supplied ids, so they are constrained rather
#: than trusted. Anything outside this set would let an id steer the path.
_SAFE_SEGMENT = re.compile(r"[^A-Za-z0-9._-]")


class AnswerStoreError(Exception):
    """Something went wrong reaching stored evidence."""


class AnswerNotFoundError(AnswerStoreError, KeyError):
    """No answer at that pointer.

    Also a ``KeyError`` because the protocol documents that for an unknown pointer, and a
    caller written against the protocol should not have to know which store it holds.
    """


class AnswerTamperedError(AnswerStoreError):
    """The stored answer no longer hashes to what was recorded when it was written."""


class FilesystemAnswerStore:
    """Answers on local disk, partitioned by organization and content-addressed."""

    def __init__(self, *, root: Path | str, organization_id: str) -> None:
        if not str(organization_id).strip():
            raise ValueError("organization_id is required; answers are never unpartitioned")
        self._root = Path(root).expanduser().resolve()
        self._organization_id = _safe_segment(str(organization_id))
        self._base = self._root / self._organization_id

    # ----------------------------------------------------------------- #
    # Protocol
    # ----------------------------------------------------------------- #

    def put(self, key: AnswerRecordKey, record: RecordedAnswer) -> StoredAnswer:
        if not record.text.strip():
            raise ValueError(
                "빈 답변은 저장하지 않습니다. 답변이 없는 실행은 오류 코드로 기록됩니다"
            )

        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        digest = hashlib.sha256(record.text.encode("utf-8")).hexdigest()
        payload = _envelope(record, digest)

        # Written 0600 from creation rather than chmod-ed afterwards: a raw AI answer is
        # customer material, and a window where it is world-readable is still a window.
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

        return StoredAnswer(ref=f"{_FILE_SCHEME}{path}", sha256=digest)

    def find(self, key: AnswerRecordKey) -> StoredAnswer | None:
        path = self._path_for(key)
        if not path.is_file():
            return None
        payload = _load(path)
        return StoredAnswer(ref=f"{_FILE_SCHEME}{path}", sha256=str(payload["sha256"]))

    def read(self, ref: str) -> RecordedAnswer:
        path = self._resolve(ref)
        if not path.is_file():
            raise AnswerNotFoundError(ref)

        payload = _load(path)
        text = str(payload["text"])
        recorded = str(payload["sha256"])
        actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if actual != recorded:
            raise AnswerTamperedError(
                f"저장된 답변이 기록된 해시와 다릅니다: {ref}. "
                "수집 이후 내용이 바뀌었으므로 근거로 사용하지 않습니다."
            )

        return RecordedAnswer(
            engine=str(payload["engine"]),
            model=str(payload["model"]),
            model_version=str(payload["model_version"]),
            text=text,
            citations=tuple(payload.get("citations", ())),
            citation_support=CitationSupport(payload["citation_support"]),
            latency_ms=int(payload["latency_ms"]),
            cost_usd=payload["cost_usd"],
            cost_basis=CostBasis(payload["cost_basis"]),
            input_tokens=payload["input_tokens"],
            output_tokens=payload["output_tokens"],
            executed_at=datetime.fromisoformat(payload["executed_at"]),
        )

    # ----------------------------------------------------------------- #
    # Paths
    # ----------------------------------------------------------------- #

    def _path_for(self, key: AnswerRecordKey) -> Path:
        parts = [_safe_segment(part) for part in key.object_key.split("/")]
        return self._base.joinpath(*parts)

    def _resolve(self, ref: str) -> Path:
        """Turn an untrusted pointer into a path inside this organization's directory."""
        if not ref.startswith(_FILE_SCHEME):
            raise AnswerNotFoundError(f"unsupported answer reference scheme: {ref}")

        candidate = Path(ref[len(_FILE_SCHEME) :])
        # resolve() collapses any ".." before the containment check, so a traversal is
        # caught rather than followed.
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self._base):
            raise AnswerNotFoundError(
                f"answer reference resolves outside this organization's store: {ref}"
            )
        return resolved


def _safe_segment(value: str) -> str:
    cleaned = _SAFE_SEGMENT.sub("_", value.strip())
    if cleaned in {"", ".", ".."}:
        raise ValueError(f"unusable path segment: {value!r}")
    return cleaned


def _envelope(record: RecordedAnswer, digest: str) -> dict[str, Any]:
    payload = asdict(record)
    payload["citations"] = list(record.citations)
    payload["citation_support"] = str(record.citation_support)
    payload["cost_basis"] = str(record.cost_basis)
    payload["executed_at"] = record.executed_at.isoformat()
    payload["sha256"] = digest
    return payload


def _load(path: Path) -> dict[str, Any]:
    try:
        loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AnswerStoreError(f"저장된 답변을 읽지 못했습니다: {path}") from exc
    return loaded


__all__ = [
    "AnswerNotFoundError",
    "AnswerStoreError",
    "AnswerTamperedError",
    "FilesystemAnswerStore",
]
