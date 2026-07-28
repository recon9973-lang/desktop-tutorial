"""The Google Gemini adapter, against the Generative Language API.

Gemini matters to VEO more than its global share suggests: consumer use in Korea is high,
and a visibility report that watched ChatGPT alone would be half-blind for exactly the
clinics this product is sold to.

Two decisions in here follow directly from the honesty rules:

* **Grounding is a search mode, not a footnote.** A grounded answer and an ungrounded one
  draw on different sources and frequently reach different conclusions, so the two are
  different measurements. Rather than inventing a parallel concept, grounding is mapped
  onto :class:`~veo.observations.runs.SearchMode`: ``BROWSING`` attaches the Google Search
  tool, ``NO_BROWSING`` does not. ``RunConditions.fingerprint`` already keeps the two
  apart, so :func:`~veo.observations.runs.aggregate_rate` refuses to pool them.
* **Citations come from grounding metadata or not at all.** ``groundingChunks[].web.uri``
  is read structurally. A response without grounding metadata carries no citation objects,
  so this adapter reports :attr:`CitationSupport.NOT_EXPOSED_BY_PROVIDER` and no
  citations — including when the search tool *was* attached, because "the model answered
  without retrieving" and "the model retrieved and we cannot see from what" are not
  distinguishable from the response, and only one of them would justify a zero in a
  citation rate. URLs sitting in the prose are never promoted.

**Unverified.** VEO has a Gemini credential slot but no recorded live response is checked
into this repository. The request shape, the ``x-goog-api-key`` header, the grounding
metadata layout and the ``usageMetadata`` key names follow the published documentation and
have not been exercised against the real service; ``INTEGRATION_REQUEST.md`` lists what to
confirm before the first customer-facing run.
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
    "GEMINI_BASE_URL",
    "GEMINI_MODELS_PATH",
    "GeminiAnswerProvider",
]

GEMINI_BASE_URL: Final = "https://generativelanguage.googleapis.com"
GEMINI_MODELS_PATH: Final = "/v1beta/models"

#: The tool that produces grounding metadata. Without it a response carries no source
#: objects and nothing can be cited.
_GOOGLE_SEARCH_TOOL: Final[dict[str, Any]] = {"google_search": {}}


class GeminiAnswerProvider(HttpAnswerProvider):
    """Asks one question of a Gemini model, or says why it could not."""

    engine: ClassVar[str] = "GOOGLE_GEMINI"
    base_url: ClassVar[str] = GEMINI_BASE_URL
    settings_field: ClassVar[str] = "google_gemini_api_key"

    def _build_request(
        self, credential: SecretStr, prompt_text: str, conditions: RunConditions
    ) -> tuple[str, Mapping[str, str], Mapping[str, Any]]:
        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt_text}]}]
        }
        if conditions.search_mode is SearchMode.BROWSING:
            body["tools"] = [dict(_GOOGLE_SEARCH_TOOL)]
        return (
            # The key goes in a header, never in the query string this API also accepts:
            # a URL is logged by every proxy on the path.
            f"{self._base_url}{GEMINI_MODELS_PATH}/{conditions.model}:generateContent",
            {
                "x-goog-api-key": credential.get_secret_value(),
                "Content-Type": "application/json",
            },
            body,
        )

    def _parse(
        self, payload: Mapping[str, Any], *, conditions: RunConditions
    ) -> ProviderAnswer:
        model_version = require_model_version(payload, "modelVersion", "model")
        candidate = _first_candidate(payload)
        text = _read_text(candidate)
        if not text.strip():
            raise AnswerSchemaError("response carries no text part")

        grounding = candidate.get("groundingMetadata")
        if conditions.search_mode is SearchMode.BROWSING and isinstance(grounding, dict):
            citations = _read_grounding_uris(grounding)
            support = CitationSupport.STRUCTURED
        else:
            citations = ()
            support = CitationSupport.NOT_EXPOSED_BY_PROVIDER

        usage = payload.get("usageMetadata")
        return ProviderAnswer(
            text=text,
            model=conditions.model,
            model_version=model_version,
            citations=citations,
            citation_support=support,
            input_tokens=read_token_count(usage, "promptTokenCount", "input_tokens"),
            output_tokens=read_token_count(usage, "candidatesTokenCount", "output_tokens"),
        )


def _first_candidate(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise AnswerSchemaError("response has no candidates array")
    first = candidates[0]
    if not isinstance(first, dict):
        raise AnswerSchemaError("candidates[0] is not an object")
    return first


def _read_text(candidate: Mapping[str, Any]) -> str:
    content = candidate.get("content")
    if not isinstance(content, dict):
        raise AnswerSchemaError("candidates[0] has no content object")
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise AnswerSchemaError("candidates[0].content has no parts array")
    return "".join(
        part["text"]
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    )


def _read_grounding_uris(grounding: Mapping[str, Any]) -> tuple[str, ...]:
    """Source URIs from ``groundingChunks``, in the order the API returned them."""
    chunks = grounding.get("groundingChunks")
    if not isinstance(chunks, list):
        return ()
    uris: list[Any] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        web = chunk.get("web")
        if isinstance(web, dict):
            uris.append(web.get("uri"))
    return collect_urls(uris)
