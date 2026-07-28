"""Is the matched name *this* customer? When the rules cannot tell, a human is asked.

Korean clinic names collide constantly. A confident wrong attribution is worse than an
admitted unknown, because the customer never sees the inflation — the number simply looks
better than it is.
"""

from __future__ import annotations

from veo.observations.detection import BrandProfile
from veo.observations.detection.disambiguation import (
    CONFIRMATION_THRESHOLD,
    ConfidenceBand,
    assess,
    looks_generic,
)
from veo.observations.detection.normalize import find_surface_matches

DISTINCTIVE = BrandProfile(
    entity_key="venom-dental",
    display_name="베놈치과",
    own_domains=("venomdental.co.kr",),
    address_terms=("강남구", "역삼동"),
    phone_numbers=("02-555-1234",),
    distinguishing_terms=("임플란트 센터",),
)

GENERIC = BrandProfile(
    entity_key="seoul-dental-gangnam",
    display_name="서울치과",
    own_domains=("seouldental-gangnam.co.kr",),
    address_terms=("강남구", "역삼동"),
)


def spans_for(text: str, profile: BrandProfile) -> tuple[tuple[int, int], ...]:
    return tuple(
        (item.start, item.end)
        for item in find_surface_matches(text, (profile.display_name, *profile.aliases))
    )


def test_a_place_name_stem_is_generic_and_a_coined_one_is_not() -> None:
    assert looks_generic("서울치과")
    assert looks_generic("강남구치과")
    assert not looks_generic("베놈치과")
    assert not looks_generic("연세더바른치과")


def test_a_distinctive_name_clears_the_bar_on_its_own() -> None:
    text = "임플란트는 베놈치과가 자주 언급됩니다."
    result = assess(text, DISTINCTIVE, spans=spans_for(text, DISTINCTIVE))
    assert result.confidence >= CONFIRMATION_THRESHOLD
    assert result.band is ConfidenceBand.HIGH
    assert not result.needs_human_review


def test_a_generic_name_without_corroboration_does_not_clear_the_bar() -> None:
    text = "부산 해운대구에서는 서울치과를 많이 갑니다."
    result = assess(text, GENERIC, spans=spans_for(text, GENERIC))
    assert result.confidence < CONFIRMATION_THRESHOLD
    assert result.needs_human_review


def test_a_nearby_address_term_corroborates_a_generic_name() -> None:
    text = "강남구 역삼동의 서울치과는 야간 진료를 합니다."
    result = assess(text, GENERIC, spans=spans_for(text, GENERIC))
    assert any(signal.code == "LOCALITY_MATCH" for signal in result.signals)


def test_a_nearby_phone_number_corroborates() -> None:
    text = "서울치과 대표번호는 02-555-1234 입니다."
    profile = BrandProfile(
        entity_key="x", display_name="서울치과", phone_numbers=("02-555-1234",)
    )
    result = assess(text, profile, spans=spans_for(text, profile))
    assert any(signal.code == "PHONE_MATCH" for signal in result.signals)


def test_our_own_domain_being_cited_settles_it() -> None:
    text = "아래 자료를 참고하세요."
    result = assess(text, GENERIC, spans=(), own_citation_count=1)
    assert result.band is ConfidenceBand.HIGH
    assert not result.needs_human_review
    assert any(signal.code == "OWN_DOMAIN_CITATION" for signal in result.signals)


def test_a_name_that_only_appears_in_a_rivals_sentence_is_discounted() -> None:
    text = "연세더바른치과는 인근 서울치과와 달리 야간 진료를 하지 않습니다."
    spans = spans_for(text, GENERIC)
    with_rival = assess(text, GENERIC, spans=spans, rival_spans=((0, 7),))
    without_rival = assess(text, GENERIC, spans=spans)
    assert with_rival.confidence < without_rival.confidence
    assert any(signal.code == "RIVAL_ONLY_CONTEXT" for signal in with_rival.signals)


def test_a_rival_in_one_sentence_does_not_discount_a_clean_sentence_elsewhere() -> None:
    text = "베놈치과는 역삼동에 있습니다. 연세더바른치과는 베놈치과와 다릅니다."
    spans = spans_for(text, DISTINCTIVE)
    rival = spans_for(text, BrandProfile(entity_key="r", display_name="연세더바른치과"))
    result = assess(text, DISTINCTIVE, spans=spans, rival_spans=rival)
    assert all(signal.code != "RIVAL_ONLY_CONTEXT" for signal in result.signals)


def test_every_signal_carries_a_korean_reason() -> None:
    text = "부산 해운대구에서는 서울치과를 많이 갑니다."
    result = assess(text, GENERIC, spans=spans_for(text, GENERIC))
    assert result.signals
    for signal in result.signals:
        assert signal.evidence_ko.strip()


def test_confidence_never_leaves_the_unit_interval() -> None:
    text = "강남구 역삼동 서울치과 대표번호 02-777-8888, 임플란트 센터 운영."
    profile = BrandProfile(
        entity_key="x",
        display_name="서울치과",
        address_terms=("강남구", "역삼동"),
        phone_numbers=("02-777-8888",),
        distinguishing_terms=("임플란트 센터",),
    )
    result = assess(text, profile, spans=spans_for(text, profile), own_citation_count=2)
    assert 0.0 <= result.confidence <= 1.0


def test_assessment_is_deterministic() -> None:
    text = "부산 해운대구에서는 서울치과를 많이 갑니다."
    spans = spans_for(text, GENERIC)
    first = assess(text, GENERIC, spans=spans)
    for _ in range(5):
        assert assess(text, GENERIC, spans=spans) == first
