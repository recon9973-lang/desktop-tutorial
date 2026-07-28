"""The publication gate.

Nothing above the review threshold reaches a customer-facing report without a human
having looked at it. A machine-generated sentence saying a clinic quotes the wrong price,
published unreviewed, is how VEO would defame its own customer.

Withheld is not dropped: the customer is told that findings exist and are waiting, in
Korean, with the count and the severity — just not the unverified text.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from review_support import CLAIM_TEXT, NOW, REVIEWER, assessment

from veo.observations.review.decisions import (
    RejectionReason,
    ReviewStage,
    ReviewTrigger,
    apply_decision,
    open_review,
)
from veo.observations.review.gating import (
    PublicationOutcome,
    apply_publication_gate,
)
from veo.observations.risk.assessment import AutomatedVerdict
from veo.observations.risk.taxonomy import ClaimDomain, RiskBand, RiskKind

#: Anything that would turn counts into a single number. A composite risk score hides
#: the one fatal finding among forty trivial ones, which is the entire reason the
#: methodology counts instead.
FORBIDDEN_KEY_FRAGMENTS = (
    "score",
    "점수",
    "총점",
    "grade",
    "rating",
    "composite",
    "risk_index",
    "weighted",
    "rank",
)


def reviewed(item, stage: ReviewStage, **kwargs: Any):  # type: ignore[no-untyped-def]
    review = open_review(item)
    if stage is ReviewStage.PENDING_REVIEW:
        return review
    review = apply_decision(
        review,
        target=ReviewStage.UNDER_REVIEW,
        trigger=ReviewTrigger.REVIEWER_CLAIM,
        reviewer_id=REVIEWER,
        at=NOW,
    )
    if stage is ReviewStage.UNDER_REVIEW:
        return review
    return apply_decision(
        review,
        target=stage,
        trigger=ReviewTrigger.REVIEWER_DECISION,
        reviewer_id=REVIEWER,
        at=NOW,
        **kwargs,
    )


def walk(payload: Any, path: str = "") -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            found.append((f"{path}.{key}", key))
            found.extend(walk(value, f"{path}.{key}"))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            found.extend(walk(value, f"{path}[{index}]"))
    return found


def numbers(payload: Any) -> list[Any]:
    found: list[Any] = []
    if isinstance(payload, dict):
        for value in payload.values():
            found.extend(numbers(value))
    elif isinstance(payload, list):
        for value in payload:
            found.extend(numbers(value))
    elif isinstance(payload, bool):
        pass
    elif isinstance(payload, (int, float)):
        found.append(payload)
    return found


# --------------------------------------------------------------------------- #
# The gate itself
# --------------------------------------------------------------------------- #


def test_a_critical_unreviewed_assessment_is_withheld_from_a_customer_report() -> None:
    result = apply_publication_gate(
        [reviewed(assessment("as-1", domain=ClaimDomain.MEDICAL), ReviewStage.PENDING_REVIEW)]
    )
    item = result.item("as-1")
    assert item.outcome is PublicationOutcome.WITHHELD_PENDING_REVIEW
    assert item.band is RiskBand.FATAL


def test_the_withholding_is_explained_in_korean_not_silently_dropped() -> None:
    result = apply_publication_gate(
        [reviewed(assessment("as-1", domain=ClaimDomain.MEDICAL), ReviewStage.PENDING_REVIEW)]
    )
    payload = result.as_customer_payload()
    assert payload["withheld"]["total"] == 1
    assert payload["withheld"]["by_severity"]["FATAL"]["count"] == 1
    assert payload["withheld"]["by_severity"]["FATAL"]["label_ko"] == "치명"
    assert payload["withheld"]["explanation_ko"].strip()
    assert result.item("as-1").explanation_ko.strip()


def test_a_withheld_finding_does_not_leak_its_unverified_text() -> None:
    result = apply_publication_gate(
        [reviewed(assessment("as-1", domain=ClaimDomain.MEDICAL), ReviewStage.PENDING_REVIEW)]
    )
    serialized = json.dumps(result.as_customer_payload(), ensure_ascii=False)
    assert CLAIM_TEXT not in serialized


def test_an_item_under_review_is_still_withheld() -> None:
    result = apply_publication_gate(
        [reviewed(assessment("as-1", domain=ClaimDomain.MEDICAL), ReviewStage.UNDER_REVIEW)]
    )
    assert result.item("as-1").outcome is PublicationOutcome.WITHHELD_PENDING_REVIEW


def test_needs_more_evidence_is_withheld() -> None:
    result = apply_publication_gate(
        [
            reviewed(
                assessment("as-1", domain=ClaimDomain.MEDICAL),
                ReviewStage.NEEDS_MORE_EVIDENCE,
                note_ko="원문 재수집 필요",
            )
        ]
    )
    assert result.item("as-1").outcome is PublicationOutcome.WITHHELD_PENDING_REVIEW


def test_a_confirmed_critical_finding_is_published() -> None:
    result = apply_publication_gate(
        [reviewed(assessment("as-1", domain=ClaimDomain.MEDICAL), ReviewStage.CONFIRMED)]
    )
    assert result.item("as-1").outcome is PublicationOutcome.PUBLISHED
    payload = result.as_customer_payload()
    assert payload["counts_by_severity"]["FATAL"]["count"] == 1
    assert payload["findings"][0]["claim_text"] == CLAIM_TEXT


def test_a_rejected_finding_is_excluded_and_says_so() -> None:
    result = apply_publication_gate(
        [
            reviewed(
                assessment("as-1", domain=ClaimDomain.MEDICAL),
                ReviewStage.REJECTED,
                rejection_reason=RejectionReason.CLAIM_IS_ACCURATE,
            )
        ]
    )
    item = result.item("as-1")
    assert item.outcome is PublicationOutcome.EXCLUDED_REJECTED
    assert result.as_customer_payload()["counts_by_severity"]["FATAL"]["count"] == 0
    assert item.explanation_ko.strip()


def test_an_unknown_verdict_is_never_published_as_a_finding() -> None:
    result = apply_publication_gate(
        [
            reviewed(
                assessment("as-1", domain=ClaimDomain.MEDICAL, verdict=AutomatedVerdict.UNKNOWN),
                ReviewStage.CONFIRMED,
            )
        ]
    )
    assert result.item("as-1").outcome is PublicationOutcome.EXCLUDED_NOT_MEASURED
    payload = result.as_customer_payload()
    assert payload["not_measured"]["total"] == 1
    assert payload["not_measured"]["explanation_ko"].strip()


def test_a_supported_claim_is_not_a_risk_finding() -> None:
    result = apply_publication_gate(
        [
            reviewed(
                assessment(
                    "as-1", domain=ClaimDomain.MEDICAL, verdict=AutomatedVerdict.SUPPORTED
                ),
                ReviewStage.CONFIRMED,
            )
        ]
    )
    assert result.item("as-1").outcome is PublicationOutcome.NOT_A_FINDING
    assert result.as_customer_payload()["counts_by_severity"]["FATAL"]["count"] == 0


# --------------------------------------------------------------------------- #
# Below the threshold
# --------------------------------------------------------------------------- #


def test_a_low_band_unreviewed_finding_is_published_with_a_caveat() -> None:
    result = apply_publication_gate(
        [
            reviewed(
                assessment("as-1", kind=RiskKind.STALENESS, domain=ClaimDomain.GENERAL),
                ReviewStage.PENDING_REVIEW,
            )
        ]
    )
    assert result.item("as-1").outcome is PublicationOutcome.PUBLISHED
    finding = result.as_customer_payload()["findings"][0]
    assert finding["review"]["state"] == "PENDING_REVIEW"
    assert finding["review"]["caveat_ko"].strip()


def test_a_published_finding_keeps_the_machine_and_the_human_apart() -> None:
    result = apply_publication_gate(
        [reviewed(assessment("as-1", domain=ClaimDomain.MEDICAL), ReviewStage.CONFIRMED)]
    )
    finding = result.as_customer_payload()["findings"][0]
    assert finding["automated"]["verdict"] == AutomatedVerdict.CONTRADICTED.value
    assert finding["automated"]["basis"] == "LANGUAGE_MODEL"
    assert finding["review"]["state"] == "CONFIRMED"
    assert finding["review"]["reviewer_id"] == REVIEWER


def test_the_threshold_is_the_taxonomys_and_not_a_local_constant() -> None:
    from veo.observations.risk.taxonomy import RISK_TAXONOMY

    result = apply_publication_gate(
        [reviewed(assessment("as-1", domain=ClaimDomain.MEDICAL), ReviewStage.PENDING_REVIEW)]
    )
    assert result.taxonomy_version == RISK_TAXONOMY.version


# --------------------------------------------------------------------------- #
# Counted, never scored
# --------------------------------------------------------------------------- #


def build_mixed() -> Any:
    return apply_publication_gate(
        [
            reviewed(assessment("as-1", domain=ClaimDomain.MEDICAL), ReviewStage.CONFIRMED),
            reviewed(assessment("as-2", domain=ClaimDomain.PRICING), ReviewStage.PENDING_REVIEW),
            reviewed(
                assessment("as-3", kind=RiskKind.STALENESS, domain=ClaimDomain.GENERAL),
                ReviewStage.PENDING_REVIEW,
            ),
            reviewed(
                assessment(
                    "as-4", domain=ClaimDomain.MEDICAL, verdict=AutomatedVerdict.UNKNOWN
                ),
                ReviewStage.PENDING_REVIEW,
            ),
        ]
    )


def test_the_payload_reports_counts_by_severity() -> None:
    payload = build_mixed().as_customer_payload()
    counts = payload["counts_by_severity"]
    assert set(counts) == {"FATAL", "HIGH", "MEDIUM", "LOW"}
    assert counts["FATAL"]["count"] == 1
    assert counts["LOW"]["count"] == 1


def test_the_payload_contains_no_composite_score_anywhere() -> None:
    payload = build_mixed().as_customer_payload()
    for path, key in walk(payload):
        lowered = str(key).lower()
        for fragment in FORBIDDEN_KEY_FRAGMENTS:
            assert fragment not in lowered, f"{path}: 종합 점수로 읽힐 수 있는 항목입니다"


def test_every_number_in_the_payload_is_a_count() -> None:
    payload = build_mixed().as_customer_payload()
    for value in numbers(payload):
        assert isinstance(value, int), f"{value!r} 은 건수가 아닙니다"
        assert value >= 0


def test_the_payload_states_the_methodology_in_korean() -> None:
    payload = build_mixed().as_customer_payload()
    assert "건수" in payload["methodology_ko"]


def test_counts_by_kind_are_also_counts() -> None:
    payload = build_mixed().as_customer_payload()
    assert payload["counts_by_kind"]["CLAIM_ACCURACY"] == 1


def test_asking_for_an_unknown_assessment_is_an_error() -> None:
    with pytest.raises(KeyError):
        build_mixed().item("as-nope")
