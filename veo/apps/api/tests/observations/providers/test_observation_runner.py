"""Executing a prompt set against real engines, and refusing to overstate the result.

The failure this suite is built around: a run that claims a mention it cannot evidence.
There are four routes to it and each has a test —

* a provider that never answered (no credential, timeout) being counted as "not mentioned";
* a citation asserted where the API exposed no citation objects;
* a mention recorded when the answer could not be stored, leaving nothing to check;
* a budget-truncated pass reported as though every planned run had happened.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import SecretStr
from tests.observations.providers.synthetic import (
    BRAND_DOMAIN,
    BRAND_PROFILE,
    OPENAI_MODEL_VERSION,
    RIVAL_DOMAIN,
    SYNTHETIC_PRICES,
    balanced_prompt_set,
    conditions,
    gemini_payload,
    mentioning_answer,
    openai_payload,
    silent_answer,
)

from veo.contracts.enums import ProviderState
from veo.observations.attribution import DisambiguatingMentionDetector
from veo.observations.providers.base import PriceTable
from veo.observations.providers.gemini import GeminiAnswerProvider
from veo.observations.providers.openai import OpenAIAnswerProvider
from veo.observations.providers.registry import ProviderRegistry
from veo.observations.providers.storage import (
    AnswerRecordKey,
    InMemoryAnswerStore,
    RecordedAnswer,
    StoredAnswer,
)
from veo.observations.runner import (
    MIN_REPETITIONS,
    ObservationRunner,
    RepetitionFloorError,
    StopReason,
)
from veo.observations.runs import MixedConditionsError, aggregate_rate

NOW = datetime(2026, 7, 28, 9, 0, tzinfo=UTC)
KEY = SecretStr("synthetic-openai-key")

#: 1,000 input + 500 output tokens against the synthetic price table.
COST_PER_CALL = 1_000 / 1_000_000 * 1.0 + 500 / 1_000_000 * 10.0


class SafeMonotonic:
    """Thread-safe fixed-step clock, so latency assertions do not race."""

    def __init__(self, step: float = 0.25) -> None:
        self._step = step
        self._value = 0.0
        self._lock = threading.Lock()

    def __call__(self) -> float:
        with self._lock:
            current = self._value
            self._value += self._step
            return current


def provider(
    handler: object,
    *,
    credential: SecretStr | None = KEY,
    price_table: PriceTable = SYNTHETIC_PRICES,
    monotonic: object | None = None,
) -> OpenAIAnswerProvider:
    return OpenAIAnswerProvider(
        credential=credential,
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        price_table=price_table,
        monotonic=monotonic or SafeMonotonic(),  # type: ignore[arg-type]
        sleep=lambda seconds: None,
        now=lambda: NOW,
    )


def runner(
    handler: object,
    *,
    store: InMemoryAnswerStore | None = None,
    budget_usd: float | None = None,
    max_concurrency: int = 1,
    credential: SecretStr | None = KEY,
    price_table: PriceTable = SYNTHETIC_PRICES,
    monotonic: object | None = None,
) -> ObservationRunner:
    return ObservationRunner(
        registry=ProviderRegistry(
            [
                provider(
                    handler,
                    credential=credential,
                    price_table=price_table,
                    monotonic=monotonic,
                )
            ]
        ),
        store=store or InMemoryAnswerStore(),
        detector=DisambiguatingMentionDetector(BRAND_PROFILE),
        # 이 스위트가 재는 것은 실행기의 **논리**이지 시계가 아니다. 간격을 0 으로
        # 두어 실제로 자지 않게 한다. 간격 자체는
        # `tests/observations/test_repetition_pacing.py` 가 가짜 시계로 잰다.
        repetition_interval=timedelta(0),
        max_concurrency=max_concurrency,
        budget_usd=budget_usd,
        clock=lambda: NOW,
    )


def answering(
    text: str | None = None, *, citation_urls: tuple[str, ...] = ()
) -> object:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=openai_payload(text=text, citation_urls=citation_urls)
        )

    return handler


def counting(handler: object) -> tuple[object, list[int]]:
    """Wrap a handler so the suite can assert how many times the transport was used."""
    calls = [0]
    lock = threading.Lock()

    def wrapped(request: httpx.Request) -> httpx.Response:
        with lock:
            calls[0] += 1
        return handler(request)  # type: ignore[operator, no-any-return]

    return wrapped, calls


# --------------------------------------------------------------------------- #
# A full pass
# --------------------------------------------------------------------------- #


def test_a_full_pass_runs_every_prompt_at_every_repetition() -> None:
    prompt_set = balanced_prompt_set()
    report = runner(answering()).execute(
        prompt_set, conditions={"OPENAI": conditions()}, repetitions=3
    )
    assert len(report.runs) == len(prompt_set.prompts) * 3
    assert report.skipped == ()
    assert report.is_complete


def test_the_report_totals_what_the_pass_cost() -> None:
    report = runner(answering()).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    assert report.total_cost_usd == pytest.approx(COST_PER_CALL * 18)
    assert report.unpriced_calls == 0


def test_run_ids_are_deterministic_for_the_same_prompt_conditions_and_attempt() -> None:
    prompt_set = balanced_prompt_set()
    first = runner(answering()).execute(
        prompt_set, conditions={"OPENAI": conditions()}, repetitions=3
    )
    second = runner(answering()).execute(
        prompt_set, conditions={"OPENAI": conditions()}, repetitions=3
    )
    assert [run.run_id for run in first.runs] == [run.run_id for run in second.runs]
    assert len({run.run_id for run in first.runs}) == len(first.runs)


# --------------------------------------------------------------------------- #
# The raw answer stays out of the row
# --------------------------------------------------------------------------- #


def test_the_raw_answer_never_appears_in_the_run_payload() -> None:
    text = f"{mentioning_answer()} 고유표식-QZX"
    report = runner(answering(text)).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    serialised = json.dumps([run.as_dict() for run in report.runs], ensure_ascii=False)
    assert "고유표식-QZX" not in serialised
    assert all(run.raw_answer_ref for run in report.runs)


def test_the_pointer_and_hash_match_what_is_in_the_store() -> None:
    import hashlib

    store = InMemoryAnswerStore()
    report = runner(answering(), store=store).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    run = report.runs[0]
    assert run.raw_answer_ref is not None
    assert run.raw_answer_hash == hashlib.sha256(store.raw(run.raw_answer_ref)).hexdigest()
    assert store.read(run.raw_answer_ref).text == mentioning_answer()


# --------------------------------------------------------------------------- #
# Conditions
# --------------------------------------------------------------------------- #


def test_the_recorded_conditions_carry_the_model_version_from_the_response() -> None:
    report = runner(answering()).execute(
        balanced_prompt_set(),
        conditions={"OPENAI": conditions(model_version="요청 시점 미상")},
        repetitions=3,
    )
    assert {run.conditions.model_version for run in report.runs} == {OPENAI_MODEL_VERSION}


def test_runs_from_two_engines_are_not_pooled_into_one_rate() -> None:
    report = runner(answering()).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    other = runner(answering()).execute(
        balanced_prompt_set(),
        conditions={"OPENAI": conditions(model="gpt-5-mini")},
        repetitions=3,
    ).runs
    with pytest.raises(MixedConditionsError):
        aggregate_rate([*report.runs, *other], label_ko="합성 노출률")


# --------------------------------------------------------------------------- #
# A run that did not happen is an error, never a "not mentioned"
# --------------------------------------------------------------------------- #


def test_a_timeout_produces_an_error_coded_run_that_leaves_the_denominator() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("합성 지연", request=request)

    report = runner(handler).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    assert len(report.runs) == 18
    assert all(run.error_code is not None for run in report.runs)
    assert all(run.brand_mentioned is False for run in report.runs)
    assert all(run.raw_answer_ref is None for run in report.runs)
    assert not any(run.is_valid_execution for run in report.runs)

    rate = aggregate_rate(report.runs, label_ko="합성 노출률")
    assert rate.trials == 0
    assert rate.value is None


def test_a_failed_run_still_records_latency_and_an_explained_cost() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("합성 지연", request=request)

    report = runner(handler).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    assert all(run.latency_ms is not None and run.latency_ms > 0 for run in report.runs)
    assert all(run.cost_usd is None for run in report.runs)
    assert report.unpriced_calls == 18


def test_an_engine_without_a_credential_yields_error_runs_and_never_dials() -> None:
    handler, calls = counting(answering())
    report = runner(handler, credential=None).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    assert calls[0] == 0
    assert len(report.runs) == 18
    assert all(run.error_code is not None for run in report.runs)
    assert report.engine_states["OPENAI"] is ProviderState.DISABLED_NO_CREDENTIAL
    assert aggregate_rate(report.runs, label_ko="합성 노출률").trials == 0


def test_a_mention_is_not_recorded_when_the_answer_could_not_be_stored() -> None:
    """No stored answer, no evidence, no claim — the run becomes an error instead."""

    class RefusingStore(InMemoryAnswerStore):
        def put(self, key: AnswerRecordKey, record: RecordedAnswer) -> StoredAnswer:
            raise OSError("합성 저장소 장애")

    report = runner(answering(), store=RefusingStore()).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    assert all(run.error_code is not None for run in report.runs)
    assert all(run.brand_mentioned is False for run in report.runs)
    assert all(run.raw_answer_ref is None for run in report.runs)


# --------------------------------------------------------------------------- #
# Mention and citation
# --------------------------------------------------------------------------- #


def test_a_brand_named_in_the_answer_is_a_mention() -> None:
    report = runner(answering(mentioning_answer())).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    assert all(run.brand_mentioned for run in report.runs)
    assert all(run.brand_cited is False for run in report.runs)


def test_an_answer_that_does_not_name_the_brand_is_not_a_mention() -> None:
    report = runner(answering(silent_answer())).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    assert not any(run.brand_mentioned for run in report.runs)
    assert all(run.is_valid_execution for run in report.runs)


def test_a_cited_brand_domain_implies_a_mention() -> None:
    report = runner(
        answering(silent_answer(), citation_urls=(f"https://{BRAND_DOMAIN}/evidence",))
    ).execute(balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3)
    assert all(run.brand_cited for run in report.runs)
    assert all(run.brand_mentioned for run in report.runs)


def test_a_rival_citation_is_not_a_brand_citation() -> None:
    report = runner(
        answering(mentioning_answer(), citation_urls=(f"https://{RIVAL_DOMAIN}/x",))
    ).execute(balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3)
    assert all(run.brand_cited is False for run in report.runs)
    assert all(run.citations == (f"https://{RIVAL_DOMAIN}/x",) for run in report.runs)


def test_a_url_in_prose_is_never_promoted_to_a_citation() -> None:
    """Without browsing the API exposes no citation objects, so nothing can be cited."""
    text = f"{mentioning_answer()} 출처: https://{BRAND_DOMAIN}/blog"
    from veo.observations.runs import SearchMode

    report = runner(answering(text)).execute(
        balanced_prompt_set(),
        conditions={"OPENAI": conditions(search_mode=SearchMode.NO_BROWSING)},
        repetitions=3,
    )
    assert all(run.brand_mentioned for run in report.runs)
    assert all(run.brand_cited is False for run in report.runs)
    assert all(run.citations == () for run in report.runs)


# --------------------------------------------------------------------------- #
# The repetition floor
# --------------------------------------------------------------------------- #


def test_the_floor_is_the_methodology_minimum() -> None:
    assert MIN_REPETITIONS == 3


def test_fewer_repetitions_than_the_floor_is_refused() -> None:
    with pytest.raises(RepetitionFloorError, match="3"):
        runner(answering()).execute(
            balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=2
        )


def test_below_the_floor_can_be_asked_for_and_is_then_marked_on_the_report() -> None:
    report = runner(answering()).execute(
        balanced_prompt_set(),
        conditions={"OPENAI": conditions()},
        repetitions=1,
        allow_below_floor=True,
    )
    assert report.below_repetition_floor is True
    assert "3" in report.summary_ko
    assert not report.is_complete


def test_zero_repetitions_is_always_refused() -> None:
    with pytest.raises(RepetitionFloorError):
        runner(answering()).execute(
            balanced_prompt_set(),
            conditions={"OPENAI": conditions()},
            repetitions=0,
            allow_below_floor=True,
        )


# --------------------------------------------------------------------------- #
# The budget ceiling
# --------------------------------------------------------------------------- #


def test_the_budget_ceiling_stops_the_run_and_names_what_was_skipped() -> None:
    handler, calls = counting(answering())
    report = runner(handler, budget_usd=COST_PER_CALL * 2).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    assert calls[0] == 2
    assert len(report.runs) == 2
    assert len(report.skipped) == 16
    assert report.stopped_reason is StopReason.BUDGET_EXCEEDED
    assert not report.is_complete
    assert all(item.reason_ko for item in report.skipped)
    assert {item.engine for item in report.skipped} == {"OPENAI"}


def test_the_skipped_work_is_logged_rather_than_only_returned(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="veo.observations.runner"):
        runner(answering(), budget_usd=COST_PER_CALL * 2).execute(
            balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
        )
    messages = " ".join(record.getMessage() for record in caplog.records)
    assert "16" in messages


def test_the_summary_says_the_pass_was_truncated() -> None:
    report = runner(answering(), budget_usd=COST_PER_CALL * 2).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    assert "예산" in report.summary_ko
    assert "16" in report.summary_ko


def test_a_budget_cannot_be_enforced_against_an_unpriced_engine() -> None:
    handler, calls = counting(answering())
    report = runner(handler, budget_usd=1.0, price_table=PriceTable()).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    assert report.stopped_reason is StopReason.COST_UNMEASURABLE
    assert calls[0] == 1
    assert len(report.skipped) == 17
    assert not report.is_complete


def test_without_a_budget_an_unpriced_engine_runs_to_completion() -> None:
    report = runner(answering(), price_table=PriceTable()).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    assert len(report.runs) == 18
    assert report.unpriced_calls == 18
    assert report.stopped_reason is None
    assert "비용" in report.summary_ko


# --------------------------------------------------------------------------- #
# Idempotence and concurrency
# --------------------------------------------------------------------------- #


def test_a_second_pass_over_recorded_work_calls_nothing_and_repeats_itself() -> None:
    store = InMemoryAnswerStore()
    handler, calls = counting(answering())
    prompt_set = balanced_prompt_set()
    execute = lambda: runner(handler, store=store).execute(  # noqa: E731
        prompt_set, conditions={"OPENAI": conditions()}, repetitions=3
    )

    first = execute()
    assert calls[0] == 18

    second = execute()
    assert calls[0] == 18, "이미 보관된 답변을 다시 물어봤습니다"
    assert [run.as_dict() for run in second.runs] == [run.as_dict() for run in first.runs]


def test_a_failed_unit_is_not_memoised_as_done() -> None:
    store = InMemoryAnswerStore()
    state = {"fail": True}

    def handler(request: httpx.Request) -> httpx.Response:
        if state["fail"]:
            raise httpx.ReadTimeout("합성 지연", request=request)
        return httpx.Response(200, json=openai_payload())

    first = runner(handler, store=store).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    assert all(run.error_code for run in first.runs)

    state["fail"] = False
    second = runner(handler, store=store).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    assert all(run.is_valid_execution for run in second.runs)


def test_concurrency_is_limited_to_the_configured_ceiling() -> None:
    barrier = threading.Barrier(3, timeout=10.0)
    lock = threading.Lock()
    in_flight = [0]
    peak = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        with lock:
            in_flight[0] += 1
            peak[0] = max(peak[0], in_flight[0])
        barrier.wait()
        with lock:
            in_flight[0] -= 1
        return httpx.Response(200, json=openai_payload())

    report = runner(handler, max_concurrency=3, monotonic=None).execute(
        balanced_prompt_set(), conditions={"OPENAI": conditions()}, repetitions=3
    )
    assert len(report.runs) == 18
    assert peak[0] == 3


# --------------------------------------------------------------------------- #
# More than one engine
# --------------------------------------------------------------------------- #


def multi_engine_runner(store: InMemoryAnswerStore) -> ObservationRunner:
    def openai_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=openai_payload(text=mentioning_answer()))

    def gemini_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=gemini_payload(text=silent_answer()))

    return ObservationRunner(
        registry=ProviderRegistry(
            [
                provider(openai_handler),
                GeminiAnswerProvider(
                    credential=KEY,
                    transport=httpx.MockTransport(gemini_handler),
                    price_table=SYNTHETIC_PRICES,
                    monotonic=SafeMonotonic(),
                    sleep=lambda seconds: None,
                    now=lambda: NOW,
                ),
            ]
        ),
        store=store,
        detector=DisambiguatingMentionDetector(BRAND_PROFILE),
        # 이 스위트가 재는 것은 실행기의 **논리**이지 시계가 아니다. 간격을 0 으로
        # 두어 실제로 자지 않게 한다. 간격 자체는
        # `tests/observations/test_repetition_pacing.py` 가 가짜 시계로 잰다.
        repetition_interval=timedelta(0),
        max_concurrency=1,
        clock=lambda: NOW,
    )


def test_two_engines_are_measured_separately_and_never_pooled() -> None:
    report = multi_engine_runner(InMemoryAnswerStore()).execute(
        balanced_prompt_set(),
        conditions={
            "OPENAI": conditions(),
            "GOOGLE_GEMINI": conditions(engine="GOOGLE_GEMINI", model="gemini-synthetic"),
        },
        repetitions=3,
    )
    assert len(report.runs) == 36
    by_engine = {run.conditions.engine for run in report.runs}
    assert by_engine == {"OPENAI", "GOOGLE_GEMINI"}

    with pytest.raises(MixedConditionsError):
        aggregate_rate(report.runs, label_ko="합성 노출률")

    openai_runs = [run for run in report.runs if run.conditions.engine == "OPENAI"]
    gemini_runs = [run for run in report.runs if run.conditions.engine == "GOOGLE_GEMINI"]
    assert aggregate_rate(openai_runs, label_ko="합성 노출률").successes == 18
    assert aggregate_rate(gemini_runs, label_ko="합성 노출률").successes == 0


def test_an_engine_key_must_match_the_conditions_it_carries() -> None:
    with pytest.raises(ValueError, match="엔진"):
        multi_engine_runner(InMemoryAnswerStore()).execute(
            balanced_prompt_set(),
            conditions={"GOOGLE_GEMINI": conditions(engine="OPENAI")},
            repetitions=3,
        )
