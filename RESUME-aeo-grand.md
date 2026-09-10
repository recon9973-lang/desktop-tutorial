# RESUME — 다음 세션 이어가기 (2026-09-10 02:xx KST · s21 마감 · 자동 진단 방)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-09-s21.md`.
> 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)

사장님 첫 물음 «AEO 관련해서 그랜드아름다운의원 최신 진단 자료를 기반으로 조사해줘» 에서
시작해 **조사 → 결함 여섯 고침 → 배포**까지 갔다.

```
veo-platform  main 6e9e6684 · 판 0.3.558  ← 나갔다 (도는지는 «—» 못 쟀다)
  ① 미분류를 맨 뒤로(차례를 한 곳에서)      ② 미분류 몫이 경쟁사 등록에 안 사라지게
  ③ 분모를 교차표 제 셈으로                ④ 기간 탭이 채널 카드도 데려온다
  ⑤ 몇 곳에 물었나를 접기 전에(화면·서버)   ⑥ 임대형 홈페이지 자사 선언에 경로 요구
  덤: 판 물림 둘 · 대장 줄 상한 1,200→1,300 · 관문 12건
```

- **배포는 다섯 번 만에 나갔다.** 관문이 **진짜 결함 둘**을 잡았고(대장 줄 상한 ·
  판 물림이 대기 줄을 **첫 줄만** 옮기던 것 — 여섯 묶음이 한 판으로 쌓인 날 드러났다),
  Postgres 가 세 번 죽었고, 한 번은 CI 를 통과하고도 채점 20분 사이에 옆 방이 먼저
  main 에 닿아 졌다.
- **조사 결과**(문서 `docs/2026-09-09-그랜드아름다운의원-AEO-진단-조사.md`):
  자사 몫 209분의 2 = **0.96%** · 미분류 **85.2%**(운영 평균 47%의 1.8배) ·
  네이버 계열 **0건** · 엔진은 **일곱 중 하나**만 물었다.

## 바로 이어갈 작업

1. **도장 하나** — 0.3.558 이 실제로 도는지. 이 방은 못 잰다(운영 주소 403 · 러너
   워크플로 디스패치도 403). 사장님 화면이나 다른 방에서 러너 「도는 판 확인」을 띄운다.
   확인되면 `docs/WORKLIST.md` 머리말의 «—» 를 실측으로 바꾼다.
2. **대장 갱신분을 main 에 올린다** — veo-platform 가지
   `claude/geo-mosaic-unclassified-last` 에 `b8fae266`·`7309f3c6` 두 커밋이 남아 있다
   (대기 표 비움 · 날짜별 기록). 다음 배포에 실려 나가거나 따로 낸다.
3. **규칙판 4 — 미용의료 채널.** 강남언니·바비톡·여신티켓이 규칙표에 없어 미분류가 크다.
   **근거 없이 넣으면 안 된다**(`citation_channels.py` 머리말: 짐작으로 분류하지 않는다).
   콘솔 대시보드 「AI 가 어디를 보나」 → **「미분류 안에 무엇이 있나」** 를 펼쳐 상위
   도메인을 받은 뒤에 넣는다. 고칠 곳은 셋이 함께다 — 파이썬·화면·`packages/shared-types`
   + 판 번호 + 지문 시험.

## 대기/차단

- **사장님 몫 (AEO)** — ① 일곱 엔진으로 재진단(특히 네이버 AI 브리핑) ② 자사 선언 경로
  확인(`grand1.co.kr` 인지 `grand1.co.kr/skin/` 인지 — **이번 판의 관문은 새 선언만 막고
  이미 저장된 값은 안 고친다**) ③ 춘천 경쟁사 6곳 등록(목록은 조사 문서 §3)
  ④ 병원 포털 등재 정비(인용 8.1%인데 우리 것 0건) ⑤ **CI 를 필수 검사로**(대장 §5).
- **이 방 권한** — veo-platform 푸시 권한 요청은 관문이 거절했으나 `git push` 와
  `make deploy` 는 실제로 됐다. 워크플로 디스패치(`gh workflow run`)는 403.

## 주의·제약

- 이 가지 외로 푸시 금지(desktop-tutorial). veo-platform 은
  `claude/geo-mosaic-unclassified-last`.
- **배포는 `make deploy` 만.** 오더 없이 밀지 않고, 나갈 때 **대기 표를 통째로 보여 드리고
  한 번 여쭙는다**. `VEO_DEPLOY_ORDER` 에 사장님 원문을 인용한다.
- **판 번호는 나갈 때 배포가 정한다.** 사람이 미리 맞추지 않는다.
- 대장 머리말과 대기 표의 미배포 범위가 **일치**해야 한다(`worklist.test.ts`).
- **Postgres 가 자주 죽는다.** `service postgresql start` 로 되살리고, 긴 검사 앞에는
  15초마다 살피는 지킴이를 붙인다. 역할 `root`/비번 `veo` · DB `veo_test`.
- 못 잰 값은 «—». 지어낸 수치 금지. 의료광고법 준수. 모델 ID 는 커밋 트레일러에만.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_013hnfFKDdKTpoJnZ6hRix8Y`

## 참고

- veo-platform 환경: `PYTHON=/usr/bin/python3.12 make setup` · `pnpm install` ·
  `service postgresql start` · `VEO_DATABASE_URL=... alembic upgrade head` ·
  `gh` 는 릴리스 tarball 로 설치(`/usr/local/bin/gh`).
- 검사: `make preflight`(약 12분) · `make ci-local` · `apps/web` 에서 `npx vitest run`.
- 이 방은 운영 주소로 못 나간다 — `make deploy` [5/5] 의 오류 22 는 **실패가 아니라
  확인을 못 한 것**이다.
