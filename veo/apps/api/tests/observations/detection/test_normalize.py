"""Korean surface matching, which is where a naive detector silently loses every hit.

``\\b베놈치과\\b`` matches nothing useful in Korean: ``는``, ``의``, ``에서`` are word
characters, so the boundary never fires and the whole check comes back empty without
raising anything. Everything in this file exists because that failure is invisible.
"""

from __future__ import annotations

import pytest

from veo.observations.detection.normalize import (
    BoundaryStrength,
    find_surface_matches,
    fold,
    is_particle_run,
    normalize_brand,
    split_business_suffix,
    surface_variants,
)

BRAND = "베놈치과"

#: Written as escapes so the source stays unambiguous; the point is that a reader who
#: pastes fullwidth Latin still matches the declared Latin alias.
FULLWIDTH_VENOM = "\uff36\uff25\uff2e\uff2f\uff2d"


#: Fold inputs including two characters whose NFKC expansion is longer than one
#: character. Those must be left alone rather than expanded, or every offset moves.
FOLD_SAMPLES = (
    "베놈치과",
    f"{FULLWIDTH_VENOM} 치과",
    "VENOM Dental",
    "①번 병원",
    "ﬁle 치과",
)


def test_folding_never_moves_an_offset() -> None:
    # Offsets are quoted back to a human reviewer. A fold that changes the length would
    # point the reviewer at the wrong characters, which is worse than not quoting at all.
    for text in FOLD_SAMPLES:
        assert len(fold(text)) == len(text)


def test_folding_makes_latin_and_fullwidth_comparable() -> None:
    assert fold(FULLWIDTH_VENOM) == "venom"
    assert fold("Venom") == "venom"


def test_spacing_variants_collapse_to_one_key() -> None:
    assert normalize_brand("베놈 치과") == normalize_brand("베놈치과")
    assert normalize_brand("VENOM 치과") == normalize_brand("venom치과")


def test_business_suffix_is_split_off_the_stem() -> None:
    assert split_business_suffix("베놈치과") == ("베놈", "치과")
    assert split_business_suffix("연세더바른치과") == ("연세더바른", "치과")
    assert split_business_suffix("베놈성형외과") == ("베놈", "성형외과")
    assert split_business_suffix("베놈") == ("베놈", "")


def test_variants_cover_the_spacing_a_writer_actually_uses() -> None:
    variants = surface_variants("베놈치과")
    assert "베놈치과" in variants
    assert "베놈 치과" in variants


@pytest.mark.parametrize(
    "particle",
    ["는", "은", "이", "가", "을", "를", "의", "도", "와", "과", "에", "에서", "에서는", "부터"],
)
def test_particle_attached_forms_still_match(particle: str) -> None:
    text = f"저희가 확인한 곳은 {BRAND}{particle} 있습니다."
    matches = find_surface_matches(text, (BRAND,))
    assert len(matches) == 1
    assert matches[0].strength is BoundaryStrength.STRONG
    assert matches[0].trailing_particle == particle
    assert text[matches[0].start : matches[0].end] == BRAND


def test_the_copula_is_a_boundary_too() -> None:
    matches = find_surface_matches(f"가장 가까운 곳은 {BRAND}입니다.", (BRAND,))
    assert len(matches) == 1
    assert matches[0].strength is BoundaryStrength.STRONG


def test_a_spacing_variant_in_the_answer_matches_the_declared_name() -> None:
    matches = find_surface_matches("베놈 치과는 역삼동에 있습니다.", (BRAND,))
    assert len(matches) == 1
    assert matches[0].quote == "베놈 치과"


def test_an_unknown_hangul_tail_is_weak_not_confirmed() -> None:
    # 베놈치과의원 is a different business name. We neither drop it silently nor count it.
    matches = find_surface_matches("베놈치과의원에 다녀왔습니다.", (BRAND,))
    assert len(matches) == 1
    assert matches[0].strength is BoundaryStrength.WEAK


def test_a_hangul_prefix_is_weak_not_confirmed() -> None:
    matches = find_surface_matches("강남베놈치과에 다녀왔습니다.", (BRAND,))
    assert len(matches) == 1
    assert matches[0].strength is BoundaryStrength.WEAK


def test_a_latin_word_that_merely_contains_the_name_is_not_a_match() -> None:
    assert find_surface_matches("venomclinic is unrelated", ("venom",)) == ()


def test_latin_matching_ignores_case() -> None:
    matches = find_surface_matches("VENOM치과는 강남에 있습니다.", ("venom치과",))
    assert len(matches) == 1
    assert matches[0].quote == "VENOM치과"


def test_five_occurrences_produce_five_surface_matches() -> None:
    text = (
        f"{BRAND}는 강남구에 있습니다. {BRAND}의 상담은 예약제이고, {BRAND}에서 "
        f"검진도 받습니다. {BRAND}가 야간 진료를 하며, {BRAND} 주차장도 있습니다."
    )
    assert len(find_surface_matches(text, (BRAND,))) == 5


def test_overlapping_aliases_do_not_double_count() -> None:
    matches = find_surface_matches("베놈치과는 강남에 있습니다.", ("베놈치과", "베놈"))
    assert len(matches) == 1
    assert matches[0].quote == "베놈치과"


def test_particle_run_recognition_is_conservative() -> None:
    assert is_particle_run("에서는")
    assert is_particle_run("의")
    assert not is_particle_run("의원")
    assert not is_particle_run("이야기")


def test_matching_is_deterministic() -> None:
    text = f"{BRAND}는 강남구 역삼동에 있고 {BRAND}의 상담은 예약제입니다."
    first = find_surface_matches(text, (BRAND,))
    for _ in range(5):
        assert find_surface_matches(text, (BRAND,)) == first
