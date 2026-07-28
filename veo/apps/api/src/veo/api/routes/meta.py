"""Health and provider-transparency endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from veo import __version__
from veo.api.deps import RequestId, ok
from veo.api.schemas import (
    HealthPayload,
    ProviderStatus,
    ProviderStatusPayload,
)
from veo.contracts.enums import ProviderState
from veo.contracts.envelope import ApiResponse
from veo.core.settings import get_provider_credentials, get_settings

router = APIRouter(tags=["meta"])

_STATE_REASONS_KO: dict[ProviderState, str] = {
    ProviderState.ENABLED: "자격증명이 설정되어 실제 데이터를 조회합니다.",
    ProviderState.DISABLED_NO_CREDENTIAL: (
        "자격증명이 없어 비활성 상태입니다. 관련 검사는 '측정 불가'로 표시되며 "
        "VEO는 추정값을 실제 데이터처럼 표시하지 않습니다."
    ),
    ProviderState.DISABLED_INVALID_CREDENTIAL: (
        "자격증명 자리에 값이 있지만 사용할 수 없는 값입니다(예: 배포 도구가 남긴 "
        "'[SENSITIVE]' 같은 자리표시자). 비어 있는 것과는 처방이 다릅니다 — 잘못 채워진 "
        "값을 걷어내고 실제 키를 넣어야 합니다. 관련 검사는 '측정 불가'로 표시됩니다."
    ),
    ProviderState.NOT_AVAILABLE: (
        "이 제공자는 해당 기능을 공개 API로 제공하지 않습니다. 자격증명을 넣어도 "
        "달라지지 않으며, 필요한 값은 제공자 콘솔에서 직접 확인해야 합니다."
    ),
    ProviderState.DISABLED_BY_CONFIG: "설정에 의해 비활성화되어 있습니다.",
    ProviderState.DEGRADED: "응답이 불안정해 일부 결과가 누락될 수 있습니다.",
    ProviderState.CIRCUIT_OPEN: "연속 실패로 호출을 일시 차단했습니다.",
}

#: Adding a ProviderState without a reason here used to 500 this endpoint. A status page
#: that dies because it met a status it did not recognise is the wrong failure.
_UNKNOWN_STATE_REASON_KO = "이 상태에 대한 설명이 아직 등록되지 않았습니다."


@router.get("/health", response_model=ApiResponse[HealthPayload], summary="서비스 상태 확인")
def health(request_id: RequestId) -> ApiResponse[HealthPayload]:
    settings = get_settings()
    return ok(
        HealthPayload(
            status="ok",
            app_name=settings.app_name,
            tagline=settings.app_tagline,
            developed_by=settings.developed_by,
            methodology_by=settings.methodology_by,
            environment=settings.environment,
            version=__version__,
        ),
        request_id,
    )


@router.get(
    "/providers",
    response_model=ApiResponse[ProviderStatusPayload],
    summary="외부 데이터 제공자 연동 상태",
    description=(
        "각 외부 제공자의 연동 상태를 그대로 보고합니다. 자격증명이 없으면 비활성 상태로 "
        "표시하며, 해당 제공자에 의존하는 검사 결과는 실패가 아니라 '측정 불가'가 됩니다."
    ),
)
def providers(request_id: RequestId) -> ApiResponse[ProviderStatusPayload]:
    credentials = get_provider_credentials()
    statuses = [
        ProviderStatus(
            provider=name,
            state=state,
            reason_ko=_STATE_REASONS_KO.get(state, _UNKNOWN_STATE_REASON_KO),
        )
        for name, state in sorted(credentials.states().items())
    ]
    return ok(ProviderStatusPayload(providers=statuses), request_id)
