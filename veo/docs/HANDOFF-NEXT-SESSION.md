# 다음 세션 인계 — 2026-08-08 (2차 갱신)

**이 파일을 새 세션 첫 메시지에 붙여넣으면 맥락 없이도 이어갈 수 있다.**

---

## 0. 먼저 읽을 것 (순서대로)

```
1  veo/docs/README.md                프로젝트 전체 지도 · 현재 상태 · 문서 색인
2  veo/docs/observation-engine.md    ③ AI 답변 관측 기준 문서 (§4-C-2 가 방금 한 작업)
3  veo/docs/SESSION-2026-08-08.md    최근 작업 · 완료/대기/미완료
4  veo/docs/CORRECTIONS.md           내가 틀린 것 전부 (15건) — 같은 실수를 다시 하지 않기 위해
5  ~/.claude/CLAUDE.md               규칙 1·2·3 (확인 줄 · 근거 등급 · 다시 밟기)
6  veo/docs/research/VEO_CLAUDE_DEVELOPMENT_MASTER_PROMPT.md  §0-A~0-J 원칙
```

---

## 1. 막혀 있던 것은 풀렸다 — 배포 완료 (2026-08-08)

```
운영 버전     0.3.74   ← /api/health 로 확인함
main          d3848f3f
막힘          해소
```

**원인은 결제 실패가 아니라 `Actions` 예산 `$0` 이었다.** 인계 문서가 "결제 실패" 라고
적어 둔 것은 틀렸다(`docs/CORRECTIONS.md` 16번). GitHub 오류 문구가 *"결제 실패했거나
**또는** 지출 한도"* 두 가지를 한 문장에 담고 있었고 앞쪽만 읽었다.

**[실측]** 세 번 실제로 돌려서 갈랐다:

```
09:18 · 12:54   예산 $0 · 카드 없음   → 실패
14:16           예산 $0 · 카드 있음   → 실패   ← 결제가 원인이면 여기서 풀렸어야 한다
예산 $5 로 올린 뒤                    → 성공
```

**지금 설정** — `Actions` 예산 `$5` · `Stop usage: Yes`. 최대 손실이 $5 에서 잘린다.
나머지 넷(Codespaces·Packages·Git LFS·AI 크레딧)은 `$0` 그대로 두었다 — 안 쓰는 것들이다.

**[실측]** 8월 1~8일 청구액은 **매일 $0** 이었다. 쓴 $14.23 을 무료 한도가 전액 덮었다.

**같은 일이 또 나면** — 짐작하지 말고 이 순서로 갈른다:

```bash
gh api repos/recon9973-lang/veo-platform/check-runs/<잡ID>/annotations   # 사유 원문
# 문구에 `or` 가 있으면 사유가 아니라 후보 목록이다. 한쪽만 바꿔서 다시 돌려 본다.
```

그리고 사용량을 줄여 두었다 — 아래 §1-A 의 CI 중복 제거.

---

## 1-A. 이번 세션(2차)에 끝낸 것 — #65 · #62 · #66 · #67

### #65 전수 — 서버에 있는데 화면에서 못 부르는 것

**[실측]** 엔드포인트 115개 중 후보 29개. 한 건씩 코드로 확인했다.
전문: `docs/audit/2026-08-08-server-ui-gap.md`. 다시 세는 명령: `python3 scripts/ui_gap.py`.

진짜 구멍 다섯 (아직 **안 고쳤다** — 찾기까지가 #65 였다):

| 무엇 | 지금 무슨 일이 일어나나 |
|---|---|
| 이슈를 "해결" 로 못 옮긴다 | 해결로 가는 문은 재측정뿐인데(`lifecycle.py:304`) 화면은 상태변경만 부른다 |
| AI 엔진 열쇠를 화면에서 못 넣는다 | credentials 4개가 마운트돼 있는데(`app.py:296`) 아무도 안 부른다 — **#64 를 직접 막고 있다** |
| 리포트 본문을 화면에서 못 읽는다 | 목록·내보내기·공유만 있다 |
| 경쟁사 비교 화면이 없다 | 브랜드 선언까지만 있다 |
| 무료 진단에 상담 요청 폼이 없다 | 접수 창구(`/public/v1/leads`)는 서버에 서 있다 |

딸린 것: `credentials/router.py:3` 의 "deliberately not mounted" 는 **사실과 다르다.**

### #62 수동 측정 (v0.3.72)

GEO 화면에 "검색어 하나만 지금 재보기" 칸. `kind=MANUAL` 로 저장되고 추이에서 빠진다.

관문으로 막은 것 셋 — 주석이 아니라 코드가 거부한다:

```
aggregate_rate   정기·수동을 섞으면 MixedRunKindsError. 예외 통로 없음
execution        실행의 kind 는 질문 집합에서 따라온다. 갈라 받지 않는다
PromptSet.build  UNCLASSIFIED 가 든 집합을 거부한다 (즉석 집합 전용 값)
```

**예상 비용은 금액을 못 낸다.** 금액은 단가 x 토큰인데 토큰은 재 봐야 알고, 관측이
0건이라 기준선이 없다. 호출 수(정확)만 내고 금액 자리는 비운 채 왜 못 내는지를 적는다.
**관측이 한 번 돌면 그때부터 금액이 나온다** — `token_baselines()` 가 저장된 답변의
중앙값을 읽는다.

### #68 이슈가 닫힌다 (v0.3.73)

이슈 상세에 **재측정 칸**과 **담당자 칸**을 달았다. 지금까지 이슈는 열리고 진행되기만
하고 닫히지 않았다 — 규칙은 처음부터 옳았고 그 규칙을 밟을 화면이 없었다.

`"해결로 표시"` 버튼은 **일부러 없다.** 진단을 고르는 칸 하나뿐이고, 판정은 그 진단이
실제로 무엇을 쟀는지에서 서버가 낸다. 시험이 그 칸이 생기는 것을 막는다
(`VerificationPanel.test.tsx` — "판정을 고르는 칸이 없다").

**[실측]** `python3 scripts/ui_gap.py` 후보 수 29 → **26**.

### #69 는 화면만으로 안 된다 — 조사만 하고 멈췄다

손대려다 더 깊은 것을 찾았다. 셋 다 실측이다.

```
1  금고에 AI 엔진이 없다      CredentialProvider 5개 · states() 8개
                             Gemini·Perplexity·Anthropic 은 자리 자체가 없다
2  금고를 읽어 호출하는 곳 0곳  *_from_vault() 는 있는데 src 안에서 아무도 안 부른다
3  그래서 화면만 만들면 거짓말  열쇠를 넣어도 아무 호출이 그 값을 안 쓴다
```

그리고 이것은 **이미 열려 있던 결정**이었다:

> "vault 방식으로 바꾸면 `credential_encryption_key` 가 없을 때 키워드 엔드포인트가
> 기동 시점부터 막히는 등 부팅 조건이 바뀌므로, 통합 담당의 결정이 필요합니다."
> (`keywords/INTEGRATION_REQUEST.md` 요청 #5, 상태: 열림)

**순서:** ① 부팅 조건 결정(사장님) → ② 금고에 AI 엔진 셋 추가 → ③ 호출 경로를 금고로
→ ④ 화면.

낡은 주석 둘은 고쳤고(`credentials/router.py`·`providers.py`), 같은 어긋남이 또
생기지 않게 시험으로 못박았다(`tests/credentials/test_provider_coverage.py`).

### #71 무료 진단 상담 요청 폼 (v0.3.74)

진단 결과 아래에 상담 요청 칸을 달았다. 접수 창구(`POST /public/v1/leads`)는 처음부터
서버에 있었는데 누를 자리가 없어서 **무료 진단이 돌아도 영업으로 이어지지 않았다.**

받는 것은 이름과 연락처 하나. **광고 수신 동의 칸은 없다** — 서버가 받지도 저장하지도
않으므로 화면에 두면 받은 것처럼 보인다. 저장한 항목은 서버가 돌려준 목록을 그대로
보인다(우리가 적으면 실제와 갈라지고, 갈라진 쪽이 개인정보 안내문이다).

**[실측]** `python3 scripts/ui_gap.py` 후보 수 26 → **25**.

### CI 중복 제거 — 같은 커밋을 두 번 검사하던 것

**[실측]** 8/1~8/8 veo-platform: 실행 153건 · 서로 다른 커밋 117개 ·
**두 가지에서 중복 실행된 커밋 36개** · 실행당 잡 시간 약 8.9분 → 약 320분 낭비.

`make deploy` 가 후보 가지에서 초록불 받은 **그 SHA** 를 main 으로 미는데, main 에서
워크플로가 처음부터 다시 돌았다. 같은 입력에 같은 답이다. `push.branches` 에서 `main` 을
뺐다.

**관문은 안 약해진다** — main 에 닿는 유일한 길이 `deploy.sh` 이고 그것이 후보 가지
초록불을 먼저 본다(`deploy.sh:66`, 확인함). PR 은 `pull_request` 로 그대로 검사한다.
되돌아가지 않게 시험 둘을 붙였다(`tests/release/test_ci_paths.py`).

### #66 · #67 채점 설명 문서

* `docs/scoring/methodology.md` 본문을 **1.9.0 기준**으로. 1.8.0 과 숫자가 같다는 것은
  문서 주장을 믿지 않고 명세 YAML 을 `diff` 해서 확인했다.
* `docs/scoring/geo-methodology.md` **신규** — GEO 발행본 1.3.0 설명. 아예 없었다.
* 두 문서의 표는 손으로 옮긴 값이라 `python3 scripts/spec_weights.py [--domain geo]`
  로 다시 셀 수 있게 했다. **[실측]** 가중치 합 SEO 100.0 · GEO 100.0.

---

## 2. 그 앞 세션에 끝낸 것 — #61 검색 켬/끔 2모드 (v0.3.71)

검색 켬은 "지금 검색하면 우리가 나오는가", 끔은 "AI 가 학습한 것만으로 우리를
아는가". 서로 다른 사실이라 한쪽으로 다른 쪽을 말할 수 없다.

**고친 결함 셋 — 셋 다 "겹쳐서 하나가 사라진다" 는 같은 모양**

| 어디 | 무엇이 겹쳤나 | 거짓이 되던 것 |
|---|---|---|
| `execute(conditions=...)` | 엔진 이름 열쇠로 검색 켬·끔이 겹침 | 한 모드만 돌고 "두 모드 쟀다" |
| `ai_engines` 조회 표 | 같은 엔진의 두 모델이 겹침 | 답변이 다른 모델 행에 붙음 |
| 안정성 지표 묶음 | (질문, 엔진) 으로만 묶음 | 조건 차이가 **엔진의 불안정**으로 |

핵심 개념: **`RunConditions.slot` = (엔진, 모델, 검색모드).** 저장 쪽이 처음부터
그 셋으로 유일했다(`ai_engines`, ADR 0010). 실행 계획만 안 나뉘어 있었다.
`execute()` 는 이제 표가 아니라 **목록**을 받는다 — 겹칠 열쇠가 없다.

**Perplexity** 는 검색을 끌 수 없는데 끔으로 요청하면 그대로 기록했다. 이제 호출
**전에** 거절한다. `supports_search_off` 를 `/observations/engines` 가 알려주고
화면은 엔진 이름으로 알아맞히지 않는다.

**만진 파일**

```
API   observations/runs.py            RunConditions.slot 추가
      observations/runner.py          execute(conditions=Sequence), _plan, SkippedWork.search_mode
      observations/execution.py       _conditions_of, DuplicateEngineSlotError, engine_rows 를 slot 으로
      observations/metrics.py         AnswerFact.search_mode · 안정성 묶음 축에 추가
      observations/providers/base.py  supports_search_off + ask() 거절
      observations/providers/perplexity.py · registry.py · router.py · schemas.py · service.py
시험  tests/observations/test_engine_slots.py                    (신규)
      tests/observations/providers/test_observation_runner.py    2모드·중복거절
      tests/observations/providers/test_answer_providers.py      Perplexity 거절
      tests/observations/test_metrics.py                         모드 미합산
웹    app/(console)/console/geo/RunForm.tsx + .test.tsx(신규) + geo.module.css + page.tsx
      app/api/observation/route.ts    searchModes 배열 받기
      lib/observations.ts             startObservation(searchModes)
      lib/observations.search-modes.test.ts (신규)
```

**[실측]** `make ci-local` 통과 (5,151 passed) · 웹 517 passed · `next build` 성공.
CI 의 실제 검사 7개도 전부 통과 — 실패한 것은 결제 때문에 시작 못 한 집계 잡뿐.

---

## 3. 남은 과제

### 배포 없이도 지금 할 수 있는 것

`#62`·`#65`·`#66`·`#67`·`#68`·`#71` 은 **끝났다** (§1-A).
`#69` 는 조사만 하고 멈췄다 — 사장님 결정이 앞에 있다.
남은 것은 #65 가 찾아 놓은 나머지다.

| # | 무엇 | 메모 |
|---|---|---|
| **#70** | 리포트 본문 화면에서 읽기 | 지금은 파일로 내려받아야만 읽는다 |
| **#72** | 경쟁사 비교 화면 | 엔드포인트 3개가 놀고 있다 |
| **#69** | AI 엔진 열쇠 넣는 화면 | **①번 결정이 앞에 있다**(위 §1-A). 화면만 만들면 거짓말이 된다 |

작은 것들(키워드 목록 저장, 지난 조회 다시 열기, CSV 내보내기, 프로젝트 수정 등)은
`docs/audit/2026-08-08-server-ui-gap.md` §B 에 있다.

### 사장님 결정이 필요한 것

| # | 무엇 | 왜 멈춰 있나 |
|---|---|---|
| **#63** | 첫 관측 실행 — venomad.com 소액 | **돈이 나간다.** 승인 필요 |
| **#59** | 토큰 과소계산 (우리 계산이 실제의 64%) | `platform.openai.com/usage` → Cost 탭을 사장님이 봐야 함 |
| **#64** | 엔진 확대 — Grok 신규 + Anthropic·Gemini·Perplexity 열쇠 | 열쇠 3개 필요 |
| **#58** | 관측 인포그래픽 (GPTO 수준) | #63 이 끝나야 그릴 데이터가 생김 |

### 범위 밖 (건드리지 않는다)

`#33` flow.seokorea.org 지역 · `#35` ERP 전체 소스 · `#36` journeymap 백업 없음 ·
`#38` flowlens·journeymap 시험 없음

---

## 4. 이 프로젝트에서 절대 어기지 않는 것

**범위** — 사장님 확정: *"seo, geo, ai대답까지야. 콘텐츠 작성은 자료 연결만하고
erp로 토스."* ④ 네이버 키워드와 ⑤ 리포트는 범위 밖.
콘텐츠 아이디어는 `docs/research/CONTENT-PROGRAM-NOTES.md` 에 계속 쌓는다.

**배포** — `make deploy` 뿐. GitHub 장애로 막혀도 우회하지 않는다.

**보안**
- 비밀값(비밀번호·API 키·토큰·접속 주소)을 대화창에 출력하지 않는다. 스크립트
  출력으로도 안 된다. 이름만 말하고 존재 여부만 확인한다.
- 사장님께 비밀값이 보이는 화면을 캡처해 달라고 하지 않는다. "있다/없다" 만 묻는다.
- 로그인 폼에 비밀번호를 입력하지 않는다. 로그인이 필요한 화면은 사장님이 연다.
- 운영 데이터를 내려받았으면 확인 후 지운다.
- `veo/.env` 는 0600 · gitignore.

**할루시네이션** — 사장님 지시: *"창의력이 필요할때만 창의력을 쓰고 나머지 모든
업무에는 실제 근거로 할루시네이션 없이."* 특히 **화면 문구와 코드 주석**. 대화는
지나가지만 제품에 들어간 문장은 남고 거기엔 관문이 없다.

**작업 지침과 제품은 다르다** — 사장님 지적: *"내 명령을 니가 일하는 방식과 니가
하는일에 실제 적용하는건 다른거야. 구분해서 해야지."* 내 규칙을 제품 화면 설명글로
옮겨 적지 않는다.

**버전 올리는 절차** — `apps/web/src/lib/changelog.ts` 맨 앞에 항목 추가(그것이 곧
APP_VERSION) + `apps/api/src/veo/__init__.py` `__version__` 같은 값 → openapi 재생성
(`apps/api/scripts/export_openapi.py`) → `npx openapi-typescript apps/api/openapi.json
-o packages/api-client/src/schema.d.ts`

**웹은 빌드까지 돌린다** — 타입체크·시험이 통과해도 `next build` 는 깨질 수 있다.
