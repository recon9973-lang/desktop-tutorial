"""Is there a passage here that answers the page's own question?

Everything in this module is a heuristic and is reported as one. It cannot know what an
answer engine would quote; it can only measure shape — whether an early passage restates
the heading's terms, whether passages survive being lifted out of their context, whether
the document is more content than furniture, and whether numbers were left loose in prose
instead of being tabulated.

The corresponding checks therefore carry ``HEURISTIC_*`` confidence, never
``DIRECT_OBSERVATION``. Saying "we measured this" about a judgement is how a diagnostic
loses the right to be believed about the things it really did measure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import pairwise

from veo.geo.parsing import PageDocument, Region, TextBlock, normalise

#: A passage shorter than this is a caption or a label, not an answer.
MIN_ANSWER_CHARACTERS = 60
MAX_ANSWER_CHARACTERS = 900

#: Passages below this length are too short to judge for independence.
MIN_JUDGEABLE_CHARACTERS = 40

#: A block repeated across URLs only matters once it is long enough to be an answer.
MIN_REPEATED_CHARACTERS = 60

#: Openings that hand the reader back to a context an extracted passage will not have.
DEPENDENT_OPENINGS = (
    "이것", "이는", "이런", "이러한", "이렇게", "이 제품", "이 서비스", "이 페이지",
    "그것", "그런", "그러한", "그래서", "그러나", "그런데", "그리고",
    "저것", "위에서", "위의", "아래에서", "아래의", "앞서", "앞에서", "여기서", "여기에",
    "따라서", "또한", "하지만", "반면", "결국", "다음으로", "마찬가지로",
    "this ", "that ", "these ", "those ", "it ", "however", "therefore", "also,",
)

#: Units that make a number worth putting in a table. Bare years are deliberately absent:
#: "2016년 설립" is a fact about a company, not a figure inviting comparison.
# No trailing ``\b``: Korean particles are word characters, so "22만원이며" would never
# match a boundary after 원 and the whole category would silently see no figures at all.
QUANTITY_PATTERN = re.compile(
    r"\d[\d,\.]*\s*(?:%|만원|억원|원|달러|위안|개월|시간|분|일간|회|명|건|"
    r"리터|ml|mL|kg|km|cm|mm|GB|MB|배)|[₩$€]\s*\d[\d,\.]*"
)

_TOKEN_PATTERN = re.compile(r"[0-9A-Za-z가-힣]{2,}")

_TOPIC_STOPWORDS = frozenset(
    {
        "그리고", "그러나", "하지만", "위한", "대한", "있는", "없는", "하는", "합니다",
        "입니다", "the", "and", "for", "with", "you", "your", "our",
    }
)


@dataclass(frozen=True, slots=True)
class DirectAnswer:
    text: str
    shared_terms: tuple[str, ...]
    position: int


@dataclass(frozen=True, slots=True)
class HeadingReport:
    levels: tuple[int, ...]
    h1_count: int
    section_count: int
    skipped_levels: tuple[tuple[int, int], ...]

    @property
    def is_well_formed(self) -> bool:
        return self.h1_count == 1 and not self.skipped_levels and self.section_count >= 2


@dataclass(frozen=True, slots=True)
class ExtractionSignals:
    direct_answer: DirectAnswer | None
    topic_terms: tuple[str, ...]
    self_contained_ratio: float
    dependent_openings: tuple[str, ...]
    judged_passage_count: int
    headings: HeadingReport
    main_content_ratio: float
    content_characters: int
    furniture_characters: int
    quantities: tuple[str, ...]
    tabulated_quantities: tuple[str, ...]
    has_structured_container: bool

    @property
    def has_quantities_worth_structuring(self) -> bool:
        return len(self.quantities) >= 2


def analyse_extractability(page: PageDocument) -> ExtractionSignals:
    passages = page.passages()
    topic_terms = _topic_terms(page)

    return ExtractionSignals(
        direct_answer=_find_direct_answer(passages, topic_terms),
        topic_terms=topic_terms,
        self_contained_ratio=_self_contained_ratio(passages),
        dependent_openings=_dependent_openings(passages),
        judged_passage_count=len(_judgeable(passages)),
        headings=_heading_report(page),
        main_content_ratio=_main_content_ratio(page),
        content_characters=len(page.content_text),
        furniture_characters=len(page.furniture_text),
        quantities=_quantities(passages),
        tabulated_quantities=_quantities(
            tuple(b for b in passages if b.in_table or b.in_list)
        ),
        has_structured_container=any(b.in_table or b.in_list for b in passages),
    )


def repeatable_passages(page: PageDocument) -> tuple[str, ...]:
    """Content passages long enough that finding them on a second URL means something."""
    return tuple(
        normalise(block.own_text)
        for block in page.passages()
        if len(block.own_text) >= MIN_REPEATED_CHARACTERS
    )


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _topic_terms(page: PageDocument) -> tuple[str, ...]:
    headings = [h for h in page.content_headings() if h.level == 1]
    source = headings[0].text if headings else page.title
    terms = [t for t in _TOKEN_PATTERN.findall(source) if t.lower() not in _TOPIC_STOPWORDS]
    return tuple(dict.fromkeys(terms))


def _term_appears(term: str, text: str) -> bool:
    if term in text:
        return True
    # Korean particles ride on the end of a noun: "보조금은" in the heading, "보조금" in
    # the sentence. Trimming one trailing character catches the common case without
    # pretending this is morphological analysis.
    return len(term) >= 3 and term[:-1] in text


def _find_direct_answer(
    passages: tuple[TextBlock, ...], topic_terms: tuple[str, ...]
) -> DirectAnswer | None:
    if not topic_terms:
        return None

    candidates = [
        block
        for block in passages
        if MIN_ANSWER_CHARACTERS <= len(block.own_text) <= MAX_ANSWER_CHARACTERS
    ]
    for position, block in enumerate(candidates[:4]):
        shared = tuple(term for term in topic_terms if _term_appears(term, block.own_text))
        if _is_dependent(block.own_text):
            continue
        if len(shared) >= 2 or (shared and len(shared) / len(topic_terms) >= 0.5):
            return DirectAnswer(text=block.own_text, shared_terms=shared, position=position)
    return None


def _is_dependent(text: str) -> bool:
    lowered = text.strip().lower()
    return any(lowered.startswith(opening.lower()) for opening in DEPENDENT_OPENINGS)


def _judgeable(passages: tuple[TextBlock, ...]) -> tuple[TextBlock, ...]:
    return tuple(b for b in passages if len(b.own_text) >= MIN_JUDGEABLE_CHARACTERS)


def _self_contained_ratio(passages: tuple[TextBlock, ...]) -> float:
    judgeable = _judgeable(passages)
    if not judgeable:
        return 0.0
    standalone = sum(1 for block in judgeable if not _is_dependent(block.own_text))
    return standalone / len(judgeable)


def _dependent_openings(passages: tuple[TextBlock, ...]) -> tuple[str, ...]:
    return tuple(
        block.own_text[:40] for block in _judgeable(passages) if _is_dependent(block.own_text)
    )


def _heading_report(page: PageDocument) -> HeadingReport:
    headings = page.content_headings()
    levels = tuple(h.level for h in headings)
    skipped: list[tuple[int, int]] = []
    for previous, current in pairwise(levels):
        if current > previous + 1:
            skipped.append((previous, current))
    return HeadingReport(
        levels=levels,
        h1_count=sum(1 for level in levels if level == 1),
        section_count=sum(1 for level in levels if level == 2),
        skipped_levels=tuple(skipped),
    )


def _main_content_ratio(page: PageDocument) -> float:
    content = len(page.content_text)
    furniture = len(page.furniture_text)
    total = content + furniture
    if total == 0:
        return 0.0
    return content / total


def _quantities(blocks: tuple[TextBlock, ...]) -> tuple[str, ...]:
    found: list[str] = []
    for block in blocks:
        if block.region is not Region.CONTENT:
            continue
        found.extend(match.group(0).strip() for match in QUANTITY_PATTERN.finditer(block.own_text))
    return tuple(found)


__all__ = [
    "MIN_ANSWER_CHARACTERS",
    "MIN_REPEATED_CHARACTERS",
    "DirectAnswer",
    "ExtractionSignals",
    "HeadingReport",
    "analyse_extractability",
    "repeatable_passages",
]
