# GEO 운영 OS — 세션 전체 작업 정리 (2026-07-14~15)

> 세션 목표(첫 오더): "실무 사용이 가능한 범위까지 개발. 우선 첨부 5종을 모두 읽고, 자료 수집과 브레인스토밍 기획까지."
> 결과: 읽기 → 리서치 → 기획 → 설계 → **P1 전 구현 + MVP 잔여 4항목** → **배포·라이브 검증** → **파일럿 런북**까지 완주. 지침서 §13.1 MVP 필수 9항목 완결.

---

## 1. 진행 흐름 (단계별)

1. **첨부 5종 정독** — AI 노출 채널 전략·출처분석·실무 가이드·자동화 가이드·상용화 작업지침서
2. **저장소 자산 실사** — "백지 아님" 확인: AI 노출 실측 엔진(`lib/ai-engines.js`)·GitHub Actions 실측 패턴·GrowthOps·intel prisma가 이미 존재. 격차 = "2업체 하드코딩 → N거래처 멀티테넌트"
3. **외부 리서치 2건**
   - API 사양·가격·한도(Perplexity/OpenAI/Gemini/Claude/GSC/Indexing/Naver) → 자동화 코어 스택 확정
   - GEO 통계 팩트체크 → **하드코딩 금지 목록**(인용%·FAQ스키마·llms.txt 등 벤더발·시점의존) 확정
4. **기획서 → 설계서 → 채널 플레이북** 작성, 아키텍처·저장·범위 **사용자 결정** 반영
5. **P1 #1~#8 구현** + **GSC 자동수집 후속** + **MVP 잔여 4항목**
6. **배포**(PR #172·#180 squash-merge → main) + **라이브 워크플로 검증**
7. **파일럿 런북** + 라이브 준비도 진단

### 사용자 결정 사항
- 구현 위치: **이 저장소(`desktop-tutorial`) 확장** (하이브리드 1차)
- 저장: **GitHub JSON + Vercel KV** (파일럿 속도)
- 범위: 상세 설계 → 전 구현 → 배포 → 파일럿

---

## 2. 산출물

### 2.1 문서 (`docs/plans/`)
| 문서 | 내용 |
|---|---|
| `geo-ops-os-plan.md` | 기획(자료수집·브레인스토밍): 자산 재사용 지도·API 스택·통계 팩트체크·MVP 범위·로드맵 |
| `geo-ops-os-design.md` | 상세 설계: 화면 9탭·JSON+KV 스키마·API 명세·자동화·P1 일정·테스트·진행현황 |
| `geo-ops-os-channel-playbooks.md` | 채널별 실행 플레이북(위키·레딧·링크드인·유튜브·깃허브·SO·arXiv·PR·SEO·네이버 UGC) — 단계별 자동화레벨·금지선 |
| `geo-ops-pilot-runbook.md` | 파일럿 운영 런북(사전설정·7일 온보딩·주간 루프·KPI·트러블슈팅) |
| `geo-ops-session-summary.md` | (이 문서) |

### 2.2 코드 — 백엔드 라이브러리 (`venom-wordpress/preview/lib/`)
| 파일 | 역할 |
|---|---|
| `geo-store.js` | 거래처·채널·업무·콘텐츠·프롬프트·자동화·성과·리포트 엔티티 CRUD(GitHub JSON, 동시쓰기 재시도, 배치 upsert) |
| `geo-templates.js` | 채널 플레이북 → Task 인스턴스화(cap 클램프: 위키/레딧 게시 D 강등) |
| `geo-aeo-input.js` | 거래처(active)+프롬프트셋 → 실측 입력 컴파일(폴백·competitors 전달) |
| `geo-metrics.js` | 성과 CSV 파싱·정규화·시계열·요약(GSC/한글/일반형) |
| `geo-gsc.js` | GSC Search Analytics(date) → 메트릭 레코드(ctr %변환) |
| `geo-report.js` | 성과·AI인용·업무 집계 → keyWins/risks/nextActions(통계 미생성) |
| `geo-sov.js` | 경쟁사 대비 Share of Voice(상대지표) |
| `geo-recur.js` | 반복 업무 자동 생성(period 중복방지) |

### 2.3 코드 — API·콘솔
- **`api/geo-ops.js`** — 단일 서버리스 함수, `?module=&action=` 라우팅 9모듈: `dashboard·clients·channels·tasks·content·prompts·automations·metrics·report` + `templates`. ADMIN_SECRET 인증. tasks: move/approve/generate/recur. metrics: ingest/series/summary/collect.
- **`geo-ops.html`** — 독립 콘솔: 관제·거래처(검색)·업무보드(칸반·승인큐)·자동화로그 + 상세 6탭(개요·채널·콘텐츠캘린더·성과·AI인용·리포트) + 역할 6종 권한 게이팅. 기존 디자인토큰·admin 시크릿 공유.

### 2.4 시드 데이터 (`content/geo/*.json`)
clients(pain/skin 이관)·channels·tasks·content-items·prompt-sets·automations·metrics·reports·checklist-templates(10 채널)

### 2.5 워크플로 (`.github/workflows/`)
| 워크플로 | 주기 | 역할 |
|---|---|---|
| `ai-expose-check.yml`(수정) | 월 1일/수동 | 거래처 AI 인용 실측 + SOV 집계(일반화·후방호환) |
| `geo-metrics-collect.yml` | 매일 07:00 KST | GSC 성과 자동수집 |
| `geo-weekly-report.yml` | 매주 금 17:00 KST | 거래처 주간 리포트 생성 |
| `geo-task-recur.yml` | 매주 월 07:00 KST | 반복 업무 인스턴스화 |

---

## 3. 검증

### 3.1 오프라인 테스트 (8 스위트, 175개)
geo-store 21 · geo-templates 20 · geo-metrics 19 · geo-gsc 9 · geo-report 25 · geo-sov-recur 15 · geo-aeo-input 13 · geo-ops-api 53 = **175 pass**
- 방식: 인메모리 백엔드 주입 + mock req/res(샌드박스 egress 차단 우회)

### 3.2 콘솔 Playwright
관제·거래처·상세 탭·칸반·승인큐·성과 SVG·리포트·역할 게이팅·검색·콘텐츠캘린더·SOV — 렌더·네비 정상, pageerror 0

### 3.3 라이브 런타임 검증 (배포 후, GitHub Actions 러너)
- **AI Exposure Check**(run 29344815433): `INPUT source=geo businesses=2` → **제 일반화 코드 경로 확정**. 40셀(2업체×5문항×4엔진) **측정 오류 0**. 스냅샷 커밋. → P1 #3 라이브 증명
- **GEO Weekly Report**(run 29395137417): `unauthorized` → **라이브 API 쓰기 보호 정상**(Vercel ADMIN_SECRET 설정됨). GitHub 저장소 Secret 부재가 자동화 유일 차단 요소로 특정됨

---

## 4. 배포 상태
- **저장소**: `recon9973-lang/desktop-tutorial` · **배포**: venom-new-site.vercel.app (main 자동)
- **머지**: PR #172(P1 GEO-OS)·#180(MVP 4항목) 모두 squash-merge → main. 브랜치는 origin/main으로 리셋
- **콘솔 주소**: https://venom-new-site.vercel.app/geo-ops.html
- **주의**: 브랜치를 리베이스해 이전 세션 스쿼시-이전 히스토리를 걷어냄 → PR은 GEO 신규 작업만(라이브 파일 regress 방지). 백업 `backup-pre-rebase-geo`

---

## 5. 파일럿 준비도

| 항목 | 상태 |
|---|---|
| 콘솔·API 배포 | ✅ |
| 라이브 쓰기 보안(Vercel ADMIN_SECRET) | ✅ 설정됨(401 확인) |
| AI 실측 라인 | ✅ 라이브 무오류 |
| 리포트 라인 | ✅ 인증계층까지 정상(Secret 등록 시 완결) |
| **GitHub 저장소 Secret `ADMIN_SECRET`** | ⚠️ **미설정 = 자동화 유일 차단** |
| GSC 서비스계정 | ⚠️ 미설정(CSV로 대체 가능) |
| 거래처 competitors(SOV) | 비어 있음(등록 시 SOV 산출) |

**파일럿 켜는 법**: GitHub Secret `ADMIN_SECRET`(Vercel과 동일 값) 추가 → 콘솔에 같은 값 입력 → 런북 §2 온보딩.

---

## 6. 첫 오더 대비 달성률
| 범위 | 달성 |
|---|---|
| 첫 오더 즉시 요청(정독+리서치+브레인스토밍 기획) | **100%** (+ 설계·구현·배포로 초과) |
| 실무 사용 가능선(P1 8항목) | **100%** |
| 지침서 §13.1 MVP 필수 9항목 | **100%** |
| **ERP 병합(M1~M6 코드·PR·검증)** | **100%** (머지·M6 실행은 팀 액션) |
| 상용화 전체(MVP+2차+3차) | **~60%** |

---

## 7. 남은 것 (다음 확장)
- **2차**: 콘텐츠 초안 자동생성 연결(B레벨 승인큐)·Slack 승인 플로우·고객 포털·PDF 리포트 발송
- **3차**: 서버측 RBAC·요금제/청구·화이트라벨·업종 벤치마크
- **운영 심화**: 거래처 competitors 등록 → SOV 실측 · 프롬프트셋 콘솔 편집 UI · 거래처 KV 시계열 SOV 추이
- **즉시 후속**: 팀이 GitHub Secret 등록 → 리포트 워크플로 재실행 → 첫 파일럿 리포트 라이브 생성

---

## 8. ERP 병합(M1~M6) — 완료 (2026-07-16 추가)

> 최종 목적 "완료 후 베놈 ERP와 병합" 실행분. 상세: [`geo-erp-integration-delivery.md`](geo-erp-integration-delivery.md) · 설계: [`geo-erp-integration-design-v2.md`](geo-erp-integration-design-v2.md)

`recon9973-lang/marketing-agency-erp`(base `erp-v1`)에 6개 모듈 이식 — **전부 open PR(자동 머지 안 함)**, 오프라인 52케이스 통과.

| 모듈 | 내용 | PR | 스키마 |
|---|---|---|---|
| M1 | 경쟁사 SOV 집계 + KPI 타일 | #42 | 0 |
| M2 | 채널 자동화 cap-clamp | #43 | 0 |
| M3 | 거래처 GEO 주간 리포트 | #44 | 0 |
| M4 | 반복 업무 자동 생성(cadenceDays) | #45 ✅빌드 green | 0 |
| M5 | 온보딩 Phase 체크리스트 | #46 | 0 |
| M6 | NAS→ERP 이관 스크립트 골격 | #47 | 0 |

---

## 9. 라이브 TODO 체크리스트 (2026-07-16 기준)

### ✅ 완료
- [x] GEO-OS 파일럿 구축·배포(P1 8항목·MVP 9항목) — §1~6
- [x] 통합 설계서 v2(ERP 실사 기반 정정)
- [x] ERP 병합 M1~M6 구현·PR·오프라인 검증(52케이스)
- [x] 통합 인도 문서(`geo-erp-integration-delivery.md`)
- [x] **PR #42~#47 전부 erp-v1 머지 완료** (2026-07-16, 전 PR Vercel green). M2#43↔M5#46 타입 충돌은 세 필드(phase·automationLevel·channel) 모두 유지로 해소됨. `sov.ts`·`geo-weekly.ts`·`recurrence.ts`·`work-recur.ts`·`migrate-nas-to-erp.ts` 및 SOV KPI 안착 확인.

### ⏭ 팀 액션 (병합 마무리)
- [ ] **M6 실행**: `sqlite3 team.db ".schema"`로 `NAS_SCHEMA` 확정 → `staff-map.json` 작성 → dry-run → `--commit`
- [ ] **desktop-tutorial 파일럿**: GitHub Secret `ADMIN_SECRET` 등록(자동화 유일 차단) — 병합 완료로 파일럿 종료 수순

### 🔜 UI 후속 (설계 §7, 선택)
- [ ] SOV 차트(M1 데이터 · `components/geo`)
- [ ] ClientDetail Phase 진행률 탭(M5 `onboardingPhaseSummary`)
- [ ] reports에 geo-weekly 타입(M3 `assembleGeoWeekly`)

### 📌 중장기 (2차·3차, §7 유지)
- [ ] 콘텐츠 초안 자동생성(B 승인큐)·Slack 승인·고객 포털·PDF 발송
- [ ] 서버측 RBAC·요금제/청구·화이트라벨·업종 벤치마크

---
*배포 파이프라인: implement → 검증(JS/Playwright) → commit → PR → squash-merge → 브랜치 origin/main 리셋. 작업 브랜치 `claude/production-ready-planning-mpkir0`.*
