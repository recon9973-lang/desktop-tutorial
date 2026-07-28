"""Share of Voice — observed AI visibility only, and never a stand-in for readiness.

Three properties are worth more than the arithmetic:

* a zero denominator is ``데이터 없음``. "Nobody was cited" is not "we hold 0% share";
* the number is meaningless without the set it was computed over, so the set travels
  with it and so does a note saying the number moves when the set changes;
* nothing in this module knows what a readiness score is.
"""

from __future__ import annotations

import inspect

import pytest
from competitor_support import load_fixture

from veo.competitors import sov as sov_module
from veo.competitors.sov import (
    NO_DATA_KO,
    ObservedVisibility,
    ParticipantVisibility,
    share_of_voice,
)


def observation(*, drop: str | None = None) -> ObservedVisibility:
    fixture = load_fixture("sov_counts.json")
    participants = tuple(
        ParticipantVisibility(
            key=entry["key"],
            label_ko=entry["label_ko"],
            is_own_brand=entry["is_own_brand"],
            cited_answer_count=entry["cited_answer_count"],
            mentioned_answer_count=entry["mentioned_answer_count"],
            won_prompt_count=entry["won_prompt_count"],
        )
        for entry in fixture["participants"]
        if entry["key"] != drop
    )
    return ObservedVisibility(
        prompt_set_label="치과 비급여 프롬프트 세트 v3",
        engine_labels=("chatgpt/web_search",),
        observed_answer_count=fixture["observed_answer_count"],
        decided_prompt_count=fixture["decided_prompt_count"],
        participants=participants,
    )


def share(report: object, key: str, metric: str) -> object:
    entry = next(p for p in report.participants if p.key == key)  # type: ignore[attr-defined]
    return getattr(entry, metric)


# --------------------------------------------------------------------------- #
# Arithmetic, against numbers a person computed
# --------------------------------------------------------------------------- #


def test_citation_and_mention_share_match_the_hand_computed_fixture() -> None:
    expected = load_fixture("sov_counts.json")["expected"]
    report = share_of_voice(observation())

    for key, value in expected["citation_share"].items():
        metric = share(report, key, "citation_sov")
        assert metric.share == pytest.approx(value), key  # type: ignore[attr-defined]
        assert metric.denominator == expected["citation_denominator"]  # type: ignore[attr-defined]

    for key, value in expected["mention_share"].items():
        metric = share(report, key, "mention_sov")
        assert metric.share == pytest.approx(value), key  # type: ignore[attr-defined]
        assert metric.denominator == expected["mention_denominator"]  # type: ignore[attr-defined]


def test_the_winning_prompt_rate_is_a_rate_over_decided_prompts_not_a_share() -> None:
    expected = load_fixture("sov_counts.json")["expected"]
    report = share_of_voice(observation())

    for key, value in expected["winning_prompt_rate"].items():
        metric = share(report, key, "winning_prompt_rate")
        assert metric.share == pytest.approx(value), key  # type: ignore[attr-defined]
        assert metric.denominator == expected["winning_prompt_denominator"]  # type: ignore[attr-defined]

    # A rate, not a share: the parts do not have to add to one.
    total = sum(
        share(report, key, "winning_prompt_rate").share  # type: ignore[attr-defined]
        for key in expected["winning_prompt_rate"]
    )
    assert total == pytest.approx(0.9)


def test_percentages_are_rendered_for_a_korean_reader() -> None:
    report = share_of_voice(observation())
    assert share(report, "us", "citation_sov").display_ko == "30.0%"  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# A zero denominator is not zero percent
# --------------------------------------------------------------------------- #


def test_nobody_cited_is_data_missing_not_a_zero_share() -> None:
    silent = ObservedVisibility(
        prompt_set_label="세트",
        engine_labels=("chatgpt/web_search",),
        observed_answer_count=12,
        decided_prompt_count=0,
        participants=(
            ParticipantVisibility(
                key="us",
                label_ko="우리 사이트",
                is_own_brand=True,
                cited_answer_count=0,
                mentioned_answer_count=0,
                won_prompt_count=0,
            ),
            ParticipantVisibility(
                key="rival",
                label_ko="경쟁사 A",
                is_own_brand=False,
                cited_answer_count=0,
                mentioned_answer_count=0,
                won_prompt_count=0,
            ),
        ),
    )

    report = share_of_voice(silent)
    for metric_name in ("citation_sov", "mention_sov", "winning_prompt_rate"):
        metric = share(report, "us", metric_name)
        assert metric.share is None, metric_name  # type: ignore[attr-defined]
        assert metric.display_ko == NO_DATA_KO, metric_name  # type: ignore[attr-defined]
        assert metric.unavailable_reason_ko, metric_name  # type: ignore[attr-defined]
        assert "0%" not in metric.display_ko  # type: ignore[attr-defined]


def test_a_participant_nobody_cited_inside_a_set_that_was_cited_really_is_zero() -> None:
    """Zero *is* the answer when the denominator exists. Only an empty one is 데이터 없음."""
    seen = ObservedVisibility(
        prompt_set_label="세트",
        engine_labels=("chatgpt/web_search",),
        observed_answer_count=10,
        decided_prompt_count=4,
        participants=(
            ParticipantVisibility(
                key="us",
                label_ko="우리 사이트",
                is_own_brand=True,
                cited_answer_count=0,
                mentioned_answer_count=1,
                won_prompt_count=0,
            ),
            ParticipantVisibility(
                key="rival",
                label_ko="경쟁사 A",
                is_own_brand=False,
                cited_answer_count=6,
                mentioned_answer_count=7,
                won_prompt_count=4,
            ),
        ),
    )

    metric = share(share_of_voice(seen), "us", "citation_sov")
    assert metric.share == pytest.approx(0.0)  # type: ignore[attr-defined]
    assert metric.display_ko == "0.0%"  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# The set is part of the number
# --------------------------------------------------------------------------- #


def test_dropping_a_competitor_changes_every_share() -> None:
    fixture = load_fixture("sov_counts.json")
    smaller = fixture["without_competitor_a"]

    full = share_of_voice(observation())
    reduced = share_of_voice(observation(drop="competitor-a"))

    assert share(full, "us", "citation_sov").share == pytest.approx(0.3)  # type: ignore[attr-defined]
    assert share(reduced, "us", "citation_sov").share == pytest.approx(  # type: ignore[attr-defined]
        smaller["citation_share"]["us"]
    )
    assert share(reduced, "us", "citation_sov").denominator == (  # type: ignore[attr-defined]
        smaller["citation_denominator"]
    )


def test_the_winning_prompt_rate_does_not_move_when_the_set_shrinks() -> None:
    """Its denominator is prompts, not the set's own totals — so it must stay put."""
    fixture = load_fixture("sov_counts.json")["without_competitor_a"]
    reduced = share_of_voice(observation(drop="competitor-a"))

    assert share(reduced, "us", "winning_prompt_rate").share == pytest.approx(  # type: ignore[attr-defined]
        fixture["winning_prompt_rate"]["us"]
    )


def test_every_report_carries_its_comparison_set_and_the_warning_about_it() -> None:
    report = share_of_voice(observation())

    assert [member.key for member in report.comparison_set] == [
        "us",
        "competitor-a",
        "competitor-b",
    ]
    assert "집합" in report.comparison_set_note_ko
    assert "달라" in report.comparison_set_note_ko


def test_the_set_note_survives_serialisation() -> None:
    document = share_of_voice(observation()).as_dict()
    assert document["comparison_set_note_ko"]
    assert len(document["comparison_set"]) == 3
    assert document["participants"][0]["citation_sov"]["display_ko"] == "30.0%"


# --------------------------------------------------------------------------- #
# Observed visibility and readiness never touch
# --------------------------------------------------------------------------- #


def test_the_module_knows_nothing_about_readiness_scores() -> None:
    source = inspect.getsource(sov_module)
    for forbidden in ("veo.scoring", "veo.compare", "readiness", "overall_score"):
        assert forbidden not in source, forbidden


def test_the_report_states_that_it_is_not_a_readiness_score() -> None:
    report = share_of_voice(observation())
    assert "준비도" in report.scope_ko


# --------------------------------------------------------------------------- #
# Impossible observations are refused, not averaged
# --------------------------------------------------------------------------- #


def test_more_citations_than_answers_is_refused() -> None:
    with pytest.raises(ValueError, match="응답 수"):
        ObservedVisibility(
            prompt_set_label="세트",
            engine_labels=("e",),
            observed_answer_count=3,
            decided_prompt_count=1,
            participants=(
                ParticipantVisibility(
                    key="us",
                    label_ko="우리",
                    is_own_brand=True,
                    cited_answer_count=4,
                    mentioned_answer_count=0,
                    won_prompt_count=0,
                ),
            ),
        )


def test_more_wins_than_decided_prompts_is_refused() -> None:
    with pytest.raises(ValueError, match="프롬프트"):
        ObservedVisibility(
            prompt_set_label="세트",
            engine_labels=("e",),
            observed_answer_count=10,
            decided_prompt_count=2,
            participants=(
                ParticipantVisibility(
                    key="us",
                    label_ko="우리",
                    is_own_brand=True,
                    cited_answer_count=1,
                    mentioned_answer_count=1,
                    won_prompt_count=2,
                ),
                ParticipantVisibility(
                    key="rival",
                    label_ko="경쟁",
                    is_own_brand=False,
                    cited_answer_count=1,
                    mentioned_answer_count=1,
                    won_prompt_count=2,
                ),
            ),
        )


def test_a_negative_count_is_refused() -> None:
    with pytest.raises(ValueError, match="음수"):
        ParticipantVisibility(
            key="us",
            label_ko="우리",
            is_own_brand=True,
            cited_answer_count=-1,
            mentioned_answer_count=0,
            won_prompt_count=0,
        )


def test_an_empty_set_is_refused() -> None:
    with pytest.raises(ValueError, match="비교 집합"):
        ObservedVisibility(
            prompt_set_label="세트",
            engine_labels=("e",),
            observed_answer_count=1,
            decided_prompt_count=1,
            participants=(),
        )
