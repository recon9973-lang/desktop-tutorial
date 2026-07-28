"""Deterministic brand detection inside an AI answer.

Five rules hold this package together, and every one of them exists because the obvious
alternative produces a number that flatters the customer:

1. **One mention event per brand per answer.** Five utterances of ``베놈치과`` are one
   mention with ``raw_occurrence_count == 5``. Counting occurrences inflates every rate
   downstream, and nothing later can tell the inflation apart from real exposure.
2. **A mention is not a citation.** Being named in prose and having your URL used as a
   source are different facts worth different amounts. They are never merged.
3. **Ambiguity goes to a human.** ``서울치과`` is dozens of businesses. When the rules cannot
   say it is *this* customer, the verdict is ``NEEDS_REVIEW`` — an admitted unknown, not a
   decision. A confident wrong attribution silently inflates the customer's numbers.
4. **The detector is deterministic.** No model decides whether a brand was mentioned. A
   model may later assist a reviewer; the recorded verdict comes from rules that can be
   reproduced from the same answer text.
5. **Every verdict carries its span** — offset and quoted fragment — so a reviewer can see
   exactly what the machine saw.

The output is shaped for the existing schema and adds no columns: ``entity_mentions``
already carries ``raw_occurrence_count``, ``match_confidence``,
``needs_human_disambiguation`` and ``review_state`` beside its
``UniqueConstraint(ai_answer_id, entity_key)``, and ``citations`` already carries
``is_own_domain``. :class:`~veo.observations.runs.ObservationRun` refuses a citation
without a mention; :attr:`AnswerDetection.brand_cited` cannot be true without
:attr:`AnswerDetection.brand_mentioned`, so that invariant holds by construction.
"""

from veo.observations.detection.citations import (
    CitationMatch,
    CitationOwnership,
    OwnDomainRule,
    match_citations,
    own_citations,
    registrable_domain,
)
from veo.observations.detection.competitors import (
    AnswerDetection,
    detect_answer,
    detect_competitor_mentions,
)
from veo.observations.detection.disambiguation import (
    CONFIRMATION_THRESHOLD,
    Attribution,
    BrandProfile,
    ConfidenceBand,
    Signal,
    assess,
    looks_generic,
)
from veo.observations.detection.mentions import (
    MentionEvent,
    MentionSpan,
    MentionVerdict,
    SpanSource,
    detect_mentions,
    surface_spans,
)
from veo.observations.detection.normalize import (
    BoundaryStrength,
    SurfaceMatch,
    find_surface_matches,
    fold,
    is_particle_run,
    normalize_brand,
    split_business_suffix,
    surface_variants,
)

__all__ = [
    "CONFIRMATION_THRESHOLD",
    "AnswerDetection",
    "Attribution",
    "BoundaryStrength",
    "BrandProfile",
    "CitationMatch",
    "CitationOwnership",
    "ConfidenceBand",
    "MentionEvent",
    "MentionSpan",
    "MentionVerdict",
    "OwnDomainRule",
    "Signal",
    "SpanSource",
    "SurfaceMatch",
    "assess",
    "detect_answer",
    "detect_competitor_mentions",
    "detect_mentions",
    "find_surface_matches",
    "fold",
    "is_particle_run",
    "looks_generic",
    "match_citations",
    "normalize_brand",
    "own_citations",
    "registrable_domain",
    "split_business_suffix",
    "surface_spans",
    "surface_variants",
]
