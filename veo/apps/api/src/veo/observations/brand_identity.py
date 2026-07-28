"""What a customer declares so that a common business name can be measured at all.

A brand name is often not an identifier. 서울치과 is dozens of practices; 중앙병원 is more.
The detector is deliberately conservative about them — it routes an unconfirmable mention
to a human rather than guessing — which is right, and which also means a customer with a
common name is unmeasurable until somebody tells VEO how to tell them apart.

Measured against the shipped detector, on a real generic name:

===================================  ==========  =============
declared                             confidence  outcome
===================================  ==========  =============
name only                            0.40        review
+ district                           0.60        review
+ district + phone                   0.85        confirmed
+ district + phone + distinguisher   1.00        confirmed
===================================  ==========  =============

Two things follow, and both matter at onboarding:

* **A district alone does not settle it.** Collecting an address feels like the obvious
  fix and is not sufficient on its own.
* **A phone number usually does.** It is the cheapest field to collect and the one that
  moves the measurement, so :func:`describe_identity_gaps_ko` names it first.

The same record describes a competitor. Share of Voice is only honest when both sides are
described, and therefore detected, identically — describing our own brand richly while
leaving a rival as a bare name would inflate our share without altering any arithmetic,
which is why :func:`describe_identity_asymmetry_ko` exists and why a comparison should
show its output rather than quietly proceeding.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from veo.observations.detection.disambiguation import BrandProfile, looks_generic

#: Korean landline and mobile numbers are 9 to 11 digits once punctuation and the country
#: code are gone. Shorter than that is a room number or a price, not a phone number.
_MIN_PHONE_DIGITS = 9
_MAX_PHONE_DIGITS = 11

_NON_DIGITS = re.compile(r"\D+")


class IdentityStrength(StrEnum):
    """Whether this record can support an unattended measurement."""

    #: The name is distinctive, or enough identifiers are declared. Mentions confirm.
    SUFFICIENT = "SUFFICIENT"
    #: Something is declared but not enough to cross the confirmation threshold.
    PARTIAL = "PARTIAL"
    #: A common name with nothing to distinguish it. Every mention goes to review.
    INSUFFICIENT = "INSUFFICIENT"


def normalise_phone(value: str) -> str | None:
    """Reduce a written phone number to comparable digits, or ``None`` if it is not one.

    The customer types ``02-1234-5678``; an AI answer prints ``(02)1234-5678`` or
    ``+82 2 1234 5678``. Comparing the strings would miss the match that decides whether
    the customer is measurable, so both sides are reduced to digits with the country code
    removed.
    """
    digits = _NON_DIGITS.sub("", value)
    if not digits:
        return None

    if digits.startswith("82"):
        digits = "0" + digits[2:]
    if not digits.startswith("0"):
        digits = "0" + digits

    if not _MIN_PHONE_DIGITS <= len(digits) <= _MAX_PHONE_DIGITS:
        return None
    return digits


@dataclass(frozen=True, slots=True)
class BrandIdentityRecord:
    """The declared facts about one brand — ours or a competitor's."""

    entity_key: str
    display_name: str
    is_own_brand: bool = True
    competitor_id: str | None = None
    aliases: tuple[str, ...] = ()
    own_domains: tuple[str, ...] = ()
    address_terms: tuple[str, ...] = ()
    phone_numbers: tuple[str, ...] = ()
    distinguishing_terms: tuple[str, ...] = ()
    name_is_ambiguous: bool | None = None
    notes_ko: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        if not self.display_name.strip():
            raise ValueError("브랜드 이름이 비어 있습니다.")
        if not self.is_own_brand and not self.competitor_id:
            raise ValueError(
                f"{self.display_name}: 경쟁사에는 competitor_id 가 필요합니다. "
                "식별자 없는 경쟁사는 점유율에서 다시 찾아낼 수 없습니다."
            )

    @property
    def name_is_generic(self) -> bool:
        if self.name_is_ambiguous is not None:
            return self.name_is_ambiguous
        return looks_generic(self.display_name)

    @property
    def normalised_phones(self) -> tuple[str, ...]:
        found = [normalise_phone(number) for number in self.phone_numbers]
        return tuple(number for number in found if number)

    @property
    def strength(self) -> IdentityStrength:
        if not self.name_is_generic:
            return IdentityStrength.SUFFICIENT
        # Mirrors what the detector actually rewards: a phone number carries the
        # generic-name case over the confirmation threshold, an address on its own
        # does not. Keep this in step with the measurement, not with intuition.
        if self.normalised_phones or self.distinguishing_terms:
            return IdentityStrength.SUFFICIENT
        if self.address_terms or self.own_domains or self.aliases:
            return IdentityStrength.PARTIAL
        return IdentityStrength.INSUFFICIENT


def to_brand_profile(record: BrandIdentityRecord) -> BrandProfile:
    """Hand the declared facts to the detector, with phones already normalised."""
    return BrandProfile(
        entity_key=record.entity_key,
        display_name=record.display_name,
        aliases=record.aliases,
        own_domains=record.own_domains,
        address_terms=record.address_terms,
        phone_numbers=record.normalised_phones or record.phone_numbers,
        distinguishing_terms=record.distinguishing_terms,
        is_own_brand=record.is_own_brand,
        competitor_id=record.competitor_id,
        name_is_ambiguous=record.name_is_ambiguous,
    )


def describe_identity_gaps_ko(record: BrandIdentityRecord) -> list[str]:
    """What to collect, ranked by how much it actually moves the measurement."""
    if record.strength is IdentityStrength.SUFFICIENT:
        return []

    gaps: list[str] = []
    if not record.normalised_phones:
        gaps.append(
            f"전화번호를 등록하세요. '{record.display_name}'처럼 여러 업체가 함께 쓰는 "
            "이름은 전화번호가 있어야 AI 답변 속 언급이 이 고객의 것이라고 확정됩니다. "
            "가장 효과가 큰 한 가지입니다."
        )
    if not record.address_terms:
        gaps.append(
            "소재지를 등록하세요. 행정동·역명·랜드마크처럼 AI 답변이 실제로 말할 만한 "
            "표현이 좋습니다. 다만 소재지만으로는 확정에 이르지 못합니다."
        )
    if not record.distinguishing_terms:
        gaps.append(
            "이 업체만의 특징을 한두 개 등록하세요. 대표 시술, 남들과 다른 진료시간, "
            "원장 성함처럼 동명 업체와 갈리는 표현이면 됩니다."
        )
    return gaps


def describe_identity_asymmetry_ko(
    ours: BrandIdentityRecord, competitors: Sequence[BrandIdentityRecord]
) -> list[str]:
    """Warn when our side is described better than a rival's.

    This is the quiet way a Share of Voice number becomes wrong. Both sides go through the
    same detector, so a rival described only by a common name has its mentions routed to
    review while ours confirm — and the share that comes out favours us for reasons that
    have nothing to do with visibility.
    """
    warnings: list[str] = []
    for rival in competitors:
        if rival.strength is IdentityStrength.SUFFICIENT:
            continue
        if ours.strength is not IdentityStrength.SUFFICIENT:
            continue
        warnings.append(
            f"'{rival.display_name}'는 식별 정보가 부족해({rival.strength}) 언급이 "
            f"검수 대기로 넘어가는 반면, '{ours.display_name}'는 확정됩니다. "
            "이 상태로 점유율을 계산하면 실제 노출 차이가 아니라 등록 정보 차이가 "
            "숫자로 나타납니다. 경쟁사에도 같은 수준의 정보를 등록하십시오."
        )
    return warnings


__all__ = [
    "BrandIdentityRecord",
    "IdentityStrength",
    "describe_identity_asymmetry_ko",
    "describe_identity_gaps_ko",
    "normalise_phone",
    "to_brand_profile",
]
