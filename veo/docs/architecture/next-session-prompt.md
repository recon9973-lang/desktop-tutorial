# 다음 세션 인수인계 프롬프트

> 새 세션을 열고 **아래 `---` 사이를 그대로 붙여넣으면** 이어서 작업할 수 있다.
> 이 문서 자체도 함께 읽히므로, 프롬프트는 짧게 두고 세부는 문서를 가리킨다.

---

VEO 플랫폼 작업을 이어서 한다. 작업 디렉터리는
`/Users/leejae-hoon/Desktop/desktop-tutorial`, 코드는 그 아래 `veo/` 모노레포다.
브랜치는 `claude/compassionate-hypatia-5wwn4d`.

**손대기 전에 이 셋을 먼저 읽어라.** 근거 없이 코드부터 고치지 마라.

1. `veo/docs/research/VEO_CLAUDE_DEVELOPMENT_MASTER_PROMPT.md` — 개발 지침.
   특히 **0-A(실측에 대한 정직성)** 와 **0-B(절대 평가)** 는 이 프로젝트의 생명이다.
2. `veo/docs/architecture/session-log-2026-07.md` — 직전 판에 무엇을 왜 했는지,
   무엇이 틀렸다가 고쳐졌는지, 무엇이 미완료인지.
3. `veo/docs/architecture/next-session-prompt.md` — 이 문서. 아래 "0. 지금 상태"
   부터 "4. 다음 작업" 까지가 현재 지시다.

나는 개발자가 아니다. 한국어로, 전문 용어를 풀어서 설명해라.

---

## 0. 지금 상태

Next 16 빌드 실패는 해결됐고 라이브 화면에 비밀번호 "보기" 버튼이 떠 있는 것을
직접 확인했다. 14일 갱신 토큰은 로그인이 필요해 아직 사람이 확인하지 못했다.

**커밋 6개가 원격에 있는지 먼저 확인하라.**

```bash
cd /Users/leejae-hoon/Desktop/desktop-tutorial
git log --oneline origin/claude/compassionate-hypatia-5wwn4d..HEAD   # 비어 있어야 한다
git push origin claude/compassionate-hypatia-5wwn4d
git subtree push --prefix=veo veo-platform main
```

**Claude 는 `git push` 가 막혀 있다. 사용자가 직접 실행해야 한다.**

**배포 후 확인** — Vercel 의 `Ready` 만 보지 마라. `Ready` 는 빌드가 끝났다는
뜻이지 내가 만든 것이 거기 있다는 뜻이 아니다. 바꾼 화면을 **실제로 열어** 확인한다.
(릴리스 체크리스트 B-9)

> **Vercel 이 계속 Error 로 끝난다면 재배포를 누르지 마라.** 재배포는 이미 건네준
> 코드를 다시 빌드하는 것이라 같은 실패를 반복한다. 터미널의 `git subtree push` 가
> 새 코드를 건네주는 유일한 경로다. 실제로 그렇게 막혀 있었다.

### 이번 판(2026-07-30 후반)에 바뀐 것

| 커밋 | 내용 |
|---|---|
| `a90f912` | 원래 빨간불이던 `ruff`·`mypy` 를 초록으로 (CI 가 이 둘을 돌린다) |
| `be1f5b1` | 사이트 전체 크롤(발견) + 사이트맵 미연결·이미지 사이트맵 오탐·분모 이동 |
| `1064e85` | 병렬 수집(11.5→4.9초) + 호스트 예산 카운터의 경쟁 상태 |
| `c5c55fa` | URL 중요도 분류 + 리다이렉트 중복 페이지 (유효 11→23장) |
| `f181a2e` | 인용 정직성 — 못 받는 모델의 "인용 0회" 를 측정 불가로 |
| `a3c3cab` | 관측 라우터 1/2 — 프롬프트 집합·엔진 상태 |

---

## 1. 절대 어기면 안 되는 규칙

**본문은 지침서 `docs/research/VEO_CLAUDE_DEVELOPMENT_MASTER_PROMPT.md` 의 0-A ~ 0-G 에
있다. 여기서 되풀이하지 않는다** — 두 곳에 적으면 반드시 갈라지고, 갈라지면 어느 쪽이
맞는지 아무도 모른다(0-D 가 바로 그 이야기다).

| | |
|---|---|
| **0-A** | 실측에 대한 정직성 — 재지 않은 것을 잰 것처럼 보이지 않는다 |
| **0-B** | 절대 평가 — 분모는 고객 상태에 따라 움직이지 않는다 (**네 번 틀렸다**) |
| **0-C** | 얇은 표본에서는 숫자를 내지 않는다 — 탐색 3회, 비교 5회 |
| **0-D** | 있는 것을 다시 만들지 않는다 — **문서보다 폴더를 먼저 열어라** |
| **0-E** | 부를 수 없는 기능은 없는 기능이다 |
| **0-F** | 초록불은 동작이 아니다 |
| **0-G** | 오래 걸리는 일은 요청 안에서 하지 않는다 |

이 판(2026-07-31) 전수조사에서 0-C·0-D·0-E·0-G 를 **각각 실제로 어긴 사례**가 나왔다.
어긴 것이 남의 코드가 아니라 직전 판에서 내가 쓴 코드였다. §4 를 보라.

여기에만 있는 것 (지침서에 없는 이 환경의 규칙):

- **비밀 값을 대화창에 출력하지 마라.** 스크립트도 값을 찍지 않는다.
  `veo/.env` 는 0600 이고 gitignore 되어 있다.
- **Claude 는 `git push` 가 막혀 있다.** 사용자가 직접 실행해야 한다.
- 사용자는 개발자가 아니다. **한국어로, 전문 용어를 풀어서** 설명해라.

## 2. 완료했다고 말하기 전에 반드시 돌릴 것 (0-F 의 실행 명령)

```bash
cd /Users/leejae-hoon/Desktop/desktop-tutorial/veo && pnpm --filter @veo/web verify
```

웹은 여기에 `next build` 가 들어 있다. 타입체크·린트·테스트가 모두 초록이어도 빌드는
깨진다.

```bash
cd /Users/leejae-hoon/Desktop/desktop-tutorial/veo && make test-db
```

**주의: `make test-db` 는 `-m requires_postgres` 만 돌린다.** 전체를 보려면 DB 를 붙여
직접 돌리고 **passed 숫자를 확인**해라. 붙이지 않으면 DB 테스트가 전부 SKIP 인데
EXIT=0 이다.

```bash
VEO_SCORING_SPECS_DIR="$PWD/packages/scoring-specs" \
VEO_TEST_DATABASE_URL="postgresql+psycopg://$USER@localhost:5432/veo_test" \
VEO_DATABASE_URL="postgresql+psycopg://$USER@localhost:5432/veo_test" \
.venv/bin/python -m pytest apps/api/tests apps/worker/tests -q
```

2026-07-31 기준 **4,174 passed · 1 skipped**(건너뛴 1건은 Redis 브로커 미기동).
`ruff` 통과, `mypy` 는 `apps/api` 안에서 돌려야 한다(밖에서 돌리면 경로 오류).

## 3. 시스템 좌표

| | |
|---|---|
| 소스 | `recon9973-lang/desktop-tutorial` (비공개, 브랜치 작업) |
| 배포 | `recon9973-lang/veo-platform` main ← `git subtree push --prefix=veo` |
| API | Railway · `veo-platform-production.up.railway.app` |
| 웹 | Vercel · `veo.seokorea.org` (Root Directory `apps/web`) |
| DB | Neon `ap-southeast-1` |

구성: `apps/api`(FastAPI·SQLAlchemy 2.0·Alembic), `apps/web`(Next.js 16 App Router),
`apps/worker`, `packages/scoring-specs`(명세 = 데이터, JSON-Schema 검증 + SHA-256).
현재 명세 **1.6.0** (57항목).

세션 쿠키는 httpOnly `veo_console_session`(15분) + `veo_console_refresh`(14일),
갱신은 `apps/web/src/proxy.ts` 에서만 한다(서버 컴포넌트는 쿠키를 못 고친다).

## 4. 다음 작업 — 우선순위 순

배포(0번)를 끝낸 뒤 아래로 간다. **착수 전에 사용자에게 어느 것부터 할지 확인.**

> ## ⚠ 앞선 판의 이 문서가 GEO 를 크게 잘못 적어 두었다
>
> *"GEO 관측 — 미착수. 제품 이름의 절반이 비어 있다"* 라고 되어 있었다. **사실이
> 아니다.** 엔진은 약 7,300줄 규모로 이미 있다 — 제공자 4종(OpenAI·Anthropic·
> Gemini·Perplexity), 인용·언급·경쟁사·동명이인 탐지, 위험 평가, 검수 대기열, 표본
> 설계, 실행기 612줄, 테스트 29개 파일. DB 모델·마이그레이션·권한도 전부 있다.
>
> 없던 것은 **`router.py`·`schemas.py`·`service.py` 세 파일**이었다. 그래서 `src/`
> 안에서 `ObservationRunner` 를 부르는 코드가 하나도 없었고, 완성된 엔진 전체가
> 테스트에서만 돌았다. 지금은 절반(프롬프트 집합·엔진 상태)이 연결됐다.
>
> **교훈: 이 문서의 "미착수" 를 믿지 말고 폴더를 먼저 열어 봐라.** 한 번 잘못 적히면
> 다음 사람이 있는 것을 새로 만들거나, 없는 줄 알고 건너뛴다. 지침서 0-D 가 됐다.
>
> **그리고 같은 사고가 한 줄 아래에도 있었다** — 네이버 SearchAd 를 "자격증명 없음·
> 미착수" 로 적어 두었는데 실제로는 실 API 에 연결돼 있고 키도 들어 있다.
> 2026-07-31 전수조사에서 추적표 전체를 실물과 대조해 고쳤다.

### 2026-07-31 전수조사 결과

백엔드는 두껍고 **문이 얇다.** API 경로 71개 중 화면이 쓰는 것은 15개, 콘솔 12화면 중
실제로 동작하는 것은 4개(`seo`·`customers`·`team`·`account`)다. 공개 진단 3화면도
자리표시자다.

**"완성됐지만 아무도 부르지 않는" 것들이 진행률에서는 완성으로 세어지고 있었다**(0-E):
답변 위험 평가·사람 검수, Celery 워커, 관측 SOV, 사용량·비용.

### 제품 — 우선순위 순

| 순위 | 항목 | 왜 |
|---|---|---|
| 1 | **GEO 콘솔 화면** (#19·#25) | `/console/geo` 는 준비도·관측 **양쪽 다 빈 화면**이다. 제품 이름의 절반이 화면에서 0. 이제 막는 것이 없다 |
| 2 | 원문 답변 영속화 (#22) | 재배포하면 근거가 사라진다 → 0-A 가 무너지는 지점 |
| 3 | 키워드 화면 (#25) | 백엔드는 네이버 실 API 에 붙어 있는데 쓸 경로가 없다 |
| 4 | 위험 평가·검수 연결 (#24) | 병원 고객에게 의료 오답 판정은 특히 중요하다 |
| 5 | SEO 스캔도 작업으로 (#21 나머지) | 지금도 동기다. 25장 4.9초라 견디지만 100장이면 위험하다. **`/console/seo` 화면이 동기 응답에 의존하므로 화면과 함께 옮겨야 한다** |
| 6 | 헤드리스 렌더링 (#8) | `js_render_parity` 상시 측정 불가 |
| 7 | 추이·회귀 알림 (#9) · 담당자 배정 (#10) | 대행사 운영에 필요 |
| ✔ | ~~사이트 전체 크롤 + 병렬 수집~~ · ~~GEO 관측 실행·저장·지표~~ | 완료 |
| ✔ | ~~지표 모듈 중복 정리~~ (#20) | **완료.** `metrics.py` 를 `sampling.ObservedRate` 위에 다시 얹었다 |
| ✔ | ~~관측을 비동기로~~ (#21) | **완료.** 202 + `GET /api/jobs/{id}`. 아래 주의 |
| — | 초대 메일 자동 발송 | **의도적 보류** — 링크 직접 전달로 충분하다고 사용자가 결정 |

> ### 작업 실행에 대해 알고 있어야 하는 것
>
> **Celery 가 아니라 API 프로세스 안의 배경 스레드다.** 배포 환경에 브로커(Redis)가
> 없어서 그렇게 했고, 없는 것을 있는 척하지 않았다.
>
> 대가: **프로세스가 재시작하면 돌던 작업은 죽는다.** 그 행은 `RUNNING` 인 채 남으므로
> `veo.jobs.service.STALE_AFTER`(20분)를 두고, 그보다 오래 소식이 없으면 응답의
> `is_stale` 이 참이 된다. **화면은 `status` 만 보고 그리면 안 된다** — `is_stale` 이
> 참인데 "실행 중" 이라고 쓰면 사용자가 오지 않을 결과를 기다린다.
>
> Redis 를 붙이면 `veo/jobs/execution.py` 의 `run_detached` 만 Celery 호출로 바꾸면
> 된다. 작업 계약과 조회 경로는 그대로다.

값싸고 효과가 큰 것: **PageSpeed 키**(#30). 무료이고 어댑터는 이미 있는데, 없어서
성능 4항목이 상시 측정 불가이고 그 배점이 **모든 고객 점수를 깎고 있다.** 0-A 의
"PageSpeed 를 못 쟀다면 그건 우리가 안 한 것이다" 가 정확히 이 경우다.

관측 실행의 세부는 `docs/architecture/session-log-2026-07.md` 의 "관측 연결 2/2" 에
있다. **가격표가 연결되지 않아** 비용이 늘 `NO_PRICE_CONFIGURED` 로 남는다는 점,
**`gpt-4o-mini`·`gpt-4.1` 로 실행하면 인용 지표가 측정 불가**가 된다는 점을 먼저 읽어라.

### 화면

- 왼쪽 목차 고정 (7화면 이동)
- **업체 전달용 인쇄·PDF** — 대행사가 고객에게 보내는 실제 경로가 지금 없다

### 알고 있는 한계 (문서화됨, 당장 고칠 필요는 없음)

- robots.txt 문법 오류는 알리지만, 의도한 차단이 실제로 안 걸린 것까지는 안 본다.
- 성능 4항목은 PageSpeed·CrUX 연동 없이는 측정 불가이고, **배점에 남아 점수를
  내린다. 의도한 동작이다** — 우리 키로 재는 항목이기 때문.
- **`CATEGORY_OR_HUB` 중요도를 자동으로 붙이지 않는다.** 픽스처에서 `/guide/` 는 허브,
  `/deep/` 은 콘텐츠인데 둘 다 1단계 경로다 — 사람이 뜻으로 라벨한 것이라 주소 모양에서
  나오지 않는다. 지어내면 절반이 틀리고, 틀린 절반은 조용히 점수를 흔든다. 콘솔에서
  사람이 고르게 하는 것이 다음 단계다.
- **`INTENTIONAL_NOINDEX` 도 자동으로 붙이지 않는다.** `noindex` 태그만 보고 "의도된
  것" 이라 하면 실수로 걸린 noindex 를 우리가 숨겨 주게 된다.
- **관측 비용이 늘 `NO_PRICE_CONFIGURED` 다.** `pricing.py` 의 `PriceTable` 이
  `build_registry` 에 연결되지 않았다. 0원이라는 뜻이 아니라 모른다는 뜻이다.
- **인용을 돌려주지 않는 모델이 있다.** 실측: `gpt-5`·`gpt-4o` 는 돌려주고
  `gpt-4.1`·`gpt-4o-mini` 는 돌려주지 않는다. 목록에 없는 모델로 재면 인용 지표가
  0 이 아니라 측정 불가다. 넓히려면 `docs/operations/verifying-citation-support.md`.

---

## 5. 참고 문서 지도

| 문서 | 내용 |
|---|---|
| `docs/research/VEO_CLAUDE_DEVELOPMENT_MASTER_PROMPT.md` | 개발 지침 (0-A 정직성 / 0-B 절대평가 + 10원칙) |
| `docs/architecture/session-log-2026-07.md` | 직전 판 전체 기록 — 알고리즘·요청 17건·결함 12건·미완료 |
| `docs/architecture/upgrade-proposal.md` | 전수조사 + 리서치 + UI/UX 제안 |
| `docs/architecture/screen-plan.md` | 화면 설계 |
| `docs/adr/0016-absolute-scoring.md` | 분모가 세 번 움직인 경위 |
| `docs/adr/0002-na-and-unknown-semantics.md` | N/A 규칙(유효) · UNKNOWN 규칙(0016 이 대체) |
| `docs/adr/0012-published-methodology-is-immutable.md` | 발행 명세는 못 고친다 |
| `docs/operations/release-checklist.md` | 배포 전후 점검 (B-9 = 바뀐 화면 직접 열기) |
| `docs/operations/local-development.md` | 로컬 DB·테스트 설정 |
