"""Share of Voice is only honest if both sides are counted by the same code.

Detecting our own brand generously and a competitor's strictly would rig every share
without touching the arithmetic, and the arithmetic is the only part anyone audits. So
this file asserts the shared code path rather than claiming it in a comment.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import pytest

from veo.observations.detection import BrandProfile, detect_answer
from veo.observations.detection import competitors as competitors_module
from veo.observations.detection import mentions as mentions_module
from veo.observations.runs import AccountState, ObservationRun, RunConditions, SearchMode

VENOM = BrandProfile(
    entity_key="venom-dental",
    display_name="베놈치과",
    own_domains=("venomdental.co.kr",),
    address_terms=("강남구", "역삼동"),
)

RIVAL = BrandProfile(
    entity_key="misodream-dental",
    display_name="미소드림치과",
    own_domains=("misodream.co.kr",),
    is_own_brand=False,
    competitor_id="comp-misodream",
)

CONDITIONS = RunConditions(
    engine="OPENAI",
    model="gpt-5",
    model_version="2026-05-01",
    search_mode=SearchMode.BROWSING,
    account_state=AccountState.ANONYMOUS,
)


def test_competitor_detection_calls_the_same_function_as_ours(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    original = mentions_module.detect_mentions

    def spy(text: str, profile: BrandProfile, **kwargs: object) -> object:
        calls.append(profile.entity_key)
        return original(text, profile, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(mentions_module, "detect_mentions", spy)
    competitors_module.detect_competitor_mentions("베놈치과와 미소드림치과.", (RIVAL,))
    assert calls == ["misodream-dental"]


def test_swapping_the_roles_produces_the_same_finding() -> None:
    text = "강남에서는 베놈치과가 자주 언급됩니다."
    as_own = mentions_module.detect_mentions(text, VENOM)
    as_rival = mentions_module.detect_mentions(
        text, dataclasses.replace(VENOM, is_own_brand=False, competitor_id="comp-x")
    )
    assert as_own.verdict is as_rival.verdict
    assert as_own.raw_occurrence_count == as_rival.raw_occurrence_count
    assert as_own.spans == as_rival.spans
    assert as_own.match_confidence == as_rival.match_confidence


def test_detect_answer_reports_both_sides() -> None:
    text = "교정은 미소드림치과가, 임플란트는 베놈치과가 자주 언급됩니다."
    result = detect_answer(text, own=VENOM, competitors=(RIVAL,))
    assert result.own.verdict.name == "CONFIRMED"
    assert len(result.competitors) == 1
    assert result.competitors[0].verdict.name == "CONFIRMED"
    assert result.competitors[0].competitor_id == "comp-misodream"


def test_a_competitor_is_never_counted_as_us() -> None:
    result = detect_answer("미소드림치과는 교정 전문입니다.", own=VENOM, competitors=(RIVAL,))
    assert result.brand_mentioned is False
    assert result.competitors[0].verdict.name == "CONFIRMED"


def test_the_result_satisfies_the_observation_run_invariants() -> None:
    text = "강남 임플란트 자료입니다."
    result = detect_answer(
        text,
        own=VENOM,
        competitors=(RIVAL,),
        citations=("https://blog.venomdental.co.kr/implant",),
    )
    assert result.brand_cited is True
    run = ObservationRun(
        run_id="r-1",
        prompt_id="p-1",
        conditions=CONDITIONS,
        executed_at=datetime(2026, 7, 28, tzinfo=UTC),
        raw_answer_ref="storage://answers/r-1",
        raw_answer_hash="a" * 64,
        brand_mentioned=result.brand_mentioned,
        brand_cited=result.brand_cited,
        citations=result.own_citation_urls,
        mentioned_entities=result.mentioned_entity_keys,
    )
    assert run.brand_mentioned is True


def test_a_citation_can_never_exist_without_a_mention() -> None:
    # runs.py refuses a cited-but-unmentioned run. The detector must never produce one,
    # including for a generic name that would otherwise sit below the review threshold.
    generic = BrandProfile(
        entity_key="seoul-dental",
        display_name="서울치과",
        own_domains=("seouldental-gangnam.co.kr",),
        address_terms=("강남구",),
    )
    result = detect_answer(
        "부산 해운대구 치과 정보입니다.",
        own=generic,
        citations=("https://seouldental-gangnam.co.kr/price",),
    )
    assert result.brand_cited is True
    assert result.brand_mentioned is True


def test_review_queue_collects_everything_the_detector_refused_to_decide() -> None:
    generic = BrandProfile(
        entity_key="seoul-dental",
        display_name="서울치과",
        address_terms=("강남구",),
    )
    result = detect_answer("부산 해운대구에서는 서울치과를 많이 갑니다.", own=generic)
    assert result.brand_mentioned is False
    assert [event.entity_key for event in result.needs_review] == ["seoul-dental"]


def test_detection_is_deterministic() -> None:
    text = "교정은 미소드림치과가, 임플란트는 베놈치과가 자주 언급됩니다."
    first = detect_answer(text, own=VENOM, competitors=(RIVAL,))
    for _ in range(5):
        assert detect_answer(text, own=VENOM, competitors=(RIVAL,)) == first
