"""Collection: turning fetched material into observations.

Collectors observe and report ``CheckOutcome``s. The evaluator, and only the evaluator,
turns those into a score using the published VEO-LAB specification.
"""

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    Collector,
    CollectorError,
    EvidenceRecord,
    IssueDraft,
    MissingOutcomeError,
    not_applicable_outcome,
    run_collectors,
    unknown_outcome,
    verify_complete,
)

__all__ = [
    "CollectionContext",
    "CollectionResult",
    "Collector",
    "CollectorError",
    "EvidenceRecord",
    "IssueDraft",
    "MissingOutcomeError",
    "not_applicable_outcome",
    "run_collectors",
    "unknown_outcome",
    "verify_complete",
]
