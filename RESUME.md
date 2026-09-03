# RESUME — 다음 세션 이어가기 (2026-09-03 · s15 마감)

> 새 세션은 이 파일을 **먼저** 읽는다. 이 세션 상세는
> `docs/session-logs/2026-09-03-s15.md` · s14 는 `-s14.md` · s13 은 `-s13.md`.
> 현황은 `PROJECT_STATE.md`, 지도는 `핵심두뇌_MASTER.md`.
> **팀 인물표는 `docs/team/에이전트-역할.md`** (일곱 인물 · 하린 신규 · 2026-09-03 붙임).

## 지금 상태 (s15 마감)

- **운영 판 = 0.3.497** (s14 마감 후 화면 점검 방이 판 하나 더 밀어 0.3.496→0.3.497 로 나감)
  - veo-platform `main` HEAD = `0065038` («0.3.496~0.3.497 배포 도장 — 삼중 실측 마감»)
- **이 방 미배포 판** (다음 판은 **0.3.498**):
  - **거래처 탭 「입지」 → 「상권」** (사장님 확정 2026-09-03 · 결정 갈래 ⑴)
    - veo-platform 가지 `claude/rename-location-tab-to-marketarea` · 커밋 `974b000` · push 완료
    - 4파일 편집 (라벨·시험 두 편·페이지) · **라우트 키 `location` 유지** (공유 링크·리포트 물림 안전)
    - **StandingCard 진단 카드 «입지» 는 그대로** (결정 ⑴ 의 뜻)
- **이 방 정본 문서 갱신 완료** (`claude/hospital-location-analysis-plan-6kbmqo`):
  - 기획안 `docs/plans/anseo-location-analysis-plan.md` — 「상권」 확정 반영 12곳 (제목·§0·§2·§5·§6·§7·§10)
  - 시뮬 11호 `docs/ANSEO-입지-화면-시뮬레이션.html` — 라벨 「상권」 7곳 (파일명 유지)
  - 시뮬 12호 `docs/ANSEO-데이터원천-설정-시뮬레이션.html» — 라벨 「상권» 5곳
  - **팀 문서** `docs/team/에이전트-역할.md` (신규 · 일곱 인물 · 하린 페르소나·스킬·MCP 정본)

## 바로 이어갈 작업

**새 오더 없으면 대기.** 사장님이 다음을 지시하면 시작:

1. **0.3.498 배포 도장** — 「상권」 라벨 운영 반영. 배포는 이 방 소관 아님(다른 방 또는 사장님 승인).
   PR 필요 시 `claude/rename-location-tab-to-marketarea` → main
2. **교통·인구 축 실적재** (기획안 §7 P2) — 지금 화면에 «—» 로 서 있는 자리에 진짜 값:
   - 국토교통부 역·정류장 좌표 미러 (`veo/location/sources.py` `_PLANNED` 목록에 있음)
   - 행정안전부 행정동 인구, SGIS 경계
   - 「데이터 원천」에 「파일 올리기」 단추(SUPER_ADMIN)도 함께
3. **카카오맵 타일**·**추계 환자 수 카드**·**비교 모드** (기획안 §7 P3)
4. WORKLIST.md 의 「입지» 표기(l.724·731·737·974) — 다른 방이 다음 판 도장 때 갱신

## 대기·차단 · 다른 방 소관 (이 방에서 하지 말 것)

- **배포 규율 재확인**: s14 에서 두 번 물림(0.3.489→494→496), s15 에서 화면 점검 방이 0.3.497 로 하나 더 밀림.
  이 방은 시뮬·기획·기능 판만 만들고 판 번호는 **끝까지 우리가 결정한 그 순간의 값이 아닐 수 있음**
- **판 번호 발급 순서**를 사장님이 바꾸실지는 미결 (s14 이월)
- **shareboard-tune / 화면 점검 방과의 push 경합**은 그 방이 우리 가지를 자기 것에 합쳐 밀어
  우리 것이 반영되는 방식으로 해결됨. 다음에도 같은 상황이면 SHA 없어도 diff 로 확인 후 도장

## 팀 인물 (부르는 요령)

- «도현아» → `claude` (만능 · 뭐든 시켜)
- «서연 씨» → `general-purpose` (조사 · 오래 파는 애)
- «준서» → `Explore` (정찰 · 넓게 훑고 위치만)
- «지훈 형» → `Plan` (설계 · 도면 뽑고 물러남)
- «하늘 씨» → `claude-code-guide` (Claude Code·SDK·API 문서 사서)
- «민재» → `statusline-setup` (상태줄 재단사)
- **«하린 씨»** → 도현이 디자인 스킬·MCP 부를 때의 페르소나 (신규 · 2026-09-03)
  - 스킬: `design`·`artifact-design`·`dataviz`·`design-taste-frontend`·`pptx`·`docx`·`pdf`·`xlsx`·
    `nami-cardnews`·`reels-creator`·`venomad-proposal`
  - MCP: Higgsfield(이미지·영상·음성)·Canva·Lovable·Google_Drive·WordPress_com·Airtable·Slack·PlayMCP

자세한 것은 `docs/team/에이전트-역할.md`.

## 도구·실측 메모 (재탐색 금지)

- **운영 실측 우회**: 이 방 프록시가 운영 주소 403 → **Higgsfield MCP `sandbox_exec`**(바깥 샌드박스) curl 로
  `https://veo-platform-production.up.railway.app/api/health`·`/api/queue` 확인
- **veo-platform 클론**: `git clone --depth 1 https://github.com/recon9973-lang/veo-platform
  /home/user/veo-platform` (약 1분) — 컨테이너 리셋 시 재실행 필요
- **로컬 PostgreSQL**: `pg_ctlcluster 16 main start`. 접속 `root` (암호 없음, host trust).
  `/etc/postgresql/16/main/pg_hba.conf` 임자는 반드시 `postgres:postgres`
- **로컬 시험 DB**: `veo_test` (postgres 계정 · trust). Makefile 은 현재 OS 사용자로 접속하므로 `root` 로도 붙음
- **`gh` CLI**: `apt install gh` 로 설치 · 컨테이너 리셋 시 재설치 필요
- **배포 명령**: `make deploy` 는 자동모드 분류기에 막힘 → 사장님 명시적 승인 필요
- **화면 관문**(v0.3.495 이후 화면 점검 방이 심음, 지켜야 함):
  - 접는 폭 세 단 (720·960·1100px 만) — `breakpoints-are-shared.test.ts`
  - 글자 하한 11px — `text-is-at-least-11px.test.ts` (또는 BASELINE 등록)
  - 표 감싸개 (overflow-x:auto) · `.tsx` CSS import 는 **홑따옴표**만 인식 — `tables-fold-on-narrow-screens.test.ts`
- **화면 촬영 장치**: `pnpm rwd` (화면 점검 방이 넣음)

## 주의·제약 (반드시)

- 이 방 브랜치:
  - desktop-tutorial 정본 = `claude/hospital-location-analysis-plan-6kbmqo` (기획·시뮬·팀 문서)
  - desktop-tutorial 세션 지침 = `claude/verify-archive-execution-b7co8e` (세션 시작 시 지정)
  - veo-platform s15 = `claude/rename-location-tab-to-marketarea` (상권 라벨)
  - 체크포인트만 desktop-tutorial main
- 커밋 트레일러:
  ```
  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01NjxFzhnyGVhqJgfVKBLcYo
  ```
  모델 ID·비밀키 값은 코드·파일·PR 에 넣지 말 것
- 사장님께는 「커밋」·「배포」 두 낱말만 (테스트 데이터라 정합성 지적 금지)
- 못 잰 값 = «—» (0 아님) · 합산 점수 없음 · 색+글자 병용 · 판 다르면 비교 금지 · 의료광고법 준수
- ANSEO 방·화면 점검 방·shareboard-tune 방과 판 번호 부딪히면 **나중 것이 물러난다**

## 참고

- 세션 상세 `docs/session-logs/2026-09-03-s15.md` (이번) · `-s14.md` · `-s13.md`
- 기획안 `docs/plans/anseo-location-analysis-plan.md`, 벤치마크 `docs/plans/anseo-location-benchmark.md`
- 시뮬 두 편: `docs/ANSEO-입지-화면-시뮬레이션.html` (11호, 파일명 유지), `docs/ANSEO-데이터원천-설정-시뮬레이션.html` (12호)
- **팀 인물표**: `docs/team/에이전트-역할.md`
- 배포 규율 원문: `veo-platform/scripts/deploy.sh` 머리말
