"""Every check must be able to pass and to fail.

A check that only ever returns one status is not a check — it is a decoration. This
module runs the whole fixture corpus once and asserts, per check id, that the corpus
contains at least one PASS and at least one genuine non-PASS.

It also pins the applicability rules: the checks the specification marks conditional must
actually reach NOT_APPLICABLE somewhere, or the "N/A is not zero" promise is theatre.
"""

from __future__ import annotations

import pytest
from tests.geo.support import GeoCase, case_names, load_case

from veo.geo.service import run_geo_readiness
from veo.scoring import CheckStatus, ScoringSpec

NON_PASS = {CheckStatus.FAIL, CheckStatus.WARNING}

#: Checks whose specification declares an applicability rule. Each must be able to
#: fall out of the denominator entirely.
CONDITIONAL_CHECKS = {
    "geo.access.indexable",
    "geo.extract.tables_lists_machine_readable",
    "geo.evidence.author_identified",
    "geo.evidence.method_disclosed",
    "geo.evidence.primary_source_linked",
    "geo.entity.stable_id_graph",
    "geo.entity.nap_consistent",
    "geo.sd.valid_syntax",
    "geo.sd.matches_visible_content",
    "geo.sd.page_type_appropriate",
    "geo.fresh.dates_present",
    "geo.fresh.dates_truthful",
    "geo.fresh.sitemap_lastmod_reliable",
}

#: 이 검사들의 **해당 없음** 조건은 페이지가 아니라 **크롤 전체**의 성질에 달려 있다 —
#: 다 돌았는가, 그리고 sitemap 이 스스로 한 장짜리임을 선언하는가.
#:
#: 아래 픽스처 말뭉치는 페이지 단위 HTML 이라 그 조건을 모델링하지 못한다. 억지로
#: 맞추려고 수집기가 "sitemap 을 못 가져왔다" 를 해당 없음으로 접으면, 그 순간
#: **덜 재는 편이 유리해진다** — 실제로 그렇게 되어 있었다.
#:
#: 그 경로는 `tests/collect/test_sample.py` 가 경우의 수 표로 고정한다.
CONDITIONAL_ON_CRAWL_SCOPE = {
    "geo.fresh.sitemap_lastmod_reliable",
}


@pytest.fixture(scope="module")
def corpus() -> dict[str, dict[str, CheckStatus]]:
    """``{check_id: {case_name: status}}`` for the whole fixture corpus."""
    table: dict[str, dict[str, CheckStatus]] = {}
    for name in case_names():
        case: GeoCase = load_case(name)
        report = run_geo_readiness(case.context)
        for outcome in report.score.outcomes:
            table.setdefault(outcome.check_id, {})[name] = outcome.status
    return table


def test_the_corpus_covers_every_check(
    corpus: dict[str, dict[str, CheckStatus]], spec: ScoringSpec
) -> None:
    assert set(corpus) == set(spec.check_ids)


def test_every_check_passes_somewhere(
    corpus: dict[str, dict[str, CheckStatus]], spec: ScoringSpec
) -> None:
    never = {
        check_id
        for check_id in spec.check_ids
        if CheckStatus.PASS not in corpus[check_id].values()
    }
    assert not never, f"no fixture makes these pass: {sorted(never)}"


def test_every_check_fails_or_warns_somewhere(
    corpus: dict[str, dict[str, CheckStatus]], spec: ScoringSpec
) -> None:
    never = {
        check_id
        for check_id in spec.check_ids
        if not NON_PASS & set(corpus[check_id].values())
    }
    assert not never, f"no fixture makes these fail or warn: {sorted(never)}"


@pytest.mark.parametrize(
    "check_id", sorted(CONDITIONAL_CHECKS - CONDITIONAL_ON_CRAWL_SCOPE)
)
def test_conditional_checks_can_leave_the_denominator(
    check_id: str, corpus: dict[str, dict[str, CheckStatus]]
) -> None:
    assert CheckStatus.NOT_APPLICABLE in corpus[check_id].values(), (
        f"{check_id} declares an applicability rule that no fixture exercises"
    )


def test_the_crawl_scope_exception_stays_small() -> None:
    """예외 목록이 조용히 자라면 이 검사 자체가 무의미해진다.

    여기 이름을 하나 더 넣기 전에, 정말 크롤 전체의 성질인지 아니면 그냥 픽스처를
    만들기 귀찮은 것인지 먼저 답해야 한다.
    """
    assert CONDITIONAL_ON_CRAWL_SCOPE <= CONDITIONAL_CHECKS
    assert len(CONDITIONAL_ON_CRAWL_SCOPE) <= 2


def test_the_specification_and_this_module_agree_on_which_checks_are_conditional(
    spec: ScoringSpec,
) -> None:
    declared = {
        check.id
        for category in spec.categories
        for check in category.checks
        if check.applicability_ko
    }
    assert declared == CONDITIONAL_CHECKS


def test_a_status_is_never_silently_missing(
    corpus: dict[str, dict[str, CheckStatus]],
) -> None:
    for check_id, per_case in corpus.items():
        assert set(per_case) == set(case_names()), check_id
