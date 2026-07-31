"""검수 HTTP 표면 — 상태 코드가 검수자에게 무엇을 하라고 말하는가.

이 파일이 서비스 계층 시험과 따로 있는 이유는 **409 와 422 의 구분**이다.

* 409 — 지금은 안 되지만 나중엔 된다 (다른 검수자가 맡고 있다)
* 422 — 이 순서로는 영영 안 된다 (맡지도 않고 판정하려 한다)

둘을 같은 코드로 덮으면 화면이 같은 문장을 띄우고, 검수자는 새로고침만 반복한다.

그리고 **권한**. 위험 지적을 확정하는 것은 고객에게 그의 평판에 대해 무엇을 말할지
정하는 일이라 보고서 발행과 같은 급이다. 관측을 읽을 수 있다는 것만으로 여기 들어오면
안 된다.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.authz.principal import Principal
from veo.core.settings import get_settings
from veo.db.models.identity import Project
from veo.db.models.observation import (
    AIAnswer,
    AIEngine,
)
from veo.db.models.observation import (
    ObservationRun as ObservationRunRow,
)
from veo.db.models.observation import (
    Prompt as PromptRow,
)
from veo.db.models.observation import (
    PromptSet as PromptSetRow,
)
from veo.observations.findings import assessment_from_held_mention, new_assessment_row
from veo.observations.review.decisions import open_review

from .support import DATABASE_URL, Tenant, error_code, payload

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(DATABASE_URL is None, reason="VEO_TEST_DATABASE_URL 이 필요합니다"),
]

QUEUE = f"{get_settings().api_prefix}/observations/review-queue"
NOW = datetime(2026, 7, 31, 6, 0, tzinfo=UTC)
HASH = "c" * 64


@pytest.fixture
def held_finding(db: Session, make_tenant: Callable[[str], Tenant]) -> tuple[Tenant, uuid.UUID]:
    """검수 대기 판정 하나. 문장은 전부 가상 사례다."""
    tenant = make_tenant("review")
    suffix = uuid.uuid4().hex[:8]

    project = Project(
        organization_id=tenant.organization_id,
        slug=f"review-{suffix}",
        name="검수 프로젝트",
        locale="ko-KR",
        settings={},
    )
    db.add(project)
    db.flush()

    prompt_set = PromptSetRow(
        organization_id=tenant.organization_id,
        project_id=project.id,
        name="집합",
        version="1",
        locale="ko-KR",
    )
    db.add(prompt_set)
    db.flush()

    prompt = PromptRow(
        organization_id=tenant.organization_id,
        prompt_set_id=prompt_set.id,
        text="합성 질문입니다.",
        intent="DEFINITION",
        funnel="PROBLEM_AWARE",
        subject_type="NON_BRAND",
        business_importance=1,
        locale="ko-KR",
    )
    # `ai_engines` 는 조직에 묶이지 않는 전역 표다. 다른 시험이 만들어 두었으면 그것을 쓴다.
    ai_engine = db.scalars(
        select(AIEngine)
        .where(AIEngine.provider == "OPENAI")
        .where(AIEngine.model == "gpt-5")
        .where(AIEngine.search_mode == "BROWSING")
    ).first()
    if ai_engine is None:
        ai_engine = AIEngine(
            provider="OPENAI",
            model="gpt-5",
            search_mode="BROWSING",
            display_name="OPENAI gpt-5",
            is_enabled=True,
            provider_state="ENABLED",
        )
        db.add(ai_engine)
        db.flush()

    run = ObservationRunRow(
        organization_id=tenant.organization_id,
        project_id=project.id,
        prompt_set_id=prompt_set.id,
        repetitions_per_prompt=3,
        engines=["OPENAI"],
        competitor_ids=[],
        started_at=NOW,
        finished_at=NOW,
        status="SUCCEEDED",
        executions_attempted=1,
        executions_valid=1,
        executions_planned=1,
        executions_skipped=0,
        is_complete=True,
        skipped_detail={},
        confidence_breakdown={},
        prompts_below_repetition_floor=[],
    )
    db.add_all([prompt, run])
    db.flush()

    answer = AIAnswer(
        organization_id=tenant.organization_id,
        observation_run_id=run.id,
        prompt_id=prompt.id,
        ai_engine_id=ai_engine.id,
        repetition_index=1,
        model_version="gpt-5-2026-05-01",
        search_mode="BROWSING",
        account_state="ANONYMOUS",
        locale="ko-KR",
        executed_at=NOW,
        is_valid_execution=True,
        raw_answer_storage_key="veo-answer://synthetic/queue.json",
        raw_answer_hash=HASH,
        citation_support="STRUCTURED",
    )
    db.add(answer)
    db.flush()

    row = new_assessment_row(
        open_review(
            assessment_from_held_mention(
                answer_id=answer.id,
                answer_ref=answer.raw_answer_storage_key or "",
                answer_hash=HASH,
                span_start=4,
                quoted_text="온담한의원",
                reasons_ko=("이름 앞뒤에 다른 한글이 붙어 있습니다.",),
                decided_at=NOW,
            )
        ),
        organization_id=tenant.organization_id,
        answer_id=answer.id,
    )
    db.add(row)
    db.commit()
    return tenant, row.id


class TestWhoMayReview:
    def test_a_sales_viewer_cannot_see_the_queue(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        held_finding: tuple[Tenant, uuid.UUID],
    ) -> None:
        """검수 전 지적의 **원문**이 들어 있는 목록이다.

        고객 문서에서 그것을 막으려고 공개 게이트를 두었는데, 이 목록이 관측 읽기
        권한으로 열리면 그 게이트를 옆으로 돌아가는 길이 된다.
        """
        tenant, _ = held_finding
        act_as(tenant.viewer)

        assert client.get(QUEUE).status_code == 403

    def test_an_analyst_sees_it(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        held_finding: tuple[Tenant, uuid.UUID],
    ) -> None:
        tenant, assessment_id = held_finding
        act_as(tenant.analyst)

        data = payload(client.get(QUEUE))

        assert [item["assessment_id"] for item in data["items"]] == [str(assessment_id)]
        assert data["items"][0]["claim_text"] == "온담한의원"
        assert data["items"][0]["automated_verdict"] == "UNKNOWN"

    def test_the_closed_list_of_rejection_reasons_travels_with_the_queue(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        held_finding: tuple[Tenant, uuid.UUID],
    ) -> None:
        """화면이 사유를 지어내지 않게 한다. 자유 서술은 셀 수 없다."""
        tenant, _ = held_finding
        act_as(tenant.analyst)

        data = payload(client.get(QUEUE))

        values = {reason["value"] for reason in data["rejection_reasons"]}
        assert "WRONG_ENTITY" in values
        assert all(reason["label_ko"] for reason in data["rejection_reasons"])


class TestWhatEachFailureTellsTheReviewer:
    def test_deciding_without_claiming_is_422_not_409(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        held_finding: tuple[Tenant, uuid.UUID],
    ) -> None:
        """이 순서로는 영영 안 된다. 409 로 답하면 검수자가 새로고침만 반복한다."""
        tenant, assessment_id = held_finding
        act_as(tenant.analyst)

        response = client.post(f"{QUEUE}/{assessment_id}/decide", json={"decision": "CONFIRMED"})

        assert response.status_code == 422

    def test_rejecting_without_a_reason_is_refused(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        held_finding: tuple[Tenant, uuid.UUID],
    ) -> None:
        tenant, assessment_id = held_finding
        act_as(tenant.analyst)
        client.post(f"{QUEUE}/{assessment_id}/claim")

        response = client.post(f"{QUEUE}/{assessment_id}/decide", json={"decision": "REJECTED"})

        assert response.status_code == 422

    def test_an_unknown_assessment_is_404(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        held_finding: tuple[Tenant, uuid.UUID],
    ) -> None:
        tenant, _ = held_finding
        act_as(tenant.analyst)

        response = client.post(f"{QUEUE}/{uuid.uuid4()}/claim")

        assert response.status_code == 404
        assert error_code(response) == "NOT_FOUND"


class TestTheRoundTrip:
    def test_claim_then_confirm_moves_it_out_of_the_queue(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        held_finding: tuple[Tenant, uuid.UUID],
    ) -> None:
        tenant, assessment_id = held_finding
        act_as(tenant.analyst)

        claimed = payload(client.post(f"{QUEUE}/{assessment_id}/claim"))
        assert claimed["stage"] == "UNDER_REVIEW"
        assert claimed["is_reviewed"] is False

        decided = payload(
            client.post(
                f"{QUEUE}/{assessment_id}/decide",
                json={"decision": "CONFIRMED", "note_ko": "원문을 확인했습니다."},
            )
        )
        assert decided["stage"] == "CONFIRMED"
        assert decided["stored_as"] == "HUMAN_CONFIRMED"
        assert decided["is_reviewed"] is True

        remaining = payload(client.get(QUEUE))
        assert remaining["items"] == []

    def test_a_release_puts_it_back(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        held_finding: tuple[Tenant, uuid.UUID],
    ) -> None:
        tenant, assessment_id = held_finding
        act_as(tenant.analyst)

        client.post(f"{QUEUE}/{assessment_id}/claim")
        released = payload(client.post(f"{QUEUE}/{assessment_id}/release"))

        assert released["stage"] == "PENDING_REVIEW"
        assert payload(client.get(QUEUE))["total"] == 1

    def test_the_queue_says_which_item_is_mine(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        held_finding: tuple[Tenant, uuid.UUID],
    ) -> None:
        """화면은 이 값으로 판정 버튼을 낼지 착수 버튼을 낼지 정한다."""
        tenant, assessment_id = held_finding
        act_as(tenant.analyst)
        client.post(f"{QUEUE}/{assessment_id}/claim")

        item = payload(client.get(QUEUE))["items"][0]

        assert item["is_mine"] is True
        assert item["is_held_by_someone"] is False

    def test_the_queue_never_names_the_holder(
        self,
        client: TestClient,
        act_as: Callable[[Principal], None],
        held_finding: tuple[Tenant, uuid.UUID],
    ) -> None:
        """검수 화면이 조직원 명단을 흘리는 자리가 되면 안 된다."""
        tenant, assessment_id = held_finding
        act_as(tenant.analyst)
        client.post(f"{QUEUE}/{assessment_id}/claim")

        body = client.get(QUEUE).text

        assert str(tenant.analyst.user_id) not in body
