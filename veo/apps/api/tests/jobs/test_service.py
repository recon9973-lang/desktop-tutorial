"""작업 기록이 지켜야 하는 것들.

가장 중요한 둘:

* **같은 요청을 두 번 청구하지 않는다.** 관측은 돈이 나가는 일이고, 새로고침 한 번이
  두 번째 실행이 되면 안 된다.
* **소식이 끊긴 작업을 "실행 중" 이라고 말하지 않는다.** 서버가 재시작하면 돌던 작업은
  죽는데 행은 `RUNNING` 인 채 남는다. 그것을 계속 실행 중으로 보여주면 사용자는 오지
  않을 결과를 기다린다 — 고장은 눈에 띄지만 이것은 안 띈다.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from veo.contracts.enums import JobStatus, JobType
from veo.db.models.analysis import Job as JobRow
from veo.jobs import service


def _row(
    *,
    status: JobStatus = JobStatus.RUNNING,
    updated_minutes_ago: float = 0.0,
) -> JobRow:
    moment = datetime.now(UTC) - timedelta(minutes=updated_minutes_ago)
    row = JobRow(
        organization_id=uuid.uuid4(),
        type=str(JobType.GEO_OBSERVATION_RUN),
        status=str(status),
        progress=0.5,
        input_hash="x" * 64,
        parameters={},
        stages=[],
        attempts=1,
    )
    row.created_at = moment
    row.updated_at = moment
    return row


class TestTheInputFingerprint:
    def test_key_order_does_not_change_the_fingerprint(self) -> None:
        """정렬하지 않으면 같은 요청이 매번 다른 지문을 갖고, 멱등성 검사가 무의미해진다."""
        first = service.input_hash(JobType.SEO_SCAN, {"a": 1, "b": 2})
        second = service.input_hash(JobType.SEO_SCAN, {"b": 2, "a": 1})

        assert first == second

    def test_different_parameters_change_the_fingerprint(self) -> None:
        assert service.input_hash(JobType.SEO_SCAN, {"a": 1}) != service.input_hash(
            JobType.SEO_SCAN, {"a": 2}
        )

    def test_the_job_type_is_part_of_the_fingerprint(self) -> None:
        """같은 입력이라도 다른 종류의 작업이면 다른 일이다."""
        assert service.input_hash(JobType.SEO_SCAN, {"a": 1}) != service.input_hash(
            JobType.SITE_CRAWL, {"a": 1}
        )


class TestStaleness:
    def test_a_fresh_running_job_is_not_stale(self) -> None:
        assert not service.is_stale(_row(updated_minutes_ago=1))

    def test_a_silent_running_job_is_stale(self) -> None:
        """이것이 프로세스 재시작으로 죽은 작업의 모습이다."""
        row = _row(updated_minutes_ago=service.STALE_AFTER.total_seconds() / 60 + 5)

        assert service.is_stale(row)

    def test_a_finished_job_is_never_stale(self) -> None:
        """오래된 것과 소식이 끊긴 것은 다르다. 끝난 작업은 조용한 게 정상이다."""
        row = _row(status=JobStatus.SUCCEEDED, updated_minutes_ago=60 * 24 * 30)

        assert not service.is_stale(row)

    def test_a_failed_job_is_never_stale(self) -> None:
        row = _row(status=JobStatus.FAILED_FINAL, updated_minutes_ago=60 * 24)

        assert not service.is_stale(row)

    @pytest.mark.parametrize(
        "status", [JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.CANCEL_REQUESTED]
    )
    def test_every_open_status_can_go_stale(self, status: JobStatus) -> None:
        """대기 중인 작업도 죽는다 — 큐에 넣은 프로세스가 사라지면 아무도 집어가지 않는다."""
        row = _row(status=status, updated_minutes_ago=60)

        assert service.is_stale(row)


class TestWhatWeTellThePerson:
    def test_a_stale_job_admits_we_do_not_know(self) -> None:
        """"실행 중" 이라고 쓰면 거짓이다. 우리는 그것이 도는지 모른다."""
        row = _row(updated_minutes_ago=60)

        note = service.status_note_ko(row)

        assert "알지 못합니다" in note
        assert "다시 실행" in note

    def test_a_partial_success_says_the_ratios_are_not_the_whole_plan(self) -> None:
        row = _row(status=JobStatus.PARTIAL_SUCCESS)

        assert "계획 전체에 대한 답이 아닙니다" in service.status_note_ko(row)

    def test_a_healthy_running_job_needs_no_excuse(self) -> None:
        assert service.status_note_ko(_row()) == ""
