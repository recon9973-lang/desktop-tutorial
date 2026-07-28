# VEO 용어집

같은 단어를 다르게 쓰면 계약이 무너집니다. 아래 정의가 코드·API·화면·보고서에서
동일하게 적용됩니다.

## 제품

| 용어 | 정의 |
|---|---|
| VEO | 제품명. SEO · GEO · Naver Keyword Intelligence Platform |
| VENOM | 개발사 |
| VEO-LAB | 연구·측정 방법론 관리 조직. 점수 명세를 작성·승인 |
| VEO Public | 로그인 없이 쓰는 공개 진단. 범위·호출량 제한 |
| VEO Console | 내부 운영 도구. 조직·프로젝트·경쟁사·이슈·보고서·권한 |

Public과 Console은 **같은 분석 엔진**을 사용합니다. 다른 것은 범위, 한도, 결과 노출입니다.

## 측정

| 용어 | 정의 | 혼동하기 쉬운 것 |
|---|---|---|
| SEO 기술 준비도 | 검색엔진이 발견·크롤링·해석·제공할 수 있는 상태 | 검색 순위 |
| GEO 준비도 | AI 답변 엔진이 접근·추출·검증할 수 있는 구조 | 실제 AI 노출 |
| AI 가시성 | 실제 프롬프트 표본에서의 언급·인용 비율 | GEO 준비도 |
| 검색 성과 | 노출·클릭·CTR·평균순위 (연동된 경우만) | 기술 준비도 |
| Share of Voice | 선택한 경쟁군 대비 언급·인용 비중 | 시장 점유율 |

**Share of Voice는 비교군이 바뀌면 값이 바뀝니다.** 항상 비교군을 함께 표시합니다.

## 검사 상태

| 상태 | 의미 | 점수 영향 |
|---|---|---|
| `PASS` | 통과 | 감점 없음 |
| `WARNING` | 부분 통과 | 실패의 절반 감점 |
| `FAIL` | 실패 | 심각도 × coverage × confidence 만큼 감점 |
| `NOT_APPLICABLE` | 대상에 적용되지 않음 | **분자·분모 양쪽에서 제외.** 0점이 아님 |
| `UNKNOWN` | 적용되지만 측정하지 못함 | **감점 없음.** coverage·confidence 하락 |

`NOT_APPLICABLE`과 `UNKNOWN`은 서로 다른 사유 컬럼에 이유와 함께 저장합니다.
화면에서 **색상만으로 구분하지 않습니다.**

## 점수 용어

| 용어 | 정의 |
|---|---|
| severity 계수 | BLOCKER 1.00 / CRITICAL 0.60 / MAJOR 0.30 / MINOR 0.10 / INFO 0.00 |
| coverage (검사) | 영향받은 중요도 가중 URL ÷ 검사한 중요도 가중 URL |
| coverage (카테고리) | 채점된 검사 수 ÷ 적용 가능한 검사 수 |
| confidence | 근거 강도. 직접 관측 1.0, 공식 API 0.9, 휴리스틱 0.5–0.8, 외부 추정 0.4 |
| budget | 카테고리에서 실제로 채점된 검사들의 severity 계수 합 = 잃을 수 있는 최대치 |
| cap (상한) | 치명적 결함이 있을 때 종합 점수의 최댓값. 점수를 올리지 않음 |
| gate (게이트) | 점수 옆에 표시되는 **별도 상태**. 점수 산식에 개입하지 않음 |
| band (구간) | 점수 해석 라벨. 검색 순위 수준이 아니라 준비도 |
| calculation_trace | 검사 단위까지 내려가는 계산 기록. 이것으로 점수를 손으로 재현할 수 있어야 함 |

## 데이터 출처

| 출처 | 의미 |
|---|---|
| `NAVER_SEARCH_AD` | 공식 API의 **절대** 월간 검색량·클릭·CTR·경쟁도 |
| `NAVER_DATALAB` | **상대** 검색 관심도 지수. 검색 횟수가 아님 |
| `NAVER_SEARCH_API` | 네이버 검색 결과 API |
| `GOOGLE_SEARCH_CONSOLE` | 노출·클릭·CTR·평균순위 |
| `GOOGLE_PAGESPEED` | Lighthouse **lab** 값 |
| `GOOGLE_CRUX` | 실사용자 **field** 값 |
| `AI_ENGINE_OBSERVATION` | 실제 AI 답변 관측 |
| `VEO_CRAWLER` | VEO 직접 수집 |
| `CALCULATED` | VEO 계산값 (합계, 기기 비중, 기회 점수 등) |
| `VEO_INTERNAL` | VEO 사용자 조회·저장 데이터 |

**lab과 field는 절대 같은 지표로 합치지 않습니다.**

## 값의 품질

| 값 | 의미 |
|---|---|
| `EXACT` | 제공자가 준 정확한 값 |
| `ROUNDED` | 제공자가 반올림한 값 |
| `RANGE` | 제공자가 범위로 준 값 |
| `SUPPRESSED_BY_PROVIDER` | 제공자가 의도적으로 가린 값 |
| `BELOW_PROVIDER_THRESHOLD` | 제공자 보고 기준 미만 |
| `MISSING` | 없음 |

**억제값과 결측값을 0으로 바꾸지 않습니다.** 0은 "검색이 없었다"는 사실이고,
나머지는 "모른다"는 사실입니다.

## 제공자 상태

| 상태 | 의미 |
|---|---|
| `ENABLED` | 자격증명 있음, 실제 조회 |
| `DISABLED_NO_CREDENTIAL` | 자격증명 없음. 관련 검사는 `UNKNOWN` |
| `DISABLED_BY_CONFIG` | 설정으로 끔 |
| `DEGRADED` | 불안정, 일부 결과 누락 가능 |
| `CIRCUIT_OPEN` | 연속 실패로 호출 차단 중 |

## 작업 상태

`QUEUED` → `RUNNING` → (`SUCCEEDED` | `PARTIAL_SUCCESS` | `FAILED_RETRYABLE` →
`FAILED_FINAL`), 그리고 `CANCEL_REQUESTED` → `CANCELLED`, 만료 시 `EXPIRED`.

`PARTIAL_SUCCESS`는 100개 중 80개를 수집한 결과가 "실패"보다 더 유용하고 더 정직하기
때문에 존재합니다. 수집·시도 건수를 함께 보고합니다.

## URL 중요도

| 분류 | 가중치 |
|---|---:|
| `CONVERSION_OR_HOME` | 3.0 |
| `CATEGORY_OR_HUB` | 2.0 |
| `CONTENT_OR_PRODUCT` | 1.0 |
| `TAG_OR_FILTER` | 0.5 |
| `INTENTIONAL_NOINDEX` | 0.0 (관련 검사 분모에서 제외) |

## 크롤러 구분

- **검색용 크롤러**: AI 답변에 인용되기 위한 접근. 차단하면 GEO 감점 대상이며
  `SEARCH_CRAWLER_BLOCKED` 게이트가 올라갑니다.
- **학습용 크롤러**: 모델 학습을 위한 접근. 차단은 **사업 선택**이며 감점하지 않고
  정보로만 표시합니다.

## 사용하지 않는 용어

- "실시간 인기검색어" — 합법적이고 문서화된 출처가 없으면 사용하지 않습니다.
  대신 "VEO 최근 조회 키워드", "최근 24시간 급상승 키워드", "업종별 추천 키워드",
  "내부 프로젝트 인기 키워드" 중 실제 데이터에 맞는 것을 쓰고 기준 기간·범위·갱신
  시각·비식별화 규칙을 표시합니다.
- "종합 SEO/GEO 점수" — 도메인을 합친 단일 총점은 만들지 않습니다.
