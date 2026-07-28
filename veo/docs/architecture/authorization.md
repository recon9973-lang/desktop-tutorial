# VEO 인증·권한 모델

이 문서는 "누가 무엇을 할 수 있는가"를 한곳에 모아 설명합니다. 배점 명세와 마찬가지로,
권한도 흩어져 있으면 아무도 답할 수 없는 질문이 됩니다.

## 1. 세 가지 질문을 분리한다

| 질문 | 담당 | 실패 시 |
|---|---|---|
| 누구인가 (Authentication) | `veo/auth/` — 토큰·세션 | **401** |
| 무엇을 할 수 있는가 (Authorization) | `veo/authz/permissions.py` — 권한 행렬 | **403** |
| 어느 조직의 데이터인가 (Tenancy) | `veo/authz/tenancy.py` — 구조적 가드 | **404** |

세 번째가 404인 것이 중요합니다. 다른 조직의 리소스에 403을 주면 그 리소스가 존재한다는
사실을 확인해 주는 셈입니다. 쓰기 권한을 가진 호출자에게도 동일하게 404입니다.

## 2. 역할

| 역할 | 하는 일 | 명시적으로 못 하는 일 |
|---|---|---|
| `SUPER_ADMIN` | 조직·보안·점수 발행·전체 설정 | — |
| `LAB_ADMIN` | VEO-LAB 측정 방법론 작성·발행, 검증용 결과 열람 | 고객 데이터 변경 |
| `ANALYST` | 프로젝트·진단 실행·검수·보고서 | 사용자 관리, 역할 부여 |
| `DEVELOPER` | 기술 이슈·원자료 확인·수정·재검증 | 고객 정보 변경, 보고서 내보내기 |
| `SALES_VIEWER` | 고객 요약, 공개 가능한 보고서 | 모든 쓰기, **원자료 열람**, 자격증명 상태 |
| `CLIENT_VIEWER` | 자기 프로젝트 읽기 전용 | 원자료, 감사 로그, 사용량, 사용자 목록 |

전체 행렬은 `apps/api/src/veo/authz/permissions.py`에 있고,
`GET /api/auth/me`가 호출자에게 해석된 권한 목록을 그대로 내려줍니다.

## 3. 라우터에서 쓰는 법

```python
from veo.authz import CurrentPrincipal, Permission, require, tenant_select

@router.get(
    "/projects",
    dependencies=[Depends(require(Permission.PROJECT_READ))],
)
def list_projects(principal: CurrentPrincipal, db: Session = Depends(get_db)):
    stmt = tenant_select(Project, principal)      # 필터가 이미 들어 있다
    assert_tenant_scoped(stmt, principal.organization_id)  # 실행 직전 확인
    return db.scalars(stmt).all()
```

하지 말아야 할 것:

- `select(Project)`로 시작하기 — 조직 필터가 빠진다.
- 라우터 안에서 역할을 직접 비교하기 (`if principal.roles == ...`) — 행렬을 우회한다.
- 권한 없음을 404로, 다른 조직을 403으로 주기 — 정확히 반대다.

## 4. 테넌트 가드가 거부하는 것

`assert_tenant_scoped`는 **AND로 연결된** `organization_id` 등호 조건을 요구합니다.

| 쿼리 | 결과 |
|---|---|
| `select(Project)` | 거부 — 필터 없음 |
| `where(Project.id == guessed_uuid)` | 거부 — 기본키만으로는 부족 |
| `where(or_(org == me, slug == "x"))` | 거부 — OR 가지는 필터가 아님 |
| `join(Site)` 했는데 Site에 조건 없음 | 거부 — 조인된 테이블도 각각 필요 |
| `where(org == me).where(Site.org == me)` | 통과 |

가드가 걸리면 `TenantIsolationError` → **500**입니다. 사용자 입력 문제가 아니라 VEO의
버그이므로, 행을 돌려주는 대신 요청을 실패시킵니다.

## 5. 토큰

| | Access | Refresh |
|---|---|---|
| 형식 | JWT HS256 | 불투명 난수 256비트 |
| 수명 | 15분 | 14일 |
| 저장 | httpOnly·Secure·SameSite=Lax 쿠키 | 동일 |
| DB | 저장 안 함 | **SHA-256만** 저장 |
| 폐기 | 불가 (짧게 유지) | 가능, 즉시 |

- **회전**: refresh할 때마다 이전 행을 폐기하고 새 행을 발급합니다. 같은 로그인에서 나온
  행들은 `family_id`를 공유합니다.
- **재사용 탐지**: 이미 회전된 토큰이 다시 오면 탈취입니다. 패밀리 전체를 폐기하고
  감사 기록을 남긴 뒤, 호출자에게는 평범한 401만 줍니다.
- **역할은 토큰이 아니라 DB에서 읽습니다.** 토큰의 `roles`는 교차 확인용 힌트입니다.
  권한을 회수했는데 15분간 유효하다면 회수가 아닙니다.
- **조직은 로그인 시점에 고정됩니다.** 헤더나 클레임으로 바꿀 수 없습니다.

## 6. 자격증명 보관

제공자 비밀값은 **들어가고 사용될 뿐, 나오지 않습니다.**

- AES-256-GCM, 쓰기마다 새 nonce, associated data에
  `(organization_id, provider, field, key_version)`을 묶습니다. 다른 테넌트나 다른
  필드로 ciphertext를 옮기면 복호화가 실패합니다.
- 평문 컬럼이 없고, 라우터가 호출할 수 있는 복호화 경로가 없으며,
  그것을 허용하는 권한 자체가 존재하지 않습니다.
- 확인할 수 있는 것: 어떤 제공자의 어떤 필드가 설정돼 있는가, 언제 설정됐는가,
  지문(fingerprint), 짧은 표시 힌트.
- 검증 실패는 기계 코드만 저장합니다. 제공자 오류 문구는 자격증명을 그대로 되돌려
  주는 일이 흔합니다.

## 7. 로그와 오류에 절대 넣지 않는 것

비밀번호, 토큰(access·refresh 모두), 제공자 자격증명, 원시 이메일, 원시 IP,
원시 AI 답변, 고객 연락처.

이메일과 IP는 필요하면 해시로 저장합니다 (`audit_logs.source_ip_hash`,
`login_attempts.identifier_hash`).

## 8. 로그인 실패 응답

이메일이 없든 비밀번호가 틀렸든 **같은 응답**입니다. 모양도, 대략의 소요 시간도
같아야 합니다 — 존재하지 않는 사용자에 대해서도 동등한 시간의 더미 검증을 수행합니다.
계정 열거를 막기 위해서이며, 프론트엔드도 같은 규칙을 따릅니다.

잠금(429)만 별도 메시지를 줍니다. 잠금은 해시된 식별자 기준이라 그 자체로는 어떤
주소에 계정이 있는지 알려주지 않습니다.

## 9. 남은 위험

- 폐기된 세션의 access token은 **최대 15분간 유효**합니다. 즉시 차단이 필요한 사건에는
  별도의 거부 목록(deny list)이 필요하며 Phase 1 범위 밖입니다.
- 권한 회수는 다음 요청에 반영되지만, 이미 진행 중인 장시간 작업은 시작 시점의 권한으로
  계속됩니다. 작업 취소로 대응합니다.
