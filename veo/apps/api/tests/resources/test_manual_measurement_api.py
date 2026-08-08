"""수동 측정과 예상치 — HTTP 표면.

두 가지를 확인한다.

**하나.** 수동 측정으로 만들어진 실행은 `kind=MANUAL` 로 남고, 목록에서 그 종류로
갈라 볼 수 있는가. 갈라 두지 않으면 사람이 고른 검색어가 정기 측정과 같은 칸에 쌓이고,
그때 추이는 검색어를 고르는 것만으로 움직인다(ADR 0015).

**둘.** 누르기 전 예상치가 **호출 수는 내고 금액은 근거 없이는 안 내는가.** 근거 없이
나온 금액은 실측과 화면에서 구별되지 않고, 그 값에 맞춰 예산을 잡게 된다.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from veo.core.settings import get_settings
from veo.db.models.identity import Project
from veo.db.models.observation import ObservationRun as ObservationRunRow
from veo.db.models.observation import PromptSet as PromptSetRow
from veo.observations import router as observations_router

from .support import DATABASE_URL, Tenant, error_code, payload

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(DATABASE_URL is None, reason="VEO_TEST_DATABASE_URL 이 필요합니다"),
]

PREFIX = get_settings().api_prefix
RUNS = f"{PREFIX}/observations/runs"
MANUAL = f"{PREFIX}/observations/runs/manual"
ESTIMATES = f"{PREFIX}/observations/estimates"

ENGINES = [{"engine": "OPENAI", "model": "gpt-5", "search_mode": "NO_BROWSING"}]


@pytest.fixture(autouse=True)
def no_background_thread(monkeypatch: pytest.MonkeyPatch) -> list[uuid.UUID]:
    """배경 스레드를 띄우지 않는다.

    이 시험이 보려는 것은 **HTTP 표면**이다. 진짜로 떨어뜨리면 스레드가 자격증명 없이
    외부 호출을 시도하고, 시험 트랜잭션이 끝난 뒤에 `jobs` 를 갱신하려다 넘어진다 —
    시험과 무관한 소음이고, 순서에 따라 결과가 달라진다.
    """
    started: list[uuid.UUID] = []
    monkeypatch.setattr(
        observations_router, "run_detached", lambda job_id, work: started.append(job_id)
    )
    return started


@pytest.fixture
def project(db: Session, make_tenant: Callable[[str], Tenant]) -> tuple[Tenant, uuid.UUID]:
    tenant = make_tenant("manual")
    row = Project(
        organization_id=tenant.organization_id,
        slug=f"manual-{uuid.uuid4().hex[:8]}",
        name="수동 측정 프로젝트",
        locale="ko-KR",
        settings={},
    )
    db.add(row)
    db.flush()
    # 요청은 **다른 세션**으로 들어온다. 커밋하지 않으면 그쪽에서 이 프로젝트가 안 보인다.
    db.commit()
    return tenant, row.id


# --------------------------------------------------------------------------- #
# 수동 측정
# --------------------------------------------------------------------------- #


def test_a_manual_run_creates_an_unbalanced_set_marked_manual(
    client: TestClient,
    db: Session,
    project: tuple[Tenant, uuid.UUID],
    act_as: Callable[..., None],
) -> None:
    """검색어 하나만으로도 잴 수 있어야 한다 — 균형 검사는 여기서 할 일이 아니다."""
    tenant, project_id = project
    act_as(tenant.analyst)

    response = client.post(
        MANUAL,
        json={
            "project_id": str(project_id),
            "questions": ["강남 임플란트 잘하는 곳"],
            "engines": ENGINES,
        },
    )
    assert response.status_code == 202, response.text
    assert payload(response)["id"]

    created = db.scalars(
        select(PromptSetRow).where(PromptSetRow.project_id == project_id)
    ).all()
    assert len(created) == 1
    assert created[0].kind == "MANUAL"
    assert created[0].is_locked is True
    assert "균형 검사" in (created[0].generation_rule_ko or "")


def test_a_manual_run_refuses_an_empty_question(
    client: TestClient,
    project: tuple[Tenant, uuid.UUID],
    act_as: Callable[..., None],
) -> None:
    tenant, project_id = project
    act_as(tenant.analyst)

    response = client.post(
        MANUAL,
        json={
            "project_id": str(project_id),
            "questions": ["   "],
            "engines": ENGINES,
        },
    )
    assert response.status_code == 422
    assert error_code(response)


def test_an_unknown_engine_is_refused_before_any_prompt_set_is_stored(
    client: TestClient,
    db: Session,
    project: tuple[Tenant, uuid.UUID],
    act_as: Callable[..., None],
) -> None:
    """실패할 작업을 만들어 두지 않는다. 즉석 집합도 남기지 않는다."""
    tenant, project_id = project
    act_as(tenant.analyst)

    response = client.post(
        MANUAL,
        json={
            "project_id": str(project_id),
            "questions": ["강남 임플란트"],
            "engines": [{"engine": "OPENAI", "model": "gpt-5", "search_mode": "설마"}],
        },
    )
    assert response.status_code == 422

    leftover = db.scalars(
        select(PromptSetRow).where(PromptSetRow.project_id == project_id)
    ).all()
    assert leftover == []


def test_the_run_list_can_separate_manual_from_scheduled(
    client: TestClient,
    db: Session,
    project: tuple[Tenant, uuid.UUID],
    act_as: Callable[..., None],
) -> None:
    tenant, project_id = project

    prompt_set = PromptSetRow(
        organization_id=tenant.organization_id,
        project_id=project_id,
        name="집합",
        version=uuid.uuid4().hex[:8],
        locale="ko-KR",
    )
    db.add(prompt_set)
    db.flush()

    def run_row(kind: str) -> ObservationRunRow:
        return ObservationRunRow(
            organization_id=tenant.organization_id,
            project_id=project_id,
            prompt_set_id=prompt_set.id,
            kind=kind,
            repetitions_per_prompt=3,
            engines=["OPENAI"],
            competitor_ids=[],
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

    db.add_all([run_row("SCHEDULED"), run_row("MANUAL")])
    db.flush()
    db.commit()

    act_as(tenant.analyst)

    both = payload(client.get(RUNS, params={"project_id": str(project_id)}))
    assert {item["kind"] for item in both["items"]} == {"SCHEDULED", "MANUAL"}

    only_manual = payload(
        client.get(RUNS, params={"project_id": str(project_id), "kind": "MANUAL"})
    )
    assert [item["kind"] for item in only_manual["items"]] == ["MANUAL"]

    only_scheduled = payload(
        client.get(RUNS, params={"project_id": str(project_id), "kind": "SCHEDULED"})
    )
    assert [item["kind"] for item in only_scheduled["items"]] == ["SCHEDULED"]


def test_an_unknown_kind_filter_is_refused_rather_than_silently_ignored(
    client: TestClient,
    project: tuple[Tenant, uuid.UUID],
    act_as: Callable[..., None],
) -> None:
    """조용히 무시하면 화면은 걸렀다고 믿고 안 걸러진 목록을 보여준다."""
    tenant, project_id = project
    act_as(tenant.analyst)

    response = client.get(RUNS, params={"project_id": str(project_id), "kind": "아무거나"})
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# 예상치
# --------------------------------------------------------------------------- #


def test_the_estimate_reports_an_exact_call_count(
    client: TestClient,
    project: tuple[Tenant, uuid.UUID],
    act_as: Callable[..., None],
) -> None:
    tenant, _ = project
    act_as(tenant.analyst)

    body = payload(
        client.post(
            ESTIMATES,
            json={
                "question_count": 5,
                "repetitions": 3,
                "engines": [
                    {"engine": "OPENAI", "model": "gpt-5", "search_mode": "BROWSING"},
                    {"engine": "OPENAI", "model": "gpt-5", "search_mode": "NO_BROWSING"},
                ],
            },
        )
    )
    assert body["total_calls"] == 30
    assert len(body["slots"]) == 2
    assert {slot["slot"] for slot in body["slots"]} == {
        "OPENAI:gpt-5:BROWSING",
        "OPENAI:gpt-5:NO_BROWSING",
    }


def test_with_nothing_measured_yet_the_estimate_has_no_amount_and_says_why(
    client: TestClient,
    project: tuple[Tenant, uuid.UUID],
    act_as: Callable[..., None],
) -> None:
    """관측이 0건이면 토큰을 모른다. 모르면 금액을 내지 않는다."""
    tenant, _ = project
    act_as(tenant.analyst)

    body = payload(
        client.post(
            ESTIMATES,
            json={"question_count": 5, "repetitions": 3, "engines": ENGINES},
        )
    )
    assert body["total_calls"] == 15
    assert body["amount_usd"] is None
    assert body["measurement"] == "NONE"
    assert body["remedies_ko"], "왜 못 내는지가 함께 나가야 한다"
    assert body["slots"][0]["baseline_samples"] == 0
