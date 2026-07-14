# GEO 운영 OS — 상세 설계서 (P1 구현 사양)

> 코드네임: **VENOM GEO-OS** (별칭 `geo-ops`) · 작성일: 2026-07-14
> 상위 문서: [`geo-ops-os-plan.md`](./geo-ops-os-plan.md) (자료수집·브레인스토밍)
> **확정 결정(사용자)**: ① 구현 위치 = **이 저장소(`desktop-tutorial`) 확장, 하이브리드 1차** · ② 저장 = **GitHub JSON + Vercel KV**(파일럿 속도, 후에 Postgres 이전) · ③ 이번 세션 = **상세 설계 산출물까지**
> 성격: 코드 착수 직전의 구현 사양. 화면·스키마·API·자동화·일정·테스트·파일럿 체크리스트 포함.

---

## 0. 설계 원칙 (기존 저장소 관례 강제 반영)

1. **엔진 재사용, 관리층만 신설.** AI 인용 실측은 `lib/ai-engines.js`·`api/insights.js?type=aeo`·`.github/workflows/ai-expose-check.yml`을 **N거래처로 일반화**(현 하드코딩 2건 제거)한다. 새 엔진을 만들지 않는다.
2. **저장소 2종만.** GitHub JSON(엔티티·설정, git 이력) + Vercel KV(시계열·카운터). `lib/github-store.js`·기존 KV 클라이언트 재사용. **Neon/prisma 미도입**(스키마는 논리 모델로만 유지, 후속 이전).
3. **함수 한도 절약.** 신규 서버리스 함수는 **`api/geo-ops.js` 단 1개**, `?module=&action=` 라우팅으로 전 CRUD 흡수(현 18개 → 19개). 실측은 기존 `insights.js`에 흡수.
4. **콘솔은 독립 페이지.** `admin.html` 수정 위험을 피해 **`/geo-ops.html`** 신설(선례: `growthops.html`). 로그인 가드는 기존 admin 인증 재사용.
5. **egress 우회.** AI 엔진 실호출·GSC 수집 등 외부 콜은 **GitHub Actions 러너**가 배포된 API를 호출(샌드박스 차단 회피). 확립된 `ai-expose-check.yml` 패턴 복제.
6. **KST 경계 통일**, **SSRF 방어**(`seo-proxy` 패턴) 신규 URL 입력에 적용, **의료광고검증** 발행 경로 필수.

---

## 1. 데이터 스키마 (GitHub JSON + Vercel KV)

### 1.1 GitHub JSON — 엔티티·설정 (git 이력, `lib/github-store.js`)

```
content/geo/clients.json          # 거래처 마스터
content/geo/channels.json         # 채널 계정(거래처별 N)
content/geo/tasks.json            # 업무 카드
content/geo/content-items.json    # 콘텐츠 항목
content/geo/prompt-sets.json      # 거래처별 AI 인용 프롬프트셋 (구 ai-expose-input.json 일반화)
content/geo/automations.json      # 자동화 정의·상태
content/geo/report-templates.json # 리포트 템플릿
content/geo/checklist-templates.json # 업무 템플릿(코드 아닌 데이터)
```

**clients.json** — `{ clients: [ ... ] }`
| 필드 | 타입 | 비고 |
|---|---|---|
| `id` | string | `clinicId`와 동일 키(ERP Client 느슨 연결) |
| `name`·`industry`·`region`·`websiteUrl` | string | |
| `coreKeywords` | string[] | 인용 판정용 core(구 `cores`) |
| `competitors` | string[] | SOV 비교 대상 |
| `priorityAiEngines` | string[] | `["perplexity","gemini",...]` 실측 대상 |
| `lifecycleStage` | enum | 진단\|기반구축\|콘텐츠생산\|채널확장\|최적화 |
| `planType`·`monthlyBudget`·`primaryContact`·`assignee` | | |
| `gscProperty`·`ga4PropertyId` | string | 성과 수집 연결키(선택) |
| `active` | bool | 실측 루프 포함 여부 |

**channels.json** — `{ channels: [ ... ] }` : `id, clientId, channelType, defaultAutomationLevel, accountUrl, ownerEmail, accessStatus, apiStatus, healthStatus, twoFactor, lastActivityAt, nextAction, riskLevel, evidenceUrl`

**channelType 전체 목록**(첨부1·4 채널 완전 반영 — A 보완):
| 카테고리 | channelType | 기본 자동화레벨 | 근거 |
|---|---|---|---|
| 성과/기술 | `website` · `gsc` · `ga4` · `schema` · `llms_txt` | 🟢 A | 수집·검증 직접 실행 |
| 로컬 | `gbp`(Google Business) · `naver_place` | 🟡 B | 정보 정합성, 승인 후 반영 |
| 콘텐츠 | `linkedin` · `youtube` · `blog`(자사) · `naver_blog` · `naver_brunch` | 🟡 B | 초안+예약, 인간 승인 게시 |
| 커뮤니티 | `reddit` · `naver_kin`(지식인) · `naver_cafe` · `stackoverflow` · `quora` | 🔵 C→🔴 D | **초안만, 게시는 인간**(계정 리스크) |
| 백과 | `wikipedia` | 🔵 C(초안)→🔴 D(게시) | **자동 게시 금지선** |
| 학술 | `arxiv` · `github` | 🔴 D(arxiv) / 🟡 B(github README) | arXiv 제출 인간필수 |
| PR | `pr_global`(PRNewswire) · `pr_kr`(뉴스와이어·연합) | 🟡 B(초안)→🔴 D(배포승인) | CEO 인용문·수치 검증 |

> `defaultAutomationLevel`은 채널 생성 시 자동 지정되며, 이 채널에서 생성되는 Task의 상한 레벨을 강제한다(예: `wikipedia`/`reddit` Task는 A/B 승격 불가 → 자동 게시 원천 차단). **한국 UGC(지식인·카페·블로그·브런치·Place)를 별도 채널로 분리**해 첨부4의 "Naver AI Tab은 카페·블로그·지식iN에서 답변 생성" 취지 반영.

**tasks.json** — `id, clientId, channelId, title, taskType, automationLevel(A|B|C|D), status(backlog|thisweek|doing|review|hold|done|failed), assignee, dueDate, priority, checklistTemplateId, inputRefs, evidenceUrl, approvalStatus, recurrenceRule`

**content-items.json** — `id, clientId, channelId, contentType, targetKeyword, targetAiEngine, draftStatus, publishStatus, publishUrl, publishedAt, schemaApplied, blufApplied`

**prompt-sets.json** — `{ sets: [ { clientId, cadence(daily|weekly), questions: [ { id, text, type(discovery|brand) } ] } ] }` (거래처당 5~10문항, q타입으로 발견형/브랜드형 구분)

**automations.json** — `id, name, clientId(nullable=전체), workflowType, tool, trigger(cron|webhook), status, lastRunAt, lastResult, errorMessage, retryCount`

### 1.2 Vercel KV — 시계열·카운터·스냅샷

```
geo:snap:<clientId>:<queryId>:<engine>:<ymd>   → JSON  # 1측정 = 1행 (구 AiExposureSnapshot)
   { mentioned, absorbed, rank, answerText, competitors[], citations[], sentiment, modelVersion, uiContext, measuredAt }
geo:daily:<clientId>:<ymd>                      → JSON  # 일별 롤업 (구 AiExposureDaily)
   { enginesTotal, enginesHit, exposureRate, discExposureRate }
geo:sov:<clientId>:<ymd>                         → JSON  # 경쟁사 대비 share of voice
   { self, competitors: { name: mentions }, share }
geo:metric:<clientId>:<metricName>:<ymd>         → number # GSC/GA4 시계열(clicks/impressions/position/sessions...)
geo:report:<clientId>:<period>                   → JSON  # 생성된 주간 리포트 캐시
geo:idx:clients:active                           → set    # 실측 루프 대상 거래처 인덱스
```

> **확장 필드(리서치 §2.3 반영)**: `absorbed`(답변 문장 반영=흡수, citation 존재=선택과 분리), `modelVersion`·`uiContext`·`measuredAt`(종단 비교용). 이는 기존 스냅샷 스키마에 **가산**.

### 1.3 논리 ERD (후속 Postgres 이전용 참조)
```
Client 1─N Channel · Client 1─N Task(─0..1 Channel) · Client 1─N ContentItem
Client 1─1 PromptSet 1─N Query · Query 1─N Snapshot(engine,ymd) → Daily rollup, SOV
Client 1─N Metric(name,ymd) · Client 1─N Automation · Client 1─N Report
Client.id ≡ clinicId ≡ ERP Client.id (느슨 연결)
```

---

## 2. 화면별 기능 명세 (`/geo-ops.html` — 독립 콘솔)

로그인 가드는 기존 admin 인증 재사용. 좌측 사이드바 8개 섹션.

### 2.1 전체 관제 대시보드 (홈)
- **위젯**: 전체 거래처 수 · 온보딩 진행률 · 이번 주 마감임박 업무 · 자동화 실패 건수 · 승인 대기 건수 · AI 인용 발생 거래처 수 · 성과 상위/하위 5.
- **리스크 알림 리스트**: 계정 미연결 · 색인 오류 · 콘텐츠 미발행 · KPI 급락 · 실측 실패. (클릭 → 해당 거래처)
- **정렬/필터**: 100거래처 기준 **클라이언트 사이드 인덱스** 로드(`clients.json` 1콜) 후 즉시 필터. 시계열은 지연 로드.
- 데이터: `geo-ops.js?module=dashboard` (집계) + `clients.json`.

### 2.2 거래처 상세 (탭 9)
개요 · 계정/채널 · 업무보드 · 콘텐츠캘린더 · 자동화 · 성과 · **AI 인용 모니터링** · 리포트 · 자료/증빙.
- **개요**: clients.json 필드 편집 폼 + 운영단계 배지.
- **AI 인용 모니터링 탭(핵심)**: 프롬프트셋 편집 → "지금 측정"(GitHub Actions dispatch 안내/트리거) → **질문×엔진 매트릭스**(언급 초록/인용 파랑/흡수 별표/미노출 빨강/측정불가 노랑) + **노출률·발견형 노출률·SOV 추이 라인차트**(경량 SVG, 의존성 0). 각 셀 클릭 → `answerText`·citations 원문.
- **성과 탭**: GSC 클릭/노출/CTR/순위 + 색인 페이지수 + GA4 세션/전환 라인차트(KV 시계열).

### 2.3 채널 계정 관리
- 거래처×채널 매트릭스(상태 색상). 채널카드: accountUrl·소유자·접근권한·2FA·API연동·최근활동·다음액션·위험도·증빙.
- 데이터: `channels.json` (`module=channels`).

### 2.4 업무 진행 보드 (칸반)
- 7열(backlog/이번주/진행중/승인대기/보류/완료/실패). 카드=거래처·채널·업무명·자동화레벨(A~D 뱃지)·담당·마감·우선순위.
- **승인 대기 최상단 고정**(지침서 §16.3). 반복업무 자동생성(recurrenceRule).

### 2.5 성과 대시보드 (전 거래처 롤업)
- 채널 성과 vs GEO 성과 분리. GEO: 프롬프트별 인용여부·자사 citation 수·SOV·감성·오정보 발생·AI별 추세.

### 2.6 AI 인용 모니터링 허브
- 전 거래처 실측 현황 그리드 + 최근 실행 로그 + 측정불가 재시도 버튼.

### 2.7 리포트 · 2.8 자동화 로그
- 주간 리포트 목록/미리보기(HTML→PDF), 자동화 실행이력·오류(실무자 언어).

---

## 3. API 명세 (`api/geo-ops.js` 단일 함수, `?module=&action=`)

공통: `GET`(조회)·`POST`(upsert/action). 응답 `{ ok, data|error }`. 인증=admin 토큰 헤더.

| module | action | 설명 | 저장 |
|---|---|---|---|
| `dashboard` | `summary` | 관제 위젯·리스크 집계 | 읽기전용 |
| `clients` | `list\|get\|upsert\|delete` | 거래처 CRUD | clients.json |
| `channels` | `list\|upsert\|delete` | 채널 CRUD(clientId 필터) | channels.json |
| `tasks` | `list\|upsert\|move\|delete\|generate` | 업무 CRUD·상태이동·반복생성 | tasks.json |
| `content` | `list\|upsert\|delete` | 콘텐츠 항목 | content-items.json |
| `prompts` | `get\|upsert` | 프롬프트셋 편집 | prompt-sets.json |
| `metrics` | `series\|ingest` | 성과 시계열 조회·수집(CSV/API) | KV `geo:metric:*` |
| `exposure` | `matrix\|series\|snapshot` | 실측 매트릭스·추이·스냅샷 조회 | KV `geo:snap/daily/sov` |
| `report` | `get\|generate\|list` | 리포트 조회·생성 | KV `geo:report:*` |
| `automation` | `list\|log\|retry` | 자동화 상태·로그·재시도 | automations.json + KV |

**실측 트리거**: `exposure?action=snapshot`은 직접 AI를 호출하지 않고(샌드박스 차단), **GitHub Actions `workflow_dispatch`를 큐잉**하거나 러너 결과 JSON을 읽어 렌더. 실제 40콜은 러너가 `insights.js?type=aeo`로 수행(기존).

**GSC/GA4 수집**: `metrics?action=ingest`는 (a) CSV 업로드 즉시 수용, (b) GitHub Actions 러너가 GSC/GA4 API OAuth로 수집→KV write. Indexing API는 **사용 안 함**(sitemap+GSC 제출로 대체).

---

## 4. 자동화 워크플로 명세 (GitHub Actions 우선, n8n/Make 선택)

| 워크플로 | 트리거 | 동작 | 출력 | 레벨 |
|---|---|---|---|---|
| `geo-exposure-check.yml`(구 ai-expose 일반화) | 매일/주 dispatch | active 거래처 전체 × 프롬프트셋 × priorityEngines 실측(동시성 5) | KV snapshot/daily/sov + `content/geo/exposure-latest.json` 커밋 | A |
| `geo-metrics-collect.yml` | 매일 07:00 KST | GSC(clicks/impr/pos/색인) + GA4(세션/전환) 수집 | KV `geo:metric:*` | A |
| `geo-weekly-report.yml` | 매주 금 17:00 KST | 거래처별 성과+SOV+AI인용 집계 → `post-generator` LLM 요약 → HTML 리포트 | KV `geo:report:*` + 알림 | A→B |
| `geo-task-generate.yml` | 매주 월 09:00 KST | recurrenceRule 기반 이번주 업무 자동생성 | tasks.json 갱신 | A |
| (선택) LinkedIn/블로그 초안 | 승인 큐 | `post-generator` 초안 → 승인 대기 | content-items.json | B |

- **금지선 하드코딩**: Wikipedia 편집·Reddit 게시·Indexing API 일반페이지 = 워크플로에 **미구현**. C레벨은 초안까지만.
- **비용 가드**: exposure 워크플로에 `maxCallsPerRun` + 엔진별 빈도(Perplexity 주1·Gemini 무료쿼터 우선·OpenAI/Claude는 월1 검증) 파라미터. 100거래처 예산 폭주 방지.

---

## 5. P1 개발 일정 (실무 사용 가능선까지, 1~2주)

| # | 작업 | 산출물 | 의존 |
|---|---|---|---|
| 1 | 스키마 부트스트랩 | `content/geo/*.json` 초기파일 + `lib/geo-store.js`(github-store 래퍼) | — |
| 2 | 거래처/채널 CRUD | `api/geo-ops.js`(clients·channels) + 테스트 | 1 |
| 3 | **실측 일반화** | `ai-expose-input.json` → prompt-sets.json 이관, `geo-exposure-check.yml`이 active 거래처 루프, 스냅샷 KV+JSON write | 1 |
| 4 | 콘솔 뼈대 | `/geo-ops.html` 사이드바 + 관제 대시보드 + 거래처 상세(개요·AI인용 탭) | 2,3 |
| 5 | 업무 보드 | tasks CRUD + 칸반 + 반복생성 + 승인큐 상단 | 2 |
| 6 | 성과 수집 | `geo-metrics-collect.yml`(우선 CSV 업로드 경로) + 성과 탭 라인차트 | 2 |
| 7 | 주간 리포트 | `geo-weekly-report.yml` + 리포트 탭 | 3,6 |
| 8 | 자동화 로그·권한 | automation 로그 + 6역할 가드 | 2 |

**착수 순서 근거**: 3(실측 일반화)이 최소노력·최대효과이자 모든 지표의 입력. 1·2는 그 그릇.

**진행 현황(2026-07-14)**: ✅ **#1 완료** `lib/geo-store.js`(테스트 21) · ✅ **#2 완료** `api/geo-ops.js`(테스트 18) + 시드 `content/geo/*.json`(pain/skin 이관) · ✅ **#3 완료** `lib/geo-aeo-input.js`(테스트 13) + `ai-expose-check.yml` 일반화(하드코딩 제거, geo 소스 우선·기존 파일 폴백). ✅ **#4 완료** `/geo-ops.html` 콘솔(관제 대시보드 + 거래처 목록/등록 + 상세: 개요·채널·AI인용 매트릭스; 기존 디자인토큰·`venom-admin-secret` 공유·`ai-expose-latest.json` 재사용; Playwright 렌더 검증). ✅ **#5 완료** 업무보드(칸반 7열·승인큐 상단고정·채널 플레이북→Task 인스턴스화 with cap 클램프: 위키/레딧 게시 D 강등) + `lib/geo-templates.js`(테스트 20) + `tasks generate/approve` 액션 + `templates` 모듈. ✅ **#6 성과수집 CSV 경로 완료** `lib/geo-metrics.js`(CSV 파싱·정규화·시계열·요약, 테스트 19) + `metrics` 컬렉션 + `metrics ingest/series/summary` 액션 + 콘솔 성과 탭(CSV 적재·요약 타일·SVG 추이). GSC "Dates"·한글·일반형 CSV 지원, 재적재 중복없이 갱신. ⏭ 남은 하위: GSC **API 자동수집 워크플로**(`geo-metrics-collect.yml`, `lib/search-console.js` 재사용 — 동일 `metrics ingest`로 적재, 러너·OAuth 필요). 남은 P1: #7 주간리포트 · #8 자동화 로그·권한. (Vercel 함수 19개 — Pro 플랜 전제; 초과 시 growthops.js에 흡수 검토.)

---

## 6. 테스트 시나리오

- **정적 검증**(기존 관례): 신규 `.js` 전부 `node --check`; `api/geo-ops.js` `require` 로드·exports 확인; 워크플로 YAML 파싱 + 임베디드 node `node --check`; `content/geo/*.json` `require` 파싱.
- **단위**: `lib/geo-store.js`(upsert/get/list/delete, 동시쓰기 충돌), 판정 로직(cited/mentioned/absorbed/none/error), SOV 계산, 반복업무 생성(recurrenceRule), 비용가드(maxCallsPerRun).
- **통합(러너 모의)**: prompt-sets 2거래처 픽스처로 exposure 워크플로 dry-run → 스냅샷/daily/sov 생성 검증.
- **UI(Playwright)**: `/geo-ops.html` 로그인 → 각 섹션 렌더·바인딩·페이지 에러 0(샌드박스 차단 CDN 폰트 제외). 거래처 추가→AI인용 탭 매트릭스 렌더→셀 원문 표시. 칸반 카드 이동. 승인큐 상단 고정.
- **회귀**: 기존 `admin.html` AI 노출 실측 패널·`growthops.html` 무영향 확인(신규는 별도 페이지·별도 함수).
- **데이터 격리**: 거래처 A 토큰으로 B 데이터 조회 차단.

---

## 7. 파일럿 10거래처 운영 체크리스트

**대상 선정**: GSC/GA4 실제 접근 가능 업체 우선(시원마취통증·시원스킨 확정 + 8곳). 업종 다양화(로컬/병원/커머스)로 프리셋 검증.

**거래처당 온보딩(7일, 지침서 §9.1)**
- [ ] 기본정보·coreKeywords 20·competitors 3~5 등록 (clients.json)
- [ ] 채널 현황 등록 + 접근권한/2FA 소유자 기록 (channels.json)
- [ ] GSC/GA4 권한 확보 or CSV 확보 (gscProperty/ga4PropertyId)
- [ ] sitemap·robots·색인 확인, llms.txt 설치여부 확인
- [ ] FAQPage/Article Schema 대상 페이지 선정(위생 항목 — 인용 리프트 약속 안 함)
- [ ] 프롬프트셋 5~10문항 생성(발견형·브랜드형 구분) (prompt-sets.json)
- [ ] 첫 실측 1회(4엔진) → 매트릭스·발견형 노출률 확인
- [ ] 콘텐츠 캘린더 4주 + 첫 초안(B레벨 승인큐)
- [ ] 7일 진단 리포트 자동생성

**주간 운영 루프**: 월(업무 자동생성) → 화(발행·색인요청·llms.txt) → 수(영상/이미지·Schema검증) → 목(커뮤니티 기회, Wikipedia는 인간) → 금(수집·주간리포트·다음주 액션3).

**성공 판정(첫 30일)**: 채널세팅 완료율 80%↑ · 실측 커버리지(프롬프트×엔진 실행률) 확보 · 주간 리포트 자동발송 · 업무 누락률 추적 시작.

---

## 8. 컴플라이언스·비용 가드 (재확인)
- **의료광고법**: AI 가시성 지표를 치료효과/전후 서사와 결합 금지 — 순수 노출/인용 메트릭만. 발행은 `medical-ad-validator` 필수.
- **통계 정직성**: 고정 인용%·FAQ스키마 배수·llms.txt 리프트 **하드코딩 금지**. 인용통계엔 시점·모델버전 라벨. 상대지표(SOV)+추세만 1급.
- **API 비용**: exposure/collect 워크플로 빈도·maxCalls 파라미터화. Gemini 무료쿼터 우선, OpenAI/Claude 검증용 월1. Indexing API 미사용.
- **보안**: 시크릿=Vercel env, 고객 비번 미저장(OAuth/초대), 리포트 거래처 격리, SSRF 방어.

---

## 9. 다음 액션 (구현 착수 시)
P1 #1~3(스키마 부트스트랩 → 거래처/채널 CRUD → 실측 일반화)부터. 각 단계 독립 커밋·검증(JS/Playwright)·배포. 파일럿 2거래처(시원)로 실측 일반화가 도는 것을 먼저 증명한 뒤 8곳 확장.
