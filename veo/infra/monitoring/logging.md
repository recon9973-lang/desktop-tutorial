# VEO 구조화 로깅 규격

VEO 는 `structlog` 로 **JSON 한 줄 = 이벤트 하나** 형식의 구조화 로그를 냅니다.
운영에서 `VEO_LOG_FORMAT=json` 은 협상 대상이 아닙니다. 로컬에서만
`console` 을 씁니다.

이 문서는 두 가지를 정합니다.

1. 모든 로그가 반드시 들고 다녀야 하는 **필드 집합**
2. 어떤 경우에도 평문으로 남으면 안 되는 **마스킹 대상 목록**

---

## 1. 왜 상관관계 ID 인가

VEO 의 한 번의 사용자 요청은 이렇게 흩어집니다.

```
브라우저 → API 요청 → 잡 큐 등록 → 워커가 집어감 → 크롤 → 렌더러 → 외부 제공자 호출 → 점수 계산 → 저장
```

"고객이 받은 점수가 왜 이렇게 나왔나"를 나중에 되짚으려면 이 조각들이 하나의
실로 꿰여 있어야 합니다. 꿰이지 않은 로그는 사고 났을 때 아무 도움이 되지
않습니다. 그래서 아래 ID 들은 **선택이 아니라 필수**입니다.

---

## 2. 필수 필드

### 2.1 모든 이벤트에 항상

| 필드 | 타입 | 설명 |
|---|---|---|
| `timestamp` | ISO 8601 (UTC, 밀리초) | `2026-07-28T02:41:07.482Z` |
| `level` | string | `debug` / `info` / `warning` / `error` / `critical` |
| `event` | string | 이벤트 이름. 사람이 읽는 문장이 아니라 **안정적인 키**. 예: `scan.page.fetched` |
| `service` | string | `veo-api` / `veo-worker` / `veo-renderer` |
| `environment` | string | `local` / `test` / `staging` / `production` |
| `version` | string | 배포된 애플리케이션 버전 |

`event` 는 검색 키입니다. 문장을 넣으면(`"페이지를 가져왔습니다"`) 집계가
불가능해집니다. 가변 정보는 별도 필드로 뺍니다.

### 2.2 상관관계 ID — 하나라도 알 수 있으면 반드시 넣는다

| 필드 | 언제 | 설명 |
|---|---|---|
| `correlation_id` | 항상 | 사용자 행동 하나를 끝까지 관통하는 ID. API 요청에서 만들어 잡·워커·렌더러·제공자 호출까지 그대로 전파한다. 경계를 넘을 때 새로 만들지 않는다. |
| `request_id` | HTTP 요청 문맥 | 개별 HTTP 요청 하나. 응답의 `meta.request_id` 및 `ApiError.internal_error_ref` 와 같은 값이어야 한다. 고객이 오류 화면의 참조번호를 들고 왔을 때 로그를 찾는 유일한 열쇠다. |
| `job_id` | 비동기 작업 문맥 | `JobDescriptor.job_id`. |
| `job_type` | 비동기 작업 문맥 | `SEO_SCAN`, `GEO_OBSERVATION_RUN` 등. |
| `project_id` | 프로젝트 문맥 | 분석 대상 프로젝트. |
| `organization_id` | 테넌트 문맥 | **테넌트 격리 사고를 사후에 증명·반증하는 근거.** 조직 데이터를 만지는 모든 이벤트에 필수. |
| `scan_run_id` | 스캔 실행 문맥 | 점수 재현의 기준점. |
| `user_id` | 인증된 요청 | 내부 식별자만. 이메일·이름은 넣지 않는다(§3 참고). |
| `surface` | 요청 출처 | `PUBLIC` / `CONSOLE`. 한도와 보존 정책이 다르다. |

**전파 규칙:** `correlation_id` 는 HTTP 헤더(`X-Correlation-ID`)와 Celery 태스크
헤더로 넘깁니다. 값이 들어오지 않으면 API 경계에서 새로 만들고, 그 이후로는
**절대 새로 만들지 않습니다.** 중간에서 새로 만드는 순간 실이 끊깁니다.

### 2.3 결과·품질 필드

| 필드 | 언제 | 설명 |
|---|---|---|
| `outcome` | 작업 종료 | `success` / `partial_success` / `failure` |
| `error_code` | 실패 시 | `ErrorCode` 열거값. 지역화된 메시지가 아니라 코드. |
| `duration_ms` | 시간 측정 | 정수 |
| `provider` | 외부 호출 | `DataSource` 열거값 |
| `provider_state` | 외부 호출 | `ProviderState` 열거값. `DISABLED_NO_CREDENTIAL` 도 정상 상태이며 반드시 기록한다. |
| `value_quality` | 수치 산출 | `ValueQuality` 열거값. 0 과 "데이터 없음"은 다른 사실이다. |
| `scoring_spec_id` / `scoring_spec_version` / `scoring_spec_checksum` | 점수 산출 | **점수 추적성의 핵심.** 이 셋이 없으면 "그때 그 점수"를 재현할 수 없다. |
| `http_status` / `http_method` / `route` | HTTP | `route` 는 경로 **템플릿**(`/projects/{id}`)을 쓴다. 실제 ID 가 박힌 경로를 쓰면 집계가 깨진다. |
| `retry_count` / `attempt` | 재시도 | 정수 |

### 2.4 예시

```json
{
  "timestamp": "2026-07-28T02:41:07.482Z",
  "level": "info",
  "event": "scoring.result.computed",
  "service": "veo-worker",
  "environment": "production",
  "version": "0.1.0",
  "correlation_id": "01JZK8QH4E9YB2R7T3N5M6PXWV",
  "job_id": "job_01JZK8QJ2A",
  "job_type": "SEO_SCAN",
  "organization_id": "org_01JZ9F",
  "project_id": "prj_01JZAB",
  "scan_run_id": "run_01JZK8QK",
  "scoring_spec_id": "veo.seo.readiness",
  "scoring_spec_version": "1.0.0",
  "scoring_spec_checksum": "sha256:9f2c…",
  "outcome": "partial_success",
  "duration_ms": 18422,
  "checks_total": 42,
  "checks_unknown": 7,
  "unknown_reason": "NAVER_SEARCH_AD=DISABLED_NO_CREDENTIAL"
}
```

`checks_unknown` 과 `unknown_reason` 을 함께 남기는 것이 중요합니다.
"몇 개를 모르는지"와 "왜 모르는지"가 로그에 없으면, 나중에 UNKNOWN 이
정상 동작이었는지 장애였는지 구분할 수 없습니다.

---

## 3. 마스킹 필수 목록 (절대 평문 금지)

아래 항목이 평문으로 로그에 남으면 **그 자체로 보안 사고**입니다.
로그는 수집기·백업·검색 인덱스로 복제되고 접근 범위가 애플리케이션보다
훨씬 넓기 때문에, 한 번 새면 회수가 사실상 불가능합니다.

### 3.1 자격증명·비밀값

- 모든 API 키·시크릿: `VEO_NAVER_SEARCHAD_*`, `VEO_NAVER_DATALAB_*`,
  `VEO_OPENAI_API_KEY`, `VEO_GOOGLE_*`, `VEO_BING_WEBMASTER_API_KEY`
- `VEO_JWT_SECRET`, 비밀번호, 비밀번호 해시, Argon2 파라미터
- S3/MinIO 액세스 키와 시크릿 (`VEO_S3_SECRET_ACCESS_KEY`, `MINIO_ROOT_PASSWORD`)
- 데이터베이스·Redis 접속 문자열 — **비밀번호가 URL 안에 들어 있습니다.**
  로깅할 때는 반드시 `postgresql+psycopg://veo:***@postgres:5432/veo` 처럼
  자격증명 부분을 지웁니다.
- 서비스 계정 JSON 전체

### 3.2 토큰·세션

- `Authorization` 헤더 전체 (Bearer 토큰, Basic 인증)
- 액세스 토큰·리프레시 토큰·API 토큰 (부분 문자열도 금지)
- `Cookie` / `Set-Cookie` 헤더 전체
- 세션 ID, CSRF 토큰
- 서명된 S3 URL — 쿼리스트링에 유효한 인증 정보가 들어 있습니다.
  경로만 남기고 쿼리는 통째로 지웁니다.
- OAuth 인가 코드, state, PKCE verifier

### 3.3 고객 개인정보 (PII)

- 이름, 이메일, 전화번호, 주소
- 사업자등록번호, 주민등록번호 등 모든 식별번호
- 결제 정보 일체
- 로그인 시도의 원본 아이디 문자열
- 크롤한 페이지 본문에서 발견된 개인정보 — **병원 홈페이지를 크롤하면
  환자 후기·상담 게시글이 딸려 들어옵니다.** 크롤 결과를 통째로 로그에
  찍는 코드는 작성 금지입니다.

내부 식별자(`user_id`, `organization_id`)는 남깁니다. 그게 PII 를 남기지 않고도
추적하기 위해 존재하는 값입니다.

### 3.4 AI 원본 응답

- GEO 관측에서 받은 **AI 엔진의 원본 답변 전문**
- 그 답변을 얻기 위해 보낸 프롬프트 전문

이유는 세 가지입니다.
(1) 답변에 제3자의 개인정보나 저작물이 그대로 섞여 들어올 수 있습니다.
(2) 응답이 길어서 로그 파이프라인을 망가뜨립니다.
(3) 원본은 로그가 아니라 **접근이 통제된 객체 스토리지**에 보관하고
    (`VEO_RAW_RESPONSE_RETENTION_DAYS`), 로그에는 해시와 저장 위치만 남기는
    것이 맞습니다.

로그에 남기는 것은 이 정도입니다.

```json
{
  "event": "geo.observation.answer.received",
  "provider": "AI_ENGINE_OBSERVATION",
  "raw_response_hash": "sha256:4b1d…",
  "raw_response_uri": "s3://veo-artifacts/obs/2026/07/28/run_01JZK8QK.json",
  "answer_chars": 2841,
  "brand_mentioned": true,
  "citation_count": 3
}
```

### 3.5 그 밖에

- 스택 트레이스에 섞인 지역 변수 값 (설정 객체·인증 헤더가 자주 딸려 옵니다)
- 요청 본문 전체 덤프
- 크롤 대상의 응답 본문 전체

---

## 4. 마스킹 구현 규칙

1. **차단 목록이 아니라 허용 목록으로 만듭니다.**
   "이건 지우자"를 나열하는 방식은 새 필드가 추가될 때마다 구멍이 생깁니다.
   로그에 실을 필드를 명시적으로 고르는 방식이어야 합니다.

2. **마스킹은 로깅 파이프라인 안에서 강제합니다.**
   호출하는 쪽의 예의에 맡기지 않습니다. `structlog` 프로세서 체인에 마스킹
   프로세서를 넣고, 그 프로세서를 우회하는 경로를 만들지 않습니다.
   `VEO_LOG_REDACTION_ENABLED=false` 는 로컬 디버깅 전용이며, 운영에서
   내리는 것은 사고로 취급합니다.

3. **비밀값은 타입으로 막습니다.**
   설정의 자격증명은 `pydantic.SecretStr` 로 선언돼 있습니다
   (`veo/core/settings.py`). `SecretStr` 은 `repr` 이 `**********` 이라
   실수로 찍어도 새지 않습니다. **`.get_secret_value()` 의 결과를 로그·예외
   메시지·오류 응답에 넣지 마세요.** 그게 유일한 유출 경로입니다.

4. **마스킹은 잘라내기가 아니라 지우기입니다.**
   토큰 앞 8자리만 남기는 방식은 안전하지 않습니다. 짧은 키에서는 대부분이
   드러나고, 여러 로그를 모으면 복원되기도 합니다. `"***"` 로 통째로 바꿉니다.

5. **고객에게 보이는 오류와 로그를 분리합니다.**
   `ApiError.message` 는 고객이 보는 안전한 문장이고, 민감한 내용은
   `internal_error_ref` 뒤에 둡니다. 이 참조값이 로그의 `request_id` 와
   같아야 지원 문의를 처리할 수 있습니다.

6. **마스킹에 대한 테스트를 씁니다.**
   "비밀값을 넣고 로그를 렌더링했을 때 그 값이 출력에 없는지" 확인하는
   테스트가 있어야 합니다. 마스킹은 조용히 깨지는 종류의 기능이라
   테스트 없이는 언제 뚫렸는지 알 수 없습니다.

---

## 5. 보존과 접근

- 운영 로그 보존 기간은 법적 요구와 조사 필요를 함께 보고 정합니다.
  잡 메타데이터는 `VEO_JOB_RETENTION_DAYS`(기본 90일), 제공자 원본 응답은
  `VEO_RAW_RESPONSE_RETENTION_DAYS`(기본 30일)를 따릅니다.
- 로그 접근 권한은 애플리케이션 접근 권한과 별도로 관리합니다.
  로그 조회 권한이 곧 전체 테넌트 데이터 열람 권한이 되지 않도록,
  `organization_id` 기준 필터를 지원 도구에 강제합니다.
- 로그에서 비밀값이 발견되면 지우는 것으로 끝내지 않습니다.
  **해당 자격증명을 폐기하고 재발급합니다.**
  절차: `docs/operations/runbook-credential-rotation.md`
