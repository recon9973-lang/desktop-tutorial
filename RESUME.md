# RESUME — 다음 세션 이어가기 (2026-09-11 · s22 마감 · AEO 진단 방)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-11-s22.md`.
> 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 사장님 답을 기다리는 것 (제일 위)

1. **없다 — 체크박스는 그대로 둔다.** (2026-09-11 확정)
   사장님 정의: **정기진단 = 정기진단 체크박스 이용(3일 간격 자동) · 일반진단 = 같지만 1회성.**
   **체크박스가 곧 정기진단의 장치다.** 이전 세션에서 내가 「없애자」고 했는데
   사장님이 방금 정의해 주신 것을 없애자는 소리였다 — 오류 201. **다시 꺼내지 말 것.**
   v0.3.564 가 한 일은 **그 체크박스가 실제로 듣게 만든 것**이다(전에는 저장이 그 값을 버렸다).
2. **SerpAPI 요금제** — 오더대로 **지금은 안 올린다**(«용량 다되면 업그레이드»).
   [실측 2026-09-11] 이달 499 사용 · 잔여 501 / 월 1,000 Starter · **9/20 경 소진**.
   바닥나면 경보가 알리고 대시보드 하단에 잔여가 실시간으로 보인다. 다음 단계는
   **월 2,500 이상**([계산] 필요량 월 1,650~1,980).

## 이번 세션에 끝낸 것 (둘 다 실측 확인)

```
v0.3.563  [실측 2026-09-11 02:49 KST] 서버·워커 둘 다
v0.3.564  [실측 2026-09-11 15:49 KST] 서버·워커 둘 다 · 뒤처진 0
          ① 한 번 눌러 본 진단이 정기 자리에 들어가던 것을 막음
          ② 판마다 그때의 코드 판을 적음(observation_runs.app_version)
          ③ AI 고르는 길을 화면·서버 양쪽에서 제거
```

**진짜 원인**(사장님 첫 물음의 뿌리): 엔진이 아니라 **종류**였다. `run_kind_for` 는
「정기 체크 안 켬 → 일반」이라고 올바로 답했는데 `_persist` 가 그 답을 버리고
질문 묶음의 종류를 베꼈다. 발행된 묶음은 `SCHEDULED` 가 기본이라 **체크를 안 켠 판까지
전부 정기로 저장**됐다. 함수만 시험하고 **저장된 값을 보는 시험이 없었다.**

## 주의·제약

- 이 가지 외로 푸시 금지(veo-platform: `claude/aeo-graph-ai-mention-diff-ioo4bz`).
- 배포는 **`make deploy` 만**. 오더 없이 밀지 않는다. `VEO_DEPLOY_ORDER` 에 원문 인용.
- **[5/5] 오류 22 는 배포 실패가 아니다** — 이 방이 운영 주소로 못 나가는 것(CONNECT 403).
  판 확인은 `rollout-check.yml`, 엔진 열쇠는 `engine-check.yml` 을 러너로 돌려서 잰다.
- **쉬운 말로 쓴다**(사장님 지시 «앞으로 쉬운말 써») — 「카드」·「패널」 같은 화면 용어 금지.
  봐 달라고 할 때는 **어느 탭 · 어디쯤 · 뭐라고 적혀 있는지** 셋을 적는다. CLAUDE.md 규칙.
- 대장·변경이력에 **「민다·푸시」 금지**(`two-words-only`) — 「커밋」·「배포」 두 낱말만.
- **돈 이야기는 업체 이름을 댄다**(`money-says-whose`).
- 대장 `WORKLIST.md` 상한 **1,300줄**(`ledger-stays-current`).
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01M2Z4aZUvu9XDna8jx9EH3A`.
- 못 잰 값 «—», 지어낸 수치 금지, 의료광고법 준수.

## 되풀이하지 말 것 (오늘 네 번 같은 병)

**저장소가 이미 재어 둔 값을 안 읽고 말했다** — 오류 197(deploy.sh 의 403) ·
198(engine_readiness 가 답하던 조건) · 199(B-14 의 Search Console 열쇠 없음) ·
그리고 「반만 고치고 다 고쳤다고 보고」. 외부 창구를 「쓸 수 있다」고 말하기 전에
**반드시 `/api/providers` 를 먼저 잰다**(`engine-check.yml`).

## 아직 사장님 몫 (대장 §5)

네이버 열쇠(최근 이레 실패 1건 · 만료 의심) · 진단 서버 무응답 · 공공데이터 인증키 ·
심평원 적재(Neon 플랜) · Sentry · 배포 상한(GitHub Actions 무료 분량) ·
Search Console 열쇠(없어서 생성형 AI 보고서를 우리 시스템이 못 읽는다).

## 참고

- veo-platform 환경: `PYTHON=/usr/bin/python3.12 make setup` · `pnpm install` ·
  PostgreSQL(`service postgresql start`, role `root`/비번 `veo`, DB `veo_test`) ·
  `gh` 없으면 `scripts/gh_fallback.sh` 가 대신한다.
- preflight: `PGPASSWORD=veo VEO_TEST_DATABASE_URL="postgresql+psycopg://root:veo@localhost:5432/veo_test" make preflight`
