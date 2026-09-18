# RESUME — 오류 상세 방 (2026-09-17 17:2x KST · s27 마감)

> **이 파일이 오류 상세 방 것**이다. 루트 `RESUME.md` 는 다른 방(재진단 텀 방) 것이니 안 건드린다.
> 이 세션 상세: `docs/session-logs/2026-09-17-s27-error-details.md`
> 현황 `PROJECT_STATE.md` · 지도 `핵심두뇌_MASTER.md`

## 지금까지 (핵심만)

- **운영 판 = 0.3.604** — [실측 2026-09-17 17:10 KST · 바깥 샌드박스 curl]
  진단 서버 `0.3.604` · 워커 `["0.3.604"]` 1대 · 웹 `0.3.604`
- **v0.3.602 — 재 본 자리 탭·승격** (커밋 `a364d7fe`) · 사장님 «A안으로 가»
  탭(거래처·테스트 자리·휴지통) · 「거래처로 올리기」(주소 미리 채워 **이력째 승격**) ·
  「마지막 진단」 칸 · `isCustomerScopePath` 가 `tests`·`trash` 를 상세로 오인해
  **머리줄이 통째로 사라지던 것** 수정
- **v0.3.604 — 하루 배포 상한 해제** (커밋 `beec0eec`) · 사장님 «상한 풀어»
  기본 2 → **0(안 셈)** · 가르는 것을 날짜에서 **숫자**로 · `preflight.sh` 가 상한을
  `deploy.sh` 에서 읽음 · 세는 대상을 배포와 맞춤 · `--limit 20` 눈금 참 고침
- 이 방 가지: veo-platform `claude/deploy-limit-released`(= main) ·
  desktop-tutorial `claude/error-details-analysis-q6nlxf`

## 바로 이어갈 작업

1. **v0.3.604 도장** — `docs/WORKLIST.md` 대기 표의 `0.3.604` 줄은 나갔으니 뺀다.
   **먼저 `git show origin/main:docs/WORKLIST.md | grep 0.3.604` 로 이미 빠졌는지 본다** —
   ANSEO 방이 주기적으로 정리하므로 이번에도 0.3.602 도장 커밋이 그렇게 쓸모없어졌다.
2. **수집 느림(장당 10.3초) 원인** — 다음 진단 뒤 Railway 로그의 `seo.scan.egress` 줄을 읽는다.
   `attempted=0` 이면 한국 경유와 무관 · `direct_failed=133` 이면 경유가 지고 있다.
   **재기 전에는 고치지 않는다**(라우팅 고정안은 감사에서 기각 — 시간당 호출 상한과
   요청 간격을 함께 건너뛰어 거래처 서버를 쉼 없이 두드린다).
3. **옛 실패 21·33 자연 감소 관찰** (롤링 7일 창).

## 대기/차단

- 없음. 사장님께 여쭌 것(배포 상한)은 «상한 풀어» 로 정해져 반영됐다.

## 이번에 값비싸게 배운 것 (다음 방이 겪지 말 것)

- **판 번호를 미리 잡지 마라.** 변경이력·`__init__.py`·대기 표가 어긋나면 `claim_version` 이
  「이미 그 번호를 쓰는 항목이 있다」로 **[1/4] 에서 선다.** 번호는 **나갈 때** 정해진다.
  새 항목을 쓸 때는 `make bump-version TO=…` 로 **여섯 자리를 함께** 맞춘다.
- **채점 15분 사이에 main 이 움직인다.** v0.3.602 는 네 번 물러났고 **채점은 네 번 다 초록**이었다.
  밀기 직전에 `gh run list --branch deploy-candidate-…` 로 다른 방이 도는지 보고 창이 빈 때 건다.
- **`git add -A` 로 충돌 자국을 커밋에 담지 마라** — `docs/DEPLOY-ORDER-LOG.md` 에
  `<<<<<<<` 가 딸려 들어갔다(점검 ⑥이 잡았다).
- **시험이 주석을 코드로 세지 않게 하라** — 내가 주석에 인용한 옛 문구로 시험이 **우연히
  초록**이 됐다. 셸 시험은 `_without_notes`, 웹은 `withoutNotes` 로 주석을 걷고 잰다.
- **[5/5] 빨간불은 실패가 아닐 수 있다** — 이 방 프록시가 운영 주소에 못 닿는다.
  «도달 못 했다» 가 아니라 «모른다» 다. 바깥에서 재는 길은 아래에.
- **컨테이너는 세션마다 초기화된다** — `make deploy` 가 ci-local·test-db 에서 죽으면
  거의 항상 **PostgreSQL 이 안 떠 있는 것**이다.

## 주의·제약 (반드시)

- **어느 사이트인지 먼저 확인한다** — 사장님이 「진단」·「화면」이라 하시면 기본값은
  **ANSEO(`veo.seokorea.org` = `veo-platform`)**. 이 저장소는 베놈 마케팅 사이트다.
- **채팅에 API 열쇠·비밀키 붙여넣기 금지** — 콘솔 「외부 연결 열쇠」로 사장님이 직접
- **`main` 에 바로 커밋하지 않는다.** 가지에서 작업하고, **배포는 오더 없이 밀지 않는다**
- **루트 `RESUME.md` 를 덮지 않는다** — 방마다 `RESUME-<방>.md` 다
- 커밋 트레일러:
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_017X76hxg2bA4a55mGynjduU
  ```
  모델 ID 는 커밋·PR·코드에 넣지 않는다
- 사장님께는 **쉬운 말** · 「커밋」·「배포」 두 낱말만 (테스트 데이터라 정합성 지적 금지)
- 못 잰 값 = «—» (0 아님) · 합산 점수 없음 · 색+글자 병용 · 판 다르면 비교 금지 · 의료광고법 준수
- **빈 자리를 남기지 않는다** — 한 줄은 8칸+4칸처럼 합이 꽉 차게

## 도구·실측 메모 (재탐색 금지)

- **운영 판 재는 길** (이 방 프록시가 운영 주소 403) — Higgsfield MCP `sandbox_exec` 로:
  ```
  curl -s https://veo-platform-production.up.railway.app/api/health   # 진단 서버 판
  curl -s https://veo-platform-production.up.railway.app/api/queue    # 워커 판
  curl -sL https://veo.seokorea.org/login | grep -oE '0\.3\.[0-9]+'   # 웹 판
  ```
- **배포**: `VEO_DEPLOY_ORDER="<사장님 문장>" make deploy`. 오더 문장 없으면 거절된다.
  **파이프(`| tail`)로 받지 말 것** — 버퍼에 갇혀 진행이 안 보인다. `> /tmp/deploy.log 2>&1` 로.
  **하루 배포 상한은 이제 없다**(0.3.604). 되걸려면 `VEO_DEPLOY_LIMIT_PER_DAY=2`.
- **판 물리기**: `make bump-version TO=0.3.60X` 가 기계 넷을 맞춘다. 사람이 쓸 글 둘이 남는다 —
  변경이력 맨 위 항목 · 대장(§2 머리말 · 대기 표 · 이력 제목). 그다음 대장 관문 다섯을 돌린다.
- **화면 글 상한 60자** — `apps/web/src/lib/screen-text-stays-short.test.ts`. 까닭은 `PageHelp` 로
- **`Date.now()` 를 서버 부품 안에서 부르면 eslint `react-hooks/purity` 가 막는다** —
  시각은 `listCompanyPage` 가 주는 `page.now` 를 쓴다
- **로컬 PostgreSQL**: `pg_ctlcluster 16 main start` · `root` 계정(암호 없음) · `veo_test`
- **veo-platform 은 Python 3.12**: `PYTHON=python3.12 make setup`

## 참고

- 손댄 자리(0.3.602): `apps/web/src/app/(console)/console/customers/`
  (`CustomerTabs.tsx` 신설 · `page.tsx` · `tests/page.tsx` · `trash/page.tsx` ·
  `CompanyForm.tsx` · `new/`) · `apps/web/src/components/ConsoleNav.tsx`
- 손댄 자리(0.3.604): `scripts/deploy.sh` · `scripts/preflight.sh` ·
  `apps/api/tests/release/test_ci_paths.py` · `apps/api/scripts/export_ledger_facts.py`
- 배포 규율 원문: `veo-platform/scripts/deploy.sh` 머리말
