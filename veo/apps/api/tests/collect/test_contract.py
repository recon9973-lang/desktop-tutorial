"""The collector contract, which exists to stop two specific failures.

1. A collector quietly not reporting a check it owns — the evaluator never sees it, so
   nothing is ever deducted and the score is silently inflated.
2. A collector deciding points for itself, which would put a weight somewhere other than
   the published specification.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from veo.collect.contract import (
    CollectionContext,
    CollectionResult,
    Collector,
    CollectorError,
    EvidenceRecord,
    MissingOutcomeError,
    not_applicable_outcome,
    run_collectors,
    unknown_outcome,
    verify_complete,
)
from veo.contracts.enums import ProviderState
from veo.scoring import CheckOutcome, CheckStatus, latest_published

SPEC = latest_published("veo.seo.readiness")


def context(**overrides: object) -> CollectionContext:
    base: dict[str, object] = {
        "target_url": "https://example.com/",
        "spec": SPEC,
        "documents": {},
    }
    base.update(overrides)
    return CollectionContext(**base)  # type: ignore[arg-type]


def outcome(check_id: str, status: CheckStatus = CheckStatus.PASS) -> CheckOutcome:
    return CheckOutcome(check_id=check_id, status=status, confidence=1.0)


class TinyCollector:
    """Reports on exactly two checks."""

    def __init__(self, result: CollectionResult) -> None:
        self._result = result

    @property
    def check_ids(self) -> frozenset[str]:
        return frozenset({"seo.http.status_ok", "seo.http.redirect_chain_sane"})

    def collect(self, context: CollectionContext) -> CollectionResult:
        return self._result


# --------------------------------------------------------------------------- #
# Silence is refused
# --------------------------------------------------------------------------- #


def test_a_collector_must_report_every_check_it_declares() -> None:
    result = CollectionResult(outcomes=(outcome("seo.http.status_ok"),))
    with pytest.raises(MissingOutcomeError, match=r"seo\.http\.redirect_chain_sane"):
        verify_complete(result, TinyCollector(result).check_ids)


def test_a_collector_may_not_report_a_check_it_does_not_own() -> None:
    result = CollectionResult(
        outcomes=(
            outcome("seo.http.status_ok"),
            outcome("seo.http.redirect_chain_sane"),
            outcome("seo.onpage.title_present_and_unique"),
        )
    )
    with pytest.raises(CollectorError, match="does not own"):
        verify_complete(result, TinyCollector(result).check_ids)


def test_a_complete_collector_passes() -> None:
    result = CollectionResult(
        outcomes=(outcome("seo.http.status_ok"), outcome("seo.http.redirect_chain_sane"))
    )
    verify_complete(result, TinyCollector(result).check_ids)


def test_reporting_unknown_counts_as_reporting() -> None:
    """A check that could not be run is still answered — that is the whole point."""
    result = CollectionResult(
        outcomes=(
            outcome("seo.http.status_ok"),
            unknown_outcome("seo.http.redirect_chain_sane", "리다이렉트를 수집하지 못했습니다"),
        )
    )
    verify_complete(result, TinyCollector(result).check_ids)


# --------------------------------------------------------------------------- #
# UNKNOWN and N/A carry their meaning
# --------------------------------------------------------------------------- #


def test_unknown_costs_no_confidence_and_states_a_reason() -> None:
    o = unknown_outcome("seo.integration.gsc_verified", "Search Console 연동이 없습니다")
    assert o.status is CheckStatus.UNKNOWN
    assert o.confidence == 0.0
    assert o.note

def test_not_applicable_is_fully_confident_about_being_irrelevant() -> None:
    """N/A is a positive determination, not a gap — it is known, not unmeasured."""
    o = not_applicable_outcome("seo.sd.jsonld_parses", "구조화 데이터가 없는 페이지입니다")
    assert o.status is CheckStatus.NOT_APPLICABLE
    assert o.confidence == 1.0
    assert o.note


def test_a_disabled_provider_is_visible_in_the_context() -> None:
    ctx = context(
        provider_states={
            "NAVER_SEARCH_AD": ProviderState.DISABLED_NO_CREDENTIAL,
            "GOOGLE_PAGESPEED": ProviderState.ENABLED,
        }
    )
    assert not ctx.provider_is_enabled("NAVER_SEARCH_AD")
    assert ctx.provider_is_enabled("GOOGLE_PAGESPEED")
    assert not ctx.provider_is_enabled("NEVER_HEARD_OF_IT")


# --------------------------------------------------------------------------- #
# Evidence
# --------------------------------------------------------------------------- #


def test_evidence_hashes_its_payload() -> None:
    import hashlib

    payload = b"<html><title>VEO</title></html>"
    record = EvidenceRecord.of("dom_snippet", url="https://example.com/", payload=payload)

    assert record.content_hash == hashlib.sha256(payload).hexdigest()
    assert record.evidence_id.startswith("dom_snippet:")
    assert record.collected_at.tzinfo is not None


def test_identical_payloads_produce_identical_evidence_ids() -> None:
    a = EvidenceRecord.of("robots_txt", url=None, payload="User-agent: *")
    b = EvidenceRecord.of("robots_txt", url=None, payload="User-agent: *")
    assert a.content_hash == b.content_hash
    assert a.evidence_id == b.evidence_id


def test_an_excerpt_is_capped_so_evidence_cannot_swallow_a_whole_page() -> None:
    record = EvidenceRecord.of(
        "text_extract", url=None, payload=b"x", excerpt="가" * 10_000
    )
    assert len(record.excerpt) <= 2000


def test_evidence_accepts_text_or_bytes_identically() -> None:
    text = EvidenceRecord.of("robots_txt", url=None, payload="User-agent: *")
    raw = EvidenceRecord.of("robots_txt", url=None, payload=b"User-agent: *")
    assert text.content_hash == raw.content_hash


# --------------------------------------------------------------------------- #
# Composition
# --------------------------------------------------------------------------- #


def test_running_several_collectors_combines_their_outcomes() -> None:
    class Other:
        @property
        def check_ids(self) -> frozenset[str]:
            return frozenset({"seo.onpage.title_present_and_unique"})

        def collect(self, context: CollectionContext) -> CollectionResult:
            return CollectionResult(outcomes=(outcome("seo.onpage.title_present_and_unique"),))

    first = TinyCollector(
        CollectionResult(
            outcomes=(outcome("seo.http.status_ok"), outcome("seo.http.redirect_chain_sane"))
        )
    )
    combined = run_collectors([first, Other()], context())
    assert len(combined.outcomes) == 3


def test_two_collectors_claiming_the_same_check_is_an_error() -> None:
    """Overlap means two sources of truth for one observation."""
    a = CollectionResult(outcomes=(outcome("seo.http.status_ok"),))
    b = CollectionResult(outcomes=(outcome("seo.http.status_ok"),))
    with pytest.raises(CollectorError, match="same check"):
        a.merge(b)


def test_run_collectors_refuses_a_silent_collector() -> None:
    silent = TinyCollector(CollectionResult(outcomes=(outcome("seo.http.status_ok"),)))
    with pytest.raises(MissingOutcomeError):
        run_collectors([silent], context())


def test_tiny_collector_satisfies_the_protocol() -> None:
    assert isinstance(TinyCollector(CollectionResult(outcomes=())), Collector)


# --------------------------------------------------------------------------- #
# The boundary that matters: collectors observe, the evaluator scores
# --------------------------------------------------------------------------- #


def test_a_collection_result_carries_no_score_field() -> None:
    """If a collector could return a number, a weight would eventually live in a checker."""
    fields = set(CollectionResult.__dataclass_fields__)
    for forbidden in ("score", "points", "weight", "severity", "penalty"):
        assert forbidden not in fields


def test_a_check_outcome_carries_no_severity_of_its_own() -> None:
    fields = set(CheckOutcome.model_fields)
    assert "severity" not in fields
    assert "weight" not in fields
    assert "score" not in fields


def test_collected_outcomes_feed_the_evaluator_unchanged() -> None:
    """End to end: observations in, a specification-derived score out."""
    from veo.scoring import evaluate

    outcomes = [outcome(check_id) for check_id in SPEC.check_ids]
    result = evaluate(SPEC, outcomes)

    assert result.overall_score == 100.0
    assert result.spec_checksum == SPEC.checksum


def test_context_defaults_are_honest_about_what_was_not_collected() -> None:
    ctx = context()
    assert ctx.robots_txt is None
    assert ctx.rendered_dom == {}
    assert ctx.primary_document is None
    assert ctx.collected_at <= datetime.now(UTC)
