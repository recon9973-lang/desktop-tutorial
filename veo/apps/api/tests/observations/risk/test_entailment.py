"""Does the cited source actually support the sentence?

The rule that shapes this module: **with no usable language model, the answer is
``UNKNOWN``.** Not "probably supported", not a keyword-overlap heuristic dressed up as a
verdict. A guess about whether a hospital's cited source backs a medical sentence is
worse than an admitted gap, because a gap gets filled and a guess gets published.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from veo.contracts.enums import ProviderState
from veo.observations.risk.assessment import AutomatedVerdict, DecisionBasis
from veo.observations.risk.entailment import (
    ENTAILMENT_PROMPT_VERSION,
    CitedSource,
    EntailmentRequest,
    ModelEntailmentVerdict,
    SourceFetchStatus,
    check_entailment,
    entailment_input_hash,
)

NOW = datetime(2026, 7, 28, 9, 0, tzinfo=UTC)

CLAIM = "가상 하늘별의원(가상 사례)은 24시간 응급 수술을 상시 운영합니다."
SOURCE_TEXT = "가상 하늘별의원(가상 사례) 진료 안내: 평일 09:00-18:00, 토요일 09:00-13:00."


class RecordingModel:
    """A stand-in judge. Records what it was asked so the test can inspect it."""

    def __init__(
        self,
        verdict: ModelEntailmentVerdict = ModelEntailmentVerdict.UNSUPPORTED,
        *,
        state: ProviderState = ProviderState.ENABLED,
        explode: bool = False,
    ) -> None:
        self._verdict = verdict
        self._state = state
        self._explode = explode
        self.requests: list[EntailmentRequest] = []

    @property
    def state(self) -> ProviderState:
        return self._state

    @property
    def model_id(self) -> str:
        return "fictional-judge-1"

    @property
    def prompt_version(self) -> str:
        return ENTAILMENT_PROMPT_VERSION

    def judge(self, request: EntailmentRequest) -> ModelEntailmentVerdict:
        self.requests.append(request)
        if self._explode:
            raise RuntimeError("provider exploded")
        return self._verdict


def source(**overrides: object) -> CitedSource:
    base: dict[str, object] = {
        "url": "https://example.invalid/fictional-clinic/hours",
        "fetch_status": SourceFetchStatus.OK,
        "text": SOURCE_TEXT,
        "fetched_at": NOW,
    }
    base.update(overrides)
    return CitedSource(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# No credential
# --------------------------------------------------------------------------- #


def test_with_no_model_at_all_the_answer_is_unknown_and_not_a_guess() -> None:
    result = check_entailment(claim_text=CLAIM, source=source(), model=None, now=NOW)
    assert result.verdict is AutomatedVerdict.UNKNOWN
    assert result.basis is DecisionBasis.NOT_MEASURED
    assert result.llm_model is None
    assert result.llm_prompt_version is None


def test_with_a_model_that_has_no_credential_the_answer_is_unknown() -> None:
    model = RecordingModel(state=ProviderState.DISABLED_NO_CREDENTIAL)
    result = check_entailment(claim_text=CLAIM, source=source(), model=model, now=NOW)
    assert result.verdict is AutomatedVerdict.UNKNOWN
    assert result.basis is DecisionBasis.NOT_MEASURED
    assert model.requests == [], "자격증명이 없는데 외부 호출이 나갔습니다"
    assert "자격증명" in result.rationale_ko


@pytest.mark.parametrize(
    "state",
    [
        ProviderState.DISABLED_INVALID_CREDENTIAL,
        ProviderState.DISABLED_BY_CONFIG,
        ProviderState.CIRCUIT_OPEN,
    ],
)
def test_any_unusable_provider_state_yields_unknown(state: ProviderState) -> None:
    model = RecordingModel(state=state)
    result = check_entailment(claim_text=CLAIM, source=source(), model=model, now=NOW)
    assert result.verdict is AutomatedVerdict.UNKNOWN
    assert model.requests == []


def test_a_provider_that_raises_produces_unknown_rather_than_a_verdict() -> None:
    model = RecordingModel(explode=True)
    result = check_entailment(claim_text=CLAIM, source=source(), model=model, now=NOW)
    assert result.verdict is AutomatedVerdict.UNKNOWN
    assert result.basis is DecisionBasis.NOT_MEASURED


# --------------------------------------------------------------------------- #
# The deterministic half
# --------------------------------------------------------------------------- #


def test_a_missing_citation_is_decided_by_rule_not_by_a_model() -> None:
    model = RecordingModel()
    result = check_entailment(claim_text=CLAIM, source=None, model=model, now=NOW)
    assert result.basis is DecisionBasis.DETERMINISTIC_RULE
    assert result.verdict is AutomatedVerdict.UNSUPPORTED
    assert result.rule_id
    assert model.requests == []


def test_a_citation_that_404s_is_decided_by_rule() -> None:
    model = RecordingModel()
    result = check_entailment(
        claim_text=CLAIM,
        source=source(fetch_status=SourceFetchStatus.NOT_FOUND, text=None),
        model=model,
        now=NOW,
    )
    assert result.basis is DecisionBasis.DETERMINISTIC_RULE
    assert result.verdict is AutomatedVerdict.UNSUPPORTED
    assert model.requests == []


@pytest.mark.parametrize(
    "status",
    [
        SourceFetchStatus.UNREACHABLE,
        SourceFetchStatus.BLOCKED,
        SourceFetchStatus.NOT_ATTEMPTED,
    ],
)
def test_a_source_we_could_not_read_is_unknown_not_unsupported(
    status: SourceFetchStatus,
) -> None:
    # "We could not fetch it" is not "it does not support the claim".
    result = check_entailment(
        claim_text=CLAIM,
        source=source(fetch_status=status, text=None),
        model=RecordingModel(),
        now=NOW,
    )
    assert result.verdict is AutomatedVerdict.UNKNOWN


def test_an_empty_source_body_is_unknown() -> None:
    result = check_entailment(
        claim_text=CLAIM,
        source=source(text="   "),
        model=RecordingModel(),
        now=NOW,
    )
    assert result.verdict is AutomatedVerdict.UNKNOWN


# --------------------------------------------------------------------------- #
# The model half
# --------------------------------------------------------------------------- #


def test_a_model_verdict_records_the_model_the_prompt_version_and_the_input_hash() -> None:
    model = RecordingModel(ModelEntailmentVerdict.UNSUPPORTED)
    result = check_entailment(claim_text=CLAIM, source=source(), model=model, now=NOW)

    assert result.basis is DecisionBasis.LANGUAGE_MODEL
    assert result.verdict is AutomatedVerdict.UNSUPPORTED
    assert result.llm_model == "fictional-judge-1"
    assert result.llm_prompt_version == ENTAILMENT_PROMPT_VERSION
    assert result.input_hash and len(result.input_hash) == 64


def test_the_model_is_shown_the_claim_and_the_source_and_nothing_invented() -> None:
    model = RecordingModel()
    check_entailment(claim_text=CLAIM, source=source(), model=model, now=NOW)
    request = model.requests[0]
    assert request.claim_text == CLAIM
    assert request.source_text == SOURCE_TEXT
    assert request.source_url == "https://example.invalid/fictional-clinic/hours"
    assert request.prompt_version == ENTAILMENT_PROMPT_VERSION


def test_the_input_hash_is_stable_for_the_same_inputs() -> None:
    first = entailment_input_hash(
        claim_text=CLAIM, source_url="https://example.invalid/a", source_text=SOURCE_TEXT
    )
    second = entailment_input_hash(
        claim_text=CLAIM, source_url="https://example.invalid/a", source_text=SOURCE_TEXT
    )
    assert first == second


def test_the_input_hash_changes_when_the_claim_changes() -> None:
    first = entailment_input_hash(
        claim_text=CLAIM, source_url="https://example.invalid/a", source_text=SOURCE_TEXT
    )
    second = entailment_input_hash(
        claim_text=CLAIM + "!", source_url="https://example.invalid/a", source_text=SOURCE_TEXT
    )
    assert first != second


def test_a_model_that_cannot_tell_returns_unknown_rather_than_unsupported() -> None:
    model = RecordingModel(ModelEntailmentVerdict.UNKNOWN)
    result = check_entailment(claim_text=CLAIM, source=source(), model=model, now=NOW)
    assert result.verdict is AutomatedVerdict.UNKNOWN
    # It was measured — a model looked and declined — so the model is still on the record.
    assert result.llm_model == "fictional-judge-1"


def test_a_model_verdict_is_still_only_an_automated_verdict() -> None:
    model = RecordingModel(ModelEntailmentVerdict.CONTRADICTED)
    result = check_entailment(claim_text=CLAIM, source=source(), model=model, now=NOW)
    assert result.verdict is AutomatedVerdict.CONTRADICTED
    assert not hasattr(result, "review_state")
