"""The OpenAI adapter, against the Responses API.

Two decisions in here are worth reading before changing anything:

* **Citations are structural or absent.** ``url_citation`` annotations are read when the
  web-search tool was attached. When it was not, the API returns no citation objects at
  all, and this adapter reports :attr:`CitationSupport.NOT_EXPOSED_BY_PROVIDER` rather
  than an empty tuple. "No citations" and "citations were never observable" are different
  facts, and only the first one may be reported as a zero in a citation rate.
* **Nothing is parsed out of prose.** A model that writes ``출처: https://example.com``
  into its answer has not cited anything the API is prepared to attest to. Promoting that
  string to a citation would manufacture the exact evidence a customer is paying VEO to
  verify.

**Partly unverified.** The request and response shapes follow the documented Responses
API. VEO has an OpenAI credential slot but no recorded live response is checked into this
repository, so ``INTEGRATION_REQUEST.md`` lists what should be confirmed against a real
call before the first customer-facing observation run.
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

__all__ = ["OPENAI_BASE_URL", "OPENAI_RESPONSES_PATH", "OpenAIAnswerProvider"]

OPENAI_BASE_URL: Final = "https://api.openai.com"
OPENAI_RESPONSES_PATH: Final = "/v1/responses"

#: The tool that makes ``url_citation`` annotations possible. Without it the response
#: carries no citation objects and none can be claimed.
_WEB_SEARCH_TOOL: Final = {"type": "web_search"}


class OpenAIAnswerProvider(HttpAnswerProvider):
    """Asks one question of an OpenAI model, or says why it could not."""

    engine: ClassVar[str] = "OPENAI"
    base_url: ClassVar[str] = OPENAI_BASE_URL
    settings_field: ClassVar[str] = "openai_api_key"

    def _build_request(
        self, credential: SecretStr, prompt_text: str, conditions: RunConditions
    ) -> tuple[str, Mapping[str, str], Mapping[str, Any]]:
        body: dict[str, Any] = {
            "model": conditions.model,
            "input": prompt_text,
        }
        if conditions.search_mode is SearchMode.BROWSING:
            body["tools"] = [dict(_WEB_SEARCH_TOOL)]
        return (
            f"{self._base_url}{OPENAI_RESPONSES_PATH}",
            {
                "Authorization": f"Bearer {credential.get_secret_value()}",
                "Content-Type": "application/json",
            },
            body,
        )

    def _parse(
        self, payload: Mapping[str, Any], *, conditions: RunConditions
    ) -> ProviderAnswer:
        model_version = require_model_version(payload)
        text, annotations = _read_output(payload)
        if not text.strip():
            raise AnswerSchemaError("response carries no output_text")

        browsing = conditions.search_mode is SearchMode.BROWSING
        citations = _read_url_citations(annotations) if browsing else ()
        support = (
            CitationSupport.STRUCTURED if browsing else CitationSupport.NOT_EXPOSED_BY_PROVIDER
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


def _read_output(payload: Mapping[str, Any]) -> tuple[str, list[Any]]:
    """Concatenated ``output_text`` and every annotation attached to it."""
    output = payload.get("output")
    if not isinstance(output, list):
        raise AnswerSchemaError("response has no output array")

    parts: list[str] = []
    annotations: list[Any] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "output_text":
                continue
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
            block_annotations = block.get("annotations")
            if isinstance(block_annotations, list):
                annotations.extend(block_annotations)
    return "".join(parts), annotations


def _read_url_citations(annotations: list[Any]) -> tuple[str, ...]:
    """URLs from ``url_citation`` annotations, in the order the model produced them."""
    urls = [
        annotation.get("url")
        for annotation in annotations
        if isinstance(annotation, dict) and annotation.get("type") == "url_citation"
    ]
    return collect_urls(urls)
