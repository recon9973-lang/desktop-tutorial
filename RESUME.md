# RESUME — 다음 세션 이어가기 (2026-08-23 19:2x KST · s06 마감)

> 새 세션은 이 파일을 **가장 먼저** 읽는다. 상세는 `docs/session-logs/2026-08-23-s05.md`,
> 현황은 `PROJECT_STATE.md`, 지도는 `핵심두뇌_MASTER.md`.

## ⚠ 작업 저장소가 다르다

이번 흐름의 구현은 전부 **`veo-platform`** 저장소에 있다. 이 저장소
(`desktop-tutorial`)에는 리포트·제안서·세션 로그만 있다.

```
veo-platform      claude/anseo-ui-v3   ← 구현 (PR #1)
desktop-tutorial  claude/anseo-screenshot-analysis-9qkxno   ← 문서 (PR #229)
```

`veo-platform` 이 세션에 안 붙어 있으면 `add_repo` 로 붙이고 클론한다.

## 지금까지 (핵심만)

사장님이 GPTO(경쟁 제품) 스크린샷 13장을 주시고 ANSEO 개편을 오더하셨다.
**요구 9건 전부 구현 완료.** PR #1 은 아직 main 에 안 들어갔다(배포 대기).

```
1~7  요구 9건 구현                    a905da5 … 9014692
+    브랜드 식별 첫 그림               f475547
+    이슈·리포트·검수 첫 그림          a3dc831
+    그림을 자료 성질에 맞게 고침       55818ce
+    사용량·프로젝트 첫 그림 · 등급 색   2bb076f
+    추이 그래프 칸 풍선(툴팁)          (s06 마지막 커밋)
```

**요구 3(각 화면 첫 그림) 마감.** 화면 전수 대조로 `usage`·`customers/projects` 까지
채웠다. `medical`(원고 검수)만 대상이 아니다 — 입력 도구라 종합 데이터가 없다.

마지막 검증: `scripts/preflight.sh` 전체 초록(ci-local 6,541 · 웹 1,777 · build · smoke).

## 사장님 확정 (2026-08-23) — 되묻지 말 것

```
메뉴 구조   지금 **탭 구조 유지**. SEO·GEO·AEO 는 거래처 상세의 탭이고
            최상위 메뉴로 안 올린다(요구 7 은 이 구조로 읽는다)
툴팁        붙인다 · **추이 그래프부터** (s06 에서 MultiTrendChart 에 넣었다)
자사 색     지금 **강조색 유지**. 참고 화면(GPTO)은 흰색이지만 밝은 판에서 묻힌다
```

## 바로 이어갈 작업

**배포가 첫 순위다.** PR #1 에 12 커밋이 쌓였고 preflight 는 초록인데 아직 main 에
없다 — 라이브에는 아무것도 안 보인다. `make deploy` 가 유일한 길이다(후보 가지 →
CI 초록 → 같은 SHA 를 main).

그다음 남은 것 둘:

```
① 리포트 본문의 등급 3색      `reports/[reportId]/[version]/ReportBody.tsx`
   콘솔 쪽은 밝기 단으로 고쳤는데 **발행본은 안 건드렸다** — 못 고치는 문서라
   CSS 를 바꾸면 지난 판의 그림까지 바뀐다. 「이 판부터 새 색」이라는 판 개념이
   먼저 있어야 한다. 같은 색각 결함이 남아 있다(deutan ΔE 1.0)
② 툴팁을 다른 그림으로 넓힐지  지금은 추이 그래프(MultiTrendChart)만
```

## 대기/차단 (사용자 액션)

- **veo-platform PR #1 배포 여부** — 사장님 판단. 아직 main 병합 안 됨.
- 이월: #36 GSC env 입력 · #37 erp-v1 PR 허락 · #40 misojin v3 Drive 업로드.

## 주의·제약 (반드시)

- **브랜치**: veo-platform 은 `claude/anseo-ui-v3`, desktop-tutorial 은
  `claude/anseo-screenshot-analysis-9qkxno`. 다른 가지에 올리지 않는다.
- **비밀키 값·모델 ID**를 커밋/PR/코드/문서/채팅에 넣지 않는다.
  커밋 트레일러 준수(Co-Authored-By / Claude-Session).
- **실측 원칙**: 실측 > 추론 > 통계 날조 금지. 못 잰 값은 `0` 이 아니라 `—`(ADR 0002).
- **관문을 무력화하지 않는다.** 박스 세는 시험·계약 시험·대비 시험이 실수를 잡아 준다.
  기준선을 고칠 땐 **왜 바뀌었는지 그 자리에 적는다**(그 관문의 규칙).
- **계약을 다시 뽑는다.** 서버 창구를 더하면
  `apps/api/scripts/export_openapi.py` → `pnpm --filter @veo/api-client generate`.
  s05 에서 이걸 빠뜨려 계약 시험이 한 판 동안 헛돌았다.
- **그려 보고 확인한다.** 시험은 글자를 세지 배치를 안 잰다 — s05 에서 브라우저로만
  보인 배치 결함이 넷이었다.

## 개발 환경 (샌드박스 재구성 방법)

```
PostgreSQL   /usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/veo-test \
             -o '-p 5432 -k /var/run/postgresql' start      (postgres 사용자로)
             DB 이름 veo_test · 기본 소켓·포트여야 백업·복원 시험까지 돈다
파이썬       /home/user/veo-platform/.venv
시험         VEO_TEST_DATABASE_URL=postgresql+psycopg://postgres@/veo_test?host=/var/run/postgresql&port=5432
브라우저      PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers · playwright 는 /opt/node22 전역
```

## 참고

- 이번 세션 상세 `docs/session-logs/2026-08-23-s05.md`
- GPTO 역설계 `docs/GPTO-벤치마크-ANSEO-적용리포트.md` · 제안서 `docs/ANSEO-개편-비교제안서.md`
- veo-platform 대장 `docs/WORKLIST.md` §1-C3~§1-C7 이 이번 판들의 기록
