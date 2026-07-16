# GEO-OS → 베놈 ERP 병합 계획서

> 작성일: 2026-07-15 · 대상: `marketing-agency-erp`(Next.js 15 + Prisma 6 + next-auth, 브랜치 `erp-v1`=라이브) ← `desktop-tutorial`의 GEO-OS
> 조사 근거: ERP 저장소 실사(prisma 1557줄 · `src/server/geo-engine/*` · `src/domain/sales/geo*` 등)
> **핵심 결론: ERP는 이미 4-AI 인용 파이프라인을 실제 구현해 두었다. 병합 = 중복 재구축 금지 + 순증분 5개만 이식.** 예상보다 작은 작업.

---

## 0. 결론 (BLUF)

1. ERP에 **이미 있는 것(재사용)**: 4-AI 엔진 어댑터(ChatGPT·Perplexity·Gemini·Claude 공식 API), 자동 관측 runner, 판정(detect), 멱등 저장(`GeoAnswerRecord`), GEO 질문 SOP(5유형×20), 질문×엔진 매트릭스·월집계·추이, GSC/GA4 OAuth 수집(`ChannelConnection`→`ChannelMetric`), 채널 플레이북 데이터, 월간 리포트 규칙조립, 크론·RBAC·감사·탭형 거래처 UI·`/geo` 페이지.
2. **GEO-OS가 채우는 순증분(GAP) 5개**: ① **SOV(경쟁사 점유율)** ② **플레이북→태스크 cap-clamp 자동배분**(위키/레딧 D강등 차단) ③ **거래처 GEO 주간 리포트(규칙기반)** ④ **태스크 반복 자동생성**(cadenceDays 로직) ⑤ AI Overview/네이버 AI 자동 어댑터(선택).
3. 이식 대상은 전부 **순수 함수**(`geo-sov.js`·`geo-templates.js`·`geo-report.js`·`geo-recur.js`) → ERP의 server-action + prisma 패턴에 얇게 감싸면 됨. **저장/ API/ 콘솔/ 워크플로/ ADMIN_SECRET은 폐기**(ERP가 이미 상위 대체).

---

## 1. 재사용 — ERP 기존 자산 (재구축 절대 금지)

| ERP 자산 | 위치 | GEO-OS 중복분(폐기) |
|---|---|---|
| 4-AI 엔진 어댑터(공식 API + web_search/grounding) | `src/server/geo-engine/engines.ts` | `lib/ai-engines.js`(재사용본)·워크플로 40콜 러너 |
| 자동 관측 runner(승인질문→엔진질의→저장, 비용상한) | `src/server/geo-engine/runner.ts` | `ai-expose-check.yml` egress 러너 |
| 판정(병원명·공식URL·경쟁사 감지) | `src/server/geo-engine/detect.ts` | 워크플로 verdict 로직 |
| 관측 저장(질문×엔진×일 멱등) | prisma `GeoAnswerRecord`(appeared/cited/competitorsMentioned) | `content/geo/*` snapshot JSON |
| GEO 질문(5유형×20 SOP·승인·의료법 차단) | `domain/sales/geo.ts`·`actions/geo.ts` | `prompt-sets.json`·`geo-aeo-input.js` |
| 매트릭스·월집계·추이 | `server/repositories/geo.ts` | admin 매트릭스·`ai-expose-latest.json` |
| GSC/GA4 수집(OAuth·refresh·30일) | `server/jobs/channel-sync.ts`·`integrations/google.ts`·`ChannelConnection` | `geo-gsc.js` collect·env 방식·`geo-metrics-collect.yml` |
| 채널 플레이북(채널×엔진 별점·자동화레벨·병원적합도) | `domain/sales/geo-channels.ts` | `checklist-templates.json`·플레이북 md |
| 월간 리포트 규칙조립 | `server/marketing/report-assembly.ts`·`Report` | (내 것은 주간이라 별개 — §2-③) |
| 크론(Vercel GET+시크릿 POST, GEO 월1) | `src/app/api/marketing/cron/route.ts` | 내 워크플로 4종 |
| RBAC/감사/서버액션 표준 | `domain/access-control.ts`·`actions/_helpers.ts` | `ADMIN_SECRET`·UI 역할 게이팅 |
| 탭형 거래처 상세 + `/geo` 페이지 | `components/clients/ClientDetail.tsx`·`app/(erp)/geo/page.tsx`·`components/geo/*` | `geo-ops.html` 콘솔 전체 |

> **즉 `geo-ops.html`·`api/geo-ops.js`·`geo-store.js`·`geo-aeo-input.js`·워크플로 4종·`ADMIN_SECRET`은 ERP 병합 시 이관하지 않는다**(ERP에 상위 구현 존재). desktop-tutorial의 GEO-OS는 파일럿/레퍼런스로 남긴다.

---

## 2. 순증분 — GEO-OS가 ERP에 실제로 더하는 것 (이식 대상)

### ① SOV(Share of Voice) — 가장 큰 순증분
- **ERP 현황**: `GeoAnswerRecord.competitorsMentioned(Json)`에 경쟁사 언급을 **기록만** 하고, **SOV 지표로 집계·시각화하지 않음**. `src/` 전체에 SOV 로직 전무.
- **이식**: `lib/geo-sov.js`의 `buildSov(cells)`(순수) → ERP `src/server/repositories/geo.ts`에 `geoSov(clientId, period)` 추가. 입력 = 해당 기간 `GeoAnswerRecord`들 → `{selfHit: appeared, compHits: competitorsMentioned}` 매핑 → `buildSov`.
- **경쟁사 출처**: `HospitalProfile.competitorHospitals`(이미 존재) 사용.
- **UI**: `components/geo/GeoMatrix`(또는 대시보드 KPI 4타일)에 SOV% 타일 + 경쟁사 분해 추가.
- **스키마**: 신규 불필요(집계는 파생). 추이 저장이 필요하면 월 롤업 필드/뷰만.

### ② 플레이북 → 태스크 cap-clamp 자동배분
- **ERP 현황**: `geo-channels.ts` 플레이북·`AI_CHANNEL_TASKS`는 정적 데이터. 계약 시 `Product.defaultTasks`→`signContract`가 WorkItem 벌크 생성하나 **자동화레벨→cap 클램프 없음**(템플릿 단순 전개).
- **이식**: `lib/geo-templates.js`의 `clampLevel`·`buildTasksFromTemplate`(순수) → ERP `domain/sales/geo-channels.ts` 근처에 `buildChannelTasks(channel, clientId)`. cap 초과 단계(위키/레딧 게시)는 D로 강등 → `WorkItem` 생성 시 자동 실행 대상에서 제외(안내형).
- **매핑**: 내 automationLevel A~D → ERP WorkItem에 `automationLevel` 필드 추가 or `category`/메모로 표기.

### ③ 거래처 GEO 주간 리포트(규칙기반)
- **ERP 현황**: 월간 리포트(`report-assembly.ts`, 네이버순위 기반) + 직원 개인 주간(`WeeklyReport`)만. **거래처 단위 GEO 주간 리포트 없음.**
- **이식**: `lib/geo-report.js`의 `buildReport`(순수) → ERP `server/marketing/`에 `buildGeoWeeklyReport(clientId, week)`. 입력 = GEO 매트릭스 요약(`repositories/geo.ts`) + ChannelMetric + WorkItem 완료율 + SOV(①). 산출 = keyWins/risks/nextActions.
- **주의**: ERP `WeeklyReport`(직원용)와 **이름 충돌** — GEO 주간은 `Report`(거래처)에 `reportType='geo-weekly'`로 넣거나 별도 저장. 용어 혼동 금지.

### ④ 태스크 반복 자동생성
- **ERP 현황**: `WorkTemplate.cadenceDays` 필드는 있으나 **자동 재생성 로직 미확인/없음**.
- **이식**: `lib/geo-recur.js`의 `dueRecurrences`(순수) → ERP 크론 `job:"work-recur"` 추가. `cadenceDays` 도래한 반복 템플릿을 이번 주기 WorkItem으로 멱등 생성(중복 방지). 기존 크론(`api/marketing/cron`)에 스텝 추가.

### ⑤ (선택) AI Overview / 네이버 AI 자동 어댑터
- **ERP 현황**: 상수·수동기록엔 `AI_OVERVIEW`/`NAVER_AI` 있으나 자동 어댑터는 4엔진만.
- **이식**: 신규 어댑터를 `geo-engine/engines.ts`에 추가(구글 AI Overview·네이버 AI Tab). 리서치상 한국 GEO 핵심(카페·블로그·지식iN 소스)이라 가치 높으나 난이도 있음 → 후순위.

---

## 3. 이식 방식 (어댑터 원칙)
- **순수 함수는 그대로 복사**(로직 재작성 0): `buildSov`·`clampLevel`·`buildTasksFromTemplate`·`buildReport`·`dueRecurrences`. TS로 옮기고 타입만 부여.
- **저장 어댑터만 신규**: JSON/`geo-store` → prisma(`db`) 쿼리로 감싼다. 예 SOV: `db.geoAnswerRecord.findMany({where:{...}})` → cells 매핑 → `buildSov`.
- **호출 표면**: ERP 표준 **server action**(`"use server"` + `requireUser`+`assertCanAccessClient`+`recordAudit`) 또는 크론 잡. 신규 REST 라우트 불필요.
- **UI**: 기존 `components/geo/*`에 타일/섹션 추가(SOV), `work` 보드에 반복 배지. 신규 페이지 최소화.

---

## 4. 폐기 목록 (ERP로 이관하지 않음)
`geo-ops.html`(콘솔) · `api/geo-ops.js` · `lib/geo-store.js` · `lib/geo-aeo-input.js` · `content/geo/*.json`(시드) · 워크플로 4종(`ai-expose-check`는 desktop-tutorial 사이트용으로만 잔존) · `ADMIN_SECRET` 인증 · UI 역할 게이팅. → **모두 ERP의 상위 구현(next-auth·RBAC·runner·크론·prisma)이 대체.**

재사용 라이브러리(순수): `geo-sov.js`·`geo-templates.js(clampLevel/buildTasksFromTemplate)`·`geo-report.js`·`geo-recur.js`. 참고용: `geo-metrics.js`(CSV 파싱 — ERP는 OAuth 자동수집이라 보조).

---

## 5. 구현 순서 (ERP 브랜치에서)
| 단계 | 작업 | ERP 위치 | 스키마 변경 |
|---|---|---|---|
| M1 | **SOV** 집계 + KPI 타일 | `repositories/geo.ts`·`components/geo/GeoMatrix` | 없음(파생) |
| M2 | 플레이북 **cap-clamp** 태스크 생성 | `domain/sales/geo-channels.ts`·`actions/work` | WorkItem `automationLevel?`(선택) |
| M3 | 거래처 **GEO 주간 리포트** | `server/marketing/`·`Report` | Report `reportType`(선택) |
| M4 | 태스크 **반복 자동생성** | `api/marketing/cron` job 추가 | 없음(cadenceDays 활용) |
| M5(선택) | AI Overview/네이버 AI **어댑터** | `geo-engine/engines.ts` | GeoAnswerRecord.engine 값 추가 |

각 단계 독립. **M1(SOV)이 최우선** — 순증분 최대, 스키마 변경 0, 기존 데이터로 즉시.

---

## 6. 실행 관문 & 주의
- **ERP 브랜치 전략**: `erp-v1`이 라이브. 병합 작업은 신규 브랜치(예: `feat/geo-sov`)에서 → PR → 검토 후 머지. (ERP 저장소는 이번 세션에 add_repo로 추가됨.)
- **prisma 마이그레이션**: M2/M3의 선택 필드 추가 시 `prisma:migrate` 필요. M1/M4는 무변경.
- **용어 충돌 방지**: ERP `WeeklyReport`(직원) ≠ GEO 주간 리포트(거래처). GEO "인용/노출"은 `GeoAnswerRecord.appeared/cited`에 매핑(중복 정의 금지).
- **테스트**: ERP는 vitest + Playwright(e2e). 이식하는 순수 함수는 기존 desktop-tutorial 테스트(geo-sov-recur 15·geo-report 25 등)를 vitest로 옮겨 회귀 유지.
- **컴플라이언스**: 의료광고법 검수는 ERP `ContentPlan.complianceRisk`·`actions/geo.ts` 차단이 이미 담당 — GEO-OS 규칙과 일치.

---

## 7. 요약
- 사용자의 "ERP 병합" 판단은 정확했고, ERP가 이미 GEO 핵심을 구현해 둔 덕에 **병합은 작다** — 순증분 5개(SOV·cap-clamp·주간리포트·반복·엔진어댑터), 그중 이식은 순수 함수 4개.
- desktop-tutorial의 GEO-OS는 **파일럿·레퍼런스**로 역할 종료, 운영 본체는 ERP로 수렴.
- 다음 액션: ERP 신규 브랜치에서 **M1(SOV)** 부터 착수(스키마 무변경·최대 순증분).
