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
| `reassignMarketer` | clientId, newMarketerId | SUPER_ADMIN/ADMIN | 대상 마케터 ACTIVE 확인 | **거래처 업무는 함께 이관, 개인 업무는 유지**(§8-2), Audit |
| `deactivateClient` | id, reason | SUPER_ADMIN/ADMIN | **차단 없음**. 미수금/미완업무/계약종료 상태를 확인단계에 표시(§8-3) | Audit |
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

## 5. 첨부파일 (1차: 링크 방식 — 확정 ✅)

- 업무/거래처 첨부는 **외부 링크(URL) 붙여넣기 방식**으로 1차 시작 (구글드라이브/노션 등 링크).
- 직접 업로드 인프라(S3/R2 등)는 **보고서 스프린트에서 도입**.

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

## 8. 세부 규칙 (확정/대기)

| # | 규칙 | 상태 |
|---|---|---|
| 1 | 업무 **상태전이 허용표** 최종 확정 (V1 규칙 그대로 쓸지) | ❓ 대기 |
| 2 | **담당자 변경 시 업무 이관** | ✅ 확정 (아래) |
| 3 | **거래처 비활성화** | ✅ 확정 (아래) |
| 4 | **첨부 방식** (URL 링크 vs 업로드) | ✅ 확정 = 1차 URL 링크, 업로드는 보고서 스프린트 |

### 확정된 규칙 상세

**#2 담당자 변경 시 업무 이관**
- 거래처 담당자(`Client.assignedMarketerId`) 변경 시: 그 **거래처에 속한 업무(WorkItem)는 새 담당자에게 함께 이관**.
- 단, **개인 업무(특정 거래처 작업이 아닌, 개인에게 직접 할당된 업무)는 이관하지 않고 기존 담당자에 유지.**
- → `reassignMarketer` 액션은 (a) Client.assignedMarketerId 변경 + (b) 해당 clientId의 미완 WorkItem.ownerId 일괄 변경을 한 트랜잭션으로. '개인 업무' 구분 기준은 구현 시 확정(예: 거래처 작업 카테고리 vs 내부 지시 성격).

**#3 거래처 비활성화**
- **차단하지 않고 언제든 비활성화 가능**(그냥 비활성화).
- 단 비활성화 화면에서 현재 상태를 **표시**: 미수금 여부 / 미완 업무 수 / 계약종료 여부.
- → `deactivateClient`는 가드로 막지 않고, 확인 단계에서 위 정보를 보여주는 **경고/확인 방식**.

### 대기 항목 (1개)
- **#1 상태전이표**: V1 규칙 그대로 사용 여부 → ERP 코드 확보 후 V1 규칙 표를 보고 확정(착수 후 해당 작업 시점에 결정해도 무방).

§1 공통 인프라부터 바로 착수 가능(별도 ERP 세션에서). 남은 미결은 #1 하나뿐.
