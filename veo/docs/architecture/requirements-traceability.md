# VEO 요구사항 추적표 (Phase 0 · 1 · 2 · 3)

**제품:** VEO — SEO · GEO · Naver Keyword Intelligence Platform
**개발:** VENOM · **연구·방법론:** VEO-LAB

근거 문서는 `docs/research/`에 원문 그대로 보관합니다. 각 행은 요구사항 →
구현 위치 → 검증 방법을 연결합니다.

> ## ⚠ 이 표를 근거로 "없다" 고 판단하지 마라
>
> 이 표는 **Phase 0 시점의 계획**으로 쓰였고, 그 뒤 코드가 앞서갔는데 표가 따라오지
> 못한 줄이 여럿 있었다. 실제로 두 번, 여기 적힌 "미착수" 때문에 **이미 있는 기능을
> 없는 줄 알았다** (GEO 관측 약 7,300줄, 네이버 SearchAd 실 연동).
>
> **손대기 전에 폴더를 열어 확인해라.** 지침서 0-D.
>
> 2026-07-31 에 실물과 대조해 아래 표를 고쳤다. 대조 방법은 각 행에 적었다.

## 1. 절대 원칙 (마스터 프롬프트 §"절대 지켜야 할 원칙")

| # | 요구사항 | 구현 | 검증 |
|---|---|---|---|
| 1 | SEO·GEO·키워드를 하나의 총점으로 합치지 않는다 | 도메인별 독립 spec `veo.seo.readiness` / `veo.geo.readiness`, 키워드는 별도 테이블·산식 | `test_published_specs.py::test_geo_readiness_never_carries_observation_metrics`, `test_schema_invariants.py::test_readiness_scores_and_observed_visibility_live_in_different_tables` |
| 2 | 정적 검사를 실제 순위·AI 노출로 표현하지 않는다 | spec의 `score_meaning.is_rank_prediction`은 스키마에서 `const: false` | `test_published_specs.py::test_published_spec_loads_and_is_marked_published`, `test_openapi_contract.py::test_published_specs_are_exposed_in_full` |
| 3 | 점수는 결정적 코드로만 계산한다 | `veo/scoring/evaluator.py` 단일 evaluator. LLM 경로 없음 | `tests/scoring/*` 전체 |
| 4 | GPT는 의미 판단에만 사용한다 | `fix_recommendations.generated_by`, `claim_assessments.llm_model/llm_prompt_version`로 LLM 산출물 분리 표시 | 스키마 존재 검증 (Phase 3에서 provider 구현 시 확장) |
| 5 | 모든 결과에 원자료·시각·범위·출처·버전을 연결 | `evidence`, `check_results.evidence_ids`, `score_results.spec_checksum/calculation_trace` | `test_schema_invariants.py::test_score_result_keeps_everything_needed_to_defend_a_number` |
| 6 | 통과/부분/실패/해당없음/측정불가를 구분 | `CheckStatus` 5개 값, `not_applicable_reason`·`unknown_reason` 컬럼 분리 | `test_evaluator.py` N/A·UNKNOWN 그룹 |
| 7 | SearchAd / DataLab / VEO 계산값 구분 | `DataSource` enum, `keyword_metrics`(절대량) vs `keyword_trends`(상대지수) 테이블 분리 | `test_schema_invariants.py::test_datalab_trend_is_stored_apart_from_search_counts` |
| 8 | 공개·내부가 같은 엔진, 다른 범위 | `Surface` enum이 job·scan_run·keyword_query에 존재 | `test_schema_invariants.py` (컬럼), Phase 2에서 한도 구현 |
| 9 | NXT 코드·디자인·카피 미복제 | 독립 spec·독립 디자인 토큰. NXT 자산 반입 없음 | 코드 리뷰 |
| 10 | 비밀키·원시 AI 답변 평문 로그 금지 | `ai_answers`는 storage key + hash만 보관, `audit_logs.source_ip_hash` | `test_schema_invariants.py::test_raw_ai_answers_are_referenced_not_inlined`, `::test_audit_log_never_stores_a_raw_ip` |

## 2. SEO 점수 모델 (마스터 §6, `docs/research/SEO_RECOMMENDED_SCORING_MODEL.md`)

| 요구사항 | 구현 | 검증 |
|---|---|---|
| 8개 카테고리 25/15/15/15/10/10/5/5 | `packages/scoring-specs/specs/veo.seo.readiness/1.0.0.yaml` | `test_published_specs.py::test_category_weights_sum_to_declared_total`, golden `seo-01` |
| 심각도 계수 1.00/0.60/0.30/0.10/0.00 | spec `severity_coefficients` | `test_evaluator.py::test_single_fail_uses_severity_over_category_budget` |
| `penalty = severity × coverage × confidence` | `evaluator._score_category` | `test_evaluator.py::test_coverage_ratio_scales_the_penalty`, `::test_confidence_scales_the_penalty` |
| `category_score = 100 × max(0, 1 − Σpenalty/budget)` | 동일 | golden `test_golden.py::test_golden_fixture_score_is_reproducible_from_its_own_trace` |
| 치명적 상한 25/35/40/55/60 | spec `caps` | `test_published_specs.py::test_seo_caps_match_the_methodology_ceilings`, golden `seo-04` |
| 상한 사유·해제 조건 표시 | `AppliedCap.reason_ko` / `release_condition_ko` | `test_evaluator.py::test_cap_bounds_the_overall_score` |
| URL 중요도 3.0/2.0/1.0/0.5, 의도된 noindex 제외 | spec `url_importance` (`INTENTIONAL_NOINDEX: 0.0`) | `test_openapi_contract.py::test_spec_detail_publishes_weights_caps_and_release_conditions` |
| Lighthouse lab과 CrUX field 분리 | `seo.perf.*_lab` vs `seo.perf.inp_field` (별도 check, CrUX 표본 없으면 N/A) | spec 정의 + golden `seo-03` |
| 필수 검사 항목 47종 | spec **1.6.0 에서 57종** | `test_published_specs.py::test_every_check_declares_required_evidence` |
| 검사 실행(collector) | **완료.** `seo/collectors/` 8개 파일 — 카테고리마다 하나 | `tests/seo/` · 실사이트 대조 |
| 사이트 전체 발견 크롤 | **완료.** `seo/discovery.py` + `seo/crawl.py` (사이트맵 + 내부링크 BFS, 동시 4개) | `tests/seo/test_discovery.py` |
| 헤드리스 렌더 (`js_render_parity`) | **미착수.** Playwright 참조가 코드에 0건 — 실사이트에서 늘 측정 불가 | — |
| PageSpeed · CrUX 실호출 | 어댑터는 `providers/google/` 에 있으나 **키 미등록** → 성능 4항목 상시 측정 불가 | `test_provider_endpoint_reports_disabled_providers_honestly` |

## 3. GEO (마스터 §7, `docs/research/GEO_RECOMMENDED_SCORING_MODEL.md`)

| 요구사항 | 구현 | 검증 |
|---|---|---|
| 준비도 7영역 | `veo.geo.readiness/1.1.0.yaml` — 점수 영역 6개로 100(외부 검증 가능성은 수집 경로가 없어 점수 밖) | `test_published_specs.py`, golden `geo-01` |
| 4xx/5xx·인증·noindex·검색봇 차단은 별도 `노출 차단` 상태 | spec `gates` (점수 산식 미개입) | `test_evaluator.py::test_gate_is_reported_without_changing_the_score`, golden `geo-02` |
| 학습용 봇 차단을 감점하지 않는다 | `geo.access.training_bot_policy_declared` severity `INFO` (계수 0) | `test_evaluator.py::test_info_severity_cannot_reduce_the_score`, golden `geo-02` |
| 주소만으로 준비도 진단 | **완료.** `POST /geo/readiness/scans` — SEO 와 **같은 수집 경로**(`collect/from_crawl.py`) | `tests/geo/test_scan_from_crawl.py` |
| GEO 도 절대 평가인가 | **완료 (1.1.0).** 1.0.0 은 상대 평가로 남아 있었다 — SEO 는 1.2.0 에서 옮겼는데 GEO 만 안 옮겨졌고, **그 규칙을 검사하는 코드가 없어서** 아무도 몰랐다. 실측 www.seokorea.org 79.86(분모 90) → 75.10(분모 100) | `test_every_published_spec_is_absolute.py` — 앞으로 발행되는 **모든** 명세를 검사한다 |
| schema 부재만으로 치명적 오류 금지 | 구조화 데이터 check 전부 `applicability_ko`로 N/A 명시 | golden `geo-03-no-schema-online-only` |
| 허위 schema는 위험으로 처리 | `geo.sd.matches_visible_content` severity `BLOCKER` + gate `STRUCTURED_DATA_MISMATCH` | spec 정의 |
| 준비도와 실제 가시성 분리 저장·표시 | `score_results` vs `observation_runs`/`ai_answers`/`citations`/`entity_mentions` | `test_schema_invariants.py::test_readiness_scores_and_observed_visibility_live_in_different_tables` |
| ObservationRun 필수 필드 | `observation_runs` + `ai_answers`(prompt·engine·model_version·search_mode·account_state·locale·executed_at·raw hash·citations) | `test_schema_invariants.py` |
| 한 응답 = 브랜드당 언급 1회 | `entity_mentions` `UniqueConstraint(ai_answer_id, entity_key)` + `raw_occurrence_count` 별도 | 스키마 제약 |
| 관측 실행 (실제 LLM 호출) | **완료.** `observations/execution.py` + `POST /observations/runs`. OpenAI 키 등록됨 | `tests/observations/test_execution_postgres.py` |
| 인용 관측 가능성 구분 | `ai_answers.citation_support` — `STRUCTURED` / `NOT_EXPOSED_BY_PROVIDER`. 실측: `gpt-5`·`gpt-4o` 는 인용을 돌려주고 `gpt-4.1`·`gpt-4o-mini` 는 안 돌려준다 | `docs/operations/verifying-citation-support.md` |
| 노출률 지표 | 언급률·인용률·질문 도달률 + Wilson 구간 | `tests/observations/test_metrics.py` |
| 가시성 지표 10종 (마스터 §7.3) | **7/10.** 없는 것: 출처 다양성 · 추천 포함 · 안정성(변동) | grep: `source_diversity`·`recommendation_inclusion` 0건 |
| 자동 판정과 사람 검수 분리 | 모듈은 완성(`observations/risk/`·`review/`)이나 **`src/` 안에 호출자가 없다.** `ClaimAssessment` 를 db/models 밖에서 쓰는 코드 0건 → 제품에서는 아직 돌지 않는다 (지침서 0-E) | `tests/observations/` 만 부른다 |
| 관측 SOV 를 실측에서 계산 | **미연결.** `competitors/sov.py` 는 완성됐으나 입력이 요청 본문(`ObservedVisibilityInput`)이라 사람이 숫자를 넣어야 한다 | — |
| 관측을 비동기로 실행 | **완료.** 202 + `GET /api/jobs/{id}` 로 진행률 조회. 작업 본문은 `observations/jobs.py` | `TestTheJobPath` |

## 4. 네이버 키워드 (마스터 §8)

| 요구사항 | 구현 | 검증 |
|---|---|---|
| SearchAd / DataLab / CALCULATED / VEO_INTERNAL 구분 | `DataSource` enum + 테이블 분리 | `test_schema_invariants.py::test_datalab_trend_is_stored_apart_from_search_counts` |
| DataLab 상대지수를 검색량처럼 표시 금지 | `keyword_trends.relative_index` (컬럼명·주석·별도 테이블) | 동일 |
| 0·결측·억제값·범위값 구분 | `ValueQuality` enum + `*_quality` 페어 컬럼, 수치 컬럼 nullable | `test_schema_invariants.py::test_keyword_metrics_pair_every_count_with_a_quality_flag` |
| 출처·갱신시각·API 버전·raw hash 보존 | `keyword_metrics.source/collected_at/api_version/raw_response_hash` | 동일 |
| 기회점수는 VEO 자체 산식이며 버전 보존 | `keyword_opportunities.formula_version` + 구성요소 컬럼 분리 + `calculation_trace` | 스키마 |
| '실시간 인기검색어' 표현 금지 | 코드·스키마·문서 어디에도 해당 명칭 없음 | 문자열 검사 (릴리스 체크리스트) |
| SearchAd 서명·호출 구현 | **완료.** `providers/naver/searchad.py` 를 `keywords/service.py` 가 직접 부른다. `veo/.env` 에 SearchAd·DataLab 자격증명 등록됨 | `tests/keywords/` · `test_provider_endpoint_reports_disabled_providers_honestly` |
| 키워드 화면 | **없음.** `/console/keywords` 는 API 를 부르지 않는 자리표시자다 — 백엔드가 실 API 에 붙어 있는데 사람이 쓸 경로가 없다 | — |

## 5. 작업·상태 모델 (마스터 §5)

| 요구사항 | 구현 | 검증 |
|---|---|---|
| 9개 작업 상태 | `JobStatus` | `packages/shared-types/src/enums.ts` 생성 + `test_openapi_contract.py::test_every_python_contract_enum_value_reaches_typescript` |
| idempotency·input_hash·재시도·취소·부분성공 | `jobs` 테이블 + `apps/worker/runtime` (런타임만. 저장소는 아직 프로세스 로컬 — 8.2) | `test_schema_invariants.py::test_jobs_support_idempotency_retry_and_partial_success` + worker 테스트 |
| 장시간 작업의 동기 실행 금지 | **관측은 해소.** `POST /observations/runs` 가 202 를 돌려주고 실행은 `veo/jobs/` 를 통해 요청 밖에서 돈다. **`POST /seo/scans` 는 아직 동기다** — 25장에 4.9초라 지금은 견디지만 100장이면 위험하다 | `tests/resources/test_jobs_api.py` · `test_execution_postgres.py::TestTheJobPath` |
| 작업 실행 방식 | **배경 스레드**다. Celery 워커가 아니다 — 배포 환경에 브로커(Redis)가 없다. 대가는 프로세스 재시작 시 작업이 죽는 것이고, `STALE_AFTER`(20분)로 **"알 수 없음"** 으로 드러낸다 | `tests/jobs/test_service.py::TestStaleness` |
| 멱등성 | `Idempotency-Key` 헤더 → 같은 키면 새 실행을 만들지 않는다. 관측은 돈이 나가므로 새로고침이 두 번째 청구가 되면 안 된다 | `TestTheJobPath::test_the_same_idempotency_key_does_not_buy_a_second_run` |
| `GET /api/public/v1/jobs/{job_id}` (마스터 §11) | **없음.** 내부용 `GET /api/jobs/{job_id}` 만 있다. 공개 진단은 아직 동기라 진행률 조회가 필요 없는 상태 | — |

## 6. API·계약 (마스터 §11)

| 요구사항 | 구현 | 검증 |
|---|---|---|
| 공통 응답: request_id / data·error / safe message / error code / pagination / generated_at | `veo/contracts/envelope.py` | `test_openapi_contract.py` envelope 그룹 |
| OpenAPI를 단일 계약으로 | `apps/api/openapi.json` + `scripts/export_openapi.py --check` | `test_openapi_contract.py::test_committed_openapi_matches_the_running_application` |
| 생성된 TS client 갱신 없이 병합 금지 | `packages/api-client` + `pnpm check` drift 검사 | `test_openapi_contract.py::test_generated_typescript_client_exists_and_covers_every_path` |
| Public/Internal 전체 endpoint | **경로 71개 발행.** 없는 것: `public/v1/jobs/{job_id}`, API usage/cost | `openapi.json` |
| 화면이 그 계약을 쓰는가 | ❌ **71개 중 15개만.** 콘솔 12화면 중 실제로 API 를 부르는 것은 `seo`·`customers`·`team`·`account` 넷뿐이고, 공개 진단 3화면도 자리표시자다 (지침서 0-E) | `apps/web` 전체에서 `fetch(` 하는 파일 8개 |

## 7. 보안 (마스터 §14)

| 요구사항 | 구현 | 검증 |
|---|---|---|
| SSRF 방어 (scheme·port·IP·redirect·rebinding) | `veo/common/security/url_guard.py` | `apps/api/tests/common/` (616건) |
| 응답 크기·시간·압축비·content-type 한도 | `veo/common/security/limits.py` | `test_fetch_limits.py` |
| RBAC deny by default | `veo/authz/permissions.py` 단일 행렬 | `tests/authz/test_permissions.py` |
| 조직 간 데이터 격리 (구조적 강제) | `veo/authz/tenancy.py` — `tenant_select` + `assert_tenant_scoped` | `tests/authz/test_tenancy.py` |
| 다른 조직 리소스는 404 (403 아님) | `OrganizationMismatch` → 404 핸들러 | `tests/resources/` cross-tenant 행렬 |
| 세션·토큰 회전·폐기 | `veo/auth/**`, `user_sessions` 테이블 | `tests/auth/` |
| credential 암호화 저장·되읽기 불가 | `veo/credentials/**`, `provider_credentials` 테이블 | `tests/credentials/` |
| 조직 간 데이터 격리 | 모든 테넌트 테이블에 `organization_id` NOT NULL + 인덱스 | `test_schema_invariants.py::test_tenant_tables_carry_organization_id` |
| credential 보호 | `ProviderCredentials`가 `SecretStr`, 응답·로그 미노출 | `test_openapi_contract.py::test_provider_endpoint_reports_disabled_providers_honestly` (값이 아니라 상태만 노출) |
| 인증·RBAC·세션 | `veo/auth/**` — argon2id, JWT 15분, refresh 회전·패밀리 폐기, 잠금 | `tests/auth/` (109건) + `tests/security/` (18건) |

## 8. 알려진 미완결 위험 — Phase 2 착수 조건

### 8.1 SSRF: 연결 단계 IP 고정 — ✅ 해소됨

`common/security/fetcher.py` 의 `SafeFetcher` 가 `decision.resolved_ip` 로 직접 연결하고
`Host` 헤더와 SNI 만 원래 호스트로 유지한다. `follow_redirects` 를 쓰지 않고 hop 마다
재검증한다. **아래 원래 우려는 해소되었으나, 무엇을 왜 만들었는지 남긴다.**

> `url_guard`는 호스트를 resolve하고 모든 주소를 검증한 뒤 `decision.resolved_ip`를
> 돌려주지만, HTTP 클라이언트가 그 IP로 접속하도록 강제할 수단이 이 모듈에는 없었다.
> 수집기가 검증만 하고 `httpx.get(url)`을 그대로 호출하면 DNS rebinding으로 위 검증이
> 전부 무력화된다. 이 두 가지가 없으면 URL 검증은 장식일 뿐이다.

### 8.1a 원문 AI 답변이 재배포에서 살아남지 못한다 (신규)

`observations/answer_store.py` 는 `FilesystemAnswerStore` 하나뿐이고 기본 경로가
`var/observations/answers` 다. `providers/storage.py` 는 "S3 어댑터는 이 모듈의 범위
밖" 이라고 스스로 적어 두었다.

`ai_answers` 행에는 저장 키와 해시만 남는다(원문 인라인 금지). Railway 컨테이너
파일시스템은 재배포마다 초기화되므로, **파일이 사라지면 "이 판정의 근거를 보여 달라"에
답할 수 없다.** 마스터 0-A 의 마지막 줄이 무너지는 지점이다. compose 에는 MinIO 가
이미 있고 어댑터만 없다.

### 8.2 작업 런타임의 저장소가 프로세스 로컬이다

`IdempotencyStore`, `JobStore`, `CancellationRegistry`의 현재 구현은 in-memory다.
프로토콜과 필요한 원자성은 문서화돼 있으나, 다중 워커 배포 전에 공유 백엔드
(Redis 또는 PostgreSQL) 구현이 필요하다.

### 8.3 Docker 이미지가 이 장비에서 검증되지 않았다

개발 장비에 Docker가 설치돼 있지 않아 `docker build`와 `docker compose up`을 실행하지
못했다. compose 파일은 YAML 파싱으로만 확인했다. Docker가 있는 환경에서 최초 1회
검증이 필요하다.

## 8.5 Phase 3 — 통합 기능 (마스터 §9, §10, §17)

| 요구사항 | 구현 | 검증 |
|---|---|---|
| 경쟁사는 동일 수집 범위·규칙으로 측정 | `veo/compare/conditions.py` — `assert_comparable()` | `tests/compare/` (25건) |
| 비교군이 바뀌면 SOV도 바뀜을 표시 | SOV 값에 비교군·안내 동봉 | `tests/competitors/` |
| 데이터 차이 경고 | `describe_differences()` — 차단·비차단 모두 보고 | `tests/compare/` |
| 이슈 → 수정 → 재검증 | `veo/issues/lifecycle.py` 상태 기계 | `tests/issues/` |
| 재발 추적 | 이슈 지문 + `RECURRED` 횟수·주기 | `tests/issues/` |
| 발행 버전 불변 | `veo/lab/versions.py` — PUBLISHED 수정 거부 | `tests/lab/` |
| 재계산 시 원 점수·재계산 점수 병존 | `veo/lab/rescore.py` — 새 행 기록, 원본 무변경 | `tests/lab/` |
| 보고서는 versioned snapshot | `veo/reports/snapshot.py`, `ReportVersion`(ImmutableMixin) | `tests/reports/` |
| 역할별 보기(경영진·마케팅·개발자) | `veo/reports/views.py` — 한 스냅샷에서 파생 | `tests/reports/` |
| HTML/CSV/XLSX 내보내기 | `veo/reports/render/` | `tests/reports/` |

## 9. Phase 1에서 추가로 확인한 위험

### 9.1 폐기된 access token은 최대 15분간 유효하다

역할 회수는 다음 요청에 즉시 반영되지만(역할을 DB에서 읽으므로), 세션 폐기는 access
token 만료까지 최대 15분이 남는다. 계정 탈취가 확정된 경우처럼 즉시 차단이 필요한
사건에는 별도의 거부 목록이 필요하며 Phase 1 범위 밖이다.

### 9.2 로그인 잠금은 식별자 단위이고 IP 단위가 아니다

한 주소에 대한 무차별 대입은 막히지만, 여러 주소에 걸친 password spraying은 느려지지
않는다. 엣지 레이트 리밋이 나머지 절반이다.

### 9.3 자격증명 지문은 마스터 키가 함께 유출되면 오프라인 오라클이 된다

HMAC-SHA256은 빠르고 행마다 salt가 없어, 네이버 `customer_id`처럼 짧고 엔트로피가 낮은
값은 무차별 대입이 가능하다. Argon2id로 바꾸면 해소된다. 삭제한 자격증명도 지문은
감사 연속성을 위해 남으므로 이 표면은 삭제 후에도 유지된다.

### 9.4 진행 중인 장시간 작업은 시작 시점의 권한으로 계속된다

권한 회수가 실행 중인 작업을 멈추지 않는다. 작업 취소로 대응해야 한다.

## 10. 지금 실제로 비어 있는 곳 (2026-07-31 실물 대조)

위 §10 은 원래 "Phase 0 범위 밖" 목록이었는데 **네 항목 중 셋이 그 뒤에 구현되었다.**
목록을 그대로 두면 다음 사람이 있는 것을 없다고 읽는다(지침서 0-D). 실물 기준으로
바꾼다.

**만들어졌고 제품에서 돈다**

- SEO 수집기 8개 · 사이트 전체 발견 크롤 · 병렬 수집
- GEO 준비도 수집기 7개
- 네이버 SearchAd / DataLab 실 호출
- AI 관측 실행 · 저장 · 노출률 지표
- 이슈 워크플로 · 보고서 스냅샷 · CSV/XLSX/HTML 내보내기 · 점수 발행 워크플로

**만들어졌지만 아무도 부르지 않는다** (지침서 0-E — 진행률에서는 완성으로 세어졌다)

| 무엇 | 증거 |
|---|---|
| 답변 위험 평가 · 사람 검수 | `ClaimAssessment` 를 db/models 밖에서 쓰는 코드 0건 |
| Celery 워커 | 태스크 전부 스텁, `.delay()` 호출 0건. **작업은 `veo/jobs/` 의 배경 스레드가 돈다** — 브로커가 생기면 이쪽으로 옮긴다 |
| 관측 SOV | 입력이 요청 본문이라 실측과 연결 안 됨 |
| 사용량·비용 | `APIUsageEvent` 참조 0건 |

**아직 없다**

- 헤드리스 렌더링(Playwright) — `js_render_parity` 상시 측정 불가
- 가시성 지표 3종: 출처 다양성 · 추천 포함 · 안정성
- 화면: `/console/sites` · `/console/api-usage` · `/console/admin` (파일 자체 없음)
- 동작하는 화면: 콘솔 12개 중 4개. 공개 진단 3개는 전부 자리표시자
- `tests/contract` · `e2e` · `integration` · `security` 는 **디렉터리가 비어 있고,
  CI 의 계약 잡은 파일이 없으면 경고만 찍고 통과시킨다** — 초록불이 검증을 뜻하지 않는다
- PDF 내보내기 (HTML/CSV/XLSX 는 있음)
- PageSpeed · Search Console · Anthropic · Gemini · Perplexity 자격증명
