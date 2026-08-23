# RESUME — 다음 세션 이어가기 (2026-08-23 16:2x KST · s05 마감)

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
1  다크모드 OS 연동 · 상단 누적을 답변 개수로     a905da5
2  새 질문 추가 단추 (+ hydration 경고 수리)      deae51d
3  업체 등록란에 지도 4종                          5d307f1
4  질문 만들기에 등록 자료 활용 (씨앗 프리필)      45a6cef
5  축의 탭 첫 그림 — 「깎인 배점」                 4ff627c
6  조직 단위 채널 집계 — 「AI 가 어디를 보나」      aa8d53c
7  경쟁 브랜드 등록 초안 프리필                     9014692
```

마지막 검증: API 6,365건 · 웹 1,736건 · UI 299건 전부 통과, build·smoke 통과.

## 바로 이어갈 작업 — 머리 그림이 없는 화면 넷

[실측 2026-08-23] 요구 3(*"각 화면 메인화면은 각 화면의 종합 데이터 인포그래픽으로
시작"*)을 화면 전수로 점검했다. **사람이 실제로 여는 화면은 전부 있다** — 메뉴 셋과
거래처 상세 여섯 탭. 없는 것은 **흡수된 화면 넷**이다:

```
/console/competitors   브랜드 식별      ← 값이 가장 크다(7번과 직결)
/console/issues        이슈 목록
/console/reports       리포트 목록
/console/review        AI 답변 검수
```

`/console/medical`(원고 검수)은 **입력 도구라 종합 데이터가 없다** — 인포그래픽이
맞지 않는 화면이라고 사장님께 말씀드렸다. 지어내서 채우지 않는다.

각 화면이 답해야 할 물음(초안):

```
브랜드 식별   등록된 경쟁사가 몇이고, 인용에 나오는데 등록 안 된 곳이 몇인가
             [실측 2026-08-21] 등록 경쟁사 0곳 · 인용 656건 중 594건이 남의 것
이슈 목록     등급 구성과 밀린 정도 (거래처 상세의 IssueGradeCard 와 같은 부품 재사용)
리포트 목록   월별 발행 현황과 밀린 곳
AI 답변 검수  대기열 규모와 적체 기간
```

**서브 페이지 중복은 없다**(요구 3 후단) — `customers/new`·`[customerId]/edit`·
`issues/[id]`·`reports/[reportId]`·`customers/projects` 전부 머리 그림이 없다.

## 사장님 확인이 필요한 것 하나

요구 7 은 *"이 프로그램은 대시보드, SEO, GEO, AEO"* 인데, 지금 SEO·GEO·AEO 는
**최상위 메뉴가 아니라 거래처 상세의 탭**이다(사장님 2026-08-21 주문: *"새 페이지
상위 네비게이션 진단 SEO GEO AEO 이슈 리포트로 변경"*). 두 주문이 어긋나는지,
탭 구조가 요구 7 의 뜻인지 확인이 필요하다.

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
