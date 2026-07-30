# VEO 개발용 Codex 마스터 프롬프트

아래 프롬프트 전체를 새로운 Codex 개발 작업에 붙여 넣어 사용한다. 통합 보고서와 리서치 폴더가 같은 작업공간에 있다면 반드시 먼저 읽도록 한다.

---

## 프롬프트 시작

당신은 VENOM의 수석 소프트웨어 아키텍트이자 풀스택 개발 책임자다. VEO-LAB의 연구 방법론을 제품으로 구현하는 신규 프로젝트 `VEO`를 구축하라.

VEO는 **SEO·GEO·네이버 키워드 검색량을 각각 정확하게 측정하고, 서로 연결해서 분석하는 통합 진단 플랫폼**이다. 기존 NXT 소스코드와 데이터베이스에는 접근할 수 없다. NXT의 화면을 복제하거나 역설계하지 말고, 제공된 리서치·비교 분석에서 확인된 장점과 결함을 반영해 독립적인 제품을 설계·구현하라.

### 조직과 브랜드

- 제품명: `VEO`
- 제품 설명: `SEO · GEO · Naver Keyword Intelligence Platform`
- 개발사: `VENOM`
- 연구·방법론: `VEO-LAB`
- 기본 표기:

```text
VEO
SEO · GEO · Naver Keyword Intelligence Platform

Developed by VENOM
Research & Methodology by VEO-LAB
```

### 먼저 읽을 근거 문서

작업공간에서 다음 자료를 찾아 완전히 읽고 요구사항 추적표를 작성하라. 파일이 없다면 누락을 기록하되 임의로 내용을 발명하지 말라.

1. `outputs/SEO_GEO_진단도구_통합분석보고서.docx` 또는 PDF
2. `outputs/NXT_GEO_TOOL_COMPARISON_REPORT.md`
3. `outputs/SEO_SCORE_IMAGE_COMPARISON_REPORT.md`
4. `outputs/VENOM_NAVER_KEYWORD_TOOL_COMPARISON_REPORT.md` 또는 동등한 네이버 키워드 비교 보고서
5. `outputs/seo-research-kit/07_audit_tools/RECOMMENDED_SCORING_MODEL.md`
6. `outputs/seo-research-kit/07_audit_tools/SCORING_COMPARISON.md`
7. `outputs/seo-research-kit/06_product_blueprint/SEO_TOOL_PRODUCT_BLUEPRINT.md`
8. `outputs/geo-research-kit/06_measurement/RECOMMENDED_GEO_SCORING_MODEL.md`
9. `outputs/geo-research-kit/06_measurement/METRIC_DICTIONARY.md`
10. `outputs/geo-research-kit/06_measurement/PROMPT_SAMPLING_AND_CONFIDENCE.md`
11. `outputs/geo-research-kit/06_measurement/TOOL_SCORING_COMPARISON.md`
12. `outputs/geo-research-kit/07_product_blueprint/GEO_TOOL_PRODUCT_BLUEPRINT.md`

### 이 제품의 생명 — 다른 모든 원칙보다 앞선다

아래 두 가지는 기능이 아니라 **제품이 존재하는 이유**다. 둘 중 하나라도 어기면
나머지를 아무리 잘 만들어도 그 진단은 쓸 수 없다. 일정에 밀려 넘길 수 있는 항목이
아니고, "일단 이렇게 보이게" 해 두었다가 나중에 고칠 수 있는 항목도 아니다.

#### 0-A. 실측에 대한 정직성

**재지 않은 것을 잰 것처럼 보여주지 않는다.**

- 자격증명이 없거나 호출이 실패했을 때 **그럴듯한 값을 지어내지 않는다.** 그때의
  올바른 출력은 `측정 불가` 이고, **왜 못 쟀는지**를 함께 남긴다. "측정 불가" 만
  띄우면 고장으로 읽힌다.
- **모르는 것을 통과로 접지 않는다.** 인증서 만료일을 못 받았다면 여유가 있는 것이
  아니다. 통과로 접는 순간, 만료 직전인 사이트를 정상이라고 보고하게 된다.
- **없는 결함을 지어내지 않는다.** 이미지가 없는 페이지의 대체 텍스트, 선언이 없는
  사이트의 JSON-LD 문법 — 대상이 존재하지 않는 것은 실패가 아니라 해당 없음이다.
- 추정치·보간값·기본값을 실측값과 **같은 자리에 표시하지 않는다.**
- 모든 판정에 원시 증거·수집 시각·측정 범위·출처·명세 버전·체크섬을 붙인다.
  **"이 점수가 왜 이렇게 나왔는가"에 답할 수 없으면 그 점수는 쓰지 않는다.**
- 우리가 못 잰 것과 고객이 권한을 안 준 것을 구분한다. PageSpeed 를 못 쟀다면 그건
  우리가 안 한 것이다.
- 오탐은 결함이다. 제대로 만든 사이트를 지적하는 검사는, 몇 번 반복되면 보고서 전체를
  믿지 않게 만든다.

#### 0-B. 절대 평가

**100점은 고정된 만점이며, 모든 고객에게 같은 뜻이어야 한다.**

- **없는 것은 0점이고, 그 배점은 분모에 그대로 남는다.** 0점 처리된 항목을 빼고
  나머지로 환산하면 안 된다. 20점 항목이 0점이면 나머지가 만점이라도 **80점**이다.
- 잴 수 없어서 못 잰 항목도 마찬가지다. 못 잰 이유가 우리 쪽이든 대상 쪽이든
  **얻지 못한 점수는 얻지 못한 것**이다.
- 예외는 **해당 없음** 하나뿐이다. 그것은 "이 대상에는 그 항목이 존재하지 않는다"는
  뜻이지 "없다"가 아니다. 페이지네이션이 없는 사이트에 페이지네이션 검사를 0점으로
  매기면 없는 결함을 만들어 내는 것이므로, 해당 없음은 분모에서 뺀다.
- **분모가 고객마다 달라지면 안 된다.** 연동을 붙일수록 분모가 커져 점수가 내려가면
  **연결하지 않는 편이 유리해진다.** 스키마를 만들수록 채점 항목이 늘어 불리해져도
  마찬가지다. 진단 도구가 만들면 안 되는 유인이고, 실제로 두 번 다 이렇게 틀렸다.
  잴 수 없는 영역은 **애초에 점수의 일부가 아니라고 명세에 적고**, 점수를 이루는
  영역만으로 100을 이루게 한다.
- 잴 수 없는 항목을 명세에 선언하지 않는다. 수집 경로가 없는 채로 선언하면 **우리가
  아직 만들지 않은 기능 때문에 모든 고객의 점수가 내려간다.** 수집을 먼저 만들고
  다음 판에 넣는다.
- 배점·심각도·가중치는 오직 `packages/scoring-specs` 의 발행 명세에만 존재한다.
  검사기 코드에 숫자가 하나라도 박히면 안 된다.

### 절대 지켜야 할 원칙

1. SEO·GEO·키워드 수요를 하나의 불투명한 총점으로 합치지 않는다.
2. 정적 URL 검사를 실제 검색 순위나 실제 AI 노출 점수라고 표현하지 않는다.
3. SEO 점수와 GEO 점수는 결정적 코드로 계산하며 GPT가 임의로 최종 점수를 만들지 않는다.
4. GPT는 검색 의도·엔터티·주장·답변 정확성·인용 적합성·설명 생성처럼 의미 판단이 필요한 영역에만 사용한다.
5. 모든 결과에 원시 증거, 실행 시각, 측정 범위, 데이터 출처, 점수 버전, 환경을 연결한다.
6. `실패`, `부분`, `통과`, `해당 없음`, `측정 불가`, `데이터 없음`을 구분한다.
7. 네이버 공식 Search AD 데이터, DataLab 상대지수, VEO 자체 계산값을 명확히 구분한다.
8. 공개 검사와 내부 정밀 검사는 같은 진단 엔진을 사용하되 범위·한도·결과 노출을 분리한다.
9. 기존 NXT의 코드·디자인·카피·상표를 복제하지 않는다.
10. 비밀키, 토큰, 고객 데이터, 원시 AI 답변을 로그에 평문으로 노출하지 않는다.

## 1. 제품 범위

### 1.1 VEO Public

로그인 없이 사용할 수 있는 공개 진입 화면을 만든다.

- `/tools/seo`: 단일 URL 기본 SEO 진단
- `/tools/geo`: 단일 URL GEO 준비도 진단
- `/tools/naver-keyword`: 단일 키워드 또는 제한된 묶음 조회
- `/results/{public_token}`: 만료되는 공개 결과 공유
- 상세 결과·사이트 전체 진단·경쟁 분석 신청 CTA

공개 검사는 반드시 다음 제한을 가진다.

- IP, 세션, 도메인, 키워드별 rate limit
- 동시 작업 제한과 작업 대기열
- 최대 redirect·응답 크기·다운로드 시간·페이지 수 제한
- 내부망·localhost·link-local·cloud metadata·사설 IP 차단
- 결과와 원시 데이터의 짧은 보존기간
- 민감정보와 고객정보 비노출

### 1.2 VEO Console

VENOM과 VEO-LAB 내부 직원이 로그인해서 사용하는 운영 도구를 만든다.

- `/console/dashboard`
- `/console/customers`
- `/console/projects`
- `/console/sites`
- `/console/seo`
- `/console/geo`
- `/console/keywords`
- `/console/competitors`
- `/console/issues`
- `/console/reports`
- `/console/scoring-versions`
- `/console/api-usage`
- `/console/admin`

역할:

- `SUPER_ADMIN`: 조직·보안·점수 발행·전체 설정
- `LAB_ADMIN`: VEO-LAB 점수 명세·검수 기준 관리
- `ANALYST`: 프로젝트·진단·검수·보고서
- `DEVELOPER`: 기술 이슈·증거·수정·재검증
- `SALES_VIEWER`: 고객 요약·공개 가능한 보고서 열람
- `CLIENT_VIEWER`: 향후 고객 포털을 위한 읽기 전용 역할

## 2. 기술 아키텍처

### 2.1 확정 스택

- Frontend: Next.js 최신 안정 버전, TypeScript strict, App Router
- UI: 접근 가능한 headless component 기반, 프로젝트 디자인 토큰
- Data fetching: 생성된 OpenAPI TypeScript client+query cache
- Backend: FastAPI, Python 최신 안정 버전, Pydantic v2, SQLAlchemy 2
- Database: PostgreSQL
- Migration: Alembic
- Queue/Cache: Redis+Celery
- Crawling: httpx 기반 HTTP crawler+Playwright renderer
- Performance: PageSpeed Insights 또는 Lighthouse runner, CrUX 연동 가능 구조
- AI: OpenAI API structured output; provider adapter
- Storage: S3 compatible object storage
- Observability: structured logging, metrics, tracing, error reporting adapter
- Deployment: Docker Compose local, production-ready container definitions
- Contract: OpenAPI를 단일 API 계약으로 사용

구체 버전은 작업 시작 시 공식 릴리스와 호환성을 확인하고 고정하라. 근거 없이 실험 버전을 선택하지 말라.

### 2.2 저장소 구조

```text
veo/
├─ apps/
│  ├─ web/
│  ├─ api/
│  └─ worker/
├─ packages/
│  ├─ ui/
│  ├─ api-client/
│  ├─ shared-types/
│  └─ scoring-specs/
├─ infra/
│  ├─ docker/
│  ├─ migrations/
│  ├─ monitoring/
│  └─ scripts/
├─ docs/
│  ├─ architecture/
│  ├─ api/
│  ├─ scoring/
│  ├─ operations/
│  └─ adr/
├─ tests/
│  ├─ contract/
│  ├─ integration/
│  ├─ e2e/
│  ├─ security/
│  └─ fixtures/
├─ .env.example
├─ docker-compose.yml
└─ README.md
```

백엔드는 하나의 모듈형 모놀리스로 시작하되 다음 도메인 모듈을 명확히 분리한다.

```text
apps/api/src/veo/
├─ auth
├─ organizations
├─ customers
├─ projects
├─ sites
├─ crawl
├─ seo
├─ geo
├─ keywords
├─ competitors
├─ scoring
├─ observations
├─ issues
├─ reports
├─ usage
├─ audit
└─ common
```

한 모듈이 다른 모듈의 DB 테이블을 직접 수정하지 않도록 서비스 인터페이스와 이벤트를 사용한다. 순환 의존성을 허용하지 않는다.

## 3. 병렬 작업 운영 규칙

가능한 작업은 반드시 병렬로 분담하라. 단, 공유 계약을 먼저 고정하고 충돌을 피해야 한다.

### 3.1 에이전트 분담 원칙

- 독립된 하위 작업에만 서브에이전트를 사용한다.
- 각 에이전트에 담당 경로, 입력 계약, 산출물, 테스트, 금지 변경 경로를 명시한다.
- 같은 파일, Alembic migration chain, OpenAPI root, 공통 설정을 두 에이전트가 동시에 수정하지 못하게 한다.
- 병렬 에이전트 결과를 그대로 신뢰하지 말고 루트 에이전트가 diff·테스트·계약을 검증한다.
- 프론트엔드는 mock server 또는 확정 OpenAPI 계약으로 병렬 개발한다.
- 외부 API 자격증명이 없어도 fixture로 개발·테스트한다.
- 충돌 가능성이 있으면 병렬화보다 계약 안정성을 우선한다.

### 3.2 Wave 0 — 루트가 먼저 완료

1. 저장소 상태와 기존 파일 조사
2. 요구사항 추적표 생성
3. ADR 작성
4. 공통 용어집 작성
5. 핵심 엔터티와 관계 확정
6. 작업 상태·오류 envelope·pagination 계약 확정
7. OpenAPI 초안과 mock 생성
8. 점수 spec JSON/YAML schema 확정
9. 테스트·포맷·lint·typecheck·CI 명령 확정

Wave 0 완료 전에는 기능 구현을 시작하지 말라.

### 3.3 Wave 1 — 병렬 에이전트

동시에 수행 가능한 작업:

- Agent A: Next.js shell, routing, auth guard, design tokens, 공통 component
- Agent B: FastAPI auth, RBAC, customers, projects
- Agent C: crawler core, URL normalization, SSRF security, fetch fixtures
- Agent D: Naver Search AD/DataLab adapter, signatures, rate limit, mock fixtures
- Agent E: Celery job model, Redis, idempotency, progress, cancellation
- Agent F: Docker, CI, logging, metrics, local developer experience

각 에이전트는 자신의 테스트를 포함하고 완료 후 변경 파일과 검증 결과를 보고한다.

### 3.4 Wave 2 — 병렬 에이전트

- Agent SEO: SEO collector, rule checks, scoring evidence
- Agent GEO: GEO readiness collector, entity graph, source evidence
- Agent Keyword: related keywords, snapshots, opportunity score
- Agent Public UI: 공개 SEO/GEO/keyword flow
- Agent Console UI: 고객·프로젝트·작업·결과 기본 화면
- Agent Report: report schema, export interface, templates skeleton

### 3.5 Wave 3 — 병렬 에이전트

- AI observation/provider adapters
- competitor comparison
- GSC/Naver/Bing integrations
- scoring version publish workflow
- issue/fix/reverification workflow
- full report rendering
- usage/cost administration

### 3.6 통합 게이트

각 Wave 끝에 루트 에이전트가 다음을 수행한다.

1. 변경 경로와 계약 차이 검토
2. migrations 정렬·재생성 검증
3. OpenAPI breaking change 검증
4. backend unit/integration test
5. frontend lint/typecheck/unit test
6. contract test
7. Docker build
8. representative E2E
9. 보안·접근성 회귀
10. 문서와 실제 동작 일치 확인

검증에 실패하면 다음 Wave로 넘어가지 말라.

## 4. 공통 도메인 모델

최소한 다음 엔터티를 설계하라.

- Organization
- User
- RoleAssignment
- Customer
- Project
- Site
- URLRecord
- Competitor
- Scan
- ScanRun
- Job
- Evidence
- Metric
- ScoringVersion
- ScoreResult
- Issue
- FixRecommendation
- VerificationRun
- KeywordQuery
- KeywordMetric
- RelatedKeyword
- KeywordTrend
- KeywordList
- KeywordOpportunity
- PromptSet
- Prompt
- AIEngine
- ObservationRun
- AIAnswer
- Citation
- EntityMention
- ClaimAssessment
- Report
- ReportVersion
- APIUsageEvent
- AuditLog

모든 시계열·실험 결과는 덮어쓰지 말고 immutable run/version으로 저장한다. 사용자 수정 메모와 검수 상태만 별도 변경 가능하게 한다.

## 5. 작업·상태 모델

장시간 작업은 동기 요청에서 수행하지 않는다.

```text
QUEUED
RUNNING
PARTIAL_SUCCESS
SUCCEEDED
FAILED_RETRYABLE
FAILED_FINAL
CANCEL_REQUESTED
CANCELLED
EXPIRED
```

Job은 다음을 포함한다.

- job_id, type, owner, project_id
- idempotency_key
- input_hash, scoring_version
- status, progress, current_stage
- created_at, started_at, finished_at
- attempts, next_retry_at
- error_code, safe_error_message
- internal_error_ref
- result_run_id
- estimated_cost와 actual_cost

중복 요청 방지, at-least-once 실행에서의 멱등성, 재시도, 취소와 부분 성공을 테스트한다.

## 6. SEO 진단 엔진

### 6.1 준비도 영역과 기본 가중치

```text
Crawl & Indexability                   25
On-page Semantics                      15
Content & Information Architecture     15
Performance & UX                       15
Structured Data                        10
Search Engine Integration              10
Observability & Outcomes                5
Off-page & Entity Signals               5
Total                                 100
```

이 점수는 순위 예측이 아니라 기술·운영 준비도다.

### 6.2 기본 계산

```text
coverage_i = 영향받은 중요도 가중 URL / 검사 대상 중요도 가중 URL
penalty_i = severity_i × coverage_i × confidence_i
category_score = 100 × max(0, 1 - Σpenalty_i/category_budget)
overall_score = Σ(category_score × category_weight)
```

심각도 기본 계수:

- Blocker 1.00
- Critical 0.60
- Major 0.30
- Minor 0.10
- Info 0.00

URL 중요도 기본값:

- 핵심 전환·대표 3.0
- 카테고리·허브 2.0
- 일반 콘텐츠·상품 1.0
- 태그·필터·보조 0.5
- 의도된 noindex는 관련 분모 제외

### 6.3 치명적 상한

- 전체 robots/noindex 차단: 최대 25
- 주요 템플릿 5xx 또는 렌더 불가: 최대 35
- 대량 외부 canonical: 최대 40
- sitemap 과반 비정상: 최대 55
- HTTPS/모바일 중대 실패: 최대 60

상한의 원인과 해제 조건을 결과에 표시한다.

### 6.4 필수 검사

- status, redirect chain/loop, content type
- robots.txt와 URL별 허용 여부
- meta/X-Robots noindex, nofollow, snippet control
- canonical, hreflang, pagination
- sitemap 발견·파싱·URL 품질
- orphan·click depth·internal links·broken links
- title, description, H1/headings, lang, alt, anchor
- duplicate/near duplicate metadata와 content
- JS 렌더 전후 핵심 콘텐츠 차이
- mobile viewport, HTTPS, mixed content
- Lighthouse lab와 CrUX field 분리
- LCP, INP 또는 lab 대체값, CLS, FCP, TBT 등 버전별 metric
- JSON-LD 파싱·유효성·보이는 콘텐츠 일치
- Google/Naver 지원 여부와 일반 Schema.org 유효성을 구분
- GSC/Naver Search Advisor 연결 상태와 관측값
- 검색 노출·클릭·CTR·평균순위는 기술 점수와 분리

## 7. GEO 진단 엔진

### 7.1 GEO 준비도 100

```text
접근·검색 적격성             20
답변 추출성                  20
근거·출처 투명성             15
엔터티 명확성·일관성         15
구조화 데이터·메타           10
최신성·변경 신호             10
외부 검증 가능성             10
Total                       100
```

### 7.2 게이트

- HTTP 4xx/5xx, 인증 필요, noindex, 지정 검색봇 차단은 별도 `노출 차단` 상태다.
- 검색용 crawler와 학습용 crawler를 구분한다.
- GPTBot 학습 차단을 GEO 오류로 감점하지 않는다.
- schema 부재만으로 치명적 오류를 만들지 않는다.
- 허위 schema와 화면 불일치는 위험으로 처리한다.

### 7.3 실제 AI 가시성

준비도와 별도 데이터로 저장·표시한다.

- Mention rate
- Citation rate
- Prompt coverage
- Mention Share of Voice
- Citation Share of Voice
- Winning prompt rate
- Source diversity
- Recommendation inclusion
- Stability/variation
- 95% confidence interval

모든 ObservationRun에 다음을 저장한다.

```text
prompt_id, prompt_text, intent, funnel, persona, locale,
engine, model/version, search_mode, account_state,
timestamp, run_id, raw_answer, citations,
mentioned_entities, errors, cost, latency
```

프롬프트×엔진당 탐색은 최소 3회, 비교 보고는 5회 이상을 기본값으로 하되 비용 설정으로 조정 가능하게 한다. 한 번의 결과를 시장 점유율로 표현하지 않는다.

### 7.4 답변 위험

- 사실 정확성
- citation entailment
- citation completeness
- entity disambiguation
- recommendation inclusion/exclusion
- sentiment와 근거
- stale information
- 의료·법률·가격·계약 등의 중요 오류 severity

자동 판정과 사람 검수 상태를 분리한다.

## 8. 네이버 키워드 엔진

### 8.1 데이터 출처

- `NAVER_SEARCH_AD`: 절대 검색량·클릭·CTR·경쟁도·광고 노출 관련 공식 응답
- `NAVER_DATALAB`: 상대 검색 관심도 추세
- `CALCULATED`: 합계·기기 비중·의도·기회 점수
- `VEO_INTERNAL`: VEO 사용자 조회·저장·캠페인 데이터

UI에서 출처 badge와 기준시각을 보여준다.

### 8.2 핵심 필드

- original_keyword, normalized_keyword
- monthly_pc_searches, monthly_mobile_searches
- monthly_total_searches
- pc/mobile share
- avg_pc/mobile_clicks
- avg_pc/mobile_ctr
- competition_index/label
- average_ad_depth 또는 공식 최신 필드
- related keywords와 source rank
- requested_at, source_period, raw response hash
- cache hit, API version, partial/error status

공식 API의 필드·정의는 최신 공식 문서와 fixture를 기준으로 adapter mapping에 고정하고 mapping test를 작성한다.

### 8.3 API 운영

- 인증 서명과 timestamp를 서버에서 생성
- secret/customer ID를 클라이언트에 노출하지 않음
- 429/5xx 지수 backoff+jitter
- account-level rate limit
- 키워드 단위 cache와 freshness
- raw response snapshot
- circuit breaker와 graceful degradation
- DataLab 상대지수를 검색량 횟수처럼 표시하지 않음

### 8.4 기회 점수

```text
demand = log1p(total_monthly_searches)의 0~1 정규화
trend = DataLab 상승률·계절성 0~1
intent_fit = 사업·페이지 목적 적합도 0~1
competition_inverse = 경쟁이 낮을수록 높은 0~1
content_gap = 자사 미보유·경쟁사 보유 기회 0~1
confidence = 최신성·결측·표본 신뢰도 0~1

opportunity_score = 100 × confidence × (
  0.30×demand + 0.20×trend + 0.20×intent_fit
  + 0.15×competition_inverse + 0.15×content_gap
)
```

VEO 자체 산식임을 명시하고 산식 버전을 저장한다. 광고 경쟁도와 자연검색 경쟁 추정을 분리한다.

### 8.5 인기 키워드 명칭

공식 근거가 없는 `실시간 인기검색어` 명칭을 사용하지 않는다. 실제 데이터에 따라 다음 중 하나를 선택한다.

- VEO 최근 조회 키워드
- 최근 24시간 급상승 키워드
- 업종별 추천 키워드
- 내부 프로젝트 인기 키워드

기준 기간, 데이터 범위, 갱신 시각, 비식별화 규칙을 표시한다.

## 9. 경쟁사 비교

- 동일한 측정 범위·프롬프트·엔진·기간·반복 횟수를 적용한다.
- 고객이 경쟁사를 직접 지정하고 시스템 추천을 별도로 표시한다.
- SEO에서는 URL/템플릿/키워드/콘텐츠/성능/링크 차이를 비교한다.
- GEO에서는 mention/citation SOV, winning prompts, 경쟁 출처, 답변 위험을 비교한다.
- 키워드에서는 demand, trend, intent, content gap을 비교한다.
- 비교군이 바뀌면 SOV 값도 달라진다는 사실을 표시한다.

## 10. 점수 버전 관리

VEO-LAB이 명세를 작성하고 VENOM이 구현·검증한다.

ScoringVersion은 다음을 가진다.

- id, domain, semantic_version
- status: DRAFT/REVIEW/APPROVED/PUBLISHED/RETIRED
- effective_at
- specification JSON/YAML
- human-readable changelog
- approved_by와 checksum
- compatible collector versions
- golden fixture results

발행된 버전은 변경하지 않는다. 새 버전으로 복제해 수정한다. 기존 결과를 새 산식으로 재계산할 때 원래 점수와 재계산 점수를 둘 다 보존한다.

## 11. API 설계

최소 endpoint를 OpenAPI로 설계하라.

### Public

- `POST /api/public/v1/seo-scans`
- `POST /api/public/v1/geo-readiness-scans`
- `POST /api/public/v1/keyword-lookups`
- `GET /api/public/v1/jobs/{job_id}`
- `GET /api/public/v1/results/{token}`
- `POST /api/public/v1/leads`

### Internal

- auth/users/roles
- customers/projects/sites/competitors CRUD
- scans/runs/jobs/evidence
- SEO/GEO/keyword execution and results
- prompt sets/observations/citations
- issues/fixes/verifications
- reports/versions/exports
- scoring versions/review/publish
- API usage/cost

### 공통 응답

- request_id
- data 또는 error
- safe user message
- machine-readable error code
- pagination
- generated_at/source_freshness
- permission-safe links

API 변경은 contract test와 generated client 갱신 없이 병합하지 않는다.

## 12. 프론트엔드 UX

### 12.1 디자인 원칙

- NXT 화면을 복제하지 않는다.
- VEO 고유 디자인 시스템을 만든다.
- 비전문 사업자는 결과를 한 번 읽고 다음 행동을 이해할 수 있어야 한다.
- 개발자는 원시 증거와 수정 위치를 확인할 수 있어야 한다.
- 색상만으로 상태를 전달하지 않는다.
- 키보드·스크린리더·모바일 반응형을 지원한다.

### 12.2 결과 카드

하나의 종합 점수 대신 다음을 분리한다.

- SEO 기술 준비도
- Google 준비도
- Naver 준비도
- 검색 성과
- GEO 준비도
- AI 가시성
- 경쟁 SOV
- 답변 위험
- 측정 신뢰도
- 키워드 수요·트렌드·기회

### 12.3 사용자별 보기

- Business view: 상태, 경쟁 격차, 상위 5개 조치
- Analyst view: segment, source, sample, confidence, history
- Developer view: URL, HTTP/DOM evidence, selector, fix example, retest

한 원시 결과에서 보기만 다르게 만들며 별도 계산을 중복하지 않는다.

## 13. GPT/OpenAI 사용 계약

GPT 호출은 provider interface 뒤에 둔다.

허용 작업:

- 검색 의도·퍼널·페이지 유형 분류
- 엔터티·주장·출처 추출
- passage extractability 평가 보조
- AI 답변의 브랜드·경쟁사 언급 판별
- citation entailment 후보 판정
- 사실 오류 후보와 설명 생성
- 사업자용 개선 설명과 콘텐츠 brief

금지 작업:

- HTTP/robots/canonical/CWV 등 결정적 사실 판정 대체
- 공식 API 값 생성
- 최종 점수 임의 생성
- 출처 없이 검색량·경쟁도 추정
- 원시 답변 없이 브랜드 노출 여부 단정

모든 GPT 응답은 JSON Schema structured output으로 검증한다. prompt_version, model, parameters, input_hash, output, token/cost, validation result를 저장한다. 중요한 위험 판정은 사람 검수 가능하게 한다.

## 14. 보안 요구사항

### URL/크롤러

- URL allow scheme http/https only
- DNS resolve 후 모든 IP 검증
- redirect마다 재검증
- localhost, RFC1918, link-local, multicast, metadata IP 차단
- DNS rebinding 완화
- port allowlist
- response size/time/decompression limit
- content-type validation
- credential-bearing URL 거부
- browser sandbox와 네트워크 정책

### 애플리케이션

- secure session/token rotation
- RBAC deny by default
- CSRF/CORS/CSP
- input validation과 output encoding
- SQL injection 방어
- secret manager
- audit logs
- PII retention/deletion
- signed expiring result/export URLs
- rate limiting과 abuse detection

보안 테스트에는 SSRF 우회, redirect 우회, IPv6, decimal/hex IP, userinfo URL, DNS 변화, 대형 응답, zip bomb 유사 상황을 포함한다.

## 15. 테스트 전략

### 단위 테스트

- scoring formulas와 caps
- URL normalization·SSRF
- Naver field mapping·rounding·null
- GEO metric calculation
- confidence intervals
- permissions

### Golden fixtures

- SEO 대표 HTML/HTTP/robots/sitemap
- JavaScript rendered/unrendered cases
- JSON-LD graph cases
- Naver API success/low volume/null/429/5xx
- AI answers with correct/incorrect/missing citations
- multilingual and same-name brands

### 통합 테스트

- DB+Redis+worker
- job retry/idempotency/cancellation
- external provider mocks
- object storage
- report export

### 계약 테스트

- OpenAPI schema
- generated TypeScript client
- backward compatibility
- scoring spec schema

### E2E

- 공개 SEO/GEO/keyword 검사
- 내부 고객 프로젝트 생성→진단→검수→보고서
- 수정사항 등록→재검증
- 권한별 접근
- external API partial failure

### 비기능

- accessibility WCAG 2.2 AA 목표
- load/rate limit
- queue backlog recovery
- backup/restore
- cost budget alerts

## 16. 관측성과 비용

다음을 metric/log/trace로 수집한다.

- request latency/error rate
- queue depth/wait/runtime/retry
- crawl pages/bytes/time/status distribution
- Playwright concurrency
- external API call/429/5xx/cache hit
- OpenAI tokens/cost/validation failures
- report generation time
- user/project/domain usage

고객 원문과 비밀정보는 관측 로그에서 마스킹한다. 프로젝트·작업·요청 ID로 추적한다.

## 17. 보고서

보고서는 versioned snapshot이다.

- Executive summary
- 측정 범위·시각·버전·신뢰도
- SEO 결과
- GEO 준비도·실제 가시성·경쟁사
- 네이버 키워드 수요·트렌드·기회
- 답변 오류·브랜드 위험
- 상위 개선 우선순위
- 사업자/마케팅/개발자 실행 항목
- 재검증 계획
- 근거 출처와 필수 고지

PDF/DOCX 또는 HTML export adapter를 설계하고 원시 증거 접근 권한을 지킨다.

## 18. 구현 단계와 완료 조건

### Phase 0 — Discovery/Contracts

산출물:

- requirements traceability matrix
- architecture ADR
- domain model
- OpenAPI draft
- scoring spec schema
- test strategy
- parallel work plan

완료 조건: 모든 핵심 계약을 루트가 검토하고 mock으로 프론트·백엔드가 독립 개발 가능하다.

### Phase 1 — Foundation

- monorepo, Docker, CI
- auth/RBAC
- customer/project/site
- job/worker/Redis
- evidence/storage
- frontend shell/design system

### Phase 2 — Public MVP

- 단일 URL SEO
- 단일 URL GEO readiness
- 단일 Naver keyword
- async progress/result
- lead conversion
- security/rate limit

### Phase 3 — Internal Console

- site crawl
- batch keyword
- issues/fixes/retest
- report baseline
- scoring versions

### Phase 4 — Advanced Intelligence

- actual AI observations
- competitor SOV
- search engine integrations
- trends and outcomes
- human review workflow

### Phase 5 — Production Hardening

- load/security/a11y
- monitoring/alerts
- backup/restore
- cost controls
- runbooks

각 Phase가 끝날 때 실행한 검증 명령과 결과를 기록한다. 테스트가 통과하지 않았으면 완료라고 말하지 않는다.

## 19. 작업 방식

1. 먼저 읽기 전용으로 저장소와 자료를 조사하라.
2. 구현 전에 상세 계획과 병렬 작업표를 제시하라.
3. 불필요한 질문으로 멈추지 말고 안전한 기본값으로 진행하되 사업·보안·비용을 크게 바꾸는 선택만 질문하라.
4. 기존 사용자 변경을 덮어쓰지 말라.
5. 작은 단위로 구현하고 테스트하라.
6. 외부 API가 없으면 mock을 제공하되 실제 연동이 됐다고 주장하지 말라.
7. 각 에이전트 완료 후 루트가 직접 검증하라.
8. 문서와 코드가 다르면 코드를 고치거나 문서를 갱신하라.
9. 마지막에는 설치·실행·환경변수·테스트·배포·운영 방법을 제공하라.

## 20. 첫 응답에서 할 일

코드를 바로 만들지 말고 다음을 먼저 제시하라.

1. 발견한 리서치·요구사항 요약
2. 누락된 입력과 안전한 기본 가정
3. 최종 아키텍처와 모듈 경계
4. 핵심 DB 엔터티 관계
5. OpenAPI 계약 초안 범위
6. 점수 엔진·외부 API·GPT 경계
7. Wave별 병렬 분담표
8. Phase별 구현·검증 계획
9. 위험 목록과 완화책

사용자 승인 후 Phase 0부터 실행하라.

## 프롬프트 끝

---

## 사용 방법

1. 새 Codex 작업에서 VEO용 빈 저장소 또는 작업 폴더를 연다.
2. 통합 보고서와 리서치 폴더를 저장소의 `docs/research/` 아래 복사한다.
3. 위 `프롬프트 시작`부터 `프롬프트 끝`까지 붙여 넣는다.
4. Codex가 제시하는 Phase 0 설계와 병렬 분담을 먼저 검토한다.
5. 승인 후 구현을 진행한다.

프롬프트가 길어 한 번에 처리하기 어렵다면 다음 경계로 나눈다.

- Part A: 1~5 — 제품·아키텍처·병렬화·도메인
- Part B: 6~10 — SEO·GEO·키워드·경쟁·점수
- Part C: 11~17 — API·UI·GPT·보안·테스트·운영·보고서
- Part D: 18~20 — 단계·작업 방식·첫 응답 계약

