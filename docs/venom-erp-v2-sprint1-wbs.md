# 베놈 ERP V2 — 1차 스프린트 WBS (업무관리 + 거래처)

작성일: 2026-06-30
선행 문서: `docs/venom-erp-v2-plan.md`
대상 코드: `recon9973-lang/marketing-agency-erp` (`erp-v1`)
확정 사항: 1차 = 업무+거래처 / 인증 = Kakao 유지 / 병원특화는 2차 이후 / CSV import는 셋업 소작업

> 모든 쓰기는 **server action + Zod 검증 + AccessScope 권한 가드 + 도메인 규칙 + AuditLog** 5단계를 통과한다.

---

## 0. 셋업 (스프린트 착수 전 / 1회성)

| # | 작업 | 비고 |
|---|---|---|
| S1 | ERP 레포 작업 권한 확보 (별도 세션 또는 권한 추가) | 코드 push 전제 |
| S2 | 운영/스테이징 PostgreSQL + `.env` (`DATABASE_URL`, `AUTH_SECRET`, `AUTH_URL`, `AUTH_KAKAO_ID/SECRET`) | |
| S3 | `prisma migrate` 적용 + 초기 `SUPER_ADMIN` seed | |
| S4 | 쓰기 공통 인프라 3종 (아래 §1) | 모든 액션이 의존 |
| S5 | 거래처/직원 CSV import 스크립트 | 도입 마찰 최소화 |

---

## 1. 쓰기 공통 인프라 (먼저 만들어야 함 — 모든 액션이 재사용)

### 1.1 `withAction` 래퍼
```
withAction(actor, { permission, domainCheck, audit })(handler)
```
- **권한 가드**: actor의 Role + AccessScope로 대상 거래처/담당자 접근 가능 여부 검사. 실패 시 거부.
- **검증**: Zod 스키마로 입력 파싱.
- **감사**: 성공 시 `AuditLog`에 `actorId, action, targetType, targetId, beforeState, afterState, ipAddress, userAgent` 저장 (스키마에 필드 이미 존재).
- **트랜잭션**: 본 변경 + AuditLog + (해당 시)CalendarEvent를 단일 `prisma.$transaction`.
- **결과**: `{ ok } | { error }` 반환 → UI 토스트 + `revalidatePath`.

### 1.2 권한 헬퍼 `canAccessClient(actor, clientId)` / `canAccessWork(actor, workItem)`
- V1의 읽기 스코프 로직을 **쓰기에도 동일 적용**(재사용/추출).

### 1.3 감사 저장 `recordAudit(tx, ...)`
- `buildAuditEvent` 헬퍼(이미 존재)를 실제 DB 저장으로 연결.

---

## 2. 거래처(Client) — server actions

| 액션 | 입력(주요) | 권한 | 도메인 규칙 | 부가효과 |
|---|---|---|---|---|
| `createClient` | name, code, businessNumber, contactInfo, 계약기간/월계약금, assignedMarketerId | SUPER_ADMIN, (범위 내)ADMIN | code 유일성, businessNumber 형식 | Audit |
| `updateClient` | id + 수정필드 | 위 + 해당 담당 | 비활성 거래처 수정 제한 | Audit(before/after) |
| `reassignMarketer` | clientId, newMarketerId | SUPER_ADMIN/ADMIN | 대상 마케터 ACTIVE 확인 | 관련 WorkItem 담당 재배정 정책 ❓, Audit |
| `deactivateClient` | id, reason | SUPER_ADMIN/ADMIN | 미완 업무/미수금 존재 시 경고 | Audit |
| `addClientAccount` | clientId, platform, label, handle, isPrimary | 담당 가능자 | client당 platform별 primary 1개 | Audit |
| `updateClientAccount` / `deactivateClientAccount` | accountId + 필드 | 담당 가능자 | — | Audit |

**UI**
- `/clients` 신규등록 폼(모달/페이지), 행 수정·비활성화
- `/clients/[id]` 상세페이지: 기본정보 / 담당자 / 계정(블로그·SNS·플레이스) / 최근 업무 / 최근 정산 탭
- 담당자 배정 변경 인라인 액션

**완료 기준**
- 관리자가 거래처를 등록→배정→수정→비활성화까지 클릭으로 수행.
- 범위 밖 거래처 생성/수정 시 차단(테스트).
- 모든 변경이 AuditLog에 1건씩 기록(테스트).

---

## 3. 업무관리(WorkItem) — server actions

상태 enum: `NOT_STARTED, IN_PROGRESS, WAITING, REVIEW_NEEDED, COMPLETED, BLOCKED`

| 액션 | 입력(주요) | 권한 | 도메인 규칙 | 부가효과 |
|---|---|---|---|---|
| `createWorkItem` | clientId, ownerId, title, category, priority, dueDate | 담당 가능자 | 거래처 접근권 확인, dueDate 유효 | dueDate→CalendarEvent(TASK) 생성, Audit |
| `changeWorkStatus` | id, nextStatus | owner/관리자 | **상태전이 규칙**(이미 존재)으로 불법전이 차단 | COMPLETED 시 completedAt, CalendarEvent 갱신, Audit(before/after) |
| `addProgressNote` | id, note | owner/관리자 | 빈 노트 거부 | progressNotes append, Audit |
| `updateWorkItem` | id, title/priority/dueDate/category | 담당 가능자 | — | dueDate 변경 시 CalendarEvent 동기화, Audit |
| `reassignWorkOwner` | id, newOwnerId | 관리자 | 대상 ACTIVE 확인 | Audit |
| `generateFromTemplate` | templateId, clientId, 기준일 | 관리자 | cadenceDays로 반복 생성 | 다건 WorkItem + CalendarEvent, Audit |

**UI**
- `/work` 상태변경 버튼(허용 전이만 활성), 진행메모 입력, 신규 업무 폼
- 필터(상태/카테고리/거래처/담당자/마감일)는 V1 존재 → 생성·변경 액션만 연결
- 지연 업무 강조는 V1 존재

**완료 기준**
- 마케터가 업무 생성→진행메모→상태전이→완료를 클릭으로 수행.
- 불법 상태전이 차단(예: NOT_STARTED→COMPLETED 직행 정책 ❓ — 규칙 확정 필요).
- 마감일 업무가 캘린더에 자동 표시.
- 반복 템플릿으로 월초 정기 업무 일괄 생성.

---

## 4. 캘린더 자동연동 (1차 범위: 내부 이벤트 자동생성만)

- 업무 생성/마감변경 → `CalendarEvent(kind=TASK, workItemId)` 생성/갱신/삭제.
- (2차) 휴가 승인 → `LEAVE`, 보고서 마감 → `REPORT_DEADLINE`.
- 외부(Google/Naver) 양방향 sync는 V3.

---

## 5. 첨부파일 (1차: 최소)

- 업무/거래처 첨부는 **URL 필드 우선**(외부 스토리지 링크 붙여넣기)으로 시작.
- 실제 업로드 인프라(S3/R2 등)는 보고서 스프린트와 함께 도입 ❓.

---

## 6. 테스트 (1차에 추가할 것)

- 권한: 범위 밖 거래처/업무 쓰기 차단.
- 도메인: 업무 상태전이 불법 케이스 거부, 템플릿 반복생성 개수.
- 감사: 각 쓰기 액션이 AuditLog 1건 + before/after 정확.
- 캘린더: 마감일 변경 시 이벤트 동기화.
- e2e: 거래처 등록→업무 생성→상태완료 happy path.

---

## 7. 작업 순서 (의존성 기준 권장 진행)

1. **§1 공통 인프라**(withAction/권한/감사) — 선행 필수
2. **§2 거래처 createClient/updateClient/상세페이지** — 업무가 거래처에 의존
3. **§3 createWorkItem/changeWorkStatus/addProgressNote** — 핵심 일상 화면
4. **§4 캘린더 자동 이벤트** — 업무 액션에 연결
5. **§3 템플릿 반복생성 + §2 배정/계정 관리** — 운영 편의
6. **§6 테스트 보강 + 회귀 확인**

---

## 8. 이번 스프린트에서 확정 필요한 세부 규칙 ❓

1. 업무 **상태전이 허용 표**의 최종 확정 (어떤 전이를 막을지). V1 규칙을 그대로 쓸지 검토.
2. 거래처 담당자 변경 시 **기존 진행중 업무의 담당자**도 함께 옮길지.
3. 거래처 **비활성화 가드** 강도(미수금/미완업무 있으면 차단 vs 경고).
4. **첨부**: URL 링크 방식으로 1차 시작 OK인지, 아니면 업로드 인프라를 1차에 포함할지.

위 4개만 정하면 §1부터 바로 구현 착수 가능(별도 ERP 세션에서).
