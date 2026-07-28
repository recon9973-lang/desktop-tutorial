"""Staged progress reporting.

A long scan is opaque unless the caller can see where it is. The tracker owns an ordered
list of stages, each with a weight, and derives a single ``progress`` value in 0..1 from
the work actually completed. It emits the shared :class:`veo.contracts.JobStage` type so
the API renders it without translation.

Progress is never inflated: a stage that was cancelled or failed part-way contributes
only the fraction of its units that really finished.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from veo.contracts import JobStage, JobStatus

__all__ = [
    "ProgressSnapshot",
    "ProgressTracker",
    "StageDefinition",
    "UnknownStageError",
]

#: Stage statuses that mean "this stage is over".
_FINISHED_STATUSES = frozenset(
    {
        JobStatus.SUCCEEDED,
        JobStatus.PARTIAL_SUCCESS,
        JobStatus.FAILED_FINAL,
        JobStatus.CANCELLED,
        JobStatus.EXPIRED,
    }
)

#: Finished stages that count as fully done for progress purposes.
_FULLY_DONE_STATUSES = frozenset({JobStatus.SUCCEEDED, JobStatus.PARTIAL_SUCCESS})


class UnknownStageError(KeyError):
    """A stage key that was never declared for this job."""

    def __init__(self, key: str, known: Iterable[str]) -> None:
        self.key = key
        super().__init__(f"Unknown stage {key!r}. Declared stages: {sorted(known)}.")


@dataclass(frozen=True, slots=True)
class StageDefinition:
    """One declared step of a job.

    ``weight`` expresses relative cost. Fetching 500 pages should not weigh the same as
    writing one summary row.
    """

    key: str
    label_ko: str
    weight: float = 1.0

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("Stage key must not be blank.")
        if self.weight <= 0:
            raise ValueError(f"Stage {self.key!r} weight must be positive; got {self.weight}.")


@dataclass(frozen=True, slots=True)
class ProgressSnapshot:
    """An immutable, copy-safe view the API can serialise."""

    progress: float
    current_stage: str | None
    stages: list[JobStage]


class ProgressTracker:
    """Owns the stage list for one job run."""

    def __init__(self, stages: Sequence[StageDefinition]) -> None:
        if not stages:
            raise ValueError("A job needs at least one stage.")
        keys = [s.key for s in stages]
        if len(set(keys)) != len(keys):
            duplicates = sorted({k for k in keys if keys.count(k) > 1})
            raise ValueError(f"Stage keys must be unique; duplicate keys: {duplicates}.")

        self._definitions: dict[str, StageDefinition] = {s.key: s for s in stages}
        self._stages: dict[str, JobStage] = {
            s.key: JobStage(key=s.key, label_ko=s.label_ko, status=JobStatus.QUEUED)
            for s in stages
        }
        self._current: str | None = None

    # -- reading -------------------------------------------------------------

    @property
    def stages(self) -> list[JobStage]:
        """Live stage objects, in declaration order."""
        return list(self._stages.values())

    @property
    def current_stage(self) -> str | None:
        return self._current

    @property
    def progress(self) -> float:
        total_weight = sum(d.weight for d in self._definitions.values())
        done_weight = 0.0
        for key, stage in self._stages.items():
            weight = self._definitions[key].weight
            if stage.status in _FULLY_DONE_STATUSES:
                done_weight += weight
            elif stage.status is JobStatus.QUEUED:
                continue
            else:
                # Running, cancelled or failed: credit only the units actually finished.
                done_weight += weight * _fraction(stage)
        return round(min(max(done_weight / total_weight, 0.0), 1.0), 6)

    def snapshot(self) -> ProgressSnapshot:
        """A deep copy, so a caller holding it cannot mutate the live run."""
        return ProgressSnapshot(
            progress=self.progress,
            current_stage=self._current,
            stages=[stage.model_copy(deep=True) for stage in self._stages.values()],
        )

    # -- writing -------------------------------------------------------------

    def _stage(self, key: str) -> JobStage:
        try:
            return self._stages[key]
        except KeyError:
            raise UnknownStageError(key, self._stages) from None

    def begin(self, key: str) -> None:
        stage = self._stage(key)
        if stage.status in _FINISHED_STATUSES:
            raise ValueError(f"Stage {key!r} has already finished and cannot be restarted.")
        stage.status = JobStatus.RUNNING
        stage.started_at = stage.started_at or datetime.now(UTC)
        self._current = key

    def advance(self, key: str, *, items_done: int, items_total: int | None = None) -> None:
        stage = self._stage(key)
        if items_done < 0:
            raise ValueError("items_done must not be negative.")
        stage.items_done = items_done
        if items_total is not None:
            if items_total < 0:
                raise ValueError("items_total must not be negative.")
            stage.items_total = items_total

    def complete(self, key: str, *, status: JobStatus = JobStatus.SUCCEEDED) -> None:
        stage = self._stage(key)
        if stage.started_at is None:
            raise ValueError(f"Stage {key!r} was not started, so it cannot be completed.")
        if status not in _FINISHED_STATUSES:
            raise ValueError(f"{status.value} is not a finished stage status.")
        stage.status = status
        stage.finished_at = datetime.now(UTC)
        if status is JobStatus.SUCCEEDED and stage.items_total is not None:
            # Only a clean success may claim every unit. PARTIAL_SUCCESS keeps its real count.
            stage.items_done = max(stage.items_done, stage.items_total)


def _fraction(stage: JobStage) -> float:
    if not stage.items_total:
        return 0.0
    done: int = stage.items_done
    total: int = stage.items_total
    return min(done / total, 1.0)
