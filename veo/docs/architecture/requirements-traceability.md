# VEO 요구사항 추적표 (Phase 0 · 1 · 2 · 3)

**제품:** VEO — SEO · GEO · Naver Keyword Intelligence Platform
**개발:** VENOM · **연구·방법론:** VEO-LAB

근거 문서는 `docs/research/`에 원문 그대로 보관합니다. 각 행은 요구사항 →
구현 위치 → 검증 방법을 연결합니다. `미착수`는 이후 Phase 대상이며, 0단계 완료
조건이 아닙니다.

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
| 필수 검사 항목 47종 | spec categories/checks | `test_published_specs.py::test_every_check_declares_required_evidence` |
| 검사 실행(collector) | **미착수 — Phase 2** | — |

## 3. GEO (마스터 §7, `docs/research/GEO_RECOMMENDED_SCORING_MODEL.md`)

| 요구사항 | 구현 | 검증 |
|---|---|---|
| 준비도 7영역 20/20/15/15/10/10/10 | `veo.geo.readiness/1.0.0.yaml` | `test_published_specs.py`, golden `geo-01` |
| 4xx/5xx·인증·noindex·검색봇 차단은 별도 `노출 차단` 상태 | spec `gates` (점수 산식 미개입) | `test_evaluator.py::test_gate_is_reported_without_changing_the_score`, golden `geo-02` |
| 학습용 봇 차단을 감점하지 않는다 | `geo.access.training_bot_policy_declared` severity `INFO` (계수 0) | `test_evaluator.py::test_info_severity_cannot_reduce_the_score`, golden `geo-02` |
| schema 부재만으로 치명적 오류 금지 | 구조화 데이터 check 전부 `applicability_ko`로 N/A 명시 | golden `geo-03-no-schema-online-only` |
| 허위 schema는 위험으로 처리 | `geo.sd.matches_visible_content` severity `BLOCKER` + gate `STRUCTURED_DATA_MISMATCH` | spec 정의 |
| 준비도와 실제 가시성 분리 저장·표시 | `score_results` vs `observation_runs`/`ai_answers`/`citations`/`entity_mentions` | `test_schema_invariants.py::test_readiness_scores_and_observed_visibility_live_in_different_tables` |
| ObservationRun 필수 필드 | `observation_runs` + `ai_answers`(prompt·engine·model_version·search_mode·account_state·locale·executed_at·raw hash·citations) | `test_schema_invariants.py` |
| 한 응답 = 브랜드당 언급 1회 | `entity_mentions` `UniqueConstraint(ai_answer_id, entity_key)` + `raw_occurrence_count` 별도 | 스키마 제약 |
| 자동 판정과 사람 검수 분리 | `claim_assessments.automated_verdict` vs `review_state` | 스키마 |
| 관측 실행 (실제 LLM 호출) | **미착수 — Phase 4.** provider 자격증명 없음 | — |

## 4. 네이버 키워드 (마스터 §8)

| 요구사항 | 구현 | 검증 |
|---|---|---|
| SearchAd / DataLab / CALCULATED / VEO_INTERNAL 구분 | `DataSource` enum + 테이블 분리 | `test_schema_invariants.py::test_datalab_trend_is_stored_apart_from_search_counts` |
| DataLab 상대지수를 검색량처럼 표시 금지 | `keyword_trends.relative_index` (컬럼명·주석·별도 테이블) | 동일 |
| 0·결측·억제값·범위값 구분 | `ValueQuality` enum + `*_quality` 페어 컬럼, 수치 컬럼 nullable | `test_schema_invariants.py::test_keyword_metrics_pair_every_count_with_a_quality_flag` |
| 출처·갱신시각·API 버전·raw hash 보존 | `keyword_metrics.source/collected_at/api_version/raw_response_hash` | 동일 |
| 기회점수는 VEO 자체 산식이며 버전 보존 | `keyword_opportunities.formula_version` + 구성요소 컬럼 분리 + `calculation_trace` | 스키마 |
| '실시간 인기검색어' 표현 금지 | 코드·스키마·문서 어디에도 해당 명칭 없음 | 문자열 검사 (릴리스 체크리스트) |
| SearchAd 서명·호출 구현 | **미착수 — Phase 2.** 자격증명 없음, provider-disabled 상태로 노출 | `test_openapi_contract.py::test_provider_endpoint_reports_disabled_providers_honestly` |

## 5. 작업·상태 모델 (마스터 §5)

| 요구사항 | 구현 | 검증 |
|---|---|---|
| 9개 작업 상태 | `JobStatus` | `packages/shared-types/src/enums.ts` 생성 + `test_openapi_contract.py::test_every_python_contract_enum_value_reaches_typescript` |
| idempotency·input_hash·재시도·취소·부분성공 | `jobs` 테이블 + `apps/worker/runtime` | `test_schema_invariants.py::test_jobs_support_idempotency_retry_and_partial_success` + worker 테스트 |
| 장시간 작업의 동기 실행 금지 | Celery 큐 분리 | worker 테스트 |

## 6. API·계약 (마스터 §11)

| 요구사항 | 구현 | 검증 |
|---|---|---|
| 공통 응답: request_id / data·error / safe message / error code / pagination / generated_at | `veo/contracts/envelope.py` | `test_openapi_contract.py` envelope 그룹 |
| OpenAPI를 단일 계약으로 | `apps/api/openapi.json` + `scripts/export_openapi.py --check` | `test_openapi_contract.py::test_committed_openapi_matches_the_running_application` |
| 생성된 TS client 갱신 없이 병합 금지 | `packages/api-client` + `pnpm check` drift 검사 | `test_openapi_contract.py::test_generated_typescript_client_exists_and_covers_every_path` |
| Public/Internal 전체 endpoint | **부분** — Phase 0은 health·providers·scoring만. 나머지는 Phase 2~4 | — |

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

### 8.1 SSRF: 연결 단계 IP 고정이 아직 없다 (최우선)

`url_guard`는 호스트를 resolve하고 모든 주소를 검증한 뒤 `decision.resolved_ip`를
돌려주지만, **HTTP 클라이언트가 그 IP로 접속하도록 강제할 수단이 이 모듈에는 없다.**
수집기가 검증만 하고 `httpx.get(url)`을 그대로 호출하면 DNS rebinding으로 위 검증이
전부 무력화된다.

Phase 2 crawler 구현 시 반드시 함께 만들어야 한다.

1. `decision.resolved_ip`로 직접 연결하고 `Host` 헤더와 SNI만 `decision.host`로 유지하는
   transport.
2. `follow_redirects=True` 금지. hop마다 `validate_redirect()`로 재검증.
3. 이 두 가지가 없으면 URL 검증은 장식일 뿐이다.

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

## 10. 0단계·1단계 범위 밖 (명시적 미착수)

Phase 0은 계약과 기반만 확정합니다. 다음은 의도적으로 구현하지 않았고,
자리표시자나 가짜 데이터로 채우지 않았습니다.

- SEO/GEO collector 실제 수집 로직 (Phase 2)
- 네이버 SearchAd/DataLab 실제 호출 (Phase 2, 자격증명 필요)
- 실제 AI 관측 실행 (Phase 4, 자격증명 필요)
- 경쟁사 비교, 이슈 워크플로, 보고서 렌더링 (Phase 3~4)
