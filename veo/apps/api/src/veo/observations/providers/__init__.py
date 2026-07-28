"""Adapters for the AI answer engines VEO observes.

One rule shapes every module in here: **VEO never fabricates an answer.** A provider with
no credential is ``DISABLED_NO_CREDENTIAL`` and opens no connection, a provider that fails
degrades to ``UNKNOWN`` with a stated reason, and both outcomes reach
:mod:`veo.observations.runner` as an error-coded run rather than as an observation that
the brand was absent.

All four engines — OpenAI, Google Gemini, Perplexity and Anthropic — take their credential
from ``ProviderCredentials`` in ``core/settings.py``. Whichever ones have no key
configured are still registered, so they appear in a report as "측정 불가" with a stated
reason rather than quietly vanishing from it.

Nothing is re-exported from :mod:`veo.observations` itself — that package's ``__init__``
is a fixed contract owned elsewhere. Import from the modules here directly.
"""

from veo.observations.providers.anthropic import AnthropicAnswerProvider
from veo.observations.providers.base import (
    DEFAULT_PRICE_TABLE,
    AnswerProvider,
    AnswerProviderError,
    CitationSupport,
    CostBasis,
    MeteredOutcome,
    ModelPrice,
    PriceTable,
    ProviderAnswer,
)
from veo.observations.providers.gemini import GeminiAnswerProvider
from veo.observations.providers.openai import OpenAIAnswerProvider
from veo.observations.providers.perplexity import PerplexityAnswerProvider
from veo.observations.providers.registry import (
    PROVIDER_CLASSES,
    ProviderRegistry,
    UnknownEngineError,
    build_registry,
)
from veo.observations.providers.storage import (
    AnswerRecordKey,
    InMemoryAnswerStore,
    RecordedAnswer,
    RecordedAnswerStore,
    StoredAnswer,
)

__all__ = [
    "DEFAULT_PRICE_TABLE",
    "PROVIDER_CLASSES",
    "AnswerProvider",
    "AnswerProviderError",
    "AnswerRecordKey",
    "AnthropicAnswerProvider",
    "CitationSupport",
    "CostBasis",
    "GeminiAnswerProvider",
    "InMemoryAnswerStore",
    "MeteredOutcome",
    "ModelPrice",
    "OpenAIAnswerProvider",
    "PerplexityAnswerProvider",
    "PriceTable",
    "ProviderAnswer",
    "ProviderRegistry",
    "RecordedAnswer",
    "RecordedAnswerStore",
    "StoredAnswer",
    "UnknownEngineError",
    "build_registry",
]
