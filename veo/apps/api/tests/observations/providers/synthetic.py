"""Obviously-invented answers and responses for the observation provider suite.

VEO has no Perplexity or Anthropic credential and does not run live AI calls in tests, so
every answer body in this suite is written by hand. The danger is not that they exist —
tests need them — but that a reader six months from now takes one for a real observation
and quotes it in a report. So:

* every synthetic answer body begins with :data:`SYNTHETIC_MARKER`;
* the brand is ``합성브랜드`` and its domain is ``synthetic-brand.example``, a reserved
  example domain that can never resolve;
* ``test_synthetic_answers_are_labelled.py`` asserts the marker mechanically, so the
  labelling cannot quietly lapse.

Nothing here is a claim about how any model actually answers any question.
"""

from __future__ import annotations

from typing import Any

from pydantic import SecretStr

from veo.core.settings import ProviderCredentials
from veo.observations.detection.disambiguation import BrandProfile
from veo.observations.prompts import Funnel, Intent, Prompt, PromptSet, Subject
from veo.observations.providers.base import ModelPrice, PriceTable
from veo.observations.providers.registry import PROVIDER_CLASSES
from veo.observations.runner import BrandTarget
from veo.observations.runs import AccountState, RunConditions, SearchMode

#: Prefix carried by every invented answer body in this suite.
SYNTHETIC_MARKER = "[합성 응답 — 실제 AI 답변 아님]"

BRAND_NAME = "합성브랜드"
BRAND_DOMAIN = "synthetic-brand.example"
RIVAL_DOMAIN = "synthetic-rival.example"

BRAND = BrandTarget(names=(BRAND_NAME,), domains=(BRAND_DOMAIN,))

#: 같은 브랜드를 판별기가 읽는 형태로. `합성브랜드` 는 지역명도 흔한 어간도 아니므로
#: 이름만으로 확정선을 넘는다 — 이 스위트가 재는 것은 귀속이 아니라 실행기라서, 매 시험이
#: 검수 대기로 떨어지면 재려던 것을 못 재게 된다. 귀속 자체는
#: `tests/observations/test_attribution.py` 와 `tests/observations/detection/` 이 잰다.
BRAND_PROFILE = BrandProfile(
    entity_key="synthetic-brand",
    display_name=BRAND_NAME,
    own_domains=(BRAND_DOMAIN,),
)

OPENAI_MODEL = "gpt-5"
OPENAI_MODEL_VERSION = "gpt-5-2026-05-01"

#: Invented prices. They are here so the arithmetic can be checked, not because VEO
#: knows what any engine charges — the shipped price table is empty on purpose.
SYNTHETIC_PRICES = PriceTable(
    prices={
        OPENAI_MODEL_VERSION: ModelPrice(
            input_usd_per_million=1.0, output_usd_per_million=10.0
        )
    }
)


def mentioning_answer() -> str:
    return f"{SYNTHETIC_MARKER} 이 문장은 {BRAND_NAME} 를 포함하도록 손으로 지어낸 문자열입니다."


def silent_answer() -> str:
    return f"{SYNTHETIC_MARKER} 이 문장은 어떤 브랜드도 포함하지 않도록 손으로 지어낸 문자열입니다."


def conditions(
    *,
    engine: str = "OPENAI",
    model: str = OPENAI_MODEL,
    model_version: str = "요청 시점 미상",
    search_mode: SearchMode = SearchMode.BROWSING,
) -> RunConditions:
    """The *requested* conditions. The version is filled in from the response."""
    return RunConditions(
        engine=engine,
        model=model,
        model_version=model_version,
        search_mode=search_mode,
        account_state=AccountState.ANONYMOUS,
        locale="ko-KR",
    )


def openai_payload(
    *,
    text: str | None = None,
    model_version: str | None = OPENAI_MODEL_VERSION,
    citation_urls: tuple[str, ...] = (),
    input_tokens: int | None = 1000,
    output_tokens: int | None = 500,
    web_search_ran: bool = True,
) -> dict[str, Any]:
    """A hand-written body in the documented shape of the OpenAI Responses API.

    ``web_search_ran`` 은 응답에 ``web_search_call`` 항목을 넣을지다. 기본이 참인 것은
    이 합성 응답들이 전부 "검색을 켜고 물었고 검색이 돌았다" 를 뜻하기 때문이다.

    실측 2026-08-08 · gpt-4o: 도구를 붙여도 모델이 검색을 건너뛰면 ``output`` 에
    ``web_search_call`` 이 아예 없다(입력 319 토큰). 검색이 돌면 있다(17k~21k 토큰).
    거짓으로 두면 그 응답이 재현된다.
    """
    annotations = [
        {"type": "url_citation", "url": url, "title": "합성 출처"} for url in citation_urls
    ]
    output: list[dict[str, Any]] = []
    if web_search_ran:
        output.append({"type": "web_search_call", "id": "ws_synthetic", "status": "completed"})
    output.append(
        {
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "output_text",
                    "text": text if text is not None else mentioning_answer(),
                    "annotations": annotations,
                }
            ],
        }
    )
    payload: dict[str, Any] = {"id": "resp_synthetic", "output": output}
    if model_version is not None:
        payload["model"] = model_version
    if input_tokens is not None or output_tokens is not None:
        payload["usage"] = {"input_tokens": input_tokens, "output_tokens": output_tokens}
    return payload


def perplexity_payload(*, text: str | None = None) -> dict[str, Any]:
    return {
        "model": "sonar-synthetic-2026-01-01",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": text if text is not None else mentioning_answer(),
                },
            }
        ],
        "citations": [f"https://{BRAND_DOMAIN}/synthetic"],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    }


def gemini_payload(
    *,
    text: str | None = None,
    model_version: str | None = "gemini-synthetic-2026-01-01",
    grounding_uris: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """A hand-written body in the documented shape of the Generative Language API."""
    candidate: dict[str, Any] = {
        "content": {
            "role": "model",
            "parts": [{"text": text if text is not None else mentioning_answer()}],
        }
    }
    if grounding_uris is not None:
        candidate["groundingMetadata"] = {
            "groundingChunks": [
                {"web": {"uri": uri, "title": "합성 출처"}} for uri in grounding_uris
            ]
        }
    payload: dict[str, Any] = {
        "candidates": [candidate],
        "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 50},
    }
    if model_version is not None:
        payload["modelVersion"] = model_version
    return payload


def anthropic_payload(*, text: str | None = None) -> dict[str, Any]:
    return {
        "id": "msg_synthetic",
        "model": "claude-synthetic-2026-01-01",
        "content": [
            {"type": "text", "text": text if text is not None else mentioning_answer()}
        ],
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }


def balanced_prompt_set() -> PromptSet:
    """Six questions spanning six intents — balanced enough for :class:`PromptSet`."""
    return PromptSet.build(
        name="합성 프롬프트 집합",
        prompts=[
            Prompt(
                text="합성 시술이란 무엇인가요?",
                intent=Intent.DEFINITION,
                funnel=Funnel.PROBLEM_AWARE,
                subject=Subject.NON_BRAND,
            ),
            Prompt(
                text="합성 시술은 어떻게 준비하나요?",
                intent=Intent.HOW_TO,
                funnel=Funnel.RESEARCH,
                subject=Subject.NON_BRAND,
            ),
            Prompt(
                text="합성 시술 A와 B를 비교해 주세요.",
                intent=Intent.COMPARISON,
                funnel=Funnel.COMPARISON,
                subject=Subject.CATEGORY,
            ),
            Prompt(
                text="합성 시술의 부작용과 안전성은 어떤가요?",
                intent=Intent.TRUST,
                funnel=Funnel.RESEARCH,
                subject=Subject.NON_BRAND,
            ),
            Prompt(
                text="합성 시술로 추천할 만한 곳은 어디인가요?",
                intent=Intent.BEST_OR_RECOMMENDED,
                funnel=Funnel.RECOMMENDATION,
                subject=Subject.CATEGORY,
            ),
            Prompt(
                text="합성 시술 비용은 얼마인가요?",
                intent=Intent.PRICE,
                funnel=Funnel.PURCHASE_OR_VISIT,
                subject=Subject.NON_BRAND,
            ),
        ],
    )


def credentials_with(value: SecretStr | None) -> ProviderCredentials:
    """Provider credentials with *every* AI engine slot set to the same value.

    Every field is named explicitly so the suite never depends on what happens to be in
    the developer's ``.env`` — a real key leaking into a test would turn "opens no
    connection" into a live network call.
    """
    return ProviderCredentials(
        **{provider.settings_field: value for provider in PROVIDER_CLASSES}
    )


def no_credentials() -> ProviderCredentials:
    return credentials_with(None)


def placeholder_credentials() -> ProviderCredentials:
    return credentials_with(SecretStr("[SENSITIVE]"))
