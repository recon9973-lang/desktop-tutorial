"""FastAPI application factory.

OpenAPI is the single API contract: the TypeScript client is generated from it and a
contract test fails the build if the committed document and the running app disagree.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from veo import __version__
from veo.api.deps import REQUEST_ID_HEADER, build_meta, get_request_id
from veo.api.routes import meta as meta_routes
from veo.api.routes import scoring as scoring_routes
from veo.auth.resolver import install_auth
from veo.auth.router import router as auth_router
from veo.auth.throttle import AccountLockedError
from veo.authz import (
    AuthenticationError,
    OrganizationMismatch,
    PermissionDeniedError,
    TenantIsolationError,
)
from veo.competitors.router import router as competitors_router
from veo.contracts.enums import ErrorCode
from veo.contracts.envelope import ApiError, FieldError
from veo.core.settings import get_settings
from veo.credentials.cipher import assert_vault_startup_ready
from veo.credentials.router import router as credentials_router
from veo.customers.router import router as customers_router
from veo.geo.router import router as geo_router
from veo.issues.router import router as issues_router
from veo.keywords.router import router as keywords_router
from veo.lab.router import router as lab_router
from veo.organizations.router import router as organizations_router
from veo.projects.router import router as projects_router
from veo.public.router import router as public_router
from veo.reports.router import router as reports_router
from veo.seo.router import router as seo_router
from veo.sites.router import router as sites_router
from veo.users.router import router as users_router

DESCRIPTION = """\
VEO — SEO · GEO · Naver Keyword Intelligence Platform

Developed by VENOM. Research & Methodology by VEO-LAB.

측정 원칙
- SEO 준비도, GEO 준비도, 실제 AI 가시성, 네이버 키워드 수요는 각각 별도의 지표입니다.
  하나의 불투명한 총점으로 합치지 않습니다.
- 준비도 점수는 검색 순위 예측값이 아닙니다.
- 모든 점수에는 방법론 버전, 체크섬, 적용 분모, 계산 과정, 신뢰도가 함께 제공됩니다.
- '해당 없음'은 0점이 아니라 분모에서 제외되고, '측정 불가'는 실패가 아니라
  coverage와 confidence에 반영됩니다.
- 외부 제공자 자격증명이 없으면 해당 항목은 '측정 불가'가 되며, VEO는 추정값을
  실제 데이터처럼 표시하지 않습니다.
"""


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="VEO API",
        summary="SEO · GEO · Naver Keyword Intelligence Platform",
        description=DESCRIPTION,
        version=__version__,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url=None,
        contact={"name": "VENOM"},
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER],
    )

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next: Any) -> Any:
        request_id = get_request_id(request)
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        request_id = get_request_id(request)
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            error = ApiError.model_validate(exc.detail)
        else:
            error = ApiError.of(_code_for_status(exc.status_code), str(exc.detail))
        return _error_response(exc.status_code, error, request_id)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = get_request_id(request)
        field_errors = [
            FieldError(
                field=".".join(str(part) for part in err.get("loc", ())[1:]) or "body",
                code=str(err.get("type", "invalid")),
                message=str(err.get("msg", "입력값이 올바르지 않습니다.")),
            )
            for err in exc.errors()
        ]
        error = ApiError.of(
            ErrorCode.VALIDATION_FAILED,
            "입력값이 올바르지 않습니다.",
            field_errors=field_errors,
        )
        return _error_response(422, error, request_id)

    @app.exception_handler(AuthenticationError)
    async def authentication_exception_handler(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        """401 — and never more detail than that.

        Whether the token was missing, expired, tampered with, or belonged to a revoked
        session, the caller gets one message. Distinguishing them tells an attacker which
        half of a forged credential to keep working on.
        """
        if isinstance(exc, OrganizationMismatch):
            return _error_response(
                404,
                ApiError.of(ErrorCode.NOT_FOUND, "요청하신 리소스를 찾을 수 없습니다."),
                get_request_id(request),
            )
        return _error_response(
            401,
            ApiError.of(ErrorCode.UNAUTHENTICATED, "로그인이 필요합니다."),
            get_request_id(request),
        )

    @app.exception_handler(AccountLockedError)
    async def account_locked_exception_handler(
        request: Request, exc: AccountLockedError
    ) -> JSONResponse:
        """429 — too many recent sign-in failures for this identifier.

        Lockout is keyed by a hashed identifier and applies to addresses that have no
        account at all, so the response reveals nothing about whether the account exists.
        """
        request_id = get_request_id(request)
        response = _error_response(
            429,
            ApiError.of(
                ErrorCode.RATE_LIMITED,
                "로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.",
                retryable=True,
                retry_after_seconds=int(exc.retry_after_seconds),
            ),
            request_id,
        )
        response.headers["Retry-After"] = str(int(exc.retry_after_seconds))
        return response

    @app.exception_handler(PermissionDeniedError)
    async def permission_exception_handler(
        request: Request, exc: PermissionDeniedError
    ) -> JSONResponse:
        """403 — the caller is known, they simply may not do this.

        The missing permission is named because it is not a secret and it makes support
        tractable. The caller's identity and organization are not echoed back.
        """
        missing = ", ".join(p.value for p in exc.permissions)
        return _error_response(
            403,
            ApiError.of(
                ErrorCode.PERMISSION_DENIED,
                f"이 작업을 수행할 권한이 없습니다. (필요 권한: {missing})",
            ),
            get_request_id(request),
        )

    @app.exception_handler(TenantIsolationError)
    async def tenant_isolation_exception_handler(
        request: Request, exc: TenantIsolationError
    ) -> JSONResponse:
        """500 — reaching this is a bug in VEO, not bad input.

        A query got as far as execution without its organization filter. Fail the request
        loudly rather than return rows, and keep the internal detail out of the response.
        """
        request_id = get_request_id(request)
        logging.getLogger("veo.security").error(
            "tenant isolation guard tripped", extra={"request_id": request_id}, exc_info=exc
        )
        return _error_response(
            500,
            ApiError.of(
                ErrorCode.INTERNAL_ERROR,
                "요청을 처리하지 못했습니다. 문제가 계속되면 지원팀에 문의해 주세요.",
                internal_error_ref=request_id,
            ),
            request_id,
        )

    # Refuse to start on a cipher backend that is not authenticated AES outside
    # local/test. A credential vault that quietly degrades is worse than one that
    # will not boot.
    assert_vault_startup_ready(settings)

    # Teach the application how to recognise a caller. Without this every guarded route
    # fails closed, which is the right behaviour for a misconfigured deployment.
    install_auth(app)

    api_prefix = settings.api_prefix
    app.include_router(meta_routes.router, prefix=api_prefix)
    app.include_router(scoring_routes.router, prefix=api_prefix)
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(organizations_router, prefix=api_prefix)
    app.include_router(customers_router, prefix=api_prefix)
    app.include_router(projects_router, prefix=api_prefix)
    app.include_router(sites_router, prefix=api_prefix)
    app.include_router(credentials_router, prefix=api_prefix)
    app.include_router(geo_router, prefix=api_prefix)
    app.include_router(keywords_router, prefix=api_prefix)
    app.include_router(seo_router, prefix=api_prefix)
    app.include_router(competitors_router, prefix=api_prefix)
    app.include_router(issues_router, prefix=api_prefix)
    app.include_router(lab_router, prefix=api_prefix)
    app.include_router(reports_router, prefix=api_prefix)
    app.include_router(users_router, prefix=api_prefix)

    # The public surface is mounted at its own root, deliberately outside ``api_prefix``.
    # Every router above requires a principal and belongs to a tenant; this one has
    # neither. Keeping the two apart in the URL space means an operator can tell from the
    # path alone whether a request was authenticated — which matters when the access log
    # is the only evidence left — and lets a proxy apply different rules to each without
    # having to enumerate route names.
    app.include_router(public_router)

    return app


def _error_response(status_code: int, error: ApiError, request_id: str) -> JSONResponse:
    body = {
        "data": None,
        "error": error.model_dump(mode="json"),
        "meta": build_meta(request_id).model_dump(mode="json"),
    }
    return JSONResponse(
        status_code=status_code, content=body, headers={REQUEST_ID_HEADER: request_id}
    )


def _code_for_status(status_code: int) -> ErrorCode:
    return {
        401: ErrorCode.UNAUTHENTICATED,
        403: ErrorCode.PERMISSION_DENIED,
        404: ErrorCode.NOT_FOUND,
        409: ErrorCode.CONFLICT,
        422: ErrorCode.VALIDATION_FAILED,
        429: ErrorCode.RATE_LIMITED,
    }.get(status_code, ErrorCode.INTERNAL_ERROR)


app = create_app()
