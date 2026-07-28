# 통합 요청 — Google · 네이버 서치어드바이저 제공자 작업자 → 통합 담당

이 작업자의 편집 범위는 다음 세 곳입니다.

- `apps/api/src/veo/providers/google/**`
- `apps/api/src/veo/providers/searchadvisor/**`
- `apps/api/tests/providers/**`

그 밖의 파일은 한 줄도 손대지 않았고, 필요한 변경은 전부 아래 요청으로 남깁니다.

상태 표기: `열림` / `처리중` / `완료` / `보류`

---

## 0. 가장 먼저 읽어야 할 사실 — 자격증명이 하나도 없습니다

VEO 에는 **PageSpeed API 키도, CrUX 키도, Search Console 서비스 계정도, IndexNow 키도
없습니다.** 이 작업 동안 받지도 못했습니다. 그래서 다음이 전부 사실입니다.

- 이 코드는 **실제 Google 응답을 한 번도 본 적이 없습니다.** 필드 이름과 값 규약은
  공개 문서를 따랐을 뿐입니다.
- `apps/api/tests/providers/google_fixtures.py` 는 전부 합성이며, RSA 키는 테스트
  프로세스에서 생성해 프로세스와 함께 사라집니다.
  `test_fixtures_are_synthetic.py` 가 호스트·키 형태·식별자를 검사해 실제 값이
  섞여 들어오면 실패합니다.
- 아래 **§A 에 "문서만 보고 추론했고 검증하지 못한 필드" 목록**이 있습니다. 실제 키가
  도착한 날 가장 먼저 대조해야 할 목록이 이것입니다.
- 자격증명이 없는 상태에서 모든 클라이언트는 **소켓을 열지 않습니다.** 상태 확인이
  요청을 만들기 전에 일어나며, `test_without_a_credential_no_connection_is_opened`
  가 전송 계층 호출 횟수 `0` 을 직접 셉니다.

### 지금 확인된 사실 하나

`.env` 에는 네이버 SearchAd·DataLab·OpenAI 키가 있고 **`VEO_GOOGLE_*` 은 없습니다.**
즉 이 모듈들은 배포되면 전부 `DISABLED_NO_CREDENTIAL` 로 동작합니다. 그것이 정상
동작입니다 — 커버리지가 내려가고, 이유가 한국어로 표시되고, 숫자는 하나도
만들어지지 않습니다.

---

## 요청 #1 — 공통 예외 기반 이전: 대부분 완료, 두 가지가 남음

**상태:** 처리중 (작업 도중 `providers/errors.py` 가 다른 작업자에 의해 들어왔습니다)
**대상 파일:** `apps/api/src/veo/providers/naver/errors.py`
**우선순위:** 낮음(주석 한 줄) + 중간(회로 차단 예외)

작업 중간에 `veo/providers/errors.py` 의 `ProviderError` 가 들어왔고,
`ProviderFailure.from_error` 도 이미 중립 기반으로 넓혀져 있었습니다. 그래서
`google/errors.py` 를 그쪽으로 옮겨 붙였습니다 — **Google 오류는 이제 타입상 네이버
오류가 아닙니다.** 남은 것은 둘입니다.

### 1-a. `ResilientCaller.call()` 의 지역 변수 주석 — **이미 해결됨**

작업 도중 `naver/errors.py:442` 의 `last: NaverProviderError` 가
`except ProviderError` 와 어긋나 mypy 오류가 하나 떠 있었습니다. `naver/**` 는 편집
금지 범위라 손대지 않고 기록만 해 두었는데, 15:55 시점에 해당 작업자가
`last: ProviderError` 로 고쳐 해소되었습니다. 지금은
`mypy src/veo/providers` 가 16개 파일 모두 통과합니다. 별도 조치가 필요 없습니다.

### 1-b. 회로 차단 예외 클래스를 주입 가능하게

`ResilientCaller.call()` 이 차단 분기에서 `except NaverCircuitOpenError` 를 **이름으로**
잡습니다. 그래서 `GoogleCircuitOpenError` 는 어쩔 수 없이 `NaverCircuitOpenError` 를
상속합니다 — 그러지 않으면 차단 예외가 `call()` 밖으로 새어 나가 "측정 불가"여야 할
자리에 500 이 뜹니다. `CircuitBreaker(circuit_open_error=...)` 처럼 클래스를 주입받게
해 주시면 `google/errors.py` 의 마지막 네이버 상속선이 사라집니다.

---

## 요청 #2 — `core/settings._is_placeholder` 를 공개 API 로

**상태:** 열림
**대상 파일:** `apps/api/src/veo/core/settings.py`
**우선순위:** 낮음

`google/credentials.py` 가 비공개 이름을 임포트하고 있습니다.

```python
from veo.core.settings import _is_placeholder
```

"자리표시자가 무엇인가"의 정의는 **한 곳에만 있어야** 합니다. 목록을 복사해 오면
드리프트가 생기고, 드리프트가 생긴 날 `[SENSITIVE]` 가 키로 취급됩니다. 그래서
비공개 이름을 그대로 쓰는 쪽을 택했습니다. `is_placeholder_credential()` 같은 공개
이름으로 노출해 주시면 임포트만 바꾸겠습니다.

---

## 요청 #3 — CrUX 전용 자격증명 슬롯 (선택)

**상태:** 열림
**대상 파일:** `apps/api/src/veo/core/settings.py`, `apps/api/src/veo/credentials/providers.py`
**우선순위:** 낮음

CrUX API 와 PageSpeed API 는 **같은 종류의 Google API 키**로 인증합니다. VEO 에는
슬롯이 하나뿐이라 `crux_from_settings()` 는 `pagespeed_from_settings()` 를 그대로
돌려주고, 그 사실을 함수 독스트링에 적어 두었습니다. 없는 슬롯을 지어내면 운영자가
"키가 두 개 필요하구나"라고 오해합니다. 실제로 해야 할 일은 **같은 Cloud 프로젝트에서
Chrome UX Report API 를 사용 설정**하는 것 하나입니다.

쿼터를 분리하고 싶다면 다음이 필요합니다.

- `ProviderCredentials.google_crux_api_key`
- `ProviderCredentials.states()` 에 `"GOOGLE_CRUX"`
- `CredentialProvider.GOOGLE_CRUX`

지금은 `contracts/enums.DataSource.GOOGLE_CRUX` 만 있고 `CredentialProvider` 에는
없어서, 금고(vault) 경로로는 CrUX 키를 따로 저장할 수 없습니다.

---

## 요청 #4 — `seo.perf.inp_field` 는 구간 라벨이 없는 CrUX 값을 읽지 못합니다

**상태:** 열림
**대상 파일:** `apps/api/src/veo/seo/collectors/performance_ux.py`
**우선순위:** 중간

사실 관계부터. CrUX 는 두 경로로 열려 있고 **주는 값이 다릅니다.**

| 경로 | 백분위수 | FAST/AVERAGE/SLOW 구간 |
| --- | --- | --- |
| PageSpeed 응답의 `loadingExperience` | 준다 | **준다** |
| 단독 CrUX 기록 API `records:queryRecord` | 준다 | **주지 않는다** |

수집기는 `metrics.<METRIC>.category` 를 읽습니다. 즉 **현재 구조에서 field 값을
평가할 수 있는 경로는 PageSpeed 뿐입니다.** 단독 CrUX 만 연동된 배포는 백분위수를
갖고 있어도 이 체크를 통과시킬 수 없습니다.

VEO 가 p75 를 자체 기준선에 대어 구간을 만들어 내는 선택지는 **택하지 않았습니다.**
그렇게 만든 단어는 고객에게 Google 의 판정처럼 읽히지만 실제로는 VEO 의 판단이고,
이 모듈의 독스트링이 명시적으로 금지하는 일이기도 합니다
(`crux.CATEGORY_ACCESS_KO` 에 한 번만 적어 두었습니다).

그래서 `crux.field_payload()` 는 **구간 라벨이 없는 측정값을 payload 에서 아예
제외합니다.** 빈 `metrics` 로 넣으면 수집기가 "표본이 없습니다"라고 말하는데, 표본이
있는 URL 에 대해 그 말은 거짓이기 때문입니다.

선택지는 둘입니다.

1. **현행 유지** — PageSpeed 연동을 field 데이터의 공식 경로로 삼는다. (권장)
2. 수집기가 `percentile` + Google 공표 임계값(INP: 200ms/500ms)으로 구간을 판정하고,
   그 값의 출처를 `CALCULATED` 로 명시한다. 이때 판정 주체가 VEO 라는 사실이
   증거·근거 문구에 드러나야 합니다.

---

## 요청 #5 — PageSpeed API 키가 쿼리스트링으로 나갑니다

**상태:** 열림
**대상 파일:** 로깅·프록시 설정 (담당 미정)
**우선순위:** 중간

PageSpeed Insights 는 API 키를 `?key=` 로 받습니다. 이것이 문서화된 형식이라 그대로
따랐습니다. 대가는 명확합니다 — **키가 액세스 로그·프록시 기록·오류 리포트의 URL 에
남습니다.**

- VEO 코드 안에서는 새어 나가지 않습니다. `repr()` 에도, `ProviderFailure.reason_ko`
  에도 없고, 테스트가 그것을 검사합니다.
- 통제할 수 없는 것은 **바깥**입니다. 아웃바운드 요청 URL 을 남기는 로깅이 있다면
  `key` 파라미터를 마스킹해 주십시오.
- `X-goog-api-key` 헤더로 보내는 방법이 있으나 PSI 엔드포인트에서의 동작을 확인하지
  못했습니다. 실제 키가 도착하면 이것부터 시험해 볼 가치가 있습니다 (§A-1 참조).

---

## 요청 #6 — `index_coverage.previous_indexed` 는 VEO 의 이력에서 와야 합니다

**상태:** 열림
**대상 파일:** `apps/api/src/veo/collect/**` 또는 스캔 오케스트레이션 담당 모듈
**우선순위:** 높음 (이것이 없으면 해당 체크가 영구히 UNKNOWN 입니다)

두 가지를 분명히 해야 합니다.

1. **Search Console 에는 색인 커버리지 집계 API 가 없습니다.** 웹 화면의 "페이지"
   보고서에 해당하는 엔드포인트는 공개되어 있지 않습니다. 그래서
   `SearchConsoleClient.index_coverage()` 는 **URL 검사 API 를 URL 하나씩 호출해
   VEO 가 직접 센 값**이며, `DataSource.CALCULATED` 로 표시되고 `inspected` /
   `requested` 를 함께 들고 다닙니다. 절대 "Google 이 N 페이지가 색인되었다고
   말했다"로 표현하면 안 됩니다.
2. `previous_indexed` 는 **직전 스캔의 값**입니다. 이 모듈은 그것을 알 수 없고,
   지어내지도 않으며, `None` 으로 둡니다. 수집기는 `previous_indexed` 가 없으면
   "직전 색인 수치가 없어 비교하지 못했습니다"라고 정직하게 UNKNOWN 을 냅니다.

필요한 것: 스캔 오케스트레이터가 직전 스캔의 `indexed` 를 읽어
`dataclasses.replace(coverage, previous_indexed=...)` 로 채운 뒤
`search_console_payload()` 에 넘기는 것. 계약 테스트가 그 형태를 그대로 보여 줍니다
(`test_collector_payload_contract.py::measured_payloads`).

**쿼터 주의.** URL 검사 API 는 속성당 하루 2,000 건입니다. 기본 상한을
`MAX_URLS_PER_COVERAGE_RUN = 50` 으로 두었습니다. 사이트 수 × 스캔 주기로 예산을
잡아 주십시오.

---

## 요청 #7 — `ProviderState` 에 `NOT_AVAILABLE` 이 없습니다

**상태:** 열림
**대상 파일:** `apps/api/src/veo/contracts/enums.py`, `apps/api/src/veo/seo/collectors/base.py`
**우선순위:** 중간

네이버 서치어드바이저는 사이트 등록·소유확인·수집 통계·사이트맵 처리 상태에 대한
**공개 API 를 제공하지 않습니다.** 자격증명을 등록해도 달라지지 않습니다. 이것은
`DISABLED_NO_CREDENTIAL` 과 성격이 다릅니다 — 전자는 키를 넣으면 해결되고, 후자는
누구도 해결할 수 없습니다.

현재 어댑터는 `searchadvisor.client.CapabilityState.NOT_AVAILABLE` 이라는 **자체
열거형**으로 이 사실을 표현하고, `search_advisor_payload()` 는 항상 `None` 을
돌려줍니다. 수집기는 payload 가 없으면 UNKNOWN 을 내므로 결과는 정직합니다. 다만
사용자에게 보이는 문구가 이렇게 됩니다.

> 네이버 서치어드바이저 연동이 구성되어 있지 않아 측정하지 못했습니다.

진짜 이유는 "구성하지 않아서"가 아니라 **"조회할 API 가 없어서"** 입니다. 요청:

1. `ProviderState.NOT_AVAILABLE` 추가 (+ `packages/shared-types` 미러, 계약 테스트).
2. `seo/collectors/base.py::provider_payload()` 가 제공자별 사유 문구를 컨텍스트에서
   읽을 수 있는 통로. 문구는 이미 준비되어 있습니다 —
   `searchadvisor.client.SEARCH_ADVISOR_UNAVAILABLE_KO`, 그리고 담당자가 대신 할 수
   있는 일을 적은 `CapabilityGap.manual_alternative_ko`.

---

## 요청 #8 — 이 어댑터들을 호출하는 곳이 아직 없습니다

**상태:** 열림
**대상 파일:** `apps/api/src/veo/collect/**`, 워커 태스크
**우선순위:** 높음

어댑터는 완성되었고 테스트도 있지만, **스캔 파이프라인이 이들을 부르지 않습니다.**
`CollectionContext.provider_payloads` 를 채우는 코드가 제 편집 범위 밖입니다.
연결해야 할 지점은 정확히 네 개이며, 계약 테스트가 실행 가능한 예제입니다.

| 제공자 키 | 만드는 함수 |
| --- | --- |
| `GOOGLE_PAGESPEED` | `pagespeed.lab_payload(measurement, ...)` |
| `GOOGLE_CRUX` | `crux.field_payload(measurement, ...)` |
| `GOOGLE_SEARCH_CONSOLE` | `search_console.search_console_payload(...)` |
| `INDEXNOW` | `searchadvisor.client.indexnow_payload(key=...)` |
| `NAVER_SEARCH_ADVISOR` | **없음 (요청 #7)** |

`provider_states` 는 `ProviderCredentials.states()` 또는 금고 해석 결과
(`CredentialResolution.state`) 를 그대로 쓰면 됩니다.

---

## 요청 #9 — IndexNow 키가 저장될 곳이 없습니다

**상태:** 열림
**대상 파일:** `apps/api/src/veo/db/models/**`, `apps/api/src/veo/credentials/providers.py`
**우선순위:** 중간

IndexNow 키는 **배포 단위 자격증명이 아니라 사이트별 데이터**입니다(사이트 루트에
공개되어 있어야 검색엔진이 검증합니다). `CredentialProvider` 에도 없고 사이트 모델에도
칸이 없습니다. 그래서 `SearchAdvisorClient.submit_indexnow()` 는 키를 **호출자에게서
인자로** 받습니다.

필요한 것: `sites` 에 `indexnow_key` / `indexnow_key_location` 두 칸, 혹은 사이트별
설정 테이블. 키가 없으면 `indexnow_payload()` 는 `None` 을 돌려주고 체크는 UNKNOWN 이
됩니다 — **"미구성"으로 단정하지 않습니다.** 아무도 VEO 에게 키를 알려주지 않았다는
사실은 그 사이트에 IndexNow 가 없다는 뜻이 아니기 때문입니다.

---

## 요청 #10 — Search Console 온보딩 문구

**상태:** 열림
**대상 파일:** 콘솔 UI / 온보딩 문서 (담당 미정)
**우선순위:** 낮음

서비스 계정 JSON 을 등록하는 것만으로는 부족합니다. **그 서비스 계정의 이메일을
Search Console 속성의 사용자로 추가**해야 합니다. 추가하지 않으면 403 이 오는데,
그 403 은 "권한 없음"이라 스코프 누락과 구분되지 않습니다. 등록 화면에 다음 문구가
필요합니다.

> 등록한 서비스 계정 이메일(`...@....iam.gserviceaccount.com`)을 Search Console
> 속성의 사용자로 추가해야 조회가 됩니다. 권한은 '제한됨'으로 충분합니다.

VEO 가 요청하는 스코프는 읽기 전용(`webmasters.readonly`) 하나뿐이며, 고객 속성에
쓰기를 하지 않습니다.

---

# §A. 문서만 보고 추론했고, 아직 검증하지 못한 필드

**실제 자격증명이 도착한 날 이 표부터 대조하십시오.** "검증"의 의미는 이 저장소에서
오프라인으로 확인 가능한 성질을 뜻하고, "추론"은 공개 문서만 보고 정한 것을 뜻합니다.

## A-1. PageSpeed Insights (`/pagespeedonline/v5/runPagespeed`)

| 항목 | 상태 | 비고 |
| --- | --- | --- |
| `lighthouseResult.audits.<id>.score` 가 0.0–1.0 실수 | 추론 | Lighthouse 규약. VEO 는 그대로 저장하고 판정에 쓰지 않음 |
| `score: null` = 측정 못 함(`notApplicable`/`error`) | 추론 | `MISSING` 으로 매핑. **0 이 아님** — Lighthouse 에서 0 은 "최악"을 뜻함 |
| `displayValue` 가 로케일 문자열 | 추론 | `locale=ko` 를 보내고 있음. 값 형식은 표시용으로만 사용 |
| `numericValue` / `numericUnit` 존재 | 추론 | 4개 감사 항목 모두에 있다고 가정 |
| `categories.performance.score` | 추론 | 보관만 하고 점수화하지 않음 |
| `strategy` 파라미터가 `MOBILE`/`DESKTOP` 대문자 | 추론 | 문서는 소문자 예시도 보여 줌. 400 이 나면 여기부터 |
| `category=PERFORMANCE` 파라미터 | 추론 | 응답 크기를 줄이려는 목적. 거부되면 파라미터를 빼면 됨 |
| API 키를 `key=` 쿼리로 전달 | 추론 | 요청 #5. `X-goog-api-key` 헤더 대안 미검증 |
| `loadingExperience` 부재 = field 표본 없음 | 추론 | **`NOT_APPLICABLE`** 로 처리. 이 가정이 틀리면 표본 있는 URL 이 없는 것으로 보고됨 |
| `loadingExperience.overall_category` (snake_case) | 추론 | 같은 응답 안에서 카멜케이스와 섞여 있는 문서화된 기벽 |
| `loadingExperience.metrics.<M>.category` ∈ FAST/AVERAGE/SLOW | 추론 | 다른 값이 오면 `category=None`, `MISSING` 으로 떨어짐(지어내지 않음) |
| `INTERACTION_TO_NEXT_PAINT` 라는 지표 이름 | 추론 | 수집기가 이미 이 철자를 쓰고 있어 맞춤 |
| `percentile` 단위(INP·LCP=ms) | 추론 | **점수화에 쓰지 않으므로 단위 오류가 전파되지 않음** |

## A-2. CrUX 기록 API (`/v1/records:queryRecord`)

| 항목 | 상태 | 비고 |
| --- | --- | --- |
| 404 = 표본 부족 | 추론 | **`NOT_APPLICABLE`, 오류 아님.** 실패로 매핑하면 트래픽 적은 페이지마다 회로 차단이 열림 |
| 응답에 구간 라벨이 **없다** | 추론 | 요청 #4 의 근거. 훗날 Google 이 추가하면 `normalize_query_record` 한 곳만 고치면 됨 |
| `record.metrics.<name>.percentiles.p75` | 추론 | 숫자 |
| `histogram[].start/end/density`, 마지막 구간에 `end` 없음 | 추론 | 그대로 보존만 함 |
| snake_case 지표 이름 → PageSpeed 철자 매핑표 | **VEO 의 결정** | `crux._RECORD_METRIC_NAMES`. `largest_contentful_paint` 와 `LARGEST_CONTENTFUL_PAINT_MS` 가 같은 지표라고 가정 |
| `origin` 조회 시 본문 키가 `origin` | 추론 | URL 조회는 `url` |

## A-3. Search Console

| 항목 | 상태 | 비고 |
| --- | --- | --- |
| **`ctr` 가 0–1 비율** | **문서 확인 + 산술 검증(오프라인)** | `CTR_UNIT = "RATIO_0_TO_1"`. 테스트가 행마다 `ctr == clicks / impressions` 를 검사. **네이버는 퍼센트라 정반대** |
| 집계 차원(예: `query`)에서도 같은 항등식이 성립 | **추론** | 반올림으로 근사만 성립할 수 있음. 실제 응답으로 확인 필요 |
| `position` 이 1부터 시작하고 클수록 나쁨 | 추론 | `POSITION_UNIT = "AVERAGE_RANK_1_IS_BEST"` |
| 기간 평균 position 을 노출수 가중으로 계산 | **VEO 의 산술** | `DataSource.CALCULATED`. Google 자체 집계값과 소수점에서 다를 수 있음 |
| `permissionLevel == "siteUnverifiedUser"` = 미확인 | 추론 | 그 외 값은 전부 확인됨으로 간주 |
| `sitemap[].errors` / `warnings` 가 문자열 숫자 | 추론 | protobuf int64 규약. 읽지 못하면 **`None`, 0 아님** |
| `keys[0]` 이 `dimensions=["date"]` 일 때 ISO 날짜 | 추론 | 다른 차원에서는 `row_date=None` |
| URL 검사 `verdict == "PASS"` = 색인됨 | **추론(중요)** | `NEUTRAL`/`PARTIAL`/`FAIL` 은 전부 색인 안 됨으로 셈. 이 판정이 커버리지 숫자를 좌우함 |
| `coverageState` 자유 문자열 | 추론 | 보관만 하고 파싱하지 않음 |
| URL 검사 쿼터 2,000/일/속성 | 추론 | `MAX_URLS_PER_COVERAGE_RUN = 50` |
| JWT bearer 그랜트 + `webmasters.readonly` 스코프 | 추론 | `assertion` 서명은 PyJWT RS256. `google-api-python-client` 미사용(의존성 추가 금지) |
| `expires_in` 초 단위 | 추론 | 만료 60초 전에 갱신 |
| `authorized_user` JSON 도 지원 | 추론 | `refresh_token` 그랜트. 실제 사용 여부 미확인 |

## A-4. 네이버 서치어드바이저 / IndexNow

| 항목 | 상태 | 비고 |
| --- | --- | --- |
| 등록·소유확인·수집통계·사이트맵 상태 **공개 API 없음** | **조사 결과** | 요청 #7. 있다고 알려지면 이 항목이 가장 먼저 바뀌어야 함 |
| IndexNow 엔드포인트 `https://searchadvisor.naver.com/indexnow` | 추론 | 네이버 IndexNow 안내 기준. **호출해 본 적 없음** |
| 본문 키 `host` / `key` / `keyLocation` / `urlList` | 추론 | IndexNow 명세 |
| 200·202 = 접수 | 추론 | 202 는 키 검증 대기. 성공으로 단정하지 않고 상태 코드를 보존 |
| 400 / 403 / 422 / 429 매핑 | 추론 | IndexNow 명세의 표. **네이버가 실제로 쓰는 코드는 미확인** |
| 요청당 URL 10,000개 상한 | 추론 | IndexNow 명세 |
| 키 파일이 `keyLocation` 에서 읽혀야 함 | 추론 | VEO 는 키 파일 도달 여부를 **검사하지 않습니다**(고객 사이트를 가져오는 일이라 크롤러 소유 영역) |

---

# §B. 수집기가 기대하는 payload 모양 (참고용, 이미 맞춰 놓았습니다)

이 형태는 문서로 옮겨 적은 것이 아니라 **실행으로 검증**됩니다.
`apps/api/tests/providers/test_collector_payload_contract.py` 가 실제
`CollectionContext` 를 만들어 진짜 수집기 세 개를 돌립니다. 어느 쪽에서든 키 이름이
바뀌면 PASS 여야 할 체크가 UNKNOWN 이 되고 그 테스트가 깨집니다.

```python
"GOOGLE_PAGESPEED": {url: {"lighthouse": {audit_id: {"score": float, ...}}}}
"GOOGLE_CRUX":      {url: {"metrics": {"INTERACTION_TO_NEXT_PAINT": {"category": "FAST"}}}}
"GOOGLE_SEARCH_CONSOLE": {"site": {...}, "sitemaps": [...], "performance": {...},
                          "index_coverage": {...}}
"INDEXNOW":         {"configured": bool, "key_location": str}
```
