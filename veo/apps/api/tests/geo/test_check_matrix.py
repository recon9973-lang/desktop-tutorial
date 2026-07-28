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


@pytest.mark.parametrize("check_id", sorted(CONDITIONAL_CHECKS))
def test_conditional_checks_can_leave_the_denominator(
    check_id: str, corpus: dict[str, dict[str, CheckStatus]]
) -> None:
    assert CheckStatus.NOT_APPLICABLE in corpus[check_id].values(), (
        f"{check_id} declares an applicability rule that no fixture exercises"
    )


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
