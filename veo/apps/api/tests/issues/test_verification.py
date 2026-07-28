"""Targeted re-measurement: what gets re-scanned, and what the result is allowed to say.

Two independent guarantees live here.

*Scope.* Verifying one issue re-scans the affected URLs and the one check that produced
it. Re-crawling a whole site to answer "is this one title tag fixed?" burns the customer's
crawl budget and takes hours, so the request object refuses to carry anything wider.

*Authority.* The verdict is derived from persisted check outcomes, never supplied by the
caller. There is no argument a client can pass that means "call it resolved".
"""

from __future__ import annotations

import uuid

import pytest

from veo.db.models.analysis import Issue
from veo.issues.lifecycle import VerificationOutcome
from veo.issues.verification import (
    MeasuredCheck,
    VerificationScopeError,
    build_verification_request,
    derive_outcome,
)
from veo.scoring import CheckStatus


def issue_row(check_id: str, urls: list[str], *, state: str = "VERIFYING") -> Issue:
    return Issue(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        check_id=check_id,
        severity="CRITICAL",
        state=state,
        title_ko="정규 URL이 선언되어 있지 않습니다",
        business_impact_ko="중복 색인 위험",
        affected_url_count=len(urls),
        sample_urls=list(urls),
        evidence_ids=["http_response:abc"],
        remediation_owner="DEVELOPER",
        regression_count=0,
    )


# --------------------------------------------------------------------------- #
# Scope of the re-scan request
# --------------------------------------------------------------------------- #


def test_a_verification_asks_for_the_affected_urls_and_nothing_else() -> None:
    urls = ["https://e.com/a", "https://e.com/b"]
    request = build_verification_request(issue_row("seo.canonical.not_cross_domain", urls))
    assert set(request.target_urls) == set(urls)


def test_a_verification_asks_for_exactly_one_check() -> None:
    request = build_verification_request(
        issue_row("seo.canonical.not_cross_domain", ["https://e.com/a"])
    )
    assert request.check_id == "seo.canonical.not_cross_domain"
    parameters = request.as_scan_parameters()
    assert parameters["check_ids"] == ["seo.canonical.not_cross_domain"]
    assert parameters["scope"] == "TARGETED_REVERIFICATION"


def test_a_verification_never_requests_a_whole_site_crawl() -> None:
    request = build_verification_request(
        issue_row("seo.canonical.not_cross_domain", ["https://e.com/a"])
    )
    parameters = request.as_scan_parameters()
    assert parameters["urls"] == ["https://e.com/a"]
    assert parameters.get("crawl_whole_site") is not True
    assert "site_id" not in parameters


def test_the_requested_urls_are_canonicalised_like_the_fingerprint() -> None:
    request = build_verification_request(
        issue_row("seo.http.status_ok", ["HTTPS://E.com:443/a", "https://e.com/a"])
    )
    assert request.target_urls == ("https://e.com/a",)


def test_a_url_scope_issue_with_no_affected_urls_cannot_be_verified() -> None:
    with pytest.raises(VerificationScopeError) as caught:
        build_verification_request(issue_row("seo.http.status_ok", []))
    assert not caught.value.message_ko.isascii()


def test_the_request_carries_a_korean_note_for_whoever_runs_it() -> None:
    request = build_verification_request(issue_row("seo.http.status_ok", ["https://e.com/a"]))
    assert request.note_ko
    assert not request.note_ko.isascii()


# --------------------------------------------------------------------------- #
# Deriving the verdict from what was measured
# --------------------------------------------------------------------------- #


def measured(check_id: str, status: CheckStatus, url: str | None) -> MeasuredCheck:
    return MeasuredCheck(check_id=check_id, status=status, url=url, check_result_id=uuid.uuid4())


def test_every_affected_url_passing_resolves_the_issue() -> None:
    verdict = derive_outcome(
        [
            measured("c", CheckStatus.PASS, "https://e.com/a"),
            measured("c", CheckStatus.PASS, "https://e.com/b"),
        ],
        affected_urls=("https://e.com/a", "https://e.com/b"),
    )
    assert verdict.outcome is VerificationOutcome.RESOLVED


def test_one_failing_url_keeps_the_issue_unresolved() -> None:
    verdict = derive_outcome(
        [
            measured("c", CheckStatus.PASS, "https://e.com/a"),
            measured("c", CheckStatus.FAIL, "https://e.com/b"),
        ],
        affected_urls=("https://e.com/a", "https://e.com/b"),
    )
    assert verdict.outcome is VerificationOutcome.STILL_FAILING


def test_a_warning_is_not_a_pass() -> None:
    verdict = derive_outcome(
        [measured("c", CheckStatus.WARNING, "https://e.com/a")],
        affected_urls=("https://e.com/a",),
    )
    assert verdict.outcome is VerificationOutcome.STILL_FAILING


def test_a_re_scan_that_measured_nothing_is_inconclusive_not_resolved() -> None:
    verdict = derive_outcome([], affected_urls=("https://e.com/a",))
    assert verdict.outcome is VerificationOutcome.INCONCLUSIVE
    assert not verdict.reason_ko.isascii()


def test_an_unknown_outcome_is_inconclusive() -> None:
    verdict = derive_outcome(
        [measured("c", CheckStatus.UNKNOWN, "https://e.com/a")],
        affected_urls=("https://e.com/a",),
    )
    assert verdict.outcome is VerificationOutcome.INCONCLUSIVE


def test_a_check_that_became_not_applicable_is_inconclusive() -> None:
    """Deleting the page is not fixing the page."""
    verdict = derive_outcome(
        [measured("c", CheckStatus.NOT_APPLICABLE, "https://e.com/a")],
        affected_urls=("https://e.com/a",),
    )
    assert verdict.outcome is VerificationOutcome.INCONCLUSIVE


def test_passing_only_some_of_the_affected_urls_is_inconclusive() -> None:
    verdict = derive_outcome(
        [measured("c", CheckStatus.PASS, "https://e.com/a")],
        affected_urls=("https://e.com/a", "https://e.com/b"),
    )
    assert verdict.outcome is VerificationOutcome.INCONCLUSIVE
    assert "https://e.com/b" in verdict.detail["unmeasured_urls"]


def test_a_site_scope_measurement_without_urls_can_still_resolve() -> None:
    verdict = derive_outcome(
        [measured("c", CheckStatus.PASS, None)], affected_urls=()
    )
    assert verdict.outcome is VerificationOutcome.RESOLVED


def test_the_verdict_records_which_check_results_it_read() -> None:
    rows = [measured("c", CheckStatus.PASS, "https://e.com/a")]
    verdict = derive_outcome(rows, affected_urls=("https://e.com/a",))
    assert verdict.detail["check_result_ids"] == [str(rows[0].check_result_id)]


def test_every_verdict_explains_itself_in_korean() -> None:
    for status in CheckStatus:
        verdict = derive_outcome(
            [measured("c", status, "https://e.com/a")], affected_urls=("https://e.com/a",)
        )
        assert verdict.reason_ko
        assert not verdict.reason_ko.isascii()
