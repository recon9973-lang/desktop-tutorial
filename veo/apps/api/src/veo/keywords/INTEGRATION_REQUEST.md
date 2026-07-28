# 통합 요청 — 네이버 키워드 작업자 → 통합 담당

이 작업자의 편집 범위는 다음 네 곳입니다.

- `apps/api/src/veo/providers/naver/**`
- `apps/api/src/veo/keywords/**`
- `apps/api/tests/keywords/**`
- `tests/fixtures/naver/**`

그 밖의 파일은 손대지 않았고, 필요한 변경은 전부 아래 요청으로 남깁니다.

상태 표기: `열림` / `처리중` / `완료` / `보류`

---

## 0. 가장 먼저 읽어야 할 사실 — 자격증명이 하나도 없습니다

VEO 에는 **네이버 SearchAd 키도, DataLab 키도 없습니다.** 이 작업 동안 받지도
못했습니다. 그래서 다음이 모두 사실입니다.

- 이 코드는 **실제 네이버 응답을 한 번도 본 적이 없습니다.**
- `tests/fixtures/naver/**` 는 전부 합성이며, 그렇게 라벨링되어 있고,
  라벨이 없으면 로더가 거부합니다.
- 아래 §A 에 **추론했지만 검증하지 못한 필드 목록**이 있습니다. 실제 키가 도착하면
  가장 먼저 대조해야 할 목록입니다.
- 자격증명이 없는 상태에서 `POST /keywords/lookups` 는 200 을 돌려주며,
  제공자 상태는 `DISABLED_NO_CREDENTIAL`, 응답의 `data.keywords` 안에는
  **숫자가 하나도 없습니다.** (`test_a_lookup_without_a_credential_returns_no_numbers_at_all`
  이 직렬화된 payload 를 순회하며 이를 검사합니다.)

---

## 요청 #1 — `veo.api.app` 에 keywords 라우터 마운트

**상태:** 열림
**대상 파일:** `apps/api/src/veo/api/app.py` (이 작업자의 편집 범위 밖)
**우선순위:** 중간

`veo/keywords/router.py` 의 `router` 는 **의도적으로 마운트하지 않았습니다.**
`veo.api.app` 은 통합 담당 소유이고, 테스트는 `create_app()` 에 라우터를 붙여
실제 오류 핸들러를 통과시키는 방식으로 검증합니다.

```python
from veo.keywords.router import router as keywords_router
...
app.include_router(keywords_router, prefix=settings.api_prefix)
```

마운트하면 `openapi.json` 이 바뀌므로 계약 테스트 재생성이 함께 필요합니다.

추가되는 경로:

| 메서드 | 경로 | 권한 |
| --- | --- | --- |
| POST | `/keywords/lookups` | `KEYWORD_RUN` |
| GET | `/keywords/lookups/{query_id}` | `KEYWORD_READ` |
| GET | `/keywords/lookups/{query_id}/related` | `KEYWORD_READ` |
| GET | `/keywords/lookups/{query_id}/export` | `KEYWORD_READ` + `REPORT_EXPORT` |
| GET | `/keywords/recent` | `KEYWORD_READ` |
| POST · GET · PUT · DELETE | `/keywords/lists[...]` | `KEYWORD_RUN` / `KEYWORD_READ` |

---

## 요청 #2 — `keyword_metrics` 에 품질 컬럼 3종 추가

**상태:** 열림
**대상 파일:** `apps/api/src/veo/db/models/keywords.py`, `alembic/**`
**우선순위:** 중간 (지금은 우회하고 있으나 우회가 깔끔하지 않음)

`keyword_metrics` 는 **검색량 컬럼에만** `*_quality` 를 짝지어 두었습니다.
다음 항목에는 전용 품질 컬럼이 없습니다.

- `monthly_total_searches` — VEO 계산값. `RANGE`(양쪽 모두 `< 10`),
  `SUPPRESSED_BY_PROVIDER`, `MISSING`, `EXACT` 네 가지가 실제로 발생합니다.
- `avg_pc_clicks`, `avg_mobile_clicks`, `avg_pc_ctr`, `avg_mobile_ctr`
  — 값이 `NULL` 일 때 '응답에 키가 없었음'과 '제공자가 `null` 을 보냄'을
  구분할 방법이 없습니다.

**현재 우회:** `provider_raw` JSONB 안에 `_veo_derived` 라는 **네임스페이스된**
블록을 만들어 품질과 구간 상한을 함께 저장하고, 읽을 때 다시 꺼냅니다
(`repository.py` 의 `_derived_block` / `_metric_from_row`). 네이버 응답 키와
충돌할 수 없는 이름이고, 최상위의 제공자 원본 키는 건드리지 않습니다.

이 우회가 나쁜 이유는 하나뿐입니다 — **JSONB 안의 값은 SQL 로 인덱싱·집계하기
어렵습니다.** "억제된 키워드만 뽑아 줘" 같은 질의가 나오는 순간 문제가 됩니다.

**요청:**

```python
monthly_total_searches_quality: Mapped[str] = mapped_column(
    String(32), nullable=False, default="MISSING"
)
avg_pc_clicks_quality: Mapped[str] = ...
avg_mobile_clicks_quality: Mapped[str] = ...
avg_pc_ctr_quality: Mapped[str] = ...
avg_mobile_ctr_quality: Mapped[str] = ...
```

구간 상한(`< 10` 의 `10`)을 담을 자리도 함께 있으면 더 좋습니다
(`monthly_pc_upper_bound_exclusive` 등, 또는 `value_bounds` JSONB 한 개).

반영되면 `_veo_derived` 블록을 지우고 컬럼을 직접 쓰겠습니다.

---

## 요청 #3 — `keyword_queries` 에 `requested_keywords` 추가

**상태:** 열림
**대상 파일:** `apps/api/src/veo/db/models/keywords.py`, `alembic/**`
**우선순위:** 낮음

`keyword_queries` 는 `original_keyword` / `normalized_keyword` 를 **단수**로
가집니다. 그런데 `keyword_metrics` 의 `UniqueConstraint(keyword_query_id,
normalized_keyword)` 는 한 조회에 여러 키워드가 붙는 것을 전제합니다.

**현재 동작:** 여러 키워드를 한 번에 조회하면 `keyword_queries` 에 한 행을 쓰고
그 행의 단수 컬럼에는 **첫 번째 키워드**를 기록합니다. 나머지 키워드도 각각
`keyword_metrics` 행을 갖습니다. 조회 기록을 다시 읽으면 요청한 키워드 전체가
아니라 metrics 가 남은 키워드만 복원됩니다.

**요청:** `requested_keywords: Mapped[JsonArray] = json_column()` 를 추가해
"무엇을 물었는가"와 "무엇을 답받았는가"를 구분할 수 있게 해 주세요. 자격증명이
없어 metrics 가 하나도 없는 조회에서 특히 중요합니다 — 지금은 그 조회가 무엇을
물었는지 첫 키워드밖에 남지 않습니다.

---

## 요청 #4 — XLSX 라이브러리 의존성 (권고: 추가하지 않아도 됨)

**상태:** 열림
**대상 파일:** `apps/api/pyproject.toml`
**우선순위:** 낮음

`openpyxl` 과 `xlsxwriter` 모두 설치되어 있지 않습니다(확인함).
새 의존성은 요청 사항이므로 추가하지 않았습니다.

**현재 구현:** `keywords/export.py` 가 표준 라이브러리(`zipfile`, `xml.sax.saxutils`)
만으로 최소 OOXML 워크북을 만듭니다. 시트 1개, inline string, 서식 없음.
`test_xlsx_export_is_a_real_workbook` 이 zip 구성과 시트 XML 내용을 검사합니다.

**한계:** Microsoft Excel / LibreOffice / 넘버스에서 **실제로 열어 본 적이
없습니다.** 자동 검증은 zip 구조와 XML 파싱까지입니다. 서식·열 너비·숫자형 셀이
필요해지면 그때 `openpyxl>=3.1` 추가를 요청하겠습니다. 지금 필요는 없다고 봅니다.

---

## 요청 #5 — 자격증명 출처를 vault 로 전환할지 결정

**상태:** 열림
**대상 파일:** 결정 사항 (구현은 이 작업자 범위)
**우선순위:** 중간

`providers/naver/credentials.py` 에 **두 가지 resolver 를 모두** 구현해 두었습니다.

- `searchad_from_settings()` / `datalab_from_settings()` — 배포 전역 환경변수
- `searchad_from_vault()` / `datalab_from_vault()` — 조직별 저장 자격증명
  (`vault.resolve_for_use` 사용, `vault.py` 는 읽기만 하고 수정하지 않았습니다)

`router.get_keyword_service` 는 **현재 settings 방식만** 씁니다. vault 방식으로
바꾸면 `credential_encryption_key` 가 없을 때 키워드 엔드포인트가 기동 시점부터
막히는 등 부팅 조건이 바뀌므로, 통합 담당의 결정이 필요합니다.

멀티테넌트 제품의 정답은 vault 쪽이라고 보지만, 그 전환은 `veo.api.app` 의
시작 검사와 맞물리므로 여기서 단독으로 정하지 않았습니다.

---

## 요청 #6 — `providers/__init__.py` 를 새로 만들었습니다

**상태:** 알림 (승인 요청)
**대상 파일:** `apps/api/src/veo/providers/__init__.py`

이 작업자의 범위는 `providers/naver/**` 입니다. 그런데 `veo.providers.naver` 를
import 가능하게 하려면 부모 패키지의 `__init__.py` 가 필요했습니다
(레포의 다른 모든 패키지가 명시적 `__init__.py` 를 쓰고, mypy `packages = ["veo"]`
설정도 그쪽을 전제합니다).

만든 파일에는 **로직이 없고 docstring 만** 있습니다. `providers/` 하위의 다른
제공자 소유권은 그대로 열려 있습니다. 위치가 마음에 들지 않으면 알려 주세요.

---

## 요청 #7 — `Permission.KEYWORD_*` 는 그대로 충분합니다 (변경 요청 아님)

`KEYWORD_READ` / `KEYWORD_RUN` 으로 필요한 구분이 전부 표현됩니다. export 는
`REPORT_EXPORT` 를 추가로 요구하도록 했습니다 — 내보내기는 데이터가 제품 밖으로
나가는 행위라 조회와 같은 권한으로 묶지 않는 편이 맞다고 판단했습니다.
이 판단이 매트릭스 의도와 다르면 알려 주세요.

---

## 요청 #8 — `apps/api` 테스트에 `--import-mode=importlib` 필요 (팀 전체 영향)

**상태:** 열림
**대상 파일:** `apps/api/pyproject.toml` (`[tool.pytest.ini_options].addopts`)
**우선순위:** 높음 (지금 `pytest apps/api/tests` 가 **수집 단계에서 중단됩니다**)

`apps/api/tests` 하위에 `__init__.py` 가 없고 `apps/api/pyproject.toml` 이
기본 import 모드(`prepend`)를 쓰기 때문에, 서로 다른 폴더의 **같은 파일 이름**이
충돌합니다. 실제로 지금 이렇게 깨집니다.

```
ERROR collecting tests/seo/test_router.py
import file mismatch:
imported module 'test_router' has this __file__ attribute:
  .../tests/credentials/test_router.py
```

레포 루트의 `pytest.ini` 는 이 문제를 알고 주석으로 설명까지 적어 두었지만
(`importlib import mode keeps them apart`), `addopts` 에는 `--strict-markers` 만
있고 `--import-mode=importlib` 가 빠져 있습니다. `apps/api/pyproject.toml` 에도
없습니다.

**요청:**

```toml
[tool.pytest.ini_options]
addopts = "-q --strict-markers --import-mode=importlib"
```

레포 루트 `pytest.ini` 의 `addopts` 에도 같은 옵션을 넣어 주세요.

**이 작업자의 임시 대응:** 키워드 테스트 모듈 이름을 전부 고유하게 바꿨습니다
(`test_keyword_router.py`, `test_keyword_service.py`, … / 로더는
`naver_fixtures.py`). 그래서 `apps/api/tests/keywords` 는 충돌 없이 수집됩니다.
다만 이건 이름 규칙으로 회피한 것이고, `tests/seo/test_router.py` 와
`tests/geo/test_router.py` 는 여전히 `tests/credentials/test_router.py` 와
충돌합니다. 그 두 폴더는 이 작업자의 편집 범위가 아니라 손대지 않았습니다.

---

# 부록 A — 추론했고 실제 응답으로 확인하지 못한 필드

**실제 키가 도착하면 이 표부터 대조하십시오.** 여기 있는 모든 항목은 공식 문서에
기술된 모양을 따랐을 뿐, 살아 있는 응답과 맞춰 본 적이 없습니다.

## A-1. SearchAd `GET /keywordstool`

| 항목 | VEO 의 가정 | 확인 못 한 것 | 틀렸을 때 증상 |
| --- | --- | --- | --- |
| `relKeyword` | 키워드 문자열 | 대소문자·공백 정규화 형태. 네이버가 대문자로 정규화해 돌려준다는 이야기가 있으나 확인 못 함 | 시드 키워드 매칭 실패 → metrics 가 통째로 연관 키워드로 분류됨 |
| `monthlyPcQcCnt` / `monthlyMobileQcCnt` | 월간 검색 수. `int` 또는 문자열 | 문자열로 오는 경우가 상시인지 저볼륨일 때만인지 | 없음(둘 다 처리함) |
| `"< 10"` | 저볼륨 억제 마커, 상한 10 미만 | **공백 유무, 부등호 형태, 임계값 10 이 맞는지** | 마커를 못 알아보면 `MISSING` 으로 떨어짐(0 은 되지 않음) |
| `monthlyAvePcClkCnt` / `monthlyAveMobileClkCnt` | 평균 클릭 수(float) | 단위와 기간 정의 | 값 자체가 어긋남 |
| `monthlyAvePcCtr` / `monthlyAveMobileCtr` | CTR | **퍼센트(1.11 = 1.11%)인지 비율(1.11 = 111%)인지** — 확인 못 함 | 리포트의 CTR 이 100배 어긋남 |
| `plAvgDepth` | 노출 광고 수(광고 depth) | 평균인지 최대인지, 기간 | 광고 경쟁 해석이 어긋남 |
| `compIdx` | 경쟁 정도 **라벨** | 값 집합이 `낮음/중간/높음` 뿐인지, 로케일에 따라 영문으로 오는지 | 모르는 라벨은 `competition_inverse` 를 **결측 처리**합니다(추측하지 않음) |
| 경쟁 지수(숫자) | **존재하지 않는다고 가정** | 0-100 숫자 지수를 주는 필드가 실제로 있는지 | 있다면 `competition_index` 컬럼이 계속 비어 있게 됨 |
| 페이지네이션 | 없다고 가정 | 연관 키워드 개수 상한, 페이징 파라미터 | 연관 키워드가 잘려도 알 수 없음 |
| `hintKeywords` 상한 | 5개 | 실제 상한 | 초과 시 400 |
| 계정 단위 호출 한도 | 문서화된 값 없음 | 429 발생 임계 | backoff 는 동작하나 한도 자체를 모름 |

## A-2. 서명

| 항목 | VEO 의 가정 | 확인 못 한 것 |
| --- | --- | --- |
| 서명 대상 문자열 | `"{timestamp}.{METHOD}.{path}"` | 살아 있는 서버가 실제로 이 문자열을 서명하는지 |
| `timestamp` | epoch **밀리초** | 초 단위일 가능성 |
| 허용 시계 오차 | 알 수 없음 | 서버가 몇 초까지 허용하는지 |
| `path` | 쿼리스트링 **제외** | 포함해야 하는지 (제외로 구현했고, 쿼리가 섞이면 예외를 던집니다) |
| `X-Customer` | 고객 ID 문자열 | 숫자형인지 |

서명 알고리즘 자체는 손으로 계산한 HMAC 벡터로 고정되어 있어
(`test_signature.py`) 구현이 규칙과 어긋나는 일은 없습니다. **규칙이 맞는지**를
확인하지 못했을 뿐입니다.

## A-3. DataLab `POST /v1/datalab/search`

| 항목 | VEO 의 가정 | 확인 못 한 것 |
| --- | --- | --- |
| `ratio` | 0-100 상대 지수 | 상한이 정확히 100 인지 (초과 시 스키마 오류로 처리) |
| `period` | ISO 날짜 | `timeUnit` 별 표기 차이 |
| `device` | `""` / `pc` / `mo` | 값 표기 |
| `keywordGroups` | 최대 5개 | 실제 상한 |
| `ages` · `gender` | 사용하지 않음 | 필요해지면 추가 |
| 오류 본문 | 파싱하지 않음 | 제공자 오류 코드 체계 (본문은 고객에게 절대 전달하지 않습니다) |

---

# 부록 B — 실제 키가 도착하면 깨질 수 있는 것

정직하게 적습니다. 다음은 **테스트가 통과한다고 해서 안전이 보장되지 않는**
부분입니다.

1. **서명이 거절될 수 있습니다.** 타임스탬프 단위나 서명 문자열이 다르면 전량
   401 입니다. 다행히 401 은 `NaverUnauthorizedError` → `UNKNOWN` 으로
   떨어지므로 **가짜 숫자가 나가지는 않습니다.** 화면에는 "자격증명 거부"가
   뜹니다.
2. **CTR 단위(%/비율)를 확인하지 못했습니다.** 여기가 가장 조용히 틀릴 수 있는
   지점입니다. 값이 그대로 통과하기 때문에 테스트가 잡아 주지 못합니다.
   실제 응답을 받는 즉시 사람이 눈으로 대조해야 합니다.
3. **`"< 10"` 마커 형태.** 다르면 억제값이 `MISSING` 이 됩니다. 0 이 되지는
   않으므로 최악은 아니지만, `BELOW_PROVIDER_THRESHOLD` 라는 더 정확한 사실을
   잃습니다.
4. **시드 키워드 매칭.** 네이버가 `relKeyword` 를 정규화해 돌려주면
   (예: 공백 제거, 대문자화) `normalize_keyword` 와 어긋나 시드 행을 못 찾고
   metrics 가 비게 됩니다. 이때도 숫자를 지어내지는 않지만 결과가 비어 보입니다.
   실제 응답 확보 후 `_split_seed_and_related` 의 매칭 규칙을 재검토해야 합니다.
5. **응답 스키마 변경.** 새 필드는 `unmapped_fields` 로 드러나고
   `partial_reason` 에 기록되지만, **이름이 바뀐 기존 필드**는 `MISSING` 이
   됩니다. 이것은 의도한 동작입니다(0 으로 채우지 않음). 다만 "왜 갑자기 전부
   측정 불가인가"를 사람이 알아채야 합니다.
6. **XLSX 를 실제 스프레드시트 앱에서 열어 본 적이 없습니다.** (요청 #4)
7. **호출 한도.** 계정 단위 rate limit 값을 모르므로 대량 조회 시 429 가 얼마나
   자주 날지 예측할 수 없습니다. backoff·circuit breaker 는 준비되어 있습니다.

---

# 부록 C — 이름에 대한 결정

`실시간 인기검색어` 라는 명칭은 **사용하지 않았습니다.** 합법적이고 문서화된
출처가 없기 때문입니다. 대신 `/keywords/recent` 가 반환하는 것은
**`VEO 최근 조회 키워드`** 이며, 응답에 다음을 모두 함께 실습니다.

- `window_hours` · `period_start` · `period_end` — 기준 기간
- `scope_ko` — 집계 범위(현재 조직의 VEO 조회 기록만)
- `refreshed_at` — 갱신 시각
- `de_identification_ko` — 비식별화 규칙
- `min_lookups` · `suppressed_count` — 최소 조회 횟수 미만으로 제외된 건수

`test_the_whole_openapi_document_never_says_the_forbidden_name` 이 OpenAPI 문서
전체를 훑어 금지된 명칭이 없는지 검사합니다.

비식별화에 대한 참고: `keyword_queries` 에는 **조회한 사용자 컬럼이 없습니다.**
그래서 사용자 단위 집계는 애초에 불가능하고, 조직 단위 합계만 나옵니다.
사용자 컬럼이 추가된다면 이 엔드포인트의 비식별화 규칙을 다시 설계해야 합니다.
