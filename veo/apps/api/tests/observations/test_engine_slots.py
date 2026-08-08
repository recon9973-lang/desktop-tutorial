"""한 엔진을 검색 켬·끔 두 조건으로 돌릴 수 있는가.

이 파일이 지키는 결함: 실행 계획이 **엔진 이름 하나로** 조건을 묶으면, 같은 엔진의
검색 켬과 끔 중 뒤에 넣은 것이 앞엣것을 덮는다. 요청은 두 모드인데 실행은 한 모드만
되고, 덮였다는 사실은 어디에도 남지 않는다. 그러면 "검색을 끄고도 이만큼 나왔다" 는
문장이 검색을 켠 숫자로 채워진다 — 고객에게 그대로 보이는 자리다.

저장 쪽은 처음부터 셋을 구분했다: `ai_engines` 는 (제공자, 모델, 검색모드) 로 유일하다
(ADR 0010). 나뉘지 않던 곳은 실행 계획의 표 하나뿐이었다.
"""

from __future__ import annotations

import pytest

from veo.observations.execution import DuplicateEngineSlotError, EngineChoice, _conditions_of
from veo.observations.runs import AccountState, RunConditions, SearchMode


def _condition(mode: SearchMode) -> RunConditions:
    return RunConditions(
        engine="OPENAI",
        model="gpt-5",
        model_version="요청 시점 미상",
        search_mode=mode,
        account_state=AccountState.ANONYMOUS,
        locale="ko-KR",
    )


def test_the_two_search_modes_of_one_engine_are_different_slots() -> None:
    on = _condition(SearchMode.BROWSING)
    off = _condition(SearchMode.NO_BROWSING)

    assert on.slot != off.slot
    assert on.engine == off.engine, "엔진은 같다 — 갈라지는 것은 조건이다"


def test_one_engine_asked_in_both_modes_becomes_two_slots() -> None:
    built = _conditions_of(
        [
            EngineChoice(engine="OPENAI", model="gpt-5", search_mode=SearchMode.BROWSING),
            EngineChoice(engine="OPENAI", model="gpt-5", search_mode=SearchMode.NO_BROWSING),
        ],
        locale="ko-KR",
    )

    assert len(built) == 2, "엔진 이름으로 묶으면 여기서 1이 된다 — 절반만 실행된다"
    assert {c.search_mode for c in built.values()} == {
        SearchMode.BROWSING,
        SearchMode.NO_BROWSING,
    }


def test_the_same_slot_twice_is_refused() -> None:
    """조용히 합치면 요청한 것보다 적게 돌고도 계획을 다 채운 것으로 기록된다."""
    with pytest.raises(DuplicateEngineSlotError):
        _conditions_of(
            [
                EngineChoice(engine="OPENAI", model="gpt-5", search_mode=SearchMode.BROWSING),
                EngineChoice(engine="OPENAI", model="gpt-5", search_mode=SearchMode.BROWSING),
            ],
            locale="ko-KR",
        )


def test_different_models_of_one_engine_stay_apart() -> None:
    """모델이 다르면 인용을 돌려주는지부터 다르다(실측: gpt-5 는 준다, gpt-4o-mini 는 안 준다)."""
    built = _conditions_of(
        [
            EngineChoice(engine="OPENAI", model="gpt-5", search_mode=SearchMode.BROWSING),
            EngineChoice(engine="OPENAI", model="gpt-4o", search_mode=SearchMode.BROWSING),
        ],
        locale="ko-KR",
    )

    assert len(built) == 2
