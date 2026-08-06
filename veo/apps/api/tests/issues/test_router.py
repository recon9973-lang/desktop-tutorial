"""The HTTP surface: who may look, who may move an issue, and what a 404 must not reveal.

The router is deliberately not mounted in ``veo.api.app`` (see ``INTEGRATION_REQUEST.md``);
the ``app`` fixture includes it under the real API prefix so these tests exercise the
same paths the integrator will publish.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.issues.support import (
    BLOCKER_CHECK,
    CRITICAL_CHECK,
    ISSUES,
    Tenant,
    error_code,
    error_message,
    items,
    payload,
    requires_database,
)

from veo.collect.contract import IssueDraft
from veo.db.models.analysis import Evidence, ScanRun
from veo.issues import service
from veo.issues.lifecycle import IssueState
from veo.scoring import CheckStatus, ScoringSpec

pytestmark = [pytest.mark.requires_postgres, requires_database]

PAGE_A = "https://shop.example.com/a"


def draft(check_id: str, *urls: str) -> IssueDraft:
    return IssueDraft(
        check_id=check_id,
        title_ko="정규 URL 선언 누락",
        summary_ko="해당 페이지에 rel=canonical이 없습니다.",
        affected_urls=urls,
        evidence_ids=("http_response:deadbeef",),
        remediation_ko="canonical 링크를 추가하세요.",
        remediation_owner="DEVELOPER",
        business_impact_ko="중복 색인 위험이 있습니다.",
        reverification_note_ko="해당 URL만 다시 수집합니다.",
    )


@pytest.fixture
def seeded(
    db: Session, org_a: Tenant, make_scan_run: Callable[..., ScanRun], seo_spec: ScoringSpec
) -> uuid.UUID:
    run = make_scan_run(org_a)
    # 지적이 부르는 근거를 실제로 남긴다. 이걸 빼면 "근거를 열 수 있는가" 를 검사하는
    # 테스트가 항상 통과하는데, 근거가 없어서 통과하는 것이라 아무것도 지키지 못한다.
    db.add(
        Evidence(
            organization_id=org_a.organization_id,
            scan_run_id=run.id,
            evidence_id="http_response:deadbeef",
            kind="http_response",
            url=PAGE_A,
            collected_at=datetime.now(UTC),
            content_hash="d" * 64,
            excerpt="<html>…</html>",
            source="COLLECTED",
            detail={},
        )
    )
    db.flush()
    [result] = service.ingest_drafts(
        db,
        org_a.analyst,
        project_id=org_a.project_id,
        scan_run_id=run.id,
        drafts=[draft(CRITICAL_CHECK, PAGE_A)],
        spec=seo_spec,
        request_id="seed",
    )
    db.commit()
    return result.issue.id


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #


def test_listing_returns_the_callers_own_issues_with_a_korean_summary(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, seeded: uuid.UUID
) -> None:
    act_as(org_a.analyst)
    response = client.get(ISSUES)
    assert response.status_code == 200
    rows = items(response)
    assert [row["id"] for row in rows] == [str(seeded)]
    assert rows[0]["state"] == IssueState.OPEN
    assert rows[0]["severity"] == "CRITICAL"
    assert not rows[0]["summary_ko"].isascii()


def test_a_read_only_caller_may_list(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, seeded: uuid.UUID
) -> None:
    act_as(org_a.viewer)
    assert client.get(ISSUES).status_code == 200


def test_filters_are_applied(
    client: TestClient,
    act_as: Callable[..., None],
    org_a: Tenant,
    seeded: uuid.UUID,
) -> None:
    act_as(org_a.analyst)
    assert items(client.get(ISSUES, params={"check_id": CRITICAL_CHECK}))
    assert not items(client.get(ISSUES, params={"check_id": BLOCKER_CHECK}))
    assert not items(client.get(ISSUES, params={"state": IssueState.VERIFIED_RESOLVED}))
    assert not items(client.get(ISSUES, params={"remediation_owner": "MARKETER"}))
    assert items(client.get(ISSUES, params={"severity": "CRITICAL"}))


def test_the_detail_view_shows_the_affected_urls_and_the_reverification_note(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, seeded: uuid.UUID
) -> None:
    act_as(org_a.analyst)
    data = payload(client.get(f"{ISSUES}/{seeded}"))
    assert data["affected_urls"] == [PAGE_A]
    assert data["fingerprint"]
    assert data["recurrence"]["count"] == 0
    assert data["verification_runs"] == []
    assert data["reverification_note_ko"]


def test_another_organizations_issue_is_a_404(
    client: TestClient, act_as: Callable[..., None], org_b: Tenant, seeded: uuid.UUID
) -> None:
    act_as(org_b.analyst)
    response = client.get(f"{ISSUES}/{seeded}")
    assert response.status_code == 404
    assert error_code(response) == "NOT_FOUND"


def test_an_id_that_exists_nowhere_answers_exactly_like_a_foreign_one(
    client: TestClient, act_as: Callable[..., None], org_b: Tenant, seeded: uuid.UUID
) -> None:
    act_as(org_b.analyst)
    foreign = client.get(f"{ISSUES}/{seeded}")
    nowhere = client.get(f"{ISSUES}/{uuid.uuid4()}")
    assert foreign.status_code == nowhere.status_code == 404
    assert error_message(foreign) == error_message(nowhere)


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #


def test_issue_read_alone_cannot_transition_anything(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, seeded: uuid.UUID
) -> None:
    act_as(org_a.viewer)
    response = client.post(
        f"{ISSUES}/{seeded}/transitions", json={"to_state": IssueState.ACKNOWLEDGED}
    )
    assert response.status_code == 403
    assert error_code(response) == "PERMISSION_DENIED"


def test_issue_read_alone_cannot_assign_or_request_verification(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, seeded: uuid.UUID
) -> None:
    act_as(org_a.viewer)
    assert (
        client.post(
            f"{ISSUES}/{seeded}/assignee", json={"assigned_to": str(org_a.analyst.user_id)}
        ).status_code
        == 403
    )
    assert client.post(f"{ISSUES}/{seeded}/verification-requests").status_code == 403
    assert (
        client.post(
            f"{ISSUES}/{seeded}/verification-results", json={"scan_run_id": str(uuid.uuid4())}
        ).status_code
        == 403
    )


def test_marking_an_issue_resolved_by_hand_is_refused(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, seeded: uuid.UUID
) -> None:
    act_as(org_a.analyst)
    response = client.post(
        f"{ISSUES}/{seeded}/transitions", json={"to_state": IssueState.VERIFIED_RESOLVED}
    )
    assert response.status_code == 409
    assert error_code(response) == "CONFLICT"
    assert not error_message(response).isascii()


def test_verified_resolved_is_not_even_an_accepted_input_shortcut(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, seeded: uuid.UUID
) -> None:
    """Every route in, at every state, is refused — there is no ordering that works."""
    act_as(org_a.analyst)
    for state in (IssueState.IN_PROGRESS, IssueState.FIX_CLAIMED):
        assert (
            client.post(f"{ISSUES}/{seeded}/transitions", json={"to_state": state}).status_code
            == 200
        )
        assert (
            client.post(
                f"{ISSUES}/{seeded}/transitions",
                json={"to_state": IssueState.VERIFIED_RESOLVED},
            ).status_code
            == 409
        )


def test_an_unknown_state_name_is_rejected_before_it_reaches_the_service(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, seeded: uuid.UUID
) -> None:
    act_as(org_a.analyst)
    response = client.post(f"{ISSUES}/{seeded}/transitions", json={"to_state": "DONE"})
    assert response.status_code == 422


def test_the_happy_path_ends_at_verified_resolved_only_through_a_passing_re_scan(
    client: TestClient,
    act_as: Callable[..., None],
    db: Session,
    org_a: Tenant,
    seeded: uuid.UUID,
    make_scan_run: Callable[..., ScanRun],
    make_check_result: Callable[..., object],
) -> None:
    act_as(org_a.analyst)
    client.post(f"{ISSUES}/{seeded}/transitions", json={"to_state": IssueState.IN_PROGRESS})
    client.post(f"{ISSUES}/{seeded}/transitions", json={"to_state": IssueState.FIX_CLAIMED})

    requested = payload(client.post(f"{ISSUES}/{seeded}/verification-requests"))
    assert requested["state"] == IssueState.VERIFYING
    assert requested["request"]["check_id"] == CRITICAL_CHECK
    assert requested["request"]["target_urls"] == [PAGE_A]

    rescan = make_scan_run(org_a)
    make_check_result(org_a, rescan, CRITICAL_CHECK, CheckStatus.PASS, urls=[PAGE_A])

    resolved = payload(
        client.post(
            f"{ISSUES}/{seeded}/verification-results", json={"scan_run_id": str(rescan.id)}
        )
    )
    assert resolved["state"] == IssueState.VERIFIED_RESOLVED
    assert resolved["outcome"] == "RESOLVED"


def test_a_verification_result_pointing_at_another_tenants_run_is_a_404(
    client: TestClient,
    act_as: Callable[..., None],
    org_a: Tenant,
    org_b: Tenant,
    seeded: uuid.UUID,
    make_scan_run: Callable[..., ScanRun],
    make_check_result: Callable[..., object],
) -> None:
    act_as(org_a.analyst)
    client.post(f"{ISSUES}/{seeded}/transitions", json={"to_state": IssueState.IN_PROGRESS})
    client.post(f"{ISSUES}/{seeded}/transitions", json={"to_state": IssueState.FIX_CLAIMED})
    client.post(f"{ISSUES}/{seeded}/verification-requests")

    foreign = make_scan_run(org_b)
    make_check_result(org_b, foreign, CRITICAL_CHECK, CheckStatus.PASS, urls=[PAGE_A])

    response = client.post(
        f"{ISSUES}/{seeded}/verification-results", json={"scan_run_id": str(foreign.id)}
    )
    assert response.status_code == 404


def test_the_client_cannot_supply_the_verdict(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, seeded: uuid.UUID,
    make_scan_run: Callable[..., ScanRun]
) -> None:
    """A body carrying ``outcome`` must not be honoured — it is not part of the contract."""
    act_as(org_a.analyst)
    client.post(f"{ISSUES}/{seeded}/transitions", json={"to_state": IssueState.IN_PROGRESS})
    client.post(f"{ISSUES}/{seeded}/transitions", json={"to_state": IssueState.FIX_CLAIMED})
    client.post(f"{ISSUES}/{seeded}/verification-requests")

    empty = make_scan_run(org_a)
    response = client.post(
        f"{ISSUES}/{seeded}/verification-results",
        json={"scan_run_id": str(empty.id), "outcome": "RESOLVED"},
    )
    assert response.status_code == 422, "요청 본문에 판정을 실어 보낼 수 없어야 합니다"


def test_assigning_an_issue_answers_with_the_new_owner(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, seeded: uuid.UUID
) -> None:
    act_as(org_a.analyst)
    data = payload(
        client.post(
            f"{ISSUES}/{seeded}/assignee", json={"assigned_to": str(org_a.analyst.user_id)}
        )
    )
    assert data["assigned_to"] == str(org_a.analyst.user_id)


def test_transitioning_another_organizations_issue_is_a_404(
    client: TestClient, act_as: Callable[..., None], org_b: Tenant, seeded: uuid.UUID
) -> None:
    act_as(org_b.analyst)
    response = client.post(
        f"{ISSUES}/{seeded}/transitions", json={"to_state": IssueState.ACKNOWLEDGED}
    )
    assert response.status_code == 404


def test_the_list_row_tells_the_console_which_buttons_to_draw(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, seeded: uuid.UUID
) -> None:
    """The screen must not keep its own copy of the state table."""
    act_as(org_a.analyst)
    row = items(client.get(ISSUES))[0]
    offered = {move["to_state"] for move in row["human_transitions"]}
    assert offered == {"ACKNOWLEDGED", "IN_PROGRESS", "WONT_FIX"}
    for move in row["human_transitions"]:
        assert not move["label_ko"].isascii()
        assert not move["reason_ko"].isascii()


def test_no_row_ever_offers_a_button_that_marks_a_problem_gone(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, seeded: uuid.UUID
) -> None:
    act_as(org_a.analyst)
    for row in items(client.get(ISSUES)):
        assert all(move["to_state"] != "VERIFIED_RESOLVED" for move in row["human_transitions"])


def test_the_detail_view_opens_the_evidence_a_finding_cites(
    client: TestClient, act_as: Callable[..., None], org_a: Tenant, seeded: uuid.UUID
) -> None:
    """이름만 돌려주던 자리에 실제 자료가 나온다.

    이름은 저장돼 있었고 근거도 저장돼 있었는데, 그 둘을 잇는 칸이 없어 서로를 찾지
    못했다. 근거를 열 수 없는 지적은 소문이다.
    """
    act_as(org_a.analyst)
    data = payload(client.get(f"{ISSUES}/{seeded}"))
    assert data["evidence_ids"]
    assert len(data["evidence"]) == len(data["evidence_ids"])
    assert data["missing_evidence_count"] == 0
    for record in data["evidence"]:
        assert record["evidence_id"] in data["evidence_ids"]
        assert len(record["content_hash"]) == 64


def test_evidence_that_cannot_be_found_is_counted_not_hidden(
    client: TestClient,
    act_as: Callable[..., None],
    org_a: Tenant,
    seeded: uuid.UUID,
    db: Session,
) -> None:
    """찾지 못한 근거를 조용히 빼면 지적이 실제보다 튼튼해 보인다."""
    from veo.db.models.analysis import Issue

    issue = db.get(Issue, seeded)
    issue.evidence_ids = [*(issue.evidence_ids or []), "http_response:0000000000000000"]
    db.commit()

    act_as(org_a.analyst)
    data = payload(client.get(f"{ISSUES}/{seeded}"))
    assert data["missing_evidence_count"] == 1
