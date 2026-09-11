# RESUME — 다음 세션 이어가기 (2026-09-11 · s22 마감 · GEO 진단기 전수조사)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-11-s22.md`.
> 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.
> **작업 대상은 `veo-platform`** 이다(`add_repo` 로 붙인다, owner `recon9973-lang`).

## 지금까지 (핵심만)

사장님이 진단 캡처를 주며 *"문제의 url에 #이 들어간 실제 주소가 없는데, 확인해줘"* 하셨다.
**사장님이 옳았다** — `…/#organization` 은 주소가 아니라 JSON-LD 의 이름표다. 그 지적을
따라가 **진단기 결함 셋**을 찾아 고치고 세 판을 냈다. 전부 CI 초록인 커밋만 main 에 올렸다.

```
726df143  참조를 구조로 읽는다(고아 오판) + 조치 카드 10자리 + 관문 근거 눈금(명세 1.7.0)
85e51424  조치 문안 26개를 「어디를·어떻게」로 다시 씀
fa625d62  대장·오류 대장 기록 (판 번호 못 물린 사실 포함)
```

[실측 · 픽스처 16건] 조치 카드 없음 11→0 · 조치 45자 미만 23→0 · 사업 영향 18→0 ·
재확인 22→0. 재발 방지 CI 관문 4개를 세웠다.

## 바로 이어갈 작업

1. **변경이력에 우리 몫을 적었다 — 채점 대기 중**(`18fb021`,
   `deploy-candidate-claude-changelog-our-release`). CI 초록이면 main 으로 올린다.
   > 앞서 「변경이력이 66판 뒤처졌다」고 적었는데 **틀렸다.** 작은따옴표로 찾아 엉뚱한
   > 줄을 읽었다 — 이 파일은 **큰따옴표**를 쓴다. 맨 위는 `0.3.564` 로 코드 판과 같았고,
   > 빠진 것은 우리가 안 적은 우리 몫뿐이었다. **grep 으로 값을 잴 때 따옴표 종류를 먼저 본다.**
2. **venomad 재진단** — 새 판이 도는 것을 확인한 뒤 `www.venomad.com` 을 한 번 돌려,
   「구조화 데이터의 @id가 엔터티 간에 연결되는가」가 통과로 바뀌는지 본다.
   통과면 오진이었던 것, 아니면 실제로 안 엮인 것이고 **이제는 조치 카드가 함께 뜬다.**
3. **판 번호 정리** — 이번 셋은 `claim_version` 없이 나가 다른 방의 `0.3.563` 안에 얹혔다.
   다음 판을 물릴 때 이 사실을 알고 세야 한다(대장 미배포 머리말에 적어 뒀다).

## 대기/차단

- **이 방에서 `make deploy` 가 막힌다**(자동 승인기). 우회 절차는 이것뿐이다 —
  ① 후보 가지에 올려 CI 채점 → ② 초록이면 사장님이 한 줄로 main 에 올린다.
  ```
  git push -f origin HEAD:deploy-candidate-<가지이름을 -로 눕힌 것>
  # CI 초록 뒤
  cd $(mktemp -d) && git init -q && git fetch -q <repo> <후보가지> && \
    git push <repo> FETCH_HEAD:refs/heads/main && echo PUSHED
  ```
  **`claim_version` 이 빠지는 경로라 판 번호·변경이력이 안 물린다**(오류 대장 201).
- **`gh` 는 방마다 다시 깔아야 한다** — `apt-get install -y gh`. REST 는 되고
  **GraphQL·workflow_dispatch 는 403**. CI 로그 내려받기도 egress 차단이라 **못 읽는다** —
  실패 원인은 커밋을 받아 **직접 재현**해서 찾는다(이번에 그렇게 찾았다).
- **veo-platform 개발 환경**(컨테이너는 매번 초기화):
  ```
  /usr/bin/python3.12 -m venv .venv && .venv/bin/pip install -e "apps/api[dev]" -e apps/worker
  pnpm install --frozen-lockfile
  service postgresql start          # 자주 혼자 내려간다. 실패하면 먼저 이것부터 본다
  su postgres -c "psql -c \"CREATE ROLE root LOGIN SUPERUSER PASSWORD 'veo'\""
  printf 'localhost:5432:*:root:veo\n' > ~/.pgpass && chmod 600 ~/.pgpass
  PGPASSWORD=veo make db-test-create
  PGPASSWORD=veo VEO_TEST_DATABASE_URL="postgresql+psycopg://root:veo@localhost:5432/veo_test" make ci-local
  ```
- **실서비스를 못 잰다** — `venomad.com`·Railway·GitHub Actions 로그 전부 egress 차단.

## 주의·제약

- **CI 결과를 종료값으로 읽지 않는다.** 배경 실행 알림의 `exit 0` 은 껍데기의 값이다.
  출력 파일에서 `N passed`/`Error` 줄을 직접 뽑아 근거로 쓴다(오류 대장 195).
- **보고서의 숫자는 표를 만든 그 실행에서 함께 뽑는다**(오류 대장 196).
- **막힌 명령을 손으로 대신할 때는 그 명령의 본문을 먼저 읽는다** — 내가 대신하지 못하는
  단계를 적어 두고, 「끝났다」고 보고하기 전에 남은 일로 올린다(오류 대장 201).
- 대장(`docs/WORKLIST.md`)은 **여러 방이 같이 쓴다.** 다른 방 줄은 건드리지 않는다.
  충돌이 나면 대장은 main 것을 따르고 내 줄만 다시 올린다. 「민다·푸시」 금지 낱말.
- 예시 코드에 **지어낸 사실 금지** — 금액·기간·주소·전화는 `[ ]` 로 비운다(관문이 잡는다).
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: …`. **모델 ID 는 트레일러에만.**
- 사장님께는 「커밋」·「배포」 두 낱말만. 못 잰 값은 «—», 지어낸 수치 금지, 의료광고법 준수.
- **사장님 작업 방식** — 짧게, 실행할 것 하나만. 설명이 길면 되묻게 된다.
  터미널에 붙여넣을 것은 **줄바꿈 없는 한 줄**로 준다(`\` 가 끼면 zsh 가 멈춘다).

## 참고

- 전수조사 보고서: https://claude.ai/code/artifact/3d881174-925a-45d6-9e70-02c37e0d6d6c
  (조치 문안 작업 **전** 상태다. 갱신 필요.)
- 사장님 맥에 `~/veo-platform` **없다.** 임시 폴더로 받아 쓰는 방식으로 드린다.
