# 다음 세션 인수인계 프롬프트

> 새 세션을 열고 **아래 `---` 사이를 그대로 붙여넣으면** 이어서 작업할 수 있다.
> 프롬프트는 짧게 두고 세부는 문서를 가리킨다.
>
> **지금 상태·다음 작업은 여기 없다. `docs/HANDOFF.md` 에 있다.** 한때 이 문서가
> 그것까지 적고 있었고, 그 사본이 낡아 SEO 명세 1.6.0(실제 1.8.0)·"PageSpeed 키
> 없음"(실제 연동 완료)·"가격표 미연결"(실제 연결됨)을 사실처럼 적어 두었다.
> 두 곳에 적으면 반드시 갈라진다(0-D). 이 문서는 **변하지 않는 것만** 담는다.

---

VEO 플랫폼 작업을 이어서 한다. 작업 디렉터리는
`/Users/leejae-hoon/Desktop/desktop-tutorial`, 코드는 그 아래 `veo/` 모노레포다.
브랜치는 `claude/compassionate-hypatia-5wwn4d`.

**손대기 전에 이 셋을 순서대로 읽어라. 근거 없이 코드부터 고치지 마라.**

1. `veo/docs/HANDOFF.md` — **지금 상태와 다음 작업은 전부 여기 있다.** 이 문서가
   현재 사실의 유일한 출처다.
2. `veo/docs/research/VEO_CLAUDE_DEVELOPMENT_MASTER_PROMPT.md` 의 **0-A ~ 0-J** —
   개발 지침. 특히 0-A(실측에 대한 정직성)와 0-B(절대 평가)는 이 제품의 생명이다.
3. `veo/docs/architecture/next-session-prompt.md` — 이 문서. 변하지 않는 규칙·
   검증 명령·시스템 좌표·알려진 한계.

**작업 전에 매번 세 가지를 먼저 말해라** — 전체 목적 / 무엇을 만드는가 / 지켜야 할 원칙.
눈에 걸리는 것부터 고치다 방향을 잃은 적이 있어서 만든 규칙이다.

나는 개발자가 아니다. 한국어로, 전문 용어를 풀어서 설명해라.

---

## 1. 절대 어기면 안 되는 규칙

**본문은 지침서 `docs/research/VEO_CLAUDE_DEVELOPMENT_MASTER_PROMPT.md` 에 있다.
여기서 되풀이하지 않는다** — 두 곳에 적으면 반드시 갈라지고, 갈라지면 어느 쪽이
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
| **0-H** | 규칙을 정했으면 **그 규칙을 지키는 검사**를 함께 만든다 |
| **0-I** | 결함을 고칠 때 **그 결함을 지키고 있던 테스트**를 찾아 이름째 바꾼다 |
| **0-J** | 못 하는 이유를 고객 탓으로 적지 않는다 |

0-C·0-D·0-E·0-G 는 **각각 실제로 어긴 사례**가 있었고, 어긴 것이 남의 코드가 아니라
직전 판에서 내가 쓴 코드였다. 0-H·0-I·0-J 는 **"고쳤는데 또 나온다"** 는 사용자의
지적에서 나왔다. 답은 "계속 틀린 게 아니라 한 번 정한 것을 끝까지 적용하지 않았다"
였다. 문지기가 없으면 규칙은 기억에 의존하고, 기억은 실패한다.

여기에만 있는 것 (지침서에 없는 이 환경의 규칙):

- **비밀 값을 대화창에 출력하지 마라.** 스크립트도 값을 찍지 않는다.
  `veo/.env` 는 0600 이고 gitignore 되어 있다.
- **Claude 는 `git push` 가 막혀 있다.** 사용자가 직접 실행해야 한다.
- **로그인 화면은 브라우저로 확인하지 않는다.** 비밀번호 입력은 금지된 행동이라,
  로그인이 필요한 화면의 최종 확인은 **사용자 몫**이다. 대신 빌드까지 돌린다.
- 사용자는 개발자가 아니다. **한국어로, 전문 용어를 풀어서** 설명해라.

## 2. 완료했다고 말하기 전에 반드시 돌릴 것 (0-F 의 실행 명령)

```bash
cd /Users/leejae-hoon/Desktop/desktop-tutorial/veo && pnpm --filter @veo/web verify
```

웹은 여기에 `next build` 가 들어 있다. **타입체크·린트·테스트가 모두 초록이어도
빌드는 깨진다.**

```bash
cd /Users/leejae-hoon/Desktop/desktop-tutorial/veo
VEO_SCORING_SPECS_DIR="$PWD/packages/scoring-specs" \
VEO_TEST_DATABASE_URL="postgresql+psycopg://$USER@localhost:5432/veo_test" \
VEO_DATABASE_URL="postgresql+psycopg://$USER@localhost:5432/veo_test" \
.venv/bin/python -m pytest apps/api/tests apps/worker/tests -q
```

**`VEO_TEST_DATABASE_URL` 을 빼면 DB 시험이 전부 SKIP 인데 EXIT=0 이다**(0-F 그 자체).
`make test-db` 는 `-m requires_postgres` 만 돌리므로 전체를 봤다고 말할 수 없다.

```bash
cd .../veo/apps/api && ../../.venv/bin/python -m mypy    # mypy 는 apps/api 안에서
cd .../veo && .venv/bin/python -m ruff check apps/api packages
```

계약이 바뀌었으면 재생성까지 해야 한다. 안 하면 계약 시험이 깨진다.

```bash
cd .../veo/apps/api && ../../.venv/bin/python scripts/export_openapi.py
cd .../veo && pnpm --filter @veo/api-client generate
```

**시험 통과 개수를 여기 적지 않는다.** 적으면 낡고, 낡은 숫자는 "그때는 맞았다" 는
말밖에 못 한다. 직접 돌려서 EXIT 와 실패 건수를 봐라.

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

**현재 명세 버전을 여기 적지 않는다.** 발행 명세는 파일이 진실이다:
`ls packages/scoring-specs/specs/veo.seo.readiness/` 로 직접 봐라. 한때 이 자리에
`1.6.0` 이라 적혀 있었고 실제로는 1.8.0 이었다.

세션 쿠키는 httpOnly `veo_console_session`(15분) + `veo_console_refresh`(14일),
갱신은 `apps/web/src/proxy.ts` 에서만 한다(서버 컴포넌트는 쿠키를 못 고친다).

### 배포할 때

```bash
cd /Users/leejae-hoon/Desktop/desktop-tutorial
git push origin claude/compassionate-hypatia-5wwn4d
git subtree push --prefix=veo veo-platform main     # 이것까지 해야 실제로 올라간다
```

- **Vercel 의 `Ready` 만 보지 마라.** `Ready` 는 빌드가 끝났다는 뜻이지 내가 만든 것이
  거기 있다는 뜻이 아니다. 바꾼 화면을 실제로 열어 확인한다(릴리스 체크리스트 B-9).
- **Vercel 이 계속 Error 로 끝나면 재배포를 누르지 마라.** 재배포는 이미 건네준 코드를
  다시 빌드하는 것이라 같은 실패를 반복한다. `git subtree push` 가 새 코드를 건네주는
  유일한 경로다. 실제로 그렇게 막혀 있었다.
- Railway 는 `alembic upgrade head` 를 자동으로 돌린다(`preDeployCommand`).
- 밖에서 확인할 수 있는 것은 **경로가 살아 있는지까지**다. 인증이 필요한 경로는
  401 이 오면 마운트된 것이다(404 면 아니다). 그 이상은 로그인해야 알 수 있다.

## 4. 다음 작업

**`docs/HANDOFF.md` §4 를 봐라.** 여기에 사본을 두지 않는다 — 예전에 두었고, 그
사본이 "GEO 관측 미착수" 라고 적어 두는 바람에 **이미 7,300줄 규모로 존재하는 엔진을
없는 것으로 알고 지나칠 뻔했다.** 실제로 없던 것은 `router.py`·`schemas.py`·
`service.py` 세 파일뿐이었다. 지침서 0-D 는 그 사고에서 나왔다.

착수 전에 사용자에게 어느 것부터 할지 확인한다.

## 5. 알고 있는 한계 (문서화됨, 당장 고칠 필요는 없음)

여기 있는 것은 **성질**이지 그날의 상태가 아니다. 상태는 HANDOFF 에 있다.

- robots.txt 문법 오류는 알리지만, **의도한 차단이 실제로 안 걸린 것까지는 안 본다.**
- **`CATEGORY_OR_HUB` 중요도를 자동으로 붙이지 않는다.** 픽스처에서 `/guide/` 는 허브,
  `/deep/` 은 콘텐츠인데 둘 다 1단계 경로다 — 사람이 뜻으로 라벨한 것이라 주소 모양에서
  나오지 않는다. 지어내면 절반이 틀리고, 틀린 절반은 조용히 점수를 흔든다. 콘솔에서
  사람이 고르게 하는 것이 다음 단계다.
- **`INTENTIONAL_NOINDEX` 도 자동으로 붙이지 않는다.** `noindex` 태그만 보고 "의도된
  것" 이라 하면 실수로 걸린 noindex 를 우리가 숨겨 주게 된다.
- **인용을 돌려주지 않는 모델이 있다.** 실측: `gpt-5`·`gpt-4o` 는 돌려주고
  `gpt-4.1`·`gpt-4o-mini` 는 돌려주지 않는다. 목록에 없는 모델로 재면 인용 지표가
  0 이 아니라 **측정 불가**다. 넓히려면 `docs/operations/verifying-citation-support.md`.

### 작업 실행에 대해 알고 있어야 하는 것

**Celery 가 아니라 API 프로세스 안의 배경 스레드다.** 배포 환경에 브로커(Redis)가
없어서 그렇게 했고, 없는 것을 있는 척하지 않았다.

대가: **프로세스가 재시작하면 돌던 작업은 죽는다.** 그 행은 `RUNNING` 인 채 남으므로
`veo.jobs.service.STALE_AFTER`(20분)를 두고, 그보다 오래 소식이 없으면 응답의
`is_stale` 이 참이 된다. **화면은 `status` 만 보고 그리면 안 된다** — `is_stale` 이
참인데 "실행 중" 이라고 쓰면 사용자가 오지 않을 결과를 기다린다.

Redis 를 붙이면 `veo/jobs/execution.py` 의 `run_detached` 만 Celery 호출로 바꾸면
된다. 작업 계약과 조회 경로는 그대로다.

---

## 6. 참고 문서 지도

| 문서 | 내용 |
|---|---|
| **`docs/HANDOFF.md`** | **지금 상태·다음 작업·최근에 배운 것. 먼저 읽는다** |
| `docs/research/VEO_CLAUDE_DEVELOPMENT_MASTER_PROMPT.md` | 개발 지침 (0-A ~ 0-J) |
| `docs/architecture/session-log-2026-07.md` | 7월 판 전체 기록 (사료. 현재 상태 아님) |
| `docs/architecture/upgrade-proposal.md` | 전수조사 + 리서치 + UI/UX 제안 |
| `docs/architecture/screen-plan.md` | 화면 설계 |
| `docs/architecture/requirements-traceability.md` | 요구사항 ↔ 구현 대조표 |
| `docs/research/SEO_SCORING_ALGORITHM_V2.md` | 점수 알고리즘 설계·검증 (부록 C 가 최신) |
| `docs/research/LIGHTHOUSE_COMPARISON.md` | 구글 158개 감사 대조, 배점 근거 |
| `docs/adr/0016-absolute-scoring.md` | 분모가 세 번 움직인 경위 |
| `docs/adr/0002-na-and-unknown-semantics.md` | N/A 규칙(유효) · UNKNOWN 규칙(0016 이 대체) |
| `docs/adr/0012-published-methodology-is-immutable.md` | 발행 명세는 못 고친다 |
| `docs/operations/release-checklist.md` | 배포 전후 점검 (B-9 = 바뀐 화면 직접 열기) |
| `docs/operations/local-development.md` | 로컬 DB·테스트 설정 |
| `docs/operations/runbook-provider-credentials.md` | 자격증명 교체 절차 |
