"""``/medical`` — 의료광고 원고 검수.

검수는 순수 함수(:mod:`veo.medical.review`)이고, 이 라우터는 그 앞의 문일 뿐이다.
저장하지 않는다 — 원고는 대행사 고객의 미발행 문안이라, 남기는 순간 우리가 지킬
것이 하나 늘어난다. 기록이 필요해지면 그때 계약을 다시 정한다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from veo.api.deps import RequestId, ok
from veo.authz import Permission, Principal
from veo.contracts.envelope import ApiResponse
from veo.medical.review import DISCLAIMER_KO, review_copy
from veo.organizations.http import guard

__all__ = ["router"]

router = APIRouter(prefix="/medical", tags=["medical"])

Reviewer = Annotated[Principal, Depends(guard(Permission.SCAN_READ))]


class CopyReviewRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50_000, description="검수할 원고 전문입니다.")


class MedicalFindingPayload(BaseModel):
    rule_id: str
    category_ko: str
    guidance_ko: str
    reference_ko: str
    excerpt: str
    offset: int | None


class CopyReviewPayload(BaseModel):
    findings: list[MedicalFindingPayload]
    #: 검토 신호이지 법률 판단이 아니라는 사실 — 화면은 이 문장을 그대로 싣는다.
    disclaimer_ko: str
    reviewed_chars: int


@router.post(
    "/copy-reviews",
    response_model=ApiResponse[CopyReviewPayload],
    summary="의료광고 원고 검수 — 위반 판정이 아니라 검토 신호",
    description=(
        "원고 텍스트를 의료법 제56조의 금지 유형 규칙에 대고, 사람이 반드시 읽어 봐야 "
        "할 표현을 근거 조항과 함께 표시합니다. 점수는 없습니다 — 숫자를 붙이는 순간 "
        "'몇 점이면 안전'이라는, 누구도 보증할 수 없는 읽기가 생깁니다. 원고는 저장하지 "
        "않습니다."
    ),
)
def review_medical_copy(
    payload: CopyReviewRequest, principal: Reviewer, request_id: RequestId
) -> ApiResponse[CopyReviewPayload]:
    findings = review_copy(payload.text)
    return ok(
        CopyReviewPayload(
            findings=[
                MedicalFindingPayload(
                    rule_id=item.rule_id,
                    category_ko=item.category_ko,
                    guidance_ko=item.guidance_ko,
                    reference_ko=item.reference_ko,
                    excerpt=item.excerpt,
                    offset=item.offset,
                )
                for item in findings
            ],
            disclaimer_ko=DISCLAIMER_KO,
            reviewed_chars=len(payload.text),
        ),
        request_id,
    )
