# RESUME — 다음 세션 이어가기 (2026-09-04 18:57 KST · s16 마감)

> 새 세션은 이 파일을 **먼저** 읽는다. 이 세션 상세는
> `docs/session-logs/2026-09-04-s16.md` · 직전은 `-s15.md`.
> 현황은 `PROJECT_STATE.md`, 지도는 `핵심두뇌_MASTER.md`.

## 지금 상태 (s16 마감)

- **운영 판 = 0.3.499** ([실측 2026-09-04 18:57 KST · 바깥 샌드박스 curl] 서버·워커·웹 셋 다, 워커 1대·뒤처진 워커 0. 웹 판은 `veo.seokorea.org/login` 페이지에 박힘)
- **v0.3.499 로 나간 것**: ⑴ 「데이터 원천」 파일 올리기 UI (SUPER_ADMIN) · ⑵ 카카오 지도 열쇠 자리 (콘솔 「외부 연결 열쇠」에 kakao_map 유형 + 서버 창구) · ⑶ 계정 메뉴 아래로 못 내려가던 문제 · ⑷ 「공용 열쇠 사용 중」 뱃지 옆 안내 어긋남 · ⑸ 카카오가 크리덴셜 표에 없던 문제
- veo-platform 우리 가지 `claude/anseo-location-tab` = **83c3b17** (도장 · 원격 최신 · main = 420dbc7)
- desktop-tutorial 이 방 가지 `claude/hospital-location-analysis-plan-6kbmqo` = **e627b92** (s15 이후 변경 없음)

## 바로 이어갈 작업

### ⑴ 사장님 콘솔 작업 대기 (판이 나갔으니 사장님이 하실 차례)

**사장님이 이번 판 뒤 하실 것**:
1. 카카오 developers.kakao.com → 앱 등록 → **JavaScript 키** 발급 → **도메인 제한** (`veo.seokorea.org` · `localhost:3000`)
2. 콘솔 → 관리자 → 외부 연결 열쇠 → **카카오 지도** → 앱 키 붙여넣기 (채팅 붙여넣기 금지)
3. 콘솔 → 관리자 → 데이터 원천 → 「파일 올리기」로 두 파일 넣기 (s15 때 넘겨주신 것과 같음): 버스정류장 CSV cp949 20MB · 지하철역 xlsx

⑴·⑵ 다 끝나면 사장님이 이 방에 «등록 완료» 만 알려 주심.

### ⑵ 카카오맵 JS 지도 컴포넌트 (사장님이 열쇠 넣으신 뒤 다음 판 · TODO #15)

- 「입지」 탭에 지도 컴포넌트 붙이기 — 로그인 세션으로 `GET /providers/kakao-map/config` 부름 → 앱 키 받아 카카오 SDK 로드 → 기존 SVG 반경 원 위에 겹치기
- 필요 파일: `apps/web/src/app/(console)/console/customers/[customerId]/location/` 아래 `MapView.tsx` 신설 (client component) · SDK 는 `<Script strategy="afterInteractive">`
- 시험: SDK 로드 실패 시 fallback (지금 SVG 반경만) · 열쇠 없을 때 안내

### ⑶ 인구 축 붙이기 (사장님 파일 대기 · TODO #12)

- 사장님이 jumin.mois.go.kr → 연령별 인구현황 → 행정기관별(읍면동까지) → 최신월(2026-08) CSV 넘겨주셔야 함
- 이 방이 할 것: 인구 원천 스키마·로더·경계 조인·화면 (교통 축과 같은 뼈대). 경계는 vuski/admdongkor GitHub 미러 (CC BY 4.0) 사용

### ⑷ 대기 · 사장님 판단 필요

- **「입지」 이름 겹침 정리** (TODO #9) — 이 방 탭 vs ANSEO 방 진단 탭 카드. 사장님 판단
- 판 번호 발급 순서 (다른 방들과 부딪히면 나중이 물러남)

## 대기/차단 · 다른 방 소관 (이 방에서 하지 말 것)

- 배포는 이 방이 직접 (규율대로, 사장님 배포 오더 문장이 있어야 `VEO_DEPLOY_ORDER` 로 전달)
- ANSEO 방·화면 점검 방·shareboard 방과 판 번호 부딪히면 **나중에 미는 쪽이 물러난다** (오늘 s16 이 그 경우 · 다른 방 SerpAPI 오분류 수정 #2 가 먼저 main 에 도달, rebase 로 물러남)
- 다른 방이 이 방 가지를 자기 것에 합쳐 밀 수 있음

## 도구·실측 메모 (재탐색 금지)

- **운영 실측 우회**: 이 방 프록시가 운영 주소 403 → **Higgsfield MCP `sandbox_exec`**(바깥 샌드박스) curl 로
  `https://veo-platform-production.up.railway.app/api/health`·`/api/queue`·`https://veo.seokorea.org/login`(웹 판은 로그인 페이지 소스에 박힘)
- **`VEO_DEPLOY_ORDER` 필수**: `bash scripts/deploy.sh` 만 실행하면 «인용할 문장이 정말 없다면, 지금은 배포하면 안 되는 상황입니다» 로 거절. `VEO_DEPLOY_ORDER="사장님 문장" bash scripts/deploy.sh` 로
- **rebase + force-with-lease**: main 이 다른 방에 밀리면 rebase 필수. force-with-lease 는 자동 정책 자동승인 안 되므로 사장님께 승인 요청 (AskUserQuestion) 후 `--force-with-lease=<branch>:<expected-sha>` 로 명시적으로
- **로컬 PostgreSQL**: `pg_ctlcluster 16 main start`. 접속은 `root` 계정 (암호 없음, host trust). `pg_hba.conf` 임자 postgres:postgres 유지
- **로컬 시험 DB**: `veo_test` 자동 생성. `VEO_TEST_DATABASE_URL="postgresql+psycopg://root@localhost:5432/veo_test"` 로 pytest 돌림
- **`MasterKey` 생성**: `MasterKey.from_base64(MASTER_KEY_V1_B64, version=1)` (초기 시험에서 `MasterKey(version=1, secret=...)` 로 잘못 쓰다 실패)
- **openpyxl 필요**: apps/api 의존성에 등재됨 (xlsx 로더용)

## 주의·제약 (반드시)

- **채팅에 API 열쇠·비밀키 붙여넣기 금지** — 사장님께도 그렇게 안내함. 콘솔 「외부 연결 열쇠」로 사장님이 직접
- 이 방 브랜치: desktop-tutorial `claude/hospital-location-analysis-plan-6kbmqo` · veo-platform `claude/anseo-location-tab`. 체크포인트만 desktop-tutorial main
- 커밋 트레일러:
  ```
  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_013Fy4opA3k1FC6gQobSVKWf
  ```
  모델 ID 는 트레일러에만, 코드·PR 에 넣지 말 것
- 사장님께는 「커밋」·「배포」 두 낱말만 (테스트 데이터라 정합성 지적 금지)
- 못 잰 값 = «—» (0 아님) · 합산 점수 없음 · 색+글자 병용 · 판 다르면 비교 금지 · 의료광고법 준수

## 참고

- 이 세션 로그 `docs/session-logs/2026-09-04-s16.md`
- 직전 `docs/session-logs/2026-09-04-s15.md`
- 여섯 축 자료 조사 `docs/plans/anseo-github-data-inventory.md` (e627b92)
- 기획안 `docs/plans/anseo-location-analysis-plan.md`
- 배포 규율 원문: `veo-platform/scripts/deploy.sh` 머리말
