# VEO 점수 방법론

**방법론:** VEO-LAB · **구현:** VENOM

이 문서는 화면에 보이는 숫자가 어떻게 나오는지를 끝까지 설명한다. 배점 자체는
`packages/scoring-specs/specs/**`에 있고, 이 문서는 그 데이터를 읽는 규칙을 설명한다.

## 1. 무엇을 재는 점수인가

| 지표 | 의미 | 아닌 것 |
|---|---|---|
| SEO 기술 준비도 | 검색엔진이 발견·크롤링·해석·제공할 수 있는 상태인가 | 검색 순위 예측 |
| GEO 준비도 | AI 답변 엔진이 접근·추출·검증할 수 있는 구조인가 | 실제 AI 노출 여부 |
| AI 가시성 | 실제 프롬프트 표본에서 언급·인용됐는가 | 구조 품질 |
| 네이버 키워드 수요 | 공식 API가 보고한 검색량과 경쟁 지표 | VEO의 추정 |
| 기회 점수 | 위 값을 VEO 산식으로 조합한 우선순위 제안 | 공식 데이터 |

이들은 **절대 하나의 총점으로 합치지 않는다.**

## 2. 계산 규칙

### 2.1 검사 단위

```
coverage_i = 영향받은 중요도 가중 URL / 검사한 중요도 가중 URL
penalty_i  = severity_계수 × status_배수 × coverage_i × confidence_i
```

- `status_배수`: FAIL 1.0, WARNING 0.5, PASS 0.0
- `severity_계수`: BLOCKER 1.00 / CRITICAL 0.60 / MAJOR 0.30 / MINOR 0.10 / INFO 0.00
- `confidence_i`: 직접 관측 1.0, 공식 API 0.9, 휴리스틱 0.5–0.8, 외부 추정 0.4

INFO 계수가 0이므로 정보성 항목은 어떤 경우에도 점수를 깎지 않는다.

### 2.2 카테고리

```
budget         = 실제로 채점된 검사들의 severity 계수 합
category_score = 100 × max(0, 1 − Σpenalty_i / budget)
coverage       = 채점된 검사 수 / 적용 가능한 검사 수
confidence     = coverage × (채점된 검사 confidence의 severity 가중 평균)
```

- `NOT_APPLICABLE`인 검사는 **적용 가능** 집합과 **budget** 양쪽에서 빠진다.
- `UNKNOWN`인 검사는 적용 가능하지만 채점되지 않는다. budget에 들어가지 않고 감점도 없으며,
  coverage와 confidence만 낮춘다.
- 적용 가능한 검사가 하나도 없으면 카테고리 상태는 `NOT_APPLICABLE`.
- 적용 가능하지만 전부 UNKNOWN이면 카테고리 상태는 `UNKNOWN`.
- budget이 0인데 채점된 검사가 있다면(INFO만 남은 경우) 잃을 것이 없으므로 100점이다.

### 2.3 종합

```
채점 가능 카테고리 = 상태가 SCORED인 것만
overall = Σ(category_score × weight) / Σ(채점 가능 카테고리의 weight)
```

카테고리가 제외되면 가중치가 나머지에 자동 재분배된다. 예: 구조화 데이터를
쓰지 않는 사이트는 SEO 분모가 100에서 90으로 줄고, 남은 8개 중 7개 카테고리로 평가된다.

### 2.4 상한(cap)

평균만 쓰면 치명적 결함이 가려진다. 상한은 종합 점수의 **최댓값**을 제한한다.

| 조건 | 상한 |
|---|---:|
| 사이트 전체 robots/noindex 차단 | 25 |
| 주요 템플릿 5xx 또는 렌더 불가 | 35 |
| 대량 외부 canonical | 40 |
| sitemap 과반 비정상 | 55 |
| HTTPS·모바일 중대 실패 | 60 |

상한은 점수를 올리지 않는다. 상한 적용 전 점수(`score_before_caps`)와 적용 후 점수를
모두 보존하고, 사유와 해제 조건을 결과에 함께 담는다.

### 2.5 게이트(gate)

게이트는 **점수를 바꾸지 않는다.** 점수 옆에 별도 상태로 표시될 뿐이다.
GEO에서 4xx/5xx, 인증 필요, noindex, 검색용 AI 크롤러 차단은 `노출 차단` 상태를 만든다.

학습용 크롤러 차단은 사업 선택이므로 감점하지 않고 정보로만 표시한다.

## 3. 결과에 반드시 함께 나가는 것

모든 점수는 다음을 동반한다. 하나라도 빠지면 그 숫자는 VEO 점수가 아니다.

- 명세 id, 버전, SHA-256 체크섬
- 적용된 분모(`effective_weight_total`)와 카테고리별 budget
- coverage와 confidence
- 카테고리별 상태, N/A 검사 목록, UNKNOWN 검사 목록, 실패 검사 목록
- 적용된 상한과 그 사유·해제 조건
- 올라온 게이트
- 검사 단위까지 내려가는 `calculation_trace` (각 항목의 계수·배수·coverage·confidence·penalty·산식 문자열)

`POST /api/scoring/evaluate`로 같은 입력을 넣으면 같은 점수가 재현된다.

## 4. 명세 버전 관리

| 상태 | 의미 |
|---|---|
| DRAFT | VEO-LAB 작성 중 |
| REVIEW | 검토 중 |
| APPROVED | 승인, 미발행 |
| PUBLISHED | 운영 사용. **수정 불가** |
| RETIRED | 폐기, 과거 결과 해석용으로만 유지 |

발행된 버전은 바꾸지 않는다. 변경은 새 버전이며, 과거 결과를 새 산식으로 재계산할 때는
원래 점수와 재계산 점수를 모두 남긴다.

## 5. 사용하지 않는 표현

다음 표현은 근거가 없으므로 제품 어디에도 쓰지 않는다.

- "이 점수면 검색 1위" / "ChatGPT 1위"
- "스키마를 넣으면 인용 보장"
- "한 번의 질문 결과가 시장 점유율"
- "실시간 인기검색어" (합법적이고 문서화된 출처가 없는 경우)
- 측정 엔진·모델·날짜·지역·표본을 숨긴 단일 점수

## 6. 근거 문서

`docs/research/`에 원문 보관:

- `SEO_RECOMMENDED_SCORING_MODEL.md`
- `GEO_RECOMMENDED_SCORING_MODEL.md`
- `GEO_METRIC_DICTIONARY.md`
- `GEO_PROMPT_SAMPLING_AND_CONFIDENCE.md`
- `VEO_DEVELOPER_CHECKLIST.md`
