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
API 를 켜는 것**뿐이다. 이미 켜져 있다 — 실측으로 SEO 진단 22건에서 `GOOGLE_CRUX:
ENABLED` 다.

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
| GOOGLE_CRUX | **연결** | SEO 진단 22건 ENABLED (PSI 키 공유) |
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

### SEO — 막힌 것 없음

PSI·CrUX·네이버 전부 붙어 있다. 최근 진단의 판정 불가는 **제공자 때문이 아니다**:

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
