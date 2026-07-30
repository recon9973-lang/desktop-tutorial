"""The Anthropic adapter. Disabled until somebody configures a key.

**Unverified.** The request shape, the ``anthropic-version`` header value, the
content-block layout and the web-search result blocks below all follow the published
Messages API documentation and none of it has been exercised against the real service.
With no credential configured the provider is
:attr:`ProviderState.DISABLED_NO_CREDENTIAL` and opens no connection, so an unverified
mapping cannot produce a wrong observation — only "측정 불가".

The credential comes from ``ProviderCredentials.anthropic_api_key`` via
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
from veo.observations.runs import RunConditions, SearchMode

__all__ = [
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_MAX_TOKENS",
    "ANTHROPIC_MESSAGES_PATH",
    "ANTHROPIC_VERSION",
    "AnthropicAnswerProvider",
]

ANTHROPIC_BASE_URL: Final = "https://api.anthropic.com"
ANTHROPIC_MESSAGES_PATH: Final = "/v1/messages"

#: The API requires a dated version header on every request.
ANTHROPIC_VERSION: Final = "2023-06-01"

#: ``max_tokens`` is required by the Messages API. It is a ceiling on the answer, not a
#: target, and it is stated here rather than guessed per call so that two runs of the
#: same study are never truncated differently.
ANTHROPIC_MAX_TOKENS: Final = 4096

#: The tool that makes citation blocks possible. Without it the response carries no
#: source objects and none can be claimed.
_WEB_SEARCH_TOOL: Final = {
    "type": "web_search_20250305",
    "name": "web_search",
}


class AnthropicAnswerProvider(HttpAnswerProvider):
    """Asks one question of a Claude model, or says why it could not."""

    engine: ClassVar[str] = "ANTHROPIC"
    base_url: ClassVar[str] = ANTHROPIC_BASE_URL
    settings_field: ClassVar[str] = "anthropic_api_key"

    def _build_request(
        self, credential: SecretStr, prompt_text: str, conditions: RunConditions
    ) -> tuple[str, Mapping[str, str], Mapping[str, Any]]:
        body: dict[str, Any] = {
            "model": conditions.model,
            "max_tokens": ANTHROPIC_MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt_text}],
        }
        if conditions.search_mode is SearchMode.BROWSING:
            body["tools"] = [dict(_WEB_SEARCH_TOOL)]
        return (
            f"{self._base_url}{ANTHROPIC_MESSAGES_PATH}",
            {
                "x-api-key": credential.get_secret_value(),
                "anthropic-version": ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            body,
        )

    def _parse(
        self, payload: Mapping[str, Any], *, conditions: RunConditions
    ) -> ProviderAnswer:
        model_version = require_model_version(payload)
        blocks = payload.get("content")
        if not isinstance(blocks, list):
            raise AnswerSchemaError("response has no content array")

        text = "".join(
            block["text"]
            for block in blocks
            if isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
        )
        if not text.strip():
            raise AnswerSchemaError("response carries no text block")

        # 검색을 켰다는 것만으로 "인용을 볼 수 있었다" 고 하지 않는다. 모델이 검색을
        # 쓰지 않기로 했다면 응답에 `web_search_tool_result` 블록이 없고, 그때 어느 출처를
        # 썼는지는 이 응답으로 답할 수 없다 — 출처가 없었다는 뜻이 아니다.
        # Gemini·Perplexity 어댑터가 쓰는 것과 같은 판정이다.
        browsing = conditions.search_mode is SearchMode.BROWSING
        observable = browsing and _has_search_result_block(blocks)
        citations = _read_search_result_urls(blocks) if observable else ()
        support = (
            CitationSupport.STRUCTURED if observable else CitationSupport.NOT_EXPOSED_BY_PROVIDER
        )

        usage = payload.get("usage")
        return ProviderAnswer(
            text=text,
            model=conditions.model,
            model_version=model_version,
            citations=citations,
            citation_support=support,
            input_tokens=read_token_count(usage, "input_tokens", "prompt_tokens"),
            output_tokens=read_token_count(usage, "output_tokens", "completion_tokens"),
        )


def _has_search_result_block(blocks: list[Any]) -> bool:
    """응답이 검색 결과 블록을 실제로 담고 있는가.

    담고 있지 않다면 이 응답은 출처에 대해 아무 말도 하지 않은 것이다. 그것을 "출처
    0건" 으로 옮기면 없는 사실을 만들어 낸다.
    """
    return any(
        isinstance(block, dict) and block.get("type") == "web_search_tool_result"
        for block in blocks
    )


def _read_search_result_urls(blocks: list[Any]) -> tuple[str, ...]:
    """URLs from ``web_search_tool_result`` blocks, in the order they were returned."""
    urls: list[Any] = []
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != "web_search_tool_result":
            continue
        content = block.get("content")
        if not isinstance(content, list):
            continue
        urls.extend(
            entry.get("url")
            for entry in content
            if isinstance(entry, dict) and entry.get("type") == "web_search_result"
        )
    return collect_urls(urls)
