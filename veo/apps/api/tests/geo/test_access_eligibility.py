"""Access and search eligibility, fixture by fixture."""

from __future__ import annotations

from tests.geo.support import load_case, replace_robots

from veo.collect.contract import CollectionContext
from veo.geo.collectors.access_eligibility import AccessEligibilityCollector
from veo.scoring import CheckStatus


def run(name: str) -> dict[str, CheckStatus]:
    context: CollectionContext = load_case(name).context
    result = AccessEligibilityCollector().collect(context)
    return {o.check_id: o.status for o in result.outcomes}


def test_a_healthy_page_passes_every_access_check() -> None:
    statuses = run("hospital_local")
    assert statuses["geo.access.http_status_ok"] is CheckStatus.PASS
    assert statuses["geo.access.no_auth_required"] is CheckStatus.PASS
    assert statuses["geo.access.indexable"] is CheckStatus.PASS
    assert statuses["geo.access.search_bots_allowed"] is CheckStatus.PASS
    assert statuses["geo.access.not_blocked_by_edge"] is CheckStatus.PASS
    assert statuses["geo.access.content_visible_without_js"] is CheckStatus.PASS


def test_a_server_error_fails_the_status_check() -> None:
    assert run("http_error")["geo.access.http_status_ok"] is CheckStatus.FAIL


def test_authentication_fails_the_reachability_check() -> None:
    assert run("auth_required")["geo.access.no_auth_required"] is CheckStatus.FAIL


def test_noindex_fails_indexability() -> None:
    assert run("noindex_page")["geo.access.indexable"] is CheckStatus.FAIL


def test_an_intentional_noindex_url_is_not_applicable() -> None:
    case = load_case("noindex_page")
    context = case.context
    from dataclasses import replace

    context = replace(
        context,
        url_importance={context.target_url: "INTENTIONAL_NOINDEX"},
    )
    result = AccessEligibilityCollector().collect(context)
    statuses = {o.check_id: o.status for o in result.outcomes}
    assert statuses["geo.access.indexable"] is CheckStatus.NOT_APPLICABLE


def test_an_edge_challenge_fails_the_edge_check() -> None:
    assert run("edge_challenge")["geo.access.not_blocked_by_edge"] is CheckStatus.FAIL


def test_a_javascript_shell_fails_the_no_javascript_check() -> None:
    assert run("js_shell")["geo.access.content_visible_without_js"] is CheckStatus.FAIL


def test_disallowing_search_crawlers_fails_only_that_check() -> None:
    statuses = run("search_crawler_blocked")
    assert statuses["geo.access.search_bots_allowed"] is CheckStatus.FAIL
    assert statuses["geo.access.http_status_ok"] is CheckStatus.PASS
    assert statuses["geo.access.indexable"] is CheckStatus.PASS


def test_disallowing_training_crawlers_fails_nothing() -> None:
    statuses = run("training_bot_blocked")
    assert statuses["geo.access.search_bots_allowed"] is CheckStatus.PASS
    assert statuses["geo.access.training_bot_policy_declared"] is CheckStatus.PASS
    assert CheckStatus.FAIL not in statuses.values()


def test_an_unreadable_robots_file_is_unknown_not_a_failure() -> None:
    case = replace_robots(load_case("hospital_local"), None)
    result = AccessEligibilityCollector().collect(case.context)
    statuses = {o.check_id: o.status for o in result.outcomes}
    assert statuses["geo.access.search_bots_allowed"] is CheckStatus.UNKNOWN
    assert statuses["geo.access.training_bot_policy_declared"] is CheckStatus.UNKNOWN


def test_an_absent_robots_file_allows_every_crawler() -> None:
    case = replace_robots(load_case("hospital_local"), "")
    result = AccessEligibilityCollector().collect(case.context)
    statuses = {o.check_id: o.status for o in result.outcomes}
    assert statuses["geo.access.search_bots_allowed"] is CheckStatus.PASS


def test_access_evidence_records_the_robots_file_that_was_judged() -> None:
    result = AccessEligibilityCollector().collect(load_case("hospital_local").context)
    kinds = {record.kind for record in result.evidence}
    assert "robots_txt" in kinds
    assert "http_response" in kinds
