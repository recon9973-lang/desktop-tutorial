# RESUME (키워드 간략표 방) — 2026-09-18 · **넘겼다. 이 방이 할 일은 없다**

> 상세는 `docs/session-logs/2026-09-18-keyword-brief.md`.
> **코드는 이 저장소에 없다** — `veo-platform` 이다(`add_repo` 로 붙인다, owner `recon9973-lang`).

## 지금까지 (핵심만)

사장님이 화면 사진과 함께 주문하셨다 — *「ANSEO AEO관측에 키워드 탭에서 이미지와 같이
간략하게 보여지는 것도 추가해줘 … 바꾼 키워드 검색하면 누적되어서 계속 보이도록 해줘」*.

키워드 화면에 **간략표**를 세웠다. 한 줄에 한 키워드(키워드 · PC · 모바일 · 총합 · 문서 ·
비율 · 순위), 키워드를 바꿔 조회할 때마다 줄이 쌓인다. 옛 자세한 보고는 「자세히 보기」
뒤에 그대로 있다.

**사진의 「문서」·「비율」·「순위」는 ANSEO 가 재던 값이 아니었다.** 지어내지 않고 사장님께
여쭤 확정한 뒤 새로 재기 시작했다 — 네이버 블로그 검색의 문서 건수(새 표
`keyword_documents`), 문서 ÷ 총합, 앞 열 자리가 어느 채널의 글인지.

```
veo-platform · 가지 claude/loving-planck-wasyyo
  366f734  키워드 탭에 간략표 — 한 줄에 한 키워드, 조회할수록 쌓인다
  c7e47fd  main(0.3.604) 합침 — 대장 충돌 둘을 양쪽 다 살려 풀었다
  e3cdd92  검사 끝 — ANSEO 방에 넘긴다
```

## 바로 이어갈 작업 — **없다. ANSEO 방이 받았다**

사장님 확인 2026-09-18 «ANSEO 방에 넘겨줘». 대장(`docs/WORKLIST.md` 배포 대기)과
현황(`docs/STATE.md`)에 「검사 끝 — ANSEO 방에 넘긴다」로 적어 두었다.

**ANSEO 방이 할 것** (이 방이 하지 않는다):

```
VEO_DEPLOY_ORDER="배포해줘" make deploy
```

- **마이그레이션이 하나 간다** — `20260917docs`(새 표 `keyword_documents`). 되돌리는 길 있음.
- **판 번호는 안 물렸다** — 대기 표 줄이 `—` 그대로다. 나갈 때 `claim_version` 이 물린다.
  미리 적으면 배포가 그 자리에서 선다(2026-09-10 에 실제로 그랬다).

## 나간 뒤에 사장님이 보실 것 (배포가 끝나야 잴 수 있다)

1. **문서·비율·순위 칸이 실제로 차는지** — 네이버 오픈API 열쇠(데이터랩과 같은 것)가
   금고에 있어야 찬다. 없으면 그 세 칸만 `—` 로 나오고 검색 건수는 그대로 나온다.
   이 방은 실서비스를 못 재므로 **확인 못 했다.**
2. **키워드 20개를 한 번에 조회했을 때** 표가 20초 상한에 걸리는지 — 걸리면 남은 줄의
   문서 칸에 「시간이 모자라…」가 뜬다. 상한은 `service.py` 의 `_DOCUMENT_BUDGET_SECONDS`.

## 대기/차단

- **이 방은 `make deploy` 를 못 돌린다** — 작업 환경이 「운영 배포」로 막는다(2026-09-18).
  우회하지 않았다. 배포는 ANSEO 방 몫이고, 그것이 대장이 정한 길이기도 하다.
- 이 방은 실서비스(`veo.seokorea.org`·Railway)를 못 잰다 — egress 막힘.

## 주의·제약

- **어느 사이트인지 먼저 확인한다.** 사장님이 「진단」·「화면이 이상하다」고 하시면 기본값은
  ANSEO(`veo.seokorea.org`)이고 코드는 `veo-platform` 이다. 이 저장소가 아니다.
- **prettier 를 돌리지 않는다** — `veo-platform` 에 prettier 설정이 없어, 돌리면 제 기본값
  (쌍따옴표)으로 파일을 통째로 바꿔 헛 diff 를 만든다. [실측 2026-09-18 · 내가 그랬다]
- 못 잰 값은 `0` 이 아니라 `—`. 지어낸 수치 금지. 사장님께는 「커밋」·「배포」 두 낱말만.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: <이 세션 주소>`. 모델 ID 는 트레일러에만.
- **다른 방 인계를 덮지 않는다** — 루트 `RESUME.md` 는 진단 오진 방 것이다. 방마다 제 파일.

## 참고

- `veo-platform` 개발 환경 세우기(컨테이너는 매 세션 초기화):
  ```
  PYTHON=/usr/bin/python3.12 make setup
  pnpm install --frozen-lockfile
  service postgresql start
  su postgres -c "psql -c \"CREATE ROLE root LOGIN SUPERUSER PASSWORD 'veo'\""
  PGPASSWORD=veo make db-test-create
  ```
  시험을 돌릴 때는 `VEO_TEST_DATABASE_URL` 과 **`VEO_DATABASE_URL` 을 둘 다** 준다 —
  하나만 주면 39건이 수집 단계에서 깨진다(이 컴퓨터에서 실측).
- 현황은 `veo-platform` 의 `docs/STATE.md`, 대장은 `docs/WORKLIST.md`(§1 확정 · §2 현황).
