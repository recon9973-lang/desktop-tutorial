"""Builders shared by the review tests.

Every business named here is fictional and says so. A fixture that reads like a real
finding about a real clinic is one copy-paste away from a customer report.
"""

from __future__ import annotations

from datetime import UTC, datetime

from veo.observations.risk.assessment import (
    AutomatedJudgement,
    AutomatedVerdict,
    ClaimAssessment,
    DecisionBasis,
    EvidenceRef,
)
from veo.observations.risk.taxonomy import ClaimDomain, RiskKind

NOW = datetime(2026, 7, 28, 9, 0, tzinfo=UTC)

FICTIONAL_CLINIC = "가상 하늘별의원(가상 사례)"
CLAIM_TEXT = f"{FICTIONAL_CLINIC}은 24시간 응급 수술을 상시 운영합니다."

REVIEWER = "reviewer-01"
OTHER_REVIEWER = "reviewer-02"


def evidence(**overrides: object) -> EvidenceRef:
    base: dict[str, object] = {
        "answer_ref": "storage://ai-answers/0001",
        "answer_hash": "b" * 64,
        "span_start": 10,
        "span_end": 10 + len(CLAIM_TEXT),
        "quoted_text": CLAIM_TEXT,
        "citation_url": "https://example.invalid/fictional-clinic",
    }
    base.update(overrides)
    return EvidenceRef(**base)  # type: ignore[arg-type]


def judgement(**overrides: object) -> AutomatedJudgement:
    base: dict[str, object] = {
        "verdict": AutomatedVerdict.CONTRADICTED,
        "basis": DecisionBasis.LANGUAGE_MODEL,
        "rationale_ko": "인용된 문서에 24시간 응급 수술 운영을 뒷받침하는 문장이 없습니다.",
        "decided_at": NOW,
        "llm_model": "fictional-judge-1",
        "llm_prompt_version": "entailment/2026-07-28.1",
        "input_hash": "c" * 64,
    }
    base.update(overrides)
    return AutomatedJudgement(**base)  # type: ignore[arg-type]


def assessment(
    assessment_id: str = "as-0001",
    *,
    kind: RiskKind = RiskKind.CLAIM_ACCURACY,
    domain: ClaimDomain = ClaimDomain.MEDICAL,
    claim_text: str = CLAIM_TEXT,
    verdict: AutomatedVerdict = AutomatedVerdict.CONTRADICTED,
) -> ClaimAssessment:
    return ClaimAssessment(
        assessment_id=assessment_id,
        ai_answer_id="ans-0001",
        kind=kind,
        domain=domain,
        evidence=evidence(quoted_text=claim_text, span_end=10 + len(claim_text)),
        automated=judgement(verdict=verdict),
    )
