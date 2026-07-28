"""The publication gate: what may appear in a customer-facing risk report.

The rule, stated plainly:

    **Nothing above the review threshold reaches a customer without a human having
    looked at it.**

A machine-generated sentence saying a clinic quotes the wrong price, published because a
batch job was confident, is how VEO would defame its own customer — and it would do it in
a document with VEO's name on it.

Withheld is not dropped. A customer who is told nothing cannot tell "we found nothing"
from "we found things and did not show you". The payload therefore carries the count and
the severity of what is being held back, in Korean, with the reason — and none of the
unverified text, because that text is exactly what has not been checked.

**Counts, never a score.** :func:`GateResult.as_customer_payload` emits counts by
severity and by kind. There is no total, no weighted index, no 100-point risk number
anywhere in this module. A single figure hides the one fatal finding among forty trivial
ones, and hiding that is the opposite of what this report is for.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from veo.observations.review.decisions import (
    ReviewedAssessment,
    ReviewStage,
    describe_stage_ko,
)
from veo.observations.risk.assessment import FINDING_VERDICTS, AutomatedVerdict
from veo.observations.risk.taxonomy import (
    RISK_TAXONOMY,
    RiskBand,
    RiskKind,
    RiskTaxonomy,
)

_BANDS: tuple[RiskBand, ...] = (RiskBand.FATAL, RiskBand.HIGH, RiskBand.MEDIUM, RiskBand.LOW)

METHODOLOGY_KO = (
    "위험은 종합 점수로 환산하지 않고 심각도별 건수로만 보고합니다. 점수 하나로 묶으면 "
    "사소한 지적 마흔 건 사이에 섞인 치명 한 건이 보이지 않게 되고, 정작 대응해야 할 "
    "항목이 평균에 묻힙니다."
)

WITHHELD_EXPLANATION_KO = (
    "아래 건수는 자동 판정만 있고 아직 사람 검수를 거치지 않아 이 보고서에 내용을 싣지 "
    "않았습니다. 검수 전 자동 판정을 그대로 옮기면 사실이 아닌 지적을 고객 이름과 함께 "
    "문서로 남기게 되므로, 건수와 심각도만 알려드립니다."
)

NOT_MEASURED_EXPLANATION_KO = (
    "아래 건수는 판정에 필요한 자료를 확보하지 못해 미확인(UNKNOWN)으로 남은 항목입니다. "
    "확인하지 못한 것을 문제 있음으로도 없음으로도 세지 않습니다."
)


class PublicationOutcome(StrEnum):
    """What the gate decided about one assessment."""

    PUBLISHED = "PUBLISHED"
    WITHHELD_PENDING_REVIEW = "WITHHELD_PENDING_REVIEW"
    EXCLUDED_REJECTED = "EXCLUDED_REJECTED"
    EXCLUDED_NOT_MEASURED = "EXCLUDED_NOT_MEASURED"
    NOT_A_FINDING = "NOT_A_FINDING"


@dataclass(frozen=True, slots=True)
class GatedItem:
    """One assessment and the gate's decision about it, with the reason in Korean."""

    review: ReviewedAssessment
    outcome: PublicationOutcome
    explanation_ko: str

    @property
    def assessment_id(self) -> str:
        return self.review.assessment.assessment_id

    @property
    def band(self) -> RiskBand:
        return self.review.assessment.band

    @property
    def kind(self) -> RiskKind:
        return self.review.assessment.kind


@dataclass(frozen=True, slots=True)
class GateResult:
    """Every assessment considered, and what may be shown."""

    taxonomy_version: str
    items: tuple[GatedItem, ...]

    def item(self, assessment_id: str) -> GatedItem:
        for item in self.items:
            if item.assessment_id == assessment_id:
                return item
        raise KeyError(f"이 보고 대상에 없는 판정입니다: {assessment_id}")

    def with_outcome(self, outcome: PublicationOutcome) -> tuple[GatedItem, ...]:
        return tuple(item for item in self.items if item.outcome is outcome)

    @property
    def published(self) -> tuple[GatedItem, ...]:
        return _ordered(self.with_outcome(PublicationOutcome.PUBLISHED))

    @property
    def withheld(self) -> tuple[GatedItem, ...]:
        return _ordered(self.with_outcome(PublicationOutcome.WITHHELD_PENDING_REVIEW))

    @property
    def not_measured(self) -> tuple[GatedItem, ...]:
        return _ordered(self.with_outcome(PublicationOutcome.EXCLUDED_NOT_MEASURED))

    # ----------------------------------------------------------------- #
    # Serialisation
    # ----------------------------------------------------------------- #

    def as_customer_payload(self) -> dict[str, Any]:
        """What a customer-facing report may contain.

        Every number below is a count of findings. Nothing here is averaged, weighted or
        normalised, and the withheld block deliberately carries no claim text.
        """
        return {
            "taxonomy_version": self.taxonomy_version,
            "methodology_ko": METHODOLOGY_KO,
            "counts_by_severity": _counts_by_band(self.published),
            "counts_by_kind": _counts_by_kind(self.published),
            "findings": [_finding_payload(item) for item in self.published],
            "withheld": {
                "total": len(self.withheld),
                "explanation_ko": WITHHELD_EXPLANATION_KO,
                "by_severity": _counts_by_band(self.withheld),
                "items": [_withheld_payload(item) for item in self.withheld],
            },
            "not_measured": {
                "total": len(self.not_measured),
                "explanation_ko": NOT_MEASURED_EXPLANATION_KO,
                "by_severity": _counts_by_band(self.not_measured),
            },
        }

    def as_internal_payload(self) -> dict[str, Any]:
        """The staff view: every item, including what the customer is not shown."""
        return {
            "taxonomy_version": self.taxonomy_version,
            "items": [
                {
                    "assessment_id": item.assessment_id,
                    "outcome": item.outcome.value,
                    "explanation_ko": item.explanation_ko,
                    **item.review.as_dict(),
                }
                for item in _ordered(self.items)
            ],
        }


def apply_publication_gate(
    reviews: Sequence[ReviewedAssessment], *, taxonomy: RiskTaxonomy = RISK_TAXONOMY
) -> GateResult:
    """Decide, for each assessment, whether it may appear in a customer report.

    The order of the checks is the policy:

    1. An unmeasured verdict is not a finding, whatever anyone reviewed.
    2. A finding a human rejected is not published — the human is right by construction.
    3. A verdict that is not a finding (supported, not applicable) is not a risk.
    4. Above the threshold and unreviewed → withheld, with an explanation.
    5. Otherwise published; below the threshold that may include an unreviewed item, and
       the finding then carries the caveat that says so.
    """
    return GateResult(
        taxonomy_version=taxonomy.version,
        items=tuple(_gate_one(review, taxonomy) for review in reviews),
    )


def _gate_one(review: ReviewedAssessment, taxonomy: RiskTaxonomy) -> GatedItem:
    assessment = review.assessment
    band = taxonomy.band_for(kind=assessment.kind, domain=assessment.domain)

    if assessment.automated.verdict is AutomatedVerdict.UNKNOWN:
        return GatedItem(
            review=review,
            outcome=PublicationOutcome.EXCLUDED_NOT_MEASURED,
            explanation_ko=(
                "자동 판정이 미확인(UNKNOWN)이라 위험 지적으로 집계하지 않습니다. "
                "검수자가 직접 확인한 내용이 있다면 근거를 붙여 새 판정으로 기록해야 합니다."
            ),
        )

    if review.stage is ReviewStage.REJECTED:
        reason = review.human.rejection_reason if review.human else None
        return GatedItem(
            review=review,
            outcome=PublicationOutcome.EXCLUDED_REJECTED,
            explanation_ko=(
                "검수에서 기각된 지적이라 보고서에 싣지 않습니다."
                + (f" 사유: {reason.label_ko}" if reason else "")
            ),
        )

    if assessment.automated.verdict not in FINDING_VERDICTS:
        return GatedItem(
            review=review,
            outcome=PublicationOutcome.NOT_A_FINDING,
            explanation_ko=(
                f"자동 판정이 {assessment.automated.verdict.value} 이므로 위험 지적이 "
                "아닙니다."
            ),
        )

    if taxonomy.requires_human_review(band) and not review.is_reviewed:
        return GatedItem(
            review=review,
            outcome=PublicationOutcome.WITHHELD_PENDING_REVIEW,
            explanation_ko=(
                f"심각도 '{band.label_ko}' 지적은 사람 검수를 거쳐야 고객 보고서에 실을 수 "
                f"있습니다. 현재 상태: {describe_stage_ko(review.stage)}. 검수 전 자동 판정을 "
                "그대로 싣는 것은 고객에 대한 사실이 아닌 지적을 문서로 남기는 일입니다."
            ),
        )

    if review.is_reviewed:
        explanation = "검수자가 확인한 지적입니다."
    else:
        explanation = (
            f"심각도 '{band.label_ko}' 이므로 검수 전에도 게재하지만, 자동 판정임을 함께 "
            "표시합니다."
        )
    return GatedItem(
        review=review, outcome=PublicationOutcome.PUBLISHED, explanation_ko=explanation
    )


# --------------------------------------------------------------------------- #
# Payload helpers
# --------------------------------------------------------------------------- #


def _ordered(items: Sequence[GatedItem]) -> tuple[GatedItem, ...]:
    return tuple(sorted(items, key=lambda item: (item.band.rank, item.assessment_id)))


def _counts_by_band(items: Sequence[GatedItem]) -> dict[str, dict[str, Any]]:
    tally = dict.fromkeys(_BANDS, 0)
    for item in items:
        tally[item.band] += 1
    return {
        band.value: {"label_ko": band.label_ko, "count": count}
        for band, count in tally.items()
    }


def _counts_by_kind(items: Sequence[GatedItem]) -> dict[str, int]:
    tally = dict.fromkeys(RiskKind, 0)
    for item in items:
        tally[item.kind] += 1
    return {kind.value: count for kind, count in tally.items()}


def _review_payload(item: GatedItem) -> dict[str, Any]:
    review = item.review
    human = review.human
    return {
        "state": review.stage.value,
        "state_label_ko": describe_stage_ko(review.stage),
        "is_reviewed": review.is_reviewed,
        "reviewer_id": human.reviewer_id if human else None,
        "decided_at": human.decided_at.isoformat() if human else None,
        "disagrees_with_automation": review.disagrees,
        "caveat_ko": (
            "검수자가 원문과 근거를 확인한 지적입니다."
            if review.is_reviewed
            else "자동 판정이며 사람 검수를 거치지 않았습니다."
        ),
    }


def _finding_payload(item: GatedItem) -> dict[str, Any]:
    assessment = item.review.assessment
    return {
        "assessment_id": item.assessment_id,
        "severity": item.band.value,
        "severity_label_ko": item.band.label_ko,
        "kind": assessment.kind.value,
        "domain": assessment.domain.value,
        "claim_text": assessment.claim_text,
        "evidence": assessment.evidence.as_dict(),
        # Two separate blocks, never merged: the report must be able to say which is the
        # machine's statement and which is the human's.
        "automated": assessment.automated.as_dict(),
        "review": _review_payload(item),
    }


def _withheld_payload(item: GatedItem) -> dict[str, Any]:
    """Severity, kind and reason — and none of the unverified sentence."""
    return {
        "assessment_id": item.assessment_id,
        "severity": item.band.value,
        "severity_label_ko": item.band.label_ko,
        "kind": item.kind.value,
        "reason_ko": item.explanation_ko,
    }


__all__ = [
    "METHODOLOGY_KO",
    "NOT_MEASURED_EXPLANATION_KO",
    "WITHHELD_EXPLANATION_KO",
    "GateResult",
    "GatedItem",
    "PublicationOutcome",
    "apply_publication_gate",
]
