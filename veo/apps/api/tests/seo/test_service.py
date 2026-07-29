"""The assembled scan: collectors in, a specification-derived score out.

The three properties this file exists to prove:

* **N/A left the denominator.** A brochure site scores *higher* than the same site with
  the inapplicable checks marked failed — because the inapplicable ones were never in
  the denominator to begin with.
* **UNKNOWN cost coverage, not points.** Turning every provider off lowers coverage and
  leaves the score alone.
* **Every finding is auditable.** Each issue points at evidence that exists in the same
  result and names an owner the specification chose.
"""

from __future__ import annotations

import dataclasses

import pytest
from tests.seo.support import (
    ALL_PROVIDERS_ENABLED,
    SPEC,
    build_context,
    healthy_provider_payloads,
)

from veo.collect.contract import run_collectors
from veo.scoring import CheckStatus
from veo.scoring.spec import load_spec
from veo.seo import run_seo_scan
from veo.seo.service import score_collection, seo_collectors

FIXTURES = (
    "healthy",
    "sitewide_noindex",
    "cross_domain_canonical",
    "redirect_loop",
    "broken_jsonld",
    "duplicate_metadata",
    "orphan_page",
    "conflicting_hreflang",
    "render_gap",
    "brochure_na",
)


def scan(fixture: str, *, providers: bool = False, **overrides: object):
    context = build_context(fixture, **overrides)  # type: ignore[arg-type]
    if providers:
        context = dataclasses.replace(
            context,
            provider_states=dict(ALL_PROVIDERS_ENABLED),
            provider_payloads=healthy_provider_payloads(tuple(context.documents)),
        )
    return run_seo_scan(context)


# --------------------------------------------------------------------------- #
# The whole spec is answered, always
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("fixture", FIXTURES)
def test_a_scan_answers_every_check_in_the_specification(fixture: str) -> None:
    result = scan(fixture)
    assert {o.check_id for o in result.score.outcomes} == set(SPEC.check_ids)
    assert result.score.spec_checksum == SPEC.checksum


@pytest.mark.parametrize("fixture", FIXTURES)
def test_a_scan_never_claims_to_predict_rank(fixture: str) -> None:
    assert SPEC.score_meaning.is_rank_prediction is False
    assert scan(fixture).summary_ko


# --------------------------------------------------------------------------- #
# A clean site scores clean
# --------------------------------------------------------------------------- #


def test_a_healthy_site_with_every_provider_connected_scores_one_hundred() -> None:
    result = scan("healthy", providers=True)
    failing = [
        o.check_id
        for o in result.score.outcomes
        if o.status in {CheckStatus.FAIL, CheckStatus.WARNING}
    ]
    assert failing == []
    assert result.score.overall_score == 100.0
    assert result.issues == ()


def test_a_healthy_site_raises_no_cap() -> None:
    assert scan("healthy", providers=True).score.applied_caps == []


# --------------------------------------------------------------------------- #
# UNKNOWN lowers coverage, never the score
# --------------------------------------------------------------------------- #


# 아래 세 검사는 **1.1.0 의 상대 평가 규칙**을 고정한다. 1.2.0 부터는 재지 못한 항목이
# 배점을 유지한 채 0점이 되므로(`tests/scoring/test_absolute_scoring.py`) 결과가 다르다.
# 그래도 지우지 않는다 — 1.1.0 으로 매긴 과거 점수는 앞으로도 그 규칙으로 설명되어야
# 하고(기획서 §10), 그 보장을 지키는 것이 이 세 검사다.
RELATIVE = "1.1.0"


def _relative(fixture: str, *, providers: bool = False):
    """1.1.0 의 규칙으로 채점한다 — 그 판에 있던 항목만 가지고.

    수집기는 명세와 따로 자란다. 오늘의 수집기는 1.1.0 이 알지 못하는 항목까지 판정하고,
    평가기는 명세에 없는 항목이 들어오면 오타로 보고 거부한다 — 그 거부는 옳다. 그래서
    옛 규칙을 확인할 때는 옛 명세가 선언한 항목만 넘긴다. 지켜야 하는 보장은 "그때
    매긴 점수가 그때 규칙으로 설명된다" 이지 "수집기가 영원히 그대로다" 가 아니다.
    """
    spec = load_spec("veo.seo.readiness", RELATIVE)
    context = build_context(fixture)
    if providers:
        context = dataclasses.replace(
            context,
            provider_states=dict(ALL_PROVIDERS_ENABLED),
            provider_payloads=healthy_provider_payloads(tuple(context.documents)),
        )
    collected = run_collectors(list(seo_collectors(context)), context)
    declared = set(spec.check_ids)
    collected = dataclasses.replace(
        collected,
        outcomes=tuple(o for o in collected.outcomes if o.check_id in declared),
    )
    return score_collection(dataclasses.replace(context, spec=spec), collected).score


def test_relative_scoring_lowers_coverage_but_not_the_score() -> None:
    connected = _relative("healthy", providers=True)
    disconnected = _relative("healthy")

    assert disconnected.overall_score == connected.overall_score
    assert disconnected.coverage < connected.coverage
    assert disconnected.confidence < connected.confidence


def test_relative_scoring_names_the_categories_that_went_unknown() -> None:
    integration = _relative("healthy").category("search_engine_integration")
    assert integration.status == "UNKNOWN"
    assert integration.score is None
    assert len(integration.unknown_check_ids) == 4


def test_relative_scoring_drops_an_unknown_category_from_the_weight_total() -> None:
    connected = _relative("healthy", providers=True)
    disconnected = _relative("healthy")
    assert disconnected.effective_weight_total < connected.effective_weight_total


# --------------------------------------------------------------------------- #
# N/A is not zero
# --------------------------------------------------------------------------- #


def test_the_brochure_site_marks_the_inapplicable_checks_not_applicable() -> None:
    result = scan("brochure_na")
    not_applicable = {
        o.check_id for o in result.score.outcomes if o.status is CheckStatus.NOT_APPLICABLE
    }
    assert {
        "seo.sd.jsonld_parses",
        "seo.sd.required_properties_present",
        "seo.sd.matches_visible_content",
        "seo.sd.google_supported_type",
        "seo.onpage.image_alt_coverage",
        "seo.content.pagination_signals",
        "seo.content.breadcrumb_present",
    } <= not_applicable


def test_a_not_applicable_check_scores_better_than_the_same_check_failed() -> None:
    """The proof that N/A left the denominator rather than scoring zero."""
    from veo.scoring import evaluate

    as_collected = scan("brochure_na").score
    rewritten = [
        outcome.model_copy(update={"status": CheckStatus.FAIL})
        if outcome.status is CheckStatus.NOT_APPLICABLE
        else outcome
        for outcome in as_collected.outcomes
    ]
    if_they_failed = evaluate(SPEC, rewritten)

    assert as_collected.overall_score is not None
    assert if_they_failed.overall_score is not None
    assert as_collected.overall_score > if_they_failed.overall_score


def test_a_site_without_structured_data_scores_zero_rather_than_being_excused() -> None:
    """만들지 않은 것은 해당 없음이 아니다.

    해당 없음으로 두면 12.5점이 분모에서 빠져, 스키마를 만든 사이트가 분모 100 에서
    채점받는 동안 안 만든 사이트는 87.5 에서 채점받게 된다 — 안 만들수록 유리해진다.
    선언이 없다는 사실은 `seo.sd.declared` 가 실패로 잡고, 그 영역은 0점이 되되
    배점은 분모에 남는다.
    """
    category = scan("brochure_na").score.category("structured_data")
    assert category.status == "SCORED"
    assert category.score == 0.0
    assert category.penalty_total > 0.0


# --------------------------------------------------------------------------- #
# Caps come from the specification, not from the collectors
# --------------------------------------------------------------------------- #


def test_a_site_wide_index_block_triggers_the_specification_cap() -> None:
    result = scan("sitewide_noindex")
    cap_ids = {cap.cap_id for cap in result.score.applied_caps}
    assert "sitewide_index_block" in cap_ids
    assert result.score.overall_score is not None
    assert result.score.overall_score <= 25.0


def test_mass_cross_domain_canonicals_trigger_their_cap() -> None:
    result = scan("cross_domain_canonical")
    assert "mass_cross_domain_canonical" in {c.cap_id for c in result.score.applied_caps}


# --------------------------------------------------------------------------- #
# Issues
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("fixture", FIXTURES)
def test_every_issue_points_at_evidence_that_exists_in_the_same_result(fixture: str) -> None:
    result = scan(fixture)
    known = {record.evidence_id for record in result.evidence}
    for issue in result.issues:
        assert issue.evidence_ids, issue.check_id
        assert set(issue.evidence_ids) <= known, issue.check_id


@pytest.mark.parametrize("fixture", FIXTURES)
def test_every_issue_takes_its_owner_from_the_specification(fixture: str) -> None:
    for issue in scan(fixture).issues:
        assert issue.remediation_owner == SPEC.check(issue.check_id).remediation_owner


@pytest.mark.parametrize("fixture", FIXTURES)
def test_every_issue_is_written_in_korean_and_says_how_to_reverify(fixture: str) -> None:
    for issue in scan(fixture).issues:
        assert issue.title_ko.strip()
        assert issue.summary_ko.strip()
        assert issue.remediation_ko.strip()
        assert issue.reverification_note_ko.strip()
        assert issue.affected_urls


@pytest.mark.parametrize("fixture", FIXTURES)
def test_an_issue_is_raised_only_for_a_non_passing_check(fixture: str) -> None:
    result = scan(fixture)
    non_passing = {
        o.check_id
        for o in result.score.outcomes
        if o.status in {CheckStatus.FAIL, CheckStatus.WARNING}
    }
    assert {issue.check_id for issue in result.issues} <= non_passing


@pytest.mark.parametrize("fixture", FIXTURES)
def test_evidence_ids_are_unique_within_a_result(fixture: str) -> None:
    ids = [record.evidence_id for record in scan(fixture).evidence]
    assert len(ids) == len(set(ids))


# --------------------------------------------------------------------------- #
# A fetch failure is not an SEO failure
# --------------------------------------------------------------------------- #


def test_a_crawl_that_collected_nothing_is_unknown_rather_than_broken() -> None:
    context = dataclasses.replace(
        build_context("healthy"),
        documents={},
        primary_document=None,
        robots_txt=None,
        sitemap_documents={},
        rendered_dom={},
        url_importance={},
    )
    result = run_seo_scan(context)

    assert result.score.status == "UNKNOWN"
    assert result.score.overall_score is None
    assert all(o.status is not CheckStatus.FAIL for o in result.score.outcomes)
    assert result.issues == ()
    assert result.summary_ko


# --------------------------------------------------------------------------- #
# Every check id, at least one PASS and at least one non-PASS
# --------------------------------------------------------------------------- #


def _observed_statuses() -> dict[str, set[CheckStatus]]:
    seen: dict[str, set[CheckStatus]] = {check_id: set() for check_id in SPEC.check_ids}
    contexts = []
    for fixture in FIXTURES:
        contexts.append(build_context(fixture))
        base = build_context(fixture)
        contexts.append(
            dataclasses.replace(
                base,
                provider_states=dict(ALL_PROVIDERS_ENABLED),
                provider_payloads=healthy_provider_payloads(tuple(base.documents)),
            )
        )
        contexts.append(build_context(fixture, with_rendered=False))

    # The same healthy site served over plain HTTP. No fixture is stored for it because
    # the only difference is the scheme, and duplicating four pages to change one letter
    # would make the fixture set harder to read, not easier.
    over_http = build_context("healthy")
    contexts.append(
        dataclasses.replace(
            over_http,
            target_url="http://healthy.example.kr/",
            documents={
                url.replace("https://", "http://"): dataclasses.replace(
                    document, final_url=document.final_url.replace("https://", "http://")
                )
                for url, document in over_http.documents.items()
            },
            primary_document=None,
            rendered_dom={},
            url_importance={
                url.replace("https://", "http://"): value
                for url, value in over_http.url_importance.items()
            },
        )
    )

    broken_providers = build_context("healthy")
    contexts.append(
        dataclasses.replace(
            broken_providers,
            provider_states=dict(ALL_PROVIDERS_ENABLED),
            provider_payloads={
                "GOOGLE_PAGESPEED": {
                    url: {
                        "lighthouse": {
                            "largest-contentful-paint": {"score": 0.1, "display_value": "7초"},
                            "cumulative-layout-shift": {"score": 0.2, "display_value": "0.44"},
                            "total-blocking-time": {"score": 0.1, "display_value": "900밀리초"},
                        }
                    }
                    for url in broken_providers.documents
                },
                "GOOGLE_CRUX": {
                    url: {"metrics": {"INTERACTION_TO_NEXT_PAINT": {"category": "SLOW"}}}
                    for url in broken_providers.documents
                },
                "GOOGLE_SEARCH_CONSOLE": {
                    "site": {"verified": False},
                    "sitemaps": [],
                    "performance": {"rows": 0, "impressions": 0, "date_range_end": "2024-01-01"},
                    "index_coverage": {"indexed": 3, "previous_indexed": 300},
                },
                "NAVER_SEARCH_ADVISOR": {"site_registered": False},
                "INDEXNOW": {"configured": False},
                "BACKLINK_INDEX": {
                    "referring_domains": 0,
                    "spam_flagged_domains": 40,
                    "sampled_domains": 40,
                },
                "BRAND_MENTIONS": {
                    "canonical_name": "온담의원",
                    "observed_names": ["온담의원", "ONDAM", "온담 클리닉"],
                    "sources_checked": 3,
                },
            },
        )
    )

    for context in contexts:
        for outcome in run_seo_scan(context).score.outcomes:
            seen[outcome.check_id].add(outcome.status)
    return seen


OBSERVED = _observed_statuses()


@pytest.mark.parametrize("check_id", sorted(SPEC.check_ids))
def test_every_check_can_pass(check_id: str) -> None:
    assert CheckStatus.PASS in OBSERVED[check_id], f"{check_id} never passed on any fixture"


@pytest.mark.parametrize("check_id", sorted(SPEC.check_ids))
def test_every_check_can_report_something_other_than_a_pass(check_id: str) -> None:
    others = OBSERVED[check_id] - {CheckStatus.PASS}
    assert others, f"{check_id} only ever passes — the failure path is untested"
