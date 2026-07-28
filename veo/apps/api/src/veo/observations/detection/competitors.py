"""The same detection, applied to the declared competitor set.

Share of Voice is a ratio, and a ratio is only as honest as the two counts feeding it.
Detecting our own brand generously and a competitor's strictly would move every share in
our favour without a single change to the arithmetic — and the arithmetic is the part
anybody would think to audit. So there is exactly one detector, and this module is a
dispatcher over it, not a second implementation.

Two consequences worth stating, because they are easy to lose later:

* Competitor detection calls :func:`veo.observations.detection.mentions.detect_mentions`
  through the module, so a test can intercept the call and prove the shared path rather
  than trust a comment.
* The "named only in a rival's sentence" signal is symmetric. Our brand's rivals are the
  competitors; each competitor's rivals are us and the other competitors. Handing that
  discount to one side only would be the same rigging by another route.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from veo.observations.detection import mentions as mentions_module
from veo.observations.detection.citations import CitationMatch, match_citations
from veo.observations.detection.disambiguation import BrandProfile
from veo.observations.detection.mentions import MentionEvent, MentionVerdict, surface_spans

__all__ = [
    "AnswerDetection",
    "detect_answer",
    "detect_competitor_mentions",
]


@dataclass(frozen=True, slots=True)
class AnswerDetection:
    """Everything one answer yielded, for us and for the comparison set."""

    own: MentionEvent
    competitors: tuple[MentionEvent, ...] = ()
    own_citations: tuple[CitationMatch, ...] = ()

    @property
    def brand_mentioned(self) -> bool:
        """What ``ObservationRun.brand_mentioned`` should be set to."""
        return self.own.is_mentioned

    @property
    def brand_cited(self) -> bool:
        """What ``ObservationRun.brand_cited`` should be set to.

        Never true without :attr:`brand_mentioned`: an own-domain citation is decisive
        evidence of the mention, so the two can only move together.
        """
        return self.own.is_cited

    @property
    def own_citation_urls(self) -> tuple[str, ...]:
        return self.own.cited_urls

    @property
    def mentioned_entity_keys(self) -> tuple[str, ...]:
        """Confirmed entities only. A pending review is not yet a mention."""
        return tuple(
            event.entity_key
            for event in (self.own, *self.competitors)
            if event.is_mentioned
        )

    @property
    def needs_review(self) -> tuple[MentionEvent, ...]:
        """Everything the detector refused to decide, for the human queue."""
        return tuple(
            event
            for event in (self.own, *self.competitors)
            if event.verdict is MentionVerdict.NEEDS_REVIEW
        )


def detect_competitor_mentions(
    answer_text: str,
    profiles: Sequence[BrandProfile],
    *,
    citations: Sequence[str] = (),
    rival_spans_by_key: dict[str, tuple[tuple[int, int], ...]] | None = None,
) -> tuple[MentionEvent, ...]:
    """Run the customer's detector over each declared competitor."""
    rivals = rival_spans_by_key or {}
    found: list[MentionEvent] = []
    for profile in profiles:
        found.append(
            mentions_module.detect_mentions(
                answer_text,
                profile,
                citations=match_citations(citations, profile),
                rival_spans=rivals.get(profile.entity_key, ()),
            )
        )
    return tuple(found)


def detect_answer(
    answer_text: str,
    *,
    own: BrandProfile,
    competitors: Sequence[BrandProfile] = (),
    citations: Sequence[str] = (),
) -> AnswerDetection:
    """Detect every declared brand in one answer, both sides by the same rules."""
    profiles = (own, *competitors)
    spans_by_key = {profile.entity_key: surface_spans(answer_text, profile) for profile in profiles}
    rivals = {
        profile.entity_key: tuple(
            span
            for other in profiles
            if other.entity_key != profile.entity_key
            for span in spans_by_key[other.entity_key]
        )
        for profile in profiles
    }

    own_matches = match_citations(citations, own)
    own_event = mentions_module.detect_mentions(
        answer_text,
        own,
        citations=own_matches,
        rival_spans=rivals[own.entity_key],
    )
    competitor_events = detect_competitor_mentions(
        answer_text,
        competitors,
        citations=citations,
        rival_spans_by_key=rivals,
    )
    return AnswerDetection(
        own=own_event,
        competitors=competitor_events,
        own_citations=own_event.citations,
    )
