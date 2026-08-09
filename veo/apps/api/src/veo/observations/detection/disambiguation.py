"""Is the matched name *this* customer, or a business that merely shares the name?

Korean clinic names collide constantly. ``서울치과`` is dozens of businesses in dozens of
districts; so is ``중앙병원``, ``연세의원``, ``우리치과``. A detector that resolves the collision
by picking the customer is not wrong occasionally — it is wrong in a direction, always
upwards, and the customer never sees it. Their exposure rate simply looks better than it is.

So this module produces a **confidence band**, not a decision. Anything that does not clear
:data:`CONFIRMATION_THRESHOLD` is routed to a human. That is the trade the product makes
deliberately: an admitted unknown costs one review, a confident wrong attribution costs the
credibility of every number on the screen.

Signals are additive, bounded, and each one carries the Korean sentence a reviewer will read:

* the name's own distinctiveness — a coined stem is evidence, a place name is not
* a declared address term, phone number or distinguishing phrase near the hit
* a locality that is not ours near the hit — the strongest same-name tell there is
* our own domain cited in the same answer — decisive, because a domain cannot be shared
* a shared name appearing *only* inside a sentence that names a rival

Nothing here consults a model. The verdict has to be reproducible from the answer text
alone, or a reviewer cannot audit it.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from veo.observations.detection.normalize import (
    find_surface_matches,
    fold,
    normalize_brand,
    split_business_suffix,
)

__all__ = [
    "CONFIRMATION_THRESHOLD",
    "CONTEXT_WINDOW",
    "GENERIC_BRAND_STEMS",
    "KOREAN_LOCALITY_TERMS",
    "Attribution",
    "BrandProfile",
    "ConfidenceBand",
    "Signal",
    "assess",
    "looks_generic",
]

#: A verdict at or above this confidence may be recorded. Below it, a human decides.
CONFIRMATION_THRESHOLD = 0.75

#: Characters either side of a hit that count as "near" for corroboration.
CONTEXT_WINDOW = 120

_BASE_DISTINCTIVE = 0.85
_BASE_GENERIC = 0.40
_W_OWN_CITATION = 0.95
_W_LOCALITY_MATCH = 0.20
_W_PHONE_MATCH = 0.25
_W_DISTINGUISHING_TERM = 0.15
_W_FOREIGN_LOCALITY = -0.15
_W_RIVAL_ONLY = -0.20
_W_WEAK_BOUNDARY_ONLY = -0.25

#: Administrative areas used to spot "this is a different branch of the same name".
#:
#: Deliberately incomplete and deliberately unambiguous — ``남구``/``서구``/``동구`` are left
#: out because they collide with ordinary words, and a false locality signal on a generic
#: name is the one thing that would push a real mention into the review queue for nothing.
KOREAN_LOCALITY_TERMS: tuple[str, ...] = (
    "서울", "서울특별시", "부산", "부산광역시", "대구", "대구광역시", "인천", "인천광역시",
    "광주", "광주광역시", "대전", "대전광역시", "울산", "울산광역시", "세종", "세종특별자치시",
    "경기도", "강원도", "강원특별자치도", "충청북도", "충청남도", "전라북도", "전북특별자치도",
    "전라남도", "경상북도", "경상남도", "제주도", "제주특별자치도",
    "강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구", "노원구",
    "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", "성동구", "성북구",
    "송파구", "양천구", "영등포구", "용산구", "은평구", "종로구", "중랑구",
    "해운대구", "부산진구", "동래구", "사하구", "금정구", "수영구", "연제구", "영도구",
    "사상구", "기장군",
    "수원", "성남", "용인", "고양", "화성", "부천", "안산", "안양", "평택", "남양주",
    "창원", "청주", "천안", "전주", "김해", "포항", "제주",
)

#: Stems that name a category, a virtue or a place rather than a business.
GENERIC_BRAND_STEMS: frozenset[str] = frozenset(
    {
        "우리", "미소", "연세", "중앙", "하나", "사랑", "행복", "웃음", "밝은", "튼튼",
        "든든", "편안", "바른", "참", "예쁨", "예쁜", "굿", "베스트", "퍼스트", "스마일",
        "리더스", "명품", "프라임", "센트럴", "메디", "메디컬", "닥터", "제일", "으뜸",
        "화이트", "화이트닝", "본", "새로",
    }
)

_LOCALITY_LOOKUP: frozenset[str] = frozenset(KOREAN_LOCALITY_TERMS)
_DIGITS_RE = re.compile(r"\d")
_PHONE_RE = re.compile(r"\d[\d\-\s.]{6,}\d")
_SENTENCE_BREAK_RE = re.compile(r"[.!?。\n]")


@dataclass(frozen=True, slots=True)
class BrandProfile:
    """Everything the customer declared about one brand — theirs or a competitor's.

    The same shape is used for both sides on purpose. Share of Voice is only honest if the
    customer and the competitor are described, and therefore detected, identically.
    """

    entity_key: str
    display_name: str
    aliases: tuple[str, ...] = ()
    own_domains: tuple[str, ...] = ()
    address_terms: tuple[str, ...] = ()
    phone_numbers: tuple[str, ...] = ()
    distinguishing_terms: tuple[str, ...] = ()
    is_own_brand: bool = True
    competitor_id: str | None = None
    name_is_ambiguous: bool | None = None
    """Override for :func:`looks_generic`. ``None`` means "work it out from the name"."""

    def __post_init__(self) -> None:
        if not self.display_name.strip():
            raise ValueError("브랜드 이름이 비어 있습니다. 빈 이름으로는 탐지할 수 없습니다.")
        if not self.entity_key.strip():
            raise ValueError(f"{self.display_name}: entity_key 가 비어 있습니다.")
        if not self.is_own_brand and self.competitor_id is None:
            raise ValueError(
                f"{self.display_name}: 경쟁사에는 competitor_id 가 있어야 합니다. "
                "식별자 없는 경쟁사는 점유율에서 다시 찾아낼 수 없습니다."
            )

    @property
    def names(self) -> tuple[str, ...]:
        """Every declared spelling, deduplicated but order-stable."""
        found: list[str] = []
        for name in (self.display_name, *self.aliases):
            cleaned = name.strip()
            if cleaned and cleaned not in found:
                found.append(cleaned)
        return tuple(found)

    @property
    def normalized_key(self) -> str:
        return normalize_brand(self.display_name)

    @property
    def is_ambiguous_name(self) -> bool:
        if self.name_is_ambiguous is not None:
            return self.name_is_ambiguous
        return looks_generic(self.display_name)


class ConfidenceBand(StrEnum):
    """How much weight the attribution can bear."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True, slots=True)
class Signal:
    """One reason the confidence moved, in words a reviewer can check."""

    code: str
    delta: float
    evidence_ko: str


@dataclass(frozen=True, slots=True)
class Attribution:
    """The outcome: a number, a band, and the reasons for both."""

    confidence: float
    band: ConfidenceBand
    signals: tuple[Signal, ...] = ()

    @property
    def needs_human_review(self) -> bool:
        return self.confidence < CONFIRMATION_THRESHOLD

    @property
    def summary_ko(self) -> str:
        return " / ".join(signal.evidence_ko for signal in self.signals)


def looks_generic(name: str) -> bool:
    """Whether the name is the kind that dozens of businesses legitimately share."""
    stem, _ = split_business_suffix(name.strip())
    folded = "".join(fold(stem).split())
    if len(folded) <= 1:
        return True
    if stem in _LOCALITY_LOOKUP or folded in _LOCALITY_LOOKUP:
        return True
    return stem in GENERIC_BRAND_STEMS or folded in GENERIC_BRAND_STEMS


def assess(
    answer_text: str,
    profile: BrandProfile,
    *,
    spans: Sequence[tuple[int, int]] = (),
    rival_spans: Sequence[tuple[int, int]] = (),
    own_citation_count: int = 0,
    weak_only: bool = False,
) -> Attribution:
    """Decide how confident we are that these hits are ``profile``'s business.

    ``spans`` are the offsets of the hits in ``answer_text``. ``rival_spans`` are the hits
    belonging to every *other* declared brand in the same answer — passed in symmetrically
    for the customer and for each competitor, so neither side gets an easier test.
    """
    signals: list[Signal] = []

    if own_citation_count > 0:
        # A domain cannot be shared. If our own URL is a source for this answer, the
        # question of which 서울치과 this is has already been answered — and it has to be
        # decisive, because runs.py refuses a citation that carries no mention.
        signals.append(
            Signal(
                "OWN_DOMAIN_CITATION",
                _W_OWN_CITATION,
                f"자사 도메인이 근거 URL {own_citation_count}건으로 인용됐습니다. "
                "도메인은 동명 업체와 공유되지 않습니다.",
            )
        )

    if weak_only:
        # Above the ``not spans`` guard on purpose. ``weak_only`` means *every* hit had a
        # weak boundary, and a caller that only forwards its strong spans (see
        # :func:`veo.observations.detection.mentions.detect_mentions`) therefore arrives
        # here with ``spans`` empty. Below the guard this signal was unreachable from that
        # caller, and the reviewer got a held finding with no reason attached — which reads
        # as a malfunction rather than as a question (0-A).
        signals.append(
            Signal(
                "WEAK_BOUNDARY_ONLY",
                _W_WEAK_BOUNDARY_ONLY,
                f"'{profile.display_name}' 앞뒤에 다른 한글이 붙어 있어 더 긴 다른 상호일 수 "
                "있습니다. 이름만으로는 이 고객이라고 말할 수 없습니다.",
            )
        )

    if not spans:
        return _finish(0.0, signals)

    if profile.is_ambiguous_name:
        base = _BASE_GENERIC
        signals.append(
            Signal(
                "AMBIGUOUS_NAME",
                base,
                f"'{profile.display_name}' 은(는) 여러 업체가 함께 쓰는 이름입니다. "
                "이름만으로는 이 고객이라고 말할 수 없습니다.",
            )
        )
    else:
        base = _BASE_DISTINCTIVE
        signals.append(
            Signal(
                "DISTINCTIVE_NAME",
                base,
                f"'{profile.display_name}' 은(는) 고유한 상호입니다. 동명 업체 위험이 낮습니다.",
            )
        )

    windows = tuple(_window(answer_text, start, end) for start, end in spans)
    joined = " ".join(text for text, _, _ in windows)

    matched_locality = _first_present(joined, profile.address_terms)
    if matched_locality:
        signals.append(
            Signal(
                "LOCALITY_MATCH",
                _W_LOCALITY_MATCH,
                f"선언된 소재지 '{matched_locality}' 이(가) 언급 주변에 함께 나옵니다.",
            )
        )
    else:
        foreign = _foreign_locality(windows, profile)
        if foreign and profile.address_terms:
            signals.append(
                Signal(
                    "FOREIGN_LOCALITY",
                    _W_FOREIGN_LOCALITY,
                    f"언급 주변의 지역은 '{foreign}' 이고 선언된 소재지"
                    f"({', '.join(profile.address_terms)})와 다릅니다.",
                )
            )

    matched_phone = _matching_phone(joined, profile.phone_numbers)
    if matched_phone:
        signals.append(
            Signal(
                "PHONE_MATCH",
                _W_PHONE_MATCH,
                f"선언된 대표번호 '{matched_phone}' 이(가) 언급 주변에 나옵니다.",
            )
        )

    matched_term = _first_present(joined, profile.distinguishing_terms)
    if matched_term:
        signals.append(
            Signal(
                "DISTINGUISHING_TERM",
                _W_DISTINGUISHING_TERM,
                f"고객만의 표현 '{matched_term}' 이(가) 언급 주변에 나옵니다.",
            )
        )

    # Rival proximity is an *identity* signal, not a quality one: it only helps decide
    # whether a shared name belongs to this customer or to the business the rival is being
    # compared against. A coined name in a rival's sentence is still unmistakably ours, and
    # "A는 …, B는 …" is the commonest shape an answer takes — discounting it would bury the
    # review queue and under-count real exposure.
    if (
        profile.is_ambiguous_name
        and rival_spans
        and _every_span_shares_a_sentence(answer_text, spans, rival_spans)
    ):
        signals.append(
            Signal(
                "RIVAL_ONLY_CONTEXT",
                _W_RIVAL_ONLY,
                "이 이름은 경쟁사를 설명하는 문장 안에서만 나옵니다. 여러 업체가 함께 쓰는 "
                "이름이라 비교 대상으로 스친 것인지 이 고객인지 문장만으로는 갈리지 않습니다.",
            )
        )

    return _finish(0.0, signals)


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _finish(start: float, signals: Sequence[Signal]) -> Attribution:
    total = start + sum(signal.delta for signal in signals)
    confidence = min(1.0, max(0.0, total))
    if confidence >= CONFIRMATION_THRESHOLD:
        band = ConfidenceBand.HIGH
    elif confidence >= 0.5:
        band = ConfidenceBand.MEDIUM
    else:
        band = ConfidenceBand.LOW
    return Attribution(confidence=confidence, band=band, signals=tuple(signals))


def _window(text: str, start: int, end: int) -> tuple[str, int, int]:
    low = max(0, start - CONTEXT_WINDOW)
    high = min(len(text), end + CONTEXT_WINDOW)
    return text[low:high], start - low, end - low


def _first_present(haystack: str, needles: Sequence[str]) -> str:
    folded = fold(haystack)
    for needle in needles:
        cleaned = needle.strip()
        if cleaned and fold(cleaned) in folded:
            return cleaned
    return ""


def _foreign_locality(
    windows: Sequence[tuple[str, int, int]], profile: BrandProfile
) -> str:
    """A locality near the hit that is not one of the declared ones.

    The brand's own span is excluded, because a name like 서울치과 contains a place name
    and would otherwise argue against itself.
    """
    declared = {fold(term.strip()) for term in profile.address_terms if term.strip()}
    for text, span_start, span_end in windows:
        for match in find_surface_matches(text, KOREAN_LOCALITY_TERMS):
            if match.start < span_end and match.end > span_start:
                continue
            if fold(match.quote) in declared:
                continue
            return match.quote
    return ""


def _matching_phone(haystack: str, declared: Sequence[str]) -> str:
    wanted = {_digits(number) for number in declared if _digits(number)}
    if not wanted:
        return ""
    for match in _PHONE_RE.finditer(haystack):
        if _digits(match.group(0)) in wanted:
            return match.group(0).strip()
    return ""


def _digits(value: str) -> str:
    return "".join(_DIGITS_RE.findall(value))


def _sentence_bounds(text: str) -> tuple[tuple[int, int], ...]:
    bounds: list[tuple[int, int]] = []
    start = 0
    for match in _SENTENCE_BREAK_RE.finditer(text):
        bounds.append((start, match.end()))
        start = match.end()
    if start < len(text):
        bounds.append((start, len(text)))
    return tuple(bounds)


def _every_span_shares_a_sentence(
    text: str,
    spans: Sequence[tuple[int, int]],
    rival_spans: Sequence[tuple[int, int]],
) -> bool:
    bounds = _sentence_bounds(text)
    for start, end in spans:
        sentence = _sentence_for(bounds, start, end)
        if sentence is None:
            return False
        low, high = sentence
        if not any(r_start < high and r_end > low for r_start, r_end in rival_spans):
            return False
    return True


def _sentence_for(
    bounds: Sequence[tuple[int, int]], start: int, end: int
) -> tuple[int, int] | None:
    for low, high in bounds:
        if start >= low and end <= high:
            return low, high
    return None
