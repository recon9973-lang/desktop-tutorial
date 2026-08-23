# RESUME — 다음 세션 이어가기 (2026-08-23 15:46 KST · s05 마감)

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

사장님이 GPTO(경쟁 제품) 스크린샷 13장을 주시고 ANSEO 개편을 오더하셨다. 요구 9건 중
**1~6번 구현 완료**, 7번만 남았다.

```
1  다크모드 OS 연동 · 상단 누적을 답변 개수로     a905da5
2  새 질문 추가 단추 (+ hydration 경고 수리)      deae51d
3  업체 등록란에 지도 4종                          5d307f1
4  질문 만들기에 등록 자료 활용 (씨앗 프리필)      45a6cef
5  축의 탭 첫 그림 — 「깎인 배점」                 4ff627c
6  조직 단위 채널 집계 — 「AI 가 어디를 보나」      aa8d53c
```

마지막 검증: API 6,362건 · 웹 1,729건 · UI 299건 전부 통과, build·smoke 통과.

## 바로 이어갈 작업 — 7번 경쟁 브랜드 로스터

**사장님이 이어서 진행하라고 지시하셨다.** 방향은 직전 문답에서 합의됐다:

> **자동화할 것은 「등록」이 아니라 「등록까지 가는 길」이다.**

이름 글자만으로 자동 등록하면 동명 업체가 섞인다(참사랑한의원은 심평원에 16곳).
그 순간 모든 점유율이 거짓이 된다 — `apps/api/src/veo/observations/rivals.py` 머리말이
이미 그 이유를 적어 뒀다: *"점유율은 사람이 신원을 채워 등록(승격)한 뒤, 기존 대칭
파이프가 그린다."*

### 지금 있는 것

```
발견   rivals.py            우리가 빠진 답변에 누가 나오나 (자동)
발견   citations_by_site.py 등록 안 된 업체 사이트 (자동, 조직 전체)
입구   RivalFindings.tsx    「경쟁사로 등록 →」 링크 — **이름 한 글자만** 들고 간다
       → /console/competitors?project=…&name=…
```

### 빠진 것 (= 7번의 일감)

1. **초안이 안 채워진다.** `Competitor` 는 `origin`(도메인)·`display_name`·
   `brand_aliases` 가 필요한데 담당자가 처음부터 다시 찾는다. 재료는 이미 있다 —
   `CitedSite.domain`·`sample_url`, 심평원 상호·주소·진료과.
2. **명단이 안 모인다.** 발견이 회차마다·거래처마다 흩어져 있어, 화면을 닫으면
   사라진다. 조직 단위 「로스터」로 모아야 경쟁 지형이 보인다.
   ([실측 2026-08-21 · 코드 주석] 인용 656건 중 등록 경쟁사 **0곳**, 594건이 남의 것)

### 설계 원칙 (4번과 같은 패턴)

```
자동   발견 + 초안 채워 넣기
사람   신원 확인 한 번 → 승격
못 가리면 아무것도 안 고른다  ← 4번 institution_for 와 같은 규칙
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
