from __future__ import annotations

import pytest

from veo_worker.runtime.cancellation import (
    CancellationToken,
    InMemoryCancellationRegistry,
    JobCancelledError,
)


class TestCancellationToken:
    def test_fresh_token_is_not_cancelled(self) -> None:
        token = CancellationToken(job_id="job-1")
        assert token.is_cancellation_requested is False
        token.checkpoint("fetch")  # must not raise

    def test_checkpoint_raises_once_cancellation_is_requested(self) -> None:
        token = CancellationToken(job_id="job-1")
        token.request(reason="user pressed stop")
        assert token.is_cancellation_requested is True
        with pytest.raises(JobCancelledError) as excinfo:
            token.checkpoint("fetch")
        assert excinfo.value.job_id == "job-1"
        assert excinfo.value.stage_key == "fetch"

    def test_work_between_checkpoints_is_not_interrupted(self) -> None:
        """A cancel arriving mid-stage lets the in-flight write finish, then stops."""
        token = CancellationToken(job_id="job-1")
        written: list[str] = []

        with pytest.raises(JobCancelledError) as excinfo:
            for stage in ("fetch", "analyse", "persist"):
                token.checkpoint(stage)
                if stage == "analyse":
                    # The cancel lands while this stage is already writing.
                    token.request()
                written.append(stage)

        assert written == ["fetch", "analyse"], "the in-flight stage completed its write"
        assert excinfo.value.stage_key == "persist", "it stopped at the next checkpoint"

    def test_request_is_idempotent_and_keeps_the_first_reason(self) -> None:
        token = CancellationToken(job_id="job-1")
        token.request(reason="first")
        token.request(reason="second")
        assert token.reason == "first"

    def test_reason_is_optional(self) -> None:
        token = CancellationToken(job_id="job-1")
        token.request()
        assert token.reason is None
        assert token.is_cancellation_requested is True


class TestCancellationRegistry:
    def test_registry_hands_the_same_token_back(self) -> None:
        registry = InMemoryCancellationRegistry()
        token = registry.issue("job-1")
        assert registry.get("job-1") is token

    def test_api_side_request_is_seen_by_the_worker_side_token(self) -> None:
        registry = InMemoryCancellationRegistry()
        token = registry.issue("job-1")
        assert registry.request_cancel("job-1", reason="quota") is True
        with pytest.raises(JobCancelledError):
            token.checkpoint("analyse")

    def test_cancelling_an_unknown_job_reports_false(self) -> None:
        registry = InMemoryCancellationRegistry()
        assert registry.request_cancel("nope") is False

    def test_cancel_before_issue_still_applies_when_the_token_is_issued(self) -> None:
        registry = InMemoryCancellationRegistry()
        registry.request_cancel_ahead_of_time("job-2", reason="raced")
        token = registry.issue("job-2")
        assert token.is_cancellation_requested is True
        assert token.reason == "raced"

    def test_release_forgets_the_token(self) -> None:
        registry = InMemoryCancellationRegistry()
        registry.issue("job-1")
        registry.release("job-1")
        assert registry.get("job-1") is None

    def test_issue_twice_returns_the_existing_token(self) -> None:
        registry = InMemoryCancellationRegistry()
        first = registry.issue("job-1")
        second = registry.issue("job-1")
        assert first is second
