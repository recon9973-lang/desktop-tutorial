"""The Perplexity adapter. Disabled until somebody configures a key.

**Unverified.** Nothing below has been checked against a live response: the request
shape, the ``citations`` field and the usage key names all follow the published
documentation for the OpenAI-compatible chat completions endpoint, and none of it has
been exercised against the real service. With no credential configured the provider is
:attr:`ProviderState.DISABLED_NO_CREDENTIAL` and opens no connection, so the unverified
mapping cannot silently produce a wrong observation — it can only produce "측정 불가".

The credential comes from ``ProviderCredentials.perplexity_api_key`` via
:meth:`~veo.observations.providers.base.HttpAnswerProvider.from_settings`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar, Final

from pydantic import SecretStr

from veo.observations.providers.base import (
    AnswerSchemaError,
    CitationSupport,
    HttpAnswerProvider,
    ProviderAnswer,
    collect_urls,
    read_token_count,
    require_model_version,
)
from veo.observations.runs import RunConditions

__all__ = [
    "PERPLEXITY_BASE_URL",
    "PERPLEXITY_CHAT_PATH",
    "PerplexityAnswerProvider",
]

PERPLEXITY_BASE_URL: Final = "https://api.perplexity.ai"
PERPLEXITY_CHAT_PATH: Final = "/chat/completions"


class PerplexityAnswerProvider(HttpAnswerProvider):
    """Asks one question of a Perplexity model, or says why it could not."""

    engine: ClassVar[str] = "PERPLEXITY"
    base_url: ClassVar[str] = PERPLEXITY_BASE_URL
    settings_field: ClassVar[str] = "perplexity_api_key"

    #: Perplexity 는 요청마다 검색한다 — 끄는 요청 자체가 없다. 예전에는 호출자가 말한
    #: 모드를 그대로 기록했는데, 그러면 검색하고 답한 것이 "검색 끔" 으로 남는다.
    #: 이제 그 요청은 :meth:`HttpAnswerProvider.ask` 에서 거절된다.
    supports_search_off: ClassVar[bool] = False

    def _build_request(
        self, credential: SecretStr, prompt_text: str, conditions: RunConditions
    ) -> tuple[str, Mapping[str, str], Mapping[str, Any]]:
        return (
            f"{self._base_url}{PERPLEXITY_CHAT_PATH}",
            {
                "Authorization": f"Bearer {credential.get_secret_value()}",
                "Content-Type": "application/json",
            },
            {
                "model": conditions.model,
                "messages": [{"role": "user", "content": prompt_text}],
            },
        )

    def _parse(
        self, payload: Mapping[str, Any], *, conditions: RunConditions
    ) -> ProviderAnswer:
        model_version = require_model_version(payload)
        text = _read_message(payload)
        if not text.strip():
            raise AnswerSchemaError("response carries no assistant message")

        raw_citations = payload.get("citations")
        if not isinstance(raw_citations, list):
            # The documented field is absent. Reporting an empty citation list here would
            # claim the engine used no sources, which is not what a missing field says.
            citations: tuple[str, ...] = ()
            support = CitationSupport.NOT_EXPOSED_BY_PROVIDER
        else:
            citations = collect_urls(raw_citations)
            support = CitationSupport.STRUCTURED

        usage = payload.get("usage")
        return ProviderAnswer(
            text=text,
            model=conditions.model,
            model_version=model_version,
            citations=citations,
            citation_support=support,
            input_tokens=read_token_count(usage, "prompt_tokens", "input_tokens"),
            output_tokens=read_token_count(usage, "completion_tokens", "output_tokens"),
        )


def _read_message(payload: Mapping[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AnswerSchemaError("response has no choices array")
    first = choices[0]
    if not isinstance(first, dict):
        raise AnswerSchemaError("choices[0] is not an object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise AnswerSchemaError("choices[0] has no message")
    content = message.get("content")
    if not isinstance(content, str):
        raise AnswerSchemaError("choices[0].message.content is not a string")
    return content
