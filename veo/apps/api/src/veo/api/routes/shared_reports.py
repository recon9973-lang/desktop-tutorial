"""리포트 거래처 전달 링크 (P2-10a) — 만드는 문(콘솔)과 여는 문(익명).

공유는 조회 권한의 위임이 아니라 **복사본의 발행**이다: 링크를 만드는 순간의 HTML
내보내기가 통째로 굳어 저장되고, 익명 읽기는 그 복사본만 연다. 그래서

* 익명 표면이 요청 시점에 고객 데이터에 닿지 않는다(공유 진단 결과와 같은 계열),
* 링크가 여는 문서는 보낸 그날의 그 문서다 — 발행 불변 원칙 그대로,
* 없는 토큰과 만료된 토큰은 같은 답을 받는다 — 어떤 토큰이 실재했는지 확인해 주는
  창구가 되지 않기 위해서.

이 라우터는 통합 담당자 소유다(veo/api). 공개 패키지의 DB 격리 불변식은 건드리지
않는다 — 여기는 처음부터 DB 를 가진 쪽이다.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from veo.api.deps import RequestId, ok
from veo.authz import CurrentPrincipal, Permission, require
from veo.contracts.envelope import ApiResponse
from veo.core.settings import get_settings
from veo.db.models import PublicSharedReport
from veo.db.session import get_db
from veo.public.tokens import fingerprint, issue_token, looks_like_token
from veo.reports.router import get_report_service
from veo.reports.service import ReportNotFoundError, ReportService

__all__ = ["anonymous_router", "console_router"]

_log = logging.getLogger(__name__)

console_router = APIRouter(prefix="/reports", tags=["reports"])
anonymous_router = APIRouter(tags=["shared"])

_NOT_FOUND_KO = "공유 문서를 찾을 수 없습니다. 링크가 만료되었거나 잘못 복사되었을 수 있습니다."


class SharedReportLinkPayload(BaseModel):
    """만든 링크에 대해 화면이 알아야 할 전부."""

    share_path: str
    expires_at: datetime
    note_ko: str


@console_router.post(
    "/{report_id}/versions/{version_number}/share",
    response_model=ApiResponse[SharedReportLinkPayload],
    status_code=201,
    summary="리포트 버전의 거래처 전달 링크 발급",
    description=(
        "이 버전의 HTML 문서를 **지금 이 순간의 복사본**으로 굳혀 저장하고, 로그인 없이 "
        "열리는 링크를 돌려줍니다. 이후 무엇이 바뀌어도 링크가 여는 것은 보낸 그날의 그 "
        "문서입니다. 같은 버전에 다시 부르면 새 링크가 나옵니다 — 이전 링크도 만료까지 "
        "그대로 살아 있습니다."
    ),
    dependencies=[
        Depends(require(Permission.REPORT_READ)),
        Depends(require(Permission.REPORT_EXPORT)),
    ],
)
def share_report_version(
    report_id: uuid.UUID,
    version_number: int,
    principal: CurrentPrincipal,
    request_id: RequestId,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[ReportService, Depends(get_report_service)],
) -> ApiResponse[SharedReportLinkPayload]:
    try:
        result = service.export(
            principal=principal,
            report_id=report_id,
            version_number=version_number,
            export_format="html",
        )
    except ReportNotFoundError:
        raise HTTPException(status_code=404, detail="report version not found") from None

    settings = get_settings()
    issued = issue_token(ttl_seconds=settings.report_share_ttl_days * 86_400)
    db.add(
        PublicSharedReport(
            fingerprint=issued.fingerprint,
            html=result.body.decode("utf-8"),
            title_ko=result.filename,
            expires_at=issued.expires_at,
        )
    )
    db.flush()

    return ok(
        SharedReportLinkPayload(
            share_path=f"/shared/reports/{issued.token}",
            expires_at=issued.expires_at,
            note_ko=(
                "이 링크는 로그인 없이 열립니다. 지금 이 순간의 문서가 굳어 저장되었고, "
                "이후 재발행해도 이 링크의 내용은 바뀌지 않습니다."
            ),
        ),
        request_id,
    )


@anonymous_router.get(
    "/shared/reports/{token}",
    response_class=HTMLResponse,
    include_in_schema=False,
    summary="공유된 리포트 열람 (로그인 불필요)",
)
def read_shared_report(
    token: str, db: Annotated[Session, Depends(get_db)]
) -> HTMLResponse:
    # 모양부터 거른다 — 경로 조각이나 1MB 문자열이 해시·조회가 되기 전에 버려진다.
    if not looks_like_token(token):
        raise HTTPException(status_code=404, detail=_NOT_FOUND_KO)

    row = db.get(PublicSharedReport, fingerprint(token))
    if row is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND_KO)
    if datetime.now(UTC) >= row.expires_at:
        # 만료된 행은 읽는 자리에서 지운다 — 공유 결과 저장소와 같은 규칙.
        db.delete(row)
        db.commit()
        raise HTTPException(status_code=404, detail=_NOT_FOUND_KO)

    return HTMLResponse(
        row.html,
        headers={
            "Cache-Control": "no-store",
            # 문서는 외부 자원 없는 단일 파일 계약 — 스크립트·폼까지 잠근다.
            "Content-Security-Policy": "sandbox",
        },
    )
