"""``/public/v1`` — the unauthenticated front door. **Not mounted.**

``veo.api.app`` belongs to the integration maintainer, so this router is defined and
tested here and included there when they are ready. See ``INTEGRATION_REQUEST.md``.

Every other VEO router fails closed without a principal. This one has no principal at
all, on purpose: a clinic owner types a URL, gets a real diagnosis, and becomes a lead.
Three consequences follow, and they are why this file looks different from its
neighbours.

* **No tenant reachability.** No route here takes a database session or a principal, so
  there is no code path from an anonymous request to a customer's row. That is asserted
  in ``tests/public/test_isolation.py`` by walking each route's dependency graph.
* **Refuse before you work.** The rate limit is charged inside the service, before the
  fetch, so a refused request costs one dictionary lookup rather than an outbound
  request to somebody else's server.
* **The caller's address is what the socket says.** ``X-Forwarded-For`` is *not* read.
  A public endpoint that trusts a caller-supplied header for its rate-limit key has no
  rate limit at all. Behind a proxy this needs the ASGI server configured to rewrite
  ``request.client`` from a trusted hop; that is deployment configuration and it is
  filed as an integration request.
"""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from veo.api.deps import REQUEST_ID_HEADER, RequestId, build_meta, ok
from veo.contracts.enums import ErrorCode
from veo.contracts.envelope import ApiError, ApiResponse
from veo.core.settings import get_settings
from veo.public.leads import InMemoryLeadStore, LeadStore, capture_lead
from veo.public.limits import Bucket, InMemoryRateLimiter, LimitScope, RateLimiter
from veo.public.schemas import (
    PublicGeoScanPayload,
    PublicKeywordLookupPayload,
    PublicKeywordLookupRequest,
    PublicLeadPayload,
    PublicLeadRequest,
    PublicResultPayload,
    PublicScanRequest,
    PublicSeoScanPayload,
)
from veo.public.service import (
    InMemoryPublicResultStore,
    PublicRefusal,
    PublicResultStore,
    PublicScanService,
)

__all__ = [
    "SESSION_HEADER",
    "get_lead_store",
    "get_public_service",
    "get_rate_limiter",
    "get_result_store",
    "router",
]

router = APIRouter(prefix="/public/v1", tags=["public"])

#: The browser's own identifier for one visitor. Opaque to VEO — it is a rate-limit key
#: and nothing else, so it must never be an email, a phone number or anything a person
#: could be recognised from.
SESSION_HEADER = "X-Veo-Public-Session"

_SESSION_SHAPE = re.compile(r"\A[A-Za-z0-9_-]{4,64}\Z")

# --------------------------------------------------------------------------- #
# Process-wide singletons
# --------------------------------------------------------------------------- #

_LIMITER = InMemoryRateLimiter()
_RESULTS = InMemoryPublicResultStore()
_LEADS = InMemoryLeadStore()


def get_rate_limiter() -> RateLimiter:
    """One limiter per process. See the module's limitation note in ``limits.py``."""
    return _LIMITER


def get_result_store() -> PublicResultStore:
    return _RESULTS


def get_lead_store() -> LeadStore:
    return _LEADS


def get_public_service(
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    results: Annotated[PublicResultStore, Depends(get_result_store)],
) -> PublicScanService:
    """Build the service for one request.

    Only the limiter and the store are handed in. The service builds its own fetcher
    around the default :class:`~veo.common.security.url_guard.UrlGuard` — which resolves
    through the system resolver and refuses everything that is not a public address —
    wrapped in the guard that charges the target-host budget per outbound request.

    Handing a ready-made fetcher in from here is exactly what the service now refuses to
    accept: one assembled without that wrapper would look identical at the call site and
    silently switch off the control that stops VEO being aimed at a third party.
    """
    return PublicScanService(limiter=limiter, results=results)


ServiceDep = Annotated[PublicScanService, Depends(get_public_service)]
LeadStoreDep = Annotated[LeadStore, Depends(get_lead_store)]
LimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]


# --------------------------------------------------------------------------- #
# Caller identity — an address and an opaque session, and nothing else
# --------------------------------------------------------------------------- #


def client_address(request: Request) -> str:
    """The peer address of the socket.

    ``X-Forwarded-For`` is deliberately ignored: it is written by the caller, and a
    rate-limit key an attacker can choose is not a rate limit.
    """
    return request.client.host if request.client else "unknown"


def session_key(
    request: Request,
    session_header: Annotated[str | None, Header(alias=SESSION_HEADER)] = None,
) -> str:
    """The session bucket's key: the supplied id, or the address when none is sent.

    Falling back to the address rather than to a shared constant matters — a shared
    default would put every anonymous visitor in one bucket and let one of them lock
    out all the others.
    """
    if session_header is None:
        return f"ip:{client_address(request)}"
    if not _SESSION_SHAPE.fullmatch(session_header):
        raise _http_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorCode.VALIDATION_FAILED,
            "세션 식별자 형식이 올바르지 않습니다.",
        )
    return f"sid:{session_header}"


ClientIp = Annotated[str, Depends(client_address)]
SessionId = Annotated[str, Depends(session_key)]


def _http_error(
    status_code: int, code: ErrorCode, message: str, **kwargs: object
) -> HTTPException:
    error = ApiError.of(code, message, **kwargs)
    return HTTPException(status_code=status_code, detail=error.model_dump(mode="json"))


def refusal_response(refusal: PublicRefusal, request_id: str) -> JSONResponse:
    """Render a refusal as the platform envelope, in the route rather than in a handler.

    Built here, and not raised as an ``HTTPException``, for one reason: ``Retry-After``.
    A 429 without it tells a well-behaved client nothing about when to come back, and
    the application's generic exception handler rebuilds the body without the headers
    the exception carried. Returning the response directly keeps the wait attached to
    the answer, and it keeps this router self-contained for whoever mounts it.
    """
    headers = {REQUEST_ID_HEADER: request_id}
    if refusal.error.retry_after_seconds:
        headers["Retry-After"] = str(refusal.error.retry_after_seconds)
    return JSONResponse(
        status_code=refusal.status_code,
        content={
            "data": None,
            "error": refusal.error.model_dump(mode="json"),
            "meta": build_meta(request_id).model_dump(mode="json"),
        },
        headers=headers,
    )


# --------------------------------------------------------------------------- #
# Scans
# --------------------------------------------------------------------------- #


@router.post(
    "/seo-scans",
    response_model=ApiResponse[PublicSeoScanPayload],
    summary="무료 SEO 준비도 진단 (로그인 불필요)",
    description=(
        "입력한 주소를 직접 수집해 SEO 준비도를 채점합니다. 채점 엔진과 발행된 명세는 유료 "
        "진단과 동일하며, 무료 진단은 페이지 수와 외부 연동만 축소합니다. 측정하지 못한 항목은 "
        "감점하지 않고 측정 범위(coverage)와 신뢰도(confidence)에 반영합니다. "
        "응답에는 근거 원문·페이지 URL 목록이 포함되지 않습니다."
    ),
)
def run_public_seo_scan(
    payload: PublicScanRequest,
    service: ServiceDep,
    client_ip: ClientIp,
    session_id: SessionId,
    request_id: RequestId,
) -> ApiResponse[PublicSeoScanPayload] | JSONResponse:
    try:
        result = service.run_seo_scan(
            urls=payload.urls, client_ip=client_ip, session_id=session_id
        )
    except PublicRefusal as refusal:
        return refusal_response(refusal, request_id)
    return ok(
        result,
        request_id,
        spec_id=result.score.spec_id,
        spec_version=result.score.spec_version,
        spec_checksum=result.score.spec_checksum,
    )


@router.post(
    "/geo-readiness-scans",
    response_model=ApiResponse[PublicGeoScanPayload],
    summary="무료 GEO 준비도 진단 (로그인 불필요)",
    description=(
        "AI 답변 엔진이 페이지에 접근·추출·검증할 수 있는 구조적 준비도를 채점합니다. "
        "준비도 점수와 노출 차단 상태는 분리된 두 블록으로 돌려주며 하나의 점수로 합치지 "
        "않습니다. 실제 AI 답변에서의 노출 결과는 별도의 관측 엔진이 보고합니다."
    ),
)
def run_public_geo_scan(
    payload: PublicScanRequest,
    service: ServiceDep,
    client_ip: ClientIp,
    session_id: SessionId,
    request_id: RequestId,
) -> ApiResponse[PublicGeoScanPayload] | JSONResponse:
    try:
        result = service.run_geo_readiness(
            urls=payload.urls, client_ip=client_ip, session_id=session_id
        )
    except PublicRefusal as refusal:
        return refusal_response(refusal, request_id)
    return ok(
        result,
        request_id,
        spec_id=result.readiness.spec_id,
        spec_version=result.readiness.spec_version,
        spec_checksum=result.readiness.spec_checksum,
    )


@router.post(
    "/keyword-lookups",
    response_model=ApiResponse[PublicKeywordLookupPayload],
    summary="무료 네이버 키워드 조회 (로그인 불필요)",
    description=(
        "네이버 검색광고가 공개하는 월간 검색수를 그대로 보여 줍니다. 연동이 없거나 제공자가 "
        "값을 주지 않으면 숫자 대신 상태와 사유를 돌려주며, 추정값을 실제 수치처럼 표시하지 "
        "않습니다. 조회 기록은 저장하지 않습니다."
    ),
)
def run_public_keyword_lookup(
    payload: PublicKeywordLookupRequest,
    service: ServiceDep,
    client_ip: ClientIp,
    session_id: SessionId,
    request_id: RequestId,
) -> ApiResponse[PublicKeywordLookupPayload] | JSONResponse:
    try:
        result = service.lookup_keywords(
            keywords=payload.keywords, client_ip=client_ip, session_id=session_id
        )
    except PublicRefusal as refusal:
        return refusal_response(refusal, request_id)
    return ok(result, request_id)


@router.get(
    "/results/{token}",
    response_model=ApiResponse[PublicResultPayload],
    summary="공유된 무료 진단 결과 열람",
    description=(
        "발급된 공유 토큰으로 저장된 진단 결과를 다시 봅니다. 토큰은 만료되며, 없는 토큰과 "
        "만료된 토큰은 똑같은 응답을 돌려줍니다 — 어떤 토큰이 실제로 존재했는지 확인해 주는 "
        "창구가 되지 않기 위해서입니다."
    ),
)
def read_public_result(
    token: str,
    service: ServiceDep,
    request_id: RequestId,
) -> ApiResponse[PublicResultPayload] | JSONResponse:
    try:
        result = service.read_result(token)
    except PublicRefusal as refusal:
        return refusal_response(refusal, request_id)
    return ok(result, request_id)


# --------------------------------------------------------------------------- #
# Leads
# --------------------------------------------------------------------------- #


@router.post(
    "/leads",
    response_model=ApiResponse[PublicLeadPayload],
    status_code=status.HTTP_201_CREATED,
    summary="무료 진단 상담 요청 접수",
    description=(
        "회신에 필요한 최소한의 정보만 받습니다 — 이름과 연락처(전화 또는 이메일), 선택으로 "
        "홈페이지 주소. 그 외의 항목은 스키마에서 거부합니다. 응답에는 실제로 저장한 항목이 "
        "무엇인지 한국어로 그대로 적혀 있습니다. 광고·마케팅 수신 동의는 받지도 저장하지도 "
        "않습니다."
    ),
)
def submit_public_lead(
    payload: PublicLeadRequest,
    store: LeadStoreDep,
    limiter: LimiterDep,
    client_ip: ClientIp,
    session_id: SessionId,
    request_id: RequestId,
) -> ApiResponse[PublicLeadPayload] | JSONResponse:
    limit = get_settings().public_rate_limit_per_hour
    decision = limiter.acquire(
        [
            Bucket(
                scope=LimitScope.CLIENT_IP, key=client_ip, limit=limit, window_seconds=3600
            ),
            Bucket(
                scope=LimitScope.SESSION, key=session_id, limit=limit, window_seconds=3600
            ),
        ]
    )
    if not decision.allowed:
        return refusal_response(PublicRefusal(429, decision.as_api_error()), request_id)
    return ok(capture_lead(payload, store=store), request_id)
