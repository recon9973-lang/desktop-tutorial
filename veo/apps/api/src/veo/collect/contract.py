"""What a collector is given, and what it must hand back.

A collector observes. It does not score. It returns a :class:`~veo.scoring.CheckOutcome`
per check — a status, the evidence behind it, and how confident that evidence makes it —
and the evaluator turns those into a number using the published specification. No checker
may contain a weight, a severity or a threshold that decides points.

Two rules the type system enforces here:

* A collector declares which check ids it owns and must return an outcome for **every**
  one of them. Silence is not permitted: if a check could not be run, it says
  ``UNKNOWN`` with a reason, which lowers coverage and confidence but never the score.
* Every non-trivial outcome points at evidence. A finding nobody can audit is a rumour.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from veo.common.security.fetcher import FetchedDocument
from veo.contracts.enums import ProviderState
from veo.scoring import CheckOutcome, CheckStatus, ScoringSpec


class CollectorError(Exception):
    """A collector could not run at all. Distinct from a check that failed."""


class MissingOutcomeError(CollectorError):
    """A collector declared a check and then did not report on it."""


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """The raw material behind one observation.

    ``content_hash`` is what makes a finding defensible months later: the bytes that were
    judged can be shown to be the bytes that were fetched.
    """

    evidence_id: str
    kind: str
    """http_response | dom_snippet | robots_txt | sitemap_document | provider_response | ..."""
    url: str | None
    collected_at: datetime
    content_hash: str
    excerpt: str = ""
    """A short, human-readable extract. Never the whole document, never a credential."""
    storage_key: str | None = None
    """Where the full artefact lives in object storage, when it was kept."""
    detail: Mapping[str, object] = field(default_factory=dict)

    @classmethod
    def of(
        cls,
        kind: str,
        *,
        url: str | None,
        payload: bytes | str,
        excerpt: str = "",
        collected_at: datetime | None = None,
        storage_key: str | None = None,
        detail: Mapping[str, object] | None = None,
    ) -> EvidenceRecord:
        raw = payload.encode("utf-8") if isinstance(payload, str) else payload
        content_hash = hashlib.sha256(raw).hexdigest()
        return cls(
            evidence_id=f"{kind}:{content_hash[:16]}",
            kind=kind,
            url=url,
            collected_at=collected_at or datetime.now(UTC),
            content_hash=content_hash,
            excerpt=excerpt[:2000],
            storage_key=storage_key,
            detail=dict(detail or {}),
        )


@dataclass(frozen=True, slots=True)
class IssueDraft:
    """A problem worth acting on, in the shape the console and reports need.

    A collector proposes an issue; nothing here decides its score contribution. The
    severity comes from the specification via the check id, not from the collector.
    """

    check_id: str
    title_ko: str
    summary_ko: str
    affected_urls: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    remediation_ko: str
    remediation_owner: str
    business_impact_ko: str = ""
    fix_example: str | None = None
    reverification_note_ko: str = ""


@dataclass(frozen=True, slots=True)
class CollectionContext:
    """Everything a collector may read. It fetches nothing itself.

    Collectors are given already-fetched material so that a single crawl feeds every
    engine, so that the SSRF guard sits in exactly one place, and so that a collector can
    be tested against a fixture with no network at all.
    """

    target_url: str
    spec: ScoringSpec
    documents: Mapping[str, FetchedDocument]
    """Fetched pages, keyed by their final URL."""
    primary_document: FetchedDocument | None = None
    robots_txt: str | None = None
    sitemap_documents: Mapping[str, str] = field(default_factory=dict)
    rendered_dom: Mapping[str, str] = field(default_factory=dict)
    """DOM after JavaScript execution, when a renderer ran. Kept apart from raw HTML
    because 'the crawler sees it' and 'the browser shows it' are different questions."""
    provider_states: Mapping[str, ProviderState] = field(default_factory=dict)
    provider_payloads: Mapping[str, object] = field(default_factory=dict)
    url_importance: Mapping[str, str] = field(default_factory=dict)
    crawl_is_exhaustive: bool = False
    """Did the crawl fetch every URL it could discover, before hitting any ceiling?

    This exists to keep a collection limit from masquerading as a fact about the site.
    Several checks compare pages against each other — duplicate titles, duplicate bodies,
    internal link density — and none of them can be judged from a single page. The
    question is *why* there is only one page, and the two answers are not interchangeable:

    * The site has one page. The check does not apply; it leaves the denominator.
    * We only fetched one page. The check could not be run; it stays in the denominator
      and scores zero.

    Defaulting to ``False`` is the honest default. A context built from a fixture, or from
    an explicit list of URLs, has established nothing about how large the site is — and
    treating "we did not look" as "there is nothing there" is how a denominator starts
    moving with what we happened to collect, which makes measuring less the better
    strategy. That mistake has been made three times already; see ADR 0016.

    Only the discovery crawl may set this, and only when it ran out of addresses to
    fetch before reaching the page ceiling, the depth ceiling or the host budget.
    """
    locale: str = "ko-KR"
    collected_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def provider_is_enabled(self, provider: str) -> bool:
        return self.provider_states.get(provider) is ProviderState.ENABLED

    def document_for(self, url: str) -> FetchedDocument | None:
        return self.documents.get(url)


@dataclass(frozen=True, slots=True)
class CollectionResult:
    """What a collector produces. Outcomes only — never a score."""

    outcomes: tuple[CheckOutcome, ...]
    evidence: tuple[EvidenceRecord, ...] = ()
    issues: tuple[IssueDraft, ...] = ()
    notes_ko: tuple[str, ...] = ()

    def outcome_ids(self) -> frozenset[str]:
        return frozenset(o.check_id for o in self.outcomes)

    def merge(self, other: CollectionResult) -> CollectionResult:
        overlap = self.outcome_ids() & other.outcome_ids()
        if overlap:
            raise CollectorError(
                "two collectors reported the same check(s): " + ", ".join(sorted(overlap))
            )
        return CollectionResult(
            outcomes=self.outcomes + other.outcomes,
            evidence=self.evidence + other.evidence,
            issues=self.issues + other.issues,
            notes_ko=self.notes_ko + other.notes_ko,
        )


@runtime_checkable
class Collector(Protocol):
    """A unit of observation, responsible for a fixed set of check ids."""

    @property
    def check_ids(self) -> frozenset[str]: ...

    def collect(self, context: CollectionContext) -> CollectionResult: ...


def unknown_outcome(
    check_id: str,
    reason_ko: str,
    *,
    evidence_ids: Sequence[str] = (),
) -> CheckOutcome:
    """The honest answer when a check could not be run.

    Used when a provider has no credential, a renderer was unavailable, or a page could
    not be fetched. It costs no points and lowers coverage instead, so the gap stays
    visible rather than masquerading as a pass.
    """
    return CheckOutcome(
        check_id=check_id,
        status=CheckStatus.UNKNOWN,
        confidence=0.0,
        evidence_ids=tuple(evidence_ids),
        note=reason_ko,
    )


def not_applicable_outcome(
    check_id: str,
    reason_ko: str,
    *,
    evidence_ids: Sequence[str] = (),
) -> CheckOutcome:
    """The check does not apply here. It leaves the denominator entirely."""
    return CheckOutcome(
        check_id=check_id,
        status=CheckStatus.NOT_APPLICABLE,
        confidence=1.0,
        evidence_ids=tuple(evidence_ids),
        note=reason_ko,
    )


def verify_complete(
    result: CollectionResult,
    declared: frozenset[str],
    *,
    collector_name: str = "collector",
) -> None:
    """Refuse a collector that stayed silent about a check it owns.

    Missing outcomes are the failure mode that quietly inflates a score: the evaluator
    would never see the check, so nothing would ever be deducted for it.
    """
    reported = result.outcome_ids()

    missing = declared - reported
    if missing:
        raise MissingOutcomeError(
            f"{collector_name} declared but did not report: {', '.join(sorted(missing))}"
        )

    extra = reported - declared
    if extra:
        raise CollectorError(
            f"{collector_name} reported checks it does not own: {', '.join(sorted(extra))}"
        )


def run_collectors(
    collectors: Sequence[Collector], context: CollectionContext
) -> CollectionResult:
    """Run every collector and combine the results, refusing overlap or silence."""
    combined = CollectionResult(outcomes=())
    for collector in collectors:
        result = collector.collect(context)
        verify_complete(result, collector.check_ids, collector_name=type(collector).__name__)
        combined = combined.merge(result)
    return combined


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
