# RESUME — 다음 세션 이어가기 (2026-09-04 · s16 마감)

> 새 세션은 이 파일을 **먼저** 읽는다. 이 세션 상세는
> `docs/session-logs/2026-09-04-s16.md` · s15 는 `2026-09-03-s15.md` · s14 는 `-s14.md`.
> 현황은 `PROJECT_STATE.md`, 지도는 `핵심두뇌_MASTER.md`.
> **팀 인물표는 `docs/team/에이전트-역할.md`** (일곱 인물 · 하린).

## 지금 상태 (s16 마감)

- **운영 판 = 0.3.497** (s15 마감 시점 그대로 · 이 세션은 배포 없음)
- **veo-platform 이 방 미배포 판** = `claude/rename-location-tab-to-marketarea` `974b000` (거래처 탭 「입지→상권」, s15 에서 밀어 놓음, 다른 방/사장님 승인 배포 대기)
- **다른 방 §7 P2 진행 중** (교통·인구 실적재 · s15 이후 사장님이 다른 방에 오더)
  - 근거: `docs/plans/anseo-github-data-inventory.md` §2 마지막 줄 + 문서 끝 «사장님이 고르실 것» 1번
  - 이 방은 뛰지 않음 (규율 준수)
- **이 방 §7 P3 준비 완료** (`claude/hospital-location-analysis-plan-6kbmqo` 문서만):
  - `docs/plans/anseo-location-p3-plan.md` — 정본 도면 (카카오맵·추계 환자 수·비교 모드 세 항목)
  - `docs/ANSEO-상권-P3-시뮬레이션.html` — 시뮬 13호 (5화면·정상·폴백·3단·비교 두 종)

## 바로 이어갈 작업

**새 오더 없으면 대기.** 사장님이 다음을 지시하거나 배포 상황이 바뀌면 시작:

### 1. 다른 방 §7 P2 배포 감시 (매 세션 시작 시)

- `cd /home/user/veo-platform && git fetch origin && git log --oneline origin/main -5` 로 확인
- 다음 판 도장(0.3.498? 그 뒤?) 이 뜨고 `sources.py` `_PLANNED` 자리에 로더가 실제로 심어졌는지 확인
- 배포 확인되면 아래 2번으로

### 2. §7 P3 도면대로 코드 얹기 (P2 배포 후)

`docs/plans/anseo-location-p3-plan.md` §6 순서대로:

1. 새 가지 (예: `claude/anseo-location-p3`) 로 갈아탐
2. `sources.py` 에 `hira_disease_stats` · `kakao_map_js` 두 행 추가
3. `core/settings.py` 에 `VEO_KAKAO_MAP_JS_KEY` 추가
4. `schemas.py` 에 `PatientEstimatePayload` · `LocationComparePayload` 추가
5. `service.py` 에 `_patient_estimate_of` · `compare_location` 순수 함수
6. `router.py` 에 `/compare` 엔드포인트 + `patient_estimate`·`map_provider` 응답 추가
7. 웹: `RingMapKakao.tsx` · `LocationCompareTab.tsx` 신규 · `LocationTab.tsx` 조건 분기
8. 시험 4벌 (`test_patient_estimate.py` · `test_compare.py` · `LocationTab.test.tsx` · `LocationCompareTab.test.tsx`)
9. `pnpm rwd` 화면 관문 (720·960·1100px · 11px 하한 · 표 감싸개) 통과
10. 커밋 · 판 안 정함 · 다른 방/사장님 도장 대기

### 3. 사장님 열쇠·파일 (P3 코드 얹은 뒤)

- **카카오 JS 열쇠** — 사장님 등록 · 도메인 화이트리스트
- **진료과별 수진율 상수 표** — 심평원 통계지표 자료 → `apps/api/data/hira_disease/<판>/prevalence.csv`
- 인구·경계는 다른 방 P2 가 심어놓음

### 4. WORKLIST.md 「입지» 표기 (l.724·731·737·974) — 다른 방 소관 · 이 방 안 만짐

## 대기·차단 · 다른 방 소관 (이 방에서 하지 말 것)

- **§7 P2 (교통·인구 실적재)** — 다른 방이 사장님 오더 받아 진행 중. `sources.py::_PLANNED` · `LocationTab.tsx` «—» 셀 · `datasources/page.tsx` 「올리기 단추」 자리 전부 다른 방 손
- **배포 규율 재확인**: 이 방은 시뮬·기획·기능 판만 만들고 판 번호는 다른 방/사장님이 결정
- **판 번호 발급 순서**를 사장님이 바꾸실지는 미결 (s14 이월)

## 팀 인물 (부르는 요령)

- «도현아» → `claude` (만능)
- «서연 씨» → `general-purpose` (오래 파는 조사)
- «준서» → `Explore` (정찰)
- «지훈 형» → `Plan` (도면)
- «하늘 씨» → `claude-code-guide` (Claude Code·SDK·API 문서)
- «민재» → `statusline-setup` (상태줄)
- **«하린 씨»** → 도현이 디자인 스킬·MCP 부를 때의 페르소나 (신규 2026-09-03)

자세한 것은 `docs/team/에이전트-역할.md`.

## 도구·실측 메모 (재탐색 금지)

- **운영 실측 우회**: 이 방 프록시가 운영 주소 403 → Higgsfield MCP `sandbox_exec` 로 우회
- **veo-platform 클론**: `git clone --depth 1 https://github.com/recon9973-lang/veo-platform /home/user/veo-platform` (약 1분) · 컨테이너 리셋 시 재실행
- **로컬 PostgreSQL**: `pg_ctlcluster 16 main start` · 접속 `root` · `pg_hba.conf` 임자는 `postgres:postgres`
- **로컬 시험 DB**: `veo_test` (postgres · trust)
- **`gh` CLI**: `apt install gh` · 컨테이너 리셋 시 재설치
- **배포 명령**: `make deploy` 자동모드 분류기에 막힘 → 사장님 명시 승인 필요
- **화면 관문**(v0.3.495 이후 화면 점검 방이 심음):
  - 접는 폭 세 단 (720·960·1100px) — `breakpoints-are-shared.test.ts`
  - 글자 하한 11px — `text-is-at-least-11px.test.ts`
  - 표 감싸개 (overflow-x:auto) · `.tsx` CSS import 는 홑따옴표만 — `tables-fold-on-narrow-screens.test.ts`
- **화면 촬영**: `pnpm rwd`

## 주의·제약 (반드시)

- 이 방 브랜치:
  - desktop-tutorial 정본 = `claude/hospital-location-analysis-plan-6kbmqo` (기획·시뮬·팀·P3 도면)
  - desktop-tutorial 세션 지침 = `claude/verify-archive-execution-b7co8e` (세션 시작 지정, 이 방 문서 작업은 정본 가지)
  - veo-platform s15 = `claude/rename-location-tab-to-marketarea` (상권 라벨 · 배포 대기)
  - **P3 코드는 새 가지 `claude/anseo-location-p3` 팔 것 (P2 배포 뒤)**
- 커밋 트레일러:
  ```
  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01NjxFzhnyGVhqJgfVKBLcYo
  ```
  모델 ID·비밀키는 코드·파일·PR 에 넣지 말 것
- 사장님께는 「커밋」·「배포」 두 낱말만 (테스트 데이터라 정합성 지적 금지)
- 못 잰 값 = «—» (0 아님) · 합산 점수 없음 · 색+글자 병용 · 판 다르면 비교 금지 · 의료광고법 준수
- 판 부딪히면 **나중 것이 물러난다**

## 참고

- 세션 상세 `docs/session-logs/2026-09-04-s16.md` (이번) · `-s15.md` · `-s14.md`
- 기획안 원본 `docs/plans/anseo-location-analysis-plan.md`
- **P3 정본 도면 `docs/plans/anseo-location-p3-plan.md` (s16 신규)**
- 다른 방 공개 자료 조사 `docs/plans/anseo-github-data-inventory.md`
- 시뮬 세 편: 11호 상권(파일명 유지) · 12호 데이터 원천 · **13호 상권 P3 (s16 신규)**
- 팀 인물표 `docs/team/에이전트-역할.md`
- 배포 규율 원문 `veo-platform/scripts/deploy.sh` 머리말
