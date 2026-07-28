# 통합 요청 — Phase 1 리소스 라우터 (organizations / customers / projects / sites)

작성: 리소스 담당 워커. 대상: 통합 담당자(`veo.api.app`, `veo.authz`, `veo.contracts` 소유자).

리소스 워커는 `apps/api/src/veo/api/app.py`를 편집하지 않았습니다. 아래 두 건은 통합
담당자만 반영할 수 있는 변경입니다.

---

## 1. 라우터 마운트 (필수)

네 개의 `APIRouter`가 준비되어 있으며 어디에도 마운트되어 있지 않습니다.

```python
from veo.customers.router import router as customers_router
from veo.organizations.router import router as organizations_router
from veo.projects.router import router as projects_router
from veo.sites.router import router as sites_router

app.include_router(organizations_router, prefix=api_prefix)
app.include_router(customers_router, prefix=api_prefix)
app.include_router(projects_router, prefix=api_prefix)
app.include_router(sites_router, prefix=api_prefix)
```

마운트하면 `apps/api/openapi.json`이 달라지므로 `tests/contract/test_openapi_contract.py`가
실패합니다. `scripts/export_openapi.py`로 문서를 다시 뽑아 커밋해 주세요. 리소스 워커는
`openapi.json`을 소유하지 않아 재생성하지 않았습니다.

`tests/resources/conftest.py`의 `app` 픽스처는 이미 마운트된 경로가 있으면 다시
`include_router`하지 않으므로, 통합 후에도 테스트는 그대로 통과합니다.

경로 요약 (모두 `settings.api_prefix` 하위):

| 경로 | 메서드 | 권한 |
| --- | --- | --- |
| `/organizations/current`, `/organizations/{id}` | GET | `ORG_READ` |
| `/customers`, `/customers/{id}` | GET / POST / PATCH / DELETE | `CUSTOMER_READ`, `CUSTOMER_WRITE` |
| `/projects`, `/projects/{id}` | GET / POST / PATCH / DELETE | `PROJECT_READ`, `PROJECT_WRITE` |
| `/sites`, `/sites/{id}` | GET / POST / PATCH / DELETE | `SITE_READ`, `SITE_WRITE` |

Phase 1에서 조직은 읽기 전용이며, 모든 조직을 나열하는 엔드포인트는 없습니다.

---

## 2. `AuthorizationError` 전역 예외 핸들러 (권장)

현재 `create_app()`에는 `StarletteHTTPException`과 `RequestValidationError` 핸들러만
등록되어 있습니다. `veo.authz`가 던지는 예외는 어느 것도 처리되지 않습니다.

- `PermissionDeniedError` → 처리되지 않으면 500
- `AuthenticationError` (및 `OrganizationMismatch`) → 처리되지 않으면 500
- `TenantIsolationError` → 500이 **맞습니다**. 이건 VEO의 버그이지 호출자의 잘못이
  아니므로 조용히 4xx로 감싸면 안 됩니다.

권한 실패가 500으로 나가면 쓰기 엔드포인트에서 "권한 없음"과 "저장 실패"를 구분할 수
없습니다. 그래서 리소스 라우터는 `veo.organizations.http.guard()`를 씁니다 — 이 함수는
권한 매트릭스를 재정의하지 않고 `veo.authz.require()`를 그대로 호출한 뒤,
`PermissionDeniedError`만 표준 `ApiError` 봉투를 실은 403 `HTTPException`으로 옮깁니다.

아래처럼 앱 차원 핸들러가 등록되면 `guard()`는 `require()`를 감싸는 얇은 통과층이 되고,
리소스 워커가 정리하겠습니다.

```python
@app.exception_handler(PermissionDeniedError)
async def permission_denied_handler(request: Request, exc: PermissionDeniedError) -> JSONResponse:
    request_id = get_request_id(request)
    error = ApiError.of(ErrorCode.PERMISSION_DENIED, "이 작업을 수행할 권한이 없습니다.")
    return _error_response(403, error, request_id)


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    request_id = get_request_id(request)
    error = ApiError.of(ErrorCode.UNAUTHENTICATED, "인증이 필요합니다.")
    return _error_response(401, error, request_id)
```

`OrganizationMismatch`는 `AuthenticationError`의 하위 클래스지만 401이 아니라 404여야
합니다(자기 클래스 docstring이 그렇게 지시합니다). 리소스 라우터는 이 예외에 의존하지
않고 서비스 계층에서 `None`을 반환해 404를 만들기 때문에 지금은 문제가 없습니다. 다만
다른 워커가 `require_same_organization()`을 직접 쓰기 시작하면, 위 핸들러보다 **먼저**
`OrganizationMismatch` 전용 404 핸들러를 등록해야 401로 새지 않습니다.

---

## 3. 계약 변경 요청 — 없음

`Permission`, `Role`, `ErrorCode`, `ApiResponse`, `PagedResponse`, `PageInfo`,
`tenant_select`, `assert_tenant_scoped`, `identity.py`의 테이블 정의는 모두 그대로
사용했습니다. 컬럼 추가·변경, 마이그레이션, 새 의존성은 없습니다.

참고로 남기는 관찰 두 가지입니다. 지금 결정할 필요는 없습니다.

- `Project`와 `Site`에는 `is_active`가 없습니다. 두 테이블에는 `scans`, `evidence`,
  `score_results`, `url_records`, `reports`가 `ON DELETE CASCADE`로 매달려 있어 삭제가
  곧 불변 측정 이력의 삭제가 됩니다. 그래서 `DELETE`는 409를 반환합니다(단, 다른 조직의
  행이면 409가 아니라 404 — 409는 그 행이 실재한다는 확인이 됩니다). 보관(archive)
  기능이 필요해지면 `is_active` 또는 `archived_at` 컬럼 추가가 선행되어야 합니다.
- `Organization`에는 `organization_id` 컬럼이 없어 `tenant_select()`가 이 모델을
  거부합니다. 의도된 동작이며, `veo/organizations/service.py`는 요청에서 조직 ID를 받지
  않고 `principal.organization_id`만 조회해 같은 보호를 얻습니다.
