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
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal, tenant_select
from veo.contracts.enums import IssueSeverity, JobType
from veo.contracts.envelope import ApiResponse, PagedResponse
from veo.db.models.identity import Site
from veo.db.session import get_db
from veo.issues import service
from veo.issues.lifecycle import (
    IllegalTransitionError,
    IssueState,
    VerificationOutcome,
    describe_state_ko,
)
from veo.issues.reverify import REVERIFY_STAGES, reverification_work
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
from veo.jobs import service as jobs_service
from veo.jobs.dispatch import dispatch
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

    # **여기가 비어 있었다.** 지금까지 이 창구는 상태를 `VERIFYING` 으로 옮기고
    # 요청서를 돌려줄 뿐 아무것도 실행하지 않았다. 그래서 사람이 "재검사" 를 눌러도
    # 재측정이 시작되지 않았고, 이슈는 영영 닫히지 않았다 —
    # 실측 2026-08-09: 운영 이슈 165건이 전부 `OPEN`, `verification_runs` 0행.
    job = _start_reverification(session, principal, issue=issue, request=request)
    session.commit()
    session.refresh(issue)

    state = IssueState(issue.state)
    payload = VerificationRequestedPayload(
        id=issue.id,
        state=state,
        state_label_ko=describe_state_ko(state),
        summary_ko=service.summarize_issue(issue),
        request=VerificationRequestPayload.of(request),
        job_id=job.id if job is not None else None,
    )
    return ok(payload, request_id)


def _start_reverification(
    session: DbSession,
    principal: Principal,
    *,
    issue: Any,
    request: Any,
) -> Any:
    """이슈의 URL 만 다시 재는 작업을 걸고, 그 작업 행을 돌려준다.

    사이트를 못 찾으면 **작업 없이** 넘어간다. 상태는 이미 `VERIFYING` 이고, 그 사실은
    사실이다 — 사람이 재검사를 요청했다. 여기서 예외를 던지면 그 요청까지 되돌아가는데,
    되돌릴 이유가 없다. 대신 작업 번호가 비어 화면이 "재측정이 시작되지 않았습니다" 를
    말할 수 있다.
    """
    site = session.execute(
        tenant_select(Site, principal)
        .where(Site.project_id == issue.project_id)
        .order_by(Site.is_primary.desc())
    ).scalars().first()
    if site is None or not request.target_urls:
        return None

    job, created = jobs_service.submit(
        session,
        principal,
        job_type=JobType.REVERIFICATION,
        project_id=issue.project_id,
        stages=list(REVERIFY_STAGES),
        parameters={
            "issue_id": str(issue.id),
            "site_id": str(site.id),
            "check_id": request.check_id,
            "urls": list(request.target_urls),
        },
    )
    if created:
        dispatch(
            job.id,
            reverification_work(
                organization_id=principal.organization_id,
                user_id=principal.user_id,
                roles=principal.roles,
                session_id=principal.session_id,
                is_service_account=principal.is_service_account,
                issue_id=issue.id,
                site_id=site.id,
                target_url=site.origin,
                urls=tuple(request.target_urls),
            ),
            job_type=JobType.REVERIFICATION,
            # **큐로 갈 때는 이 값들만 건넌다.** 함수는 프로세스를 건너지 못한다.
            # 위 `reverification_work(...)` 의 인자와 하나씩 짝이 맞아야 하고, 하나라도
            # 빠지면 워커에서 `KeyError` 로 멈춘다 — 기본값으로 때우는 것보다 낫다.
            # 큐가 없는 배포에서는 `dispatch` 가 배경 스레드로 떨어뜨린다.
            parameters={
                "organization_id": str(principal.organization_id),
                "user_id": str(principal.user_id),
                "roles": [str(role) for role in principal.roles],
                "session_id": principal.session_id,
                "is_service_account": principal.is_service_account,
                "issue_id": str(issue.id),
                "site_id": str(site.id),
                "target_url": site.origin,
                "urls": list(request.target_urls),
                "locale": "ko-KR",
            },
        )
    return job


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
