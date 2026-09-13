# RESUME — 모션 방 (2026-09-13 23:2x KST · s23 마감)

> 이 저장소에는 인계가 여럿이다. **이 파일은 모션 방 것이다.** 상세는
> `docs/session-logs/2026-09-13-s23-motion-port.md`. 다른 방 RESUME 은 건드리지 않는다.

## 지금까지 (핵심만)

Lovable 시안(ANSEO 콘솔)을 **디자인 원본으로 확정**하고, 거기 정해진 `motion-*` 체계를
`veo-platform` 으로 옮겼다. **시간·굴곡은 `tokens.css` 토큰 한 벌**, **움직임은 새 파일
`packages/ui/src/motion.css` 전역 유틸리티**로 갈라 옮겼다.

덮인 범위 — 공용 그래픽 8 · `components/infographic` 13 · 거래처(고리·점·피라미드·곡선·
게이지) · AEO(언급 점유·출처 행렬) · 대시보드 · 리포트 · 공용 조각(머리줄 두 메뉴·엔진
점·진단서) · 공유 리포트 · 콘솔 화면 등장 차례. 상권 화면의 **빈 상자 850px** 와 목록 칸
글자 단위 절단도 함께 고쳤다. 죽은 규칙 14(화면 7 + 유틸리티 7)를 지웠다.

**2026-09-13 23:0x KST 에 판 0.3.574 로 나갔다**(가지 `claude/anseo-motion-port` →
CI 초록 → main `a8589c4` · 도장 `07dbd05`). 한 판에 옆 방의 오류 210 수정이 함께 나갔다.

## 바로 이어갈 작업

1. **실서비스 확인 — 아직 못 쟀다.** 이 방은 `veo.seokorea.org` 에 못 닿는다(응답 000 ·
   egress 차단). 콘솔 화면 아래 **판 표시가 0.3.574** 인지, 화면이 제목 → 지표 → 패널
   차례로 뜨는지, 막대가 왼쪽에서 자라는지를 **사람 눈으로** 한 번 봐야 끝난다.
   (사장님이 2026-09-13 «확인했어» 라고 하셨다 — 무엇을 확인하셨는지 원문은 그 한 마디뿐이라,
   판 표시까지 보신 것인지는 이 방이 단정하지 않는다.)
2. **어색한 자리가 보이면 그 화면만 손본다.** 값을 만드는 움직임은 없다는 규칙(대장 §1-C23)
   안에서 고친다 — 밝기·진하기가 곧 값인 그림은 색을 건드리지 않는다.
3. 남은 것은 없다. 화면 쪽 그림은 전부 덮였다.

## 대기/차단

- **실서비스 관측을 이 방에서 못 한다** — `veo.seokorea.org`·Railway 전부 egress 차단.
  판 확인은 사장님 화면이거나, 닿는 방에서만 된다.
- 배포는 `VEO_DEPLOY_ORDER="사장님 원문"` 없이는 안 나간다(관문).

## 주의·제약

- 작업 저장소는 **`recon9973-lang/veo-platform`**(`add_repo` 로 붙인다 → `/home/user/veo-platform`).
  이 저장소(desktop-tutorial)에는 기록만 남긴다. 가지 `claude/tender-bell-wtempg`.
- **veo-platform 환경 세우기**: `PYTHON=/usr/bin/python3.12 make setup` · `pnpm install
  --frozen-lockfile` · `service postgresql start` · `su postgres -c "psql -c \"CREATE ROLE
  root LOGIN SUPERUSER PASSWORD 'veo'\""` · `PGPASSWORD=veo make db-test-create`.
  **postgres 는 세션 중에 죽는다** — 점검이 빨간불이면 먼저 `pg_isready`.
- **방이 여럿이라 main 이 작업 중에 움직인다.** 배포 직전 `git fetch` 로 보고, 밀기 전이면
  멈추고 합친다. 오류 대장 번호도 자주 겹친다 — 먼저 올라간 쪽이 그 번호를 갖는다.
- 못 잰 값은 «—». 지어낸 수치 금지. 모델 ID 는 커밋 트레일러에만.

## 참고

- 규칙: veo-platform `docs/WORKLIST.md` **§1-C23**(화면 모션 확정) · 현황 `docs/STATE.md`
- 이 방이 적은 오류: `docs/CORRECTIONS.md` **209**(화면 차례) · **212**(없는 화면에 걸었다고 보고)
- 시안: Lovable 프로젝트 `c99930c9-cf5b-4586-855c-f9a913d79f15` (korean's Lovable)
