from __future__ import annotations

from datetime import UTC, datetime

import pytest
from veo.contracts import JobType

from veo_worker.runtime.idempotency import (
    IdempotencyConflictError,
    InMemoryIdempotencyStore,
    canonical_json,
    compute_input_hash,
)


class TestCanonicalisation:
    def test_hash_is_deterministic_across_key_ordering(self) -> None:
        a = {"url": "https://example.kr", "depth": 3, "scope": "SITE"}
        b = {"scope": "SITE", "depth": 3, "url": "https://example.kr"}
        assert compute_input_hash(a) == compute_input_hash(b)

    def test_hash_is_deterministic_for_nested_key_ordering(self) -> None:
        a = {"opts": {"b": 1, "a": {"y": 2, "x": 1}}, "z": [1, 2]}
        b = {"z": [1, 2], "opts": {"a": {"x": 1, "y": 2}, "b": 1}}
        assert compute_input_hash(a) == compute_input_hash(b)

    def test_list_order_is_significant(self) -> None:
        assert compute_input_hash({"k": [1, 2]}) != compute_input_hash({"k": [2, 1]})

    def test_hash_changes_when_a_value_changes(self) -> None:
        base = compute_input_hash({"url": "https://example.kr", "depth": 3})
        assert base != compute_input_hash({"url": "https://example.kr", "depth": 4})

    def test_hash_is_sha256_hex(self) -> None:
        digest = compute_input_hash({"a": 1})
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)

    def test_enums_datetimes_and_sets_are_canonicalised(self) -> None:
        moment = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
        payload = {"type": JobType.SEO_SCAN, "at": moment, "tags": {"b", "a"}}
        assert compute_input_hash(payload) == compute_input_hash(
            {"tags": {"a", "b"}, "at": moment, "type": JobType.SEO_SCAN}
        )
        assert "SEO_SCAN" in canonical_json(payload)

    def test_non_finite_floats_are_rejected(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            compute_input_hash({"score": float("nan")})

    def test_unsupported_type_is_rejected_rather_than_stringified(self) -> None:
        with pytest.raises(TypeError):
            compute_input_hash({"conn": object()})


class TestIdempotencyStore:
    def test_duplicate_submission_returns_the_same_job(self) -> None:
        store = InMemoryIdempotencyStore()
        digest = compute_input_hash({"url": "https://example.kr"})

        first = store.reserve(
            job_type=JobType.SEO_SCAN,
            idempotency_key="client-key-1",
            input_hash=digest,
            job_id="job-aaa",
        )
        second = store.reserve(
            job_type=JobType.SEO_SCAN,
            idempotency_key="client-key-1",
            input_hash=digest,
            job_id="job-bbb",
        )

        assert first.created is True
        assert first.job_id == "job-aaa"
        assert second.created is False
        assert second.job_id == "job-aaa", "a repeat submission must not start a second job"

    def test_same_key_with_different_input_is_a_conflict(self) -> None:
        store = InMemoryIdempotencyStore()
        store.reserve(
            job_type=JobType.SEO_SCAN,
            idempotency_key="client-key-1",
            input_hash=compute_input_hash({"url": "https://example.kr"}),
            job_id="job-aaa",
        )

        with pytest.raises(IdempotencyConflictError) as excinfo:
            store.reserve(
                job_type=JobType.SEO_SCAN,
                idempotency_key="client-key-1",
                input_hash=compute_input_hash({"url": "https://other.kr"}),
                job_id="job-ccc",
            )

        assert excinfo.value.existing_job_id == "job-aaa"
        assert store.get(JobType.SEO_SCAN, "client-key-1") is not None
        assert store.get(JobType.SEO_SCAN, "client-key-1").job_id == "job-aaa"

    def test_conflict_does_not_silently_overwrite(self) -> None:
        store = InMemoryIdempotencyStore()
        digest = compute_input_hash({"url": "https://example.kr"})
        store.reserve(
            job_type=JobType.SEO_SCAN,
            idempotency_key="k",
            input_hash=digest,
            job_id="job-aaa",
        )
        with pytest.raises(IdempotencyConflictError):
            store.reserve(
                job_type=JobType.SEO_SCAN,
                idempotency_key="k",
                input_hash=compute_input_hash({"url": "https://nope.kr"}),
                job_id="job-ddd",
            )
        record = store.get(JobType.SEO_SCAN, "k")
        assert record is not None
        assert record.input_hash == digest

    def test_same_key_under_a_different_job_type_is_independent(self) -> None:
        store = InMemoryIdempotencyStore()
        digest = compute_input_hash({"url": "https://example.kr"})
        a = store.reserve(
            job_type=JobType.SEO_SCAN, idempotency_key="k", input_hash=digest, job_id="job-a"
        )
        b = store.reserve(
            job_type=JobType.SITE_CRAWL, idempotency_key="k", input_hash=digest, job_id="job-b"
        )
        assert a.job_id == "job-a"
        assert b.job_id == "job-b"
        assert b.created is True

    def test_without_a_key_every_submission_is_a_new_job(self) -> None:
        store = InMemoryIdempotencyStore()
        digest = compute_input_hash({"url": "https://example.kr"})
        a = store.reserve(
            job_type=JobType.SEO_SCAN, idempotency_key=None, input_hash=digest, job_id="job-a"
        )
        b = store.reserve(
            job_type=JobType.SEO_SCAN, idempotency_key=None, input_hash=digest, job_id="job-b"
        )
        assert (a.job_id, a.created) == ("job-a", True)
        assert (b.job_id, b.created) == ("job-b", True)

    def test_conflict_message_carries_hashes_not_payloads(self) -> None:
        store = InMemoryIdempotencyStore()
        store.reserve(
            job_type=JobType.SEO_SCAN,
            idempotency_key="k",
            input_hash=compute_input_hash({"api_key": "sk-live-SECRET"}),
            job_id="job-a",
        )
        with pytest.raises(IdempotencyConflictError) as excinfo:
            store.reserve(
                job_type=JobType.SEO_SCAN,
                idempotency_key="k",
                input_hash=compute_input_hash({"api_key": "sk-live-OTHER"}),
                job_id="job-b",
            )
        assert "sk-live-SECRET" not in str(excinfo.value)
        assert "sk-live-OTHER" not in str(excinfo.value)
