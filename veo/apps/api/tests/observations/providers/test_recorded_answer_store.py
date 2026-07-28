"""Where the raw answer goes, and what the run is allowed to keep.

The run row keeps a pointer and a hash. The answer itself — long, sensitive, sometimes
quoting a named person — lives behind the evidence permission in object storage. These
tests pin the boundary and the round trip.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.observations.providers.synthetic import (
    BRAND_DOMAIN,
    mentioning_answer,
)

from veo.observations.providers.base import CitationSupport, CostBasis
from veo.observations.providers.storage import (
    AnswerRecordKey,
    InMemoryAnswerStore,
    RecordedAnswer,
    RecordedAnswerStore,
)

NOW = datetime(2026, 7, 28, 9, 0, tzinfo=UTC)

KEY = AnswerRecordKey(prompt_id="p" * 32, conditions_fingerprint="c" * 32, attempt=1)


def record(text: str | None = None) -> RecordedAnswer:
    return RecordedAnswer(
        engine="OPENAI",
        model="gpt-5",
        model_version="gpt-5-2026-05-01",
        text=text if text is not None else mentioning_answer(),
        citations=(f"https://{BRAND_DOMAIN}/a",),
        citation_support=CitationSupport.STRUCTURED,
        latency_ms=250,
        cost_usd=0.5,
        cost_basis=CostBasis.CALCULATED_FROM_USAGE,
        input_tokens=1000,
        output_tokens=500,
        executed_at=NOW,
    )


def test_the_in_memory_store_satisfies_the_protocol() -> None:
    store: RecordedAnswerStore = InMemoryAnswerStore()
    assert store.find(KEY) is None


def test_a_stored_answer_round_trips_byte_for_byte() -> None:
    store = InMemoryAnswerStore()
    original = record()
    stored = store.put(KEY, original)
    assert store.read(stored.ref) == original


def test_the_hash_is_the_sha256_of_what_was_stored() -> None:
    import hashlib

    store = InMemoryAnswerStore()
    stored = store.put(KEY, record())
    assert stored.sha256 == hashlib.sha256(store.raw(stored.ref)).hexdigest()
    assert len(stored.sha256) == 64


def test_two_different_answers_under_the_same_key_do_not_collide_silently() -> None:
    store = InMemoryAnswerStore()
    first = store.put(KEY, record(text="합성 답변 1"))
    second = store.put(KEY, record(text="합성 답변 2"))
    assert first.ref == second.ref
    assert first.sha256 != second.sha256
    assert store.read(second.ref).text == "합성 답변 2"


def test_the_key_is_stable_for_the_same_prompt_conditions_and_attempt() -> None:
    same = AnswerRecordKey(
        prompt_id="p" * 32, conditions_fingerprint="c" * 32, attempt=1
    )
    assert same.object_key == KEY.object_key
    other = AnswerRecordKey(
        prompt_id="p" * 32, conditions_fingerprint="c" * 32, attempt=2
    )
    assert other.object_key != KEY.object_key


def test_reading_an_unknown_reference_raises_rather_than_returning_an_empty_answer() -> None:
    store = InMemoryAnswerStore()
    with pytest.raises(KeyError):
        store.read("storage://answers/nothing-here")


def test_a_negative_attempt_is_refused() -> None:
    with pytest.raises(ValueError, match="attempt"):
        AnswerRecordKey(prompt_id="p", conditions_fingerprint="c", attempt=0)


def test_the_store_module_states_that_the_s3_adapter_is_out_of_scope() -> None:
    """The only implementation here is in-memory, and it says so rather than implying more."""
    import veo.observations.providers.storage as storage

    assert storage.__doc__ is not None
    assert "S3" in storage.__doc__
