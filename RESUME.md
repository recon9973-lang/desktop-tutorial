# RESUME — 다음 세션 이어가기 (2026-09-10 02:1x KST · s21 마감 · ANSEO 보안 점검 방)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-09-s21.md`.
> 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)

**ANSEO 보안 전수 점검 → 고침 셋 → 배포 확인까지 끝났다.**
대상 저장소는 **`veo-platform`**(이 저장소가 아니다). 가지
`claude/anseo-security-review-f4wtdr`.

```
569bf4f  거래처 경계 둘(키워드·인용) + robots 되짚기 제거
9ba7af3  관문 둘을 전수로 · 경계를 못 좁히면 선다
fe059b9  실험 금액은 최고관리자만 (사장님 결정)
93620792 0.3.557 나감 도장 — 대장 대기 표 비움     ← CI 채점 중
```

- **샌 것은 「거래처 경계」뿐이다** — 조직 경계(대행사끼리)는 한 군데도 안 샜다.
  걸리는 계정은 `CLIENT_VIEWER` 하나만 가진 **병원 포털 계정**. 네 자리(키워드 창구
  다섯 · 인용 사이트 집계 · 진단 회차 셋 · 실험 지출) 전부 막았다.
- **이미 운영에서 돈다.** [실측 2026-09-10 01:45 KST · 러너 실행 34378754595]
  진단 서버 `0.3.557` · 워커 1대 `0.3.557` · 뒤처진 0. 웹은 **못 쟀다**
  (`/api/health` 가 Vercel 쪽엔 없어 404 — 「아니다」가 아니라 「못 잰다」).
  다른 방이 이 가지를 합쳐 0.3.557 로 내보냈다(`6cb6c4cd`).

## 바로 이어갈 작업

1. **CI 결과 확인 후 main 으로 (이것 하나만 남았다).**
   실행 **34380738762** · 후보 가지 `deploy-candidate-claude-anseo-security-review-f4wtdr` ·
   커밋 `936207929a0389cbd01dac207c23e66e2b14a0fd`.
   ```
   초록불이면 :  git push origin 936207929a0389cbd01dac207c23e66e2b14a0fd:main
   빨간불이면 :  main 을 건드리지 말고 원인부터
   ```
   **`gh` 는 이 방에서 인증이 없다**(`GH_TOKEN` 비었음) — `make deploy` 는 [3/4] 에서
   20분 헛돌다 선다. CI 상태는 **GitHub MCP 도구**(`mcp__github__actions_list`)로 읽는다.
   고르는 순서는 `deploy.sh` 그대로: **실패 > 도는 중 > 초록**.
   문서만 바뀌므로 **판 번호는 올리지 않는다**(운영 동작 무변경).
2. 그 뒤 이 방에 **남은 코드 일감은 없다.** 새 오더를 받으면 그때부터다.

## 대기/차단

- **`gh` 인증** — `GH_TOKEN` 이 비어 있어 `make deploy`·`make preflight` 의 gh 부분이
  안 돈다. git 자격에서 토큰을 꺼내려 했으나 **관문이 막았고 우회하지 않았다.**
  풀려면 사장님이 세션 환경에 토큰을 넣으셔야 한다(**값은 문서·코드에 안 적는다**).
- **사장님 몫 둘**(GitHub 설정 — 에이전트가 못 한다)
  - **CI 를 필수 검사로**: Settings → Branches → main → Require status checks → CI.
    [실측 2026-09-09] 이게 없어서 **빨간불 PR 이 main 에 들어와 모든 방 배포가 막혔다.**
  - JS 의존성 검사 추가(파이썬 쪽은 이미 있다).
- **보고서 §8 의 남은 것 셋** — 오더 받으면 한다. 4번(권한 확인 두 줄)이 가장 싸다.

## 주의·제약

- 이 가지 외로 푸시 금지. 체크포인트 문서는 desktop-tutorial main 에 커밋.
- 배포는 오더 받고서만. 하루 상한 2회 — **그 자리에서 다시 재라**(이 방 값은 낡는다).
- `deploy-candidate-*` 는 덮어쓰는 채점 자리. **main 은 절대 force 금지.**
- **대기 표에 판 번호를 미리 적지 마라** — `claim_version` 이 고칠 자리를 못 찾아
  배포가 선다(2026-09-10 실제로 그랬다). 새 일감은 `—` 로 쌓는다.
- 대장·변경이력에 **「민다·푸시」 금지**(`two-words-only` 관문). 「커밋」·「배포」만.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_017tUhCvkiUBcyDxqwdzyRqu`.
  **모델 ID 는 트레일러에만** — 문서·코드·PR 본문에 안 쓴다.
- 못 잰 값은 «—», 지어낸 수치 금지, 의료광고법 준수.
- **사장님께는 선택지 표 대신 추천 하나를 평범한 말로.** s21 에서 «무슨 말인지
  모르겠네» 를 들었다.

## 참고 — 이 방 환경 세우기 (veo-platform)

```
PYTHON=/usr/bin/python3.12 make setup        # .venv 를 만든다 (preflight·CI 가 이걸 쓴다)
service postgresql start                     # role root / 비번 veo / DB veo_test
PGPASSWORD=veo make preflight
```

**웹을 만졌으면 `pnpm -r typecheck` 를 반드시 돌린다** — `vitest` 도 `next build` 도
시험 파일의 형은 안 본다. s21 에서 이것을 빠뜨려 형 어긋남 둘을 놓쳤다.
