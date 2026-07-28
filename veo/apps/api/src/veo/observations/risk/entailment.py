"""Does the cited source actually support the sentence?

An answer engine citing a page is not the same as the page saying the thing. The gap
between the two is where the expensive errors live: a clinic's cited "success rate" that
appears nowhere in the linked document is a medical-advertising problem the moment
anybody reads the answer.

The check runs in two halves, and the split is deliberate:

**The deterministic half runs first and needs no credential.** No citation at all, or a
citation that 404s, settles the question by rule — there is nothing for a model to read.
A source VEO could not fetch settles nothing, and returns ``UNKNOWN``: "we could not read
it" is not "it does not support the claim", and conflating them would manufacture
findings out of network trouble.

**The model half needs a credential, and without one the answer is ``UNKNOWN``.** Not a
keyword-overlap heuristic, not a similarity threshold with a confident-looking number. A
guess about whether a source backs a medical sentence is worse than an admitted gap: the
gap gets filled, the guess gets published. Every model verdict records the model id, the
prompt version and a hash of exactly what the model was shown, so the same judgement can
be re-run and disputed later.

The model is reached through :class:`EntailmentModel`, a protocol. This module makes no
network calls, holds no credential, and never sees a secret; an adapter that does lives
behind the protocol and reports its own :class:`~veo.contracts.enums.ProviderState`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from veo.contracts.enums import ProviderState
from veo.observations.risk.assessment import (
    AutomatedJudgement,
    AutomatedVerdict,
    DecisionBasis,
)

#: Bump when the entailment prompt text changes. A judgement made under a different
#: prompt is a different judgement, and the version is what makes that visible.
ENTAILMENT_PROMPT_VERSION = "entailment/2026-07-28.1"

#: No citation was attached to the sentence at all.
RULE_NO_CITATION = "ENT-R001"

#: The cited URL does not exist.
RULE_CITATION_NOT_FOUND = "ENT-R002"


class SourceFetchStatus(StrEnum):
    """What happened when VEO tried to read the cited page.

    ``NOT_FOUND`` is a fact about the citation — the page is gone, so it supports
    nothing. The other failures are facts about VEO's attempt, and decide nothing.
    """

    OK = "OK"
    NOT_FOUND = "NOT_FOUND"
    UNREACHABLE = "UNREACHABLE"
    BLOCKED = "BLOCKED"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"


class ModelEntailmentVerdict(StrEnum):
    """What a language model may conclude. Narrower than the model's own vocabulary.

    ``UNKNOWN`` is included so a model that cannot tell has somewhere honest to land
    instead of rounding itself to ``UNSUPPORTED``.
    """

    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


_MODEL_VERDICTS: dict[ModelEntailmentVerdict, AutomatedVerdict] = {
    ModelEntailmentVerdict.SUPPORTED: AutomatedVerdict.SUPPORTED,
    ModelEntailmentVerdict.UNSUPPORTED: AutomatedVerdict.UNSUPPORTED,
    ModelEntailmentVerdict.CONTRADICTED: AutomatedVerdict.CONTRADICTED,
    ModelEntailmentVerdict.UNKNOWN: AutomatedVerdict.UNKNOWN,
}


@dataclass(frozen=True, slots=True)
class CitedSource:
    """A page an answer cited, and what VEO managed to read from it."""

    url: str
    fetch_status: SourceFetchStatus
    text: str | None
    fetched_at: datetime | None = None

    @property
    def has_body(self) -> bool:
        return self.fetch_status is SourceFetchStatus.OK and bool(
            self.text and self.text.strip()
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "fetch_status": self.fetch_status.value,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "has_body": self.has_body,
        }


@dataclass(frozen=True, slots=True)
class EntailmentRequest:
    """Exactly what a model is shown. Nothing here is invented by this module."""

    claim_text: str
    source_url: str
    source_text: str
    prompt_version: str
    input_hash: str


class EntailmentModel(Protocol):
    """The seam a language model sits behind.

    ``state`` is checked before ``judge`` is ever called, so a deployment with no
    credential makes no outbound request and produces no verdict.
    """

    @property
    def state(self) -> ProviderState: ...

    @property
    def model_id(self) -> str: ...

    @property
    def prompt_version(self) -> str: ...

    def judge(self, request: EntailmentRequest) -> ModelEntailmentVerdict: ...


def entailment_input_hash(*, claim_text: str, source_url: str, source_text: str) -> str:
    """A stable fingerprint of what a judgement was made from.

    Canonical JSON rather than concatenation: without a separator, changing where the
    claim ends and the source begins would leave the hash identical, and the hash exists
    precisely to notice that the inputs changed.
    """
    payload = json.dumps(
        {
            "claim_text": claim_text,
            "source_url": source_url,
            "source_text": source_text,
            "prompt_version": ENTAILMENT_PROMPT_VERSION,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def check_entailment(
    *,
    claim_text: str,
    source: CitedSource | None,
    model: EntailmentModel | None,
    now: datetime,
) -> AutomatedJudgement:
    """Decide whether the cited source supports the sentence, or admit that nobody did.

    Order matters. The rules are tried first because they are free, reproducible, and
    available without a credential; the model is only reached for the question a rule
    cannot answer.
    """
    # --- rules ---------------------------------------------------------- #
    if source is None or not source.url.strip():
        return AutomatedJudgement(
            verdict=AutomatedVerdict.UNSUPPORTED,
            basis=DecisionBasis.DETERMINISTIC_RULE,
            rule_id=RULE_NO_CITATION,
            rationale_ko=(
                "이 문장에는 인용 출처가 붙어 있지 않습니다. 확인할 근거가 없으므로 "
                "'뒷받침 없음' 입니다."
            ),
            decided_at=now,
        )

    if source.fetch_status is SourceFetchStatus.NOT_FOUND:
        return AutomatedJudgement(
            verdict=AutomatedVerdict.UNSUPPORTED,
            basis=DecisionBasis.DETERMINISTIC_RULE,
            rule_id=RULE_CITATION_NOT_FOUND,
            rationale_ko=(
                f"인용된 주소가 존재하지 않습니다(404): {source.url}. "
                "없는 문서는 어떤 문장도 뒷받침하지 못합니다."
            ),
            decided_at=now,
        )

    if not source.has_body:
        return _not_measured(
            now,
            f"인용된 문서를 읽지 못했습니다({source.fetch_status.value}: {source.url}). "
            "읽지 못한 것은 '뒷받침하지 않는다'는 뜻이 아니므로 판정하지 않습니다.",
        )

    # --- the model ------------------------------------------------------ #
    if model is None:
        return _not_measured(
            now,
            "함의 판정에 사용할 언어모델이 설정되어 있지 않습니다. 자격증명 없이 추측하지 "
            "않고 미확인으로 남깁니다.",
        )

    state = model.state
    if state is not ProviderState.ENABLED:
        return _not_measured(
            now,
            f"함의 판정 제공자를 사용할 수 없습니다({state.value}). 자격증명 문제일 때 "
            "그럴듯한 판정을 만들어내지 않고 미확인으로 남깁니다.",
        )

    # ``has_body`` already established the text is present; this rebinding is for mypy.
    source_text = source.text or ""
    input_hash = entailment_input_hash(
        claim_text=claim_text, source_url=source.url, source_text=source_text
    )
    request = EntailmentRequest(
        claim_text=claim_text,
        source_url=source.url,
        source_text=source_text,
        prompt_version=model.prompt_version,
        input_hash=input_hash,
    )

    try:
        model_verdict = model.judge(request)
    except Exception:
        # A provider failure is an absence of measurement. Deriving a verdict from it
        # would make VEO's findings worse exactly when its infrastructure is worst.
        return _not_measured(
            now,
            "함의 판정 호출이 실패했습니다. 실패는 판정이 아니므로 미확인으로 남깁니다.",
        )

    return AutomatedJudgement(
        verdict=_MODEL_VERDICTS[model_verdict],
        basis=DecisionBasis.LANGUAGE_MODEL,
        rationale_ko=_model_rationale_ko(model_verdict, source.url),
        decided_at=now,
        llm_model=model.model_id,
        llm_prompt_version=model.prompt_version,
        input_hash=input_hash,
    )


def _not_measured(now: datetime, rationale_ko: str) -> AutomatedJudgement:
    return AutomatedJudgement(
        verdict=AutomatedVerdict.UNKNOWN,
        basis=DecisionBasis.NOT_MEASURED,
        rationale_ko=rationale_ko,
        decided_at=now,
    )


def _model_rationale_ko(verdict: ModelEntailmentVerdict, url: str) -> str:
    return {
        ModelEntailmentVerdict.SUPPORTED: (
            f"인용 문서({url})에 이 문장을 뒷받침하는 내용이 있다고 판정했습니다. "
            "자동 판정이며 사람 검수로 확정됩니다."
        ),
        ModelEntailmentVerdict.UNSUPPORTED: (
            f"인용 문서({url})에서 이 문장을 뒷받침하는 내용을 찾지 못했습니다. "
            "자동 판정이며 사람 검수로 확정됩니다."
        ),
        ModelEntailmentVerdict.CONTRADICTED: (
            f"인용 문서({url})의 내용이 이 문장과 어긋난다고 판정했습니다. "
            "자동 판정이며 사람 검수로 확정됩니다."
        ),
        ModelEntailmentVerdict.UNKNOWN: (
            f"인용 문서({url})만으로는 판단할 수 없다고 응답했습니다. "
            "추측 대신 미확인으로 남깁니다."
        ),
    }[verdict]


__all__ = [
    "ENTAILMENT_PROMPT_VERSION",
    "RULE_CITATION_NOT_FOUND",
    "RULE_NO_CITATION",
    "CitedSource",
    "EntailmentModel",
    "EntailmentRequest",
    "ModelEntailmentVerdict",
    "SourceFetchStatus",
    "check_entailment",
    "entailment_input_hash",
]
