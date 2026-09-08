# RESUME — 다음 세션 이어가기 (2026-09-07 21:0x KST · s19 마감 · 자동 진단 방)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-07-s19.md`.
> 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)

**끝났다.** 사장님 첫 물음 «왜 항상 진단이 오전 9시 오전 12시 2번 진행이 되는지» 에서
시작해 **다섯을 냈다.** 전부 main 에 있다(`72f9d3cd` · 남은 커밋 0).

```
v0.3.544  고침 넷 — 하루 두 번 돌던 정기 진단 · 실행자 「자동」 ·
                    GEO 탭에서도 「자동」 · 서버 여러 대에서 청소 안 끊김
v0.3.546  대장 도장 — 이미 나간 넷이 대기 목록에 남아 있던 것
v0.3.551  판 번호를 나갈 때 정한다        (구조 제안 1)
v0.3.554  채점 자리를 방마다 나눈다        (구조 제안 2) + 로그가 진단을 안 죽인다
v0.3.555  지금 누가 도는지 알려 준다        (구조 제안 3)
```

- **v0.3.544 는 실서비스 확인 끝** — [실측 2026-09-08 17:28 KST] 서버·워커 둘 다 `0.3.544` ·
  뒤처진 0. **0.3.540 이 반만 나가 있던 것(워커 ✗)도 이때 풀렸다.** v0.3.546 은 캡처의
  웹 `0.3.549` 로 확인됐다. **0.3.551·0.3.554·0.3.555 는 아직 못 쟀다.**
- **구조 셋이 실제로 도는 것을 배포에서 봤다.**
  - 1번: 「물릴 것 없습니다」와 「0.3.555 로 물립니다」 둘 다. **그 뒤 판 번호에 손댄 적 없다.**
    *왜 「채점보다 앞」인가* — 뒤에 두면 CI 가 채점한 커밋과 나가는 커밋이 달라진다(오류 135).
  - 2번: 원격에 **두 자리가 나란히 선다**(옛 이름=다른 방 · `deploy-candidate-<가지 이름>`=이 방).
    **`/` 가 아니라 `-` 다** — git 은 같은 이름을 가지이면서 폴더로 못 쓴다.
  - 3번: 첫 배포에서 「없습니다 — 지금 채점 중인 방이 없습니다」가 찍혔고 **한 번에** 들어갔다.
    **알려 주는 줄이지 관문이 아니다** — 못 읽어도 배포는 나간다.
- **이 방은 실서비스로 못 나간다**(프록시가 CONNECT 에서 403). `make deploy` 의 [5/5] 가 늘
  오류 22 로 끝난다 — **배포 실패가 아니라 확인을 못 한 것**이다.
- **오늘 배운 것**: 판 충돌 열두 번 · 남의 채점 자리를 한 번 덮음 · **내가 네 번 틀림**
  (파일 관례 · 남의 관문과 이름 부딪힘 · **git 이 못 받는 이름 설계** · 문서 줄 길이) ·
  **남의 PR 이 main 을 깨뜨려 모든 방이 막힘**. 상세는 세션 로그 §2-6·§2-7·§3-2·§3-4·§3-5·§3-6.
  **PostgreSQL 이 다섯 번 죽었다** — `service postgresql start` 로 되살린다.

## 바로 이어갈 작업

1. **실측 한 번**(가벼움) — 이 방은 못 잰다. 이것 하나로 셋이 한꺼번에 풀린다.
   ```
   https://veo-platform-production.up.railway.app/api/health   → 0.3.555 인가
   ```
   확인되면 대장 §2 머리말·대기 표에서 **이 방 줄(0.3.554·0.3.555)만** 지우고
   변경이력 절 제목에 「나갔다」. **다른 방 줄은 건드리지 않는다.**
2. **사장님 몫 하나 — CI 를 필수 검사로.** 대장 §5 에 올려 뒀다.
   `GitHub → Settings → Branches → main → Require status checks → CI`.
   [실측 2026-09-09] 이게 없어서 **빨간불 PR 이 main 에 들어와 모든 방 배포가 막혔다**(#5).
   `ci.yml` 은 이미 `pull_request` 로 검사하므로 **지정만 하면 그 PR 은 막혔다.**
   오늘 겪은 것 중 **가장 값싸고 가장 큰** 처방이다.
3. **이 방에 남은 코드 일감은 없다.** 사장님 첫 물음에서 시작한 것은 다 나갔고,
   구조 제안 셋도 다 냈다. 새 오더를 받으면 그때부터다.

## 대기/차단

- **`make deploy` 권한** — `.claude/settings.json` 에 아래를 넣고 **방을 새로 시작**해야 듣는다.
  에이전트가 제 권한을 넓히는 건 관문이 막으므로 **사장님이 직접** 넣으셔야 한다.
  ```json
  "permissions": { "allow": [
    "Bash(make deploy)", "Bash(make deploy:*)",
    "Bash(make preflight)", "Bash(make preflight:*)",
    "Bash(export VEO_DEPLOY_ORDER=*)"
  ] },
  ```
- **방 공조** — 클라우드 방끼리 직접 호출이 안 된다(`ListAgents` 에 안 잡히고 세션 ID 로도 거절).
  사장님이 전달자. **앞질러 잡는 것은 안 통한다는 것이 오늘 두 번 확인됐다**(0.3.540 을
  ANSEO 방이 먼저 가져갔다) — 번호는 main 에 먼저 닿는 쪽이 갖는다. 알릴 것은
  「이 방이 0.3.541 로 대기 중」 하나이고, 물러나는 값은 싸다(판 물림 + 문서 넷).

## 주의·제약

- 이 가지 외로 푸시 금지. 체크포인트 문서는 desktop-tutorial main 에 커밋(CLAUDE.md 규칙).
- 배포는 **`make deploy` 만**. 오더 없이 밀지 않는다. `VEO_DEPLOY_ORDER` 에 사장님 원문 인용.
- `deploy-candidate` 는 덮어쓰는 채점 자리라 **`--force` 가 정상**. main 은 절대 force 금지.
- 대장·변경이력에 **「민다·푸시」 금지**(`two-words-only` 관문) — 「커밋」·「배포」 두 낱말만.
- 대기 표와 §2 머리말의 **미배포 범위가 일치**해야 한다(`worklist.test.ts`). 오늘 여기서 한 번 걸렸다.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01SmorTxHEe4BY34eFSpBBnX`. 모델 ID 는 트레일러에만.
- 사장님께는 「커밋」·「배포」 두 낱말만. 못 잰 값 «—», 지어낸 수치 금지, 의료광고법 준수.

## 참고

- veo-platform 환경 세우기: `PYTHON=/usr/bin/python3.12 make setup` · `pnpm install` ·
  로컬 PostgreSQL(`service postgresql start`, role `root`/비번 `veo`, DB `veo_test`, `alembic upgrade head`) ·
  `gh` 는 릴리스 tarball 로 설치(`/usr/local/bin/gh`).
- preflight 실행: `PGPASSWORD=veo VEO_TEST_DATABASE_URL="postgresql+psycopg://root:veo@localhost:5432/veo_test" make preflight`
