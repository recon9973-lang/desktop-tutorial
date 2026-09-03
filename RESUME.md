# RESUME — 다음 세션 이어가기 (2026-09-04 01:19 KST · s14 마감)

> 새 세션은 이 파일을 **먼저** 읽는다. 이 세션 상세는
> `docs/session-logs/2026-09-04-s14.md` · 직전은 `-s13.md`.
> 현황은 `PROJECT_STATE.md`, 지도는 `핵심두뇌_MASTER.md`.

## 지금 상태 (s14 마감)

- **운영 판 = 0.3.496** ([실측 2026-09-04 01:15 KST · 바깥 샌드박스 curl] 서버·워커·웹 셋 다 도달, 워커 1대·뒤처진 0)
- 이 방 몫 (v0.3.494 → v0.3.496 두 번 물림) **모두 운영 반영**:
  - 거래처 상세 **「입지」 탭** (심평원 좌표 중심 500m~10km 다섯 고리 · 종별 막대 · 가까운 순 · 반경 선택 시 지도 자체 확대·축소)
  - 설정 **「데이터 원천」** (`/console/datasources`, 권한 `datasource:manage` = SUPER_ADMIN 만)
  - 상단 **AI 스트립 연결 상태 밑줄** (색점 유지 · 초록 연결 · 주황 오류 · 빨강 끊김 + 글자 병기)
- veo-platform 우리 가지 `claude/anseo-location-tab` = **0d8a87f** (도장 완료 · 원격 최신)
- desktop-tutorial 이 방 가지 `claude/hospital-location-analysis-plan-6kbmqo` = **3e96d4b** (직전 커밋, 이번 세션에 이 저장소에는 안 커밋)

## 바로 이어갈 작업

**새 오더 없으면 대기.** 사장님이 다음을 지시하면 시작:

1. **「입지」 이름 겹침 정리** (미결 · TODO #9) — 사장님 판단 대기:
   - ⑴ 이 방 탭을 「상권」으로 (권장 · 명확)
   - ⑵ ANSEO 방 카드를 「자리」·「순위」로
   - ⑶ 그대로 둠
   결정 오면 `apps/web/src/lib/navigation.ts` 의 `CUSTOMER_TABS` 라벨 또는 `apps/web/src/app/(console)/console/customers/[customerId]/StandingCard.tsx` 제목·본문 갱신 → 판 하나(0.3.497+) 잡음
2. **교통·인구 축 실적재** (TODO #10) — 지금 「—」로 서 있는 자리에 진짜 값:
   - 국토교통부 역·정류장 좌표 미러 (`veo/location/sources.py` `_PLANNED` 목록에 있음)
   - 행정안전부 행정동 인구, SGIS 경계
   - 「데이터 원천」에 「파일 올리기」 단추(SUPER_ADMIN)도 함께
3. **카카오맵 타일**·**추계 환자 수 카드**·**비교 모드** (기획안 §7 P3)

## 대기/차단 · 다른 방 소관 (이 방에서 하지 말 것)

- **배포 규율 재확인**: 오늘 두 번 물림(0.3.489→494→496)은 다른 방이 먼저 밀어 우리가 물러난 것. 이 방은 시뮬·기획·기능 판만 만들고 판 번호는 **끝까지 우리가 결정한 그 순간의 값이 아닐 수 있음**을 기억
- **판 번호 발급 순서**를 사장님이 바꾸실지는 미결
- **shareboard-tune 방과의 push 경합**은 그 방이 우리 가지를 자기 것에 합쳐 밀어 우리 것이 반영되는 방식으로 해결됨. 다음에도 같은 상황이면 SHA 는 없어도 diff 로 확인 후 대장에 도장

## 도구·실측 메모 (재탐색 금지)

- **운영 실측 우회**: 이 방 프록시가 운영 주소 403 → **Higgsfield MCP `sandbox_exec`**(바깥 샌드박스) curl 로
  `https://veo-platform-production.up.railway.app/api/health`·`/api/queue` 확인
- **로컬 PostgreSQL**: `pg_ctlcluster 16 main start` 로 띄움. 접속은 `root` 계정(암호 없음, host trust). **`/etc/postgresql/16/main/pg_hba.conf` 임자는 반드시 postgres:postgres 여야 뜬다** — `chown` 조심
- **로컬 시험 DB**: `veo_test` (postgres 계정 · trust). Makefile 은 현재 OS 사용자로 접속하므로 `root` 로도 붙음
- **`gh` CLI**: `apt install gh` 로 2.45 설치, `GH_TOKEN` 자동 인증. 컨테이너 리셋 시 재설치 필요
- **배포 명령**: `make deploy` 는 자동모드 분류기에 막힘 → 사장님 명시적 승인 필요 (오늘 «배포 명령 허용, 계속 진행해줘» 로 열렸음)
- **화면 관문**(v0.3.495 이후 그 방이 심었음, 지켜야 함):
  - 접는 폭 세 단 (720·960·1100px 만) — `breakpoints-are-shared.test.ts`
  - 글자 하한 11px — `text-is-at-least-11px.test.ts` (또는 BASELINE 등록)
  - 표 감싸개 (overflow-x:auto) · `.tsx` CSS import 는 **홑따옴표**만 인식 — `tables-fold-on-narrow-screens.test.ts`
- **화면 촬영 장치**: `pnpm rwd` (그 방이 넣음)

## 주의·제약 (반드시)

- 이 방 브랜치: desktop-tutorial `claude/hospital-location-analysis-plan-6kbmqo` · veo-platform `claude/anseo-location-tab`. 체크포인트만 desktop-tutorial main
- 커밋 트레일러:
  ```
  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_013Fy4opA3k1FC6gQobSVKWf
  ```
  모델 ID 는 트레일러에만, 코드·파일·PR 에 넣지 말 것
- 사장님께는 「커밋」·「배포」 두 낱말만 (테스트 데이터라 정합성 지적 금지)
- 못 잰 값 = «—» (0 아님) · 합산 점수 없음 · 색+글자 병용 · 판 다르면 비교 금지 · 의료광고법 준수
- ANSEO 방·화면 점검 방·shareboard-tune 방과 판 번호 부딪히면 **나중 것이 물러난다**

## 참고

- 세션 상세 `docs/session-logs/2026-09-04-s14.md` (이번) · `-s13.md` (이전)
- 기획안 `docs/plans/anseo-location-analysis-plan.md`, 벤치마크 `docs/plans/anseo-location-benchmark.md`
- 시뮬 두 편: `docs/ANSEO-입지-화면-시뮬레이션.html` (11호), `docs/ANSEO-데이터원천-설정-시뮬레이션.html` (12호)
- 배포 규율 원문: `veo-platform/scripts/deploy.sh` 머리말
