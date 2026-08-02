# SEO 점수 알고리즘 v3 — 2단계 측정: 설계와 검증

**작성 2026-08-01.** 참조 구현 `docs/research/prototypes/seo_scoring_v3_pages.py`,
성질 시험 `test_seo_scoring_v3_pages.py`(24개, 기존 v2 24개와 함께 48개 전부 통과).

이 판은 사이트 점수 산식을 **바꾸지 않는다.** 같은 입력이면 v2/1.8.0 과 같은
점수가 나온다(시험으로 고정). 더하는 것은 넷이다: 손실의 검사 단위 **분해**,
**페이지 점수**, **부재 주장 규칙**, **부분 재측정** 규칙.

모든 수치 결정의 근거는 §5 대조표에 있다. 구글이 공표한 것(실측한 Lighthouse
배점·Search Central 문서·CWV 임계값)과 구글이 공표하지 않아 VEO 가 판단한 것을
표에서 구분했다 — **구글이 말하지 않은 것을 구글 근거처럼 꾸미지 않는다(0-A).**

---

## 1. 왜 — 제품 구조 (사용자 확정)

- 상위 탭 = **사이트 점수**: 전체 크롤, 59개 검사, 1.8.0 산식 그대로.
- 하위 = **페이지 점수**: 그 페이지의 URL 범위 검사만 재집계.
- 사이트 점수가 페이지 점수들보다 낮을 수 있고, **그 차이의 이유를 화면이 스스로
  설명해야 한다.**

이 구조 자체에 구글 근거가 있다. 구글의 순위 평가는 기본적으로 페이지 단위이되
사이트 단위 평가가 따로 존재한다:

> "Our core ranking systems generally evaluate content on a page-specific basis
> … However, we do have some site-wide assessments."
> — https://developers.google.com/search/docs/appearance/page-experience

색인의 단위도 페이지다 — "not every page that Google processes will be indexed"
(https://developers.google.com/search/docs/fundamentals/how-search-works).
**페이지 점수(URL 검사)와 사이트 점수(SITE 검사 포함)를 따로 내는 것은 구글이
실제로 평가하는 구조와 동형이고, 둘을 합치지 않는 것도 같은 이유다.**

확정된 사실(재검증 불필요):

- 100점의 구성: 전페이지×URL검사(성능 제외) **71.6** / 전페이지×SITE검사 **20.1**
  / 상위 5장×성능 **8.3** (원배점 기준, 관문 30 포함).
- URL 검사도 크롤한 모든 페이지에서 판정한다. 표본은 성능뿐.
- 실패 evidence 에 URL 이 이미 남는다 → 페이지별 재집계는 **새 측정 없이** 가능.
- 관문을 뺀 다섯 단계의 가중치 합이 정확히 100.0.

---

## 2. 이 판이 고치는 결함 — 부재 주장 (0-A 위반)

잘린 크롤(100장 상한)에서 부재형 SITE 검사(`no_duplicate_*`, `no_orphan`,
`no_broken_links`)가 PASS 를 단정한다. **표본으로 존재는 증명되지만 부재는
증명되지 않는다.** `collect/sample.py` 의 `is_whole_site` 규칙 자체는 옳다 —
문제는 수집기가 그 질문을 **1장 크롤 경로에서만** 묻는다는 것이다. 100장 잘린
크롤은 질문 없이 통과한다.

v3 규칙 (`absence_claim`):

| 관측 | 표본 | 판정 |
|---|---|---|
| 결함 발견 | 무엇이든 | **FAIL** — 존재는 표본으로 증명된다 |
| 미발견 | 전체 크롤 | **PASS** — 부재가 실제로 증명됐다 |
| 미발견 | 일부(잘린 크롤 포함) | **UNKNOWN** — "본 N장 중에는 없었다. 나머지는 확인 못함" |

UNKNOWN 은 분모에 남아 0점이므로(ADR 0016) **덜 재서 점수가 오르지 않는다.**
시험 `test_seeing_fewer_pages_never_raises_the_site_score` 가 전체→100장→1장
순서로 단조 비증가를 고정한다 — 1장 52.23 > 25장 50.11 실측이 재발하지 않는다.

---

## 3. 설계

### 3.1 분해 — 항등식

```
overall_before_caps(= quality) = 100 − Σ(URL손실) − Σ(SITE손실)     ← 항등식, 1e-9
score                          = 도달률(reach) × quality             ← 곱셈
(실코드) 최종 점수              = min(score, 상한들)                  ← 절단
```

손실은 전부 **검사 하나에 귀속**되고 명세의 scope(URL|SITE)가 붙는다.
도달률(관문)과 상한은 **뺄셈 항이 아니다** — 손실 목록에 섞으면 합이 안 맞거나
이중으로 깎인다. 화면은 관문을 "차단으로 도달률 X% 소실"(곱셈)로, 상한을
"이 결함이 있으면 최대 N점"(절단)으로 따로 그린다.

이 항등식이 있어야 "페이지는 전부 100점인데 사이트는 왜 낮은가" 를 화면이
**SITE 손실 목록 + 도달률**만으로 끝까지 설명한다. 시험
`test_perfect_pages_with_a_lower_site_score_is_fully_explained` 가 이 재구성을
고정한다: URL 검사가 전부 통과면 손실 목록에 URL 항목이 있을 수 없고,
`score == reach × (100 − SITE손실합)`.

모서리 하나: 단계 전체가 해당 없음이면 v2 산식은 그 단계 가중치를 재분배하지
않고 잃는다. 항등식을 지키기 위해 그 손실을 구성 검사에 배점 비례로 귀속한다
(`kind=STAGE_NOT_APPLICABLE`). §6 의 불일치 기록을 함께 봐라.

### 3.2 페이지 점수

페이지 p 의 점수 = **그 페이지에서 판정된 URL 범위 검사만으로**, 같은 단계
구조를 페이지 분모로 재정규화:

```
페이지 단계분모 = 그 단계 URL 검사 배점 합 (명세 상수: S2=11, S3=16, S4=13.5, S5=7, S6=2.4)
페이지 도달률   = Π (1 − 그 페이지 관문 검사의 상태배수)      ← robots meta·HTTP 상태 등
페이지 점수     = 도달률 × Σ(단계점수 × 가중치) / Σ(채점가능 단계 가중치)
```

- **페이지 관문 실패 → 그 페이지 ~0점.** 색인 단위가 페이지라는 구글 문서가
  근거다 — noindex 페이지는 검색에 존재하지 않으므로 나머지가 완벽해도 무의미하다.
- **SITE 검사를 페이지에 넣으면 오류다**(조용한 무시가 아니라 ValueError).
  분모가 다른 두 숫자를 같은 눈금처럼 보이게 하는 것이 우리가 타사에서 잡아낸
  바로 그 결함이다(methodology §2.9).
- 못 잰 관문은 곱하지 않는다(0-A) — 사이트와 같은 방향.

### 3.3 세 가지 '안 잰 것' — NOT_SAMPLED 신설

| 상태 | 분모 | 뜻 | 근거 |
|---|---|---|---|
| `NOT_APPLICABLE` | 뺀다 | 이 페이지에 그 항목이 없다 | ADR 0002 |
| `UNKNOWN` | 남긴다, 0점 | 재려 했으나 실패했다 | ADR 0016 |
| `NOT_SAMPLED` | **뺀다 + "표본 밖 — 요청 시 측정" 표기** | 명세의 표본 정책이 안 재기로 했다 | 0-J |

근거 둘. 첫째, **0-J**: 성능 lab 은 명세가 상위 5장만 재기로 했다
(`sampling.perf_lab`, 한 장 16~60초 실측). 표본 밖 페이지에서 그 8.3점어치를
UNKNOWN 으로 두면 우리 정책으로 안 잰 것이 그 페이지의 감점이 된다 — 고객
탓으로 돌리는 것이다. 둘째, **조작 유인이 없다**: 표본 선정이 명세에 고정돼
있고(중요도 상위, `url_importance`), 재는 쪽이 표본을 고를 수 없다.

**반론(기록해 둔다).** 절대평가의 원칙은 "못 잰 것은 분모에 남는다"(ADR 0016)
이고 NOT_SAMPLED 는 그 예외다. 예외가 늘면 원칙이 죽는다. 그래서 경계를 코드가
지킨다: NOT_SAMPLED 는 명세가 표본 정책을 선언한 검사(성능 lab 6개 + field 1개)
에만 허용되고, 다른 검사에 붙이면 **오류**다. "안 재기로 했다" 가 절대평가를
비껴가는 뒷문이 되지 않는다. 시험 둘이 이 경계와, NOT_SAMPLED 가 페이지 간
순위를 바꾸지 않음(동일 정책 동일 적용)을 고정한다.

구글도 성능을 전수 실측으로 말하지 않는다 — Search Console 은 URL 그룹으로,
CrUX 는 origin 값과 75퍼센타일로 답한다(§5 근거 5·6). 표본·집계로 성능을 말하는
것 자체가 구글의 방식이다.

### 3.4 변화 대응 — 부분 재측정과 명세 개정

- 페이지를 고친 뒤 **그 페이지만 재크롤**: URL 판정만 갱신된다. SITE 판정은
  이전 전체 진단 값에 **"이 값은 YYYY-MM-DD 전체 진단 기준"** 을 달아 유지한다
  (`page_panel`). 날짜가 없으면 사용자는 방금 잰 값으로 읽는다(0-J).
- **명세 개정(검사 추가)**: 고정분모 원칙대로 같은 단계·같은 범위 안에서 배점을
  재분할하면, 페이지 단계분모(URL 배점 합)가 변하지 않으므로 **무관한 페이지의
  점수가 흔들리지 않는다.** 시험이 title 6→5 + 신설 1 재분할로 이를 고정한다.
  URL 검사가 SITE 검사에서 배점을 가져오는 재분할은 페이지 눈금을 바꾸므로,
  그때는 페이지 점수 재산정 공지가 필요하다(의도적 결정으로 드러나게 했다).

### 3.5 성능

- lab(LCP·CLS·TBT·압축·이미지포맷·리소스힌트)은 상위 5장 실측, 그 밖 페이지는
  NOT_SAMPLED.
- 실사용자(INP field)는 **origin(사이트 전체) 값**이므로 사이트 점수에서만 쓰고
  페이지에는 붙이지 않는다 — 어느 페이지에서도 NOT_SAMPLED 다. 범위 혼합 금지
  (methodology §3.1): 사이트 전체 값은 방문 많은 페이지가 지배하므로, 특정
  페이지에 붙이면 그 페이지가 겪지도 않은 트래픽으로 칭찬하게 된다.

---

## 4. 판단이 갈린 지점 — 결정·근거·반론

**(1) 페이지 종합은 채점 가능한 단계로 재정규화한다 (사이트 v2 산식과 다른 점).**
페이지는 템플릿에 따라 구조가 다르다 — 구조화 데이터가 원래 없는 안내 페이지에서
S5 가 통째로 빠졌다고 감점하면 페이지 순위가 결함이 아니라 템플릿 종류로 갈린다.
실코드 평가기(`evaluator.py`)도 영역 단위에서 같은 재정규화를 한다.
**반론**: 사이트 점수(v2 프로토타입)는 단계가 통째로 사라지면 그 가중치를 잃는다
— 페이지와 사이트가 이 모서리에서 다르게 움직인다. 기록해 두고 §6 에서 다룬다.

**(2) inp_field 를 모든 페이지에서 NOT_SAMPLED 로 둔다.** N/A("이 페이지엔
없다")도 UNKNOWN("재려다 실패")도 사실과 다르다 — 값은 있는데 **범위가 사이트**라
안 붙이는 것이므로 "정책상 안 잼" 이 정확하다. **반론**: CrUX 는 페이지 값을
주기도 한다(트래픽 많은 페이지). 그때 페이지 값을 붙이는 확장은 가능하지만,
페이지마다 있다 없다 하는 값은 페이지 간 비교를 다시 깨뜨린다. 1단계에서는
일괄 NOT_SAMPLED 가 맞다.

**(3) 부재 주장에서 sitemap 선언 수와 크롤 수의 불일치는 아직 안 본다.**
`is_whole_site` 는 "2장 이상 + 크롤이 스스로 멈춤"이면 전체로 친다. sitemap 이
200장을 선언했는데 링크로는 50장만 발견된 경우(잘 숨겨진 JS 메뉴)도 전체로
접힌다 — 잠재 구멍이다. 이번 판 범위 밖으로 두고 기록만 남긴다. 강화하면 stale
sitemap 사이트가 영영 "전체" 판정을 못 받는 부작용이 있어, `sitemap.urls_valid`
판정과 함께 설계해야 한다.

**(4) 배점 수치는 1.8.0 에서 한 숫자도 바꾸지 않았다.** §5 대조 결과 1.8.0 을
바꿔야 할 지점은 발견되지 않았다 — 1.8.0 자체가 2026-08-01 Lighthouse 실측
대조로 짜였기 때문이다(발행본 불변, ADR 0012). 다음 판 검토 후보만 §5.3 에 남긴다.

---

## 5. 배점 근거 대조표 — 구글이 말한 것과 VEO 가 판단한 것

**읽는 법.** 근거 등급 세 가지:

- ● **실측** — 구글 Lighthouse 13.4.1 의 실제 배점(`auditRefs[].weight`)을 직접
  읽었다. 출처: `docs/research/LIGHTHOUSE_COMPARISON.md` (2026-08-01, 원본 응답 보관).
- ◐ **문서** — 구글이 공식 문서로 공표했다(아래 URL). 배점 **수치**는 VEO 판단.
- ○ **없음** — 구글 근거 없음. VEO 판단이며 그렇게 적는다. 업계 통설은 구글
  공식 입장과 섞지 않는다.

구글은 순위 알고리즘 자체를 공개하지 않는다. 이 표의 어떤 항목도 "이만큼 순위가
오른다" 를 뜻하지 않는다 — VEO 점수는 준비도이지 순위 예측이 아니다
(`is_rank_prediction: false`).

### 5.1 v3 구조 결정의 근거 (조사 출처 URL 포함)

| 결정 | 구글 근거 | 출처 |
|---|---|---|
| 페이지 점수를 따로 낸다 | 색인·평가의 기본 단위가 페이지: "not every page that Google processes will be indexed" | https://developers.google.com/search/docs/fundamentals/how-search-works |
| SITE 검사는 사이트 점수에만 | "generally evaluate content on a page-specific basis … we do have some site-wide assessments" — 페이지 평가와 사이트 평가가 **둘 다, 따로** 존재 | https://developers.google.com/search/docs/appearance/page-experience |
| 페이지 관문(곱셈) | 구글 SEO 카테고리에서 is-crawlable 하나가 4.04/13.04 = **31%** (실측) — 색인 가능성에 압도적 배점. 색인 단위가 페이지이므로 관문도 페이지 단위 | ● 실측 + 위 how-search-works |
| 성능 총 8.3/100 (지배적이지 않게) | "Google Search always seeks to show the most relevant content, **even if the page experience is sub-par**" + "in cases where there are many pages that may be similar in relevance, page experience can be much more important" — 성능은 관문이 아니라 **동점일 때 갈리는** 신호 | https://developers.google.com/search/docs/appearance/page-experience · https://developers.google.com/search/blog/2020/05/evaluating-page-experience |
| CWV 판정 임계값 | LCP 2.5s · INP 200ms · CLS 0.1, **75퍼센타일** | https://web.dev/articles/vitals |
| 성능은 표본·집계로 말한다 (NOT_SAMPLED 의 방향) | Search Console CWV 보고서는 URL 을 그룹으로 묶어 답한다: "pages that have a similar user experience", 그룹 상태 하나로 보고. CrUX 는 origin 값 제공(PageSpeed 응답 동봉, 실측) | https://support.google.com/webmasters/answer/9205520 |
| 범위 지수 0.7 의 **방향** | 같은 보고서: 그룹의 결함은 "common framework … same underlying reasons" — 결함은 템플릿 단위라는 판단을 구글도 한다. 구글은 아예 그룹 전체를 한 상태로 찍는다(사실상 지수 0 방향). VEO 0.7 은 선형(1.0)과 그 사이 | 위와 동일. **0.7 이라는 수치 자체는 ○ VEO 판단** |
| S2(대표 URL) 검사들의 근거 | canonical 미지정 시 "Google will identify which version … is objectively the best"(임의 선택), 중복은 크롤 낭비·신호 분산("consolidate the signals … into a single, preferred URL"). **패널티라는 말은 구글 문서에 없고 우리도 쓰지 않는다** | https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls |
| 못 잰 것을 실패로 안 적는다 | 구글 근거가 아니라 **구글의 결함을 반면교사로**: Lighthouse 는 robots.txt fetch 타임아웃을 0점 실패로 적었고 같은 사이트가 1.00↔0.92 를 오갔다(실측) | LIGHTHOUSE_COMPARISON.md §5 |

### 5.2 검사별 대조 (1.8.0 배점, 원배점 단위)

관문 S1 (30 — 곱셈):

| 검사 | 배점 | 등급 | 구글 대응 |
|---|---:|:-:|---|
| http.status_ok | 10 | ● | Lighthouse SEO `http-status-code` w1 + is-crawlable 계열. 관문化는 is-crawlable 31% 실측이 근거 |
| robots.txt_allows_url | 8 | ● | `is-crawlable` w4.04 — SEO 카테고리 최대 배점 |
| robots.meta_indexable | 8 | ● | `is-crawlable` w4.04 (noindex 포함) |
| content.js_render_parity | 4 | ◐ | 구글 JavaScript SEO 문서(렌더링 후 색인). 배점 수치는 VEO |

S2 대표 URL (15 = URL 11 + SITE 4):

| 검사 | 배점 | 등급 | 구글 대응 |
|---|---:|:-:|---|
| canonical.declared_and_consistent | 6 | ●◐ | Lighthouse `canonical` w1 + consolidate-duplicate-urls(§5.1) |
| canonical.not_cross_domain | 5 | ◐ | 같은 문서 — 신호가 남의 도메인으로 통합됨. 수치 VEO |
| onpage.no_duplicate_metadata (SITE) | 2 | ◐ | 같은 문서 — 중복은 대표 선택·신호 분산 문제. Lighthouse 는 1페이지 도구라 원리적으로 못 잰다 |
| content.no_duplicate_bodies (SITE) | 2 | ◐ | 같은 문서. 수치 VEO |

S3 해석 (20 = URL 16 + SITE 4):

| 검사 | 배점 | 등급 | 구글 대응 |
|---|---:|:-:|---|
| onpage.title_present_and_unique | 6 | ● | Lighthouse `document-title` w1. **주의**: 구글 상대비중은 1/13.04≈8%, VEO 는 6/20=30% — 구글보다 훨씬 높다. 근거는 "대체 불가 신호" 라는 ○ VEO 판단이다 (§5.3 후보) |
| content.no_thin_signal (SITE) | 4 | ○ | 구글 근거 없음(대응 감사 없음) — VEO 판단 |
| onpage.single_meaningful_h1 | 3 | ○ | 접근성 `heading-order` 는 있으나 SEO 카테고리 아님 — VEO 판단 |
| onpage.single_title_element | 2 | ○ | 구글 근거 없음(NXT 대조에서 옴) — VEO 판단 |
| sd.matches_visible_content | 2 | ◐ | 구조화 데이터 일반 가이드라인(불일치 시 무시·수동 조치). 수치 VEO |
| onpage.heading_hierarchy | 1 | ○ | 접근성 항목 — SEO 근거 없음 |
| onpage.html_lang_declared | 1 | ○ | 접근성 `html-has-lang` — SEO 근거 없음 |
| onpage.image_alt_coverage | 1 | ● | Lighthouse SEO `image-alt` w1 |

S4 경쟁력 (20 = URL 13.5 + SITE 6.5):

| 검사 | 배점 | 등급 | 구글 대응 |
|---|---:|:-:|---|
| ux.mobile_viewport | 3.5 | ◐ | 모바일 우선 색인 문서 + Lighthouse `meta-viewport`(접근성). 수치 VEO |
| security.https_valid (SITE) | 3 | ◐ | 구글이 공표한 순위 신호(HTTPS, 2014 공지). "매우 약한 요인" 이라 1.8.0 에서 4→3 |
| perf.lcp_lab | 3 | ● | Lighthouse 성능 w25/100 + good 2.5s (web.dev) |
| perf.inp_field | 2 | ◐ | CWV 본체, good 200ms (web.dev). Lighthouse 는 실험실이라 INP 없음 — TBT 가 대역 |
| perf.cls_lab | 2 | ● | Lighthouse 성능 w25 — **LCP 와 동등**(실측). 1.8.0 에서 0.5→2.0 상향의 근거 |
| crawl.no_orphan_key_pages (SITE) | 1.75 | ◐ | 크롤링 문서 — 발견은 링크 추적으로. 수치 VEO |
| crawl.crawlable_anchors | 1.5 | ● | Lighthouse SEO `crawlable-anchors` w1. 원인이라 결과(고아 1.75)보다 낮게 — 구글의 원인-무배점 설계와 같은 방향 |
| security.certificate_not_expiring (SITE) | 0.75 | ○ | 구글 근거 없음 — 운영 예방 항목, VEO 판단 |
| content.lazy_loading_safe | 0.75 | ◐ | 구글 lazy loading 문서("잘못 구현하면 검색에서 숨겨질 수 있다"). 수치 VEO |
| security.no_mixed_content | 0.75 | ○ | 브라우저 동작 근거 — 구글 배점 근거 없음, VEO 판단 |
| content.click_depth_reasonable (SITE) | 0.5 | ○ | **업계 통설** — 1.8.0 이 그 이유로 1→0.5 감액 |
| content.internal_link_density (SITE) | 0.5 | ○ | **업계 통설** — 같은 이유로 감액 |

S5 클릭·표현 (10 = URL 7 + SITE 3):

| 검사 | 배점 | 등급 | 구글 대응 |
|---|---:|:-:|---|
| onpage.meta_description_quality | 2 | ● | Lighthouse SEO `meta-description` w1 |
| sd.declared (SITE) | 2 | ◐○ | 리치 결과의 전제(구조화 데이터 문서). 단 **구글은 채점하지 않는다**(structured-data 수동, w0 실측) — 기회비용으로 채점하는 것은 VEO 판단 |
| sd.naver_supported_type | 2 | — | **구글 무관 — 네이버 근거**(오픈그래프). 국내 시장 판단 |
| sd.required_properties_present | 1 | ◐ | 리치 결과 요건 문서(필수 속성 없으면 미출력) |
| sd.jsonld_parses | 1 | ◐ | 같은 문서(문법 오류 시 무시) |
| sd.google_supported_type | 1 | ◐ | 지원 타입 목록 문서 |
| sitemap.discoverable (SITE) | 1 | ◐ | sitemap 문서(발견 개선, 보장 아님). 수치 VEO |

S6 위생 (5 = URL 2.4 + SITE 2.6) — 요점만:

| 검사 | 배점 | 등급 | 구글 대응 |
|---|---:|:-:|---|
| http.redirect_chain_sane | 0.75 | ◐ | 리다이렉트 문서. 수치 VEO |
| sitemap.urls_valid (SITE) | 0.75 | ◐ | sitemap 문서. 수치 VEO |
| crawl.no_broken_internal_links (SITE) | 0.6 | ○ | 구글은 404 자체를 결함으로 보지 않는다 — UX 근거의 VEO 판단 |
| onpage.descriptive_anchor_text (SITE) | 0.5 | ● | Lighthouse SEO `link-text` w1 |
| perf.tbt_lab | 0.5 | ● | 구글은 w30 — 그러나 그것은 **실험실이 INP 를 못 재서 쓰는 대역**. VEO 는 inp_field 로 원본을 읽으므로 낮게(같은 성질 이중 채점 방지) |
| perf.text_compression | 0.5 | ● | 구글 **w0**(원인 항목, 실측). 조치 구체성 때문에 최소 배점으로 남김 — 중복 채점임을 인정 |
| html.charset_declared | 0.3 | ● | Lighthouse 권장사항 `charset` w1 |
| content.breadcrumb_present (SITE) | 0.25 | ◐ | breadcrumb 구조화 데이터 문서 존재. 수치 VEO |
| content.pagination_signals (SITE) | 0.25 | ○ | **주의** — 구글은 rel=prev/next 를 색인에 쓰지 않는다고 밝혔다(2019). 판정 기준 재검토 후보(§5.3) |
| perf.modern_image_format · perf.resource_hints | 0.15×2 | ● | 구글 w0 원인 항목 — text_compression 과 같은 처리 |
| robots.txt_parses_cleanly (SITE) | 0.15 | ● | Lighthouse SEO `robots-txt` w1 |
| crawl.favicon_declared_and_crawlable (SITE) | 0.1 | ◐ | 파비콘 검색결과 표시 문서 |
| html.doctype_standards_mode | 0.05 | ○ | 구글 근거 없음 — 렌더링 위생, VEO 판단 |

### 5.3 대조가 남긴 다음 판(1.9.0+) 검토 후보 — 이번 판에서는 바꾸지 않는다

1. **title 의 상대 비중**(구글 8% vs VEO 30%) — 근거가 "대체 불가" 라는 VEO
   판단뿐이다. 네이버 가중이 실제 이유라면 명세에 그렇게 적어야 한다.
2. **pagination_signals** — 구글이 rel=prev/next 를 쓰지 않는다고 밝힌 뒤이므로,
   판정이 무엇을 보는지 확인하고 기준을 다시 세운다.
3. **h1·single_title·mixed_content 등 ○ 항목들** — 구글 근거가 없다는 사실이
   명세 reference_ko 에 적혀 있어야 다음 사람이 배점을 변호할 수 있다.

---

## 6. 기록해 둔 불일치 — v2 프로토타입 vs 실코드 평가기

단계(영역) 전체가 해당 없음일 때:

- **v2 프로토타입**: 그 단계 가중치를 잃는다(재분배 없음). `test_a_site_where_
  only_one_stage_applies_still_scores_out_of_100` 이 7.1 을 단언한다.
- **실코드 `evaluator.py`**: NOT_APPLICABLE 영역을 분모에서 빼고 재정규화한다
  (`scoreable` 가중 평균) — 같은 상황에서 100 이 된다.

둘 다 자기 시험을 갖고 있고 서로 모순된다. v3 은 과제 제약("같은 입력이면 v2 와
같은 사이트 점수")에 따라 사이트는 v2 를, 페이지는 평가기(재정규화)를 따랐다.

**결정(2026-08-02, 1.9.0 발행과 함께): 재정규화로 통일한다.** 근거는 ADR 0002 와
같다 — 해당 없음은 결함이 아니므로 0점처럼 굴어서는 안 되는데, 가중치를 잃게 두면
그 단계가 통째로 0점인 것과 같은 산수가 된다. 실코드 평가기는 처음부터 재정규화로
계산했으므로 발행된 점수는 하나도 바뀌지 않는다 — 어긋나 있던 것은 이 연구
프로토타입 쪽이고, v2 프로토타입과 그 시험(7.1 을 못박던
`test_a_site_where_only_one_stage_applies_still_scores_out_of_100`)을 이름째
바꿨다(0-I → `test_an_all_na_stage_renormalises_instead_of_costing_its_weight`).
실무에서 점수가 갈린 사례는 없었다.

---

## 7. 실구현 시 바꿔야 할 코드 — 우선순위

1. **수집기 부재검사 경로** (`apps/api/src/veo/seo/collectors/**`) — 결함이
   여기 있다. `no_duplicate_*`·`no_orphan`·`no_broken_links` 가 PASS 를 내기 전에
   `SampleScope.is_whole_site` 를 묻게 한다. 다중 페이지 잘린 크롤에서 UNKNOWN
   ("본 N장 중에는 없었다") + 무엇을 하면 판정되는지 문구.
2. **`collect/sample.py` 확장** — `absence_claim`(프로토타입 참조) 을 단일
   구현으로 추가. SEO·GEO 수집기가 같은 함수를 쓴다(0-D).
3. **page_results 저장** — `scan_runs` 에 페이지 단위 판정 스냅숏(검사×페이지
   상태, evidence 연결). 이미 evidence 에 URL 이 있으므로 재집계용 인덱스만
   필요하다. HANDOFF §4 의 "페이지별 측정 상태 저장" 과 같은 항목.
4. **평가기·명세** — `CheckStatus.NOT_SAMPLED` 추가(분모 제외 + 별도 표기),
   페이지 평가 진입점(`evaluate_page`), 명세 1.9.0 에 표본 정책 검사 목록 선언.
   발행본 1.8.0 은 불변(ADR 0012).
5. **API** — `GET /api/scans/{id}/pages` (페이지 점수 목록) ·
   `GET /api/scans/{id}/pages/{url}` (페이지 상세 = 페이지 점수 + SITE 값 날짜
   표기). 재크롤 없는 재집계.
6. **화면** — 상위 탭(사이트)/하위(페이지별), 사이트-페이지 차이 설명(SITE 손실
   목록 + 도달률), NOT_SAMPLED "표본 밖 — 요청 시 측정" 배지, SITE 값
   "YYYY-MM-DD 전체 진단 기준" 표기. 두 점수를 나란히 비교하는 UI 금지
   (methodology §2.9 경고).

---

## 8. 검증

```
cd veo && .venv/bin/python -m pytest \
  docs/research/prototypes/test_seo_scoring_v2.py \
  docs/research/prototypes/test_seo_scoring_v3_pages.py -q
→ 48 passed  (v2 24 + v3 24)
```

v3 시험이 고정하는 성질: 분해 항등식(임의 조합 200회, 1e-9) · v2 와 사이트 점수
동일(임의 조합 120회, 완전 일치) · 페이지 전부 100 인데 사이트가 낮으면 SITE
손실+도달률로 정확히 재구성 · 부재형 검사는 표본에서 PASS 불가, 덜 볼수록 점수
단조 비증가 · 페이지 관문 실패 = 0점 · 못 잰 페이지 관문은 차단을 지어내지 않음 ·
NOT_SAMPLED 는 순위 불변·경계 밖 사용 거부 · 배점 재분할 시 무관 페이지 불변 ·
SITE 값은 날짜를 달고 유지 · v3 배점표가 v2(=1.8.0)와 한 숫자도 다르지 않음.

---

## 9. 추가 설계 후보 — 템플릿 그룹 표본 (2026-08-02, 사용자 제안 + 실측 검증)

**제안(사용자).** 블로그형 페이지(칼럼·소식 등)는 수백~수천 장이 되지만 페이지별로
SEO 작업을 하는 것이 아니라 자동 생성이므로, **자동 생성(템플릿)만 측정하면 된다** —
나머지는 모두 같기 때문. 블로그형을 제외하면 200장을 넘는 사이트는 드물다.

**실측 검증 (chamsarang1075.com, 2026-08-02).**

```
172장 = 고정 페이지 37 + 게시판 칼럼 103(?uid= 쿼리) + news 9 + 기타
칼럼 무작위 3장: layout·JSON-LD·canonical 선언 완전 동일 (한 템플릿)
그리고 — title 세 장이 전부 같다: "참사랑한의원 칼럼 - 마산 참사랑한의원"
```

같은 물리 페이지가 uid 파라미터로 문서를 갈아 끼우는 게시판 플러그인이라 템플릿
동일성이 **구조적으로 보장**된다. 진단이 잡은 title 중복 127장·canonical 문제
103장의 원인이 이 템플릿 결함 하나다. **표본 3장이면 103장의 결함을 잡는다** —
breadth 지수 0.7 의 근거("결함은 템플릿 단위")가 측정 쪽에서도 성립함을 보였다.

**구글 정합.** Search Console CWV 가 정확히 이 방식이다 — URL 을 템플릿 그룹으로
묶고("similar user experience… common framework"), 그룹 하나로 판정한다(§5.1).

**설계 방향 (1.9.0, 2단계 측정 범위 정책과 한 판).**

1. **그룹 감지** — URL 모양(경로 접두, `?uid=` 류 쿼리 패턴)으로 후보를 묶고,
   **뼈대 동일성(레이아웃·head 구조 해시)을 확인한 뒤에만** 그룹으로 인정한다.
   확인에 실패하면 그룹을 해체하고 전량 측정으로 돌아간다 — 오판이 일반화되면
   표본의 결함이 무고한 페이지에, 무고한 표본이 결함 페이지에 씌워진다.
2. **크롤 정책** — 고정 페이지는 전부 + 그룹당 표본 K장(명세 고정). 수천 글
   사이트가 200장 예산 안에 들어온다.
3. **채점** — 템플릿이 내보내는 속성(canonical 구조·title 패턴·뷰포트·JSON-LD)은
   표본 판정을 그룹 전체로 일반화(coverage = 그룹 크기), 화면에 "표본 K장 기준"
   명시. 콘텐츠 의존 속성(본문 빈약·alt 습관)은 그룹 경향으로만 보고.
4. **부재형** — 그룹 안 부재는 표본+뼈대 동일성으로 판정 가능해진다. 사이트
   전역 비교(그룹 간 중복 등)는 여전히 전량이 필요하나, title 같은 소량 필드는
   저비용 수집(title-only fetch)로 채우는 길이 있다.
5. **조작 유인 없음** — 표본 선정이 명세 고정이므로 perf_lab·NOT_SAMPLED 와 같은
   논리 위에 선다.

**검증 필요 가정** — "블로그형 제외 시 200장 초과는 드물다". chamsarang 은 고정
37장으로 부합. 표본 8도메인 전체가 100장 상한에 걸렸으므로 고정/블로그 비율을
더 확인해야 한다.
