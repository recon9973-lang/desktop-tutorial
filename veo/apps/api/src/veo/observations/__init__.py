"""Observed AI visibility.

Kept apart from GEO readiness at every level — separate engine, separate score, separate
screen. Readiness asks whether a page *can* be used by an AI answer engine; observation
asks whether it *was*. Merging them would let a structurally tidy page report visibility
it has never had.
"""

from veo.observations.prompts import (
    MAX_BRAND_SUBJECT_SHARE,
    MAX_SINGLE_INTENT_SHARE,
    MIN_PROMPTS_PER_SET,
    REQUIRED_INTENTS,
    Exclusion,
    Funnel,
    Intent,
    Prompt,
    PromptSet,
    PromptSetImbalanceError,
    Subject,
)
from veo.observations.runs import (
    AccountState,
    MixedConditionsError,
    ObservationRun,
    RunConditions,
    SearchMode,
    aggregate_rate,
    group_by_conditions,
)
from veo.observations.sampling import (
    MIN_RUNS_FOR_COMPARISON,
    MIN_RUNS_FOR_EXPLORATION,
    InsufficientSampleError,
    ObservedRate,
    SampleAdequacy,
    wilson_interval,
)

__all__ = [
    "MAX_BRAND_SUBJECT_SHARE",
    "MAX_SINGLE_INTENT_SHARE",
    "MIN_PROMPTS_PER_SET",
    "MIN_RUNS_FOR_COMPARISON",
    "MIN_RUNS_FOR_EXPLORATION",
    "REQUIRED_INTENTS",
    "AccountState",
    "Exclusion",
    "Funnel",
    "InsufficientSampleError",
    "Intent",
    "MixedConditionsError",
    "ObservationRun",
    "ObservedRate",
    "Prompt",
    "PromptSet",
    "PromptSetImbalanceError",
    "RunConditions",
    "SampleAdequacy",
    "SearchMode",
    "Subject",
    "aggregate_rate",
    "group_by_conditions",
    "wilson_interval",
]
