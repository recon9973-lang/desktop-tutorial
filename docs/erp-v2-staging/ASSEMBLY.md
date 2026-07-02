# 베놈 ERP V2.1 — 조립 가이드 (drop-in assembly)

> 이 문서는 `docs/erp-v2-staging/`의 39개 부품을 **`recon9973-lang/marketing-agency-erp` (erp-v1)** 레포에
> 한 번에 배치·마이그레이션·연결하기 위한 실행 가이드다.
>
> **왜 여기서 바로 조립하지 않았나:** 이 세션(`desktop-tutorial`)은 콘텐츠/워드프레스 레포이고
> Next.js·Prisma 앱 기반이 없으며, GitHub 권한도 `desktop-tutorial`에만 있어 erp-v1에 push할 수 없다.
> 부품은 검증을 마쳐 "그대로 떨어뜨리면 되는" 상태로 정리해 두었다. 실제 조립은 **erp-v1로 스코프된 새 세션**에서 수행한다.
>
> 부품 39개 전체를 상호참조 정합성 관점에서 검증했다(actions·server/domain/prisma·UI 3개 축).
> 아래는 그 결과와, 조립 시 반드시 처리해야 할 항목이다.

---

## 0. 조립 순서 요약 (체크리스트)

1. [ ] **스키마 병합** — `prisma/schema-additions.prisma`의 신규 6모델 + **주석 블록의 기존모델 필드추가**를 `prisma/schema.prisma`에 삽입 → `pnpm prisma migrate dev --name v2_1_structure`
2. [ ] **env 설정** — `CREDENTIAL_ENC_KEY`, `KW_PROXY_URL`, (이메일 로그인 채택 시) `AUTH_SECRET`/`EMAIL_SERVER`/`EMAIL_FROM`
3. [ ] **npm 의존성 추가** — `next-auth`·`@auth/prisma-adapter`·`nodemailer`·`vitest`(dev)·`tsx`(dev). `playwright`는 기존 devDep 확인.
4. [ ] **파일 배치** — 아래 §2 배치표대로 복사
5. [ ] **조립 시 필수 수정** — §3의 A~F 처리 (특히 A: schema 주석 필드, B: `Role` enum, C: `getIndustryTree` flat)
6. [ ] **시드** — `tsx prisma/seed-masters.ts` (또는 seed.ts 병합)
7. [ ] **빌드/테스트** — `pnpm prisma generate && pnpm build && pnpm vitest run`
8. [ ] **UI 연결** — §4대로 `/clients`·`/work`·`/settings` 등에 컴포넌트/액션 배선
9. [ ] 통과 → 커밋 → PR

---

## 1. 부품 인덱스 (39 파일)

| 그룹 | 파일 |
|---|---|
| prisma | `schema-additions.prisma`, `seed-masters.ts` |
| server | `crypto.ts`, `auth-email.ts`, `tracking.ts`, `report-pdf.ts` |
| server/repositories | `clients-v2.ts`, `masters.ts`, `work-v2.ts` |
| domain | `finance-rules.ts`, `leave-rules.ts` |
| jobs | `keyword-rank.ts` |
| actions | `_helpers.ts`, `clients.ts`, `work.ts`, `work-schedule.ts`, `channel-accounts.ts`, `masters.ts`, `finance.ts`, `leave.ts`, `reports.ts`, `employees.ts` |
| components | `ClientForm`, `ClientList`, `ClientDetail`, `CredentialField`, `WorkStatusButtons`, `MasterManager`, `BankReconcile`, `CalendarScheduler`, `DashboardCards`, `EmployeeSettings`, `LeavePanel`, `ReportEditor` |
| app-routes | `clients-page.tsx`, `report-pdf-route.ts` |
| tests | `crypto.test.ts`, `finance-leave-rules.test.ts` |

---

## 2. 배치표 (staging 경로 → erp-v1 목표 경로)

각 파일 최상단 주석의 "목표 경로"를 그대로 반영한 것이다.

| staging | erp-v1 목표 경로 |
|---|---|
| `actions/_helpers.ts` | `src/server/actions/_helpers.ts` |
| `actions/clients.ts` | `src/server/actions/clients.ts` |
| `actions/work.ts` | `src/server/actions/work.ts` |
| `actions/work-schedule.ts` | `src/server/actions/work-schedule.ts` |
| `actions/channel-accounts.ts` | `src/server/actions/channel-accounts.ts` |
| `actions/masters.ts` | `src/server/actions/masters.ts` |
| `actions/finance.ts` | `src/server/actions/finance.ts` |
| `actions/leave.ts` | `src/server/actions/leave.ts` |
| `actions/reports.ts` | `src/server/actions/reports.ts` |
| `actions/employees.ts` | `src/server/actions/employees.ts` |
| `server/crypto.ts` | `src/server/crypto.ts` |
| `server/auth-email.ts` | `src/server/auth.ts` (기존 Kakao provider를 이메일 매직링크로 교체) |
| `server/tracking.ts` | `src/server/tracking.ts` |
| `server/report-pdf.ts` | `src/server/report-pdf.ts` |
| `server/repositories/clients-v2.ts` | `src/server/repositories/clients.ts` 에 병합 |
| `server/repositories/masters.ts` | `src/server/repositories/masters.ts` |
| `server/repositories/work-v2.ts` | `src/server/repositories/work.ts` 에 병합 |
| `domain/finance-rules.ts` | `src/domain/finance-rules.ts` |
| `domain/leave-rules.ts` | `src/domain/leave-rules.ts` |
| `jobs/keyword-rank.ts` | `src/server/jobs/keyword-rank.ts` |
| `prisma/schema-additions.prisma` | `prisma/schema.prisma` 에 병합 |
| `prisma/seed-masters.ts` | `prisma/seed.ts` 병합 또는 `tsx`로 단독 실행 |
| `components/ClientForm.tsx` | `src/components/clients/ClientForm.tsx` |
| `components/ClientList.tsx` | `src/components/clients/ClientList.tsx` |
| `components/ClientDetail.tsx` | `src/components/clients/ClientDetail.tsx` |
| `components/CredentialField.tsx` | `src/components/clients/CredentialField.tsx` |
| `components/WorkStatusButtons.tsx` | `src/components/work/WorkStatusButtons.tsx` |
| `components/MasterManager.tsx` | `src/components/settings/MasterManager.tsx` |
| `components/EmployeeSettings.tsx` | `src/components/settings/EmployeeSettings.tsx` |
| `components/BankReconcile.tsx` | `src/components/finance/BankReconcile.tsx` |
| `components/CalendarScheduler.tsx` | `src/components/calendar/CalendarScheduler.tsx` |
| `components/DashboardCards.tsx` | `src/components/dashboard/DashboardCards.tsx` |
| `components/LeavePanel.tsx` | `src/components/leave/LeavePanel.tsx` |
| `components/ReportEditor.tsx` | `src/components/reports/ReportEditor.tsx` |
| `app-routes/clients-page.tsx` | `src/app/(erp)/clients/page.tsx` |
| `app-routes/report-pdf-route.ts` | `src/app/api/reports/[id]/pdf/route.ts` |
| `tests/crypto.test.ts` | `tests/server/crypto.test.ts` |
| `tests/finance-leave-rules.test.ts` | `tests/domain/finance-leave-rules.test.ts` |

---

## 3. 조립 시 필수 수정 (검증에서 발견된 정합성 이슈)

부품 검증 중 발견한 항목이다. **A~C는 하지 않으면 빌드/런타임이 깨진다.** D~F는 설계상 반드시 결정해야 한다.
(staging 자체에서 안전하게 고칠 수 있는 2건은 이미 적용해 두었다 — 맨 아래 "이미 적용됨" 참고.)

### A. 【필수】 스키마 주석 필드추가를 실제로 반영할 것
`schema-additions.prisma`의 신규 6모델(`IndustryCategory`, `WorkCategoryMaster`, `ChannelType`, `LoginHistory`,
`BankTransaction`, `CompanySetting`)은 그대로 붙이면 된다. 하지만 파일 하단 **주석 블록**(기존 모델
`Client`/`WorkItem`/`ClientAccount`/`User`/`BillingRecord`에 대한 필드·관계 추가)은 주석이라 마이그레이션에
포함되지 않는다. **손으로 각 기존 모델 본문에 삽입해야 한다.**
- 반영 안 하면: `LoginHistory.user`↔`User.loginHistory`, `BankTransaction.matchedBilling`↔`BillingRecord.bankMatches`
  **역관계 누락으로 `prisma generate` 실패**.
- 또한 `repositories/clients-v2.ts`(`client.industryCategory.parent`)와 `repositories/work-v2.ts`
  (`scheduledStart/End`, `estimatedMinutes`, `sequence`, `parentId`, `subtasks`), `actions/work-schedule.ts`가
  이 추가 필드를 사용 → 미반영 시 타입 에러.

### B. 【필수】 `@/domain/types`의 `Role`은 런타임 enum이어야 함
`clients-page.tsx`는 `Role.SUPER_ADMIN`/`Role.ADMIN`/`Role.MARKETER`를 **값(enum member)**으로 사용하고,
`DashboardCards.tsx`는 `Role`을 **type-only import**한 뒤 문자열 리터럴(`role !== "MARKETER"`)과 비교한다.
→ erp-v1의 `Role`이 **문자열 값을 갖는 런타임 enum**(예: `enum Role { SUPER_ADMIN="SUPER_ADMIN", ... }`)이어야
두 사용처가 모두 컴파일된다. `EmployeeSettings`·`WorkStatusButtons`·`LeavePanel`·`masters.ts`는 문자열 리터럴을
쓰므로 enum 멤버 문자열과 정확히 일치해야 한다. 마찬가지로 `@/domain/types`는 `BillingStatus`(UNPAID/
PARTIALLY_PAID/OVERDUE/PAID), `LeaveType`(ANNUAL/HALF_DAY_AM/HALF_DAY_PM), `WorkCategory`,
`ClientAccountPlatform`, `UserStatus`(ACTIVE/INVITED) enum을 제공해야 한다(부품 다수가 의존).

### C. 【필수】 `getIndustryTree()`는 이름과 달리 flat 배열을 반환해야 함
`clients-page.tsx`가 `getIndustryTree()` 결과를 `ClientForm`에 `industries`로 넘기는데,
`ClientForm`은 `parentId === null`로 대분류를 필터링하는 **평탄한 노드 배열**(`{id,name,parentId,colorTag}`)을 기대한다.
`repositories/masters.ts`의 `getIndustryTree` 구현이 중첩 트리를 반환하면 폼의 업종 2단 선택이 깨진다.
→ 구현이 flat을 반환하는지 확인(부품 구현은 flat select이므로 대개 OK, 이름만 헷갈림).

### D. 【결정】 `ClientAccount` 생성 경로 이원화
- `actions/clients.ts#addClientAccount`: 기존 enum 필드 `platform`(`ClientAccountPlatform`)으로 생성, `channelTypeId` 미설정.
- `actions/channel-accounts.ts`: V2 `channelTypeId`로 생성, `platform` 미설정.
→ base `ClientAccount.platform`이 **NOT NULL**이면 channel-accounts 경로 생성이 실패한다.
**결정 필요:** `platform`을 nullable로 완화하거나, 두 경로 중 하나로 통일(권장: 신규는 channel-accounts로 일원화,
`platform`은 이관 기간 동안 nullable). 마이그레이션에 반영할 것.

### E. 【권장】 도메인 규칙 모듈을 액션이 import하도록 정리
`domain/finance-rules.ts`(`computeBillingStatus`)와 `domain/leave-rules.ts`(`leaveDays`,`remainingLeave`)는
`BillingStatus`/`LeaveType` enum을 반환하는 "정답" 구현이고, 각 파일 주석도 "actions가 import하라"고 명시한다.
그런데 `actions/finance.ts`·`actions/leave.ts`는 이를 무시하고 **문자열 반환 인라인 버전**을 재구현하며 `as never`로
캐스팅한다(시그니처 drift). → 조립 시 액션의 인라인 `computeBillingStatus`/`leaveDays`를 지우고 도메인 모듈을
import하도록 교체하면 중복 제거 + `as never` 제거 가능. (base enum과 붙는 작업이라 erp-v1에서 타입확인 후 적용 권장.)

### F. 【결정】 UI 배선 누락 지점
- `WorkStatusButtons`는 어떤 부품에서도 참조되지 않는다. `ClientDetail`의 "업무" 탭은 상태를 텍스트로만 보여주고
  전이 버튼을 붙이지 않았다. → 업무 상세/목록에서 상태전이가 필요하면 직접 배치.
- `ReportEditor`도 `ClientDetail` "보고서" 탭에 임베드되지 않고 `/reports` 링크만 있다. 의도 확인 후 연결.
- **디자인시스템 미사용**: 12개 컴포넌트 전부 원시 HTML+Tailwind이며 브랜드 컬러 `#533afd`가 9개 파일에 하드코딩됨.
  특히 `MasterManager.tsx`는 `#533afd`를 생성 레코드의 `colorTag` **데이터 기본값**으로 심는다.
  → erp-v1 UI 셸/토큰에 맞춰 스타일 조정, 색상은 디자인토큰으로 치환 권장.

### 인증(auth) 관련 확인 — auth-email.ts
`auth-email.ts`는 `PrismaAdapter` + `session.strategy:"database"` + 이메일 매직링크(nodemailer provider)를 쓴다.
→ Auth.js 어댑터 모델 `VerificationToken`·`Session`·`Account`(및 어댑터 형태의 `User`)가 **base 스키마에 이미 있어야**
이메일 로그인이 동작한다. schema-additions에는 없으므로 base 확인 필수. 이메일 로그인을 채택하지 않으면 이 파일은 배치 보류.

### 이미 적용됨 (staging에서 안전하게 선반영한 수정)
- **`actions/_helpers.ts`에서 `"use server"` 제거.** 이 파일은 `runAction(fn)`처럼 **함수를 인자로 받는** 유틸이라
  server action으로 노출하면 안 되고, 동기 함수 `toAuditState`를 export하므로 `"use server"`(async-only) 규칙에도 위배된다.
  → 일반 서버 유틸로 두는 것이 정답(실제 진입점은 이 파일을 import하는 `actions/*.ts`들이며 각자 `"use server"` 보유). **빌드 차단 이슈였음.**
- **`actions/channel-accounts.ts`의 미사용 `Role` import 제거.**

---

## 4. UI ↔ 서버액션 연결 맵

각 컴포넌트가 호출하는 액션(모두 `{ ok: boolean; error?: string }` 반환, `revealCredentials`만 `data` 추가):

| 컴포넌트 | 호출 액션 (모듈) | 시그니처 주의 |
|---|---|---|
| `ClientForm` | `createClient`,`updateClient` (clients) | |
| `CredentialField` | `revealCredentials` (channel-accounts) | 인자 `accountId` **문자열**, 반환 `data:{username,password}` |
| `WorkStatusButtons` | `changeWorkStatus` (work) | `{id, action}`; action ∈ start/submit_for_review/approve/block/resume |
| `CalendarScheduler` | `scheduleWorkItem`,`unscheduleWorkItem` (work-schedule) | `unschedule`는 인자 **문자열** |
| `MasterManager` | `upsertWorkCategory`,`setMasterLock` (masters) | `setMasterLock({kind,id,locked})` |
| `BankReconcile` | `confirmBankMatch` (finance) | `{bankTxId, billingId}` |
| `EmployeeSettings` | `inviteEmployee`,`changeRole`,`setExpensePolicy` (employees) | |
| `LeavePanel` | `requestLeave`,`approveLeave`,`rejectLeave` (leave) | `approveLeave(id)` 문자열 vs `rejectLeave({id})` 객체 |
| `ReportEditor` | `updateReportMetrics`,`transitionReport` (reports) | action ∈ submit/approve/deliver; PDF는 `/api/reports/{id}/pdf` |
| `clients-page` (서버컴포넌트) | 액션 아님 — `listClientsForUser`,`getIndustryTree`,`getCurrentUser`,`db` | §3-C 참고 |

`revalidatePath` 대상 라우트: `/clients`, `/clients/[id]`, `/work`, `/calendar`, `/settings`, `/finance`, `/leave`, `/reports`.
→ 실제 App Router 경로와 일치해야 revalidate가 동작.

---

## 5. 환경변수 / 의존성 요약

**env**
| 변수 | 용도 | 형식 |
|---|---|---|
| `CREDENTIAL_ENC_KEY` | 채널계정 자격증명 AES-256-GCM 키 (crypto.ts) | 32바이트 = hex 64자 또는 base64 |
| `KW_PROXY_URL` | 키워드 순위 프록시 base URL (keyword-rank.ts) | `https://.../kw-proxy` |
| `AUTH_SECRET` | Auth.js 세션 서명 (auth-email.ts) | 랜덤 시크릿 |
| `EMAIL_SERVER` | 매직링크 SMTP (auth-email.ts) | `smtp://user:pass@host:587` |
| `EMAIL_FROM` | 발신 주소 (auth-email.ts) | `noreply@…` |
| `DATABASE_URL` | Prisma (기존) | |

**npm (erp-v1 package.json에 추가)**
- 런타임: `next-auth`(v5), `@auth/prisma-adapter`, `nodemailer`
- dev: `vitest`, `tsx`
- `playwright`: report-pdf.ts가 동적 `import("playwright")` 사용 — 기존 devDep 여부 확인(없으면 추가). puppeteer는 대안 언급만, 코드는 playwright chromium 사용.

---

## 6. 검증 완료 사항 (참고)

- 39개 부품의 staging 간 상호 import·함수 참조는 **누락/오탈자 없음**(예: `_helpers` export 6종, `crypto` export 3종을
  각 액션이 정확히 참조; `auth-email→recordLogin`, keyword-rank 내부 체인, report-pdf가 읽는 `metrics.keywordRanks`
  형태와 keyword-rank가 쓰는 형태 일치).
- 테스트 2종(`crypto`, `finance-leave-rules`)은 대상 모듈의 export 이름·시그니처·기대값과 정확히 일치.
- 모든 `actions/*.ts`는 `"use server"` 보유(단, `_helpers.ts`는 §3대로 유틸이므로 제외가 정답).
- Next 15 규약 반영됨: `await headers()`, route handler의 `params: Promise<…>` + `await params`.

> 남은 외부 의존(erp-v1 base에 존재해야 하는 것): `@/server/db`, `@/server/session`(`getCurrentUser`→`{id,name,email,role}`),
> `@/domain/access-control`(`assertCanAccessClient`, `AccessScopeRecord`), `@/domain/work`(`nextWorkStatus`, `WorkStatusAction`),
> `@/domain/types` enum들, base 모델 `AccessScope`·`AuditLog`·`CalendarEvent`·`Report`·`BillingRecord`·`PaymentRecord`·
> `LeaveRequest`·`LeavePolicy`·`User`·`Client`·`WorkItem`·`ClientAccount`, Auth.js 어댑터 모델.
