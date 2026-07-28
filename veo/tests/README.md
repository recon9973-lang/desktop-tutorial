# VEO 테스트 전략

테스트는 기능 옆에 두는 것을 기본으로 하고, 여러 앱을 가로지르는 것만 이 폴더에 둡니다.

| 위치 | 범위 | 실행 |
|---|---|---|
| `apps/api/tests/scoring` | 점수 evaluator, golden fixture, 발행 명세 무결성 | `pytest apps/api/tests/scoring` |
| `apps/api/tests/db` | 스키마 불변식, Alembic upgrade/downgrade, 모델·마이그레이션 drift | `pytest apps/api/tests/db` (PostgreSQL 필요) |
| `apps/api/tests/contract` | OpenAPI·생성 클라이언트·공유 타입 drift, 응답 봉투 | `pytest apps/api/tests/contract` |
| `apps/api/tests/common` | SSRF URL guard, 정규화, 응답 한도 | `pytest apps/api/tests/common` |
| `apps/worker/tests` | 작업 상태 기계, 멱등성, 재시도, 취소, 부분 성공 | `pytest apps/worker/tests` |
| `packages/ui`, `packages/api-client` | 컴포넌트, 클라이언트 봉투 처리 | `pnpm -r test` |
| `tests/e2e` | 전체 시나리오 | Phase 2 이후 |
| `tests/fixtures` | 앱을 가로지르는 공유 fixture | — |

## 규칙

1. **테스트를 먼저 쓰고 실패를 확인한 뒤 구현합니다.** 특히 점수와 보안 모듈에서는
   예외가 없습니다.
2. **네트워크를 타지 않습니다.** DNS 리졸버와 HTTP 클라이언트는 주입해서 테스트에서
   가짜를 넣습니다.
3. **가짜 외부 데이터를 제품 경로에 두지 않습니다.** fixture는 `tests/` 아래에만 있고,
   제품 코드에서 참조하지 않습니다.
4. **건너뛴 테스트는 통과가 아닙니다.** `requires_postgres`, `requires_redis`로 표시된
   테스트가 skip되면 그 영역은 미검증입니다. CI는 두 서비스를 모두 띄웁니다.
5. **점수 관련 변경은 golden fixture를 통과해야 합니다.** 기대값은 사람이 방법론에서
   손으로 계산한 값이며, evaluator 출력으로 갱신하지 않습니다. 그렇게 하면 테스트가
   자기 자신을 증명하는 셈이 됩니다.

## 마커

```
requires_postgres   VEO_TEST_DATABASE_URL 필요
requires_redis      VEO_TEST_REDIS_URL 필요
```

## 로컬 전체 검증

```bash
make ci-local
```
