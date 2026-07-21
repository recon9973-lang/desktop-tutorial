# GEO → ERP 통합 인도(Delivery) 문서 — 전체 작업 기록

> 최종 갱신 2026-07-16 · 기준 설계서: [`geo-erp-integration-design-v2.md`](geo-erp-integration-design-v2.md) · 러닝 요약: [`geo-ops-session-summary.md`](geo-ops-session-summary.md)
>
> **"GEO 운영 OS → VENOM ERP 병합"** 작업의 완전한 기록. 코어 6개 모듈(M1~M6) + UI 후속 3종을
> 모두 구현·검증·**erp-v1 머지 완료**했다. 이 문서 하나로 무엇을·왜·어떻게·검증·머지·남은 것을 추적한다.

---

## 0. 한눈에 보기 — 전부 머지 완료 ✅

### 코어 모듈 (M1~M6)
| 모듈 | 내용 | PR | 브랜치 | 머지 SHA | 스키마 | 오프라인 |
|---|---|---|---|---|---|---|
| **M1** | 경쟁사 SOV 집계 + KPI 타일 | [#42](https://github.com/recon9973-lang/marketing-agency-erp/pull/42) | `feat/geo-sov` | `041dc4a` | 0 | 6/6 |
| **M2** | 채널 자동화 cap-clamp | [#43](https://github.com/recon9973-lang/marketing-agency-erp/pull/43) | `feat/geo-capclamp` | `c957b3a` | 0 | 7/7 |
| **M3** | 거래처 GEO 주간 리포트(조립) | [#44](https://github.com/recon9973-lang/marketing-agency-erp/pull/44) | `feat/geo-weekly` | `37eff64` | 0 | 8/8 |
| **M4** | 반복 업무 자동 생성(cadenceDays) | [#45](https://github.com/recon9973-lang/marketing-agency-erp/pull/45) | `feat/geo-recur` | `0e76ea8` | 0 | 10/10 |
| **M5** | 온보딩 Phase 체크리스트 | [#46](https://github.com/recon9973-lang/marketing-agency-erp/pull/46) | `feat/geo-onboarding-checklist` | `3d570de` | 0 | 8/8 |
| **M6** | NAS→ERP 이관 스크립트 골격 | [#47](https://github.com/recon9973-lang/marketing-agency-erp/pull/47) | `feat/geo-nas-migration` | `5958805` | 0 | 13/13 |

### UI 후속 (설계 §7)
| UI | 내용 | PR | 브랜치 | 머지 SHA | 오프라인 |
|---|---|---|---|---|---|
| **U-SOV** | SOV 차트(자사/경쟁사 점유 바 + 경쟁사별 분해) | [#48](https://github.com/recon9973-lang/marketing-agency-erp/pull/48) | `feat/geo-sov-chart` | `7194e1b` | 13/13 |
| **U-Phase** | 온보딩 Phase 진행률 탭(거래처 상세) | [#49](https://github.com/recon9973-lang/marketing-agency-erp/pull/49) | `feat/geo-phase-tab` | `27ba7e2` | 11/11 |
| **U-Weekly** | GEO 주간 리포트 UI(reports 서브라우트) | [#50](https://github.com/recon9973-lang/marketing-agency-erp/pull/50) | `feat/geo-weekly-ui` | `5a489a6` | 19/19 |

- **대상 저장소**: `recon9973-lang/marketing-agency-erp` (Next.js 15 App Router · Prisma 6 · Neon Postgres · pnpm), base 브랜치 `erp-v1`.
- **9개 PR 전부 squash-merge 완료**, 전 PR Vercel 배포(=`next build`+tsc) green.
- **총 오프라인 검증 95케이스**(코어 52 + UI 43). ERP node_modules 미설치 환경이라 순수-로직 하니스로 검증, `tsc`/`vitest`/`next build`는 Vercel CI에서 최종 확인.
- **스키마 변경 0** (전 모듈 기존 필드 재사용/파생).

---

## 1. 배경과 목표

- **출발점**: 별도 저장소 `desktop-tutorial`에 파일럿으로 구축한 **GEO 운영 OS**(거래처 AI 인용 모니터링·업무·성과·리포트, 자동화 A~D 등급)를, 이미 거래처·계약·업무·이미지스튜디오를 갖춘 **VENOM ERP**(`marketing-agency-erp`)에 병합하는 것이 최종 목적("결국 목적은 완료 후 베놈 ERP와 병합").
- **핵심 정정(설계서 v2)**: v1 설계서는 ERP를 그린필드로 가정해 신규 모델(`GeoChannel`·`GeoChecklistProgress`·`ClientNote`)을 대거 신설하려 했다. **ERP 실사 결과 이미 4-AI GEO 파이프라인**(`geo-engine/*`·`GeoQuestion`·`GeoAnswerRecord`·`ContentPlan`·`WorkItem`·`WorkTemplate`·`ClientAccount`·`Comment`)**이 있었다.** → 병합은 "신규 시스템 구축"이 아니라 **기존 모델 위에 빠진 조각(순수 함수)만 이식**하는 소규모 작업으로 재정의.

---

## 2. 아키텍처 정정 (설계서 §6)

```
v1(❌): ERP(소비) ── clinicId ──> desktop-tutorial(엔진, GitHub Actions egress 우회)
v2(✅): ERP 단독 — geo-engine 서버 내장. 실측·수집·리포트·크론 전부 ERP 안에서.
         desktop-tutorial GEO-OS = 로직 도너(이식 후 파일럿 종료)
```

- ERP는 풀 서버(Next.js)라 AI 엔진·GSC를 서버에서 직접 호출 → GitHub Actions egress 우회 불필요.
- 크론은 기존 `src/app/api/marketing/cron/route.ts`(Vercel cron GET + 시크릿 POST)에 GEO job을 추가(M4가 이 경로 사용).
- desktop-tutorial의 GEO-OS/워크플로/콘솔/`ADMIN_SECRET`은 **이관하지 않음**(파일럿 종료 대상).

---

## 3. 코어 모듈 상세 (M1~M6)

### M1 — 경쟁사 SOV(Share of Voice) · #42
**빈칸**: `GeoAnswerRecord.competitorsMentioned`(Json)에 경쟁사 언급을 기록만 하고 SOV로 집계 안 함.
**구현**
- `src/server/geo-engine/sov.ts`(신규, 순수): `buildSov(cells)` = 자사 출현 / (자사+경쟁사 언급 합). 언급 0이면 `null`. `asCompetitors(json)` Json→`string[]` 안전 변환.
- `src/server/repositories/geo.ts`: `GeoCell`에 `competitors: string[]` 파생 + `computeGeoSov(rows)`(추가 쿼리 없음, RETIRED 제외).
- `src/app/(erp)/geo/page.tsx`: KPI 타일 "경쟁사 SOV"(열세 <50% amber).
- `sov.test.ts`(vitest). **정직성**: 절대 인용% 없음, 상대지표만. **6/6**.

### M2 — 채널 자동화 cap-clamp · #43
**빈칸**: 채널별 `automationLevel`(cap)은 있으나 업무 레벨이 cap을 넘지 못하게 강제하는 로직 없음.
**구현**(`src/domain/sales/geo-channels.ts`)
- `AUTOMATION_RANK`(A>B>C>D) + `clampLevel(level,cap)`(cap 초과면 강등, 유지) + `channelCap()` + `resolveAiChannelTasks()`(capped 플래그) + `riskyAutomationViolations()`(불변식 점검).
- `AI_CHANNEL_TASKS` 8종 구조화 태깅. `onboarding-tasks.ts` 타입에 `automationLevel?`/`channel?` 추가.
- **설계 정합**: 위키·레딧·커뮤니티 게시=인간 필수를 코드가 강제. **7/7**.

### M3 — 거래처 GEO 주간 리포트 · #44
**빈칸**: 월간 리포트·직원 개인 주간만 있고 거래처 단위 GEO 주간 리포트 없음.
**구현**(`src/server/marketing/geo-weekly.ts`, 신규)
- `buildGeoWeekly(input)`(순수): 출현/인용·SOV·성과 델타(순위 낮을수록 개선)·업무 → keyWins/risks/nextActions. **통계 미생성**.
- `assembleGeoWeekly(clientId,weekStart,weekEnd,opts?)`: `geoMonthlySummary`+WorkItem 집계. SOV 선택 주입(M1). 저장 안 함.
- `geo-weekly.test.ts`(vitest). **용어 충돌 방지**: `WeeklyReport`(직원)≠GEO 주간(거래처). **8/8**.

### M4 — 반복 업무 자동 생성 · #45
**빈칸**: `WorkTemplate.cadenceDays`를 읽어 주기적 WorkItem을 만드는 로직 없음.
**구현**
- `src/server/work/recurrence.ts`(신규, 순수): `dueWorkRecurrences(series,now)` — 경과일 ≥ cadenceDays면 1건(dueDate=now+cadenceDays), 시리즈별 실행당 1건, **소급 백필 없음**, null/0/음수 스킵.
- `src/server/jobs/work-recur.ts`(신규): `runWorkRecurrence(now)` — 활성·cadenceDays 템플릿 → (거래처×템플릿) 최신 인스턴스 앵커 → createMany. **멱등**(방금 만든 게 다음 앵커).
- `cron/route.ts`: GET 일일 배치 + POST `{"job":"work-recur"}`. `recurrence.test.ts`. **10/10**. Vercel green 확인.

### M5 — 온보딩 Phase 체크리스트 · #46
**빈칸**: 매뉴얼 Phase 1/2/3+주간 체크리스트 구조 미반영. v1은 `GeoChecklistProgress` 신설 제안 → **모델 없이 checklist[]로**(설계 §4).
**구현**(`src/domain/sales/onboarding-tasks.ts`)
- `phase` 필드 + `OnboardingPhase` 타입 + 라벨. `STANDARD_ONBOARDING_TASKS` 11개 전부 phase 태깅 + checklist 확장(54항목). `WEEKLY_ROUTINE_TASKS`(월~금 15항목, cadenceDays=7로 M4 연동). `onboardingPhaseSummary()`/`totalChecklistItems()` 순수 헬퍼.
- `onboarding-tasks.test.ts`. **정직성**: 36p 매뉴얼 원문이 저장소에 없어 항목 근거는 저장소 권위 문서(ops-plan·pilot-runbook·design-v2 §4)에서만. 통계 미생성. **런타임 위험 0**. **8/8**.

### M6 — NAS 팀 앱 → ERP 이관 스크립트 골격 · #47
**목적**: 사내 NAS SQLite(거래처·계정·체크리스트46·메모·스태프5)를 ERP 기존 모델로 1회 이관.
**매핑**: clients→`Client`(assignedMarketerId) / accounts(+hint)→`ClientAccount`(평문 미이관·credentialHint·옵션 passwordEnc) / checklist_progress→`WorkItem`(done→COMPLETED) / memos→`Comment`(CLIENT) / staff→`User`(선매핑 staffIdMap).
**구현**(`scripts/migrate-nas-to-erp.ts`)
- 순수 매핑(`mapClient`/`mapAccount`/`mapChecklistItem`/`mapMemo`/`nasId`/`resolveUser`) ↔ I/O(`readNasDb`·`migrateNas`) 분리. 멱등(`nas-` 접두 결정적 id). `--commit` 없으면 dry-run. FK 보장(fallbackUserId+실재 검증). 자격증명 평문 미이관. `better-sqlite3` 선택 의존성(동적 import).
- ⚠️ NAS 실제 테이블/컬럼명은 상단 **`NAS_SCHEMA` 상수를 설계 §5 기준 추정치**로 채움 — 실물 `.schema` 확인 후 확정 필요.
- `migrate-nas-to-erp.test.ts`. **13/13**.

---

## 4. UI 후속 상세 (설계 §7) — #48·#49·#50

> 세 UI 후속은 동일 세션에서 병렬 브랜치로 작성 → CI green 확인 후 순차 머지. 모두 **스키마 0, 신규 조회 0**(페이지가 이미 로드/계산한 값 소비).

### U-SOV — 경쟁사 SOV 차트 · #48
- `src/components/geo/SovChart.tsx`(신규, 서버 컴포넌트): 자사 점유율 헤드라인(열세<50% amber) + 자사(emerald)/경쟁사(slate) 2세그먼트 바 + 경쟁사별 언급 상대 막대. 순수 뷰모델 `buildSovView(sov)` 분리.
- `src/app/(erp)/geo/page.tsx`: 관측 현황 탭 배선. `SovChart.test.ts`(vitest 5). **13/13**.
- 데이터: M1 `computeGeoSov` 파생값(page가 이미 계산한 `sov` 전달만).

### U-Phase — 온보딩 Phase 진행률 탭 · #49
- `src/components/clients/ClientOnboardingProgress.tsx`(신규): 전체 + Phase(1/2/3·라이프사이클)별 완료율 바 + 태스크 체크리스트(완료=취소선/emerald, 미생성=점선). 순수 `buildOnboardingProgress(works)` — 표준 태스크↔WorkItem **제목 매칭**, Phase 그룹·완료율. 진행 바 terracotta→100% emerald.
- `src/components/clients/ClientDetail.tsx`: "Phase 진행률" 탭 추가. `ClientOnboardingProgress.test.ts`(vitest 6). **11/11**.
- 데이터: M5 phase 태깅 + ClientDetail이 이미 로드한 `works` 소비(신규 조회 0).

### U-Weekly — GEO 주간 리포트 UI · #50
- `src/components/reports/GeoWeeklyReport.tsx`(신규): 주 라벨 + 요약 + 성과(emerald)/리스크(amber)/다음 액션(brand) 3열.
- `src/app/(erp)/reports/geo-weekly/page.tsx`(신규): 거래처 탭 → 이번 주 창 → `listGeoMatrix→computeGeoSov`(M1 sovPct 주입) → `assembleGeoWeekly` 조립·렌더. 미보장 고지 상시.
- `src/server/marketing/week-window.ts`(신규, 순수): `currentWeekWindow`(월~일, 로컬 달력 기반 라벨로 UTC 이탈 방지). `week-window.test.ts`(vitest 5).
- `src/app/(erp)/reports/page.tsx`: 진입 링크. **19/19**(TZ 독립 확인 UTC/KST/NY).
- 데이터: M3 `assembleGeoWeekly` + M1 SOV 주입(파생·비영속).

---

## 5. 관통 설계 원칙

1. **스키마 변경 0** — 전 모듈 기존 필드(`competitorsMentioned`·`cadenceDays`·`checklist`·`credentialHint`) 재사용/파생.
2. **판정 로직 = 순수 함수** — 계산/판정을 DB I/O와 분리 → 오프라인 단위 테스트(총 95케이스). ERP `detect.ts`/`report-assembly.ts`의 "순수 집계/비동기 조립 분리" 패턴 준수.
3. **통계 하드코딩 금지** — 벤더 인용 점유율("Wikipedia 12.1%" 등) 미채택. 상대지표(SOV) + 추세(delta)만 1급.
4. **자동화 금지선 코드 강제** — 위키/레딧/커뮤니티=D(인간 필수) cap-clamp.
5. **의료광고법 준수** — 체크리스트에 "의료광고 검수" 상시 포함, "미보장 고지" 상시 표기.
6. **멱등·안전 기본값** — 반복 생성·이관은 재실행 안전(결정적 id/앵커), 이관은 dry-run 기본, 자격증명 평문 미이관.
7. **디자인 토큰 준수** — 테라코타 `#d9662e` + GEO emerald, 신규 토큰 도입 금지, a11y(텍스트 병기·sr-only·대비 3:1↑).

---

## 6. 검증 요약

| 구분 | 모듈 | 오프라인 | vitest(케이스) |
|---|---|---|---|
| 코어 | M1 | 6/6 | `sov.test.ts` |
| | M2 | 7/7 | `geo-channels.test.ts`(7) |
| | M3 | 8/8 | `geo-weekly.test.ts`(4) |
| | M4 | 10/10 | `recurrence.test.ts`(8) |
| | M5 | 8/8 | `onboarding-tasks.test.ts`(7) |
| | M6 | 13/13 | `migrate-nas-to-erp.test.ts`(10) |
| UI | U-SOV | 13/13 | `SovChart.test.ts`(5) |
| | U-Phase | 11/11 | `ClientOnboardingProgress.test.ts`(6) |
| | U-Weekly | 19/19 | `week-window.test.ts`(5) |
| **합계** | | **95/95** | |

- 순수 함수를 TS 타입만 벗겨 동일 케이스로 오프라인 검증. `tsc`/`vitest`/`next build`는 각 PR **Vercel CI**에서 최종 검증 — **9개 PR 전부 green**.

---

## 7. 병합 진행 결과

- **9개 PR 전부 squash-merge 완료**(erp-v1). 최근 커밋 순: `5a489a6`(#50) → `27ba7e2`(#49) → `7194e1b`(#48) → `5958805`(#47) → … → `041dc4a`(#42).
- **충돌 1건 해소**: M2(#43)와 M5(#46)가 같은 `OnboardingTaskTemplate` 타입에 optional 필드 추가 → **세 필드(`phase`·`automationLevel`·`channel`) 모두 유지**로 병합(마커 0 확인).
- UI 3종은 서로 disjoint 파일(geo/page·ClientDetail·reports)이라 충돌 없이 안착.
- 산출물 파일 존재를 erp-v1에서 직접 확인(`git cat-file -e`) 완료.

---

## 8. 남은 것 (팀 액션)

### 8-1. M6 실행 (NAS 데이터 이관)
1. NAS SQLite **백업본** 확보 — 상시 연결 불필요(§부록 A). 앱 쓰는 중 원본 복사 금지:
   ```bash
   sqlite3 /volume1/docker/<앱>/team.db ".backup '/volume1/team-backup.db'"
   ```
2. `sqlite3 team-backup.db ".schema"` → `NAS_SCHEMA`(스크립트 상단) 테이블/컬럼명 확정.
3. `staff-map.json` 작성(NAS staff→ERP User.id, fallbackUserId).
4. dry-run으로 건수 확인 → `--commit` 반영.

### 8-2. 파일럿 종료 수순
- 병합 완료로 desktop-tutorial GEO-OS는 파일럿 종료 대상(설계 §6). 팀이 GitHub Secret `ADMIN_SECRET`로 파일럿을 잠깐 더 돌릴지, 즉시 종료할지 결정.

---

## 9. 파일 인벤토리 (ERP 저장소)

**신규 (코어)**
- `src/server/geo-engine/sov.ts` + `sov.test.ts` (M1, U-SOV용 `rankCompetitors`는 #48에서 별도 뷰모델)
- `src/server/marketing/geo-weekly.ts` + `geo-weekly.test.ts` (M3)
- `src/server/work/recurrence.ts` + `recurrence.test.ts` (M4)
- `src/server/jobs/work-recur.ts` (M4)
- `scripts/migrate-nas-to-erp.ts` + `migrate-nas-to-erp.test.ts` (M6)

**신규 (UI)**
- `src/components/geo/SovChart.tsx` + `SovChart.test.ts` (#48)
- `src/components/clients/ClientOnboardingProgress.tsx` + `ClientOnboardingProgress.test.ts` (#49)
- `src/components/reports/GeoWeeklyReport.tsx` (#50)
- `src/app/(erp)/reports/geo-weekly/page.tsx` (#50)
- `src/server/marketing/week-window.ts` + `week-window.test.ts` (#50)

**수정**
- `src/server/repositories/geo.ts` (M1)
- `src/app/(erp)/geo/page.tsx` (M1 SOV KPI, #48 SovChart 배선)
- `src/domain/sales/geo-channels.ts` (M2)
- `src/domain/sales/onboarding-tasks.ts` (M2 타입 / M5 phase·checklist·주간·헬퍼)
- `src/app/api/marketing/cron/route.ts` (M4 work-recur job)
- `src/components/clients/ClientDetail.tsx` (#49 탭)
- `src/app/(erp)/reports/page.tsx` (#50 링크)

**참고 문서 (desktop-tutorial `docs/plans/`)**
- `geo-erp-integration-design-v2.md` (설계 근거)
- `geo-erp-integration-delivery.md` (이 문서)
- `geo-erp-next-session-prompt.md` (다음 세션 이어가기)
- `geo-ops-session-summary.md` (러닝 요약 §8·§9)

---

## 부록 A — NAS 접근 가이드 (LAN vs 온라인)

**핵심**: M6 마이그레이션은 NAS 상시 연결이 아니라 **SQLite `.db` 파일 1개**만 필요. `team.db`는 소규모라 **어느 경로든 무방**, File Station 다운로드가 가장 간단(LAN·온라인 동일).

**장단점**
| 축 | LAN | 온라인 |
|---|---|---|
| 속도 | 🟢 최상(기가 ~110MB/s) | 🟡 회선 업로드에 종속 |
| 지연 | 🟢 <1ms | 🟡 10~40ms, 릴레이 시↑↑ |
| 보안 | 🟢 외부 노출 0 | 🔴 인터넷 노출(2FA·방화벽 필수) |
| 가용성 | 🔴 현장/VPN 안에서만 | 🟢 어디서나 |

**속도(대략)**: LAN 유선 ~110MB/s · Wi-Fi 30~70 · VPN후 SMB=회선 업로드만큼 · SFTP 20~100(NAS CPU 병목) · QuickConnect 직결=회선근접 / **릴레이 fallback=1~3MB/s(급감)**. → 온라인 속도는 "NAS 회선 업로드"에 종속, QuickConnect는 직결/릴레이 두 얼굴. SMB 인터넷 직개방은 비권장(VPN 안 SMB 또는 SFTP).

**연결 조합별**
- **양쪽 다**(권장 실무): 접속 주소에 따라 경로 자동 선택(QuickConnect: LAN→WAN직결→릴레이). 편의 최고 ↔ 공격면 최대.
- **LAN만**: 안전·빠름, 현장/VPN 필수. 원격·외부 자동화 불가.
- **온라인만**: 어디서나 되나 느릴 수 있고 노출 부담. 사내에서도 로컬 IP 병행 안 하면 인터넷 우회로 느려질 수 있음.
- **둘 다 없음**: 물리 접근/관리콘솔만 → 최소 File Station이라도 열어야 반출 가능.

---

## 부록 B — 작업 연대기

1. **파일럿(직전 세션들)**: desktop-tutorial GEO 운영 OS 구축·배포(P1 8항목·MVP 9항목), venom-new-site.vercel.app/geo-ops.html.
2. **설계 v2**: 업로드된 통합 설계서 v1의 그린필드 전제오류를 ERP 실사로 정정 → `geo-erp-integration-design-v2.md`.
3. **코어 이식 M1~M6**: 순수 함수 위주 이식, PR #42~#47(오프라인 52케이스). base erp-v1.
4. **문서화**: 인도 문서 + 다음 세션 프롬프트 + 러닝 요약 §8·§9.
5. **머지**: PR #42~#47 순차 squash-merge. M2↔M5 타입 충돌 세 필드 유지로 해소(M5 #46은 사용자 직접 머지분 포함).
6. **UI 후속**: SOV 차트·Phase 진행률·주간 리포트 UI를 병렬 작성 → #48·#49·#50 CI green 확인 후 머지(오프라인 43케이스). (중복 착수분은 폐기하고 기존 green PR 채택.)
7. **NAS 접근 가이드**: LAN vs 온라인 장단점·속도·조합별 정리(부록 A).
8. **현재**: 코어+UI 전부 erp-v1 머지 완료. 남은 것 = M6 실제 실행(NAS 백업본 필요) + 파일럿 종료 수순.

---

_생성: Claude Code · 세션 https://claude.ai/code/session_01WmD9W9g7GEVaM7TVh1xm7B_
