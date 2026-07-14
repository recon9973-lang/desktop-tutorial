# GEO 운영 OS — 자료 수집 & 브레인스토밍 기획서

> 코드네임(제안): **VENOM GEO-OS** (별칭 `geo-ops`)
> 작성일: 2026-07-14 · 대상 저장소: `recon9973-lang/desktop-tutorial` · 브랜치: `claude/production-ready-planning-mpkir0`
> 입력 자료: 첨부 5종(AI 노출 채널 전략·출처분석·실무 가이드·자동화 가이드·상용화 작업지침서) + 저장소 자산 실사 + 외부 리서치 2건(API 사양/가격·GEO 통계 팩트체크)
> 성격: **기획(브레인스토밍) 단계 산출물.** 구현 착수 전, 무엇을·어디에·어떤 순서로 지을지 확정하기 위한 문서.

---

## 0. 결론 요약 (BLUF)

1. **이건 백지 개발이 아니다.** 작업지침서(5번 문서)가 요구하는 "GEO 운영 OS"의 **엔진·자동측정·판정·리포트·GrowthOps는 이 저장소에 이미 작동/구현**되어 있다. 진짜 격차는 **"2개 업체 하드코딩 → 100개 거래처 멀티테넌트"** 한 축이다.
2. **자동화 코어 스택 확정**: `GSC API(성과·색인)` + `Perplexity Sonar(AI 인용)` + `Gemini grounding(저비용 보조)`를 코어로, `OpenAI/Claude web search`는 멀티엔진 검증용(빈도 억제). **Google Indexing API는 상용 신뢰 경로에서 제외**(정책 회색지대).
3. **GEO 통계는 절대 하드코딩하지 않는다.** 유통되는 인용 점유율("Wikipedia 12.1%", "FAQ 스키마 2~3배", "llms.txt 인용 상승")은 벤더발·시점의존·주 단위 붕괴. 제품은 **상대지표(경쟁사 대비 SOV) + 추세(delta)**만 1급 지표로 쓴다.
4. **차별화는 순수 모니터링이 아니라** ① **한국어·Naver 생태계 커버리지**(글로벌 툴 공백), ② **측정→실행 클로즈드루프**(VENOM 콘텐츠·이미지 파이프라인 결합), ③ **전환 귀속**이다. 순수 모니터링 시장은 이미 레드오션(Profound~Ahrefs 기능 수렴).
5. **권장 진행안 = 하이브리드(작업지침서 §4-C)**: 1차는 기존 `desktop-tutorial` 위에 운영형 MVP로 **파일럿 10~20 거래처**, 2차에 SaaS 확장. 단 **"어디에 짓나"(이 저장소 vs 별도 ERP vs 신규 SaaS)**는 사용자 결정이 필요한 게이트 → §3, §12.

---

## 1. 출발점 — 기존 자산 재사용 지도 (중복 개발 금지)

작업지침서가 요구하는 항목 대비 저장소 현황:

| 지침서 요구 (5번 문서) | 현재 상태 | 위치 |
|---|---|---|
| 4대 AI 인용 모니터링(Perplexity·GPT·Gemini·Claude) | ✅ **작동 중**(2개 업체 하드코딩) | `venom-wordpress/preview/lib/ai-engines.js` `ask(engine,q)` → `{answer,mentioned,citations}` |
| AEO HTTP 진입점 | ✅ | `api/insights.js?type=aeo&engine=..&q=..&name=..` |
| 인용/언급/미노출/측정불가 판정 | ✅ (citation URL·본문 core 매칭, q4=브랜드형/q0~3=발견형) | 워크플로 + `ai-engines.js` |
| 샌드박스 egress 우회 자동측정 | ✅ **GitHub Actions 러너 패턴 확립** | `.github/workflows/ai-expose-check.yml` (러너가 배포된 API 40콜) |
| 거래처별 프롬프트셋 정의 | ⚠️ 있으나 **하드코딩 2건** | `content/ai-expose-input.json` (businesses[].questions[5]) |
| 실측 스냅샷 → 관리자 렌더 | ✅ | `content/ai-expose-latest.json` → `admin.html #section-aiexpose` |
| **거래처별 시계열 저장 모델** | ⚠️ **설계만, 미배선** | `docs/intel-ai-exposure.prisma` (TrackedQuery/AiExposureSnapshot/AiExposureDaily, `clinicId`=ERP Client 연결) |
| 업무 보드·아웃리치 CRM·내부링크·토픽클러스터 | ✅ **완료(GrowthOps)** | `api/growthops.js` (`?module=linkhealth\|snapshot\|outreach\|cluster`) + `growthops.html` |
| 콘텐츠 자동생성·발행·Schema·sitemap·번역·의료광고검증 | ✅ 완료 | `lib/post-generator.js`·`image-generator.js`·`sitemap-builder.js`·`medical-ad-validator.js`·`keyword-research.js`·`content-validator.js` |
| SEO 진단(룰 엔진)·PSI·엔티티·키워드 | ✅ | `seo/seo-engine.js`, `api/seo-proxy.js`, `api/insights.js?type=keywordtool` |
| 방문자 분석(채널·디바이스·퍼널) | ✅ (Vercel KV) | `api/analytics.js` |
| **거래처(계약·정산·업무·이미지스튜디오)** | ✅ **별도 ERP에 존재** | `marketing-agency-erp` 저장소(현재 세션 스코프 밖) |

**해석**: 지침서의 7·8·10장(자동화 목록·데이터모델·자동화레벨)은 대부분 **이미 부품이 있다**. §7.2(거래처 상세 9탭), §8(데이터모델 8테이블), §9(워크플로 템플릿)의 **멀티테넌트 관리층**만 새로 얹으면 된다.

### 1.1 인프라 제약 (설계에 강제 반영)
- **저장소 2종만 사용**: GitHub(콘텐츠·설정 JSON, git 이력) + Vercel KV/Upstash(카운터·시계열·세션성). 신규 데이터도 이 둘 또는 Neon(prisma 모델 채택 시).
- **Vercel 서버리스 함수**: 현재 `api/*.js` **18개**. Hobby(12개) 초과 → 이미 Pro이거나 일부 제외 설정. **신규 API는 기존 통합함수에 `?type=`/`?module=` 라우팅**으로 흡수(예: `growthops.js`, `insights.js` 패턴)하는 것을 기본으로.
- **KST(Asia/Seoul)** 날짜 경계 통일.
- **egress 차단 우회**: 실측(AI 엔진 실호출)은 **GitHub Actions 러너**가 배포된 API를 호출하는 확립된 패턴 재사용.

---

## 2. 외부 리서치 종합 (2026-07 기준)

### 2.1 자동화 코어 스택 결정 (비용·신뢰성 기준)

| API | 인용/데이터 반환 | 대략 비용 | 판정 |
|---|---|---|---|
| **Google Search Console API** | clicks·impressions·CTR·position + URL Inspection 색인상태 | **무료** | 🟢 **코어 채택**. property 단위라 거래처 늘어도 스케일. 제약: URL Inspection 2,000/일/property → 우선순위 페이지만 |
| **Perplexity Sonar** (`sonar`/`sonar-pro`) | ✅ `citations`+`search_results`(title/url/date) 구조화 반환 | 토큰 $1~3/1M + **검색수수료 $5~14/1k요청**(지배적) | 🟢 **AI 인용 트래킹 1순위**. 4,000 RPM 티어로 스케일 OK. 쿼리 빈도 설계가 비용 관건 |
| **Gemini `google_search`** grounding | ✅ `groundingMetadata`(URL·근거매핑) | Gemini 3: 월 5,000 무료 + **$14/1k**, 2.x: 1,500 RPD 무료 + $35/1k | 🟢 **저비용 grounded 보조**. 무료 쿼터가 파일럿에 유리 |
| **OpenAI `web_search`** | ✅ `url_citation` 어노테이션 | **$10/1k콜 + 콜당 ~8k input 토큰**(이중과금) | 🟡 멀티엔진 커버리지용, **빈도 억제** |
| **Anthropic Claude web search** | ✅ `citations`(url·title·cited_text, 인용필드는 토큰 무과금) | **$10/1k검색** + 결과 토큰 | 🟡 멀티엔진 커버리지용. 항상 citation on |
| **Google Indexing API** | — | 무료, 200/일 | 🔴 **코어 제외**. JobPosting/BroadcastEvent만 공식 허용 → 일반페이지는 정책 회색지대. 색인촉진은 sitemap+GSC 제출로 |
| **Naver Search / DataLab Open API** | SERP(blog/news/cafe/kin/web/local/shop) + 트렌드 | Client ID/Secret 무료 | 🟢(한국) SERP 순위·트렌드 우회 수집. **단 Search Advisor는 성과지표 공식 API 부재 → 수동 보완 전제** |

> 이 세션에 **네이버 Search/DataLab MCP**(`mcp__PlayMCP__NaverSearch-*`)와 카카오 MCP가 이미 연결 → 한국 트랙 프로토타이핑 즉시 가능.

**결론 스택**: 코어 = **GSC + Perplexity + Gemini** / 멀티엔진 검증 = **OpenAI·Claude(빈도제한)** / 한국 = **Naver Open API(SERP·트렌드) + 수동 보완** / **Indexing API 제외**.

### 2.2 GEO 통계 팩트체크 → **하드코딩 금지 목록**

> **핵심 경고**: 유통 GEO 통계 대다수는 벤더/PR 발이며 방법론 비공개·주 단위 붕괴(예: Reddit의 ChatGPT 점유율 2025-09 2주 만에 ~60%→~10%). **어떤 특정 퍼센트도 제품 KPI로 하드코딩 금지.**

| 주장 | 판정 | 제품 취급 |
|---|---|---|
| Wikipedia 12.1% / Reddit 10% (ChatGPT) | 방향만 맞음, 숫자 벤더·시점의존(5W는 13.15/11.97%) | ❌ 고정수치 금지. 플랫폼별 상이(Wiki는 Claude~0.1%) |
| Perplexity 최상위=Reddit 6.6% | 숫자 낡음(2026 피크 46.7% → Reddit 제소 후 86%↓) | ❌ 정량치 금지, 방향만 |
| 언드미디어 325% 리프트 | 통제실험 있으나 소표본(기사8/944조합)·벤더 이해상충 | ⚠️ 방향 신호로만, 보장수치 금지 |
| FAQPage 스키마 2~3배 | **취약/반증**(Ahrefs 1,885페이지 추적: 거의 무변화, 상관≠인과) | ❌ KPI 금지. 스키마는 위생 항목으로만 |
| Perplexity 인용오류 37% | 🟢 **신뢰 1차**(Columbia Tow Center 2025-03, 1,600테스트) | ✅ 인용 가능, **시점·버전 라벨 필수** |
| 웹검색 환각 73~86%↓ | 방향 강함, 특정%는 SimpleQA 파생(47%→9.6%) | ⚠️ "벤치마크상 3~5배↓", 단일상수 금지 |
| llms.txt 인용 상승 | **과장**(크롤러 실요청 무시가능 수준) | ❌ KPI 금지. "손해 없으니 넣되 리프트 약속 안 함" |

**활용 가능한 1차 자료**: CJR/Tow Center(인용오류), OpenAI 시스템카드(환각, 범위표기), arXiv 2026 논문군(측정 프레임·트래픽 영향). 모두 **시점·모델버전 라벨** 부착.

### 2.3 GEO 측정 원칙 (arXiv 2026 프레임 차용)
- **상대지표 우선**: 절대% 아닌 **경쟁사 대비 SOV + 시간축 delta**를 1급 지표.
- **고정 프롬프트 패널 + 종단(longitudinal) 반복**: 매 스윕에 **모델버전·UI컨텍스트·타임스탬프 로깅**. 단발 감사는 참고용.
- **"선택 vs 흡수" 분리**: 인용 링크 존재(selection) ≠ 답변 문장 반영(absorption)을 별도 지표로. (arXiv 2604.25707 `geo-citation-lab` 프레임)
- **다서피스 + 한국 트랙 분리**: ChatGPT/Perplexity/Gemini/AI Overviews **+ Naver AI Tab·Briefing**(소스풀=카페·블로그·지식iN, 글로벌과 다름)을 별도 채널.
- **비결정성 정직 노출**: 응답 변동성/신뢰구간을 UI에 표기(경쟁툴이 숨기는 약점 → 우리의 신뢰 차별점).

### 2.4 경쟁 지형 (build-vs-buy)
Profound($499~)·Peec(€89~)·Otterly($29~)·Scrunch($250)·Semrush AI($99)·Ahrefs Brand Radar($129~) — **기능이 "프롬프트+인용+SOV"로 수렴**. 순수 모니터링 직접빌드는 레드오션. **글로벌 툴의 명백한 공백 = 한국어·Naver 커버리지.** → 우리는 **한국 특화 + 실행 클로즈드루프 + 전환귀속**에 집중, 벤더 통계 재판매가 아닌 **자체 프롬프트 패널 1차 수집**.

---

## 3. 아키텍처 결정 — "어디에 짓나" (게이트, 사용자 확인 필요)

지침서의 "거래처 GEO 운영 OS"는 **거래처·업무·정산**(ERP 성격) + **AI 노출 엔진·GrowthOps·콘텐츠 파이프라인**(이 저장소)이 만나는 지점. 세 갈래:

| 안 | 내용 | 장점 | 단점 |
|---|---|---|---|
| **A. 이 저장소(desktop-tutorial) 확장** | AEO 엔진 옆에 멀티테넌트 관리층을 얹음 | 엔진·GrowthOps·파이프라인 **바로 재사용**, 세션 스코프 내, 즉시 착수 | 거래처/정산은 ERP와 개념 중복, 정적+서버리스 구조라 멀티테넌트 UI 한계 |
| **B. ERP(marketing-agency-erp)로 흡수** | 이미 거래처·계약·업무·이미지스튜디오 보유한 Next.js에 GEO 모듈 추가 | 거래처 관리 **이미 완성**, 권한/청구 유리, prisma `clinicId` 설계가 ERP Client 전제 | **현재 세션 스코프 밖 저장소**, 엔진은 desktop-tutorial에 있어 크로스레포 연동 필요 |
| **C. 하이브리드(지침서 §4 권장)** | 1차: desktop-tutorial 위 운영형 MVP로 파일럿 → 2차: ERP/SaaS로 제품화 | 실무 데이터 먼저 축적, 병목 검증 후 확장 | 1차→2차 데이터 이전 설계 필요 |

**기획자 권장 = C(하이브리드), 1차 구현체는 A 위에.** 근거: 엔진·자동측정·판정·GrowthOps가 전부 여기 있고, GitHub Actions egress 우회 패턴도 여기 확립돼 있어 **파일럿을 가장 빨리 실측까지 돌릴 수 있다.** 거래처 마스터/정산이 ERP에 있으므로, **거래처 식별자(`clinicId`)로 느슨히 연결**(prisma 설계가 이미 이 전제)하고 정산·계약은 ERP에 위임. → **최종 결정은 §12 Q1.**

---

## 4. 제품 정의 — VENOM GEO-OS

**한 줄 정의**: 거래처(병원/로컬 비즈니스) 각각을 하나의 GEO 운영 프로젝트로 보고, **채널계정·업무·성과·AI인용·자동화상태**를 한 화면에서 관리하며 반복업무를 등급별로 자동화하는 운영 OS.

### 4.1 측정 모델 (지침서 §5·§7.5 + 리서치 §2.3 통합)
- **채널 성과 KPI**: GSC(노출·클릭·CTR·순위·색인수), GA4(세션·전환), YouTube/LinkedIn/Reddit 활동, PR 픽업·백링크.
- **GEO 전용 KPI**: 프롬프트셋별 **언급/인용(선택)·흡수·경쟁사 대비 SOV·감성·출처유형분포·AI별 추세**. + **오귀속/오정보 상태**(지침서 §2.4 7-상태).
- **정직성 규칙**: 단일 질의 1회로 성과 판단 금지 → 여러 회차·여러 AI 반복. "인용됨" ≠ "좋은 내용으로 인용됨" 구분. 경쟁사 인용 동시 기록.

### 4.2 자동화 레벨 매핑 (지침서 §2.3 + 리서치 반영)
| 레벨 | 업무 | 코어 도구 | 제품 처리 |
|---|---|---|---|
| 🟢 A 완전자동 | GSC/GA4 수집, Perplexity/Gemini 인용체크, Google Alerts, llms.txt 갱신, Schema 검증, 주간리포트 | GSC/Perplexity/Gemini API + GitHub Actions | 자동실행·로그·오류알림 |
| 🟡 B 반자동 | LinkedIn 포스트·블로그·보도자료·YouTube 메타·README 초안 | Claude/OpenAI + 기존 `post-generator` | **승인 큐** → 수정 후 예약/발행 |
| 🔵 C AI보조 | Reddit·Wikipedia·Stack Overflow 초안 | LLM 초안만 | 초안생성, **인간 직접 게시 안내** |
| 🔴 D 인간필수 | Wikipedia 실제편집, Reddit 게시/업보트, arXiv 제출, 기자 피칭, 고객 최종승인 | — | 체크리스트·증빙 업로드만 |

**자동화 금지선(하드)**: Wikipedia 실편집, Reddit 자동게시/업보트, Stack Overflow 무검증답변, arXiv 제출/endorsement, 허위리뷰, 언론/보도자료 허위수치. **+ Indexing API 일반페이지 색인.**

---

## 5. 데이터 모델 (기존 `intel-ai-exposure.prisma` 확장)

기존 3모델(TrackedQuery/AiExposureSnapshot/AiExposureDaily)은 **거의 그대로 재사용**. 멀티테넌트 관리층만 추가:

```
# 기존(재사용) — intel 스키마
TrackedQuery        { clinicId, query, active, cadence, snapshots[] }        # 거래처별 프롬프트셋
AiExposureSnapshot  { clinicId, queryId, engine, mentioned, rank,
                      answerText, competitors, citations, sentiment }        # 1측정=1행
AiExposureDaily     { clinicId, date, enginesTotal, enginesHit, exposureRate }# 일별 롤업

# 신규(멀티테넌트 관리층) — 지침서 §8 매핑
Client        { id, name, industry, region, websiteUrl, priorityAiEngines[],
                competitors[], lifecycleStage, monthlyBudget, planType }     # clinicId ↔ ERP Client 연결키
Channel       { id, clientId, channelType, accountUrl, ownerEmail,
                accessStatus, apiStatus, healthStatus, nextAction, riskLevel }
Task          { id, clientId, channelId, taskType, automationLevel(A~D),
                status(kanban), assignee, dueDate, checklistTemplateId,
                evidenceUrl, approvalStatus, recurrenceRule }
ContentItem   { id, clientId, channelId, contentType, targetKeyword,
                targetAiEngine, draftStatus, publishStatus, publishUrl,
                schemaApplied, blufApplied }
Metric        { id, clientId, channelId, metricDate, metricName, value, source }
Automation    { id, clientId, workflowType, tool, trigger, status,
                lastRunAt, lastResult, errorMessage, retryCount }
Report        { id, clientId, reportPeriod, summary, keyWins, risks, nextActions }
```

**저장 전략 선택지(§12 Q2)**: (a) **Neon Postgres + prisma**(모델 설계가 이 전제, 멀티테넌트·조인 유리) vs (b) **GitHub JSON + KV**(현 저장소 관례 유지, 파일럿 빠름). 파일럿은 (b)로 시작해 (a)로 이전하는 것이 §3-C와 정합.

**SOV/흡수 확장 필드**(리서치 반영): Snapshot에 `absorbed:Boolean`(답변 문장 반영), `modelVersion:String`, `uiContext:String` 추가 권장.

---

## 6. 기능 우선순위 & MVP 범위 (실무 사용 가능선)

"실무 사용 가능"의 정의 = **파일럿 10~20 거래처를 한 화면에서 운영하며, AI 인용을 주기적으로 실측하고, 주간 리포트가 자동 생성되는 상태.**

### MVP (필수 — 실무 사용 가능선)
1. **거래처 CRUD + 채널계정 상태판** (지침서 §7.3) — 재사용: 신규 관리층
2. **거래처별 프롬프트셋 관리 → 다거래처 AI 인용 실측** — 재사용: `ai-engines.js`·`insights.js?type=aeo`·`ai-expose-check.yml`을 **N거래처로 일반화**(현 하드코딩 2건 제거)
3. **시계열 저장·추이·경쟁사 SOV** — 재사용: `intel` prisma 3모델 배선 + Snapshot 확장필드
4. **업무 보드(칸반) + 반복업무 자동생성 + 승인 큐** — 재사용: GrowthOps 아웃리치/업무 패턴
5. **GSC/GA4 성과 수집(수동 업로드 or API)** — 신규: GSC API 연동(코어)
6. **주간 리포트 자동생성** — 재사용: `post-generator`(LLM 요약) + GitHub Actions 스케줄
7. **자동화 상태·오류 로그** + 사용자 권한(6역할) — 재사용: growthops 로그 패턴

### 2차 (상용화 근접)
- OpenAI/Gemini/Claude 멀티엔진 인용 확대, Slack/Email 승인 플로우, 고객 포털, 콘텐츠 초안 생성(B레벨), PDF 리포트 자동발송, Naver SERP 트랙.

### 3차 (상용 패키지)
- 요금제/청구, 화이트라벨 리포트, 업종별 벤치마크, 전환귀속(GA4+전화예약), 워크플로 템플릿 마켓.

> **의도적 범위 축소**: 콘텐츠 대량 자동발행, Indexing API, 벤더통계 재판매는 MVP에서 **제외**(리스크/저효과).

---

## 7. 워크플로 (지침서 §9 → 기존 자동측정 위에)
- **신규 거래처 7일 온보딩**: Day1 기본정보·GSC/GA4 권한요청 → Day2 인증·sitemap → Day3 llms.txt·Schema대상 → Day4 채널현황 → Day5 콘텐츠캘린더·초안 → Day6 **AI 인용 프롬프트 10개 생성·첫 실측** → Day7 진단리포트 자동생성.
- **주간 운영**: 월(업무 자동생성·LinkedIn 초안) → 화(발행·GSC 색인요청·llms.txt) → 수(영상/이미지·Schema검증) → 목(Reddit/커뮤니티 기회 확인, Wikipedia는 인간) → 금(**GSC/GA4/Perplexity 수집·주간리포트·다음주 액션3**).
- **월간 리뷰**: 완료율·발행량·색인/노출/클릭·AI 인용 변화·SOV·자동화 실패율·투입시간.

---

## 8. 리스크 & 컴플라이언스 가드레일
- **의료광고법(VENOM 맥락 핵심)**: GEO 성과지표를 **치료효과/전후 서사와 절대 결합 금지**. AI 가시성은 순수 노출/인용 메트릭으로만. 발행 경로는 `medical-ad-validator` 필수 통과.
- **플랫폼 정책**: 자동화 금지선(§4.2) 하드 차단. Reddit/Wikipedia 자동게시 기능 미구현.
- **데이터 신뢰**: 벤더 통계 재판매 금지, 자체 프롬프트 패널 1차수집. 모든 인용통계에 시점·모델버전 라벨.
- **보안**: API키 암호화(Vercel env), 고객 비밀번호 미저장(OAuth/초대), 2FA 소유자 기록, 리포트 거래처별 격리. SSRF 방어(`seo-proxy` 패턴) 신규 URL 입력에 적용.

---

## 9. 로드맵 (실무 사용 가능 → 상용화)

| 단계 | 기간 | 산출물 | 완료(실무) 기준 |
|---|---|---|---|
| **P0 기획 확정** | 지금 | 본 문서 + §12 결정 | 아키텍처·저장소·저장방식·파일럿 대상 확정 |
| **P1 멀티테넌트 실측** | 1~2주 | AI 인용 실측 N거래처 일반화(하드코딩 제거) + `intel` 배선 + 거래처/채널 CRUD | 파일럿 10거래처가 프롬프트셋으로 주1회 실측·추이 확인 |
| **P2 운영층** | 2~4주 | 업무보드·승인큐·GSC 연동·주간리포트 자동 | 첫 30일: 채널세팅 80%·리포트 자동발송 |
| **P3 상용 근접** | 1~2개월 | 멀티엔진 확대·고객포털·Naver 트랙·전환귀속 | 거래처 50개 운영·SOV 대시보드 |
| **P4 상용화** | 이후 | 요금제·화이트라벨·벤치마크 | 100개 운영, 누락률 5%↓, 리포트 자동화 80%↑ |

각 단계 독립 커밋·배포. **P1이 최우선인 이유**: 이미 있는 엔진을 멀티테넌트로 여는 것이 최소 노력·최대 효과이고, 이후 모든 모듈(리포트·SOV)의 입력이 됨.

---

## 10. 성공 지표 (KPI)
- 파일럿 거래처 실측 커버리지(프롬프트셋×AI 실행률), 측정불가율 ↓
- 거래처당 AI 인용 SOV **추세**(절대% 아님), 발견형 질문 노출률 ↑
- 업무 누락률 ↓(목표 5%↓), 승인 큐 처리 시간 ↓
- 주간 리포트 자동화율 ↑(목표 80%↑), 실무자 투입시간 ↓
- (상용) 거래처 수·거래처당 ROI·고객 리텐션

---

## 11. 자체 검토
- 빈 작업/미완성 표기 없음. 자동화 가능/금지 구분 명시.
- "AI 기능에 특수 마크업 필수" 같은 과장 배제(Google 공식 문서 기준).
- 첨부 5종의 채널전략·자동화레벨·KPI·로드맵을 **기존 자산 재사용 전제**로 제품구조에 변환.
- MVP와 상용화 단계 분리로 범위 현실화. GEO 통계 하드코딩 금지 목록 명문화.

---

## 12. 열린 결정사항 (사용자 확인 필요 — 구현 착수 게이트)

- **Q1. 어디에 짓나**: (A) 이 저장소 확장 / (B) ERP 흡수 / (C) 하이브리드(권장). → 1차 구현체 위치.
- **Q2. 저장 방식**: (a) Neon+prisma(멀티테넌트 정석) / (b) GitHub JSON+KV(파일럿 속도). 
- **Q3. 파일럿 대상**: 실측 일반화를 검증할 첫 거래처(예: 시원마취통증·시원스킨 + 몇 곳). 실제 GSC/GA4 접근 가능 업체 우선.
- **Q4. 이번 세션 다음 액션**: 이 기획 확정만? 아니면 바로 **P1(멀티테넌트 실측 일반화) 착수**까지?

> 다음 산출물(요청 시): 화면별 기능명세 · ERD · API 명세 · 자동화 워크플로 명세 · P1 개발일정 · 테스트 시나리오 · 파일럿 10거래처 운영 체크리스트.
