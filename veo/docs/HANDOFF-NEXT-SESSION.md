# 다음 세션 인계 — 2026-08-08

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

## 1. 지금 딱 하나 막혀 있다 — GitHub 결제

**v0.3.71 코드는 끝났고 검사도 전부 통과했는데 배포가 안 됐다.**

```
운영 버전     0.3.70   (그대로. 아무것도 안 망가졌다)
main 가지     그대로   (관문이 막아서 안 밀었다)
작업 가지     claude/compassionate-hypatia-5wwn4d
              e10d52a3 docs(veo): 오류 대장 15번
              0164a8e7 feat(veo): 검색 켬·끔을 한 실행에서 나란히 잰다 (v0.3.71)
              둘 다 원격에 밀어둠 · 안 올린 변경 없음
```

**사유 원문** (GitHub check-run 주석):

> "The job was not started because recent account payments have failed or your
> spending limit needs to be increased. Please check the 'Billing & plans'
> section in your settings"

`veo-platform` 은 **비공개 저장소**라 Actions 시간이 무료 한도(월 2,000분)에서
차감된다. 이번 달 실행 100건 이상, 한 건에 약 9분.

**사장님이 하실 것** — https://github.com/settings/billing
카드가 살아 있는지 · Spending limit 이 `$0` 인지. 되돌리기는 언제든 `$0` 으로.

**해결되면 할 것**

```bash
cd ~/Desktop/desktop-tutorial/veo && make deploy
```

그 뒤 운영 확인 — `/api/health` 의 `version` 이 `0.3.71` 이어야 한다.
**절대 우회하지 않는다.** 배포는 `make deploy` 뿐이다.

**진단 명령** (CI 잡이 단계 기록 없이 실패하면 짐작하지 말고 이것부터):

```bash
gh api repos/recon9973-lang/veo-platform/check-runs/<잡ID>/annotations
```

---

## 2. 방금 끝낸 것 — #61 검색 켬/끔 2모드 (v0.3.71)

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

| # | 무엇 | 메모 |
|---|---|---|
| **#62** | 수동 측정 — 관리자가 특정 검색어를 직접 잰다 | `kind=MANUAL`, 추이에서 제외, 예상 비용 미리 표시 (사장님 지시) |
| **#65** | [전수] 서버에는 있는데 화면에서 못 부르는 것 찾기 | 이번 세션에만 3건 나왔다 (0-E) |
| **#66** | [문서] `scoring/methodology.md` 를 SEO 1.9.0 기준으로 | 본문이 1.8.0 기준 — 운영과 다름 |
| **#67** | [문서] GEO 발행본 1.3.0 설명 문서 신규 | 아예 없음 |

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
