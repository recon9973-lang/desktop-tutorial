"""``/issues`` — findings, ownership and verified resolution. **Not mounted.**

``veo.api.app`` belongs to the integration maintainer, so this router is defined and
tested here and included there when the integrator is ready. See
``INTEGRATION_REQUEST.md``.

The permission split is the module's rule expressed in HTTP: ``ISSUE_READ`` reaches the
two ``GET`` routes and nothing else, so a read-only caller cannot move an issue, claim a
fix, request a verification or record one. ``ISSUE_WRITE`` reaches the write routes — and
even then there is no route, body or ordering of calls that writes ``VERIFIED_RESOLVED``.
That state is produced by ``POST /issues/{id}/verification-results``, which reads the
persisted outcomes of a re-scan and derives the verdict itself.

404 rather than 403 for another organization's issue: a 403 would confirm the row exists.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal
from veo.contracts.enums import IssueSeverity
from veo.contracts.envelope import ApiResponse, PagedResponse
from veo.db.session import get_db
from veo.issues import service
from veo.issues.lifecycle import (
    IllegalTransitionError,
    IssueState,
    VerificationOutcome,
    describe_state_ko,
)
from veo.issues.schemas import (
    AssignRequest,
    IssueDetailPayload,
    IssuePayload,
    RemediationOwner,
    TransitionRequest,
    VerificationRecordedPayload,
    VerificationRequestedPayload,
    VerificationRequestPayload,
    VerificationResultRequest,
)
from veo.issues.verification import VerificationScopeError
from veo.organizations.errors import ReferenceNotFoundError
from veo.organizations.http import PageParams, conflict, guard, not_found, paged

router = APIRouter(prefix="/issues", tags=["issues"])

DbSession = Annotated[Session, Depends(get_db)]
Reader = Annotated[Principal, Depends(guard(Permission.ISSUE_READ))]
Writer = Annotated[Principal, Depends(guard(Permission.ISSUE_WRITE))]

NOT_FOUND_KO = "이슈를 찾을 수 없습니다."


@router.get(
    "",
    response_model=PagedResponse[IssuePayload],
    summary="이슈 목록 — 상태·심각도·담당 직군·검사로 필터",
    description=(
        "인증된 세션이 속한 조직의 이슈만 반환합니다. 각 항목의 `summary_ko`는 "
        "'수정 보고'와 '재측정으로 확인된 해결'을 절대 같은 말로 표현하지 않습니다."
    ),
)
def list_issues(
    session: DbSession,
    principal: Reader,
    request_id: RequestId,
    pagination: PageParams,
    project_id: Annotated[uuid.UUID | None, Query(description="특정 프로젝트만 조회")] = None,
    state: Annotated[list[IssueState] | None, Query(description="이슈 상태")] = None,
    severity: Annotated[
        list[IssueSeverity] | None, Query(description="심각도(명세에서 결정됨)")
    ] = None,
    remediation_owner: Annotated[
        list[RemediationOwner] | None, Query(description="조치 담당 직군")
    ] = None,
    check_id: Annotated[list[str] | None, Query(description="검사 ID")] = None,
    assigned_to: Annotated[uuid.UUID | None, Query(description="담당자 사용자 ID")] = None,
) -> PagedResponse[IssuePayload]:
    issues, total = service.list_issues(
        session,
        principal,
        project_id=project_id,
        states=state,
        severities=severity,
        remediation_owners=remediation_owner,
        check_ids=check_id,
        assigned_to=assigned_to,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paged(
        [IssuePayload.of(issue, summary_ko=service.summarize_issue(issue)) for issue in issues],
        request_id,
        pagination=pagination,
        total_items=total,
    )


@router.get(
    "/{issue_id}",
    response_model=ApiResponse[IssueDetailPayload],
    summary="이슈 상세 — 영향 URL·조치 방법·재측정 이력·재발 주기",
    description=(
        "상태 변경 이력과 재측정 실행 기록을 모두 포함합니다. 다른 조직의 이슈 ID는 "
        "존재 여부와 무관하게 404를 반환합니다."
    ),
)
def get_issue(
    issue_id: uuid.UUID,
    session: DbSession,
    principal: Reader,
    request_id: RequestId,
) -> ApiResponse[IssueDetailPayload]:
    detail = service.get_issue_detail(session, principal, issue_id)
    if detail is None:
        raise not_found(NOT_FOUND_KO)
    return ok(IssueDetailPayload.of_detail(detail), request_id)


@router.post(
    "/{issue_id}/assignee",
    response_model=ApiResponse[IssuePayload],
    summary="담당자 지정",
    description="같은 조직에 소속된 사용자만 지정할 수 있습니다. `null`이면 지정을 해제합니다.",
)
def assign_issue(
    issue_id: uuid.UUID,
    payload: AssignRequest,
    session: DbSession,
    principal: Writer,
    request_id: RequestId,
) -> ApiResponse[IssuePayload]:
    try:
        issue = service.assign_issue(
            session, principal, issue_id, payload.assigned_to, request_id=request_id
        )
    except ReferenceNotFoundError as exc:
        raise not_found(exc.message_ko) from exc
    return ok(IssuePayload.of(issue, summary_ko=service.summarize_issue(issue)), request_id)


@router.post(
    "/{issue_id}/transitions",
    response_model=ApiResponse[IssuePayload],
    summary="이슈 상태 변경 (담당자 조작)",
    description=(
        "담당자가 직접 바꿀 수 있는 상태만 허용합니다. `FIX_CLAIMED`는 '무언가를 바꿨다'는 "
        "보고일 뿐 해결이 아니며, `VERIFIED_RESOLVED`는 이 엔드포인트로 지정할 수 없습니다 — "
        "표적 재측정이 통과를 확인했을 때만 기록됩니다. 허용되지 않는 전이는 409와 함께 "
        "지금 선택 가능한 상태를 한국어로 알려줍니다."
    ),
)
def transition_issue(
    issue_id: uuid.UUID,
    payload: TransitionRequest,
    session: DbSession,
    principal: Writer,
    request_id: RequestId,
) -> ApiResponse[IssuePayload]:
    try:
        issue = service.transition_issue(
            session, principal, issue_id, payload.to_state, request_id=request_id
        )
    except ReferenceNotFoundError as exc:
        raise not_found(exc.message_ko) from exc
    except IllegalTransitionError as exc:
        raise conflict(exc.message_ko) from exc
    return ok(IssuePayload.of(issue, summary_ko=service.summarize_issue(issue)), request_id)


@router.post(
    "/{issue_id}/verification-requests",
    response_model=ApiResponse[VerificationRequestedPayload],
    summary="표적 재검사 요청",
    description=(
        "이슈를 `VERIFYING`으로 옮기고, 재검사가 수집해야 할 URL과 검사 하나를 반환합니다. "
        "사이트 전체를 다시 진단하지 않습니다."
    ),
)
def request_verification(
    issue_id: uuid.UUID,
    session: DbSession,
    principal: Writer,
    request_id: RequestId,
) -> ApiResponse[VerificationRequestedPayload]:
    try:
        issue, request = service.request_verification(
            session, principal, issue_id, request_id=request_id
        )
    except ReferenceNotFoundError as exc:
        raise not_found(exc.message_ko) from exc
    except IllegalTransitionError as exc:
        raise conflict(exc.message_ko) from exc
    except VerificationScopeError as exc:
        raise conflict(exc.message_ko) from exc

    state = IssueState(issue.state)
    payload = VerificationRequestedPayload(
        id=issue.id,
        state=state,
        state_label_ko=describe_state_ko(state),
        summary_ko=service.summarize_issue(issue),
        request=VerificationRequestPayload.of(request),
    )
    return ok(payload, request_id)


@router.post(
    "/{issue_id}/verification-results",
    response_model=ApiResponse[VerificationRecordedPayload],
    summary="재측정 결과 반영 — 해결로 이동하는 유일한 경로",
    description=(
        "재측정을 수행한 진단 실행 ID만 받습니다. 판정(`RESOLVED` / `STILL_FAILING` / "
        "`INCONCLUSIVE`)은 그 실행이 남긴 검사 결과에서 VEO가 도출하며, 요청 본문으로 "
        "지정할 수 없습니다. 영향 URL 중 일부만 측정되었거나 검사 결과가 없으면 "
        "`INCONCLUSIVE`이며 해결로 인정되지 않습니다."
    ),
)
def record_verification_result(
    issue_id: uuid.UUID,
    payload: VerificationResultRequest,
    session: DbSession,
    principal: Writer,
    request_id: RequestId,
) -> ApiResponse[VerificationRecordedPayload]:
    try:
        issue, run = service.record_verification_outcome(
            session,
            principal,
            issue_id,
            scan_run_id=payload.scan_run_id,
            request_id=request_id,
        )
    except ReferenceNotFoundError as exc:
        raise not_found(exc.message_ko) from exc
    except IllegalTransitionError as exc:
        raise conflict(exc.message_ko) from exc

    state = IssueState(issue.state)
    detail = run.detail or {}
    recorded = VerificationRecordedPayload(
        id=issue.id,
        state=state,
        state_label_ko=describe_state_ko(state),
        outcome=VerificationOutcome(run.outcome),
        reason_ko=str(detail.get("reason_ko", "")),
        verification_run_id=run.id,
        scan_run_id=run.scan_run_id,
        summary_ko=service.summarize_issue(issue),
    )
    return ok(recorded, request_id)


__all__ = ["router"]
