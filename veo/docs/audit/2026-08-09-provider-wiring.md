# 외부 API 연결 전수 — 무엇이 붙어 있고 무엇이 없나

2026-08-09 · 사장님 질문: *"구글 psi, crux 같은 경우 연결은 어디서 하는거지? seo geo
ai대답에 필요한 미연결된 api가 있다면 모두 정리해서 보고."*

근거는 셋이다 — 운영 `GET /api/providers` 응답, **실제로 돈 진단 47건**이 기록한
`scan_runs.provider_states`, 그리고 코드.

## 1. PSI 와 CrUX 는 키 **하나**를 쓴다

`crux_from_settings()` 가 `pagespeed_from_settings()` 를 그대로 돌려준다
(`providers/google/credentials.py:191`). 그 자리의 주석:

> "Both APIs authenticate with the same kind of Google API key and VEO stores one slot.
> Inventing a second setting would suggest two credentials exist to configure when only
> one does; what the operator actually has to do is **enable the Chrome UX Report API on
> the same Cloud project**."

즉 넣는 것은 키 하나, 추가로 할 일은 **같은 Google Cloud 프로젝트에서 Chrome UX Report
API 를 켜는 것**뿐이다. 열쇠는 들어가 있다 — 다만 **값이 나온 적은 없다.** §6 을 볼 것.

### 어디서 넣나 — 길은 둘, 지금 되는 건 하나

| 길 | 상태 |
|---|---|
| **금고**(조직별) `PUT /api/credentials/GOOGLE_PAGESPEED/api_key` | 서버 창구는 있는데 **화면이 없다** (#69) |
| **환경변수**(배포 전체) `VEO_GOOGLE_PAGESPEED_API_KEY` | **지금 이것으로 연결돼 있다** |

그래서 오늘 키를 바꾸려면 **Railway 환경변수를 고치는 수밖에 없다.** 화면에서 넣는
길은 서버 쪽 엔드포인트 4개가 놀고 있는 그 자리다.

## 2. 전수 — 실측

**[실측]** 진단 47건 기록 집계 + 운영 `/api/providers`:

| 제공자 | 상태 | 근거 |
|---|---|---|
| GOOGLE_PAGESPEED | **연결** | 42/43건 ENABLED |
| GOOGLE_CRUX | 열쇠는 있음 · **값은 아직 없음** | 아래 §6 |
| NAVER_SEARCH_AD | **연결** | 43/43 |
| NAVER_DATALAB | **연결** | 43/43 |
| geo_external (네이버 검색 대조) | **연결** | 최근 진단 ENABLED |
| OPENAI | **연결** | 최근 2건 ENABLED — 그 전 41건은 없었다 |
| GOOGLE_GEMINI | 없음 | 43건 전부 `DISABLED_NO_CREDENTIAL` |
| PERPLEXITY | 없음 | 43건 전부 |
| ANTHROPIC | 없음 | 43건 전부 |
| GOOGLE_SEARCH_CONSOLE | 없음 | 43건 전부 — **다만 아래를 볼 것** |
| 네이버 서치어드바이저 | **API 자체가 없음** | *"publishes no public API"* (`providers/searchadvisor/__init__.py:5`) |

## 3. 축별로 무엇이 막히나

### SEO — 열쇠는 다 있다. 다만 CrUX 값은 안 나온다

PSI·네이버는 값을 낸다. **CrUX 는 열쇠가 있어도 값이 없다** — 구글이 이 사이트들의
실사용자 데이터를 공개하지 않기 때문이고, 우리가 할 수 있는 것이 없다(§6).

최근 진단의 나머지 판정 불가는 **제공자 때문이 아니다**:

```
seo.content.js_render_parity        자바스크립트 렌더 대조
seo.crawl.no_broken_internal_links  크롤 상한
```

### GEO — 막힌 것 없음

사이트 쪽 준비도는 전부 잰다. 외부 대조(`geo_external`)도 붙어 있다. 최근 판정 불가
하나는 `geo.fresh.dates_truthful` — **이전 수집 이력이 없어서**이고, 두 번째 진단이
돌면 풀린다.

### AI 답변 — 여기가 비어 있다

* 엔진 4개 중 **OPENAI 하나만** 연결. Gemini·Perplexity·Anthropic 은 열쇠가 없다.
* 클라이언트 코드는 **넷 다 있다** (`observations/providers/{openai,anthropic,gemini,
  perplexity}.py`). 열쇠만 넣으면 된다.
* 그리고 **`observation_runs = 0`** — AI 답변 관측은 아직 한 번도 돌지 않았다.
  진단 47건은 SEO·GEO 축이고 AI 답변과는 다른 축이다.

## 4. 짚어 둘 것 둘

### 가. Search Console 은 열쇠가 없어서 못 쓰는 게 아니다

**[실측]** `SearchConsoleClient` 를 생성하는 코드가 `apps/api/src` 전체에 **0곳**이다.
클라이언트는 만들어 뒀는데 어느 수집기에도 붙이지 않았다. **지금 열쇠를 넣어도 달라지는
것이 없다.** 붙이는 일이 먼저다.

### 나. `/api/providers` 가 실제로 쓰는 것을 다 말하지 않는다

`/api/providers` 는 8개를 말한다. 그런데 진단 기록에는 **`GOOGLE_CRUX` 와
`geo_external` 이 더 있다** — 열이 열이다.

`credentials/providers.py` 머리글은 이 두 목록을 맞추는 것이 *"the one maintenance
obligation this module carries"* 라고 적어 두었는데, 지금 어긋나 있다. 연동 상태 화면을
그 응답만 보고 만들면 **CrUX 는 화면에 아예 안 나오고**, 사장님이 지금 하신 질문("CrUX
는 어디서 연결하지?")을 화면을 보고도 다시 하게 된다.

## 5. 그래서 필요한 것

| 무엇 | 왜 | 누가 |
|---|---|---|
| Gemini · Perplexity · Anthropic 열쇠 3개 | AI 답변을 엔진 하나로만 재면 그 엔진의 취향이 곧 결과가 된다 | 사장님 (발급) |
| 첫 AI 답변 관측 실행 (#63) | 한 번도 안 돌았다. 돈이 나가서 승인이 필요하다 | 사장님 (승인) |
| 자격증명 화면 (#69) | 지금은 Railway 환경변수로만 넣는다 | 위 두 개가 정해진 뒤 |
| Search Console 을 수집기에 붙이기 | 클라이언트만 있고 부르는 곳이 없다 | 필요하다고 정해지면 |
| `/api/providers` 에 CRUX·geo_external 넣기 | 화면이 실제와 다른 것을 말하게 된다 | 작은 수정 |


---

## 6. 정정 — CrUX 는 "연결됨" 이 아니다 (2026-08-09, 사장님 지적)

이 문서의 첫 판은 CrUX 를 **연결됨**으로 적었다. 근거로 댄 것은
`scan_runs.provider_states` 의 `GOOGLE_CRUX: ENABLED` 22건이었다. **틀렸다.**
`ENABLED` 는 **열쇠가 있다**는 뜻이지 **값을 받았다**는 뜻이 아니다
(`docs/CORRECTIONS.md` 19번).

**[실측]** 진단 47건 전체에서 CrUX 를 읽는 유일한 검사 `seo.perf.inp_field` 의 결과:

```
NOT_APPLICABLE  40건
UNKNOWN         14건
PASS / FAIL      0건   ← 값이 나온 적이 한 번도 없다
```

사유는 시기에 따라 셋이었다:

```
7/29 ~ 7/31   "CrUX 연동이 구성되어 있지 않아"   열쇠가 없던 때
8/03 · 8/04   "받은 응답이 없어"                4건
8/02 ~ 8/08   "표본이 없어"                     지금 — 호출은 되고 데이터가 없다
```

**지금 사유는 하나다: 구글이 이 사이트들의 값을 공개하지 않는다.** CrUX 는 크롬
실사용자 데이터라 방문자가 일정 수를 넘는 사이트만 구글이 낸다. 수집기 주석이 같은
말을 한다 — *"방문자 수에 관한 사실이지 사이트의 결함이 아니다"*
(`seo/collectors/performance_ux.py`).

**우리가 고칠 수 있는 것은 없다.** 열쇠 문제도, Chrome UX Report API 를 켜는 문제도
아니다. 배점에서 빼고 점수를 깎지 않는 지금 처리가 맞다.

**고친 것은 문구다.** 앞의 판은 "…표본이 없어 … 측정하지 못했습니다" 였고 사장님이
그것을 **"CrUX 실패"** 로 읽으셨다. 우리가 뭔가 못 한 것처럼 읽히는 문장이었다. 지금은:

> 구글이 이 사이트의 실사용자(CrUX) 데이터를 아직 공개하지 않습니다. 크롬 방문자가
> 일정 수를 넘어야 제공되며, 사이트의 결함이 아니고 점수도 깎지 않습니다. 방문자가
> 쌓이면 자동으로 평가 대상이 됩니다.

시험이 이 문구를 붙잡는다 — `tests/providers/test_collector_payload_contract.py`
(`측정하지 못했습니다` 가 다시 들어오면 실패한다).
