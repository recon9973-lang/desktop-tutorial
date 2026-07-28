"""One mention event per brand per answer — and never a guess.

The rule that shapes this file: **an answer that names a brand five times is one mention.**
Visibility is a property of the answer, not of the writer's repetition habits. Counting
occurrences multiplies every rate downstream, and no later stage can undo it because the
inflation is indistinguishable from real exposure by then. The repetition is still worth
keeping, so it is kept — separately, as ``raw_occurrence_count``, exactly as
``entity_mentions`` already models it.

Two more rules travel with it:

* **A citation is not a mention, but it implies one.** Prose and sources are different facts
  and are never merged. A source URL on our own domain does, however, name us, so an answer
  that cites us with no prose is still a mention — which is also what
  :class:`veo.observations.runs.ObservationRun` insists on.
* **Ambiguity goes to a human.** When the rules cannot tell whether ``서울치과`` is *this*
  ``서울치과``, the verdict is :attr:`MentionVerdict.NEEDS_REVIEW`. The alternative is a
  number that is quietly too good, which is the one failure a customer cannot audit.

Every verdict carries its spans: the offset and the fragment, so a reviewer sees what the
machine saw. Nothing here consults a model; the verdict is reproducible from the answer text.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from veo.observations.detection.citations import CitationMatch, own_citations
from veo.observations.detection.disambiguation import (
    Attribution,
    BrandProfile,
    ConfidenceBand,
    Signal,
    assess,
)
from veo.observations.detection.normalize import (
    BoundaryStrength,
    find_surface_matches,
)

__all__ = [
    "Attribution",
    "BrandProfile",
    "ConfidenceBand",
    "MentionEvent",
    "MentionSpan",
    "MentionVerdict",
    "Signal",
    "SpanSource",
    "detect_mentions",
    "surface_spans",
]


class MentionVerdict(StrEnum):
    """What the detector is willing to state.

    ``CONFIRMED`` — the brand was named and the rules can say it is this customer.
    ``NEEDS_REVIEW`` — the name appeared, the attribution did not clear the bar. Not a
    mention until a human says so, and never silently counted as one.
    ``NOT_FOUND`` — the name does not appear at all.
    """

    CONFIRMED = "CONFIRMED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_FOUND = "NOT_FOUND"


class SpanSource(StrEnum):
    """Which string the offsets index into."""

    ANSWER_TEXT = "ANSWER_TEXT"
    CITATION_URL = "CITATION_URL"


@dataclass(frozen=True, slots=True)
class MentionSpan:
    """One piece of evidence, quotable back to a reviewer.

    ``source_ref`` is empty for prose (the offsets belong to the answer) and holds the
    canonical URL for a citation hit, so the invariant
    ``haystack[start:end] == quote`` holds for both kinds.
    """

    start: int
    end: int
    quote: str
    surface_form: str
    source: SpanSource
    source_ref: str = ""
    trailing_particle: str = ""
    strength: BoundaryStrength = BoundaryStrength.STRONG


@dataclass(frozen=True, slots=True)
class MentionEvent:
    """One brand, one answer, one event — whatever the repetition count."""

    entity_key: str
    display_name: str
    is_own_brand: bool
    competitor_id: str | None
    verdict: MentionVerdict
    raw_occurrence_count: int
    spans: tuple[MentionSpan, ...]
    first_position: int | None
    match_confidence: float
    confidence_band: ConfidenceBand
    needs_human_disambiguation: bool
    signals: tuple[Signal, ...]
    citations: tuple[CitationMatch, ...] = ()

    @property
    def is_mentioned(self) -> bool:
        """Only a confirmed verdict counts. A pending review is not a mention yet."""
        return self.verdict is MentionVerdict.CONFIRMED

    @property
    def is_cited(self) -> bool:
        return self.is_mentioned and bool(self.citations)

    @property
    def cited_urls(self) -> tuple[str, ...]:
        return tuple(item.canonical_url or item.raw_url for item in self.citations)

    @property
    def evidence_ko(self) -> tuple[str, ...]:
        return tuple(signal.evidence_ko for signal in self.signals)

    def as_entity_mention_values(self) -> dict[str, Any]:
        """The column values an ``entity_mentions`` row wants.

        No new columns: ``review_state`` and ``needs_human_disambiguation`` already exist,
        and the raw count already has its own home beside the single mention event.
        """
        return {
            "entity_key": self.entity_key,
            "is_own_brand": self.is_own_brand,
            "competitor_id": self.competitor_id,
            "raw_occurrence_count": self.raw_occurrence_count,
            "first_position": self.first_position,
            "match_confidence": self.match_confidence,
            "needs_human_disambiguation": self.needs_human_disambiguation,
            "review_state": (
                "PENDING_REVIEW"
                if self.verdict is MentionVerdict.NEEDS_REVIEW
                else "NOT_REVIEWED"
            ),
        }


def surface_spans(answer_text: str, profile: BrandProfile) -> tuple[tuple[int, int], ...]:
    """Where ``profile``'s declared names appear. Used to build one brand's rival set."""
    return tuple(
        (match.start, match.end) for match in find_surface_matches(answer_text, profile.names)
    )


def detect_mentions(
    answer_text: str,
    profile: BrandProfile,
    *,
    citations: Sequence[CitationMatch] = (),
    rival_spans: Sequence[tuple[int, int]] = (),
) -> MentionEvent:
    """Detect one brand in one answer.

    This is the single entry point. The customer's brand and every declared competitor go
    through it with the same arguments and the same rules — asymmetric detection would rig
    Share of Voice without anyone touching the arithmetic.
    """
    matches = find_surface_matches(answer_text, profile.names)
    ours = own_citations(citations)

    text_spans = tuple(
        MentionSpan(
            start=match.start,
            end=match.end,
            quote=match.quote,
            surface_form=match.surface_form,
            source=SpanSource.ANSWER_TEXT,
            trailing_particle=match.trailing_particle,
            strength=match.strength,
        )
        for match in matches
    )
    citation_spans = tuple(_citation_span(item) for item in ours)
    spans = text_spans + citation_spans

    if not spans:
        return _empty(profile)

    strong = tuple(
        span for span in text_spans if span.strength is BoundaryStrength.STRONG
    )
    attribution = assess(
        answer_text,
        profile,
        spans=tuple((span.start, span.end) for span in strong),
        rival_spans=rival_spans,
        own_citation_count=len(ours),
        weak_only=bool(text_spans) and not strong,
    )

    verdict = (
        MentionVerdict.CONFIRMED
        if attribution.band is ConfidenceBand.HIGH
        else MentionVerdict.NEEDS_REVIEW
    )

    return MentionEvent(
        entity_key=profile.entity_key,
        display_name=profile.display_name,
        is_own_brand=profile.is_own_brand,
        competitor_id=profile.competitor_id,
        verdict=verdict,
        raw_occurrence_count=len(spans),
        spans=spans,
        first_position=text_spans[0].start if text_spans else None,
        match_confidence=attribution.confidence,
        confidence_band=attribution.band,
        needs_human_disambiguation=verdict is MentionVerdict.NEEDS_REVIEW,
        signals=attribution.signals,
        citations=ours,
    )


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _citation_span(match: CitationMatch) -> MentionSpan:
    """A citation of our own domain names us, so it is evidence like any other."""
    url = match.canonical_url or match.raw_url
    start = url.find(match.host)
    if start < 0:
        start, end = 0, len(url)
    else:
        end = start + len(match.host)
    return MentionSpan(
        start=start,
        end=end,
        quote=url[start:end],
        surface_form=match.matched_domain or match.host,
        source=SpanSource.CITATION_URL,
        source_ref=url,
    )


def _empty(profile: BrandProfile) -> MentionEvent:
    return MentionEvent(
        entity_key=profile.entity_key,
        display_name=profile.display_name,
        is_own_brand=profile.is_own_brand,
        competitor_id=profile.competitor_id,
        verdict=MentionVerdict.NOT_FOUND,
        raw_occurrence_count=0,
        spans=(),
        first_position=None,
        match_confidence=0.0,
        confidence_band=ConfidenceBand.LOW,
        needs_human_disambiguation=False,
        signals=(),
        citations=(),
    )
