"""Engine name to provider, and a per-engine state nobody has to guess at.

An observation report that quietly omits an engine is worse than one that says the engine
could not be reached: the first reads as "we looked everywhere", the second is true. So
the registry always reports *every* engine VEO knows about together with its state, and
an unknown engine name is refused rather than skipped.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Final

import httpx

from veo.contracts.enums import ProviderState
from veo.core.settings import ProviderCredentials
from veo.observations.providers.anthropic import AnthropicAnswerProvider
from veo.observations.providers.base import AnswerProvider, HttpAnswerProvider, PriceTable
from veo.observations.providers.gemini import GeminiAnswerProvider
from veo.observations.providers.openai import OpenAIAnswerProvider
from veo.observations.providers.perplexity import PerplexityAnswerProvider

__all__ = [
    "PROVIDER_CLASSES",
    "ProviderRegistry",
    "UnknownEngineError",
    "build_registry",
]

#: Every engine VEO knows how to ask, in one place.
#:
#: :func:`build_registry` iterates this tuple and the provider test suite parametrises
#: over it, so an engine added here is registered *and* covered by the credential checks
#: automatically. Adding an adapter without adding it here would make it invisible to
#: both — which is how an engine ends up shipping with no "opens no connection" test.
PROVIDER_CLASSES: Final[tuple[type[HttpAnswerProvider], ...]] = (
    OpenAIAnswerProvider,
    GeminiAnswerProvider,
    PerplexityAnswerProvider,
    AnthropicAnswerProvider,
)

_STATE_LABELS_KO: Mapping[ProviderState, str] = {
    ProviderState.ENABLED: "사용 가능",
    ProviderState.DISABLED_NO_CREDENTIAL: "자격증명 없음 — 호출하지 않으며 '측정 불가'로 남습니다",
    ProviderState.DISABLED_INVALID_CREDENTIAL: (
        "자격증명 자리에 자리표시자가 들어 있음 — 호출하지 않으며 '측정 불가'로 남습니다"
    ),
    ProviderState.DISABLED_BY_CONFIG: "설정에 의해 비활성 — '측정 불가'로 남습니다",
    ProviderState.DEGRADED: "불안정 — 일부 실행이 '측정 불가'가 될 수 있습니다",
    ProviderState.CIRCUIT_OPEN: "연속 실패로 호출을 일시 차단 — 지금은 '측정 불가'입니다",
}


class UnknownEngineError(KeyError):
    """An engine name VEO has no adapter for."""


class ProviderRegistry:
    """The engines VEO can ask, and what each of them can do right now."""

    def __init__(self, providers: Iterable[AnswerProvider]) -> None:
        resolved: dict[str, AnswerProvider] = {}
        for provider in providers:
            key = provider.engine.upper()
            if key in resolved:
                raise ValueError(f"두 제공자가 같은 엔진 이름을 주장합니다: {key}")
            resolved[key] = provider
        self._providers = resolved

    def __repr__(self) -> str:
        return f"<ProviderRegistry engines={','.join(self.engines())}>"

    def engines(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    def resolve(self, engine: str) -> AnswerProvider:
        try:
            return self._providers[engine.upper()]
        except KeyError:
            raise UnknownEngineError(
                f"VEO 가 아는 엔진이 아닙니다: {engine} (가능: {', '.join(self.engines())})"
            ) from None

    def states(self) -> dict[str, ProviderState]:
        """Every engine's state — including the ones that cannot answer."""
        return {name: provider.state for name, provider in sorted(self._providers.items())}

    def enabled_engines(self) -> tuple[str, ...]:
        return tuple(
            name for name, state in self.states().items() if state is ProviderState.ENABLED
        )

    def describe_ko(self) -> str:
        """One line per engine, readable beside a report."""
        return "\n".join(
            f"{name}: {_STATE_LABELS_KO.get(state, str(state))}"
            for name, state in self.states().items()
        )


def build_registry(
    *,
    credentials: ProviderCredentials | None = None,
    transport: httpx.BaseTransport | None = None,
    price_table: PriceTable | None = None,
) -> ProviderRegistry:
    """Every engine in :data:`PROVIDER_CLASSES`, wired the same way.

    Engines with no credential are still registered. An engine missing from the registry
    disappears from the report; a disabled engine appears in it with a stated reason, and
    that difference is the whole point — a report that silently drops Gemini reads as
    "we looked everywhere".
    """
    return ProviderRegistry(
        [
            provider_class.from_settings(
                credentials, transport=transport, price_table=price_table
            )
            for provider_class in PROVIDER_CLASSES
        ]
    )
