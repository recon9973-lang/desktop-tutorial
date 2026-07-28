# ADR 0008 — 조직 격리는 리뷰가 아니라 구조로 강제한다

- 상태: 채택
- 일자: 2026-07-28

## 배경

멀티테넌트 시스템에서 데이터 유출은 거의 항상 같은 방식으로 일어난다. 누군가
`WHERE organization_id = ...`를 빠뜨린 쿼리를 한 줄 쓰고, 그 쿼리는 조용히 다른 고객의
행을 돌려준다. 리뷰로는 막지 못한다. 사람은 매번 같은 것을 확인하지 못한다.

## 결정

- 테넌트 소유 테이블 조회는 `tenant_select(Model, principal)`로만 시작한다.
  이 함수는 필터를 이미 포함한 `SELECT`를 만든다.
- 실행 직전 `assert_tenant_scoped(stmt, principal.organization_id)`를 호출한다.
  이 가드는 statement가 건드리는 모든 테넌트 테이블에 대해 **AND로 연결된**
  `organization_id` 등호 조건을 요구한다.
  - `OR` 가지는 인정하지 않는다. `WHERE org = :me OR slug = 'x'`는 필터가 아니다.
  - JOIN으로 끌어온 테이블도 각각 조건이 있어야 한다.
  - 기본키만으로 거르는 것(`WHERE id = :guessed_uuid`)은 불충분하다.
- 가드가 걸리면 `TenantIsolationError`이며 **500**이다. 사용자 입력 문제가 아니라
  VEO의 버그이므로, 행을 돌려주는 대신 요청을 실패시킨다.
- **다른 조직의 리소스는 404다. 403이 아니다.** 403은 그 리소스가 존재한다는 사실을
  확인해 준다. 쓰기 권한을 가진 호출자에게도 동일하게 404다.

## 결과

- `organization_id`가 NOT NULL인 모든 테이블이 자동으로 가드 대상이 된다.
  새 테이블을 추가하면 별도 등록 없이 보호된다.
- `audit_logs`, `api_usage_events`는 organization이 nullable이다. 조직이 삭제돼도
  기록이 남아야 하기 때문이며, 이들은 권한으로 보호한다.
- `login_attempts`는 인증 이전에 쓰이므로 조직이 없다. 해시된 식별자만 저장한다.
- 대가: 가드가 statement를 훑는 비용이 요청마다 든다. 데이터 유출 한 건의 비용보다 싸다.
