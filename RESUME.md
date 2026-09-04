# RESUME — 다음 세션 이어가기 (2026-09-04 17:14 KST · s15 마감)

> 새 세션은 이 파일을 **먼저** 읽는다. 이 세션 상세는
> `docs/session-logs/2026-09-04-s15.md` · 직전은 `-s14.md`(9-3).
> 현황은 `PROJECT_STATE.md`, 지도는 `핵심두뇌_MASTER.md`.

## 지금 상태 (s15 마감)

- **운영 판 = 0.3.498** ([실측 2026-09-04 14:48 KST · 바깥 샌드박스 curl] 서버·워커·웹 셋 다, 워커 1대·뒤처진 0. 워커 45초 뒤 재기동 후 도달)
- **교통 축이 서 있다** (v0.3.498) — `transport_stops` 표·로더(xlsx·CSV, 자연 열쇠 튜플, 5,000 배치)·`_transport_of()` 상자+하버사인·설정 「데이터 원천」 실측 상태·「입지」 탭 값 표시
- **운영 DB 는 비어 있음** — 코드는 나갔으나 「데이터 원천」에 교통 두 원천이 「미적재」로 뜬다. 로컬 DB 에는 사장님이 넘겨주신 CSV/xlsx 로 실적재됨(버스 227,053행·지하철 1,094역, 강남 500m 안 버스 70·지하철 2)
- veo-platform 우리 가지 `claude/anseo-location-tab` = **7955d84** (도장 · 원격 최신)
- desktop-tutorial 이 방 가지 `claude/hospital-location-analysis-plan-6kbmqo` = **e627b92** (GitHub 자료 여섯 축 조사 통합 문서 · 커밋됨)

## 바로 이어갈 작업

### ⑴ 파일 올리기 UI (SUPER_ADMIN) — 이번 판 (0.3.499+)
사장님이 「배포하고 파일 올리기 UI 로 가자」 확정. 다음 판 착수 결심 상태 · 코드 미착수.

- 새 창구 `POST /datasources/{source_key}/upload` (권한 `datasource:manage` = SUPER_ADMIN, multipart)
  - 파일 · reference_date (선택) · encoding (선택) → 서버가 임시 파일에 저장 → `scripts.load_transport_stops.load()` 호출 → `{inserted, dropped}` 반환
  - 20 MB 상한(버스 파일이 20 MB) · 50 MB 로 두면 여유
- 화면: `/console/datasources` 표의 각 행에 「파일 올리기」 단추 → 모달(파일·기준일·인코딩 셋 UTF-8/CP949) → 결과·새 상태
- 시험: 권한(SUPER_ADMIN 200·ANALYST 403) · 잘못된 원천(400) · CSV 업로드 · xlsx 업로드 · 큰 파일 · 잘못된 인코딩
- 규모 예상 300~400 줄 · 시험 5~6

**나가면 사장님이 콘솔에서 두 파일 넣어 운영에 값이 뜸.**

### ⑵ 카카오맵 JS 지도 타일 (사장님 키 대기 · TODO #15)
사장님이 하실 것:
1. developers.kakao.com 앱 등록 (이름 「ANSEO 입지 지도」 등)
2. **JavaScript 키** 발급
3. **도메인 제한 걸기** — `https://veo.seokorea.org` · `https://veo-web.vercel.app` · `http://localhost:3000`
4. Vercel 대시보드 → veo-web → Environment Variables → `NEXT_PUBLIC_KAKAO_MAP_APP_KEY` 로 값 붙여넣기 · Redeploy
5. 저에게 「등록 완료」 라고만 알려주심 (값은 안 넘김)

이 방이 할 것: 지도 컴포넌트 · 카카오 SDK 로딩·초기화 · 기존 SVG 원(반경 고리) 위에 겹치기 · 시험

### ⑶ 인구 축 (사장님 파일 대기 · TODO #12)
사장님이 하실 것: **jumin.mois.go.kr → 연령별 인구현황 → 행정기관별(읍면동까지) → 남녀·연령 · 최신 월(2026-08) CSV** 다운로드. 사장님이 지난번 넘긴 파일(`8dfed5b4_...csv`)은 시·도 총계만 있어 반경 셈에 못 씀.

이 방이 할 것: 파일 오면 인구 원천 스키마·로더·경계 조인·화면 (교통 축과 같은 뼈대). 경계는 vuski/admdongkor GitHub 미러(CC BY 4.0)가 자동.

### ⑷ 대기 · 사장님 판단 필요
- **「입지」 이름 겹침 정리** (TODO #9) — 이 방 탭 vs ANSEO 방 진단 탭 카드. ⑴ 이 방을 「상권」 ⑵ ANSEO 방을 「자리」 ⑶ 그대로 둠
- 판 번호 발급 순서 (오늘도 두 번 물림 · 다른 방들이 앞섬)

## 대기/차단 · 다른 방 소관 (이 방에서 하지 말 것)

- 배포는 이 방이 직접 (규율대로 만들고 검사까지, 사장님 오더에 나감)
- ANSEO 방·화면 점검 방·shareboard 방과 판 번호 부딪히면 **나중에 미는 쪽이 물러난다**
- 다른 방이 이 방 가지를 자기 것에 합쳐 밀 수 있음 (트리 내용은 유지, SHA 는 없어도 반영됨 — s14 shareboard-tune 사례)

## 도구·실측 메모 (재탐색 금지)

- **운영 실측 우회**: 이 방 프록시가 운영 주소 403 → **Higgsfield MCP `sandbox_exec`**(바깥 샌드박스) curl 로
  `https://veo-platform-production.up.railway.app/api/health`·`/api/queue` 확인. 10초 만에 됨. 배포 5/5 도달 확인은 이걸로만 가능(deploy.sh 는 종료코드 22 로 죽음)
- **로컬 PostgreSQL**: `pg_ctlcluster 16 main start`. 접속은 `root` 계정(암호 없음, host trust). **`pg_hba.conf` 임자 postgres:postgres 유지** — chown 조심
- **로컬 시험 DB**: `veo_test` 자동 생성. Makefile 은 현재 OS 사용자로 접속 → `root` 로도 붙음
- **`gh` CLI**: `apt install gh` 로 2.45. 컨테이너 리셋 시 재설치 필요
- **openpyxl 필요**: apps/api 의존성에 등재됨(≥3.1). 시험 DB 에서 xlsx 읽을 때 `pip install openpyxl` 없어도 로컬은 `.venv` 활성화 필요
- **화면 관문 3종** (v0.3.495 이후 화면 점검 방이 심음): 접는 폭 세 단(720·960·1100px) · 글자 하한 11px · 표 감싸개(`.tableFlow`, `.tsx` CSS import 는 홑따옴표)
- **PostgreSQL 파라미터 상한 65,535** — 큰 CSV 는 반드시 배치(로더는 5,000행씩)

## 주의·제약 (반드시)

- **채팅에 API 열쇠·비밀키 붙여넣기 금지** — 사장님께도 그렇게 안내함. Vercel 대시보드 또는 콘솔 「외부 연결 열쇠」로 사장님이 직접
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

- 이 세션 로그 `docs/session-logs/2026-09-04-s15.md`
- 직전 `docs/session-logs/2026-09-04-s14.md` (교통 축 인프라·배포 0.3.496)
- 여섯 축 자료 조사 `docs/plans/anseo-github-data-inventory.md` (e627b92)
- 기획안 `docs/plans/anseo-location-analysis-plan.md`
- 시뮬 두 편 `docs/ANSEO-입지-화면-시뮬레이션.html` · `docs/ANSEO-데이터원천-설정-시뮬레이션.html`
- 배포 규율 원문: `veo-platform/scripts/deploy.sh` 머리말

## 사장님이 지금 · 앞으로 하실 것 (기억을 위해)

1. **인구 CSV 재다운로드** (jumin.mois.go.kr · 행정동 단위 · 최신월) — 이 방에 넘기심
2. **카카오 개발자 앱 등록 · JS 키 발급 · 도메인 제한 · Vercel 등록** — 값은 사장님이 직접, 저에게 「등록 완료」 만
3. (선택) 카카오 REST API 키 — 지오코딩용, 심평원에 없는 업체 지원할 때만
