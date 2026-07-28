"""VEO scoring: versioned specifications and one deterministic evaluator.

Weights, severities, caps and gates live in ``packages/scoring-specs`` and are authored
by VEO-LAB. Checker code contributes observations only; it never contributes numbers.
"""

from veo.scoring.errors import ScoringSpecError, SpecNotFoundError
from veo.scoring.evaluator import evaluate
from veo.scoring.models import (
    AppliedCap,
    CategoryScore,
    CheckOutcome,
    CheckStatus,
    RaisedGate,
    ScoreResult,
    ScoringDomain,
    ScoringSpec,
    Severity,
    SpecCap,
    SpecCategory,
    SpecCheck,
    SpecGate,
    SpecStatus,
)
from veo.scoring.spec import (
    available_specs,
    build_spec,
    canonical_json,
    compute_checksum,
    find_specs_root,
    latest_published,
    load_spec,
    load_spec_file,
)

__all__ = [
    "AppliedCap",
    "CategoryScore",
    "CheckOutcome",
    "CheckStatus",
    "RaisedGate",
    "ScoreResult",
    "ScoringDomain",
    "ScoringSpec",
    "ScoringSpecError",
    "Severity",
    "SpecCap",
    "SpecCategory",
    "SpecCheck",
    "SpecGate",
    "SpecNotFoundError",
    "SpecStatus",
    "available_specs",
    "build_spec",
    "canonical_json",
    "compute_checksum",
    "evaluate",
    "find_specs_root",
    "latest_published",
    "load_spec",
    "load_spec_file",
]
