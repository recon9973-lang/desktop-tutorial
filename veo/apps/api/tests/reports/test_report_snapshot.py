"""Freezing a diagnosis, and proving the frozen thing cannot drift."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest
from report_support import (
    COMPETITOR_SCORE,
    EVIDENCE_SENTINEL,
    GEO_OVERALL,
    NOT_APPLICABLE_REASON,
    SEO_CONTENT_SCORE,
    SEO_COVERAGE,
    SEO_CRAWL_SCORE,
    SEO_OVERALL,
    SPEC_CHECKSUM,
    SPEC_VERSION,
    UNKNOWN_REASON,
    make_conditions,
    make_diagnosis,
)

from veo.reports.snapshot import (
    NOT_APPLICABLE_KO,
    UNMEASURED_KO,
    MeasuredValue,
    ReportTamperedError,
    ValueStatus,
    freeze,
    from_payload,
    to_payload,
)


def test_a_frozen_snapshot_carries_every_number_it_was_given() -> None:
    snapshot = freeze(make_diagnosis())

    assert snapshot.metric("SEO_READINESS.overall").value.value == SEO_OVERALL
    assert snapshot.metric("GEO_READINESS.overall").value.value == GEO_OVERALL
    assert snapshot.metric("SEO_READINESS.category.crawlability").value.value == SEO_CRAWL_SCORE
    assert snapshot.metric("SEO_READINESS.category.content").value.value == SEO_CONTENT_SCORE
    assert snapshot.metric("SEO_READINESS.coverage").value.value == pytest.approx(
        SEO_COVERAGE * 100
    )


def test_every_number_names_the_methodology_that_produced_it() -> None:
    snapshot = freeze(make_diagnosis())

    for row in snapshot.metrics:
        provenance = snapshot.provenance[row.provenance_ref]
        assert provenance.methodology_ko, f"{row.metric_key} has provenance with no method"
        assert row.value.source, f"{row.metric_key} has a value with no source"
        if row.domain is not None and row.provenance_ref == row.domain:
            # A scored figure must name the published specification behind it.
            assert provenance.has_spec
            assert provenance.measured_at is not None

    seo = snapshot.provenance["SEO_READINESS"]
    assert seo.spec_version == SPEC_VERSION
    assert seo.spec_checksum == SPEC_CHECKSUM
    assert SPEC_VERSION in snapshot.methodology_summary_ko()
    assert SPEC_CHECKSUM in snapshot.methodology_summary_ko()


def test_a_keyword_figure_does_not_borrow_the_scoring_specs_authority() -> None:
    """Keyword demand comes from a provider, not from a VEO-LAB specification."""
    snapshot = freeze(make_diagnosis())
    row = snapshot.metric("keyword.강남 임플란트.monthly_searches")
    provenance = snapshot.provenance[row.provenance_ref]

    assert provenance.has_spec is False
    assert provenance.methodology_ko
    assert row.value.source == "NAVER_SEARCH_AD"


def test_an_unmeasured_category_says_measurement_unavailable_and_why() -> None:
    snapshot = freeze(make_diagnosis())
    row = snapshot.metric("SEO_READINESS.category.indexing")

    assert row.value.status is ValueStatus.UNMEASURED
    assert row.value.value is None
    assert row.value.display() == UNMEASURED_KO
    assert row.value.reason_ko
    assert UNKNOWN_REASON in row.value.reason_ko


def test_a_not_applicable_category_says_not_applicable_and_why() -> None:
    snapshot = freeze(make_diagnosis())
    row = snapshot.metric("SEO_READINESS.category.i18n")

    assert row.value.status is ValueStatus.NOT_APPLICABLE
    assert row.value.display() == NOT_APPLICABLE_KO
    assert NOT_APPLICABLE_REASON in (row.value.reason_ko or "")


def test_an_unmeasured_value_is_never_zero_and_never_a_dash() -> None:
    snapshot = freeze(make_diagnosis())
    for row in snapshot.metrics:
        if row.value.status is ValueStatus.MEASURED:
            continue
        assert row.value.value is None
        assert row.value.display() not in {"0", "0.0", "-", "", "—", "N/A"}
        assert row.value.display() in {UNMEASURED_KO, NOT_APPLICABLE_KO}


def test_a_value_without_a_number_must_carry_a_reason() -> None:
    with pytest.raises(ValueError, match="사유"):
        MeasuredValue(status=ValueStatus.UNMEASURED, value=None, reason_ko=None, source="x")


def test_a_measured_value_must_actually_have_a_number() -> None:
    with pytest.raises(ValueError):
        MeasuredValue(status=ValueStatus.MEASURED, value=None, source="x")


def test_a_competitor_gap_measured_under_a_different_methodology_is_not_subtracted() -> None:
    snapshot = freeze(make_diagnosis())

    theirs = snapshot.metric("competitor.competitor-a.SEO_READINESS.theirs")
    gap = snapshot.metric("competitor.competitor-a.SEO_READINESS.gap")

    assert theirs.value.value == COMPETITOR_SCORE
    assert gap.value.status is ValueStatus.UNMEASURED
    assert gap.value.display() == UNMEASURED_KO
    assert "방법론" in (gap.value.reason_ko or "")


def test_a_comparison_records_the_conditions_it_was_measured_under() -> None:
    snapshot = freeze(make_diagnosis())
    comparison = snapshot.competitors[0]

    assert comparison.our_conditions["spec_version"] == SPEC_VERSION
    assert comparison.their_conditions["spec_version"] == "1.3.0"
    assert comparison.is_comparable is False
    fields = {difference["field"] for difference in comparison.differences}
    assert "spec_version" in fields
    assert all(difference["explanation_ko"] for difference in comparison.differences)


def test_a_comparable_competitor_produces_a_gap() -> None:
    diagnosis = make_diagnosis()
    competitor = replace(diagnosis.competitors[0], their_conditions=make_conditions())
    snapshot = freeze(replace(diagnosis, competitors=(competitor,)))

    gap = snapshot.metric("competitor.competitor-a.SEO_READINESS.gap")
    assert gap.value.status is ValueStatus.MEASURED
    assert gap.value.value == pytest.approx(SEO_OVERALL - COMPETITOR_SCORE)


def test_the_payload_is_content_hashed_and_tampering_is_detected() -> None:
    payload = to_payload(freeze(make_diagnosis()))
    assert payload["content_hash"]

    restored = from_payload(payload)
    assert restored.metric("SEO_READINESS.overall").value.value == SEO_OVERALL

    tampered = json.loads(json.dumps(payload))
    for row in tampered["snapshot"]["metrics"]:
        if row["metric_key"] == "SEO_READINESS.overall":
            row["value"]["value"] = 99.9

    with pytest.raises(ReportTamperedError):
        from_payload(tampered)


def test_the_content_hash_is_stable_across_two_freezes_of_the_same_input() -> None:
    diagnosis = make_diagnosis()
    assert to_payload(freeze(diagnosis))["content_hash"] == to_payload(freeze(diagnosis))[
        "content_hash"
    ]


def test_freezing_records_what_changed_since_the_previous_version() -> None:
    previous = freeze(make_diagnosis())

    diagnosis = make_diagnosis()
    lowered = replace(
        diagnosis.domains[0],
        score=diagnosis.domains[0].score.model_copy(update={"overall_score": 60.5}),
    )
    current = freeze(replace(diagnosis, domains=(lowered, diagnosis.domains[1])), previous=previous)

    change = next(c for c in current.changes if c.metric_key == "SEO_READINESS.overall")
    assert change.previous.value == SEO_OVERALL
    assert change.current.value == 60.5
    assert change.delta.value == pytest.approx(60.5 - SEO_OVERALL)
    assert change.direction == "DOWN"


def test_a_change_across_methodology_versions_is_reported_as_unmeasurable() -> None:
    previous = freeze(make_diagnosis())

    diagnosis = make_diagnosis()
    moved = replace(diagnosis.domains[0], conditions=make_conditions(spec_version="2.0.0"))
    current = freeze(replace(diagnosis, domains=(moved, diagnosis.domains[1])), previous=previous)

    change = next(c for c in current.changes if c.metric_key == "SEO_READINESS.overall")
    assert change.delta.status is ValueStatus.UNMEASURED
    assert change.delta.display() == UNMEASURED_KO
    assert "방법론" in (change.delta.reason_ko or "")


def test_the_standing_disclosure_says_a_readiness_score_is_not_a_rank_prediction() -> None:
    snapshot = freeze(make_diagnosis())
    joined = " ".join(snapshot.disclosures_ko)
    assert "순위 예측" in joined


def test_evidence_excerpts_can_be_redacted_without_losing_a_single_score() -> None:
    from veo.reports.snapshot import redact_evidence

    snapshot = freeze(make_diagnosis())
    assert EVIDENCE_SENTINEL in json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False)

    redacted = redact_evidence(snapshot)
    body = json.dumps(redacted.model_dump(mode="json"), ensure_ascii=False)
    assert EVIDENCE_SENTINEL not in body

    assert [row.value.display() for row in redacted.metrics] == [
        row.value.display() for row in snapshot.metrics
    ]
    assert redacted.evidence[0].evidence_id == snapshot.evidence[0].evidence_id
    assert redacted.evidence[0].content_hash == snapshot.evidence[0].content_hash
    assert redacted.evidence[0].excerpt_redacted is True
