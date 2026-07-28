"""One observation run, and the conditions that make it comparable to another.

An answer from GPT-4 with browsing on is a different measurement from the same question
to the same model with browsing off — different sources, different answer, often a
different conclusion. Pooling them into one "AI 노출률" is the same class of error as
comparing a four-page crawl with a two-hundred-page one: the arithmetic is fine and the
number means nothing.

So every run records exactly what produced it, and aggregation across engines or models
has to be asked for explicitly. The default refuses.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from veo.observations.runs import (
    AccountState,
    MixedConditionsError,
    ObservationRun,
    RunConditions,
    SearchMode,
    aggregate_rate,
    group_by_conditions,
)

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)


def conditions(**overrides: object) -> RunConditions:
    base: dict[str, object] = {
        "engine": "OPENAI",
        "model": "gpt-5",
        "model_version": "2026-05-01",
        "search_mode": SearchMode.BROWSING,
        "account_state": AccountState.ANONYMOUS,
        "locale": "ko-KR",
    }
    base.update(overrides)
    return RunConditions(**base)  # type: ignore[arg-type]


def run(
    *,
    mentioned: bool = True,
    cited: bool = False,
    answer_ref: str | None = "storage://answers/abc",
    prompt_id: str = "p1",
    **condition_overrides: object,
) -> ObservationRun:
    return ObservationRun(
        run_id=f"r-{prompt_id}-{mentioned}-{cited}-{len(condition_overrides)}",
        prompt_id=prompt_id,
        conditions=conditions(**condition_overrides),
        executed_at=NOW,
        raw_answer_ref=answer_ref,
        raw_answer_hash="a" * 64 if answer_ref else None,
        brand_mentioned=mentioned,
        brand_cited=cited,
        latency_ms=1200,
        cost_usd=0.004,
    )


# --------------------------------------------------------------------------- #
# A run must be able to account for itself
# --------------------------------------------------------------------------- #


def test_a_run_records_engine_model_and_search_mode() -> None:
    item = run()
    assert item.conditions.engine == "OPENAI"
    assert item.conditions.model_version
    assert item.conditions.search_mode is SearchMode.BROWSING


def test_a_claimed_mention_requires_a_stored_answer() -> None:
    """Without the answer there is no evidence, only an assertion."""
    with pytest.raises(ValueError, match="원문"):
        run(mentioned=True, answer_ref=None)


def test_a_run_with_no_answer_may_still_record_a_failure() -> None:
    """A provider error is a real outcome and must not be silently dropped."""
    failed = ObservationRun(
        run_id="r-failed",
        prompt_id="p1",
        conditions=conditions(),
        executed_at=NOW,
        raw_answer_ref=None,
        raw_answer_hash=None,
        brand_mentioned=False,
        brand_cited=False,
        error_code="PROVIDER_TIMEOUT",
    )
    assert not failed.is_valid_execution
    assert failed.error_code == "PROVIDER_TIMEOUT"


def test_a_citation_implies_a_mention() -> None:
    """Citing the site without mentioning the brand is not a state we accept silently."""
    with pytest.raises(ValueError, match="인용"):
        run(mentioned=False, cited=True)


def test_runs_are_frozen() -> None:
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        run().brand_mentioned = False  # type: ignore[misc]


def test_cost_and_latency_are_recorded() -> None:
    item = run()
    assert item.latency_ms == 1200
    assert item.cost_usd == pytest.approx(0.004)


# --------------------------------------------------------------------------- #
# Conditions decide what may be pooled
# --------------------------------------------------------------------------- #


def test_identical_conditions_share_a_fingerprint() -> None:
    assert conditions().fingerprint == conditions().fingerprint


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("engine", "PERPLEXITY"),
        ("model", "gpt-4"),
        ("model_version", "2026-01-01"),
        ("search_mode", SearchMode.NO_BROWSING),
        ("account_state", AccountState.SIGNED_IN),
        ("locale", "en-US"),
    ],
)
def test_any_condition_change_changes_the_fingerprint(field: str, value: object) -> None:
    assert conditions().fingerprint != conditions(**{field: value}).fingerprint


def test_grouping_separates_engines() -> None:
    runs = [run(), run(engine="PERPLEXITY")]
    groups = group_by_conditions(runs)
    assert len(groups) == 2


def test_grouping_separates_browsing_from_no_browsing() -> None:
    """Same model, different retrieval — different measurement."""
    runs = [run(), run(search_mode=SearchMode.NO_BROWSING)]
    assert len(group_by_conditions(runs)) == 2


# --------------------------------------------------------------------------- #
# Aggregation refuses to mix by default
# --------------------------------------------------------------------------- #


def test_aggregating_one_condition_group_works() -> None:
    runs = [run(prompt_id=f"p{i}", mentioned=i < 4) for i in range(6)]
    rate = aggregate_rate(runs, label_ko="언급률")
    assert rate.trials == 6
    assert rate.successes == 4


def test_aggregating_across_engines_is_refused() -> None:
    """The headline number a dashboard wants, and the one that means nothing."""
    runs = [run(prompt_id="p1"), run(prompt_id="p2", engine="PERPLEXITY")]
    with pytest.raises(MixedConditionsError, match=r"엔진|조건"):
        aggregate_rate(runs, label_ko="언급률")


def test_mixing_can_be_requested_explicitly_and_is_labelled() -> None:
    runs = [run(prompt_id="p1"), run(prompt_id="p2", engine="PERPLEXITY")]
    rate = aggregate_rate(runs, label_ko="언급률", allow_mixed_conditions=True)
    assert rate.trials == 2
    assert "엔진" in rate.qualifier_ko or "조건" in rate.qualifier_ko


def test_failed_runs_are_excluded_from_the_denominator() -> None:
    """A timeout is not a 'not mentioned'. It is an absence of measurement."""
    good = [run(prompt_id=f"p{i}", mentioned=True) for i in range(3)]
    failed = ObservationRun(
        run_id="r-x",
        prompt_id="p9",
        conditions=conditions(),
        executed_at=NOW,
        raw_answer_ref=None,
        raw_answer_hash=None,
        brand_mentioned=False,
        brand_cited=False,
        error_code="PROVIDER_TIMEOUT",
    )
    rate = aggregate_rate([*good, failed], label_ko="언급률")
    assert rate.trials == 3, "the failed run must not count as a run where we were absent"
    assert rate.successes == 3


def test_aggregating_nothing_is_data_absent_not_zero() -> None:
    rate = aggregate_rate([], label_ko="언급률")
    assert rate.value is None
    assert "데이터 없음" in rate.summary_ko


def test_the_rate_carries_the_sampling_rules_from_the_methodology() -> None:
    """Three runs is directional, not a percentage to one decimal place."""
    runs = [run(prompt_id=f"p{i}", mentioned=i < 2) for i in range(3)]
    rate = aggregate_rate(runs, label_ko="언급률")
    assert "방향" in rate.qualifier_ko


# --------------------------------------------------------------------------- #
# Serialisation keeps everything an auditor needs
# --------------------------------------------------------------------------- #


def test_a_run_serialises_with_its_conditions_and_evidence() -> None:
    import json

    payload = json.loads(json.dumps(run().as_dict(), ensure_ascii=False))
    for key in ("run_id", "prompt_id", "executed_at", "raw_answer_ref", "raw_answer_hash"):
        assert key in payload, key
    for key in ("engine", "model", "model_version", "search_mode", "account_state"):
        assert key in payload["conditions"], key


def test_the_raw_answer_is_referenced_not_inlined() -> None:
    """Raw AI answers are sensitive and large; the run holds a pointer and a hash."""
    payload = run().as_dict()
    assert payload["raw_answer_ref"].startswith("storage://")
    assert len(payload["raw_answer_hash"]) == 64
    assert "answer_text" not in payload
