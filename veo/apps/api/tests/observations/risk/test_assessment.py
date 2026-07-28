"""A claim assessment, and what makes one admissible.

Two invariants dominate this file:

* An assessment without a reference to the stored answer and the exact span assessed is
  refused at construction. A verdict nobody can re-read is an assertion, not evidence.
* The machine's judgement and the human's review are two different facts and live in two
  different places, all the way down to the row.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from risk_support import CLAIM_TEXT, NOW, assessment, evidence, judgement

from veo.contracts.enums import ReviewState
from veo.observations.risk.assessment import (
    AutomatedJudgement,
    AutomatedVerdict,
    ClaimAssessment,
    DecisionBasis,
    EvidenceRef,
    InadmissibleAssessmentError,
    MissingEvidenceError,
    PriceOnRecord,
    judge_price_claim,
)
from veo.observations.risk.taxonomy import ClaimDomain, RiskBand, RiskKind
from veo.scoring.models import Severity

#: Columns ``claim_assessments`` actually has. A row this module builds may not invent
#: a column, because this worker may not add one.
CLAIM_ASSESSMENT_COLUMNS = frozenset(
    {
        "ai_answer_id",
        "claim_text",
        "assessment_type",
        "severity",
        "automated_verdict",
        "automated_rationale",
        "llm_model",
        "llm_prompt_version",
        "review_state",
        "reviewed_by",
        "reviewer_note",
        "supporting_citation_id",
    }
)


# --------------------------------------------------------------------------- #
# Evidence
# --------------------------------------------------------------------------- #


def test_an_assessment_without_an_evidence_reference_is_refused() -> None:
    with pytest.raises(MissingEvidenceError):
        assessment(evidence=None)


def test_evidence_must_name_the_stored_answer() -> None:
    with pytest.raises(MissingEvidenceError, match="원문"):
        evidence(answer_ref="  ")


def test_evidence_must_carry_the_answer_hash_so_the_span_stays_checkable() -> None:
    with pytest.raises(MissingEvidenceError, match="해시"):
        evidence(answer_hash="short")


def test_the_span_must_actually_be_a_span() -> None:
    with pytest.raises(MissingEvidenceError, match="구간"):
        evidence(span_start=50, span_end=10)


def test_the_quoted_text_must_match_the_span_it_claims() -> None:
    with pytest.raises(MissingEvidenceError, match="구간"):
        evidence(span_start=0, span_end=3, quoted_text=CLAIM_TEXT)


def test_an_empty_quotation_is_not_an_assessed_span() -> None:
    with pytest.raises(MissingEvidenceError):
        evidence(span_start=0, span_end=0, quoted_text="")


# --------------------------------------------------------------------------- #
# Rules versus models
# --------------------------------------------------------------------------- #


def test_a_model_judgement_must_name_the_model_and_the_prompt_version() -> None:
    with pytest.raises(InadmissibleAssessmentError, match="모델"):
        judgement(llm_model=None)
    with pytest.raises(InadmissibleAssessmentError, match="프롬프트"):
        judgement(llm_prompt_version=None)


def test_a_model_judgement_must_record_the_hash_of_what_it_was_shown() -> None:
    with pytest.raises(InadmissibleAssessmentError, match="입력"):
        judgement(input_hash=None)


def test_a_rule_judgement_may_not_claim_a_model_produced_it() -> None:
    with pytest.raises(InadmissibleAssessmentError, match="규칙"):
        judgement(basis=DecisionBasis.DETERMINISTIC_RULE, rule_id="RISK-R010")


def test_a_rule_judgement_must_name_its_rule() -> None:
    with pytest.raises(InadmissibleAssessmentError, match="규칙"):
        judgement(
            basis=DecisionBasis.DETERMINISTIC_RULE,
            rule_id=None,
            llm_model=None,
            llm_prompt_version=None,
            input_hash=None,
        )


def test_an_unmeasured_judgement_may_only_be_unknown() -> None:
    with pytest.raises(InadmissibleAssessmentError, match="UNKNOWN"):
        judgement(
            verdict=AutomatedVerdict.CONTRADICTED,
            basis=DecisionBasis.NOT_MEASURED,
            llm_model=None,
            llm_prompt_version=None,
            input_hash=None,
        )


def test_the_basis_says_plainly_whether_a_rule_or_a_model_decided() -> None:
    rule = judge_price_claim(
        claimed_amount_krw=1_200_000,
        on_record=PriceOnRecord(
            item_ko="가상 시술 A",
            amount_krw=900_000,
            source_url="https://example.invalid/fictional-clinic/price",
            captured_at=NOW,
        ),
        now=NOW,
    )
    assert rule.basis is DecisionBasis.DETERMINISTIC_RULE
    assert rule.verdict is AutomatedVerdict.CONTRADICTED
    assert rule.llm_model is None
    assert rule.rule_id


def test_a_price_matching_the_customers_own_site_is_supported_by_rule() -> None:
    on_record = PriceOnRecord(
        item_ko="가상 시술 A",
        amount_krw=900_000,
        source_url="https://example.invalid/fictional-clinic/price",
        captured_at=NOW,
    )
    result = judge_price_claim(claimed_amount_krw=900_000, on_record=on_record, now=NOW)
    assert result.verdict is AutomatedVerdict.SUPPORTED
    assert result.basis is DecisionBasis.DETERMINISTIC_RULE


# --------------------------------------------------------------------------- #
# Severity
# --------------------------------------------------------------------------- #


def test_severity_comes_from_the_taxonomy_and_not_from_the_caller() -> None:
    medical = assessment(domain=ClaimDomain.MEDICAL)
    assert medical.band is RiskBand.FATAL
    assert medical.severity is Severity.BLOCKER

    general = assessment(kind=RiskKind.STALENESS, domain=ClaimDomain.GENERAL)
    assert general.band is not RiskBand.FATAL


def test_an_assessment_cannot_be_handed_a_severity() -> None:
    with pytest.raises(TypeError):
        ClaimAssessment(  # type: ignore[call-arg]
            assessment_id="as-9",
            ai_answer_id="ans-9",
            kind=RiskKind.CLAIM_ACCURACY,
            domain=ClaimDomain.MEDICAL,
            evidence=evidence(),
            automated=judgement(),
            severity=Severity.INFO,
        )


# --------------------------------------------------------------------------- #
# The row
# --------------------------------------------------------------------------- #


def test_the_row_keeps_the_machine_verdict_and_the_review_state_apart() -> None:
    row = assessment().to_row()
    assert row["automated_verdict"] == AutomatedVerdict.CONTRADICTED.value
    assert row["review_state"] == ReviewState.PENDING_REVIEW.value
    assert row["llm_model"] == "fictional-judge-1"
    assert row["llm_prompt_version"] == "entailment/2026-07-28.1"


def test_a_fresh_machine_assessment_is_never_written_as_reviewed() -> None:
    for verdict in AutomatedVerdict:
        row = assessment(automated=judgement(verdict=verdict)).to_row()
        assert row["review_state"] != ReviewState.HUMAN_CONFIRMED.value


def test_the_row_invents_no_column_this_worker_may_not_add() -> None:
    assert set(assessment().to_row()) <= CLAIM_ASSESSMENT_COLUMNS


def test_the_row_stores_a_type_the_schema_accepts() -> None:
    row = assessment(kind=RiskKind.RECOMMENDATION_EXCLUSION).to_row()
    assert row["assessment_type"] == "RECOMMENDATION"


def test_the_assessed_span_is_what_gets_stored_as_the_claim() -> None:
    row = assessment().to_row()
    assert row["claim_text"] == CLAIM_TEXT


def test_an_assessment_is_frozen() -> None:
    item = assessment()
    with pytest.raises(FrozenInstanceError):
        item.assessment_id = "tampered"  # type: ignore[misc]


def test_the_serialised_form_carries_both_facts_separately() -> None:
    payload = assessment().as_dict()
    assert payload["automated"]["verdict"] == AutomatedVerdict.CONTRADICTED.value
    assert payload["automated"]["basis"] == DecisionBasis.LANGUAGE_MODEL.value
    assert payload["evidence"]["answer_ref"] == "storage://ai-answers/0001"
    assert "review" not in payload["automated"]


def test_an_evidence_reference_survives_round_tripping_to_a_dict() -> None:
    reference = evidence()
    assert reference.as_dict()["span_end"] == reference.span_end
    assert isinstance(reference, EvidenceRef)


def test_a_judgement_is_a_frozen_record() -> None:
    item = judgement()
    assert isinstance(item, AutomatedJudgement)
    with pytest.raises(FrozenInstanceError):
        item.verdict = AutomatedVerdict.SUPPORTED  # type: ignore[misc]
