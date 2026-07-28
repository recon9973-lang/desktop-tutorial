"""Partial-success accounting.

A crawl that reached 80 of 100 pages produced something useful. Reporting it as a flat
failure throws that away; reporting it as a success is a lie. The accumulator keeps the
real counts and derives the honest status from them.

The counts are the point. ``PARTIAL_SUCCESS`` without ``collected``/``attempted`` beside
it is just a shrug.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime

from veo.contracts import ErrorCode, JobStatus

__all__ = [
    "PartialOutcome",
    "PartialResultAccumulator",
    "UnitFailure",
]


@dataclass(frozen=True, slots=True)
class UnitFailure:
    unit_ref: str
    error_code: ErrorCode
    at: datetime


@dataclass(frozen=True, slots=True)
class UnitSkip:
    unit_ref: str
    reason: str


@dataclass(frozen=True, slots=True)
class PartialOutcome:
    """Immutable verdict on a run, with the numbers that justify it."""

    status: JobStatus
    unit_label: str
    planned: int
    attempted: int
    collected: int
    failed: int
    skipped: int
    coverage_ratio: float
    failures: tuple[UnitFailure, ...]
    failures_truncated: bool
    failures_by_code: dict[ErrorCode, int]
    skips: tuple[UnitSkip, ...]

    @property
    def summary_ko(self) -> str:
        """One-line Korean summary safe to show a customer."""
        return (
            f"{self.unit_label} {self.planned}건 중 {self.collected}건 수집"
            f" (실패 {self.failed}건, 건너뜀 {self.skipped}건)"
        )


class PartialResultAccumulator:
    """Records the fate of every unit a job tried to collect."""

    def __init__(
        self,
        *,
        unit_label: str,
        planned: int = 0,
        max_recorded_failures: int = 50,
        max_recorded_skips: int = 50,
    ) -> None:
        if planned < 0:
            raise ValueError("planned must not be negative.")
        if max_recorded_failures < 1:
            raise ValueError("max_recorded_failures must be at least 1.")
        self.unit_label = unit_label
        self._planned = planned
        self._max_failures = max_recorded_failures
        self._max_skips = max_recorded_skips
        self._seen: set[str] = set()
        self._collected = 0
        self._failed = 0
        self._skipped = 0
        self._failures: list[UnitFailure] = []
        self._skips: list[UnitSkip] = []
        self._failures_by_code: Counter[ErrorCode] = Counter()

    # -- recording -----------------------------------------------------------

    def plan(self, total: int) -> None:
        """Revise the expected total, e.g. once a crawl has discovered the sitemap."""
        if total < 0:
            raise ValueError("planned must not be negative.")
        self._planned = total

    def _claim(self, unit_ref: str) -> None:
        if unit_ref in self._seen:
            raise ValueError(f"{self.unit_label} {unit_ref!r} was already recorded.")
        self._seen.add(unit_ref)

    def record_success(self, unit_ref: str) -> None:
        self._claim(unit_ref)
        self._collected += 1

    def record_failure(self, unit_ref: str, error_code: ErrorCode) -> None:
        self._claim(unit_ref)
        self._failed += 1
        self._failures_by_code[error_code] += 1
        if len(self._failures) < self._max_failures:
            self._failures.append(
                UnitFailure(unit_ref=unit_ref, error_code=error_code, at=datetime.now(UTC))
            )

    def record_skipped(self, unit_ref: str, *, reason: str) -> None:
        """A unit deliberately not attempted — robots.txt, an exclusion rule, a budget cap."""
        self._claim(unit_ref)
        self._skipped += 1
        if len(self._skips) < self._max_skips:
            self._skips.append(UnitSkip(unit_ref=unit_ref, reason=reason))

    # -- reading -------------------------------------------------------------

    @property
    def attempted(self) -> int:
        """Units the job actually tried. Skips were never attempted."""
        return self._collected + self._failed

    @property
    def collected(self) -> int:
        return self._collected

    def resolve(self) -> PartialOutcome:
        """Derive the job status from the counts."""
        attempted = self.attempted
        # The plan is widened, never silently exceeded: discovering more work than
        # expected must not make coverage look better than it was.
        planned = max(self._planned, attempted + self._skipped)
        coverage = (self._collected / attempted) if attempted else 0.0

        if self._collected == 0:
            # Nothing was gathered. There is no partial result to offer.
            status = JobStatus.FAILED_FINAL
        elif self._collected == planned and self._failed == 0 and self._skipped == 0:
            status = JobStatus.SUCCEEDED
        else:
            status = JobStatus.PARTIAL_SUCCESS

        return PartialOutcome(
            status=status,
            unit_label=self.unit_label,
            planned=planned,
            attempted=attempted,
            collected=self._collected,
            failed=self._failed,
            skipped=self._skipped,
            coverage_ratio=round(coverage, 6),
            failures=tuple(self._failures),
            failures_truncated=self._failed > len(self._failures),
            failures_by_code=dict(self._failures_by_code),
            skips=tuple(self._skips),
        )
