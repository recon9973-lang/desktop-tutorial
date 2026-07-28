"""Evidence has to outlive the process that gathered it.

Every mention VEO claims is backed by a stored answer. Until now the only implementation
was in-memory, so a restart erased the evidence behind every claim already made — leaving
rows that assert a mention with nothing to check them against. That is the shape of a
number nobody can defend.

This is the durable half. It is a filesystem store, not object storage: S3 is the
production adapter and is not built here, but the protocol is the same, so swapping it is
a constructor change rather than a rewrite.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from veo.observations.answer_store import (
    AnswerNotFoundError,
    AnswerTamperedError,
    FilesystemAnswerStore,
)
from veo.observations.providers.base import CitationSupport, CostBasis
from veo.observations.providers.storage import (
    AnswerRecordKey,
    RecordedAnswer,
    RecordedAnswerStore,
)

TEXT = "서초구의 베놈치과는 야간 진료를 운영합니다."


@pytest.fixture
def store(tmp_path: Path) -> FilesystemAnswerStore:
    return FilesystemAnswerStore(root=tmp_path, organization_id="org-a")


def key(prompt: str = "p1", attempt: int = 1) -> AnswerRecordKey:
    return AnswerRecordKey(prompt_id=prompt, conditions_fingerprint="cond-abc", attempt=attempt)


def answer(text: str = TEXT) -> RecordedAnswer:
    return RecordedAnswer(
        engine="OPENAI",
        model="gpt-5",
        model_version="2026-05-01",
        text=text,
        citations=("https://example.test/a",),
        citation_support=CitationSupport.STRUCTURED,
        latency_ms=1200,
        cost_usd=None,
        cost_basis=CostBasis.NO_PRICE_CONFIGURED,
        input_tokens=120,
        output_tokens=340,
        executed_at=datetime(2026, 7, 28, 12, 0, tzinfo=UTC),
    )


# --------------------------------------------------------------------------- #
# Durability — the reason this exists
# --------------------------------------------------------------------------- #


def test_an_answer_survives_a_new_store_object(tmp_path: Path) -> None:
    stored = FilesystemAnswerStore(root=tmp_path, organization_id="org-a").put(key(), answer())
    reopened = FilesystemAnswerStore(root=tmp_path, organization_id="org-a")
    assert reopened.read(stored.ref).text == TEXT


def test_put_returns_a_pointer_and_the_hash_of_the_text(
    store: FilesystemAnswerStore,
) -> None:
    stored = store.put(key(), answer())
    assert stored.ref
    assert stored.sha256 == hashlib.sha256(TEXT.encode("utf-8")).hexdigest()


def test_the_whole_envelope_is_kept_not_just_the_text(store: FilesystemAnswerStore) -> None:
    """Cost and citations travel with the answer, so a resumed pass is not reported free."""
    restored = store.read(store.put(key(), answer()).ref)
    assert restored.model_version == "2026-05-01"
    assert restored.citations == ("https://example.test/a",)
    assert restored.citation_support is CitationSupport.STRUCTURED
    assert restored.latency_ms == 1200
    assert restored.input_tokens == 120
    assert restored.cost_basis is CostBasis.NO_PRICE_CONFIGURED


# --------------------------------------------------------------------------- #
# Idempotency
# --------------------------------------------------------------------------- #


def test_find_returns_previously_recorded_work(store: FilesystemAnswerStore) -> None:
    stored = store.put(key(), answer())
    assert store.find(key()) == stored


def test_find_returns_none_for_work_never_done(store: FilesystemAnswerStore) -> None:
    assert store.find(key(prompt="never-asked")) is None


def test_a_different_attempt_is_a_different_object(store: FilesystemAnswerStore) -> None:
    """Repetitions are separate measurements and must not overwrite each other."""
    first = store.put(key(attempt=1), answer())
    second = store.put(key(attempt=2), answer("다른 답변입니다."))
    assert first.ref != second.ref
    assert store.read(first.ref).text != store.read(second.ref).text


# --------------------------------------------------------------------------- #
# Integrity
# --------------------------------------------------------------------------- #


def test_a_tampered_answer_is_refused_rather_than_returned(
    store: FilesystemAnswerStore,
) -> None:
    """Evidence that changed since it was recorded is not evidence.

    The realistic attack edits the answer text and leaves the envelope intact, so the
    file still parses and still looks like a record. Only the hash catches it.
    """
    import json

    stored = store.put(key(), answer())
    path = Path(stored.ref.removeprefix("file://"))
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["text"] = "베놈치과는 로봇수술도 가능합니다."
    path.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(AnswerTamperedError):
        store.read(stored.ref)


def test_a_corrupted_file_is_refused_too(store: FilesystemAnswerStore) -> None:
    """Unreadable evidence is refused as loudly as altered evidence."""
    from veo.observations.answer_store import AnswerStoreError

    stored = store.put(key(), answer())
    Path(stored.ref.removeprefix("file://")).write_text("not json at all", encoding="utf-8")

    with pytest.raises(AnswerStoreError):
        store.read(stored.ref)


def test_a_missing_answer_is_a_named_error(store: FilesystemAnswerStore) -> None:
    with pytest.raises(AnswerNotFoundError):
        store.read("file:///nowhere/at/all.json")


# --------------------------------------------------------------------------- #
# Tenancy and confinement
# --------------------------------------------------------------------------- #


def test_answers_are_partitioned_by_organization(tmp_path: Path) -> None:
    """One tenant's raw answers must not land in another's directory."""
    a = FilesystemAnswerStore(root=tmp_path, organization_id="org-a").put(key(), answer())
    b = FilesystemAnswerStore(root=tmp_path, organization_id="org-b").put(key(), answer())
    assert a.ref != b.ref
    assert "org-a" in a.ref and "org-b" in b.ref


def test_one_organization_cannot_read_another_by_pointer(tmp_path: Path) -> None:
    """A pointer comes out of the database; a stolen one must still not cross tenants."""
    theirs = FilesystemAnswerStore(root=tmp_path, organization_id="org-b").put(key(), answer())
    ours = FilesystemAnswerStore(root=tmp_path, organization_id="org-a")

    with pytest.raises((AnswerNotFoundError, ValueError)):
        ours.read(theirs.ref)


def test_a_reference_cannot_escape_the_store_root(store: FilesystemAnswerStore) -> None:
    with pytest.raises((AnswerNotFoundError, ValueError)):
        store.read("file:///etc/passwd")


def test_a_traversal_attempt_is_refused(store: FilesystemAnswerStore, tmp_path: Path) -> None:
    (tmp_path.parent / "secret.txt").write_text("비밀", encoding="utf-8")
    with pytest.raises((AnswerNotFoundError, ValueError)):
        store.read(f"file://{tmp_path}/org-a/../../secret.txt")


def test_stored_files_are_not_readable_by_others(store: FilesystemAnswerStore) -> None:
    """Raw AI answers are customer material behind the evidence permission."""
    stored = store.put(key(), answer())
    mode = Path(stored.ref.removeprefix("file://")).stat().st_mode & 0o777
    assert mode & 0o077 == 0, f"answer file is readable by others: {oct(mode)}"


# --------------------------------------------------------------------------- #
# Contract
# --------------------------------------------------------------------------- #


def test_the_store_satisfies_the_protocol(tmp_path: Path) -> None:
    assert isinstance(
        FilesystemAnswerStore(root=tmp_path, organization_id="org-a"), RecordedAnswerStore
    )


def test_an_empty_answer_is_refused(store: FilesystemAnswerStore) -> None:
    """An empty answer means a failed call, and a failed call records an error, not a file."""
    with pytest.raises(ValueError):
        store.put(key(), answer("   "))
