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
from veo.observations.providers.openai import OpenAIAnswerProvider, reports_citations
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


# --------------------------------------------------------------------------- #
# 인용을 못 돌려주는 모델은 "인용 0건" 이 아니라 "측정 불가" 다
# --------------------------------------------------------------------------- #


def test_a_model_that_cannot_report_citations_is_not_a_zero() -> None:
    """실측: gpt-4o-mini 는 web_search 를 붙여도 url_citation 을 하나도 돌려주지 않는다.

    검색 모드이기만 하면 STRUCTURED 로 단정하던 시절, 이 조합은
    `citation_support=STRUCTURED` + `citations=()` 가 되어 **"찾아봤지만 인용이 없었다"**
    로 기록됐다. 사실은 **"이 모델은 인용을 알려주지 않는다"** 다. 앞의 것으로 기록되면
    인용률이 0 으로 계산되어 고객에게 "AI 가 당신을 한 번도 인용하지 않습니다" 라고
    보고하게 된다 — 지어낸 값보다 나쁘다. 지어낸 줄도 모른다.
    """
    provider = openai_provider(ok(openai_payload()))

    outcome = provider.ask("합성 질문", conditions=conditions(model="gpt-4o-mini"))

    assert outcome.succeeded
    assert outcome.value is not None
    assert outcome.value.citation_support is CitationSupport.NOT_EXPOSED_BY_PROVIDER
    assert outcome.value.citations == ()


def test_an_answer_written_without_searching_is_not_a_zero() -> None:
    """도구를 붙였다고 검색이 도는 것이 아니다.

    실측 2026-08-08 · gpt-4o · 같은 `web_search` 도구를 붙인 채:

        "임플란트 수술 후 붓기는 며칠 가나요?"  output=['message']
                                               입력 319 토큰 · annotation 0
        "베놈애드는 어떤 회사인가요?" 3회 반복   output=['web_search_call','message']
                                               입력 17,286 / 17,310 / 21,504 토큰

    모델이 그때그때 정한다. 검색을 건너뛴 답변을 `STRUCTURED` + `citations=()` 로 적으면
    **"AI 가 찾아봤지만 당신을 인용하지 않았다"** 가 된다. 사실은 "AI 가 찾아보지도
    않았다" 이고, 거래처에 주는 지시가 정반대다 — 앞은 "경쟁사에 밀렸으니 콘텐츠를
    고쳐라", 뒤는 "이 질문은 애초에 검색으로 가지 않는다" 이다.
    """
    provider = openai_provider(ok(openai_payload(web_search_ran=False)))

    outcome = provider.ask("합성 질문", conditions=conditions(model="gpt-4o"))

    assert outcome.succeeded
    assert outcome.value is not None
    assert outcome.value.citation_support is CitationSupport.NOT_EXPOSED_BY_PROVIDER
    assert outcome.value.citations == ()


def test_citations_are_dropped_when_no_search_ran() -> None:
    """검색이 안 돌았는데 annotation 이 붙어 있으면 그것은 우리가 모르는 경로로 온
    값이다. 인용으로 세면 근거 없는 인용을 만들어 낸다 — 비운다."""
    provider = openai_provider(
        ok(
            openai_payload(
                web_search_ran=False, citation_urls=("https://a.example/x",)
            )
        )
    )

    outcome = provider.ask("합성 질문", conditions=conditions(model="gpt-4o"))

    assert outcome.value is not None
    assert outcome.value.citations == ()


def test_a_search_that_ran_but_cited_nobody_is_still_a_zero() -> None:
    """반대 방향도 지킨다. **검색이 실제로 돌았는데** 아무도 인용하지 않았다면 그것은
    진짜 0 이고, 측정 불가로 접으면 거래처가 알아야 할 사실을 지우는 것이다."""
    provider = openai_provider(ok(openai_payload(web_search_ran=True)))

    outcome = provider.ask("합성 질문", conditions=conditions(model="gpt-4o"))

    assert outcome.value is not None
    assert outcome.value.citation_support is CitationSupport.STRUCTURED
    assert outcome.value.citations == ()


def test_the_adapter_counts_the_searches_it_saw() -> None:
    """검색 횟수는 **돈** 때문에 센다.

    OpenAI 는 검색에 호출당 요금을 따로 받는다(2026-08-08 공식 문서: 추론 $10/1k,
    비추론 $25/1k). 한 응답에 검색이 두 번 돌면 두 번 청구되므로 참/거짓이 아니라
    개수여야 한다. 어댑터가 세지 않으면 가격표는 셀 방법이 없다.
    """
    payload = openai_payload()
    payload["output"].insert(
        0, {"type": "web_search_call", "id": "ws_second", "status": "completed"}
    )

    provider = openai_provider(ok(payload))
    outcome = provider.ask("합성 질문", conditions=conditions(model="gpt-4o"))

    assert outcome.value is not None
    assert outcome.value.search_calls == 2


def test_a_call_without_search_reports_zero_not_none() -> None:
    """0과 '모른다' 는 다르다. 검색이 안 돈 것을 **봤으면** 0이고, 그때는 검색 요금이
    없는 것이 확실하므로 금액을 낼 수 있다."""
    provider = openai_provider(ok(openai_payload(web_search_ran=False)))

    outcome = provider.ask("합성 질문", conditions=conditions(model="gpt-4o"))

    assert outcome.value is not None
    assert outcome.value.search_calls == 0


def test_the_search_count_reaches_the_price_table() -> None:
    """세 놓고 안 넘기면 세지 않은 것과 같다(0-E). 요금이 붙는 모델로 확인한다."""
    from veo.observations.providers.base import ModelPrice, PriceTable

    provider = OpenAIAnswerProvider(
        credential=KEY,
        transport=httpx.MockTransport(ok(openai_payload())),  # type: ignore[arg-type]
        price_table=PriceTable(
            prices={
                OPENAI_MODEL_VERSION: ModelPrice(
                    input_usd_per_million=0.0,
                    output_usd_per_million=0.0,
                    search_usd_per_1k_calls=10.0,
                )
            }
        ),
        monotonic=FakeMonotonic(),
        sleep=lambda seconds: None,
        now=lambda: NOW,
    )

    outcome = provider.ask("합성 질문", conditions=conditions(model="gpt-4o"))

    # 토큰 단가 0 · 검색 1회 → 순수하게 검색 요금만 남는다
    assert outcome.cost_usd == pytest.approx(0.01)
    assert outcome.cost_basis is CostBasis.CALCULATED_FROM_USAGE


def test_an_unverified_model_is_not_assumed_capable() -> None:
    """확인하지 않은 능력을 있다고 가정하면 그 모델의 모든 답변이 거짓 0 이 된다."""
    provider = openai_provider(ok(openai_payload()))

    outcome = provider.ask("합성 질문", conditions=conditions(model="gpt-9-future"))

    assert outcome.value is not None
    assert outcome.value.citation_support is CitationSupport.NOT_EXPOSED_BY_PROVIDER


def test_a_verified_model_still_reports_its_citations() -> None:
    """고치면서 되는 것을 깨뜨리지 않았는지 — gpt-5 는 실측으로 확인된 모델이다."""
    provider = openai_provider(ok(openai_payload()))

    outcome = provider.ask("합성 질문", conditions=conditions(model="gpt-5"))

    assert outcome.value is not None
    assert outcome.value.citation_support is CitationSupport.STRUCTURED


@pytest.mark.parametrize(
    ("model", "capable"),
    [
        ("gpt-4o", True),
        ("GPT-4O", True),
        ("gpt-4o-2024-11-20", True),
        ("gpt-5", True),
        ("gpt-5-2026-05-01", True),
        ("gpt-4o-mini", False),
        ("gpt-4o-mini-2024-07-18", False),
        ("gpt-4.1", False),
        ("gpt-5-mini", False),
        ("", False),
    ],
)
def test_the_prefix_match_separates_a_model_from_its_mini(model: str, capable: bool) -> None:
    """`gpt-4o-mini` 가 `gpt-4o` 에 걸리면 이 장치가 존재할 이유가 사라진다.

    날짜 변형만 같은 모델로 본다. `-mini` 는 실측에서 인용을 돌려주지 않았고,
    `gpt-5-mini` 는 아직 재보지 않았으므로 둘 다 능력을 인정하지 않는다.
    """
    assert reports_citations(model) is capable


def test_no_browsing_is_still_not_a_zero_even_on_a_capable_model() -> None:
    """검색을 끄면 API 가 인용 객체를 아예 만들지 않는다. 그것도 0건이 아니다."""
    provider = openai_provider(ok(openai_payload()))

    outcome = provider.ask(
        "합성 질문",
        conditions=conditions(model="gpt-5", search_mode=SearchMode.NO_BROWSING),
    )

    assert outcome.value is not None
    assert outcome.value.citation_support is CitationSupport.NOT_EXPOSED_BY_PROVIDER
