"""작업 기록 — 오래 걸리는 일이 요청 밖에서 도는 동안 붙잡고 있는 것.

## 왜 이 모듈이 늦게 생겼나

`jobs` 테이블과 `JobStatus` 9단계는 Phase 0 부터 있었다. 워커 런타임(멱등성·진행률·
취소)도 있었다. **그런데 아무도 쓰지 않았다** — `apps/api` 전체에 `.delay()` 호출이
0건이었고, `Job` 모델을 `db/models` 밖에서 참조하는 코드도 0건이었다. 관측 실행은
요청 안에서 그대로 돌았고, 프롬프트 곱하기 엔진 곱하기 반복만큼 외부 AI 를 순서대로 부르니
수 분이 걸렸다. 그 요청은 게이트웨이가 먼저 끊는다. 지침서 0-G 가 그래서 생겼다.

## 지금 무엇이 돌고 무엇이 안 도는가

**실행은 API 프로세스 안의 배경 스레드에서 돈다. Celery 워커가 아니다.**
브로커(Redis)가 배포 환경에 없기 때문이고, 없는 것을 있는 척하지 않는다.

이 선택의 대가는 분명하다 — **API 프로세스가 재시작하면 돌던 작업은 그대로 죽는다.**
그때 그 행은 `RUNNING` 인 채 영원히 남는다. 그것을 "실행 중" 이라고 계속 보여주면
사용자는 오지 않을 결과를 기다린다. 그래서 :data:`STALE_AFTER` 를 두고, 그보다 오래
소식이 없는 작업은 **진행 상황을 알 수 없음**으로 보고한다. 낫게 보이려고 상태를
바꿔 쓰지는 않는다(0-A).

브로커가 생기면 :func:`submit` 이 돌려준 행을 Celery 가 집어가면 된다. 계약은 그대로다.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy.orm import Session

from veo.authz.principal import Principal
from veo.authz.tenancy import tenant_select
from veo.contracts.enums import JobStatus, JobType, Surface
from veo.db.models.analysis import Job as JobRow

#: 이보다 오래 소식이 없는 미완료 작업은 "실행 중" 이라고 말하지 않는다.
#:
#: 관측 한 번은 길면 몇 분이다. 여유를 넉넉히 두되, 무한정 두지는 않는다 — 죽은 작업을
#: 살아 있다고 보여주는 화면은 고장난 화면보다 나쁘다. 고장은 눈에 띄고 이것은 안 띈다.
STALE_AFTER: Final = timedelta(minutes=20)

#: 진행 중을 뜻하는 상태들.
_OPEN_STATUSES: Final = frozenset(
    {JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.CANCEL_REQUESTED}
)


class JobNotFoundError(LookupError):
    """그 조직에 그런 작업이 없다. 남의 조직 것이어도 똑같이 없는 것이다."""


def input_hash(job_type: JobType, parameters: dict[str, Any]) -> str:
    """같은 입력인지 판단하는 지문.

    키 순서가 달라도 같은 값이 나오도록 정렬해서 직렬화한다. 정렬하지 않으면 같은
    요청이 매번 다른 지문을 갖고, 멱등성 검사가 아무것도 걸러내지 못한다.
    """
    canonical = json.dumps(
        {"type": str(job_type), "parameters": parameters},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def submit(
    session: Session,
    principal: Principal,
    *,
    job_type: JobType,
    parameters: dict[str, Any],
    project_id: uuid.UUID | None = None,
    idempotency_key: str | None = None,
    surface: Surface = Surface.CONSOLE,
    stages: list[str] | None = None,
) -> tuple[JobRow, bool]:
    """작업을 등록한다. ``(행, 새로_만들었는가)``.

    같은 `idempotency_key` 로 다시 부르면 **새 작업을 만들지 않고 원래 것을 돌려준다.**
    관측은 돈이 나가는 일이라, 새로고침 한 번이 두 번 청구되면 안 된다.
    """
    if idempotency_key is not None:
        existing = session.scalars(
            tenant_select(JobRow, principal)
            .where(JobRow.type == str(job_type))
            .where(JobRow.idempotency_key == idempotency_key)
        ).first()
        if existing is not None:
            return existing, False

    row = JobRow(
        organization_id=principal.organization_id,
        project_id=project_id,
        # 예약 실행(서비스 계정)은 사람이 아니다 — 실행자 칸을 비운다(FK·거짓 기록 방지).
        requested_by=None if principal.is_service_account else principal.user_id,
        type=str(job_type),
        surface=str(surface),
        status=str(JobStatus.QUEUED),
        progress=0.0,
        current_stage=None,
        stages=list(stages or []),
        idempotency_key=idempotency_key,
        input_hash=input_hash(job_type, parameters),
        parameters=parameters,
        attempts=0,
    )
    session.add(row)
    session.flush()
    return row, True


def begin(session: Session, job_id: uuid.UUID, *, stage: str | None = None) -> None:
    """작업이 실제로 돌기 시작했다."""
    row = session.get(JobRow, job_id)
    if row is None:
        return
    row.status = str(JobStatus.RUNNING)
    row.started_at = datetime.now(UTC)
    row.attempts += 1
    row.current_stage = stage


def advance(
    session: Session, job_id: uuid.UUID, *, progress: float, stage: str | None = None
) -> None:
    """진행률을 올린다. 이것이 살아 있다는 신호이기도 하다 — `STALE_AFTER` 참조."""
    row = session.get(JobRow, job_id)
    if row is None:
        return
    row.progress = min(1.0, max(0.0, progress))
    if stage is not None:
        row.current_stage = stage


def succeed(
    session: Session,
    job_id: uuid.UUID,
    *,
    result_run_id: uuid.UUID | None = None,
    partial: bool = False,
    scoring_spec_id: str | None = None,
    scoring_spec_version: str | None = None,
) -> None:
    """끝났다. `partial` 이면 **부분 성공**이지 성공이 아니다.

    절반만 실행된 관측을 `SUCCEEDED` 로 적으면 그 위에서 계산한 노출률이 완전한
    측정처럼 읽힌다. 분모가 틀렸다는 사실이 어디에도 남지 않는다.

    **어느 명세로 채점했는지도 여기서 남긴다.** 잡을 만드는 시점에는 아직 모르고,
    끝나는 시점에는 안다. 표에 칸이 있는데 운영 17건이 전부 비어 있었다
    (2026-08-06 실측) — 명세가 바뀌면 점수가 바뀌는데, 그 잡이 어느 판으로
    채점됐는지 되짚을 수 없었다.
    """
    row = session.get(JobRow, job_id)
    if row is None:
        return
    row.status = str(JobStatus.PARTIAL_SUCCESS if partial else JobStatus.SUCCEEDED)
    row.progress = 1.0
    row.finished_at = datetime.now(UTC)
    row.result_run_id = result_run_id
    row.partial_result_available = partial
    if scoring_spec_id is not None:
        row.scoring_spec_id = scoring_spec_id
    if scoring_spec_version is not None:
        row.scoring_spec_version = scoring_spec_version


def fail(
    session: Session,
    job_id: uuid.UUID,
    *,
    error_code: str,
    safe_message_ko: str,
    retryable: bool = False,
    internal_error_ref: str | None = None,
) -> None:
    """실패로 닫는다.

    `safe_message_ko` 는 **사람에게 보여줄 수 있는 문장만** 담는다. 공급자 오류 원문을
    그대로 옮기면 자격증명·내부 호스트명이 화면과 로그로 새어 나간다. 원문은
    `internal_error_ref` 로만 가리킨다.
    """
    row = session.get(JobRow, job_id)
    if row is None:
        return
    row.status = str(JobStatus.FAILED_RETRYABLE if retryable else JobStatus.FAILED_FINAL)
    row.finished_at = datetime.now(UTC)
    row.error_code = error_code
    row.safe_error_message = safe_message_ko
    row.internal_error_ref = internal_error_ref


def read(session: Session, principal: Principal, job_id: uuid.UUID) -> JobRow:
    """조직 범위 안에서 하나를 읽는다. 남의 조직 것은 **없는 것**이다(403 아님)."""
    row = session.scalars(
        tenant_select(JobRow, principal).where(JobRow.id == job_id)
    ).first()
    if row is None:
        raise JobNotFoundError(str(job_id))
    return row


def recent(
    session: Session,
    principal: Principal,
    *,
    job_type: JobType | None = None,
    limit: int = 50,
) -> tuple[JobRow, ...]:
    statement = tenant_select(JobRow, principal).order_by(JobRow.created_at.desc())
    if job_type is not None:
        statement = statement.where(JobRow.type == str(job_type))
    return tuple(session.scalars(statement.limit(limit)).all())


def is_stale(row: JobRow, *, now: datetime | None = None) -> bool:
    """소식이 끊긴 미완료 작업인가.

    프로세스가 재시작하면 돌던 작업은 `RUNNING` 인 채 남는다. 그것을 계속 "실행 중"
    이라고 보여주면 오지 않을 결과를 기다리게 된다.
    """
    if JobStatus(row.status) not in _OPEN_STATUSES:
        return False
    moment = now or datetime.now(UTC)
    last_seen = row.updated_at or row.created_at
    if last_seen is None:
        return False
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=UTC)
    return (moment - last_seen) > STALE_AFTER


def status_note_ko(row: JobRow, *, now: datetime | None = None) -> str:
    """이 상태를 사람에게 어떻게 설명할 것인가. 빈 문자열이면 덧붙일 말이 없다는 뜻이다."""
    if is_stale(row, now=now):
        return (
            "이 작업의 소식이 20분 넘게 끊겼습니다. 서버가 재시작하면서 중단됐을 수 "
            "있습니다. **끝났는지 아닌지 저희도 알지 못합니다** — 결과가 남아 있는지 "
            "확인하시고, 없으면 다시 실행해 주십시오."
        )
    status = JobStatus(row.status)
    if status is JobStatus.PARTIAL_SUCCESS:
        return (
            "계획한 실행 가운데 일부만 수행됐습니다. 결과의 비율은 실제로 던진 질문에 "
            "대한 값이며, 계획 전체에 대한 답이 아닙니다."
        )
    if status is JobStatus.QUEUED:
        return "대기 중입니다. 아직 시작하지 않았습니다."
    return ""


__all__ = [
    "STALE_AFTER",
    "JobNotFoundError",
    "advance",
    "begin",
    "fail",
    "input_hash",
    "is_stale",
    "read",
    "recent",
    "status_note_ko",
    "submit",
    "succeed",
]
