# RESUME (삭제·휴지통 방) — 2026-09-14

> 이 저장소에는 인계가 여럿이다. **이것은 「삭제·휴지통 방」 것이다.**
> 상세는 `docs/session-logs/2026-09-14-s23-trash-30d.md`.
> **구현은 `veo-platform` 에 있다** — 이 저장소에는 ANSEO 문서만 있다.

## 지금까지 (핵심만)

사장님이 「등록된 업체 삭제 단추 + 30일 휴지통」을 오더하셨고, 이어서 「등록되지 않은
업체(테스트한 업체)도」, 그리고 사양을 확정해 주셨다 —
**«삭제-휴지통 이동-휴지통 내에 의무 보관 30일-30일 후 자동삭제-30일 전 원할시 바로 삭제 가능»**.

전부 만들어 `veo-platform` 가지 **`claude/customer-trash-30d`** 에 커밋 둘이 올라가 있다.

```
966ca38  지운 업체를 30일 담아 두는 자리를 만든다 — 재 본 자리도 지울 수 있게
724ce55  30일은 못 지우는 기간이 아니라 저절로 없어지는 때다 — 자동삭제를 넣고 잠금을 푼다
```

둘째가 첫째의 **오독을 정정한 것**이다. 처음에 「의무 보관 30일」을 최소 보관 기간으로
읽어 30일 전 영구삭제를 409 로 막아 놨는데, 사장님 뜻은 **자동삭제 시점**이었다.

## 바로 이어갈 작업

1. **배포** — 이것 하나만 남았다. 사장님이 «배포해» 하셨으나 **하네스가 막았다**(아래).
   ```bash
   cd veo-platform
   git checkout claude/customer-trash-30d
   git pull origin claude/customer-trash-30d      # 724ce55 인지 확인
   make deploy
   ```
   `make deploy` 가 preflight → 후보 가지 채점 → **초록불일 때만** main 으로 민다.
   판 번호(0.3.577)는 나갈 때 `claim_version` 이 스스로 물린다 — 미리 잡지 않는다.
2. **나간 뒤 확인** — 콘솔 `/console/customers` 에서 줄마다 「삭제」, 제목 옆에 「테스트
   자리」·「휴지통」이 보이는지. 휴지통에서 「그냥 두면 N일 뒤 자동삭제」가 붙는지.
3. **대장 정리** — 나가면 `docs/WORKLIST.md` 배포 대기 목록에서 **이 방 줄만** 지운다
   (「업체 삭제 단추 · 휴지통 · 30일 자동삭제」). 다른 방 줄은 건드리지 않는다.

## 대기/차단

- **배포 명령이 이 방에서 막힌다.** `make deploy` 가 하네스 auto mode 분류기에 「Production
  Deploy」로 걸려 거절된다. 사장님이 직접 돌리시거나, `.claude/settings.json` 에 Bash 권한
  규칙을 더하셔야 한다. **우회하지 않았다.**
- **배포 대기 목록에 여섯 줄이 있고 이 방 것은 하나다.** 나머지 다섯은 다른 방
  (`claude/same-page-same-verdict` 등)이 만든 것으로 이 방이 읽지도 검사하지도 않았다.
  함께 내보내려면 그 가지들을 합치고 검증하는 일이 따로 필요하다.
- **STATE.md 와 WORKLIST.md 가 어긋나 있다** — STATE 는 미배포 「없다」였는데 WORKLIST
  배포 대기에는 0.3.576 다섯 줄이 있었다. 이 방은 재지 않았으므로 **어긋남만 적어 두었다.**
  나갈 때는 대기 표를 원천으로 본다.

## 주의·제약

- **가지**: veo-platform 은 `claude/customer-trash-30d`, desktop-tutorial 은
  `claude/zealous-cannon-16h04s`. 그 밖으로 푸시 금지.
- **배포는 `make deploy` 만.** 오더 없이 밀지 않는다. 하루 2회 상한.
- **이 컨테이너의 PostgreSQL 이 잘 내려간다.** preflight/시험이 통째로 빨간불이면
  `pg_isready -h localhost -p 5432` 부터 본다 — 코드가 아니라 DB 가 죽은 것일 수 있다.
  `service postgresql start` 로 살린다. [실측 2026-09-14] 한 세션에 두 번 났다.
- veo-platform 개발 환경(컨테이너는 매번 초기화):
  ```
  PYTHON=/usr/bin/python3.12 make setup && pnpm install --frozen-lockfile
  service postgresql start
  su postgres -c "psql -c \"CREATE ROLE root LOGIN SUPERUSER PASSWORD 'veo'\""
  PGPASSWORD=veo make db-test-create
  ```
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: <이 세션 URL>`. **모델 ID 는 트레일러에만** — 커밋·PR·코드 본문에 넣지 않는다.
- 사장님께는 「커밋」·「배포」 두 낱말만. 못 잰 값 «—», 지어낸 수치 금지, 의료광고법 준수.

## 참고

- veo-platform 은 `add_repo`(owner `recon9973-lang`) 로 붙인다 → `/home/user/veo-platform`.
- 그 저장소의 대장은 `docs/WORKLIST.md`(§1 확정 · §2 현황 · §4 남은 것), 지금 상태는
  `docs/STATE.md` 한 장. 날짜별 기록 `WORKLIST-HISTORY.md` 는 **평소에 안 연다.**
- 이 저장소 현황은 `PROJECT_STATE.md`, 지도는 `핵심두뇌_MASTER.md`.
