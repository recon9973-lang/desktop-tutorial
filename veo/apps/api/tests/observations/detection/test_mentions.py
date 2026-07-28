"""One mention event per brand per answer, and never a guess.

The three rules this file pins down:

* An answer that says the name five times is **one** mention with a raw count of five.
  Counting occurrences inflates every rate downstream and nothing further along can undo it.
* A citation of our own URL is a mention even with no prose, because the URL names us.
* When the rules cannot tell whether the name is *this* customer, the verdict is
  ``NEEDS_REVIEW`` — never a decision.
"""

from __future__ import annotations

from pathlib import Path

from veo.observations.detection import BrandProfile
from veo.observations.detection.citations import match_citations
from veo.observations.detection.mentions import (
    MentionVerdict,
    SpanSource,
    detect_mentions,
)

VENOM = BrandProfile(
    entity_key="venom-dental",
    display_name="베놈치과",
    aliases=("VENOM치과",),
    own_domains=("venomdental.co.kr",),
    address_terms=("강남구", "역삼동"),
    phone_numbers=("02-555-1234",),
)

SEOUL = BrandProfile(
    entity_key="seoul-dental-gangnam",
    display_name="서울치과",
    own_domains=("seouldental-gangnam.co.kr",),
    address_terms=("강남구", "역삼동"),
)

MODULE_DIR = Path(__file__).resolve().parents[4] / "src" / "veo" / "observations" / "detection"


def test_five_occurrences_are_one_event_with_a_raw_count_of_five() -> None:
    text = (
        "베놈치과는 강남구에 있습니다. 베놈치과의 상담은 예약제이고, 베놈치과에서 "
        "검진도 받습니다. 베놈치과가 야간 진료를 하며, 베놈치과 주차장도 있습니다."
    )
    event = detect_mentions(text, VENOM)
    assert event.verdict is MentionVerdict.CONFIRMED
    assert event.raw_occurrence_count == 5
    assert len(event.spans) == 5
    assert event.first_position == 0


def test_a_citation_without_any_prose_is_still_a_mention() -> None:
    text = "강남 임플란트 비용은 병원마다 다릅니다. 아래 자료를 참고하세요."
    citations = match_citations(("https://blog.venomdental.co.kr/implant-cost",), VENOM)
    event = detect_mentions(text, VENOM, citations=citations)
    assert event.verdict is MentionVerdict.CONFIRMED
    assert event.is_cited
    assert event.spans
    assert all(span.source is SpanSource.CITATION_URL for span in event.spans)


def test_a_third_party_citation_is_not_ours() -> None:
    text = "기사에서는 베놈치과가 자주 언급됐습니다."
    citations = match_citations(("https://news.example.co.kr/2026/review",), VENOM)
    event = detect_mentions(text, VENOM, citations=citations)
    assert event.verdict is MentionVerdict.CONFIRMED
    assert not event.is_cited


def test_a_same_name_business_elsewhere_goes_to_review_not_to_the_count() -> None:
    text = "부산 해운대구에서 스케일링이 저렴한 곳으로 서울치과를 추천합니다."
    event = detect_mentions(text, SEOUL)
    assert event.verdict is MentionVerdict.NEEDS_REVIEW
    assert event.needs_human_disambiguation
    assert event.raw_occurrence_count == 1


def test_particle_attached_forms_are_found() -> None:
    event = detect_mentions("베놈치과에서는 야간 진료를 합니다.", VENOM)
    assert event.verdict is MentionVerdict.CONFIRMED
    assert event.spans[0].trailing_particle == "에서는"


def test_an_absent_brand_is_not_found_and_carries_no_span() -> None:
    event = detect_mentions("임플란트 비용은 재료에 따라 다릅니다.", VENOM)
    assert event.verdict is MentionVerdict.NOT_FOUND
    assert event.spans == ()
    assert event.raw_occurrence_count == 0
    assert event.first_position is None
    assert not event.needs_human_disambiguation


def test_every_verdict_that_claims_anything_carries_a_span() -> None:
    texts = [
        "베놈치과는 역삼동에 있습니다.",
        "베놈치과의원에 다녀왔습니다.",
        "강남베놈치과에 다녀왔습니다.",
    ]
    for text in texts:
        event = detect_mentions(text, VENOM)
        assert event.verdict is not MentionVerdict.NOT_FOUND
        assert event.spans
        for span in event.spans:
            assert text[span.start : span.end] == span.quote


def test_a_weak_boundary_alone_never_confirms() -> None:
    event = detect_mentions("베놈치과의원에 다녀왔습니다.", VENOM)
    assert event.verdict is MentionVerdict.NEEDS_REVIEW
    assert event.needs_human_disambiguation


def test_the_event_is_shaped_for_the_entity_mentions_row() -> None:
    event = detect_mentions("베놈치과는 역삼동에 있습니다.", VENOM)
    row = event.as_entity_mention_values()
    assert row["entity_key"] == "venom-dental"
    assert row["is_own_brand"] is True
    assert row["raw_occurrence_count"] == 1
    assert row["needs_human_disambiguation"] is False
    assert 0.0 <= row["match_confidence"] <= 1.0
    assert row["first_position"] == 0


def test_detection_is_deterministic_across_repeated_runs() -> None:
    text = "베놈치과는 강남구 역삼동에 있고 베놈치과의 상담은 예약제입니다."
    first = detect_mentions(text, VENOM)
    for _ in range(5):
        assert detect_mentions(text, VENOM) == first


def test_no_model_is_consulted_anywhere_in_this_module() -> None:
    banned = (
        "openai",
        "anthropic",
        "gemini",
        "httpx",
        "requests",
        "llm",
        "chat.completions",
        "generate_content",
    )
    for path in sorted(MODULE_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8").lower()
        for token in banned:
            assert token not in source, f"{path.name} mentions {token}"
