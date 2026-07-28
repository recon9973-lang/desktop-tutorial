"""Declared identifiers are what make a common Korean business name measurable.

Measured on a real generic name, with the shipped detector:

    name only                            0.40  -> 검수 대기
    + district                           0.60  -> 검수 대기
    + district + phone                   0.85  -> 확정
    + district + phone + distinguisher   1.00  -> 확정

So a district alone does not settle it and a phone number usually does. That is the whole
reason this record exists: without it, every mention of a customer called 서울치과 goes to
a human, and the product cannot measure them at all.

The same record describes competitors, because Share of Voice is only honest when both
sides are described — and therefore detected — identically. Giving our own brand richer
identifiers than a rival's would inflate our share without touching the arithmetic.
"""

from __future__ import annotations

import pytest

from veo.observations.brand_identity import (
    BrandIdentityRecord,
    IdentityStrength,
    describe_identity_gaps_ko,
    normalise_phone,
    to_brand_profile,
)
from veo.observations.detection.mentions import detect_mentions

ANSWER = (
    "서초구에서 임플란트로 알려진 곳으로는 서울치과가 있습니다. "
    "서울치과는 강남역 근처이고 문의는 02-1234-5678 입니다. 야간 진료도 운영합니다."
)


def record(**overrides: object) -> BrandIdentityRecord:
    base: dict = {
        "entity_key": "seoul-dental",
        "display_name": "서울치과",
        "is_own_brand": True,
    }
    base.update(overrides)
    return BrandIdentityRecord(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Phone normalisation — the signal that actually decides
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "written",
    ["02-1234-5678", "0212345678", "02 1234 5678", "(02)1234-5678", "+82-2-1234-5678"],
)
def test_the_same_number_written_differently_normalises_alike(written: str) -> None:
    assert normalise_phone(written) == normalise_phone("02-1234-5678")


def test_a_mobile_number_normalises_consistently() -> None:
    assert normalise_phone("010-1111-2222") == normalise_phone("+82 10 1111 2222")


def test_a_string_with_no_digits_is_not_a_phone_number() -> None:
    assert normalise_phone("전화 문의") is None


def test_a_number_too_short_to_be_a_phone_is_refused() -> None:
    assert normalise_phone("1234") is None


# --------------------------------------------------------------------------- #
# The measured effect
# --------------------------------------------------------------------------- #


def test_a_generic_name_alone_cannot_be_confirmed() -> None:
    event = detect_mentions(ANSWER, to_brand_profile(record()))
    assert event.needs_human_disambiguation


def test_a_district_alone_is_still_not_enough() -> None:
    """Worth knowing at onboarding: collecting only an address does not fix this."""
    event = detect_mentions(ANSWER, to_brand_profile(record(address_terms=("서초구",))))
    assert event.needs_human_disambiguation


def test_a_district_and_a_phone_number_confirm_it() -> None:
    event = detect_mentions(
        ANSWER,
        to_brand_profile(record(address_terms=("서초구",), phone_numbers=("02-1234-5678",))),
    )
    assert not event.needs_human_disambiguation
    assert event.is_mentioned


def test_a_differently_formatted_phone_still_confirms() -> None:
    """The customer types it one way; the AI answer prints it another."""
    event = detect_mentions(
        ANSWER,
        to_brand_profile(record(address_terms=("서초구",), phone_numbers=("0212345678",))),
    )
    assert not event.needs_human_disambiguation


def test_a_distinctive_name_needs_no_extra_identifiers() -> None:
    distinctive = ANSWER.replace("서울치과", "베놈치과")
    event = detect_mentions(
        distinctive, to_brand_profile(record(entity_key="venom", display_name="베놈치과"))
    )
    assert not event.needs_human_disambiguation


# --------------------------------------------------------------------------- #
# Telling an operator what is missing, before the measurement fails
# --------------------------------------------------------------------------- #


def test_strength_is_weak_for_a_generic_name_with_nothing_declared() -> None:
    assert record().strength is IdentityStrength.INSUFFICIENT


def test_strength_improves_as_identifiers_are_declared() -> None:
    with_address = record(address_terms=("서초구",))
    with_phone = record(address_terms=("서초구",), phone_numbers=("02-1234-5678",))

    assert with_address.strength is IdentityStrength.PARTIAL
    assert with_phone.strength is IdentityStrength.SUFFICIENT


def test_a_distinctive_name_is_sufficient_on_its_own() -> None:
    assert record(display_name="베놈치과", entity_key="venom").strength is (
        IdentityStrength.SUFFICIENT
    )


def test_the_gap_report_names_the_phone_number_first() -> None:
    """Advice has to be ranked by what actually moves the measurement."""
    gaps = describe_identity_gaps_ko(record(address_terms=("서초구",)))
    assert gaps
    assert "전화" in gaps[0]


def test_a_sufficient_identity_reports_no_gaps() -> None:
    assert describe_identity_gaps_ko(record(display_name="베놈치과", entity_key="venom")) == []


# --------------------------------------------------------------------------- #
# Symmetry between our brand and a competitor's
# --------------------------------------------------------------------------- #


def test_a_competitor_uses_the_same_record_shape() -> None:
    ours = record()
    theirs = record(
        entity_key="rival", display_name="미소치과", is_own_brand=False, competitor_id="c-1"
    )
    assert type(ours) is type(theirs)
    assert to_brand_profile(theirs).is_own_brand is False


def test_a_competitor_without_an_identifier_is_refused() -> None:
    with pytest.raises(ValueError):
        record(entity_key="rival", display_name="미소치과", is_own_brand=False)


def test_richer_identity_on_our_side_than_a_rivals_is_reported() -> None:
    """Asymmetric identifiers rig Share of Voice without touching the arithmetic."""
    from veo.observations.brand_identity import describe_identity_asymmetry_ko

    ours = record(address_terms=("서초구",), phone_numbers=("02-1234-5678",))
    theirs = record(
        entity_key="rival", display_name="미소치과", is_own_brand=False, competitor_id="c-1"
    )

    warnings = describe_identity_asymmetry_ko(ours, [theirs])
    assert warnings
    assert any("미소치과" in line for line in warnings)


def test_evenly_described_sides_produce_no_warning() -> None:
    from veo.observations.brand_identity import describe_identity_asymmetry_ko

    ours = record(display_name="베놈치과", entity_key="venom")
    theirs = record(
        entity_key="rival", display_name="미소드림치과", is_own_brand=False, competitor_id="c-1"
    )
    assert describe_identity_asymmetry_ko(ours, [theirs]) == []
