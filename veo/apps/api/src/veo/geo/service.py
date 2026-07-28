"""Assemble the collectors, run them, and hand the outcomes to the evaluator.

The order here matters more than it looks. Collectors observe; ``veo.scoring.evaluate``
scores; gates are raised by the evaluator from the same outcomes and reported *beside* the
number. Nothing in this module adds, subtracts or bounds a score, and the report it
returns keeps the readiness number and the exposure status in separate fields so that no
caller can accidentally merge them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    EvidenceRecord,
    IssueDraft,
    run_collectors,
)
from veo.geo.collectors import (
    AccessEligibilityCollector,
    AnswerExtractabilityCollector,
    EntityClarityCollector,
    EvidenceTransparencyCollector,
    ExternalVerifiabilityCollector,
    FreshnessSignalsCollector,
    StructuredDataMetaCollector,
)
from veo.scoring import (
    CheckOutcome,
    CheckStatus,
    RaisedGate,
    ScoreResult,
    ScoringSpec,
    evaluate,
    latest_published,
)

GEO_SPEC_ID = "veo.geo.readiness"


@runtime_checkable
class GeoCategoryCollector(Protocol):
    """A collector that also names the specification category it is responsible for."""

    category_id: str

    @property
    def check_ids(self) -> frozenset[str]: ...

    def collect(self, context: CollectionContext) -> CollectionResult: ...


def geo_collectors() -> tuple[GeoCategoryCollector, ...]:
    """One collector per category, in the specification's own order."""
    return (
        AccessEligibilityCollector(),
        AnswerExtractabilityCollector(),
        EvidenceTransparencyCollector(),
        EntityClarityCollector(),
        StructuredDataMetaCollector(),
        FreshnessSignalsCollector(),
        ExternalVerifiabilityCollector(),
    )


def declared_check_ids() -> frozenset[str]:
    """Every check some collector has taken responsibility for."""
    covered: frozenset[str] = frozenset()
    for collector in geo_collectors():
        covered |= collector.check_ids
    return covered


@dataclass(frozen=True, slots=True)
class GeoReadinessReport:
    """A readiness result and an exposure status, side by side and never merged.

    A page can be structurally excellent and completely invisible. ``score`` answers
    "is this page ready", ``gates`` answers "can anyone reach it", and the two are
    reported separately because acting on them is different work.
    """

    spec: ScoringSpec
    score: ScoreResult
    evidence: tuple[EvidenceRecord, ...]
    issues: tuple[IssueDraft, ...]
    notes_ko: tuple[str, ...]

    @property
    def gates(self) -> tuple[RaisedGate, ...]:
        return tuple(self.score.gates)

    @property
    def gate_status_codes(self) -> tuple[str, ...]:
        seen: list[str] = []
        for gate in self.score.gates:
            if gate.status_code not in seen:
                seen.append(gate.status_code)
        return tuple(seen)

    @property
    def is_exposure_blocked(self) -> bool:
        return bool(self.score.gates)

    def outcome(self, check_id: str) -> CheckOutcome:
        for item in self.score.outcomes:
            if item.check_id == check_id:
                return item
        raise KeyError(check_id)

    def failing_outcomes(self) -> tuple[CheckOutcome, ...]:
        return tuple(o for o in self.score.outcomes if o.status is CheckStatus.FAIL)

    def summary_ko(self) -> str:
        """One line that states the number and the exposure status without merging them."""
        if self.score.overall_score is None:
            headline = "GEO 준비도를 산출할 수 있는 검사가 없습니다"
        else:
            band = self.spec.band_for(self.score.overall_score)
            label = band.label_ko if band else "판정 없음"
            headline = f"GEO 준비도 {self.score.overall_score:.1f}점 ({label})"

        if not self.score.gates:
            exposure = "노출 차단 상태는 확인되지 않았습니다"
        else:
            exposure = "노출 상태: " + ", ".join(gate.label_ko for gate in self.score.gates)
        return f"{headline}. {exposure}."


def run_geo_readiness(
    context: CollectionContext, *, spec: ScoringSpec | None = None
) -> GeoReadinessReport:
    """Observe, then score. The two steps never swap places."""
    chosen = spec or context.spec or latest_published(GEO_SPEC_ID)
    if chosen.spec_id != GEO_SPEC_ID:
        raise ValueError(
            f"GEO readiness needs the {GEO_SPEC_ID} specification, not {chosen.spec_id}"
        )

    missing = set(chosen.check_ids) - declared_check_ids()
    if missing:
        raise ValueError(
            "no GEO collector owns " + ", ".join(sorted(missing)) + "; a published check "
            "without a collector would silently leave the denominator"
        )

    collected: CollectionResult = run_collectors(list(geo_collectors()), context)
    result = evaluate(chosen, collected.outcomes)

    return GeoReadinessReport(
        spec=chosen,
        score=result,
        evidence=collected.evidence,
        issues=collected.issues,
        notes_ko=collected.notes_ko,
    )


__all__ = [
    "GEO_SPEC_ID",
    "GeoReadinessReport",
    "declared_check_ids",
    "geo_collectors",
    "run_geo_readiness",
]
