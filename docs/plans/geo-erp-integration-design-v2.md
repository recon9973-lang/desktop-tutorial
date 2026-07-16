# GEO·SEO 운영 OS → ERP 통합 설계서 v2 (업그레이드)

> 작성일: 2026-07-15 · 대체 대상: 업로드된 "통합 설계서 v1" · 상위: `geo-ops-erp-merge-plan.md`
> 근거: `marketing-agency-erp` 저장소 **실사**(prisma 1557줄 · `src/server/geo-engine/*` · `domain/sales/geo*` · `onboarding-tasks.ts` · `Comment`/`ClientAccount`/`WorkItem` 등)
> **v2 핵심: v1은 ERP를 GEO 그린필드로 가정해 10개 모델·`app/geo` 전체를 신규 생성하려 했으나, ERP는 이미 GEO 전체 스택을 보유. 따라서 "신규 생성" → "기존 매핑 + 순증분만"으로 재설계.**

---

## 0. 왜 v1을 업그레이드하나 (전제 오류 정정)

v1은 다음을 **모른 채** 작성되었다(실사로 반증):
- ❌ v1 가정: "ERP는 GEO 그린필드, desktop-tutorial이 엔진층으로 남아 GitHub Actions로 실측"
- ✅ 실제: **ERP가 이미 4-AI 인용 엔진·질문·판정·저장·매트릭스·GSC수집·크론·RBAC·GEO 탭 UI를 서버에 구현**(`src/server/geo-engine/*`). desktop-tutorial을 엔진으로 유지하면 이중 구축 + 불필요한 egress 우회.

→ v1의 신규 모델·페이지 대부분은 **중복**. v2는 중복을 걷어내고 **진짜 빠진 것만** 얹는다.

---

## 1. 3-시스템 재정의 + ERP 실제 보유 현황

| 시스템 | 정체 | 역할(v2) |
|---|---|---|
| **NAS 팀 앱** (SQLite/Docker, 사내 24h) | 거래처·계정·**체크리스트 46항목**·**메모**·스태프 5 | 데이터 소스(1회 이관) → 이후 오프라인 백업 뷰어 |
| **GEO-OS** (desktop-tutorial, Vercel) | 파일럿에서 검증한 GEO 로직(순수함수) | **로직 도너**(SOV·cap-clamp·리포트·recurrence 이식) 후 파일럿/레퍼런스로 종료 |
| **ERP** (marketing-agency-erp, Next.js+Prisma+Neon) | 운영 본체. GEO 스택 이미 대량 보유 | **최종 통합처**. 기존 모델에 순증분 얹음 |

### ERP가 이미 가진 것 (v1이 신규 생성하려던 것들)
| ERP 기존 | 위치 | v1이 만들려던 중복 모델 |
|---|---|---|
| 4-AI 엔진 어댑터·runner·detect | `src/server/geo-engine/*` | (엔진층을 desktop-tutorial에 유지 — 불필요) |
| `GeoQuestion`(5유형 SOP) / `GeoAnswerRecord`(engine·appeared·cited·competitorsMentioned) | prisma | `TrackedQuery`/`AiExposureSnapshot` |
| `ClientAccount`(**usernameEnc/passwordEnc 암호화** + `credentialHint` + channelType) + `ChannelConnection`(GSC/GA4 OAuth) + `ChannelType` | prisma | `GeoChannel`(평문 힌트 — 더 위험) |
| `WorkItem`+`WorkTemplate`(cadenceDays) + `onboarding-tasks.ts`(**checklist: string[]**) | prisma·domain | `GeoTask`/`GeoChecklistProgress` |
| `ContentPlan`(month·faq·qa·complianceRisk·거래처포털컨펌·publishedUrl) | prisma | `GeoContentItem` |
| `ChannelMetric`(채널×지표×일) | prisma | `GeoMetric` |
| `Report`(거래처 월간)·`WeeklyReport`(직원) | prisma | `GeoReport`(부분 중복) |
| **`Comment`**(targetType=CLIENT·WORK·REPORT) | prisma | `ClientNote` |
| `Client.assignedMarketerId`(담당자 필터) + RBAC(`AccessScope`) | prisma·`domain/access-control.ts` | (담당자 연결 — 이미 있음) |
| `automationLevel A~D` + 플레이북 | `domain/sales/geo-channels.ts` | (자동화레벨 — 이미 있음) |

**결론: v1의 10개 신규 모델 중 8개가 중복.** 신규는 SOV 저장(선택)·자동화 실행로그(선택)뿐.

---

## 2. 진짜 순증분 (v2 업그레이드 대상)

ERP에 실제로 **없는 것**만. 대부분 GEO-OS **순수 함수 이식**.

| # | 순증분 | ERP 현황 | 이식/구현 | 스키마 |
|---|---|---|---|---|
| **U1** | **SOV(경쟁사 점유율)** ★ | `competitorsMentioned` 기록만, 집계 없음 | `geo-sov.js buildSov` → `repositories/geo.ts` `geoSov()` + KPI 타일 | 무(파생) / 추이 저장 시 `AiExposureSov` 롤업만 |
| **U2** | 플레이북→태스크 **cap-clamp** | 플레이북·automationLevel 있으나 클램프 없음 | `geo-templates.js clampLevel` → `geo-channels.ts` 태스크 생성 시 D강등 강제 | `WorkItem.automationLevel?`(선택) |
| **U3** | 거래처 **GEO 주간 리포트** | 월간·직원주간만 | `geo-report.js buildReport` → `server/marketing/` | `Report.reportType?`(선택) |
| **U4** | 태스크 **반복 자동생성** | cadenceDays 필드만 | `geo-recur.js dueRecurrences` → 크론 job 추가 | 무(cadenceDays 활용) |
| **U5** | **Phase 체크리스트(46항목)** | onboarding-tasks `checklist[]` 존재하나 매뉴얼 46항목 미반영 | 매뉴얼 Phase1/2/3/주간 → `STANDARD_ONBOARDING_TASKS` 확장(checklist[]) | 무 |
| **U6** | **NAS 앱 이관** | — | SQLite→ERP **기존 모델**(Client·ClientAccount·Comment·WorkItem)로 이전 스크립트 | 무 |
| **U7** | 메모 | `Comment`(CLIENT) 존재 | UI에서 Comment 연결만(신규 모델 X) | 무 |
| **U8**(선택) | AI Overview/네이버 AI 어댑터 | 4엔진만 자동 | `geo-engine/engines.ts` 어댑터 추가 | engine 값 추가 |
| **U9**(선택) | 자동화 실행 로그 | 크론 있으나 per-run 로그 테이블 미확인 | 경량 로그 모델 | `GeoAutomationRun`(선택) |

**즉 스키마 변경은 최대 4개 선택 필드/모델**(AiExposureSov 롤업·WorkItem.automationLevel·Report.reportType·GeoAutomationRun), U1·U4·U5·U6·U7은 **스키마 무변경**.

---

## 3. 스키마 설계 (v1의 10모델 → v2 최소 변경)

**신규 생성 안 함**: `GeoChannel·GeoTask·GeoChecklistProgress·GeoContentItem·GeoMetric·TrackedQuery·AiExposureSnapshot·ClientNote·GeoReport` (전부 ERP 기존 모델로 대체).

**추가(전부 선택·비파괴)**:
```prisma
// U1 추이 저장이 필요할 때만(파생으로 충분하면 생략)
model AiExposureSov {
  id String @id @default(cuid())
  clientId String
  date DateTime @db.Date
  selfShare Float
  competitors Json   // { name: mentions }
  @@unique([clientId, date])
  @@index([clientId, date])
}
// U2: WorkItem 에 필드 1개
// automationLevel String? // A|B|C|D (cap-clamp 결과)
// U3: Report 에 필드 1개
// reportType String @default("monthly") // monthly | geo-weekly
// U9(선택): 자동화 실행 로그
model GeoAutomationRun {
  id String @id @default(cuid())
  name String        // exposure_check | metrics_collect | geo_weekly | task_recur
  clientId String?
  status String      // success | error
  detail String?
  ranAt DateTime @default(now())
  @@index([name, ranAt])
}
```
> intel 별도 스키마·`AiExposure*` 대량 신설 불필요 — ERP `GeoAnswerRecord`가 이미 스냅샷 역할. SOV만 파생/롤업.

---

## 4. Phase 체크리스트(매뉴얼 46항목) 매핑 — U5

v1은 `GeoChecklistProgress` 모델 신설을 제안했으나, ERP `onboarding-tasks.ts`가 이미 **`checklist?: string[]`**을 지원한다. 매뉴얼(36p)의 Phase 항목을 **온보딩 태스크 템플릿 + checklist 배열**로 반영:

| Phase | 매뉴얼 근거 | ERP 반영 |
|---|---|---|
| Phase 1 계정설정(19) | 2부 5~11장 | `STANDARD_ONBOARDING_TASKS`에 START 기준 태스크 + checklist[] |
| Phase 2 콘텐츠(10) | 2부 7~11장 | 콘텐츠 태스크(WorkCategory.CONTENT) + `ContentPlan` 연동 |
| Phase 3 GEO확인(8) | 3부 15장·4부 | GEO 태스크 + `runGeoWatch` 트리거 |
| 주간루틴(12) | 4부 17장 | `WorkTemplate.cadenceDays=7` + U4 반복생성 |

> 진행률 UI는 WorkItem 상태 집계 또는 태스크의 checklist 토글로. **별도 진행 모델 불필요**(단, 팀이 "태스크 카드보다 가벼운 체크박스"를 강하게 원하면 경량 `ChecklistTick(workItemId, idx, done)` 1테이블만 추가 — §9 열린결정).

---

## 5. NAS 앱 → ERP 이관 — U6 (v1 스크립트 정정)

v1 스크립트는 `GeoChannel`·`GeoChecklistProgress`·`ClientNote`(신규모델)로 이전하려 했다. **정정: ERP 기존 모델로 이전**한다.

| NAS 테이블 | v1 대상(❌) | v2 대상(✅ ERP 기존) |
|---|---|---|
| clients | (Client) | `Client`(assignedMarketerId=스태프 매핑) |
| accounts(+password_hint) | GeoChannel | **`ClientAccount`**(credentialHint + 필요시 passwordEnc 암호화) |
| checklist_progress(46) | GeoChecklistProgress | `WorkItem`(온보딩 태스크) 또는 체크 토글 |
| memos | ClientNote | **`Comment`**(targetType=CLIENT) |
| staff(5) | — | `User`(Role: MARKETER) + AccessScope |

- 스크립트 위치: ERP `scripts/migrate-nas-to-erp.ts`(better-sqlite3 → prisma). 1회성, 멱등(upsert), `nas-` 접두 id로 원본 추적.
- 스태프 매핑 테이블(`staffIdMap`) 선행 필요(NAS staff → ERP User.id).

---

## 6. 아키텍처 정정 — 엔진은 ERP 내장

```
v1(❌): ERP(소비) ── clinicId ──> desktop-tutorial(엔진, GitHub Actions egress)
v2(✅): ERP 단독 — geo-engine 서버 내장. 실측·수집·리포트·크론 전부 ERP 안에서.
         desktop-tutorial GEO-OS = 로직 도너(이식 후 종료)
```
- ERP는 풀 서버(Next.js)라 **AI 엔진·GSC를 서버에서 직접 호출** → GitHub Actions egress 우회 불필요.
- 크론: 기존 `src/app/api/marketing/cron/route.ts`(Vercel cron + 시크릿 POST)에 GEO job 추가(이미 `geo-watch` 월1회 존재).
- desktop-tutorial의 GEO-OS/워크플로/콘솔/`ADMIN_SECRET`은 **이관하지 않음**(파일럿 종료).

---

## 7. UI 정정 — 기존 GEO 모듈 확장 (신규 app/geo 안 만듦)

v1은 `app/geo/` 전체 신설을 제안했으나 ERP는 이미 `src/app/(erp)/geo/page.tsx` + `components/geo/*`(GeoMatrix·GeoTabs·GeoAutoWatch·GeoTools·GeoChannelGuide·GeoTrendBars·GeoLlmsTxt) + 탭형 `ClientDetail.tsx`를 보유.
- **SOV(U1)**: `components/geo/GeoMatrix` 또는 KPI 타일에 SOV% + 경쟁사 분해 추가. (신규 `SovChart` 1개 정도만)
- **Phase 체크리스트(U5)**: `ClientDetail` 탭에 진행률 표시(WorkItem 집계).
- **주간 리포트(U3)**: `reports` 페이지에 geo-weekly 타입 추가.
- 스타일: ERP 토큰(테라코타 `#d9662e` + GEO emerald 액센트) 준수. 신규 디자인 토큰 도입 금지.

---

## 8. 로드맵 재작성 (v1 6주 3단계 → v2 순증분 순)

| 단계 | 작업 | ERP 위치 | 스키마 |
|---|---|---|---|
| **M1** | **SOV** 집계 + KPI 타일 | `repositories/geo.ts`·`components/geo/` | 무(또는 롤업 1) |
| **M2** | 플레이북 **cap-clamp** 태스크 | `domain/sales/geo-channels.ts`·`actions/work` | WorkItem 필드 1 |
| **M3** | 거래처 **GEO 주간 리포트** | `server/marketing/`·`reports` | Report 필드 1 |
| **M4** | 태스크 **반복 생성** | `api/marketing/cron` job | 무 |
| **M5** | **Phase 체크리스트(46)** 반영 | `onboarding-tasks.ts` | 무 |
| **M6** | **NAS 이관** 스크립트 | `scripts/migrate-nas-to-erp.ts` | 무 |
| **M7** | 메모(Comment) UI 연결 | `ClientDetail` | 무 |
| M8(선택) | AI Overview/네이버 AI 어댑터·자동화 로그 | `geo-engine`·(GeoAutomationRun) | engine값/모델1 |

**M1(SOV) 최우선** — 순증분 최대·스키마 0·기존 데이터 즉시. v1의 "P1 스키마 대량 신설 + migrate"는 폐기.

---

## 9. 유지할 v1 원칙 + 열린 결정

**v1에서 유지(좋음)**:
1. `clinicId = ERP Client.id` 단일 키. 기존 `pain/skin`은 실제 CUID로 교체.
2. **채널 자동화레벨 상한 불변**(위키/레딧 D → A/B 승격 불가, 서버 강제).
3. **통계 하드코딩 금지**(SOV 등 실측만).
4. **의료광고법 가드**(발행 전 검수) — ERP `ContentPlan.complianceRisk`·`actions/geo.ts` 이미 담당.

**열린 결정(사용자 확인 필요)**:
- **Q1. Phase 체크리스트 저장**: (a) 온보딩 WorkItem + checklist 토글(모델 0) / (b) 경량 `ChecklistTick` 1테이블. → UX 선호.
- **Q2. SOV 저장**: (a) 매 조회 파생(저장 0) / (b) 일 롤업 `AiExposureSov`(추이 그래프용).
- **Q3. NAS 이관 시점**: M1~M4(순증분) 후 vs 지금 먼저.
- **Q4. ERP 브랜치**: `erp-v1` 라이브 → 순증분별 신규 브랜치(`feat/geo-sov` 등) PR.

---

## 10. 요약
- v1의 방향(ERP 통합)은 옳으나, **ERP 그린필드 가정으로 대량 중복 설계** → v2에서 정정.
- 실제 작업 = **순수 함수 4개 이식(SOV·cap-clamp·리포트·recurrence) + 매뉴얼 체크리스트 반영 + NAS 이관 + 메모 연결**. 스키마 변경 최소(선택 4).
- 착수: **M1(SOV)** — ERP `feat/geo-sov` 브랜치, 스키마 무변경.

*통합 설계서 v2 · 2026-07-15 · v1 대체 · 근거: ERP 실사*
