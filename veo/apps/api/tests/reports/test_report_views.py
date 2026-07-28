"""Three audiences, one snapshot.

The point of these tests is a single claim: an executive, a marketer and a developer
reading "the report" are reading the same document. If the number on the board slide and
the number in the ticket can differ, everything downstream of them is an argument.
"""

from __future__ import annotations

import pytest
from report_support import (
    EVIDENCE_SENTINEL,
    GEO_OVERALL,
    SEO_OVERALL,
    make_diagnosis,
)

from veo.reports.snapshot import UNMEASURED_KO, ValueStatus, freeze, redact_evidence
from veo.reports.views import build_views

SHARED_KEYS = (
    "SEO_READINESS.overall",
    "SEO_READINESS.coverage",
    "SEO_READINESS.confidence",
    "GEO_READINESS.overall",
)


@pytest.fixture
def views() -> object:
    return build_views(freeze(make_diagnosis()))


def test_the_same_number_appears_identically_in_all_three_views(views) -> None:  # type: ignore[no-untyped-def]
    for key in SHARED_KEYS:
        rendered = {
            views.executive.number(key).display(),
            views.marketing.number(key).display(),
            views.developer.number(key).display(),
        }
        assert len(rendered) == 1, f"{key} rendered differently per audience: {rendered}"

    assert views.executive.number("SEO_READINESS.overall").value == SEO_OVERALL
    assert views.developer.number("GEO_READINESS.overall").value == GEO_OVERALL


def test_no_view_invents_a_metric_the_snapshot_does_not_hold(views) -> None:  # type: ignore[no-untyped-def]
    snapshot_keys = {row.metric_key for row in views.snapshot.metrics}
    for view in (views.executive, views.marketing, views.developer):
        assert {row.metric_key for row in view.metrics} <= snapshot_keys


def test_every_metric_a_view_shows_is_the_identical_row_from_the_snapshot(views) -> None:  # type: ignore[no-untyped-def]
    by_key = {row.metric_key: row for row in views.snapshot.metrics}
    for view in (views.executive, views.marketing, views.developer):
        for row in view.metrics:
            assert row == by_key[row.metric_key]


def test_the_executive_view_leads_with_status_gap_actions_and_change(views) -> None:  # type: ignore[no-untyped-def]
    executive = views.executive
    assert executive.status_ko
    assert executive.headline
    assert executive.competitive_gap
    assert 0 < len(executive.top_actions) <= 5
    assert executive.top_actions[0].title_ko
    assert executive.top_actions[0].owner_ko
    assert executive.changes_ko


def test_the_marketing_view_carries_categories_keywords_and_competitors(views) -> None:  # type: ignore[no-untyped-def]
    marketing = views.marketing
    assert {table.domain for table in marketing.category_tables} == {
        "SEO_READINESS",
        "GEO_READINESS",
    }
    assert marketing.keyword_rows
    assert marketing.competitor_rows
    unmeasured = [row for row in marketing.keyword_rows if row.monthly_searches.value is None]
    assert unmeasured, "the fixture holds a suppressed keyword"
    assert unmeasured[0].monthly_searches.display() == UNMEASURED_KO
    assert unmeasured[0].monthly_searches.reason_ko


def test_the_developer_view_carries_urls_evidence_fixes_and_reverification(views) -> None:  # type: ignore[no-untyped-def]
    developer = views.developer
    assert developer.work_items
    first = developer.work_items[0]
    assert first.affected_urls
    assert first.evidence_ids
    assert first.fix_example
    assert first.reverification_ko
    assert developer.unmeasured_checks
    assert developer.unmeasured_checks[0].reason_ko


def test_a_view_never_shows_an_unmeasured_category_as_zero(views) -> None:  # type: ignore[no-untyped-def]
    marketing = views.marketing
    table = next(t for t in marketing.category_tables if t.domain == "SEO_READINESS")
    indexing = next(row for row in table.rows if row.category_id == "indexing")

    assert indexing.value.status is ValueStatus.UNMEASURED
    assert indexing.value.display() == UNMEASURED_KO
    assert indexing.value.reason_ko


def test_every_view_carries_the_same_disclosure_block(views) -> None:  # type: ignore[no-untyped-def]
    blocks = [
        views.executive.disclosure,
        views.marketing.disclosure,
        views.developer.disclosure,
    ]
    assert len({block.methodology_ko for block in blocks}) == 1
    for block in blocks:
        assert block.scope_ko
        assert block.measured_at_ko
        assert block.confidence_ko
        assert "순위 예측" in block.rank_prediction_notice_ko


def test_without_evidence_permission_the_views_still_carry_full_scores() -> None:
    snapshot = freeze(make_diagnosis())
    gated = build_views(redact_evidence(snapshot))
    full = build_views(snapshot)

    for key in SHARED_KEYS:
        assert gated.executive.number(key).display() == full.executive.number(key).display()

    excerpts = [
        record.excerpt for record in gated.developer.evidence if record.excerpt is not None
    ]
    assert EVIDENCE_SENTINEL not in " ".join(excerpts)
    assert gated.developer.evidence[0].evidence_id
