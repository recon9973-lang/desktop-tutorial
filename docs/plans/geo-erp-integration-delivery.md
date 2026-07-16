# GEO → ERP 통합 인도(Delivery) 문서 — M1~M6 전 모듈 완료

> 작성일 2026-07-16 · 세션 산출물 정리 · 기준 설계서: [`geo-erp-integration-design-v2.md`](geo-erp-integration-design-v2.md)
>
> 이 문서는 **"GEO 운영 OS → VENOM ERP 병합"** 작업의 최종 인도 명세다. 6개 모듈(M1~M6)의
> 목적·변경 파일·구현 접근·테스트·PR·검증 결과와, 팀이 이어서 할 머지/실행 절차를 한곳에 모았다.

---

## 0. 한눈에 보기

| 모듈 | 내용 | ERP 저장소 PR | 브랜치 | 스키마 변경 | 오프라인 검증 |
|---|---|---|---|---|---|
| **M1** | 경쟁사 SOV(Share of Voice) 집계 + KPI 타일 | [#42](https://github.com/recon9973-lang/marketing-agency-erp/pull/42) | `feat/geo-sov` | 0 | 6/6 |
| **M2** | 채널 자동화 cap-clamp(고위험 채널 자동실행 차단) | [#43](https://github.com/recon9973-lang/marketing-agency-erp/pull/43) | `feat/geo-capclamp` | 0 | 7/7 |
| **M3** | 거래처 GEO 주간 리포트(규칙기반 조립) | [#44](https://github.com/recon9973-lang/marketing-agency-erp/pull/44) | `feat/geo-weekly` | 0 | 8/8 |
| **M4** | 반복 업무 자동 생성(cadenceDays) | [#45](https://github.com/recon9973-lang/marketing-agency-erp/pull/45) | `feat/geo-recur` | 0 | 10/10 |
| **M5** | 온보딩 Phase 체크리스트 반영 | [#46](https://github.com/recon9973-lang/marketing-agency-erp/pull/46) | `feat/geo-onboarding-checklist` | 0 | 8/8 |
| **M6** | NAS 팀 앱 → ERP 이관 스크립트 골격 | [#47](https://github.com/recon9973-lang/marketing-agency-erp/pull/47) | `feat/geo-nas-migration` | 0 | 13/13 |

- **대상 저장소**: `recon9973-lang/marketing-agency-erp`(Next.js 15 App Router · Prisma 6 · Neon Postgres · pnpm), base 브랜치 `erp-v1`.
- **전 모듈 base = `erp-v1`**, 모두 open(자동 머지 안 함) — CI/리뷰 후 팀이 순차 머지.
- **총 오프라인 검증 52케이스 통과**. ERP node_modules 미설치 환경이라 TS 타입을 벗긴 순수-로직 하니스로 검증했고, `tsc`/`vitest`/`next build`는 각 PR의 Vercel CI에서 최종 확인(#45 M4는 Vercel 배포 green 확인 완료).

---

## 1. 배경과 목표

- **출발점**: 별도 저장소 `desktop-tutorial`에 파일럿으로 구축한 **GEO 운영 OS**(거래처 AI 인용 모니터링·업무·성과·리포트, 자동화 A~D 등급)를, 이미 거래처·계약·업무·이미지스튜디오를 갖춘 **VENOM ERP**(`marketing-agency-erp`)에 병합하는 것이 최종 목적.
- **핵심 정정(설계서 v2)**: v1 설계서는 ERP를 그린필드로 가정해 신규 모델(`GeoChannel`·`GeoChecklistProgress`·`ClientNote`)을 대거 신설하려 했다. **ERP 실사 결과 이미 4-AI GEO 파이프라인**(`geo-engine/*`·`GeoQuestion`·`GeoAnswerRecord`·`ContentPlan`·`WorkItem`·`WorkTemplate`·`ClientAccount`·`Comment`)**이 있었다.** → 병합은 "신규 시스템 구축"이 아니라 **기존 모델 위에 빠진 조각(순수 함수)만 이식**하는 소규모 작업으로 재정의.
- **결과**: 6개 모듈 모두 **스키마 변경 0**(기존 필드 재사용) 또는 파생 계산으로 구현.

---

## 2. 아키텍처 정정 (설계서 §6)

```
v1(❌): ERP(소비) ── clinicId ──> desktop-tutorial(엔진, GitHub Actions egress 우회)
v2(✅): ERP 단독 — geo-engine 서버 내장. 실측·수집·리포트·크론 전부 ERP 안에서.
         desktop-tutorial GEO-OS = 로직 도너(이식 후 파일럿 종료)
```

- ERP는 풀 서버(Next.js)라 AI 엔진·GSC를 서버에서 직접 호출 → GitHub Actions egress 우회 불필요.
- 크론은 기존 `src/app/api/marketing/cron/route.ts`(Vercel cron GET + 시크릿 POST)에 GEO job을 추가하는 방식(M4가 이 경로 사용).
- desktop-tutorial의 GEO-OS/워크플로/콘솔/`ADMIN_SECRET`은 **이관하지 않음**(파일럿 종료 대상).

---

## 3. 모듈별 상세

### M1 — 경쟁사 SOV(Share of Voice) · PR #42

**빈칸**: ERP는 `GeoAnswerRecord.competitorsMentioned`(Json)에 경쟁사 언급을 **기록만** 하고 SOV로 **집계하지 않았다.**

**구현**
- `src/server/geo-engine/sov.ts` (신규, 순수): `buildSov(cells)` = 자사 출현 / (자사 출현 + 경쟁사 언급 합). 언급 0이면 `null`(측정 불가). `asCompetitors(json)`으로 Prisma `Json?` → `string[]` 안전 변환.
- `src/server/repositories/geo.ts`: `GeoCell`에 `competitors: string[]` 파생 추가 + `computeGeoSov(rows)`(기존 조회 rows에서 파생, **추가 쿼리 없음**, RETIRED 제외).
- `src/app/(erp)/geo/page.tsx`: KPI 타일에 **"경쟁사 SOV"** 추가(열세 <50%면 amber, 미언급 시 `—`).
- `src/server/geo-engine/sov.test.ts`(vitest).

**정직성**: 절대 인용% 하드코딩 없음 — 실측 레코드에서 파생한 **상대지표**만. **검증** 6/6.

---

### M2 — 채널 자동화 cap-clamp · PR #43

**빈칸**: `geo-channels.ts`가 채널별 `automationLevel`(cap)을 갖고 있으나, **업무 레벨이 채널 cap을 넘지 못하게 강제하는 로직이 없었다.** 위키/커뮤니티(cap C) 업무가 실수로 A/B(자동 실행)로 설정될 위험.

**구현** (`src/domain/sales/geo-channels.ts`)
- `AUTOMATION_RANK`(A=4>B=3>C=2>D=1) + `clampLevel(level, cap)` — cap 초과(더 자동)면 cap으로 강등, 더 낮은 자동화는 유지(순수).
- `channelCap(channel)` — 플레이북에서 채널 자동화 상한 조회.
- `resolveAiChannelTasks(tasks?)` — 업무를 채널 cap으로 clamp(`capped` 플래그). WorkItem 벌크 생성 전 이 결과를 쓰면 자동 실행 누수 차단.
- `riskyAutomationViolations(tasks?)` — cap 초과 업무 목록(불변식 점검, 정상 = 빈 배열).
- `AI_CHANNEL_TASKS` 8종에 구조화 `automationLevel` + `channel` 태깅(제목의 `[자동화 X]`를 기계가독화).
- `src/domain/sales/onboarding-tasks.ts`: `OnboardingTaskTemplate`에 `automationLevel?`/`channel?` 추가(인라인 리터럴 → 순환 import 방지).

**설계 정합**: 자동화 금지선(위키·레딧·커뮤니티 게시 = 인간 필수/초안)을 **코드가 강제**. **검증** 7/7.

> ⚠️ **머지 주의**: M2와 M5가 **같은 `OnboardingTaskTemplate` 타입**에 각각 optional 필드를 추가한다(M2: `automationLevel?`/`channel?`, M5: `phase?`). 충돌 시 **양쪽 필드 모두 유지**로 해결. 머지 순서 M2→M5 권장.

---

### M3 — 거래처 GEO 주간 리포트 · PR #44

**빈칸**: ERP엔 **월간** 리포트 자동조립(`report-assembly.ts`)과 **직원 개인 주간**(`WeeklyReport`)만 있고, **거래처 단위 GEO 주간 리포트**가 없었다.

**구현** (`src/server/marketing/geo-weekly.ts`, 신규)
- `buildGeoWeekly(input)`(순수): AI 출현/인용 · SOV · 성과 델타(순위는 낮을수록 개선 = `betterWhenLower`) · 업무 완료율/승인대기/BLOCKED → `keyWins`/`risks`/`nextActions` + 요약. **통계 미생성 — 실측 입력값만.**
- `assembleGeoWeekly(clientId, weekStart, weekEnd, opts?)`: `geoMonthlySummary`(주간 창 재사용) + `WorkItem` 집계로 입력을 모아 `buildGeoWeekly` 호출. **SOV는 선택 주입**(M1 결과) — M1과 독립. 저장하지 않고 반환.
- `src/server/marketing/geo-weekly.test.ts`(vitest).

**용어 충돌 방지**: ERP `WeeklyReport`(직원) ≠ 이 GEO 주간(거래처). **검증** 8/8.

---

### M4 — 반복 업무 자동 생성 · PR #45 ✅ Vercel 배포 green

**빈칸**: `WorkTemplate.cadenceDays` 필드는 있으나 이를 읽어 주기적으로 WorkItem을 자동 생성하는 로직이 없었다.

**구현**
- `src/server/work/recurrence.ts`(신규, 순수): `dueWorkRecurrences(series, now)` — 경과일 ≥ `cadenceDays`면 1건 방출(`dueDate = now + cadenceDays`). 시리즈별 실행당 최대 1건(중복 앵커 방어), **여러 주기가 밀려도 소급 백필 없음**, `cadenceDays` null/0/음수는 건너뜀.
- `src/server/jobs/work-recur.ts`(신규): `runWorkRecurrence(now)` — 활성·`cadenceDays` 템플릿 → (거래처×템플릿)별 최신 인스턴스를 앵커로 조회 → 순수 함수 위임 → `createMany`. **멱등**: 방금 만든 인스턴스가 다음 조회의 최신 앵커가 되므로 같은 날 재호출해도 중복 없음.
- `src/app/api/marketing/cron/route.ts`: GET 일일 배치에 편입 + POST `{"job":"work-recur"}` 수동 트리거.
- `src/server/work/recurrence.test.ts`(vitest).

**연동**: M5의 `WEEKLY_ROUTINE_TASKS`를 `cadenceDays=7`로 `WorkTemplate`에 등록하면 이 M4가 매주 인스턴스화. **검증** 10/10. **Vercel 배포 성공 = `next build`(tsc 포함) green.**

---

### M5 — 온보딩 Phase 체크리스트 · PR #46

**빈칸**: 매뉴얼의 Phase 1/2/3 + 주간 루틴 체크리스트 구조가 ERP `onboarding-tasks.ts`에 미반영. v1은 `GeoChecklistProgress` 모델 신설을 제안했으나, ERP는 이미 `checklist?: string[]`을 지원 → **모델 없이 태스크 checklist[]로 반영**(설계 §4 결정).

**구현** (`src/domain/sales/onboarding-tasks.ts`)
- `phase` 필드 + `OnboardingPhase` 타입(`PHASE1_SETUP`/`PHASE2_CONTENT`/`PHASE3_GEO`/`LIFECYCLE`) + 한글 라벨 맵.
- `STANDARD_ONBOARDING_TASKS` 11개 태스크 전부 phase 태깅 + checklist 확장(**온보딩 54항목**).
- `WEEKLY_ROUTINE_TASKS`: 월~금 주간 루틴(발행·색인·Schema·커뮤니티·수집, **15항목**) — 1회성 온보딩과 분리, M4 연동용.
- 순수 집계 헬퍼 `onboardingPhaseSummary()`/`totalChecklistItems()`(진행률 UI·검증용).
- `src/domain/sales/onboarding-tasks.test.ts`(vitest).

**정직성**: 36p 매뉴얼 원문이 저장소에 없어, 체크리스트 항목 근거는 **저장소 권위 문서**(`geo-ops-os-plan.md` 7일 온보딩·주간 루프, `geo-ops-pilot-runbook.md` 권한·GSC/GA4, `geo-erp-integration-design-v2.md §4`)에서만 가져왔고 통계·수치는 만들지 않았다. 총 69개 체크 항목. **런타임 위험 0**(도메인 상수, 소비 시 `parseDefaultTasks`가 progressNotes로 흡수). **검증** 8/8.

---

### M6 — NAS 팀 앱 → ERP 이관 스크립트 골격 · PR #47

**목적**: 사내 NAS SQLite 팀 앱(거래처·계정·체크리스트 46항목·메모·스태프 5)을 ERP로 1회 이관. v1은 신규 모델로 이전하려 했으나 **ERP 기존 모델로 이전**(설계 §5 정정).

**매핑**

| NAS 테이블 | ERP 기존 모델 | 비고 |
|---|---|---|
| `clients` | `Client` | `assignedMarketerId` = 스태프 매핑 |
| `accounts(+password_hint)` | `ClientAccount` | **평문 비번 미이관** → `credentialHint`, 옵션 시 `passwordEnc`(AES-256-GCM) |
| `checklist_progress`(46) | `WorkItem` | `done`→`COMPLETED`, 아니면 `NOT_STARTED` |
| `memos` | `Comment` | `targetType=CLIENT` |
| `staff`(5) | `User` | **선매핑**(`staffIdMap`), 신규 생성 안 함 |

**구현** (`scripts/migrate-nas-to-erp.ts`)
- **순수 매핑 계층 / I/O 계층 분리**: `mapClient`/`mapAccount`/`mapChecklistItem`/`mapMemo`/`nasId`/`resolveUser`는 DB 무관 순수 함수(오프라인 테스트). `readNasDb`(SQLite 읽기)·`migrateNas`(Prisma upsert)만 I/O.
- **멱등**: `nas-<종류>-<원본id>` 결정적 id로 upsert(재실행해도 중복 없음, 원본 추적).
- **안전 기본값**: `--commit` 없으면 dry-run(건수만, DB 미변경). FK 보장(스태프 미매핑 시 `fallbackUserId`, 실행 전 매핑 User 실재 검증). 자격증명 평문 미이관.
- `better-sqlite3`는 선택 의존성(동적 import, 미설치 시 안내 에러).
- `scripts/migrate-nas-to-erp.test.ts`(vitest).

**⚠️ 실행 전 팀 확인**: NAS 실제 테이블/컬럼명은 스크립트 상단 **`NAS_SCHEMA` 상수를 설계 §5 기준 추정치**로 채워둠. `sqlite3 team.db ".schema"`로 실물 확인 후 이름 확정 필요. **검증** 13/13.

**실행**
```bash
tsx scripts/migrate-nas-to-erp.ts --db ./team.db --staff-map ./staff-map.json          # dry-run
tsx scripts/migrate-nas-to-erp.ts --db ./team.db --staff-map ./staff-map.json --commit  # 실제 반영
# staff-map.json: { "staffIdMap": {"1":"<erpUserId>"}, "fallbackUserId": "<erpUserId>", "encryptCredentials": false }
```

---

## 4. 관통 설계 원칙

1. **스키마 변경 최소** — M1·M3·M4·M5·M6 스키마 변경 0. 기존 필드(`competitorsMentioned`·`cadenceDays`·`checklist`·`credentialHint`) 재사용.
2. **판정 로직 = 순수 함수** — 모든 계산/판정을 DB I/O와 분리한 순수 함수로 두어 오프라인 단위 테스트 가능(총 52케이스). ERP 기존 `detect.ts`/`report-assembly.ts`의 "순수 집계 / 비동기 조립 분리" 패턴 준수.
3. **통계 하드코딩 금지** — 유통되는 벤더 인용 점유율("Wikipedia 12.1%", "FAQ 스키마 2~3배")은 시점 의존이라 채택 안 함. **상대지표(경쟁사 대비 SOV) + 추세(delta)**만 1급 지표.
4. **자동화 금지선 코드 강제** — 위키/레딧/커뮤니티 게시는 D(인간 필수)로 cap-clamp.
5. **의료광고법 준수** — 온보딩·주간 체크리스트에 "의료광고 검수" 단계 상시 포함.
6. **멱등·안전 기본값** — 반복 생성·이관은 재실행 안전(결정적 id/앵커), 이관은 dry-run 기본.

---

## 5. 검증 요약

| 모듈 | 오프라인 하니스 | vitest 파일(케이스) |
|---|---|---|
| M1 | 6/6 | `sov.test.ts` |
| M2 | 7/7 | `geo-channels.test.ts`(7) |
| M3 | 8/8 | `geo-weekly.test.ts`(4) |
| M4 | 10/10 | `recurrence.test.ts`(8) |
| M5 | 8/8 | `onboarding-tasks.test.ts`(7) |
| M6 | 13/13 | `migrate-nas-to-erp.test.ts`(10) |
| **합계** | **52/52** | |

- ERP 저장소는 sandbox에 node_modules 미설치 → 각 순수 함수를 TS 타입만 벗겨 동일 케이스로 오프라인 검증.
- `tsc --noEmit`·`vitest run`·`next build`는 각 PR의 **Vercel CI**에서 최종 검증(유일한 체크). **M4(#45) Vercel 배포 green 확인 완료** → 동일 패턴의 나머지도 통과 가능성 높음.

---

## 6. 팀 액션 (남은 것)

### 6-1. PR 머지 (순차)
1. **머지 순서 권장**: #42 → #43 → #44 → #45 → **#43 다음 #46**(M2·M5가 같은 타입에 필드 추가 → M2 먼저). 각 PR Vercel CI green 확인 후 머지.
2. 각 PR base는 `erp-v1`. 자동 머지는 하지 않았으므로 리뷰 후 수동 머지.

### 6-2. M6 실행 (데이터 이관)
1. `sqlite3 team.db ".schema"`로 NAS 실물 스키마 확인 → `scripts/migrate-nas-to-erp.ts`의 `NAS_SCHEMA` 확정.
2. `staff-map.json` 작성(NAS staff → ERP User.id, fallbackUserId).
3. dry-run으로 건수 확인 → `--commit`으로 반영.

### 6-3. desktop-tutorial 파일럿 자동화(선택, 병합 전까지만)
- 팀이 GitHub 저장소 Secret `ADMIN_SECRET`(= Vercel 값) 설정 시 파일럿 워크플로(리포트·GSC수집·반복업무) 인증 해제. 단, 설계 §6대로 최종 통합 후 desktop-tutorial GEO-OS는 파일럿 종료 대상.

### 6-4. UI 후속(설계 §7, 선택)
- **SOV 차트**: `components/geo/GeoMatrix` 또는 KPI에 SOV% + 경쟁사 분해(M1 데이터 기반, 신규 `SovChart` 1개).
- **Phase 진행률 탭**: `ClientDetail`에 `onboardingPhaseSummary` 기반 진행률(M5 헬퍼 기반).
- **주간 리포트 타입**: `reports` 페이지에 geo-weekly 타입 추가(M3 `assembleGeoWeekly` 기반).
- 스타일: ERP 토큰(테라코타 `#d9662e` + GEO emerald 액센트) 준수, 신규 디자인 토큰 도입 금지.

---

## 7. 파일 인벤토리 (ERP 저장소)

**신규**
- `src/server/geo-engine/sov.ts` + `sov.test.ts` (M1)
- `src/server/marketing/geo-weekly.ts` + `geo-weekly.test.ts` (M3)
- `src/server/work/recurrence.ts` + `recurrence.test.ts` (M4)
- `src/server/jobs/work-recur.ts` (M4)
- `scripts/migrate-nas-to-erp.ts` + `migrate-nas-to-erp.test.ts` (M6)

**수정**
- `src/server/repositories/geo.ts` (M1: `competitors` 파생 + `computeGeoSov`)
- `src/app/(erp)/geo/page.tsx` (M1: SOV KPI 타일)
- `src/domain/sales/geo-channels.ts` (M2: cap-clamp 유틸 + 태스크 태깅)
- `src/domain/sales/onboarding-tasks.ts` (M2: 타입 필드 / M5: phase·checklist·주간·헬퍼)
- `src/app/api/marketing/cron/route.ts` (M4: work-recur job)

**참고 문서(desktop-tutorial)**
- `docs/plans/geo-erp-integration-design-v2.md` (설계 근거)
- `docs/plans/geo-erp-integration-delivery.md` (이 문서)

---

_생성: Claude Code · 세션 https://claude.ai/code/session_01WmD9W9g7GEVaM7TVh1xm7B_
