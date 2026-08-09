# AI 답변 관측 엔진 — 기준 문서

**③ AI 답변 관측**이 무엇을 어떻게 재는가. SEO 쪽의 `docs/scoring/methodology.md` 와 같은
자리다.

**모든 숫자는 2026-08-08 에 명령을 실행해 얻었다.**

---

# 0. 한 문장

**AI 에게 실제로 물어보고, 그 답변에 우리 거래처가 나오는지 센다.**

②GEO 준비도와 헷갈리면 안 된다(ADR 0003).

| | ② GEO 준비도 | ③ AI 답변 관측 |
|---|---|---|
| 대상 | **우리 사이트**를 뜯어본다 | **AI 에게 묻는다** |
| 결과 | 점수 0~100 | 관측 기록 (몇 번 중 몇 번) |
| 비용 | 없음 | **호출마다 돈** |
| 실행 | SEO 와 함께 자동 | 사람이 시작 · 정기 예약 |

**두 값을 하나의 점수로 합치지 않는다.** 어느 화면에서도.

---

# 1. 흐름

```
① 브랜드 신원        누가 우리인가          brand_identities
      ↓              (동명 업체를 가르는 근거)
② 질문 집합          무엇을 묻는가          prompt_sets · prompts
      ↓              (균형이 검사된다 — ADR 0015)
③ 엔진·모드 선택     누구에게 묻는가
      ↓
④ 실행               실제 호출 · 반복        observation_runs · ai_answers
      ↓
⑤ 판정               언급했나 · 인용했나     entity_mentions · citations
      ↓
⑥ 검수               사람이 확인             claim_assessments
      ↓
⑦ 지표               노출률 · 인용률         (분모를 고르는 일)
```

각 단계의 코드:

```
① brands/ · observations/brand_identity.py
② observations/prompts.py · question_sources.py
③ observations/providers/registry.py
④ observations/runner.py (727줄) · execution.py (633줄)
⑤ observations/detection/ (mentions · citations · disambiguation · competitors)
⑥ observations/review/ (queue · decisions · gating) · review_service.py
⑦ observations/metrics.py (465줄) · sampling.py (339줄)
    risk/ (assessment · entailment · taxonomy) · findings.py
```

---

# 2. ① 브랜드 신원 — 누가 우리인가

한국 병원 상호는 겹친다. **`서울치과` 는 수십 곳이고, 고유한 이름조차 더 긴 상호에
통째로 들어간다.** 실측: `온담한의원` 을 찾으면 검색 1위가 `백세온담한의원` 이었다.

그래서 이름만으로는 확정하지 않는다.

```
저장하는 것 (brand_identities)
  display_name          정식 상호
  aliases               줄임말·옛 상호·영문
  own_domains           자사 도메인      ← 확정 근거 중 가장 셈
  address_terms         행정동·역명·랜드마크
  phone_numbers         대표번호        ← 흔한 상호를 확정선 위로 올리는 유일한 항목
  distinguishing_terms  원장명·진료과목·그 밖
  name_is_ambiguous     이름이 흔한가
```

**`identity_strength` 가 요점이다.** `INSUFFICIENT` 면 그 브랜드의 언급은 **전부 검수
대기로 넘어간다** — 확정할 수 없기 때문이다.

## 2-A. 공유 도메인은 거부된다 (v0.3.68)

`blog.naver.com` 은 네이버 블로그 **전체**가 함께 쓴다. 자사 도메인으로 저장되면 AI 가
아무 블로그를 인용해도 우리 업체 인용으로 잡힌다 — **없는 노출이 생기고, 고객에게
유리한 방향이라 아무도 이의를 제기하지 않는다.**

```
막는 곳   brands/domains.py · SHARED_HOSTS
          POST·PATCH 양쪽에서 막는다 (만들 때만 막으면 보완 경로로 들어온다)
받는 것   주소를 통째로 붙여넣어도 된다 — https://ondam.kr/about → ondam.kr
```

## 2-B. 비대칭이 점유율을 조용히 틀어놓는다

우리 쪽만 꼼꼼히 채우고 경쟁사는 이름만 적으면, **경쟁사 언급이 더 자주 검수 대기로
떨어져 분자에서 빠지고, 산술을 한 글자도 안 고치고 우리 점유율이 오른다.**
그래서 화면은 자사와 비교 대상을 같은 자리에 두고 `asymmetry_ko` 로 경고한다.

---

# 3. ② 질문 집합 — 무엇을 묻는가

## 3-A. 균형은 주장이 아니라 검사된다 (ADR 0015)

> 경쟁 비교를 조작하는 데 숫자를 위조할 필요가 없다. **질문만 고르면 된다.**
> 고객이 잘 나오는 "서초 임플란트 잘하는 곳" 은 묻고, 잘 안 나오는 "임플란트 부작용" 은
> 뺀다. 이후 모든 계산은 산술적으로 완벽하고 결론은 거짓이다. 그리고 이 실패는 데이터에
> 아무 흔적을 남기지 않는다.

```
MIN_PROMPTS_PER_SET      5      이보다 적으면 그 몇 개가 곧 결론이 된다
MAX_SINGLE_INTENT_SHARE  0.5    한 의도가 절반을 넘으면 그 의도 하나를 잰 것
MAX_BRAND_SUBJECT_SHARE  0.5    상호가 든 질문은 언급이 거의 보장 — 노출이 아니라 회상
REQUIRED_INTENTS         TRUST · COMPARISON
                                브랜드가 가장 빼고 싶어 하는 둘
```

**이 넷은 [설계 판단]이다.** 통계에서 나온 값이 아니라 2026-07-28 에 정했다. ADR 도 왜
5이고 왜 50%인지는 적지 않았다. 바꾸려면 ADR 을 고쳐야 하고, 그때 그 숫자여야 하는 이유를
대야 한다(`tests/test_thresholds_cite_a_decision.py` 가 강제).

의도 7종 — 정의 · 방법 · 추천 · 비교 · 가격 · 지역 · **신뢰·안전(부작용·후기)**

## 3-B. 질문은 가져오는 것이지 지어내는 것이 아니다 (v0.3.67)

```
observations/question_sources.py

  네이버 지식iN    kin.json · display=100 · title · 태그제거 · 5자 이상
                   [실측] "마산 교통사고 한의원" → 전체 118건 중 90건
  구글 관련 질문   SerpAPI engine=google&hl=ko&gl=kr · related_questions
                   [실측 2026-08-08] 열쇠 없음 → DISABLED_NO_CREDENTIAL 로 목록에 남음
```

**못 쓰는 출처를 목록에서 빼지 않는다.** 빼면 "여기 있는 게 전부" 로 읽히고, 열쇠만
넣으면 얻을 수 있었던 질문을 아무도 모른 채 지나간다.

**의도·퍼널을 기계가 자동 배정하지 않는다.** 질문은 실제로 수집한 것인데 분류를 기계가
지어내면, 그 분류가 균형 판정을 통과시킨다. 고르는 것은 사람이 한다.

**중복 예외** — 같은 수집을 ERP 환자질문분석(PAA)이 이미 한다. 0-D 위반이며 사장님이
2026-08-08 에 명시적으로 허용했다("veo가 별도로 완전하게 작동했으면"). ERP 방식을 소스
대조해 그대로 따랐고 다른 곳만 코드에 적었다.

---

# 4. ③④ 엔진과 실행

## 4-A. 아는 엔진을 전부 돌려준다

```
OPENAI · ANTHROPIC · GOOGLE_GEMINI · PERPLEXITY   (어댑터 4개)
[실측 2026-08-08] 열쇠가 있는 것: OPENAI 하나
```

못 쓰는 엔진도 상태와 함께 목록에 남는다(ADR 0004) — 빼면 "여기 있는 게 전부" 로 읽힌다.

## 4-B. 인용을 돌려주는 모델은 정해져 있다

```
[실측 2026-07-30] 같은 질문 · web_search 도구 부착
   gpt-5        url_citation 6개   ← 돌려준다
   gpt-4o       url_citation 2개   ← 돌려준다
   gpt-4.1      0개                ← 못 돌려준다
   gpt-4o-mini  0개                ← 못 돌려준다 (검색은 실행됨: 입력 23 → 8,174 토큰)
```

**목록에 없는 모델로 재면 인용 지표는 0 이 아니라 측정 불가다.** 넓히는 절차:
`docs/operations/verifying-citation-support.md`

## 4-C. 도구를 붙였다고 검색이 도는 것이 아니다 (v0.3.63)

```
[실측 2026-08-08] gpt-4o · 같은 web_search 도구
   "임플란트 붓기 며칠"      output=['message']                    입력    319 토큰
   "베놈애드는 어떤 회사" ×3  output=['web_search_call','message']  입력 17,286/17,310/21,504
```

모델이 그때그때 정한다. 검색을 건너뛴 답변을 `STRUCTURED` + `citations=()` 로 적으면
**"찾아봤지만 인용하지 않았다"** 가 된다. 사실은 "찾아보지도 않았다" 이고, 거래처에 주는
지시가 정반대다 — 앞은 "경쟁사에 밀렸다", 뒤는 "이 질문은 검색으로 안 간다".

**그래서 응답에 `web_search_call` 이 있을 때만 인용을 센다.**

## 4-C-2. 검색 켬과 끔은 서로 다른 조건이다 (v0.3.71)

한 실행에서 두 모드를 나란히 잰다. 둘은 **다른 질문에 대한 답**이라 서로를 대신하지
못한다.

```
검색 켬 (BROWSING)      지금 검색하면 우리가 나오는가
검색 끔 (NO_BROWSING)   AI 가 학습한 것만으로 우리를 아는가
```

**실행 계획의 칸은 (엔진, 모델, 검색모드) 셋이다.** `RunConditions.slot` 이 그 셋을
문자열로 만든다. 저장 쪽이 처음부터 그 셋으로 유일했으므로(`ai_engines`, ADR 0010)
계획도 같은 축이어야 한다.

**엔진 이름 하나로 묶으면 뒤엣것이 앞엣것을 덮는다.** v0.3.70 까지 `execute()` 는
엔진 이름을 열쇠로 하는 표를 받았다. 같은 엔진을 두 모드로 넣으면 하나가 사라졌고,
사라졌다는 사실이 어디에도 남지 않았다 — 요청은 두 모드, 실행은 한 모드, 화면에는
"두 모드를 쟀다". v0.3.71 에서 표를 **목록**으로 바꿨다. 겹칠 열쇠가 없으면 겹치지
않는다. 같은 칸이 두 번 들어오면 합치지 않고 거절한다(반복은 `repetitions` 로 늘린다).

**끌 수 없는 엔진이 있다.** Perplexity 는 요청마다 검색한다. 예전에는 호출자가 말한
모드를 그대로 기록했으므로, 끔으로 요청하면 검색해서 나온 답이 "검색 끔" 으로
저장됐다. 이제 `HttpAnswerProvider.ask` 가 호출 전에 거절한다.

```
supports_search_off   OPENAI · ANTHROPIC · GEMINI  = 참
                      PERPLEXITY                   = 거짓
```

이 값은 `/api/observations/engines` 가 `supports_search_off` 와 `search_off_note_ko`
로 돌려준다. **화면이 엔진 이름으로 알아맞히지 않는다** — 알아맞히는 목록은 엔진이
늘 때 조용히 틀리고, 틀린 결과는 "검색 끔" 이라 적힌 검색한 답변이다.

**호출 수는 모드 수만큼 늘어난다.** 질문 × 반복 × 모드. 실행 폼의 비용 줄이 이 곱을
그대로 보여준다.

## 4-D. AI 답변은 매번 다르다 — 반복이 표본이다

```
[공식 문서] OpenAI Cookbook
   "The Chat Completions and Completions APIs are non-deterministic by default"
   seed 를 고정해도 "Determinism is not guaranteed."

[실측 2026-08-08] gpt-4o · 완전히 같은 질문 3회
   인용 7개 / 7개 / 10개 · 입력 17,286 / 17,310 / 21,504 토큰
```

```
반복 3회 미만    비율을 아예 내지 않는다
반복 5회 이상    경쟁사 비교 보고에 실을 수 있다
반복 간격        기본 120초 (연속으로 던지면 제공자 캐시가 걸릴 수 있다)
```

## 4-E. 중단 사유는 기록된다

```
runner.py · StopReason
   BUDGET_EXCEEDED       예산 상한 도달
   COST_UNMEASURABLE     비용을 못 재서 중단 — 상한을 건 실행은 금액을 모른 채 못 돈다
```

**부분 실행도 그대로 남긴다.** `executions_planned · attempted · valid · skipped` 를 함께
저장한다 — `executions_valid` 만 보면 절반만 실행된 관측이 완전한 측정처럼 읽힌다.

---

# 5. ⑤ 판정 — 언급과 인용

```
detection/mentions.py         답변 본문에 상호가 나왔나
detection/disambiguation.py   그것이 정말 우리인가 (동명 업체 가르기)
detection/citations.py        url_citation 에서 우리 도메인이 나왔나
detection/competitors.py      경쟁사 언급
detection/normalize.py        표기 정규화
```

**확정 근거의 세기** — 도메인 인용 > 전화번호 > 소재지 + 구별표현 > 이름만.
이름만으로 확정되지 않으면 **검수 대기**로 넘어간다. 0으로 세지 않는다.

`?utm_source=openai` 는 저장할 때 뗀다(v0.3.61). 안 떼면 같은 페이지가 엔진마다 다른
주소가 되어 "우리 어느 페이지가 인용됐나" 를 이을 수 없다.
[실측] 실제 관측 4건 중 3건에 붙어 있었다.

---

# 6. ⑥ 검수 — 사람이 확인

```
review/queue.py       대기 목록 (DB 에 있다 — 재기동해도 살아남는다)
review/decisions.py   확정 · 반려
review/gating.py      검수를 안 거친 것은 발행되지 않는다
risk/assessment.py    답변이 우리에 대해 한 주장의 위험 판정
risk/entailment.py    그 주장이 근거에서 나오는가
risk/taxonomy.py      위험 분류
findings.py           위험 판정을 claim_assessments 로
```

`identity_strength` 가 부족한 브랜드의 언급은 전부 여기로 온다.

---

# 7. ⑦ 지표 — 분모를 고르는 일

`metrics.py` 의 첫 문장: **"이 모듈이 하는 일은 분모를 고르는 것뿐이다."**

```
노출률(언급)   몇 번 물어서 몇 번 나왔나
인용률         몇 번 중 몇 번 우리 페이지가 근거로 쓰였나
점유율(SoV)    비교 대상 대비
```

**비율은 맨숫자로 내지 않는다(ADR 0013).** 표본이 작으면 소수점을 줄이고 방향성으로
표기하며, Wilson 구간 같은 이항 신뢰구간을 함께 붙인다.

**인용을 못 돌려주는 모델의 답변은 인용률 분모에서 빠진다.** 0으로 세면 "AI 가 당신을
한 번도 인용하지 않습니다" 라는 거짓 보고가 된다.

---

# 8. 비용

## 8-A. 실측 단가 (2026-08-08 공식 문서)

```
                    입력/M      출력/M     검색 요금/1k호출
OpenAI gpt-5        $1.25      $10.00     $10   [대조 2곳]
OpenAI gpt-4o       $2.50      $10.00     $25   + 검색 토큰 무료 → 금액 계산 불가
Claude Sonnet 5     $2.00      $10.00     $10
Gemini 3.6 Flash    $1.50      $ 7.50     $14   (월 5,000회 무료)
Perplexity Sonar    $1.00      $ 1.00     $5~12
Grok 4.3            $1.25      $ 2.50     문서에 없음
```

**5곳 중 4곳이 검색에 호출당 요금을 따로 받는다.** 토큰만 세면 청구서보다 싸게 나오고,
예산 상한이 늦게 걸린다 — 늦게 걸리는 상한은 없는 것과 같다(v0.3.64).

**gpt-4o 계열은 검색 호출의 금액을 낼 수 없다.** 검색 토큰이 무료인데 제공자가 프롬프트와
검색 결과를 합친 `input_tokens` 하나만 준다. 그래서 **관측에는 gpt-5 를 쓴다.**

## 8-B. 실측 호출 비용

```
[실측 2026-08-08] gpt-4o
   검색 안 함   입력    319 · 출력  130  →  $0.002
   검색 함      입력 17,264 · 출력 1,119 →  $0.054 (토큰만)
```

## 8-C. 월 비용 (확정된 설계 기준)

```
질문 1개 1회 측정 (반복3 · 검색켬+끔 · 엔진5) = $0.61 ≈ 854원

핵심 5~8개 주1회 + 확장 20개 월1회
   거래처 1곳   약 $20~28/월 (2.8~4만 원)
   거래처 8곳   약 22~32만 원/월
```

## 8-D. 미해결 — 우리가 읽는 토큰이 실제의 64% (과제 #59)

```
[실측] 2026-08-07(UTC) OpenAI 사용량 CSV 대조
   OpenAI 집계   요청 14회 · 입력 143,653
   내가 부른 것  9회 · 우리가 읽은 입력 합 91,756

   요청 차이 5 = 검색이 실제로 돈 호출 5건과 정확히 일치
[추정] 검색이 도는 호출은 모델을 두 번 부르고, 최종 응답 usage 에는 한 번분만 실린다
```

---

# 9. 확정된 운영 설계 (사장님 결정 2026-08-08)

```
주기      핵심 질문 주 1회 · 확장 질문 월 1회
          근거: GPTO 도 "10대 LLM 매주 · 주 1회 오토 사이클"(2곳 확인)
                그리고 같은 질문 3회에 인용 7/7/10 — 일 단위 변화는 노이즈에 묻힌다
기본값    핵심 5~8개 · 확장 20개 안팎 (화면에서 수정)
엔진      5개 **동일 횟수**. 비중 조절 금지 — 구성비가 전체 언급률을 좌우한다
반복      3회
모드      검색 켬 + 끔 (Perplexity Sonar 는 끔이 없다)
수동측정  kind=MANUAL 로 별도 저장 · 추이 그래프에서 제외        ← 미구현
```

---

# 10. 지금 상태와 남은 것

```
[실측 2026-08-08] observation_runs 0 · prompt_sets 0 · brand_identities 4

✅ 서버 전체 (라우트 12 · 어댑터 4 · 탐지 · 위험 · 검수 · 지표)
✅ 가격표 · 검색 요금 계산
✅ 브랜드 식별 화면 (등록 · 수정 · 공유 도메인 차단)
✅ 질문 집합 만들기 · 지식iN 실수집

✅ 검색 켬/끔 2모드를 한 실행에서 나란히      v0.3.71 (RunForm 이 searchModes 로 보낸다)
✅ 수동 측정 별도 저장                        v0.3.72 (kind=MANUAL · aggregate_rate 가 섞기를 거부)
⬜ 첫 관측 실행 — venomad.com 소액   ← 돈이 나감. 사장님 확인 필요
⬜ 인포그래픽 (과제 #58)             ← 데이터가 있어야 그린다
⬜ 토큰 과소계산 보정 (과제 #59)
⬜ Grok 어댑터 + 엔진 열쇠 3개
```

---

# 11. 관련 문서

```
adr/0003   GEO 준비도는 AI 노출이 아니다        ← 이 문서의 전제
adr/0004   제공자 비활성은 일급 상태
adr/0010   비교는 같은 조건에서만
adr/0013   비율은 맨숫자로 내지 않는다
adr/0014   관측 조건은 측정의 일부다
adr/0015   프롬프트 집합은 감사 대상 산출물이다  ← §3 의 근거

research/GEO_METRIC_DICTIONARY.md              지표 이름 사전
research/GEO_PROMPT_SAMPLING_AND_CONFIDENCE.md 표본·반복 설계
research/CONTENT-PROGRAM-NOTES.md              경쟁사(GPTO) 분석 · 콘텐츠 자료
operations/verifying-citation-support.md       인용 지원 모델 넓히는 절차
```
