from __future__ import annotations

import pytest
from veo.contracts import ErrorCode, JobStatus

from veo_worker.runtime.partial import PartialResultAccumulator


class TestPartialAccounting:
    def test_eighty_of_a_hundred_pages_is_a_partial_success_with_real_numbers(self) -> None:
        acc = PartialResultAccumulator(unit_label="page", planned=100)
        for i in range(80):
            acc.record_success(f"https://example.kr/{i}")
        for i in range(80, 100):
            acc.record_failure(f"https://example.kr/{i}", ErrorCode.PROVIDER_UNAVAILABLE)

        outcome = acc.resolve()
        assert outcome.status is JobStatus.PARTIAL_SUCCESS
        assert outcome.collected == 80
        assert outcome.attempted == 100
        assert outcome.planned == 100
        assert outcome.failed == 20
        assert outcome.coverage_ratio == pytest.approx(0.8)
        assert "80" in outcome.summary_ko and "100" in outcome.summary_ko

    def test_a_complete_run_succeeds(self) -> None:
        acc = PartialResultAccumulator(unit_label="page", planned=3)
        for i in range(3):
            acc.record_success(str(i))
        outcome = acc.resolve()
        assert outcome.status is JobStatus.SUCCEEDED
        assert outcome.collected == 3
        assert outcome.attempted == 3
        assert outcome.coverage_ratio == pytest.approx(1.0)

    def test_collecting_nothing_is_a_final_failure_not_a_partial_success(self) -> None:
        acc = PartialResultAccumulator(unit_label="page", planned=5)
        for i in range(5):
            acc.record_failure(str(i), ErrorCode.PROVIDER_UNAVAILABLE)
        outcome = acc.resolve()
        assert outcome.status is JobStatus.FAILED_FINAL
        assert outcome.collected == 0
        assert outcome.attempted == 5

    def test_attempting_nothing_at_all_is_a_final_failure(self) -> None:
        acc = PartialResultAccumulator(unit_label="page", planned=5)
        outcome = acc.resolve()
        assert outcome.status is JobStatus.FAILED_FINAL
        assert outcome.attempted == 0
        assert outcome.coverage_ratio == 0.0

    def test_units_skipped_before_the_attempt_are_counted_separately(self) -> None:
        acc = PartialResultAccumulator(unit_label="page", planned=10)
        for i in range(6):
            acc.record_success(str(i))
        for i in range(6, 10):
            acc.record_skipped(str(i), reason="robots.txt disallow")

        outcome = acc.resolve()
        assert outcome.collected == 6
        assert outcome.attempted == 6
        assert outcome.skipped == 4
        assert outcome.planned == 10
        assert outcome.status is JobStatus.PARTIAL_SUCCESS

    def test_a_full_run_with_a_smaller_plan_does_not_claim_more_than_planned(self) -> None:
        acc = PartialResultAccumulator(unit_label="page", planned=2)
        acc.record_success("a")
        acc.record_success("b")
        acc.record_success("c")
        outcome = acc.resolve()
        assert outcome.collected == 3
        assert outcome.planned == 3, "the plan must be widened, never silently exceeded"
        assert outcome.status is JobStatus.SUCCEEDED

    def test_plan_can_be_revised_upwards_while_crawling(self) -> None:
        acc = PartialResultAccumulator(unit_label="page", planned=10)
        acc.plan(40)
        acc.record_success("a")
        outcome = acc.resolve()
        assert outcome.planned == 40
        assert outcome.status is JobStatus.PARTIAL_SUCCESS

    def test_failures_are_retained_but_bounded(self) -> None:
        acc = PartialResultAccumulator(unit_label="page", planned=500, max_recorded_failures=10)
        acc.record_success("ok")
        for i in range(300):
            acc.record_failure(str(i), ErrorCode.RATE_LIMITED)
        outcome = acc.resolve()
        assert outcome.failed == 300
        assert len(outcome.failures) == 10, "failure detail is capped to bound memory"
        assert outcome.failures_truncated is True

    def test_failure_breakdown_by_error_code(self) -> None:
        acc = PartialResultAccumulator(unit_label="page", planned=4)
        acc.record_success("a")
        acc.record_failure("b", ErrorCode.RATE_LIMITED)
        acc.record_failure("c", ErrorCode.RATE_LIMITED)
        acc.record_failure("d", ErrorCode.TARGET_URL_REJECTED)
        outcome = acc.resolve()
        assert outcome.failures_by_code == {
            ErrorCode.RATE_LIMITED: 2,
            ErrorCode.TARGET_URL_REJECTED: 1,
        }

    def test_recording_the_same_unit_twice_is_rejected(self) -> None:
        acc = PartialResultAccumulator(unit_label="page", planned=2)
        acc.record_success("a")
        with pytest.raises(ValueError, match="already recorded"):
            acc.record_success("a")

    def test_negative_plan_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="planned"):
            PartialResultAccumulator(unit_label="page", planned=-1)

    def test_outcome_is_immutable(self) -> None:
        acc = PartialResultAccumulator(unit_label="page", planned=1)
        acc.record_success("a")
        outcome = acc.resolve()
        with pytest.raises((AttributeError, TypeError)):
            outcome.collected = 99  # type: ignore[misc]
