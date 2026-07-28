"""Every fixture case, run end to end through the detector.

The fixtures are the readable half of the contract: a reviewer can open one JSON file and
see the Korean answer, the declaration, and the verdict it must produce.
"""

from __future__ import annotations

import pytest
from tests.observations.detection.support import DetectionCase, case_names, load_case

from veo.observations.detection import detect_answer
from veo.observations.detection.mentions import SpanSource

EXPECTED_CASES = {
    "cited_via_redirect",
    "competitor_mentioned",
    "inside_competitor_sentence",
    "no_mention",
    "particle_forms",
    "plain_mention",
    "same_name_other_business",
    "third_party_article",
}


def run_case(case: DetectionCase) -> object:
    return detect_answer(
        case.answer_text,
        own=case.brand,
        competitors=case.competitors,
        citations=case.citations,
    )


def test_the_fixture_set_covers_the_cases_the_module_promises() -> None:
    assert set(case_names()) == EXPECTED_CASES


@pytest.mark.parametrize("name", sorted(EXPECTED_CASES))
def test_case_matches_its_expected_verdict(name: str) -> None:
    case = load_case(name)
    result = detect_answer(
        case.answer_text,
        own=case.brand,
        competitors=case.competitors,
        citations=case.citations,
    )
    expected = case.expected["own"]

    assert result.own.verdict.value == expected["verdict"], case.purpose_ko
    assert result.own.raw_occurrence_count == expected["raw_occurrence_count"], case.purpose_ko
    assert result.own.needs_human_disambiguation == expected["needs_human_disambiguation"]
    assert result.brand_cited == expected["brand_cited"], case.purpose_ko

    by_competitor = {event.competitor_id: event for event in result.competitors}
    for competitor_id, want in case.expected["competitors"].items():
        event = by_competitor[competitor_id]
        assert event.verdict.value == want["verdict"], case.purpose_ko
        assert event.raw_occurrence_count == want["raw_occurrence_count"], case.purpose_ko
        assert event.needs_human_disambiguation == want["needs_human_disambiguation"]


@pytest.mark.parametrize("name", sorted(EXPECTED_CASES))
def test_every_span_quotes_what_the_machine_actually_saw(name: str) -> None:
    case = load_case(name)
    result = detect_answer(
        case.answer_text,
        own=case.brand,
        competitors=case.competitors,
        citations=case.citations,
    )
    for event in (result.own, *result.competitors):
        for span in event.spans:
            haystack = (
                case.answer_text if span.source is SpanSource.ANSWER_TEXT else span.source_ref
            )
            assert haystack[span.start : span.end] == span.quote


@pytest.mark.parametrize("name", sorted(EXPECTED_CASES))
def test_a_cited_brand_is_always_a_mentioned_brand(name: str) -> None:
    case = load_case(name)
    result = detect_answer(
        case.answer_text,
        own=case.brand,
        competitors=case.competitors,
        citations=case.citations,
    )
    if result.brand_cited:
        assert result.brand_mentioned


@pytest.mark.parametrize("name", sorted(EXPECTED_CASES))
def test_repeating_a_case_changes_nothing(name: str) -> None:
    case = load_case(name)
    first = run_case(case)
    assert run_case(case) == first
