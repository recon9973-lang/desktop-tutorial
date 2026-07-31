"""검수 큐를 **재기동해도 살아남는 자리**에 올린다.

## 왜 인메모리로는 안 되나

`review/queue.py` 의 점유·반납·판정은 전부 프로세스 메모리에 있었다. 그래서:

* 프로세스가 재시작되면 누가 무엇을 맡고 있었는지 사라진다.
* 서버가 두 대면 같은 치명 등급 건을 두 사람이 각각 판정한다. 둘 다 자기 쪽 메모리에서
  "내가 점유했다" 를 보기 때문에 아무도 충돌을 모른다.

`risk/INTEGRATION_REQUEST.md` 요청 #3 이 이것이고, 이 모듈은 그 자리를
`claim_assessments` 의 `claimed_by`·`claimed_at`·`review_stage`·`review_history` 로
옮긴다. 상태 기계 자체는 옮기지 않는다 — 전이 규칙은 `review/decisions.py` 의 선언된
간선 표 하나뿐이고, 여기서 다시 쓰면 두 벌이 되어 갈라지기 시작한다(0-D).

## 점유를 DB 가 강제한다

`claim` 은 `SELECT … FOR UPDATE` 로 행을 잠그고 나서 판단한다. 잠그지 않으면 두 요청이
같은 순간에 "비어 있네" 를 읽고 둘 다 자기 이름을 적는다. 검수는 자주 일어나는 일이
아니라 잠금 경합이 문제 될 여지가 없고, 여기서 아끼면 아무도 못 보는 방식으로 틀린다.

## 착수와 판단은 다른 칸이다

`claimed_by` 는 **아직 판단하지 않았지만 보고 있는 사람**이고 `reviewed_by` 는
**판단한 사람**이다. 둘을 합치면 착수만 하고 만 건이 검수 완료로 읽힌다.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from veo.authz import Principal, assert_tenant_scoped, tenant_select
from veo.db.models.observation import ClaimAssessment as ClaimAssessmentRow
from veo.observations.findings import review_from_row
from veo.observations.review.decisions import (
    RejectionReason,
    ReviewedAssessment,
    ReviewStage,
    ReviewTrigger,
    apply_decision,
    describe_stage_ko,
)
from veo.organizations import audit

#: 이 시간이 지나도록 판단이 없으면 점유가 풀린다. 사람은 자리를 비우고 브라우저는
#: 닫힌다 — 반납을 누르게 만들어 두면 큐가 서서히 잠긴다.
CLAIM_EXPIRES_AFTER = timedelta(minutes=30)

AUDIT_TARGET_TYPE = "claim_assessment"
CLAIM_ACTION = "observation_review.claim"
RELEASE_ACTION = "observation_review.release"
DECIDE_ACTION = "observation_review.decide"


class AssessmentNotFoundError(LookupError):
    """이 조직에 그 판정이 없다."""


class ReviewConflictError(Exception):
    """다른 검수자가 맡고 있는 건이다.

    `message_ko` 는 그대로 화면에 보여도 되는 문장이다. 누가 맡고 있는지는 이름이 아니라
    **다른 검수자**로만 말한다 — 판정 화면이 조직원 명단을 흘리는 자리가 되면 안 된다.
    """

    def __init__(self, message_ko: str) -> None:
        super().__init__(message_ko)
        self.message_ko = message_ko


def _locked(
    session: Session, principal: Principal, assessment_id: uuid.UUID
) -> ClaimAssessmentRow:
    statement = tenant_select(ClaimAssessmentRow, principal).where(
        ClaimAssessmentRow.id == assessment_id
    )
    assert_tenant_scoped(statement, principal.organization_id)
    row = session.scalars(statement.with_for_update()).one_or_none()
    if row is None:
        raise AssessmentNotFoundError(f"판정을 찾을 수 없습니다: {assessment_id}")
    return row


def _holder_is_someone_else(row: ClaimAssessmentRow, user_id: uuid.UUID, now: datetime) -> bool:
    if row.claimed_by is None or row.claimed_by == user_id:
        return False
    if row.claimed_at is None:
        return True
    return now - row.claimed_at < CLAIM_EXPIRES_AFTER


def _store(row: ClaimAssessmentRow, moved: ReviewedAssessment) -> None:
    """상태 기계가 만든 결과를 행에 적는다. 여기서 판단을 더하지 않는다."""
    stored = moved.to_row()
    row.review_state = stored["review_state"]
    row.review_stage = moved.stage.value
    row.reviewer_note = stored["reviewer_note"]
    row.reviewed_by = (
        uuid.UUID(moved.human.reviewer_id) if moved.human is not None else None
    )
    row.review_history = [entry.as_dict() for entry in moved.history]


def claim(
    session: Session,
    principal: Principal,
    assessment_id: uuid.UUID,
    *,
    now: datetime | None = None,
    request_id: str | None = None,
) -> ReviewedAssessment:
    """이 건을 맡는다. 자동 판정이 사람 앞에 놓이는 유일한 입구다."""
    at = now or datetime.now(UTC)
    row = _locked(session, principal, assessment_id)

    if _holder_is_someone_else(row, principal.user_id, at):
        raise ReviewConflictError(
            "다른 검수자가 맡고 있는 건입니다. 같은 지적을 두 사람이 각각 판정하면 "
            "어느 쪽이 고객에게 나가는지 알 수 없게 됩니다."
        )

    current = review_from_row(row)

    # 이미 내가 들고 있으면 아무 일도 하지 않는다. 새로고침 한 번이 이력을 한 줄
    # 늘리면, 나중에 그 이력을 읽는 사람은 뭔가 일어난 줄 안다.
    if current.stage is ReviewStage.UNDER_REVIEW and row.claimed_by == principal.user_id:
        return current

    # 만료된 점유는 **선언된 간선을 밟아서** 풀린다. 곧장 다시 맡게 두면 큐로 돌아간
    # 적이 없는데 주인이 바뀌고, 이력에서 그 순간이 사라진다. `SYSTEM_LAPSE` 가 바로
    # 이 자리를 위해 표에 있다.
    if current.stage is ReviewStage.UNDER_REVIEW:
        current = apply_decision(
            current,
            target=ReviewStage.PENDING_REVIEW,
            trigger=ReviewTrigger.SYSTEM_LAPSE,
            reviewer_id=None,
            at=at,
        )

    moved = apply_decision(
        current,
        target=ReviewStage.UNDER_REVIEW,
        trigger=ReviewTrigger.REVIEWER_CLAIM,
        reviewer_id=str(principal.user_id),
        at=at,
    )
    _store(row, moved)
    row.claimed_by = principal.user_id
    row.claimed_at = at
    audit.record(
        session,
        principal,
        action=CLAIM_ACTION,
        target_type=AUDIT_TARGET_TYPE,
        target_id=row.id,
        request_id=request_id,
        detail={"stage": moved.stage.value},
    )
    session.flush()
    return moved


def release(
    session: Session,
    principal: Principal,
    assessment_id: uuid.UUID,
    *,
    now: datetime | None = None,
    request_id: str | None = None,
) -> ReviewedAssessment:
    """판단하지 않고 반납한다. 판단하지 않았다는 사실도 기록으로 남는다."""
    at = now or datetime.now(UTC)
    row = _locked(session, principal, assessment_id)

    if _holder_is_someone_else(row, principal.user_id, at):
        raise ReviewConflictError("다른 검수자가 맡고 있는 건입니다.")

    moved = apply_decision(
        review_from_row(row),
        target=ReviewStage.PENDING_REVIEW,
        trigger=ReviewTrigger.REVIEWER_RELEASE,
        reviewer_id=str(principal.user_id),
        at=at,
    )
    _store(row, moved)
    row.claimed_by = None
    row.claimed_at = None
    audit.record(
        session,
        principal,
        action=RELEASE_ACTION,
        target_type=AUDIT_TARGET_TYPE,
        target_id=row.id,
        request_id=request_id,
    )
    session.flush()
    return moved


def decide(
    session: Session,
    principal: Principal,
    assessment_id: uuid.UUID,
    *,
    target: ReviewStage,
    rejection_reason: RejectionReason | None = None,
    note_ko: str | None = None,
    now: datetime | None = None,
    request_id: str | None = None,
) -> ReviewedAssessment:
    """맡고 있는 건에 대해 결론을 남긴다.

    **자동 판정은 바뀌지 않는다.** 사람의 결론은 별도 칸에 쌓이고, 두 기록이 어긋나는
    경우까지 나란히 읽을 수 있다(`ReviewedAssessment.disagrees`). 사람이 옳다고 해서
    기계가 뭐라고 했는지를 지우면, 자동 판정이 어디서 빗나가는지 셀 수 없게 된다.

    맡지 않은 건은 판단할 수 없다. 상태 기계가 `PENDING_REVIEW → CONFIRMED` 간선을
    선언하지 않았으므로 여기서 막는 것이 아니라 거기서 막힌다.
    """
    at = now or datetime.now(UTC)
    row = _locked(session, principal, assessment_id)

    if _holder_is_someone_else(row, principal.user_id, at):
        raise ReviewConflictError(
            "다른 검수자가 맡고 있는 건입니다. 먼저 그 검수자가 반납해야 합니다."
        )

    moved = apply_decision(
        review_from_row(row),
        target=target,
        trigger=ReviewTrigger.REVIEWER_DECISION,
        reviewer_id=str(principal.user_id),
        at=at,
        rejection_reason=rejection_reason,
        note_ko=note_ko,
    )
    _store(row, moved)
    # 결론이 난 건은 더 이상 점유 상태가 아니다. 근거 보강 대기로 보낸 건도 마찬가지 —
    # 다음에 집는 사람의 것이다.
    row.claimed_by = None
    row.claimed_at = None
    audit.record(
        session,
        principal,
        action=DECIDE_ACTION,
        target_type=AUDIT_TARGET_TYPE,
        target_id=row.id,
        request_id=request_id,
        detail={
            "stage": moved.stage.value,
            "stage_label_ko": describe_stage_ko(moved.stage),
            "rejection_reason": rejection_reason.value if rejection_reason else None,
            # 검수자 메모는 남기지 않는다. 자유 서술이라 고객 연락처가 섞일 수 있고,
            # 감사 로그는 그런 값을 담는 자리가 아니다. 메모 자체는 판정 행에 있다.
            "has_note": bool(note_ko),
            "disagrees_with_automation": moved.disagrees,
        },
    )
    session.flush()
    return moved


def pending_for_review(
    session: Session, principal: Principal, *, limit: int = 50
) -> tuple[tuple[uuid.UUID, ReviewedAssessment], ...]:
    """사람이 봐야 하는 건들 — 심각한 것부터.

    이미 결론이 난 건은 빼지만 **근거 보강 대기는 남긴다.** 그것은 끝난 것이 아니라
    멈춰 있는 것이고, 목록에서 빠지면 영영 아무도 다시 보지 않는다.
    """
    statement = (
        tenant_select(ClaimAssessmentRow, principal)
        .where(
            ClaimAssessmentRow.review_stage.in_(
                [
                    ReviewStage.PENDING_REVIEW.value,
                    ReviewStage.UNDER_REVIEW.value,
                    ReviewStage.NEEDS_MORE_EVIDENCE.value,
                ]
            )
        )
        .order_by(ClaimAssessmentRow.created_at, ClaimAssessmentRow.id)
        .limit(limit)
    )
    assert_tenant_scoped(statement, principal.organization_id)
    rows = list(session.scalars(statement))
    reviews = [(row.id, review_from_row(row)) for row in rows]
    # 심각도 순으로 세운다. 치명이 목록 아래에 있으면 그날 안 읽힌다.
    reviews.sort(key=lambda pair: pair[1].assessment.band.rank)
    return tuple(reviews)


__all__ = [
    "CLAIM_EXPIRES_AFTER",
    "AssessmentNotFoundError",
    "ReviewConflictError",
    "claim",
    "decide",
    "pending_for_review",
    "release",
]
