"""Recomputing stored scores under a newer specification.

Rule 2 in one sentence: **both numbers survive.** The original ``score_results`` row is
not read-modify-written, not superseded and not flagged stale — it is left exactly as it
was, and the recomputed value lands in a *new* row that points back at it through
``recomputed_from_score_result_id``. Each row carries the specification version and
checksum that produced its number, so a customer asking "why is this report's score
different from last quarter's" gets an answer with two methodology versions in it rather
than a shrug.

The inputs are rebuilt from the original row's ``calculation_trace``, which already
records every check's status, confidence and importance weights — that is what made the
original number reproducible in the first place. Two asymmetries follow from that, and
both are deliberate:

* a check the new specification adds was never collected on the old run, so it is scored
  ``UNKNOWN``. It lowers coverage and confidence, and it does not invent a failure;
* a check the new specification dropped simply is not scored.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.authz import assert_tenant_scoped
from veo.db.models.analysis import ScoreResult as ScoreResultRow
from veo.scoring import CheckOutcome, CheckStatus, ScoringSpec, evaluate

#: Scores are stored rounded to six places, so anything under this is not a movement.
UNCHANGED_TOLERANCE = 1e-6

Direction = Literal["RISEN", "FALLEN", "UNCHANGED", "INCOMPARABLE"]

#: Confidence recorded for a check the old run never measured. Zero, because there is no
#: evidence behind it at all — the point is that the gap stays visible.
UNMEASURED_CONFIDENCE = 0.0


def outcomes_from_trace(
    spec: ScoringSpec, trace: Mapping[str, Any]
) -> list[CheckOutcome]:
    """Rebuild one outcome per check in ``spec`` from a stored calculation trace."""
    recorded: dict[str, Mapping[str, Any]] = {}
    rows = trace.get("checks") if isinstance(trace, Mapping) else None
    if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)):
        for row in rows:
            if isinstance(row, Mapping) and isinstance(row.get("check_id"), str):
                recorded[str(row["check_id"])] = row

    outcomes: list[CheckOutcome] = []
    for check_id in spec.check_ids:
        row = recorded.get(check_id)
        if row is None:
            outcomes.append(
                CheckOutcome(
                    check_id=check_id,
                    status=CheckStatus.UNKNOWN,
                    confidence=UNMEASURED_CONFIDENCE,
                    note="이 검사는 원본 실행 당시 존재하지 않아 측정되지 않았습니다.",
                )
            )
            continue

        evidence = row.get("evidence_ids")
        outcomes.append(
            CheckOutcome(
                check_id=check_id,
                status=CheckStatus(str(row.get("status", "UNKNOWN"))),
                confidence=float(row.get("confidence", 0.0)),
                affected_weight=float(row.get("affected_weight", 1.0)),
                evaluated_weight=float(row.get("evaluated_weight", 1.0)),
                evidence_ids=tuple(str(item) for item in evidence)
                if isinstance(evidence, Sequence) and not isinstance(evidence, (str, bytes))
                else (),
            )
        )
    return outcomes


@dataclass(frozen=True)
class ScoreShift:
    """One original score and its recomputed counterpart, both labelled."""

    score_result_id: uuid.UUID
    scan_run_id: uuid.UUID
    recomputed_score_result_id: uuid.UUID | None
    before_score: float | None
    after_score: float | None
    before_spec_version: str
    before_spec_checksum: str
    after_spec_version: str
    after_spec_checksum: str
    direction: Direction

    @property
    def delta(self) -> float | None:
        if self.before_score is None or self.after_score is None:
            return None
        return round(self.after_score - self.before_score, 6)

    def to_record(self) -> dict[str, Any]:
        return {
            "score_result_id": str(self.score_result_id),
            "scan_run_id": str(self.scan_run_id),
            "recomputed_score_result_id": (
                str(self.recomputed_score_result_id)
                if self.recomputed_score_result_id
                else None
            ),
            "before_score": self.before_score,
            "after_score": self.after_score,
            "delta": self.delta,
            "before_spec_version": self.before_spec_version,
            "before_spec_checksum": self.before_spec_checksum,
            "after_spec_version": self.after_spec_version,
            "after_spec_checksum": self.after_spec_checksum,
            "direction": self.direction,
        }


@dataclass(frozen=True)
class RescoreSummary:
    spec_id: str
    to_version: str
    to_checksum: str
    shifts: tuple[ScoreShift, ...]
    skipped: int = 0

    @property
    def total(self) -> int:
        return len(self.shifts)

    @property
    def risen(self) -> int:
        return sum(1 for shift in self.shifts if shift.direction == "RISEN")

    @property
    def fallen(self) -> int:
        return sum(1 for shift in self.shifts if shift.direction == "FALLEN")

    @property
    def unchanged(self) -> int:
        return sum(1 for shift in self.shifts if shift.direction == "UNCHANGED")

    @property
    def incomparable(self) -> int:
        return sum(1 for shift in self.shifts if shift.direction == "INCOMPARABLE")

    @property
    def deltas(self) -> tuple[float, ...]:
        return tuple(
            shift.delta for shift in self.shifts if shift.delta is not None
        )

    @property
    def mean_delta(self) -> float:
        values = self.deltas
        return round(sum(values) / len(values), 6) if values else 0.0

    @property
    def max_rise(self) -> float:
        rises = [value for value in self.deltas if value > UNCHANGED_TOLERANCE]
        return max(rises) if rises else 0.0

    @property
    def max_fall(self) -> float:
        falls = [value for value in self.deltas if value < -UNCHANGED_TOLERANCE]
        return min(falls) if falls else 0.0

    def summary_ko(self) -> str:
        if self.total == 0:
            tail = (
                f" 이미 {self.to_version}로 재계산된 결과 {self.skipped}건은 건너뛰었습니다."
                if self.skipped
                else ""
            )
            return (
                f"{self.spec_id}@{self.to_version} 기준으로 다시 계산할 기존 점수가 "
                f"없습니다.{tail}"
            )

        breakdown = f"상승 {self.risen}건, 하락 {self.fallen}건, 변화 없음 {self.unchanged}건"
        if self.incomparable:
            breakdown += f", 비교 불가 {self.incomparable}건"
        skipped = (
            f" 이미 재계산되어 있던 {self.skipped}건은 건너뛰었습니다." if self.skipped else ""
        )
        return (
            f"{self.spec_id}@{self.to_version} 기준으로 {self.total}건을 다시 계산했습니다: "
            f"{breakdown}. 평균 변화 {self.mean_delta:+.2f}점, "
            f"최대 상승 {self.max_rise:+.2f}점, 최대 하락 {self.max_fall:+.2f}점."
            f"{skipped} 원본 점수는 손대지 않았고, 재계산 결과는 각각 새 행으로 남겼습니다."
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "to_version": self.to_version,
            "to_checksum": self.to_checksum,
            "total": self.total,
            "risen": self.risen,
            "fallen": self.fallen,
            "unchanged": self.unchanged,
            "incomparable": self.incomparable,
            "skipped": self.skipped,
            "mean_delta": self.mean_delta,
            "max_rise": self.max_rise,
            "max_fall": self.max_fall,
            "summary_ko": self.summary_ko(),
            "shifts": [shift.to_record() for shift in self.shifts],
        }


def rescore_results(
    session: Session,
    spec: ScoringSpec,
    originals: Iterable[ScoreResultRow],
) -> RescoreSummary:
    """Write one new score row per original. Nothing already stored is modified."""
    shifts: list[ScoreShift] = []
    skipped = 0

    for original in originals:
        if _already_recomputed(session, original, spec):
            skipped += 1
            continue

        result = evaluate(spec, outcomes_from_trace(spec, original.calculation_trace or {}))
        recomputed = ScoreResultRow(
            organization_id=original.organization_id,
            scan_run_id=original.scan_run_id,
            spec_id=spec.spec_id,
            spec_version=spec.version,
            spec_checksum=spec.checksum,
            domain=str(spec.domain),
            status=result.status,
            score=result.overall_score,
            score_before_caps=result.overall_score_before_caps,
            band_id=result.band_id,
            coverage=result.coverage,
            confidence=result.confidence,
            effective_weight_total=result.effective_weight_total,
            category_scores=[c.model_dump(mode="json") for c in result.categories],
            applied_caps=[c.model_dump(mode="json") for c in result.applied_caps],
            gates=[g.model_dump(mode="json") for g in result.gates],
            calculation_trace=result.trace,
            recomputed_from_score_result_id=original.id,
        )
        session.add(recomputed)
        session.flush()

        shifts.append(
            ScoreShift(
                score_result_id=original.id,
                scan_run_id=original.scan_run_id,
                recomputed_score_result_id=recomputed.id,
                before_score=original.score,
                after_score=result.overall_score,
                before_spec_version=original.spec_version,
                before_spec_checksum=original.spec_checksum,
                after_spec_version=spec.version,
                after_spec_checksum=spec.checksum,
                direction=_direction(original.score, result.overall_score),
            )
        )

    return RescoreSummary(
        spec_id=spec.spec_id,
        to_version=spec.version,
        to_checksum=spec.checksum,
        shifts=tuple(shifts),
        skipped=skipped,
    )


def _direction(before: float | None, after: float | None) -> Direction:
    if before is None or after is None:
        return "INCOMPARABLE"
    delta = after - before
    if delta > UNCHANGED_TOLERANCE:
        return "RISEN"
    if delta < -UNCHANGED_TOLERANCE:
        return "FALLEN"
    return "UNCHANGED"


def _already_recomputed(
    session: Session, original: ScoreResultRow, spec: ScoringSpec
) -> bool:
    """``score_results`` is unique on (scan_run_id, spec_id, spec_version).

    Carries the organization filter even though ``scan_run_id`` alone would be selective,
    so the structural tenant guard has something to verify rather than an exemption.
    """
    statement = (
        select(ScoreResultRow)
        .where(ScoreResultRow.organization_id == original.organization_id)
        .where(ScoreResultRow.scan_run_id == original.scan_run_id)
        .where(ScoreResultRow.spec_id == spec.spec_id)
        .where(ScoreResultRow.spec_version == spec.version)
        .limit(1)
    )
    assert_tenant_scoped(statement, original.organization_id)
    return session.scalars(statement).first() is not None
