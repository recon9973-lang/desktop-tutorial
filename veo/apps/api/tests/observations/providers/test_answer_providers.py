"""The AI answer adapters: what they refuse to do, and what they must record.

Four rules are load-bearing and each has a test here that fails loudly if it lapses:

* **No credential opens no connection.** The transport must never be touched.
* **A failure is metered too.** Cost and latency are recorded whether the call worked or
  not, because VEO-LAB has to know what a 500-run study costs before authorising it.
* **The model version comes from the response.** A run recorded as "gpt-5" without the
  dated build cannot be compared with one from last month.
* **A citation is a citation only when the provider said so.** Where the API exposes no
  citation objects the adapter reports that, rather than running a URL regex over prose
  and calling the result evidence.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from pydantic import SecretStr
from tests.observations.providers.synthetic import (
    BRAND_DOMAIN,
    OPENAI_MODEL_VERSION,
    RIVAL_DOMAIN,
    SYNTHETIC_PRICES,
    anthropic_payload,
    conditions,
    gemini_payload,
    no_credentials,
    openai_payload,
    perplexity_payload,
    placeholder_credentials,
    silent_answer,
)

from veo.contracts.enums import ErrorCode, ProviderState
from veo.observations.providers.anthropic import AnthropicAnswerProvider
from veo.observations.providers.base import (
    AnswerProvider,
    AnswerRateLimitedError,
    AnswerSchemaError,
    CitationSupport,
    CostBasis,
    ModelPrice,
    PriceTable,
    ProviderAnswer,
    classify_answer_status,
)
from veo.observations.providers.gemini import GeminiAnswerProvider
from veo.observations.providers.openai import OpenAIAnswerProvider
from veo.observations.providers.perplexity import PerplexityAnswerProvider
from veo.observations.providers.registry import PROVIDER_CLASSES, build_registry
from veo.observations.runs import SearchMode
from veo.providers.naver.errors import UNKNOWN

NOW = datetime(2026, 7, 28, 9, 0, tzinfo=UTC)
KEY = SecretStr("synthetic-openai-key")


class FakeMonotonic:
    """A clock that advances a fixed amount every time it is read.

    Latency has to be a real number in these assertions, and a real clock would make them
    flaky. Each ``ask`` reads the clock twice, so one attempt costs ``step`` seconds.
    """

    def __init__(self, step: float = 0.25) -> None:
        self._step = step
        self._value = 0.0

    def __call__(self) -> float:
        current = self._value
        self._value += self._step
        return current


def openai_provider(
    handler: object, *, credential: SecretStr | None = KEY, **kwargs: object
) -> OpenAIAnswerProvider:
    return OpenAIAnswerProvider(
        credential=credential,
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        price_table=SYNTHETIC_PRICES,
        monotonic=FakeMonotonic(),
        sleep=lambda seconds: None,
        now=lambda: NOW,
        **kwargs,  # type: ignore[arg-type]
    )


def ok(payload: object) -> object:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return handler


# --------------------------------------------------------------------------- #
# No credential opens no connection
# --------------------------------------------------------------------------- #


#: Driven off the registry rather than a hand-written list, so an engine added to
#: ``PROVIDER_CLASSES`` cannot skip the two checks below by nobody remembering it.
REGISTERED_ENGINES = build_registry(credentials=no_credentials()).engines()


def test_every_known_engine_is_registered() -> None:
    assert set(REGISTERED_ENGINES) == {provider.engine for provider in PROVIDER_CLASSES}
    assert "GOOGLE_GEMINI" in REGISTERED_ENGINES


@pytest.mark.parametrize("engine", REGISTERED_ENGINES)
def test_no_credential_opens_no_connection(engine: str) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={})

    registry = build_registry(
        credentials=no_credentials(),
        transport=httpx.MockTransport(handler),
    )
    provider = registry.resolve(engine)
    assert provider.state is ProviderState.DISABLED_NO_CREDENTIAL

    outcome = provider.ask("합성 질문", conditions=conditions(engine=engine))

    assert calls == 0, f"{engine}: 자격증명이 없는데 연결을 열었습니다"
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None
    assert outcome.failure.provider_state is ProviderState.DISABLED_NO_CREDENTIAL
    assert outcome.attempts == 0


@pytest.mark.parametrize("engine", REGISTERED_ENGINES)
def test_a_placeholder_is_not_a_credential_and_also_never_dials(engine: str) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={})

    registry = build_registry(
        credentials=placeholder_credentials(),
        transport=httpx.MockTransport(handler),
    )
    provider = registry.resolve(engine)
    assert provider.state is ProviderState.DISABLED_INVALID_CREDENTIAL

    outcome = provider.ask("합성 질문", conditions=conditions(engine=engine))

    assert calls == 0, f"{engine}: 자리표시자를 자격증명으로 받아들였습니다"
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None
    assert outcome.failure.provider_state is ProviderState.DISABLED_INVALID_CREDENTIAL


@pytest.mark.parametrize("engine", REGISTERED_ENGINES)
def test_a_disabled_engine_still_reports_latency_and_an_explained_cost(engine: str) -> None:
    provider = build_registry(credentials=no_credentials()).resolve(engine)
    outcome = provider.ask("합성 질문", conditions=conditions(engine=engine))
    assert outcome.latency_ms >= 0
    assert outcome.cost_usd is None
    assert outcome.cost_basis is CostBasis.NO_USAGE_REPORTED


def test_a_configured_engine_is_enabled_and_sends_its_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer synthetic-perplexity-key"
        return httpx.Response(200, json=perplexity_payload())

    provider = PerplexityAnswerProvider(
        credential=SecretStr("synthetic-perplexity-key"),
        transport=httpx.MockTransport(handler),
        monotonic=FakeMonotonic(),
        sleep=lambda seconds: None,
        now=lambda: NOW,
    )
    assert provider.state is ProviderState.ENABLED
    assert provider.ask("합성 질문", conditions=conditions(engine="PERPLEXITY")).succeeded


def test_anthropic_sends_its_documented_headers() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.headers))
        return httpx.Response(200, json=anthropic_payload())

    provider = AnthropicAnswerProvider(
        credential=SecretStr("synthetic-anthropic-key"),
        transport=httpx.MockTransport(handler),
        monotonic=FakeMonotonic(),
        sleep=lambda seconds: None,
        now=lambda: NOW,
    )
    outcome = provider.ask("합성 질문", conditions=conditions(engine="ANTHROPIC"))
    assert outcome.succeeded
    assert seen["x-api-key"] == "synthetic-anthropic-key"
    assert seen["anthropic-version"]


# --------------------------------------------------------------------------- #
# The model version is read off the response
# --------------------------------------------------------------------------- #


def test_the_model_version_comes_from_the_response_not_the_request() -> None:
    provider = openai_provider(ok(openai_payload(model_version="gpt-5-2026-06-30")))
    outcome = provider.ask("합성 질문", conditions=conditions(model_version="요청 시점 미상"))
    answer = outcome.value
    assert isinstance(answer, ProviderAnswer)
    assert answer.model_version == "gpt-5-2026-06-30"


def test_a_response_without_a_model_field_is_refused_rather_than_assumed() -> None:
    provider = openai_provider(ok(openai_payload(model_version=None)))
    outcome = provider.ask("합성 질문", conditions=conditions())
    assert outcome.value is UNKNOWN
    assert outcome.failure is not None
    assert outcome.failure.error_code is ErrorCode.PROVIDER_UNAVAILABLE


def test_an_empty_answer_is_a_schema_failure_not_an_empty_string() -> None:
    provider = openai_provider(ok({"model": OPENAI_MODEL_VERSION, "output": []}))
    outcome = provider.ask("합성 질문", conditions=conditions())
    assert outcome.value is UNKNOWN


# --------------------------------------------------------------------------- #
# Citations
# --------------------------------------------------------------------------- #


def test_structured_citations_are_taken_from_the_annotations() -> None:
    provider = openai_provider(
        ok(
            openai_payload(
                citation_urls=(f"https://{BRAND_DOMAIN}/a", f"https://{RIVAL_DOMAIN}/b")
            )
        )
    )
    outcome = provider.ask("합성 질문", conditions=conditions(search_mode=SearchMode.BROWSING))
    answer = outcome.value
    assert isinstance(answer, ProviderAnswer)
    assert answer.citation_support is CitationSupport.STRUCTURED
    assert answer.citations == (f"https://{BRAND_DOMAIN}/a", f"https://{RIVAL_DOMAIN}/b")


def test_without_browsing_the_adapter_says_citations_are_not_exposed() -> None:
    """Not "zero citations" — the API was never asked for any, so none can be evidenced."""
    text = f"{silent_answer()} 참고: https://{BRAND_DOMAIN}/prose"
    provider = openai_provider(ok(openai_payload(text=text)))
    outcome = provider.ask(
        "합성 질문", conditions=conditions(search_mode=SearchMode.NO_BROWSING)
    )
    answer = outcome.value
    assert isinstance(answer, ProviderAnswer)
    assert answer.citation_support is CitationSupport.NOT_EXPOSED_BY_PROVIDER
    assert answer.citations == ()
    assert BRAND_DOMAIN in answer.text, "본문은 그대로 보관되어야 합니다"


def test_an_unknown_search_mode_is_a_programming_error_not_a_measurement() -> None:
    provider = openai_provider(ok(openai_payload()))
    with pytest.raises(ValueError, match="검색"):
        provider.ask("합성 질문", conditions=conditions(search_mode=SearchMode.UNKNOWN))


def test_an_answer_cannot_claim_citations_it_says_are_not_exposed() -> None:
    with pytest.raises(ValueError, match="인용"):
        ProviderAnswer(
            text="합성",
            model="m",
            model_version="m-1",
            citations=("https://example.test/",),
            citation_support=CitationSupport.NOT_EXPOSED_BY_PROVIDER,
            input_tokens=None,
            output_tokens=None,
        )


# --------------------------------------------------------------------------- #
# 429 backs off and then succeeds
# --------------------------------------------------------------------------- #


def test_a_rate_limited_call_backs_off_and_then_succeeds() -> None:
    attempts = 0
    slept: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"retry-after": "2"}, json={"error": "slow down"})
        return httpx.Response(200, json=openai_payload())

    provider = OpenAIAnswerProvider(
        credential=KEY,
        transport=httpx.MockTransport(handler),
        price_table=SYNTHETIC_PRICES,
        monotonic=FakeMonotonic(),
        sleep=slept.append,
        now=lambda: NOW,
    )
    outcome = provider.ask("합성 질문", conditions=conditions())

    assert attempts == 2
    assert slept == [2.0], "제공자가 알려준 Retry-After 를 그대로 기다려야 합니다"
    assert outcome.succeeded
    assert outcome.attempts == 2


def test_a_429_is_classified_as_a_retryable_rate_limit() -> None:
    error = classify_answer_status(429, retry_after="7")
    assert isinstance(error, AnswerRateLimitedError)
    assert error.retryable is True
    assert error.retry_after_seconds == 7
    assert error.error_code is ErrorCode.PROVIDER_RATE_LIMITED


def test_no_provider_error_message_names_naver() -> None:
    """The machinery is shared with the Naver adapters; the customer text is not."""
    for status in (401, 403, 429, 500, 418):
        assert "네이버" not in classify_answer_status(status).message_ko


# --------------------------------------------------------------------------- #
# Cost and latency, on success and on failure
# --------------------------------------------------------------------------- #


def test_cost_is_calculated_from_the_reported_usage() -> None:
    provider = openai_provider(ok(openai_payload(input_tokens=1_000_000, output_tokens=100_000)))
    outcome = provider.ask("합성 질문", conditions=conditions())
    assert outcome.cost_basis is CostBasis.CALCULATED_FROM_USAGE
    assert outcome.cost_usd == pytest.approx(1.0 + 1.0)
    assert outcome.input_tokens == 1_000_000
    assert outcome.output_tokens == 100_000


def test_latency_is_recorded_on_a_successful_call() -> None:
    provider = openai_provider(ok(openai_payload()))
    outcome = provider.ask("합성 질문", conditions=conditions())
    assert outcome.latency_ms == 250


def test_cost_and_latency_are_recorded_on_a_timeout_too() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("합성 지연", request=request)

    provider = openai_provider(handler)
    outcome = provider.ask("합성 질문", conditions=conditions())

    assert outcome.value is UNKNOWN
    assert outcome.latency_ms > 0, "실패한 호출도 시간을 소비했습니다"
    assert outcome.cost_usd is None
    assert outcome.cost_basis is CostBasis.NO_USAGE_REPORTED


def test_an_unpriced_model_reports_no_cost_rather_than_zero() -> None:
    provider = OpenAIAnswerProvider(
        credential=KEY,
        transport=httpx.MockTransport(ok(openai_payload())),  # type: ignore[arg-type]
        price_table=PriceTable(),
        monotonic=FakeMonotonic(),
        sleep=lambda seconds: None,
        now=lambda: NOW,
    )
    outcome = provider.ask("합성 질문", conditions=conditions())
    assert outcome.succeeded
    assert outcome.cost_usd is None
    assert outcome.cost_basis is CostBasis.NO_PRICE_CONFIGURED


def test_the_shipped_price_table_is_empty_so_no_price_is_invented() -> None:
    from veo.observations.providers.base import DEFAULT_PRICE_TABLE

    assert DEFAULT_PRICE_TABLE.prices == {}


def test_a_price_table_prefers_the_dated_version_over_the_family() -> None:
    table = PriceTable(
        prices={
            "gpt-5": ModelPrice(input_usd_per_million=100.0, output_usd_per_million=100.0),
            "gpt-5-2026-05-01": ModelPrice(
                input_usd_per_million=1.0, output_usd_per_million=1.0
            ),
        }
    )
    cost, basis = table.cost(
        model="gpt-5",
        model_version="gpt-5-2026-05-01",
        input_tokens=1_000_000,
        output_tokens=0,
    )
    assert basis is CostBasis.CALCULATED_FROM_USAGE
    assert cost == pytest.approx(1.0)


def test_usage_absent_from_the_response_is_reported_as_such() -> None:
    provider = openai_provider(ok(openai_payload(input_tokens=None, output_tokens=None)))
    outcome = provider.ask("합성 질문", conditions=conditions())
    assert outcome.succeeded
    assert outcome.cost_usd is None
    assert outcome.cost_basis is CostBasis.NO_USAGE_REPORTED


# --------------------------------------------------------------------------- #
# Protocol conformance
# --------------------------------------------------------------------------- #


def test_every_adapter_satisfies_the_protocol() -> None:
    built: list[AnswerProvider] = [
        provider_class.from_settings(no_credentials())
        for provider_class in PROVIDER_CLASSES
    ]
    assert {provider.engine for provider in built} == {
        "OPENAI",
        "GOOGLE_GEMINI",
        "PERPLEXITY",
        "ANTHROPIC",
    }
    assert all(isinstance(provider, AnswerProvider) for provider in built)


def test_the_secret_never_appears_in_a_repr() -> None:
    provider = openai_provider(ok(openai_payload()))
    assert "synthetic-openai-key" not in repr(provider)


def test_a_schema_error_is_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, content=b"<html>maintenance</html>")

    provider = openai_provider(handler)
    outcome = provider.ask("합성 질문", conditions=conditions())
    assert outcome.value is UNKNOWN
    assert calls == 1
    assert isinstance(AnswerSchemaError(), AnswerSchemaError)


# --------------------------------------------------------------------------- #
# Gemini: grounding is a search mode, and citations come from its metadata
# --------------------------------------------------------------------------- #


def gemini_provider(handler: object, **kwargs: object) -> GeminiAnswerProvider:
    return GeminiAnswerProvider(
        credential=SecretStr("synthetic-gemini-key"),
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        monotonic=FakeMonotonic(),
        sleep=lambda seconds: None,
        now=lambda: NOW,
        **kwargs,  # type: ignore[arg-type]
    )


def test_gemini_reads_its_model_version_from_the_response() -> None:
    provider = gemini_provider(ok(gemini_payload(model_version="gemini-synthetic-2026-07-01")))
    outcome = provider.ask("합성 질문", conditions=conditions(engine="GOOGLE_GEMINI"))
    answer = outcome.value
    assert isinstance(answer, ProviderAnswer)
    assert answer.model_version == "gemini-synthetic-2026-07-01"


def test_gemini_without_a_model_version_is_refused() -> None:
    provider = gemini_provider(ok(gemini_payload(model_version=None)))
    assert provider.ask("합성 질문", conditions=conditions(engine="GOOGLE_GEMINI")).value is UNKNOWN


def test_gemini_sends_its_key_in_a_header_and_never_in_the_url() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-goog-api-key", "")
        return httpx.Response(200, json=gemini_payload())

    gemini_provider(handler).ask("합성 질문", conditions=conditions(engine="GOOGLE_GEMINI"))
    assert seen["key"] == "synthetic-gemini-key"
    assert "synthetic-gemini-key" not in seen["url"]


def test_grounding_is_requested_only_when_the_search_mode_says_so() -> None:
    seen: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json as _json

        seen.append(_json.loads(request.content).get("tools"))
        return httpx.Response(200, json=gemini_payload(grounding_uris=()))

    provider = gemini_provider(handler)
    provider.ask(
        "합성 질문",
        conditions=conditions(engine="GOOGLE_GEMINI", search_mode=SearchMode.BROWSING),
    )
    provider.ask(
        "합성 질문",
        conditions=conditions(engine="GOOGLE_GEMINI", search_mode=SearchMode.NO_BROWSING),
    )
    assert seen[0] == [{"google_search": {}}]
    assert seen[1] is None


def test_gemini_citations_come_from_grounding_metadata() -> None:
    provider = gemini_provider(
        ok(gemini_payload(grounding_uris=(f"https://{BRAND_DOMAIN}/a",)))
    )
    outcome = provider.ask(
        "합성 질문",
        conditions=conditions(engine="GOOGLE_GEMINI", search_mode=SearchMode.BROWSING),
    )
    answer = outcome.value
    assert isinstance(answer, ProviderAnswer)
    assert answer.citation_support is CitationSupport.STRUCTURED
    assert answer.citations == (f"https://{BRAND_DOMAIN}/a",)


def test_gemini_without_grounding_metadata_claims_no_citations() -> None:
    """No metadata means nothing can be evidenced — not that no source was used."""
    text = f"{silent_answer()} 참고: https://{BRAND_DOMAIN}/prose"
    provider = gemini_provider(ok(gemini_payload(text=text)))
    outcome = provider.ask(
        "합성 질문",
        conditions=conditions(engine="GOOGLE_GEMINI", search_mode=SearchMode.BROWSING),
    )
    answer = outcome.value
    assert isinstance(answer, ProviderAnswer)
    assert answer.citation_support is CitationSupport.NOT_EXPOSED_BY_PROVIDER
    assert answer.citations == ()


def test_ungrounded_gemini_never_promotes_a_url_from_prose() -> None:
    text = f"{silent_answer()} 출처: https://{BRAND_DOMAIN}/prose"
    provider = gemini_provider(ok(gemini_payload(text=text)))
    outcome = provider.ask(
        "합성 질문",
        conditions=conditions(engine="GOOGLE_GEMINI", search_mode=SearchMode.NO_BROWSING),
    )
    answer = outcome.value
    assert isinstance(answer, ProviderAnswer)
    assert answer.citations == ()
    assert answer.citation_support is CitationSupport.NOT_EXPOSED_BY_PROVIDER


def test_gemini_grounded_and_ungrounded_runs_are_different_measurements() -> None:
    grounded = conditions(engine="GOOGLE_GEMINI", search_mode=SearchMode.BROWSING)
    ungrounded = conditions(engine="GOOGLE_GEMINI", search_mode=SearchMode.NO_BROWSING)
    assert grounded.fingerprint != ungrounded.fingerprint


def test_gemini_records_the_usage_it_was_given() -> None:
    provider = gemini_provider(ok(gemini_payload()), price_table=PriceTable())
    outcome = provider.ask("합성 질문", conditions=conditions(engine="GOOGLE_GEMINI"))
    assert outcome.input_tokens == 100
    assert outcome.output_tokens == 50
    assert outcome.cost_usd is None
    assert outcome.cost_basis is CostBasis.NO_PRICE_CONFIGURED
