# 통합 요청 — 이슈 수명주기 (`veo.issues`)

작성: 이슈 담당 워커. 대상: 통합 담당자(`veo.api.app`, `veo.contracts`, `veo.db`, `openapi.json`,
`packages/shared-types` 소유자).

이슈 워커는 `apps/api/src/veo/issues/**`와 `apps/api/tests/issues/**` 밖의 어떤 파일도
편집하지 않았습니다. 컬럼 추가·변경, 마이그레이션, 새 의존성은 없습니다.

이 모듈이 지키는 규칙 하나만 기억하시면 됩니다.

> **이슈는 사람이 '완료'를 누를 때가 아니라, 다시 측정했을 때 닫힙니다.**

사람은 "무언가를 바꿨다"(`FIX_CLAIMED`)까지만 말할 수 있고, "이제 통과한다"는
표적 재측정 결과만 말할 수 있습니다(`VERIFIED_RESOLVED`). 두 상태는 절대 하나로
합쳐지면 안 됩니다.

---

## 1. 라우터 마운트 (필수)

`APIRouter` 하나가 준비되어 있으며 어디에도 마운트되어 있지 않습니다.

```python
from veo.issues.router import router as issues_router

app.include_router(issues_router, prefix=api_prefix)
```

마운트하면 `apps/api/openapi.json`이 달라져 `tests/contract/test_openapi_contract.py`가
실패합니다. 아래 순서로 산출물을 다시 뽑아 커밋해 주세요. 이슈 워커는 `openapi.json`과
`packages/**`를 소유하지 않아 재생성하지 않았습니다.

```
python scripts/export_openapi.py
python scripts/export_shared_types.py
pnpm --filter @veo/api-client generate
```

`tests/contract/test_router_mounting.py`의 `EXPECTED_MOUNTS`에 다음 줄을 추가해 주시면
회귀를 잡을 수 있습니다.

```python
"issues": "/api/issues",
```

`tests/issues/conftest.py`의 `app` 픽스처는 생성된 OpenAPI 문서를 보고 이미 마운트된
경우 다시 `include_router`하지 않으므로, 통합 후에도 테스트는 그대로 통과합니다.

경로 요약 (모두 `settings.api_prefix` 하위):

| 경로 | 메서드 | 권한 | 비고 |
| --- | --- | --- | --- |
| `/issues` | GET | `ISSUE_READ` | 상태·심각도·담당 직군·검사 ID·담당자 필터 |
| `/issues/{id}` | GET | `ISSUE_READ` | 전이 이력·재측정 이력·재발 주기 포함 |
| `/issues/{id}/assignee` | POST | `ISSUE_WRITE` | 같은 조직 구성원만 지정 가능 |
| `/issues/{id}/transitions` | POST | `ISSUE_WRITE` | 담당자 조작. `VERIFIED_RESOLVED` 불가 |
| `/issues/{id}/verification-requests` | POST | `ISSUE_WRITE` | 표적 재검사 요청 |
| `/issues/{id}/verification-results` | POST | `ISSUE_WRITE` | 판정은 요청 본문이 아니라 저장된 검사 결과에서 도출 |

---

## 2. 계약 변경 요청 — `veo.contracts.enums.IssueState`

**지금 결정이 필요한 유일한 항목입니다.**

`veo/contracts/enums.py`의 `IssueState`는 이 모듈이 구현한 상태 기계와 일치하지 않습니다.
이슈 워커는 `veo/contracts/**`를 소유하지 않아 수정하지 않았고, 대신
`veo.issues.lifecycle.IssueState`를 별도로 정의했습니다. `issues.state` 컬럼은
`String(32)`이고 DB 제약이 없어 저장에는 문제가 없지만, **`packages/shared-types`로
내보내지는 값과 실제 저장 값이 다릅니다.**

| 현재 `contracts.IssueState` | `issues.lifecycle.IssueState` | 차이 |
| --- | --- | --- |
| `OPEN` | `OPEN` | 동일 |
| `ACKNOWLEDGED` | `ACKNOWLEDGED` | 동일 |
| `IN_PROGRESS` | `IN_PROGRESS` | 동일 |
| `FIXED_PENDING_VERIFICATION` | `FIX_CLAIMED` | 이름만 다름 |
| — | `VERIFYING` | **없음** — 재검사를 요청했지만 결과가 아직 없는 상태 |
| `VERIFIED_RESOLVED` | `VERIFIED_RESOLVED` | 동일 |
| — | `VERIFICATION_FAILED` | **없음** — 재측정에서도 실패한 상태 |
| `WONT_FIX` | `WONT_FIX` | 동일 |
| `REGRESSED` | `RECURRED` | 이름만 다름 |

`VERIFYING`과 `VERIFICATION_FAILED`가 없는 것이 실질적인 문제입니다.

- `VERIFYING`이 없으면 "재검사를 요청함"과 "수정했다고 보고함"을 구분할 수 없고,
  그러면 재측정 결과를 받을 자격이 있는 이슈를 상태만으로 판별할 수 없습니다.
  이 모듈은 `VERIFYING`이 아닌 이슈의 재측정 결과 기록을 거부하는데, 그 거부가
  "사람이 통과 판정을 만들어 넣는" 경로를 막는 마지막 잠금장치입니다.
- `VERIFICATION_FAILED`가 없으면 실패한 재측정이 `OPEN`이나
  `FIXED_PENDING_VERIFICATION`으로 되돌아가야 하는데, 둘 다 거짓말입니다. 전자는
  "측정해서 아니었다"는 사실을 지우고, 후자는 실패를 수정 보고처럼 보이게 합니다.

요청: `contracts.enums.IssueState`를 아래로 교체하고 `scripts/export_shared_types.py`를
다시 실행해 주세요. 그러면 `veo/issues/lifecycle.py`의 `IssueState`를 지우고
`contracts`의 것을 그대로 쓰도록 이슈 워커가 정리하겠습니다.

```python
class IssueState(StrEnum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    FIX_CLAIMED = "FIX_CLAIMED"                    # 사람이 '바꿨다'고 보고한 상태
    VERIFYING = "VERIFYING"                        # 표적 재검사 요청됨, 결과 대기
    VERIFIED_RESOLVED = "VERIFIED_RESOLVED"        # 재측정 통과가 확인된 상태
    VERIFICATION_FAILED = "VERIFICATION_FAILED"    # 재측정에서도 실패
    WONT_FIX = "WONT_FIX"
    RECURRED = "RECURRED"
```

기존 값을 쓰는 저장 데이터는 아직 없습니다(이 모듈이 `issues` 테이블의 첫 작성자입니다).
`FIXED_PENDING_VERIFICATION` / `REGRESSED`를 유지해야 한다면 이름만 그쪽에 맞추고
`VERIFYING` · `VERIFICATION_FAILED` 두 개만 추가해도 됩니다 — 필요한 건 이름이 아니라
**상태의 개수**입니다.

---

## 3. 스키마 관찰 (지금 결정 불필요)

컬럼을 추가하지 않았고, 아래는 기록으로만 남깁니다.

1. **`issues.sample_urls`에는 표본이 아니라 영향 URL 전체가 들어갑니다.**
   이슈 지문은 `(check_id, 정규화된 영향 URL 집합)`이고 별도 컬럼이 없으므로, 행에서
   지문을 다시 계산할 수 있어야 두 번째 사본이 생기지 않습니다. 컬럼 이름이 `sample_`인
   것이 오해를 부를 수 있어 언젠가 `affected_urls`로 바꾸면 좋겠습니다(이름만 변경).
   URL이 매우 많은 사이트 전체 이슈에서 이 컬럼이 커질 수 있습니다. 상한이 필요해지면
   `issues.fingerprint` 컬럼(인덱스 포함)을 추가하는 편이 낫습니다 — 지금은
   `(project_id, check_id)`로 후보를 좁힌 뒤 파이썬에서 비교합니다.

2. **`audit_logs`에는 단조 증가 순번이 없습니다.** PostgreSQL의 `now()`는 트랜잭션
   시각이므로, 한 트랜잭션 안에서 커밋된 여러 전이는 같은 `created_at`을 가지며 서로
   간의 순서가 정해지지 않습니다. 요청이 다르면 항상 올바르게 정렬됩니다. 이슈 상세의
   이력 표시 품질 문제이며 상태 자체에는 영향이 없습니다. 필요해지면
   `audit_logs`에 `BIGSERIAL` 순번 컬럼 하나면 해결됩니다.

3. **`verification_runs.outcome`에는 CHECK 제약이 없습니다.** 이 모듈은
   `RESOLVED` / `STILL_FAILING` / `INCONCLUSIVE`만 씁니다(컬럼 주석과 동일).
   다른 패키지가 이 테이블에 쓰기 시작하면 제약을 거는 편이 안전합니다.

4. **`issues.regression_count`가 재발 횟수입니다.** 각 주기의 시각은
   `verification_runs`(해결 시점)와 `audit_logs`의 `issue.recurred` 행(재발 시점)에서
   재구성합니다. 요약값을 따로 저장하지 않으므로 카운트와 타임라인이 어긋날 수 없습니다.

---

## 4. 아직 아무도 호출하지 않는 진입점

`veo.issues.service.ingest_drafts(...)`가 수집기의 `IssueDraft`를 이슈 행으로 만드는
유일한 경로입니다. `veo/seo/service.py`와 `veo/geo/service.py`는 현재 `IssueDraft`를
반환만 하고 저장하지 않으므로, 스캔 파이프라인 소유자가 스캔 성공 직후 아래처럼 불러
주셔야 이슈가 생깁니다. 이슈 워커는 두 서비스를 소유하지 않아 연결하지 않았습니다.

```python
from veo.issues import service as issues

issues.ingest_drafts(
    session,
    principal,
    project_id=project.id,
    scan_run_id=scan_run.id,
    drafts=result.issues,      # SeoScanResult.issues / GeoReadinessReport 의 IssueDraft들
    spec=context.spec,         # 심각도는 여기서만 옵니다
    request_id=request_id,
)
```

호출 시 동작:

- 같은 지문의 이슈가 이미 있으면 **새 행을 만들지 않고** 근거·마지막 관측 실행만
  갱신합니다.
- 그 이슈가 `VERIFIED_RESOLVED` 였다면 재발로 기록되고 `RECURRED`로 이동합니다.
- 명세에 없는 `check_id`는 `ReferenceNotFoundError`로 거절합니다. 심각도를 정할 근거가
  없는 발견을 저장하면 곧 하드코딩된 심각도가 생기기 때문입니다.

표적 재검사를 실제로 실행하는 워커도 아직 없습니다.
`POST /issues/{id}/verification-requests`가 돌려주는 `scan_parameters`
(`{"scope": "TARGETED_REVERIFICATION", "check_ids": [...], "urls": [...], ...}`)를
`JobType.REVERIFICATION` 잡의 입력으로 쓰고, 그 잡이 끝나면 그 `ScanRun`의 ID로
`POST /issues/{id}/verification-results`를 호출하면 됩니다. 판정은 그 실행이 남긴
`check_results`에서 VEO가 도출하므로 워커가 결과를 해석할 필요가 없습니다.

---

## 5. 전역 예외 핸들러 — 추가 요청 없음

`veo.api.app`에 이미 `PermissionDeniedError`(403), `AuthenticationError`(401),
`OrganizationMismatch`(404), `TenantIsolationError`(500) 핸들러가 있습니다. 이슈 라우터는
`veo.organizations.http`의 `guard` · `not_found` · `conflict`를 그대로 쓰며 새 핸들러를
필요로 하지 않습니다.

- 다른 조직의 이슈 ID / 진단 실행 ID → 404 (`NOT_FOUND`), 존재하지 않는 ID와 **문자까지
  동일한** 응답
- 허용되지 않는 상태 전이 → 409 (`CONFLICT`), 지금 선택 가능한 상태를 한국어로 안내
- 재검사 대상 URL이 없는 이슈의 재검사 요청 → 409 (`CONFLICT`)
