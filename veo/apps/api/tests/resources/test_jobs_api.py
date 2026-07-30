"""``/jobs`` — 요청 밖에서 도는 일을 화면이 물어보는 경로.

이 경로가 없는 동안 관측은 요청 안에서 돌았다. 질문 여덟 개를 세 번씩 던지면 스물네
번의 외부 호출이고, 그것을 기다리는 요청은 게이트웨이가 먼저 끊는다. 사용자에게는
"기능이 고장났다" 로 보이고, 그 시점에 비용은 이미 나갔다.

여기서 고정하는 것 둘:

* **남의 조직 작업은 403 이 아니라 404 다.** 403 은 "있지만 못 본다" 를 알려주고,
  그것만으로도 남의 조직에 무엇이 있는지 세어 볼 수 있다.
* **소식이 끊긴 작업을 실행 중과 같게 그리지 않는다.** 응답에 `is_stale` 이 늘 들어
  있고, 참일 때는 끝났는지 아닌지 모른다고 말한다.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.resources.support import Tenant, payload

from veo.contracts.enums import JobStatus, JobType
from veo.db.models.analysis import Job as JobRow
from veo.jobs import service

JOBS = "/api/jobs"


def _job(
    db: Session,
    tenant: Tenant,
    *,
    status: JobStatus = JobStatus.RUNNING,
    updated_minutes_ago: float = 0.0,
) -> JobRow:
    row = JobRow(
        organization_id=tenant.organization_id,
        type=str(JobType.GEO_OBSERVATION_RUN),
        status=str(status),
        progress=0.4,
        current_stage="AI 엔진 호출",
        stages=["질문 준비", "AI 엔진 호출", "저장"],
        input_hash="a" * 64,
        parameters={},
        attempts=1,
    )
    db.add(row)
    db.commit()

    if updated_minutes_ago:
        moment = datetime.now(UTC) - timedelta(minutes=updated_minutes_ago)
        row.created_at = moment
        row.updated_at = moment
        db.commit()
    db.refresh(row)
    return row


class TestReadingOne:
    def test_a_running_job_reports_its_progress(
        self, client: TestClient, db: Session, org_a: Tenant, act_as: Callable[..., None]
    ) -> None:
        act_as(org_a.analyst)
        row = _job(db, org_a)

        response = client.get(f"{JOBS}/{row.id}")

        assert response.status_code == 200, response.text
        body = payload(response)
        assert body["status"] == "RUNNING"
        assert body["is_stale"] is False
        assert body["progress"] == 0.4
        assert body["current_stage"] == "AI 엔진 호출"

    def test_a_silent_job_says_we_do_not_know(
        self, client: TestClient, db: Session, org_a: Tenant, act_as: Callable[..., None]
    ) -> None:
        """서버가 재시작하면 돌던 작업은 죽는데 행은 RUNNING 인 채 남는다."""
        act_as(org_a.analyst)
        row = _job(db, org_a, updated_minutes_ago=service.STALE_AFTER.total_seconds() / 60 + 10)

        body = payload(client.get(f"{JOBS}/{row.id}"))

        assert body["is_stale"] is True
        assert "알지 못합니다" in body["note_ko"]

    def test_a_job_that_does_not_exist_is_404(
        self, client: TestClient, org_a: Tenant, act_as: Callable[..., None]
    ) -> None:
        act_as(org_a.analyst)

        assert client.get(f"{JOBS}/{uuid.uuid4()}").status_code == 404


class TestTenantIsolation:
    def test_another_organizations_job_is_not_found_rather_than_forbidden(
        self,
        client: TestClient,
        db: Session,
        org_a: Tenant,
        org_b: Tenant,
        act_as: Callable[..., None],
    ) -> None:
        """403 이면 남의 조직에 그 id 가 있다는 사실을 알려주게 된다."""
        row = _job(db, org_a)
        act_as(org_b.analyst)

        assert client.get(f"{JOBS}/{row.id}").status_code == 404

    def test_the_list_never_crosses_organizations(
        self,
        client: TestClient,
        db: Session,
        org_a: Tenant,
        org_b: Tenant,
        act_as: Callable[..., None],
    ) -> None:
        mine = _job(db, org_a)
        theirs = _job(db, org_b)
        act_as(org_a.analyst)

        listed = {item["id"] for item in payload(client.get(JOBS))["items"]}

        assert str(mine.id) in listed
        assert str(theirs.id) not in listed


class TestTheList:
    def test_failed_jobs_stay_in_the_list(
        self, client: TestClient, db: Session, org_a: Tenant, act_as: Callable[..., None]
    ) -> None:
        """실패를 목록에서 빼면 없던 일이 된다. 무엇이 안 됐는지 아무도 모른다."""
        act_as(org_a.analyst)
        failed = _job(db, org_a, status=JobStatus.FAILED_FINAL)

        listed = {item["id"]: item for item in payload(client.get(JOBS))["items"]}

        assert str(failed.id) in listed
        assert listed[str(failed.id)]["status"] == "FAILED_FINAL"

    def test_it_can_be_narrowed_to_one_kind_of_work(
        self, client: TestClient, db: Session, org_a: Tenant, act_as: Callable[..., None]
    ) -> None:
        act_as(org_a.analyst)
        observation = _job(db, org_a)

        response = client.get(JOBS, params={"type": str(JobType.SEO_SCAN)})

        listed = {item["id"] for item in payload(response)["items"]}
        assert str(observation.id) not in listed
