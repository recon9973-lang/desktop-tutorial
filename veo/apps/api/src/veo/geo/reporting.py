"""Shared plumbing for the GEO collectors: outcomes, evidence and Korean findings.

Every helper here is deliberately arithmetic-free. A collector states *what it saw* and
*how sure the evidence makes it*; the published specification turns that into a number.
Confidence is always named — ``DIRECT_OBSERVATION`` when something was read straight off
the wire, ``HEURISTIC_*`` when it was judged, ``EXTERNAL_ESTIMATE`` when an outside
source said so — so a reader can tell measurement from opinion without reading the code.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from veo.collect.contract import EvidenceRecord, IssueDraft
from veo.scoring import CheckOutcome, CheckStatus

#: Named confidence levels defined by ``veo.geo.readiness``. The numbers behind these
#: names live in the specification and nowhere else.
DIRECT: Final = "DIRECT_OBSERVATION"
HIGH: Final = "HEURISTIC_HIGH"
MEDIUM: Final = "HEURISTIC_MEDIUM"
LOW: Final = "HEURISTIC_LOW"
OUTSIDE: Final = "EXTERNAL_ESTIMATE"

TROUBLED_STATUSES = frozenset({CheckStatus.FAIL, CheckStatus.WARNING})


def observed(
    check_id: str,
    status: CheckStatus,
    *,
    confidence_level: str,
    note_ko: str,
    evidence_ids: Sequence[str] = (),
    observed_value: Any = None,
    affected_weight: float = 1.0,
    evaluated_weight: float = 1.0,
) -> CheckOutcome:
    """One observation, in the shape the evaluator expects."""
    return CheckOutcome(
        check_id=check_id,
        status=status,
        confidence_level=confidence_level,
        evidence_ids=tuple(evidence_ids),
        observed_value=observed_value,
        note=note_ko,
        affected_weight=affected_weight,
        evaluated_weight=evaluated_weight,
    )


def html_evidence(url: str, body: bytes, *, excerpt: str = "") -> EvidenceRecord:
    return EvidenceRecord.of("http_response", url=url, payload=body, excerpt=excerpt)


def snippet_evidence(
    url: str,
    kind: str,
    payload: str,
    *,
    excerpt: str = "",
    detail: Mapping[str, object] | None = None,
) -> EvidenceRecord:
    return EvidenceRecord.of(
        kind, url=url, payload=payload, excerpt=excerpt or payload[:400], detail=detail
    )


def finding(
    check_id: str,
    *,
    title_ko: str,
    summary_ko: str,
    remediation_ko: str,
    remediation_owner: str,
    urls: Sequence[str],
    evidence_ids: Sequence[str],
    business_impact_ko: str = "",
    fix_example: str | None = None,
    reverification_note_ko: str = "",
) -> IssueDraft:
    """A problem worth acting on. Nothing here decides what it costs."""
    return IssueDraft(
        check_id=check_id,
        title_ko=title_ko,
        summary_ko=summary_ko,
        affected_urls=tuple(urls),
        evidence_ids=tuple(evidence_ids),
        remediation_ko=remediation_ko,
        remediation_owner=remediation_owner,
        business_impact_ko=business_impact_ko,
        fix_example=fix_example,
        reverification_note_ko=reverification_note_ko,
    )


def worst(*statuses: CheckStatus) -> CheckStatus:
    """The most serious of several observations about one check."""
    order = (
        CheckStatus.FAIL,
        CheckStatus.WARNING,
        CheckStatus.UNKNOWN,
        CheckStatus.PASS,
        CheckStatus.NOT_APPLICABLE,
    )
    for candidate in order:
        if candidate in statuses:
            return candidate
    return CheckStatus.UNKNOWN


__all__ = [
    "DIRECT",
    "HIGH",
    "LOW",
    "MEDIUM",
    "OUTSIDE",
    "TROUBLED_STATUSES",
    "finding",
    "html_evidence",
    "observed",
    "snippet_evidence",
    "worst",
]
