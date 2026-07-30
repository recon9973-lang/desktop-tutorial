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

## 0. 지금 상태 — 배포가 막혀 있다

로컬 커밋 **3개가 아직 원격에 없다.**

| 커밋 | 내용 |
|---|---|
| `8c6f3e0` | Vercel 빌드 실패(`middleware.ts`/`proxy.ts` 충돌) 수정 + CI 웹 빌드 신설 |
| `d751b7d` | 작업 기록 문서 |
| (미커밋) | ADR 0014 번호 중복 → `0016-absolute-scoring.md` 로 재번호 |

**Claude 는 `git push` 가 막혀 있다. 사용자가 직접 실행해야 한다.**

```bash
cd /Users/leejae-hoon/Desktop/desktop-tutorial
git push origin claude/compassionate-hypatia-5wwn4d
git subtree push --prefix=veo veo-platform main
```

올라가기 전까지 **라이브 화면에는 자동 로그인·비밀번호 보기 기능이 없다.**
마지막 Vercel 배포 `f9b9759` 가 Error 로 끝나 화면이 옛 코드로 남아 있다.

**배포 후 확인** — Vercel 의 `Ready` 만 보지 마라. `Ready` 는 빌드가 끝났다는
뜻이지 내가 만든 것이 거기 있다는 뜻이 아니다. **로그인 화면을 실제로 열어**
비밀번호 칸 오른쪽에 "보기" 버튼이 있는지 보고, 한 번 로그아웃 → 재로그인 해서
14일 갱신 토큰이 생기는지 확인한다. (릴리스 체크리스트 B-9)

---

## 1. 절대 어기면 안 되는 규칙

- **자격증명이 없으면 그럴듯한 값을 지어내지 마라.** 명시적 픽스처와
  "공급자 비활성" 상태로 남긴다. 이것을 어기면 제품 전체가 무의미해진다.
- **N/A 는 분모에서 빼고, UNKNOWN 은 분모에 남긴 채 0점.** (절대 평가)
  N/A 를 0점 처리하거나 UNKNOWN 을 분모에서 빼는 순간 상대 평가가 된다.
- **점수를 이루는 영역만으로 100.** 그 분모는 고객 상태에 따라 움직이지 않는다.
  움직이면 "연결할수록 불리 / 만들수록 불리" 같은 잘못된 유인이 생긴다.
  → 세 번 틀렸던 경위는 세션 로그 1.3 과 ADR 0016.
- **모든 숫자는 `packages/scoring-specs` 의 발행 명세에만 있다.** 검사기 코드에
  숫자를 넣지 마라. 명세를 고쳤으면 **새 판을 발행**한다(발행본은 불변, ADR 0012).
- **GEO 준비도와 AI 관측은 분리된 채로 둔다.** 섞지 마라.
- 모든 점수는 방법론 판·원자료·분모·추적·신뢰도를 함께 지닌다.
- SSRF 방어, 조직 간 격리, 자격증명 보호는 타협 대상이 아니다.
- **하위 에이전트·워커의 보고를 믿지 말고 직접 확인해라.** 실제로 여러 번 틀렸다.
- **비밀 값을 대화창에 출력하지 마라.** 스크립트도 값을 찍지 않는다.
  `veo/.env` 는 0600 이고 gitignore 되어 있다.

## 2. 완료했다고 말하기 전에 반드시 돌릴 것

**웹(Next.js)을 고쳤으면:**

```bash
cd /Users/leejae-hoon/Desktop/desktop-tutorial/veo && pnpm --filter @veo/web verify
```

타입체크·린트·테스트가 **모두 초록이어도 `next build` 는 깨질 수 있다.**
실제로 그렇게 틀렸다 — Next 16 이 `middleware` 규약을 `proxy` 로 바꾼 것을 모르고
`middleware.ts` 를 새로 만들어 빌드가 거부됐는데, 배포가 Error 로 끝났고 화면은
옛 코드로 남아 사용자가 "기능이 없는데?" 라고 물어보고서야 알았다.

**API(파이썬)를 고쳤으면:** DB 테스트가 조용히 **건너뛰어진다.**
`VEO_TEST_DATABASE_URL` 없이 돌리면 3,789개가 전부 SKIPPED 인데 EXIT=0 이라
통과처럼 보인다. 로컬 `veo_test` DB 를 붙여서 돌리고, **passed 숫자를 확인**해라.
설정은 `docs/operations/local-development.md`.

**화면을 고쳤으면 렌더해서 실제로 재라.** 스크린샷만 보고 추측하지 마라.
직전 판에서 테스트보다 "그려 보고·재 보고·배포해 보고" 잡은 결함이 더 많았다.

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

### 제품

| 순위 | 항목 | 왜 |
|---|---|---|
| 1 | **GEO 관측** (AI 답변 인용 추적) | 제품 이름의 절반이 비어 있다 |
| 2 | **사이트 전체 크롤 + 병렬 수집** | 지금 0.29초/페이지 **직렬**. 한 장만 봐서 내부 링크·중복 본문·클릭 깊이가 측정 불가 |
| 3 | 헤드리스 렌더링 | `js_render_parity` 가 실사이트에서 늘 측정 불가 |
| 4 | 추이·회귀 알림 | `RECURRED`·`regression_count` 는 이미 기록 중 |
| 5 | 담당자별 업체 배정 · "누가 무엇을 언제 고쳤나" | 대행사 운영에 필요 |
| — | 초대 메일 자동 발송 | **의도적 보류** — 링크 직접 전달로 충분하다고 사용자가 결정 |

### 화면

- 왼쪽 목차 고정 (7화면 이동)
- **업체 전달용 인쇄·PDF** — 대행사가 고객에게 보내는 실제 경로가 지금 없다

### 알고 있는 한계 (문서화됨, 당장 고칠 필요는 없음)

- robots.txt 문법 오류는 알리지만, 의도한 차단이 실제로 안 걸린 것까지는 안 본다.
- 수집 페이지가 적으면 측정 불가가 많다 → 위 2번이 해결한다.
- 성능 4항목은 PageSpeed·CrUX 연동 없이는 측정 불가이고, **배점에 남아 점수를
  내린다. 의도한 동작이다** — 우리 키로 재는 항목이기 때문.

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
