"""프롬프트 집합을 받아들이는 규칙과, 엔진 목록이 무엇을 숨기지 않는가.

DB 나 HTTP 없이 검사한다. 여기서 고정하는 것들은 전부 **저장하기 전에** 결정되는
판단이고, 그것이 이 계층이 존재하는 이유다 — 불균형한 집합이 한 번 저장되면 그것으로
잰 결과가 남는다.
"""

from __future__ import annotations

from datetime import date

import pytest

from veo.contracts.enums import ProviderState
from veo.core.settings import ProviderCredentials
from veo.observations.pricing import DatedPriceTable
from veo.observations.prompts import PromptSet, PromptSetImbalanceError
from veo.observations.providers.base import CostBasis, ModelPrice
from veo.observations.providers.registry import _STATE_LABELS_KO, build_registry
from veo.observations.service import (
    UnknownPromptFieldError,
    build_prompt_set,
    engine_registry,
)


def _prompt(text: str, intent: str, funnel: str = "RESEARCH", subject: str = "NON_BRAND") -> dict:
    return {
        "text": text,
        "intent": intent,
        "funnel": funnel,
        "subject": subject,
        "business_importance": 0.5,
        "locale": "ko-KR",
        "persona": None,
    }


def _balanced() -> list[dict]:
    """균형 검사를 통과하는 최소 집합."""
    return [
        _prompt("레이저 토닝이란 무엇인가요?", "DEFINITION"),
        _prompt("레이저 토닝은 어떻게 받나요?", "HOW_TO"),
        _prompt("강남 레이저 토닝 잘하는 곳 추천해 주세요", "BEST_OR_RECOMMENDED"),
        _prompt("레이저 토닝과 IPL 중 무엇이 나은가요?", "COMPARISON"),
        _prompt("레이저 토닝 가격은 얼마인가요?", "PRICE"),
        _prompt("강남역 근처 피부과를 알려주세요", "LOCAL"),
        _prompt("레이저 토닝 부작용이 있나요?", "TRUST"),
        _prompt("레이저 토닝 후기가 궁금합니다", "TRUST"),
    ]


class TestBalanceIsCheckedBeforeSaving:
    def test_a_balanced_set_is_accepted(self) -> None:
        built = build_prompt_set(name="테스트@1", prompts=_balanced(), exclusions=[])

        assert len(built.prompts) == 8
        assert built.checksum

    def test_a_set_without_trust_questions_is_refused(self) -> None:
        """부작용·후기 질문을 빼면 노출률이 실제보다 높게 나온다.

        브랜드에 유리한 방향의 거짓이라 더 오래 살아남는다. 그래서 저장 전에 막는다.
        """
        without_trust = [item for item in _balanced() if item["intent"] != "TRUST"]

        with pytest.raises(PromptSetImbalanceError) as caught:
            build_prompt_set(name="테스트@1", prompts=without_trust, exclusions=[])

        assert "질문" in str(caught.value)

    def test_the_refusal_says_what_is_missing(self) -> None:
        """'부적합합니다' 로 뭉개면 무엇을 고쳐야 하는지 알 수 없다."""
        too_few = _balanced()[:2]

        with pytest.raises(PromptSetImbalanceError) as caught:
            build_prompt_set(name="테스트@1", prompts=too_few, exclusions=[])

        assert str(caught.value).strip()
        assert "최소" in str(caught.value)


class TestUnknownClassificationsAreRefused:
    def test_an_unknown_intent_is_not_silently_defaulted(self) -> None:
        """조용히 기본값으로 떨어뜨리면 집합의 균형이 실제와 달라진다."""
        prompts = _balanced()
        prompts[0]["intent"] = "AWARENESS"

        with pytest.raises(UnknownPromptFieldError) as caught:
            build_prompt_set(name="테스트@1", prompts=prompts, exclusions=[])

        assert "AWARENESS" in str(caught.value)

    def test_the_refusal_lists_the_allowed_values(self) -> None:
        prompts = _balanced()
        prompts[0]["funnel"] = "없는단계"

        with pytest.raises(UnknownPromptFieldError) as caught:
            build_prompt_set(name="테스트@1", prompts=prompts, exclusions=[])

        assert "RESEARCH" in str(caught.value)


class TestExclusionsAreRecorded:
    def test_an_excluded_question_keeps_its_reason(self) -> None:
        """뺀 것을 기록하지 않으면 집합이 처음부터 그랬던 것처럼 보인다."""
        built = build_prompt_set(
            name="테스트@1",
            prompts=_balanced(),
            exclusions=[{"text": "이 병원 망했나요?", "reason_ko": "질문 자체가 사실이 아님"}],
        )

        assert len(built.exclusions) == 1
        assert built.exclusions[0].reason_ko == "질문 자체가 사실이 아님"

    def test_excluding_a_question_changes_the_checksum(self) -> None:
        """무엇을 뺐는지가 다르면 같은 집합이 아니다."""
        plain = build_prompt_set(name="테스트@1", prompts=_balanced(), exclusions=[])
        with_exclusion = build_prompt_set(
            name="테스트@1",
            prompts=_balanced(),
            exclusions=[{"text": "뺀 질문", "reason_ko": "이유"}],
        )

        assert plain.checksum != with_exclusion.checksum


class TestRebuildDoesNotRevalidate:
    def test_a_stored_set_survives_a_stricter_rule(self) -> None:
        """규칙이 나중에 엄격해졌다고 이미 발행된 집합이 소급해서 거부되면,
        그 집합으로 잰 과거 결과를 다시 열 수 없게 된다."""
        built = build_prompt_set(name="테스트@1", prompts=_balanced(), exclusions=[])
        unbalanced = built.prompts[:2]

        restored = PromptSet.rebuild(name="테스트@1", prompts=unbalanced)

        assert len(restored.prompts) == 2
        assert restored.checksum

    def test_rebuilding_the_same_prompts_gives_the_same_checksum(self) -> None:
        """저장했다 되살려도 지문이 달라지면 비교가 성립하지 않는다."""
        built = build_prompt_set(name="테스트@1", prompts=_balanced(), exclusions=[])

        restored = PromptSet.rebuild(name="테스트@1", prompts=built.prompts)

        assert restored.checksum == built.checksum


class TestTheEngineListHidesNothing:
    def test_engines_without_a_credential_are_still_listed(self) -> None:
        """목록에서 빼면 '여기 있는 게 전부' 로 읽히고, 자격증명만 넣으면 잴 수 있었던
        것을 아무도 모른 채 지나간다."""
        registry = build_registry(credentials=ProviderCredentials())

        states = registry.states()

        assert set(states) >= {"OPENAI", "ANTHROPIC", "GOOGLE_GEMINI", "PERPLEXITY"}

    def test_every_state_can_be_explained_in_korean(self) -> None:
        """'측정 불가' 만 띄우면 고장으로 읽힌다. 왜 못 쓰는지가 함께 있어야 한다.

        어떤 자격증명이 설정돼 있는지는 환경마다 다르므로 상태 값 자체를 단정하지 않는다.
        고정하는 것은 **어떤 상태든 사람이 읽을 문장이 있다**는 것이다.
        """
        registry = build_registry(credentials=ProviderCredentials())

        for state in registry.states().values():
            assert _STATE_LABELS_KO.get(state), f"{state} 에 대한 한국어 설명이 없다"

    def test_a_disabled_engine_is_not_dropped_from_the_list(self) -> None:
        registry = build_registry(credentials=ProviderCredentials())

        states = registry.states()
        disabled = [name for name, state in states.items() if state is not ProviderState.ENABLED]

        # 이 환경에 자격증명이 없는 엔진이 하나라도 있다면, 그것은 목록에 남아 있어야 한다.
        assert set(disabled) <= set(states)
        assert len(states) == 4


class TestThePriceTableIsAttached:
    """가격표가 `packages/model-prices/` 에 있는데 등록소에 연결되어 있지 않았다.

    그래서 모든 호출이 `NO_PRICE_CONFIGURED` 로 기록됐다. "공짜" 가 아니라 "모른다" 이지만,
    예산 상한을 건 실행은 금액을 모르면 돌지 못하므로 예산 기능이 사실상 닫혀 있었다.
    """

    def test_the_registry_carries_a_dated_price_table(self) -> None:
        provider = engine_registry().resolve("OPENAI")

        # 연결 여부는 밖에서 볼 방법이 없다. 이 검사가 곧 그 계약이다.
        table = provider._prices

        assert isinstance(table, DatedPriceTable)

    def test_an_empty_table_reports_no_price_rather_than_zero(self) -> None:
        """모르는 것과 공짜인 것은 다르다. 표에 값이 없으면 0원이 아니라 '가격 미설정' 이다."""
        table = engine_registry().resolve("OPENAI")._prices

        cost, basis = table.cost(
            model="존재하지-않는-모델",
            model_version="존재하지-않는-모델-2026",
            input_tokens=1000,
            output_tokens=500,
        )

        assert cost is None
        assert basis is CostBasis.NO_PRICE_CONFIGURED

    def test_a_stale_table_is_passed_through_not_dropped(self) -> None:
        """오래된 표를 여기서 버리면 '오래됐다' 가 '없다' 로 바뀌어 무엇을 고칠지 알 수 없다."""
        stale = DatedPriceTable(
            version="test",
            as_of=date(2020, 1, 1),
            stale_after_days=90,
            currency="USD",
            prices={"gpt-4o": ModelPrice(input_usd_per_million=1.0, output_usd_per_million=1.0)},
            today=date(2026, 7, 30),
        )

        cost, basis = stale.cost(
            model="gpt-4o", model_version="gpt-4o", input_tokens=1000, output_tokens=0
        )

        assert cost is None
        assert basis is CostBasis.PRICE_TABLE_STALE
