# VEO GEO 준비도 점수 방법론

**방법론:** VEO-LAB · **구현:** VENOM

> **이 본문은 운영 발행본 GEO `1.3.0` 을 설명한다** (발효 2026-08-02, 2026-08-08 확인).
>
> 배점 숫자 자체는 문서가 아니라 **데이터**에 있다:
> `packages/scoring-specs/specs/veo.geo.readiness/1.3.0.yaml`.
> 아래 표는 손으로 옮겨 적은 것이라 어긋날 수 있다. 의심되면 세어 본다:
>
> ```bash
> python3 scripts/spec_weights.py --domain geo
> ```

SEO 점수의 기준 문서는 [`methodology.md`](methodology.md) 하나이고, 이 문서는 **GEO
쪽만** 다룬다. 두 점수가 공유하는 규칙(못 잰 것의 처리, 측정 범위, 절대평가)은 여기서
다시 설명하지 않고 그쪽을 가리킨다 — 두 곳에 적으면 반드시 갈라진다(0-D).

---

## 1. 이 점수가 말하는 것과 말하지 않는 것

명세가 스스로 적어 둔 뜻을 그대로 옮긴다(`score_meaning.ko`):

> "AI 답변 엔진이 페이지에 접근하고, 답변에 쓸 수 있게 내용을 추출하고, 근거와
> 엔터티를 검증할 수 있는 **구조적 준비도**입니다. 실제 AI 노출·인용 여부는 이 점수가
> 아니라 별도의 AI 가시성 관측 결과로만 확인합니다."

**이것이 이 점수의 전부다.** 준비도 100점이 "ChatGPT 가 우리를 말한다" 는 뜻이 아니고,
40점이 "AI 가 우리를 모른다" 는 뜻도 아니다. 둘은 다른 축이고, 섞는 것을 ADR 0003 이
금지한다([`docs/adr/0003-geo-readiness-is-not-ai-visibility.md`](../adr/0003-geo-readiness-is-not-ai-visibility.md)).

실제 노출은 **③ AI 답변 관측**이 잰다 — 같은 질문을 여러 번 던져 언급·인용을 세는
별개의 엔진이다([`observation-engine.md`](../observation-engine.md)).

| | GEO 준비도 | AI 가시성 관측 |
|---|---|---|
| 무엇을 보나 | 우리 **홈페이지의 구조** | AI 엔진의 **실제 답변** |
| 어떻게 | 페이지를 가져와 검사 | 엔진에 질문을 던져 세기 |
| 돈 | 안 든다 | **호출마다 든다** |
| 답하는 질문 | "AI 가 쓸 수 있는 모양인가" | "지금 AI 가 우리를 말하는가" |

---

## 2. 여섯 영역과 배점

**[실측]** `python3 scripts/spec_weights.py --domain geo` 출력 (2026-08-08):

| 영역 | 뜻 | 가중치 | 검사 |
|---|---|---:|---:|
| `access_eligibility` | 접근·검색 적격성 | 22.22 | 7 |
| `answer_extractability` | 답변 추출성 | 22.22 | 6 |
| `evidence_transparency` | 근거·출처 투명성 | 16.67 | 5 |
| `entity_clarity` | 엔터티 명확성·일관성 | 16.67 | 6 |
| `structured_data_meta` | 구조화 데이터·메타 | 11.11 | 5 |
| `freshness_signals` | 최신성·변경 신호 | 11.11 | 4 |
| **합** | | **100.0** | **33** |

| 점수 밖 | | 10 | 4 |
|---|---|---:|---:|
| `external_verifiability` | 외부 검증 가능성 | (분모에 안 들어감) | 4 |

**SEO 와 달리 곱해지는 관문 영역이 없다.** SEO 의 `s1_blocked` 는 가중 평균 밖에서
곱해지지만, GEO 는 여섯 영역이 전부 가중 평균 안에 있고 차단은 **게이트 라벨**로 따로
말한다(§4).

### 왜 `external_verifiability` 는 점수 밖인가

명세에 적힌 사유 그대로다 — 두 가지 한계 때문이다.

* **네이버 한 곳만 본다.** 다른 사이트에서 이 사업자가 어떻게 언급되는지를 보는
  영역인데, 조회 가능한 창구가 네이버뿐이다.
* **이름이 비슷한 다른 업체의 글을 고객 것으로 셀 위험이 있다.**

그래서 `REFERENCE_ONLY` — **"참고 · 별도 확인 필요"** 로 보여는 주되 점수로 확정하지
않는다. 1.1.0 이 이 영역을 점수 밖으로 옮겼고, 1.2.0 이 그 사유를 고쳐 적었다.

> 1.1.0 이전에는 이 영역이 배점 안에 있었다. 수집 경로가 없는 항목을 배점에 두면
> **우리가 안 만든 기능 때문에 모든 고객의 점수가 내려간다.** 그래서 뺐다. 사라지지
> 않고 "이 진단의 배점 밖" 으로 사유와 함께 계속 보고된다.

---

## 3. 계산 규칙

### 3.1 심각도 계수

```
BLOCKER   1.0
CRITICAL  0.6
MAJOR     0.3
MINOR     0.1
INFO      0.0
```

`INFO` 가 0.0 인 것은 **점수를 안 깎는다**는 뜻이다. 보고는 하되 감점하지 않는다.

### 3.2 판정 상태가 점수에 미치는 영향

```
FAIL      감점 x 1.0
WARNING   감점 x 0.5
PASS      감점 x 0.0
N/A       분모에서 제외        (EXCLUDE_FROM_DENOMINATOR)
UNKNOWN   0점, 분모에 남김     (SCORE_AS_ZERO_KEEP_IN_DENOMINATOR)
```

**마지막 두 줄이 방향이 반대다.** 이유는 SEO 와 같다 —
[`methodology.md` §2.3](methodology.md) 을 볼 것. 요약하면:

* **해당 없음(N/A)** 은 결함이 아니므로 분모에서 뺀다.
* **측정 불가(UNKNOWN)** 를 분모에서 빼면 **덜 잴수록 점수가 오른다.** 그래서 남긴다.

GEO 도 1.1.0 에서 이 절대평가로 옮겼다. 그전에는 못 잰 항목을 분모에서 빼는 상대
평가였고, 실측으로 차이가 잡혔다:

```
www.seokorea.org   79.86 (분모 90)  →  71.88 (분모 100)
```

SEO 는 1.2.0 에서 이미 옮긴 규칙인데 **GEO 만 다섯 달 동안 남아 있었다.** 그것을
검사하는 코드가 없어서 아무도 몰랐다.

### 3.3 확신도

```
DIRECT_OBSERVATION  1.00   직접 봤다
OFFICIAL_API        0.90   공식 API 가 말했다
HEURISTIC_HIGH      0.80
HEURISTIC_MEDIUM    0.65
HEURISTIC_LOW       0.50
EXTERNAL_ESTIMATE   0.40   바깥 추정치
```

손실에 그대로 곱해진다:

```
penalty_i = weight_i x status_multiplier x breadth_i x confidence_i
```

(`apps/api/src/veo/scoring/evaluator.py:16`)

**확신이 낮은 판정은 덜 깎는다** — 우리가 애매하게 본 것으로 고객 점수를 세게 깎지
않는다.

### 3.4 URL 중요도

```
CONVERSION_OR_HOME   3.0
CATEGORY_OR_HUB      2.0
CONTENT_OR_PRODUCT   1.0
TAG_OR_FILTER        0.5
INTENTIONAL_NOINDEX  0.0
```

이 값은 손실에 직접 곱해지지 않고, **폭(breadth)** 을 잴 때 페이지마다의 무게가 된다:

```
coverage_i = affected_importance_weight / evaluated_importance_weight
```

(`apps/api/src/veo/scoring/evaluator.py:10`)

그래서 홈·전환 페이지의 결함이 태그 목록 페이지의 결함보다 무겁게 센다. 일부러
`noindex` 를 건 페이지는 0.0 — **의도한 것을 결함으로 세지 않는다.**

---

## 4. 게이트 — 점수를 바꾸지 않고 라벨을 바꾼다

게이트는 감점이 아니라 **표시**다. 점수와 별개로 "지금 이 상태" 를 한 줄로 말한다.

| 게이트 | 상태 코드 | 언제 |
|---|---|---|
| 노출 차단 — 응답 오류 | `EXPOSURE_BLOCKED` | `geo.access.http_status_ok` 실패 (4xx/5xx) |
| 노출 차단 — 인증 필요 | `EXPOSURE_BLOCKED` | `geo.access.no_auth_required` 실패 |
| 노출 차단 — noindex | `EXPOSURE_BLOCKED` | `geo.access.indexable` 실패 |
| 노출 차단 — 검색용 AI 크롤러 차단 | `SEARCH_CRAWLER_BLOCKED` | 검색용 크롤러를 robots 로 막음 |
| 위험 — 구조화 데이터 불일치 | `STRUCTURED_DATA_MISMATCH` | 화면과 다른 schema 선언 |

### 학습용 봇 차단은 감점하지 않는다

명세가 영역 설명에 못박아 두었다:

> "검색용 크롤러 차단만 평가합니다. **학습용 크롤러 차단은 정책 선택이며 감점하지
> 않습니다.**"

GPTBot 을 막는 것은 틀린 선택이 아니라 **선택**이다. 그것을 감점하면 우리가 고객의
정책을 대신 정하는 것이 된다.

### schema 가 없는 것과 틀린 것은 다르다

```
schema 부재      치명적 오류가 아니다
화면과 불일치    위험(STRUCTURED_DATA_MISMATCH)
```

없는 것보다 **틀린 것이 나쁘다.** 화면에 없는 평점·가격을 schema 로 선언하면 AI 가
그것을 사실로 인용하고, 그 거짓은 우리 고객의 이름으로 퍼진다.

---

## 5. 측정 범위

```
max_pages: 200                한 진단이 가져오는 페이지 상한
max_depth: 4                  시드에서 몇 번 이동까지
template_group_sample: 12     상한 초과가 예상될 때만, 게시판형 그룹당 표본
truncated_absence: UNKNOWN    잘린 크롤에서 부재 주장은 측정 불가
```

**SEO 와 같은 값이고 같은 크롤러(`ConsoleCrawler`)·같은 서버 설정이다.** 근거 실측도
같다(참사랑한의원: 100장 상한 76.4 → 200장 71.8, 무조건 표본 71.8→77.6) —
[`methodology.md` §2.9](methodology.md) 에 자세히 있다.

같은 값이 두 명세에 적혀 있는 이유: **각 명세가 자기 점수의 분모를 스스로 말해야 한다.**
서버 설정과 어긋나지 않는 것은 시험이 강제한다.

### GEO 에는 표본 정책이 없다

SEO 1.9.0 은 성능 검사 7개를 표본으로 줄이고 그 페이지 판정을 `NOT_SAMPLED` 로 둔다.
**GEO 는 그런 항목이 아직 없다** — 페이지당 실측 비용이 큰 검사가 없어서 줄일 이유가
없다. 그래서 명세가 `sampling` 을 선언하지 않고, 선언하지 않은 판에서는 `NOT_SAMPLED`
판정 자체가 허용되지 않는다.

---

## 6. 등급 구간

| 등급 | 구간 | 뜻 |
|---|---:|---|
| 준비 완료 | 85–100 | AI 답변 엔진이 접근·추출·검증하기에 구조적 장애가 없다 |
| 양호 | 70–85 | 일부 영역에서 추출성 또는 근거 보강이 필요하다 |
| 주의 | 45–70 | 답변 인용에 필요한 근거·엔터티 신호가 부족하다 |
| 취약 | 20–45 | 접근성 또는 추출성에 광범위한 문제가 있다 |
| 차단 | 0–20 | — |

등급은 점수를 바꾸지 않는다. 같은 점수는 언제나 같은 등급이다.

---

## 7. 판 이력 — 무엇이 언제 바뀌었나

명세의 `changelog` 를 요약한다. 원문은 YAML 안에 있다.

| 판 | 날짜 | 무엇이 바뀌었나 | 점수가 바뀌나 |
|---|---|---|---|
| `1.3.0` | 2026-08-02 | 측정 범위(`measurement_scope`)를 명세로 선언 | **아니오** |
| `1.2.0` | 2026-07-31 | 외부 검증 항목의 제외 사유를 고쳐 적음 (`PAID_PROVIDER` → `REFERENCE_ONLY`) | **아니오** |
| `1.1.0` | 2026-07-31 | 절대평가로 이동 · `external_verifiability` 를 점수 밖으로 | **예** |
| `1.0.0` | 2026-07-28 | 최초 발행 | — |

**1.2.0 이 고친 것은 말이다.** 1.1.0 은 외부 검증 네 항목을 "유료 데이터원 필요" 라고
적었는데 **사실이 아니었다.** 실측해 보니 이미 가진 네이버 자격증명으로 지역·블로그·
뉴스·웹문서 검색이 전부 열린다. 돈 문제가 아니었다.

> "유료 서비스가 필요합니다" 라고 적으면 **우리 쪽 한계를 고객이 돈으로 풀어야 할
> 일처럼 넘기게 된다.** 우리가 못 잰 것과 고객이 권한을 안 준 것을 구분한다(0-A).

---

## 8. 이 문서와 다른 문서의 경계

| 무엇을 찾나 | 어디로 |
|---|---|
| SEO 점수 산식·PageSpeed·성능 배점 | [`methodology.md`](methodology.md) |
| 못 잰 것의 처리 · 측정 범위 · 사이트/페이지 점수 | [`methodology.md`](methodology.md) §2.3·§2.9 |
| GEO 준비도와 AI 노출을 왜 안 섞나 | [ADR 0003](../adr/0003-geo-readiness-is-not-ai-visibility.md) |
| 해당 없음 / 측정 불가의 뜻 | [ADR 0002](../adr/0002-na-and-unknown-semantics.md) |
| 실제 AI 답변 관측 | [`observation-engine.md`](../observation-engine.md) |
| 배점 숫자 원본 | `packages/scoring-specs/specs/veo.geo.readiness/1.3.0.yaml` |
