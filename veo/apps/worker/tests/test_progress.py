from __future__ import annotations

import pytest
from veo.contracts import JobStage, JobStatus

from veo_worker.runtime.progress import ProgressTracker, StageDefinition, UnknownStageError

STAGES = [
    StageDefinition(key="fetch", label_ko="수집", weight=2.0),
    StageDefinition(key="analyse", label_ko="분석", weight=1.0),
    StageDefinition(key="persist", label_ko="저장", weight=1.0),
]


def tracker() -> ProgressTracker:
    return ProgressTracker(STAGES)


class TestProgressTracker:
    def test_starts_empty(self) -> None:
        t = tracker()
        assert t.progress == 0.0
        assert t.current_stage is None
        assert [s.status for s in t.stages] == [JobStatus.QUEUED] * 3

    def test_stages_are_contract_job_stages(self) -> None:
        t = tracker()
        assert all(isinstance(stage, JobStage) for stage in t.stages)
        assert [s.key for s in t.stages] == ["fetch", "analyse", "persist"]
        assert [s.label_ko for s in t.stages] == ["수집", "분석", "저장"]

    def test_beginning_a_stage_sets_current_stage_and_running(self) -> None:
        t = tracker()
        t.begin("fetch")
        assert t.current_stage == "fetch"
        assert t.stages[0].status is JobStatus.RUNNING
        assert t.stages[0].started_at is not None

    def test_progress_is_weighted_by_stage_weight(self) -> None:
        t = tracker()
        t.begin("fetch")
        t.complete("fetch")
        assert t.progress == pytest.approx(0.5)
        t.begin("analyse")
        t.complete("analyse")
        assert t.progress == pytest.approx(0.75)

    def test_partial_units_within_a_stage_move_progress(self) -> None:
        t = tracker()
        t.begin("fetch")
        t.advance("fetch", items_done=50, items_total=100)
        assert t.progress == pytest.approx(0.25)
        assert t.stages[0].items_done == 50
        assert t.stages[0].items_total == 100

    def test_progress_is_monotonic_over_a_normal_run(self) -> None:
        t = tracker()
        seen = [t.progress]
        for key in ("fetch", "analyse", "persist"):
            t.begin(key)
            t.advance(key, items_done=1, items_total=2)
            seen.append(t.progress)
            t.complete(key)
            seen.append(t.progress)
        assert seen == sorted(seen)
        assert seen[-1] == pytest.approx(1.0)

    def test_progress_never_leaves_the_zero_to_one_range(self) -> None:
        t = tracker()
        t.begin("fetch")
        t.advance("fetch", items_done=9_999, items_total=10)
        assert 0.0 <= t.progress <= 1.0

    def test_cancelled_stage_keeps_only_the_work_actually_done(self) -> None:
        t = tracker()
        t.begin("fetch")
        t.advance("fetch", items_done=25, items_total=100)
        t.complete("fetch", status=JobStatus.CANCELLED)
        assert t.progress == pytest.approx(0.125)
        assert t.stages[0].status is JobStatus.CANCELLED
        assert t.stages[0].finished_at is not None

    def test_partial_success_stage_counts_as_done(self) -> None:
        t = tracker()
        t.begin("fetch")
        t.advance("fetch", items_done=80, items_total=100)
        t.complete("fetch", status=JobStatus.PARTIAL_SUCCESS)
        assert t.progress == pytest.approx(0.5)

    def test_snapshot_matches_the_live_view(self) -> None:
        t = tracker()
        t.begin("fetch")
        t.advance("fetch", items_done=1, items_total=4)
        snap = t.snapshot()
        assert snap.current_stage == "fetch"
        assert snap.progress == pytest.approx(t.progress)
        assert [s.key for s in snap.stages] == ["fetch", "analyse", "persist"]
        snap.stages[0].items_done = 999
        assert t.stages[0].items_done == 1, "snapshot must not alias internal state"

    def test_unknown_stage_is_rejected(self) -> None:
        t = tracker()
        with pytest.raises(UnknownStageError):
            t.begin("nope")
        with pytest.raises(UnknownStageError):
            t.advance("nope", items_done=1, items_total=2)

    def test_completing_a_stage_that_never_started_is_rejected(self) -> None:
        t = tracker()
        with pytest.raises(ValueError, match="not started"):
            t.complete("analyse")

    def test_duplicate_stage_keys_are_rejected(self) -> None:
        with pytest.raises(ValueError, match="duplicate"):
            ProgressTracker(
                [
                    StageDefinition(key="a", label_ko="가", weight=1.0),
                    StageDefinition(key="a", label_ko="나", weight=1.0),
                ]
            )

    def test_empty_stage_list_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least one stage"):
            ProgressTracker([])

    def test_non_positive_weight_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="weight"):
            StageDefinition(key="a", label_ko="가", weight=0.0)
