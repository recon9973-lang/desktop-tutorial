"""One risk finding about one sentence an answer engine produced.

Three things make an assessment admissible, and each is enforced at construction rather
than checked later by a caller who might forget:

**It points at the evidence.** :class:`EvidenceRef` names the stored answer, its hash, and
the exact character span assessed. A verdict without them is an assertion — nobody can
re-read the sentence, and nobody can tell whether the answer has since changed. Rule: *an
LLM verdict without the raw answer is inadmissible.*

**It says what decided it.** :class:`DecisionBasis` separates the two, in the record and
not only in prose:

===========================  ===============================================================
``DETERMINISTIC_RULE``       A rule looked at two values and compared them — a cited URL
                             that 404s, a price that differs from the customer's own
                             published page. Reproducible, no model, no ``llm_model``.
``LANGUAGE_MODEL``           A model was asked. The model id, the prompt version and the
                             hash of what it was shown are all recorded, or the record is
                             refused.
``NOT_MEASURED``             Nothing decided it. The verdict is ``UNKNOWN`` and may be
                             nothing else.
===========================  ===============================================================

**It carries no human judgement whatsoever.** There is no review field on this class. An
assessment is what the machine says; what a person says lives in
:mod:`veo.observations.review.decisions` and is attached from outside. That is why
:meth:`ClaimAssessment.to_row` always writes ``review_state=PENDING_REVIEW``: a freshly
computed finding has, by definition, not been reviewed, and there is no code path in this
module that could write anything else.

Severity is never a parameter. It is looked up from :data:`~veo.observations.risk.
taxonomy.RISK_TAXONOMY` from the kind and the subject matter, so a fatal medical claim
cannot be filed as a minor one by a caller in a hurry.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from veo.contracts.enums import ReviewState
from veo.observations.risk.taxonomy import (
    RISK_TAXONOMY,
    ClaimDomain,
    RiskBand,
    RiskKind,
    RiskTaxonomy,
)
from veo.scoring.models import Severity

_HASH_PATTERN = re.compile(r"\A[0-9a-f]{64}\Z")


class AutomatedVerdict(StrEnum):
    """What the machine concluded about the sentence.

    ``UNSUPPORTED`` and ``CONTRADICTED`` are different findings and are never collapsed:
    "the source does not say this" is a gap, "the source says the opposite" is an error,
    and a clinic responds to them differently.

    ``UNKNOWN`` is the value for every unanswerable case — no credential, source
    unreachable, model declined. It is a first-class outcome, not a failure to record.
    """

    UNKNOWN = "UNKNOWN"
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


#: The verdicts that describe something wrong. Only these can become a report finding;
#: a supported claim is a measurement, not a risk.
FINDING_VERDICTS: frozenset[AutomatedVerdict] = frozenset(
    {AutomatedVerdict.UNSUPPORTED, AutomatedVerdict.CONTRADICTED}
)


class DecisionBasis(StrEnum):
    """Who decided: a rule, a model, or nobody."""

    DETERMINISTIC_RULE = "DETERMINISTIC_RULE"
    LANGUAGE_MODEL = "LANGUAGE_MODEL"
    NOT_MEASURED = "NOT_MEASURED"


class MissingEvidenceError(ValueError):
    """An assessment was built without a usable reference to what it assessed."""


class InadmissibleAssessmentError(ValueError):
    """A judgement that does not record enough about itself to be checked later."""


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    """Where the assessed sentence lives.

    The raw answer is not carried here. It is large, it is sensitive, and it sits behind
    the evidence permission; this reference keeps the finding checkable without the
    finding itself becoming the disclosure. ``answer_hash`` is what makes the check
    meaningful — if the stored answer changes, the span no longer belongs to it.
    """

    answer_ref: str
    answer_hash: str
    span_start: int
    span_end: int
    quoted_text: str
    citation_url: str | None = None

    def __post_init__(self) -> None:
        if not self.answer_ref or not self.answer_ref.strip():
            raise MissingEvidenceError(
                "원문 답변 참조가 없습니다. 원문을 다시 열어볼 수 없는 판정은 근거가 아니라 "
                "주장입니다."
            )
        if not _HASH_PATTERN.match(self.answer_hash or ""):
            raise MissingEvidenceError(
                "원문 답변 해시(sha256 64자리)가 없습니다. 해시가 없으면 나중에 이 문장이 "
                "정말 그 답변의 문장이었는지 확인할 수 없습니다."
            )
        if self.span_start < 0 or self.span_end <= self.span_start:
            raise MissingEvidenceError(
                f"평가 구간이 올바르지 않습니다 ({self.span_start}~{self.span_end}). "
                "판정 대상 문장의 위치는 필수입니다."
            )
        if not self.quoted_text.strip():
            raise MissingEvidenceError("평가한 문장이 비어 있습니다.")
        if len(self.quoted_text) != self.span_end - self.span_start:
            raise MissingEvidenceError(
                f"인용한 문장 길이({len(self.quoted_text)})가 평가 구간 길이"
                f"({self.span_end - self.span_start})와 다릅니다. 원문에서 잘라낸 위치가 "
                "틀렸다는 뜻입니다."
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "answer_ref": self.answer_ref,
            "answer_hash": self.answer_hash,
            "span_start": self.span_start,
            "span_end": self.span_end,
            "quoted_text": self.quoted_text,
            "citation_url": self.citation_url,
        }


@dataclass(frozen=True, slots=True)
class AutomatedJudgement:
    """What the machine concluded, and everything needed to reproduce it.

    A ``LANGUAGE_MODEL`` judgement without the model id, the prompt version and the input
    hash cannot be reproduced or audited, so it is refused outright rather than stored as
    a verdict nobody can explain six months later.
    """

    verdict: AutomatedVerdict
    basis: DecisionBasis
    rationale_ko: str
    decided_at: datetime
    rule_id: str | None = None
    llm_model: str | None = None
    llm_prompt_version: str | None = None
    input_hash: str | None = None

    def __post_init__(self) -> None:
        if not self.rationale_ko.strip():
            raise InadmissibleAssessmentError("판정 근거 설명이 비어 있습니다.")

        if self.basis is DecisionBasis.LANGUAGE_MODEL:
            if not self.llm_model:
                raise InadmissibleAssessmentError(
                    "언어모델 판정인데 사용한 모델이 기록되지 않았습니다."
                )
            if not self.llm_prompt_version:
                raise InadmissibleAssessmentError(
                    "언어모델 판정인데 프롬프트 버전이 기록되지 않았습니다. 프롬프트가 바뀌면 "
                    "판정도 바뀌므로 버전 없이는 재현할 수 없습니다."
                )
            if not self.input_hash:
                raise InadmissibleAssessmentError(
                    "언어모델에 무엇을 보여줬는지에 대한 입력 해시가 없습니다."
                )
            if self.rule_id:
                raise InadmissibleAssessmentError(
                    "언어모델 판정에 규칙 식별자가 함께 붙어 있습니다. 둘 중 무엇이 "
                    "판정했는지 모호해집니다."
                )
            return

        if self.llm_model or self.llm_prompt_version or self.input_hash:
            raise InadmissibleAssessmentError(
                "규칙 판정 또는 미측정인데 언어모델 정보가 붙어 있습니다. 규칙이 내린 판정에 "
                "모델 이름이 남으면 사람이 근거를 잘못 읽게 됩니다."
            )

        if self.basis is DecisionBasis.DETERMINISTIC_RULE:
            if not self.rule_id:
                raise InadmissibleAssessmentError(
                    "규칙 판정인데 어떤 규칙이 판정했는지 기록되지 않았습니다."
                )
            return

        # NOT_MEASURED
        if self.verdict is not AutomatedVerdict.UNKNOWN:
            raise InadmissibleAssessmentError(
                f"측정하지 못했는데 판정이 UNKNOWN 이 아닙니다 ({self.verdict.value}). "
                "측정 실패는 판정이 아닙니다."
            )

    @property
    def is_finding(self) -> bool:
        """Whether this judgement describes something wrong."""
        return self.verdict in FINDING_VERDICTS

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "basis": self.basis.value,
            "rationale_ko": self.rationale_ko,
            "decided_at": self.decided_at.isoformat(),
            "rule_id": self.rule_id,
            "llm_model": self.llm_model,
            "llm_prompt_version": self.llm_prompt_version,
            "input_hash": self.input_hash,
        }


@dataclass(frozen=True, slots=True)
class ClaimAssessment:
    """One machine finding about one span of one stored answer.

    Deliberately absent: any field about human review. The class cannot express a
    reviewed state, so no code path in this module can produce one.
    """

    assessment_id: str
    ai_answer_id: str
    kind: RiskKind
    domain: ClaimDomain
    evidence: EvidenceRef
    automated: AutomatedJudgement
    taxonomy: RiskTaxonomy = RISK_TAXONOMY

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, EvidenceRef):
            raise MissingEvidenceError(
                f"{self.assessment_id}: 근거 참조가 없는 판정은 보고서에 올릴 수 없습니다. "
                "원문 답변과 평가 구간을 함께 기록해야 합니다."
            )
        if not self.assessment_id.strip() or not self.ai_answer_id.strip():
            raise InadmissibleAssessmentError("판정 식별자와 답변 식별자는 필수입니다.")

    # ----------------------------------------------------------------- #
    # Severity — read from the taxonomy, never supplied
    # ----------------------------------------------------------------- #

    @property
    def band(self) -> RiskBand:
        return self.taxonomy.band_for(kind=self.kind, domain=self.domain)

    @property
    def severity(self) -> Severity:
        return self.taxonomy.severity_for(kind=self.kind, domain=self.domain)

    @property
    def requires_human_review(self) -> bool:
        return self.taxonomy.requires_human_review(self.band)

    @property
    def claim_text(self) -> str:
        """The exact span assessed — not a paraphrase of it."""
        return self.evidence.quoted_text

    # ----------------------------------------------------------------- #
    # Serialisation
    # ----------------------------------------------------------------- #

    def to_row(self) -> dict[str, Any]:
        """The ``claim_assessments`` columns this finding fills on insert.

        ``review_state`` is always ``PENDING_REVIEW``. A finding this module produced has
        not been reviewed by anyone — that is the whole reason the column is separate from
        ``automated_verdict``. Writing a reviewed state is
        :meth:`veo.observations.review.decisions.ReviewedAssessment.to_row`'s job, and it
        needs a human decision to do it.
        """
        return {
            "ai_answer_id": self.ai_answer_id,
            "claim_text": self.claim_text,
            "assessment_type": self.kind.storage_value,
            "severity": self.severity.value,
            "automated_verdict": self.automated.verdict.value,
            "automated_rationale": self.automated.rationale_ko,
            "llm_model": self.automated.llm_model,
            "llm_prompt_version": self.automated.llm_prompt_version,
            "review_state": ReviewState.PENDING_REVIEW.value,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "ai_answer_id": self.ai_answer_id,
            "kind": self.kind.value,
            "stored_as": self.kind.storage_value,
            "domain": self.domain.value,
            "band": self.band.value,
            "band_label_ko": self.band.label_ko,
            "severity": self.severity.value,
            "claim_text": self.claim_text,
            "evidence": self.evidence.as_dict(),
            "automated": self.automated.as_dict(),
            "taxonomy_version": self.taxonomy.version,
        }


# --------------------------------------------------------------------------- #
# Deterministic rules
# --------------------------------------------------------------------------- #
#
# Everything below decides by comparison, not by asking a model. Each carries a rule id
# so a report can name what compared what.

#: A price in an AI answer disagrees with the price the customer publishes themselves.
RULE_PRICE_CONTRADICTS_OWN_SITE = "RISK-R010"


@dataclass(frozen=True, slots=True)
class PriceOnRecord:
    """A price the customer publishes on their own site, and when VEO last saw it."""

    item_ko: str
    amount_krw: int
    source_url: str
    captured_at: datetime


def judge_price_claim(
    *, claimed_amount_krw: int, on_record: PriceOnRecord, now: datetime
) -> AutomatedJudgement:
    """Compare a price an engine stated with the customer's own published price.

    This is arithmetic, not judgement: two integers either match or they do not. Routing
    it through a language model would add a failure mode and no information, and would
    make a fatal pricing finding depend on a credential VEO may not have.
    """
    captured = on_record.captured_at.date().isoformat()
    if claimed_amount_krw == on_record.amount_krw:
        return AutomatedJudgement(
            verdict=AutomatedVerdict.SUPPORTED,
            basis=DecisionBasis.DETERMINISTIC_RULE,
            rule_id=RULE_PRICE_CONTRADICTS_OWN_SITE,
            rationale_ko=(
                f"'{on_record.item_ko}' 금액이 고객 홈페이지 게시 금액과 같습니다 "
                f"({on_record.amount_krw:,}원, {on_record.source_url}, {captured} 수집)."
            ),
            decided_at=now,
        )
    return AutomatedJudgement(
        verdict=AutomatedVerdict.CONTRADICTED,
        basis=DecisionBasis.DETERMINISTIC_RULE,
        rule_id=RULE_PRICE_CONTRADICTS_OWN_SITE,
        rationale_ko=(
            f"AI 답변의 '{on_record.item_ko}' 금액 {claimed_amount_krw:,}원이 고객 홈페이지 "
            f"게시 금액 {on_record.amount_krw:,}원과 다릅니다 "
            f"({on_record.source_url}, {captured} 수집)."
        ),
        decided_at=now,
    )


__all__ = [
    "FINDING_VERDICTS",
    "RULE_PRICE_CONTRADICTS_OWN_SITE",
    "AutomatedJudgement",
    "AutomatedVerdict",
    "ClaimAssessment",
    "DecisionBasis",
    "EvidenceRef",
    "InadmissibleAssessmentError",
    "MissingEvidenceError",
    "PriceOnRecord",
    "judge_price_claim",
]
