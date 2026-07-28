"""Resolving an engine name, and reporting honestly what each engine can do today."""

from __future__ import annotations

import httpx
import pytest
from pydantic import SecretStr
from tests.observations.providers.synthetic import (
    credentials_with,
    no_credentials,
    openai_payload,
    placeholder_credentials,
)

from veo.contracts.enums import ProviderState
from veo.observations.providers.gemini import GeminiAnswerProvider
from veo.observations.providers.openai import OpenAIAnswerProvider
from veo.observations.providers.registry import (
    PROVIDER_CLASSES,
    ProviderRegistry,
    UnknownEngineError,
    build_registry,
)

ALL_ENGINES = {"OPENAI", "GOOGLE_GEMINI", "PERPLEXITY", "ANTHROPIC"}


def handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=openai_payload())


def test_an_engine_name_resolves_to_its_provider() -> None:
    provider = OpenAIAnswerProvider(credential=SecretStr("synthetic-openai-key"))
    registry = ProviderRegistry([provider])
    assert registry.resolve("OPENAI") is provider


def test_engine_names_are_matched_case_insensitively() -> None:
    provider = GeminiAnswerProvider(credential=None)
    registry = ProviderRegistry([provider])
    assert registry.resolve("google_gemini") is provider


def test_an_unknown_engine_is_refused_rather_than_silently_skipped() -> None:
    registry = ProviderRegistry([OpenAIAnswerProvider(credential=None)])
    with pytest.raises(UnknownEngineError):
        registry.resolve("GROK")


def test_two_providers_cannot_claim_the_same_engine() -> None:
    with pytest.raises(ValueError, match="OPENAI"):
        ProviderRegistry(
            [OpenAIAnswerProvider(credential=None), OpenAIAnswerProvider(credential=None)]
        )


def test_build_registry_wires_every_engine_veo_knows() -> None:
    registry = build_registry(
        credentials=no_credentials(), transport=httpx.MockTransport(handler)
    )
    assert set(registry.engines()) == ALL_ENGINES
    assert set(registry.engines()) == {provider.engine for provider in PROVIDER_CLASSES}


def test_every_engine_reports_a_state_even_when_it_cannot_answer() -> None:
    registry = build_registry(credentials=no_credentials())
    assert registry.states() == dict.fromkeys(
        ALL_ENGINES, ProviderState.DISABLED_NO_CREDENTIAL
    )


def test_a_placeholder_credential_is_reported_as_its_own_state() -> None:
    registry = build_registry(credentials=placeholder_credentials())
    assert registry.states() == dict.fromkeys(
        ALL_ENGINES, ProviderState.DISABLED_INVALID_CREDENTIAL
    )


def test_enabled_engines_lists_only_the_ones_that_can_answer() -> None:
    credentials = no_credentials().model_copy(
        update={"google_gemini_api_key": SecretStr("synthetic-gemini-key")}
    )
    registry = build_registry(
        credentials=credentials, transport=httpx.MockTransport(handler)
    )
    assert registry.enabled_engines() == ("GOOGLE_GEMINI",)


def test_all_engines_enabled_when_all_are_configured() -> None:
    registry = build_registry(credentials=credentials_with(SecretStr("synthetic-key")))
    assert set(registry.enabled_engines()) == ALL_ENGINES


def test_the_registry_explains_each_engine_in_korean() -> None:
    description = build_registry(credentials=no_credentials()).describe_ko()
    for engine in ALL_ENGINES:
        assert engine in description
    assert "측정" in description
