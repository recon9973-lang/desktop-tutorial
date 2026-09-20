# RESUME — 입지 피라미드·상권 칸 방 (2026-09-20 23:20 KST · **둘 다 나감 · 이 방 할 일 없음**)

<!-- 가지: claude/wonderful-pascal-my56sw -->

**작업은 `veo-platform`(ANSEO · veo.seokorea.org)에서 한다.** 세션 시작 때
`add_repo recon9973-lang/veo-platform` → `/home/user/veo-platform` 에 clone → 같은 이름 가지
`claude/wonderful-pascal-my56sw` 를 checkout. 이 저장소(desktop-tutorial)는 인계본만 둔다.

## 지금까지 (핵심만)
- 「입지」 인구 두 피라미드 같은 높이 + 시군구 칸 아래 행정동 표 + 표 머리말 쉬운 말 → **0.3.635 로 나갔다**(ANSEO 방이 합쳐 냄).
- 「입지」 상권 칸 업종 막대: 이름 칸 44px 고정 → 목록 전체 한 격자·이름 안 꺾임 · 출처 문장 한 번만 → 코드 `e669f24a` → **0.3.639 로 main 에 닿았다**(ANSEO 방 · 22:42 KST · main `6c33f1c8`). 이 방은 운영 화면을 못 봐 «—» — 사장님 화면 한 장으로 확인.
- 가지 머리 `f932b67f` = main(0.3.638) 합침 + 판 0.3.639 물림(셋 같은 값) + 변경이력·대기 표·HISTORY 다 적음. 관문(worklist·changelog·openapi) 초록.
- 이 방에서 `make deploy` 두 번: ① 시험 DB 꺼져 실패 ② 점검·CI 초록인데 [4/5] 에서 main 이 움직여 거절. 그 뒤 main 에 **배포 방 관문**(`scripts/deploy_room_gate.sh` · `git config veo.deploy-room=anseo` 아니면 거부)이 들어와 이 방은 이제 `make deploy` 를 못 돌린다.

## 바로 이어갈 작업
0. **끝.** 상권 칸 고침이 0.3.639 로 main 에 닿았다(22:42). 새 지시가 올 때까지 할 일 없음. (기록) 사장님 답 = «인계»(22:1x). 인계문 `docs/HANDOFF-2026-09-20-store-bars.md`(veo-platform · 가지 머리 `1a77704c`) 를 남겼다. ANSEO 방이 합쳐 낸다. 이 방은 새 지시가 올 때까지 할 일이 없다 — 새 지시면 먼저 main 이 상권 칸 고침(`e669f24a`)을 품었는지 본다.
1. (참고 · 끝난 갈래) 사장님 답을 본다 — (가) ANSEO 방에 「인계」(기본 · 대기 표에 가지 적힌 줄 있음) / (나) 사장님이 이 방을 배포 방으로 정하시면 그때만 `git config veo.deploy-room anseo` 넣고 `VEO_DEPLOY_ORDER="<원문>" VEO_TEST_DATABASE_URL=postgresql+psycopg://root:root@localhost:5432/veo_test make deploy`.
2. 배포 전 `git fetch origin main && git merge origin/main` — main 이 움직였으면 판이 또 밀린다(변경이력 맨 위 내 항목의 번호·`__init__`·`openapi`·대기 표·HISTORY 제목을 main+1 로).
3. 배포 뒤 사장님 화면 확인 부탁: 「입지」 탭 → 「상권」 칸 업종 막대 줄 간격 같은가 · 「사는 사람」 두 피라미드 높이 같은가.

## 대기/차단
- ~~사장님 결정~~ → «인계»로 정해짐. ANSEO 방이 낼 때까지 미배포.
- 원격 가지에 낡은 판 물림 커밋 `de377bce` 이력이 남아 있다(코드는 0.3.635 로 나감). 강제 밀기는 허가 장치가 막음 · 해 없음.

## 주의·제약
- 시험 DB: `pg_ctlcluster 16 main start` · 역할 root(비번 root) · DB veo_test — 세션마다 새로.
- 이 방 `.venv` 는 python3.12 로 `make setup PYTHON=python3.12`. 웹은 `pnpm install --frozen-lockfile`.
- 커밋·PR·코드에 모델 ID 금지 · 못 잰 값은 «—» · 배포는 `make deploy` 만.

## 참고
- veo-platform: `docs/STATE.md`(한 장) · `docs/WORKLIST.md` §2 대기 표 · `docs/HANDOFF-2026-09-20-pyramid-same-size.md`.
- 여기: `PROJECT_STATE.md` · `핵심두뇌_MASTER.md`.
