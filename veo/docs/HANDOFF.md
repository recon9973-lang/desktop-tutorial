# 인수인계 — 2026-08-01

새 대화를 여는 사람이 **이 문서 하나만 읽고** 이어갈 수 있도록 적는다.
지난 세션이 아주 길어져 맥락이 잘렸고, 결정과 근거를 대화가 아니라 파일에 남긴다.

---

## 0. 먼저 읽을 것 (순서대로)

1. `docs/research/VEO_CLAUDE_DEVELOPMENT_MASTER_PROMPT.md` 의 **0-A ~ 0-J**
2. `docs/architecture/requirements-traceability.md`
3. 이 문서
4. 필요하면 `docs/research/SEO_SCORING_ALGORITHM_V2.md` (부록 C 가 최신 결정)

**작업 전에 매번 세 가지를 먼저 말한다** — 전체 목적 / 무엇을 만드는가 / 지켜야 할 원칙.
눈에 걸리는 것부터 고치다 방향을 잃은 적이 있어서 만든 규칙이다.

---

## 1. 지켜야 할 제약 (변하지 않음)

- **사용자는 개발자가 아니다.** 한국어로, 전문 용어를 풀어서 설명한다.
- **비밀 값을 대화창에 출력하지 않는다.** 스크립트도 값을 찍지 않는다.
  `veo/.env` 는 0600 이고 gitignore 되어 있다.
- **자격증명이 없으면 그럴듯한 값을 지어내지 않는다.** 명시적 픽스처와 "공급자 비활성".
- SSRF 방어 · 조직 간 격리 · 자격증명 보호는 타협 대상이 아니다.
- **하위 에이전트·워커의 보고를 믿지 말고 직접 확인한다.**
- **Claude 는 `git push` 가 막혀 있다.** 사용자가 직접 실행해야 한다.
- N/A 는 분모에서 빼고, UNKNOWN 은 분모에 남긴 채 0점.
- 모든 숫자는 `packages/scoring-specs` 의 발행 명세에만 있다.
- GEO 준비도와 AI 관측은 분리된 채로 둔다.
- 로그인 폼에 비밀번호를 입력하는 것은 금지된 행동이다 — 로그인이 필요한 화면은
  브라우저로 검증하지 않는다.

### 자주 틀리는 것

- **명세 디렉터리 환경변수는 `packages/scoring-specs` 를 가리킨다** (그 아래 `specs` 가
  아니다). `VEO_SCORING_SPECS_DIR=/절대경로/veo/packages/scoring-specs`
- 시험은 `apps/api` 에서 돌린다. mypy 도 거기서.
- ruff 는 저장소 루트(`veo/`)에서 `ruff check apps/api packages`.
- 웹은 **빌드까지** 돌려야 한다: `pnpm --filter @veo/web verify`
  (타입체크·시험이 통과해도 `next build` 가 깨진 적이 있다)

---

## 2. 지금 상태

### 이번 세션에 한 일

```
9a263db  유료 호출을 세기 시작한다 — 한도까지 얼마나 남았는가
e19da76  PageSpeed 를 실제로 부른다 — 어댑터에 호출자가 생겼다
9dba228  성능 표본 정책 — 덜 재서 이득 보지 못하게 한다
253d2bd  PageSpeed 는 키가 있어도 측정되지 않는다 — 인수인계 정정
b345084  인수인계 — 새 대화가 이 문서 하나로 이어지게 한다
e4e7513  0점의 이유를 화면에 적는다 — 도달률과 확인 못 한 관문
4c1e6c0  명세 1.8.0 — 검색 여정 여섯 단계로 채점한다
b2ea43a  검사를 더해도 분모가 자라지 않는다 — 검사별 배점과 고정 분모
eb88cc6  앞이 막히면 뒤는 무의미하다 — 관문 영역을 곱셈으로 계산한다
155e56a  메뉴가 자바스크립트뿐인 사이트와 인코딩을 선언하지 않은 사이트를 잰다
09dfc58  점수 알고리즘 v2 — 단계 안에서도 분모가 움직이고 있었다
0820b91  키를 주소에 실어 보내고 있었고, 제한시간은 첫 진단마다 걸렸다
e89b8eb  구글 Lighthouse 158개 감사를 VEO 명세와 대조했다
```

**배포(subtree push)는 아직 안 했을 수 있다.** 아래 §6 참조.

### 점수 체계가 바뀌었다 — 명세 1.8.0

채점 영역이 **검색 여정 여섯 단계**로 재편됐다. 앞 단계일수록 손실이 크다.

| 단계 | 원배점 | 환산 | 성격 |
| --- | ---: | ---: | --- |
| `s1_blocked` 색인 차단 | 30 | — | **관문. 곱한다** |
| `s2_identity` 대표 URL 혼란 | 15 | 21.4 | |
| `s3_meaning` 해석 불가 | 20 | 28.6 | |
| `s4_compete` 경쟁력 | 20 | 28.6 | |
| `s5_click` 클릭·표현 | 10 | 14.3 | |
| `s6_hygiene` 위생 | 5 | 7.1 | |

연동이 있어야 잴 수 있는 세 영역(`search_engine_integration`, `observability_outcomes`,
`offpage_entity`)은 그대로 **점수 밖**이다.

계산식:

```
도달률 = 관문 영역의 곱(1 - 상태배수 × 범위)
점수   = 도달률 × Σ(영역점수 × 가중치) / Σ(채점 가능 가중치)
그 뒤 상한(cap) 적용
```

**못 잰 관문은 곱하지 않는다**(없는 차단을 지어내지 않는다, 0-A).
**못 잰 품질 항목은 배점을 잃는다**(ADR 0016). 방향이 반대인 것이 설계의 핵심이다.

### 픽스처 점수 (1.7.0 → 1.8.0)

```
sitewide_noindex        25.00 →  0.00
render_gap              35.00 → 21.94
duplicate_metadata      47.32 → 41.18
healthy                 95.31 → 89.24   (제공자 전부 연결 시 100.0 유지)
cross_domain_canonical  40.00 → 40.00
broken_jsonld           70.48 → 72.32
orphan_page             65.63 → 70.72
brochure_na             69.28 → 78.89
```

---

## 3. 이번 세션에서 배운 것 (반복하지 말 것)

### 상태를 못 박는 시험은 반드시 정상적인 개정을 막는다

**하루에 네 번 같은 실수를 했다.**

- "발행된 명세는 관문을 선언하지 않는다" ← 그날 아침 내가 쓴 시험
- "발행된 명세는 배점을 쓰지 않는다"
- "crawl_indexability 가중치는 31.25 다"
- "structured_data 영역 점수가 0 이다"
- (이전 세션) "`spec.version == "1.6.0"`" ← 명세 발행 자체를 막고 있었다

전부 **그날의 사실**이지 성질이 아니었다. 시험은 "지금 이런 상태다" 가 아니라
"이런 성질이 유지된다" 를 확인해야 한다.

### 수집기 묶음 ≠ 채점 영역

둘이 1:1 이었던 것은 **우연**이다. 수집기는 *무엇을 어떻게 재는가*로 묶이고
(HTML 파싱끼리, 크롤 구조끼리, 제공자 API 끼리), 채점 영역은 *결함이 검색에 어떻게
작용하는가*로 묶인다. 같은 성능 수집기가 재는 CLS 는 '경쟁력', TBT 는 '위생' 단계다.
`SEO_COLLECTORS` 로 이름을 바꿨고, 계약 시험은 "재는 사람 없는 검사가 없고 두 번 재는
검사도 없다" 를 본다.

### 같은 값을 세는 곳이 여럿이면 하나만 고쳐도 나머지가 조용히 틀린다

가중치 합을 네 곳(평가기 1 + 시험 3)에서 각자 계산하고 있었다.
`ScoringSpec.scoring_weight_total` 로 모았다.

### 구글도 틀린다 — 따라 하면 안 되는 것

Lighthouse 는 **못 잰 것을 실패로 적는다.** robots.txt fetch 타임아웃이 0점으로
기록되고, 화면에서 "크롤러를 막고 있음" 과 구분되지 않는다. 같은 사이트가 잴 때마다
SEO 1.00 과 0.92 를 오간다. **이것이 VEO 와 구글의 진짜 차이이고, 잃으면 안 된다.**

### 시험이 상한(cap)에 가려질 수 있다

배점 비율을 재려던 시험 둘이 25점 상한에 눌려 6점짜리와 3점짜리가 같은 값이었다.
배점을 재는 시험은 상한 없는 사본에서 재야 한다.

---

## 4. 남은 일 (우선순위 순)

### 가. 사용량을 보는 화면이 없다 — **지금 가장 급하다**

기록은 쌓이기 시작했는데 **읽을 곳이 없다.** 한도(하루 25,000회)에 다가가는 것을
아무도 모르고, 넘고 나서야 "성능이 전부 측정 불가" 로 드러난다.

`/console/usage` 화면이 이미 있다. 거기에 붙이면 된다.
경보도 필요하다 — 일정 비율을 넘으면 알려야 한다. 넘고 나서 알면 늦다.

관련: `was_cache_hit` 컬럼이 NOT NULL 이라 "모른다" 를 담을 수 없다. 지금은 호출
횟수만 세므로 미뤄 뒀지만, **캐시 비율을 지표로 쓰기 시작하면 반드시 먼저** nullable
로 바꾸는 마이그레이션이 필요하다. 코드 주석에 적어 뒀다.

### 나. 배포 후 실제 콘솔에서 성능이 나오는지 확인

로컬에서는 확인했다. Railway 에 키가 제대로 들어갔는지는 화면으로만 알 수 있다.
안 나오면 환경변수 이름(`VEO_GOOGLE_PAGESPEED_API_KEY`)부터 본다.

### 다. 등급 구간 재검토 — **근거 없이 유지 중**

`bands` 는 1.8.0 에서 손대지 않았다(ready 90+/good 75+/at_risk 50+/poor 25+/blocked 0+).
절대 평가에서 구간을 점수에 맞춰 옮기면 절대 평가가 아니므로 **그대로 둔 것이 옳다.**
다만 실제 고객 사이트 표본으로 한 번은 확인해야 한다 — "준비 완료" 를 받는 사이트가
현실적으로 존재하는가.

### 라. #37 구글 400 오분류 — 고객이 조치할 수 없는 문구

400 하나에 원인이 둘인데 구분하지 않는다.

```
키가 잘못됐다        → 우리가 고칠 일     (details[].reason == API_KEY_INVALID)
대상 사이트를 못 열었다 → 고객에게 알릴 정보  (FAILED_DOCUMENT_REQUEST)
```

둘 다 "Google 응답 형식이 VEO가 아는 형식과 다릅니다" 로 나온다.
`providers/google/errors.py:205` `classify_status` 가 401/403/429/5xx 만 분기한다.
**네이버 쪽 같은 이름의 함수에는 4xx 분기가 이미 있다**(`providers/naver/errors.py:241`).

**배선이 끝난 지금 이것이 더 중요해졌다** — 실제로 400 이 나가기 시작했다.

### 마. 조직별 자격증명 · 요청 본문 신뢰

- `pagespeed_from_vault` 가 있는데 안 쓴다. 지금은 **전역 키 하나를 모든 조직이 공유**한다.
- `/seo/scan`(이미 수집된 자료 채점)이 요청 본문의 `provider_states` 를 믿는다.
  클라이언트가 "이 제공자 켜졌다" 고 주장할 수 있다. 조직 간 격리 관점에서 재검토.
  (콘솔이 쓰는 `/seo/scans` 는 서버가 스스로 읽으므로 문제없다.)

### 바. #39 "구글은 SEO 100점 주는데" 영업 근거 정리

구글 SEO 카테고리는 **11개(자동 채점 10개), 그것도 입력한 URL 1장만** 본다.
실측 목록은 `docs/research/LIGHTHOUSE_COMPARISON.md` §3.
가장 뾰족한 예: 구글은 canonical 을 통과시켰고, VEO 는 100페이지를 훑어 40장에서
문제를 찾았다. **구글이 틀린 게 아니라 본 페이지 수가 다르다** — 이 표현을 그대로 쓸 것.

### 사. #38 에이전트형 브라우징 — 제품 판단 필요

구글이 Lighthouse 에 `AGENTIC_BROWSING` 카테고리를 만들었다(개발 중이라 명시).
배점 있는 항목은 실질 2개(접근성 트리, CLS)뿐이고 **llms.txt·WebMCP 는 배점 0** 이다.
VEO GEO 준비도와 겹치므로 판단이 필요하다.

### 아. #8 헤드리스 렌더링 — `js_render_parity` 를 실제로 측정

지금 UNKNOWN 이고, **이 검사는 관문(S1)에 있다.** 못 잰 관문은 곱하지 않으므로
점수를 죽이지는 않지만, 화면에 "확인하지 못함" 으로 계속 남는다.

### 자. 그 밖

- 다른 제공자(OpenAI·네이버)도 사용량 기록. OpenAI 는 토큰·비용이 실제로 들어
  `input_tokens`/`output_tokens`/`cost_krw` 를 채워야 한다.
- #29 tests/contract·e2e·integration·security 디렉터리 검증
- #9 추이·회귀 알림 / #10 담당자 배정 / #11 인쇄·PDF / #12 목차 고정

### 차. 이전에 결정했으나 아직 안 한 것

- **페이지별 점수 코너** — 전체 크롤은 유지하고, URL 범위 검사만으로 페이지별 점수를
  따로 보여준다. 페이지별 측정 상태를 저장해 재로그인 후에도 이어볼 수 있어야 한다.
- **추가 항목 분리 표시** — `80 + 1` 또는 `80 / 1`. **81점이 아니다.**
  합산하면 `92+8=100` 과 `100+0=100` 이 같아 보이는데, 앞의 사이트는 검색에 직접 영향
  있는 결함이 8점어치 남아 있다. 보안 헤더 6종 등 점수 밖 항목이 생긴 뒤에 한다.
- 조치를 **붙여넣을 수 있는 코드**로 (`fix_recommendations.code_example`)
- 사이트맵 `observed_value={}` 채우기
- OG 검사 이름을 `seo.sd.*` → `seo.social.*`
- 카카오/페북 공유 미리보기 검사

## 5. 자격증명 상태

| | 상태 |
| --- | --- |
| 네이버 SearchAd / DataLab | 있음 |
| OpenAI | 있음 |
| **Google PageSpeed** | 있음. **배선 완료 — 실제로 잰다** |
| Google Search Console | 없음 |
| CrUX 단독 API | **켤 필요 없음** — 실사용자 데이터는 PageSpeed 응답에 함께 온다 |

### PageSpeed — 이제 실제로 잰다 (작업 #44 완료)

키가 있는데도 성능이 측정 불가였던 이유는 **스캔 파이프라인이 어댑터를 부르지 않아서**
였다. 어댑터는 완성돼 있고 시험도 있었지만 호출자가 0건이었다. 2026-08-01 에 배선했다.

실측 (chamsarang1075.com, 8장 크롤):

```
크롤       8장   7.4초
성능 측정  5장  25.3초  (병렬)
LCP FAIL / CLS PASS / TBT PASS / INP 해당없음 · 점수 88.57
```

**표본 정책이 먼저다.** 실험실 성능은 한 장에 16~60초라 다 잴 수 없다. 명세가 정한다:

```
sampling.perf_lab.max_urls            5     중요도 상위 몇 장
sampling.perf_lab.min_measured_ratio  0.6   계획한 표본 중 최소 이만큼
sampling.perf_field.prefer_origin_scope true 사이트 전체 값 우선
```

문턱을 못 넘으면 검사는 **측정 불가**이고 배점을 잃는다 — 덜 재서 이득 볼 수 없다.
이 문턱이 없으면 **너무 느려서 로드에 실패한 페이지가 분모에서 빠져 사이트가 더 빨라
보인다.** 실제로 Lighthouse 가 `FAILED_DOCUMENT_REQUEST` 로 페이지를 못 여는 사례가
나왔고, 못 여는 이유는 대개 느려서다 — 편향이 우리에게 유리하게 걸린다.

**실사용자 지표에는 표본 문제가 없다.** 구글이 같은 응답에 사이트 전체 값을 함께 준다
(실측 seoul.go.kr: 페이지 값 LCP 1041ms·INP 96ms / 사이트 전체 LCP 1011ms·INP 122ms).
어댑터가 그것을 버리고 있었고, 이제 `PageSpeedResult.origin_field` 로 읽는다.
범위는 섞지 않는다 — 사이트 전체 값은 방문 많은 페이지가 지배하므로 특정 URL 에 붙이면
그 URL 이 겪지 않은 트래픽으로 칭찬하게 된다.

표본을 고르는 함수는 `lab_sample` **하나뿐**이다. 재는 쪽과 채점하는 쪽이 각자 고르면
"잰 페이지" 와 "재려던 페이지" 가 어긋나고, 그 어긋남은 조용히 점수를 올린다.

### 사용량 — 세는 것은 돈이 아니라 횟수다 (작업 #28 완료)

PageSpeed 는 하루 25,000회 무료라 돈은 안 든다. **넘기면 그날의 모든 고객 진단에서
성능이 측정 불가가 된다.** 진단 한 번에 최대 5회이므로 이론상 하루 5,000회가 한계다.

`cost_krw = 0` 은 **정말 0원**이라는 뜻이다. 값을 모르는 제공자는 `None` 으로 둔다 —
0 과 None 을 섞으면 "공짜라서 0" 과 "몰라서 0" 이 같은 자리에 앉는다.

캐시 여부는 추측하지 않는다. `analysisUTCTimestamp` 가 우리 요청보다 앞서면 새로 돌린
것이 아니다. 근거가 없으면 `None` — "새로 쟀다" 와 "모른다" 는 다른 사실이다.

**기록은 쌓이는데 볼 화면이 없다.** 아래 §4 가 참조.

## 6. 배포

브랜치는 원격에 올라가 있다(`e4e7513`). **배포용 subtree push 가 남았다.**

```bash
cd /Users/leejae-hoon/Desktop/desktop-tutorial && git subtree push --prefix=veo veo-platform main
```

Railway 가 `alembic upgrade head` 를 자동으로 돌린다(`preDeployCommand`).
이번 변경에 마이그레이션은 없다 — 명세와 계산만 바뀌었다.

**배포 후 확인할 것:** 콘솔에서 사이트 하나를 진단해 점수가 1.8.0 기준으로 나오는지,
그리고 색인이 막힌 사이트에서 새 안내 문구가 보이는지.

---

## 7. 검증 명령 모음

```bash
# API 시험 (apps/api 에서)
VEO_SCORING_SPECS_DIR=/Users/leejae-hoon/Desktop/desktop-tutorial/veo/packages/scoring-specs \
  ../../.venv/bin/python -m pytest tests -q

# 타입 (apps/api 에서)
../../.venv/bin/python -m mypy

# 린트 (veo/ 에서)
.venv/bin/python -m ruff check apps/api packages

# 웹 — 빌드까지 (veo/ 에서)
pnpm --filter @veo/web verify

# 점수 알고리즘 성질 시험 24개 (veo/ 에서)
.venv/bin/python -m pytest docs/research/prototypes/test_seo_scoring_v2.py -q
```

---

## 8. 참고 문서

| 파일 | 무엇 |
| --- | --- |
| `docs/research/SEO_SCORING_ALGORITHM_V2.md` | v2 설계·검증·결정 (부록 C 가 최신) |
| `docs/research/LIGHTHOUSE_COMPARISON.md` | 구글 158개 감사 대조, 배점 근거 |
| `docs/research/prototypes/seo_scoring_v2.py` | 배점표 참조 구현 |
| `docs/research/prototypes/test_seo_scoring_v2.py` | 알고리즘 성질 시험 24개 |
| `packages/scoring-specs/specs/veo.seo.readiness/1.8.0.yaml` | 발행 명세 (changelog 에 근거 전부) |
| `apps/api/tests/scoring/test_gate_categories.py` | 관문 시험 |
| `apps/api/tests/scoring/test_fixed_denominator.py` | 고정 분모·배점·범위 지수 시험 |
| `apps/api/tests/seo/test_charset_and_anchors.py` | 새 검사 둘 (무엇을 세지 **않는가**가 절반) |
