# 배포 이관서 — veo-platform 「어느 AI 가 어느 채널을 보나」 넷 (+덤 하나)

받는 곳 **ANSEO 방** · 보내는 곳 **자동 진단 방**(desktop-tutorial 세션 · AEO 진단 조사)
작성 2026-09-09 · 적용 기준 `origin/main` = `37aa650f`

> **사장님 오더 원문**: *«ANSEO방에 배포 이관»*
> 그 앞 오더: *«①④ 고쳐줘»* · *«⑥번 두 개도 고쳐줘»* · *«이어서 진행»*
> `VEO_DEPLOY_ORDER` 에 이 문장을 그대로 인용하십시오.

## 왜 이관인가 — 이 방은 못 민다

```
veo-platform 푸시 권한 요청     관문에서 거절됨(자동 승인 분류기)
운영 주소(railway) 두드리기     프록시가 CONNECT 에서 403 — [5/5] 확인 불가
```

**코드는 다 됐고 검사도 다 돌았다.** 남은 것은 미는 일뿐이다.

## 무엇을 넘기나 — 커밋 셋 · 관문 11건

| 커밋 | 무엇 | 왜 |
| --- | --- | --- |
| `ed26b42c` | ① 미분류를 맨 뒤로(차례를 한 곳에서) · ② 미분류 몫을 경쟁사 상자에서 꺼내 늘 적는다 · ③ 분모를 교차표 제 셈으로 | 맨 위가 「모르겠다」였고, 경쟁사를 등록하면 그 숫자가 사라졌다 |
| `4eb7499d` | ④ 기간 탭이 이 카드도 데려간다 · ⑤ `claim_version.py` 가 대장 머리말을 넓게 고치던 것 | 「이번 주」인데 판 하나를 그렸다 · 남의 판 번호까지 갈렸다 |
| `aafea593` | ⑥ 몇 곳에 물었나를 접기 전에(화면·서버) · ⑦ 임대형 홈페이지 자사 선언에 경로 요구 | 일곱 중 하나에 물은 판이 다 물은 판과 같아 보였다 · 호스트만 선언하면 옆 업체 인용이 우리 것이 됐다 |

**모두 되돌려 빨간불인 것을 확인한 관문이 붙어 있다**(11건). 마이그레이션 없음 ·
저장된 자료 무변경 · 잰 값 무변경.

## 가져가는 법

패치는 desktop-tutorial 가지에 있다(main 이 아니다).

```bash
git -C <desktop-tutorial> fetch origin claude/aeo-grand-beautiful-clinic-diagnosis-1tnsbt
git -C <desktop-tutorial> checkout FETCH_HEAD -- docs/patches

git -C <veo-platform> fetch origin main
git -C <veo-platform> checkout -b claude/geo-mosaic-unclassified-last origin/main
git -C <veo-platform> am <desktop-tutorial>/docs/patches/000*.patch
```

**`37aa650f` 위에서 만든 것이다.** main 이 그 뒤로 또 움직였으면 `am` 이 대장·변경이력에서
멈춘다 — 그때는 **지금 참인 쪽(HEAD)을 살리고 내 줄만 끼우면 된다**(아래 「대장 상태」).

## 나가기 전에 — 이 방이 이미 돌린 검사

```
vitest        2,540건 통과      (apps/web · 리베이스 후 재실행)
API           1,572건 통과      브랜드·관측·계약·판물림 (PostgreSQL 필요)
mypy          456파일 통과
ruff · tsc · next build        통과
```

API 시험은 나무가 필요하다:

```bash
service postgresql start
VEO_TEST_DATABASE_URL="postgresql+psycopg://root:veo@localhost:5432/veo_test" \
  .venv/bin/python -m pytest apps/api/tests/brands apps/api/tests/observations
```

## 순서에 걸린 것 하나 — **`0002` 가 판 물림을 고친다**

`4eb7499d` 안에 `scripts/claim_version.py` 고침이 들어 있다. 이것이 **들어가기 전에**
다른 판을 밀면, 배포가 대장 머리말에서 그 판 번호를 **전부** 바꾼다.

```
[실측 2026-09-09] 머리말 한 줄(6,236자)에 0.3.555 가 일곱 번
    ① 범위 선언 · ② 그 방 항목      옮겨야 한다
    ③~⑦ 다른 방 항목 · 지난 기록    그대로 둬야 한다  ← 전부 갈렸다
```

셋을 한 판으로 미시면 이 문제는 그 판에서 사라진다. **따로 미실 거면 `0002` 를 먼저.**

## 대장 상태 — 이미 맞춰 두었다

- 변경이력 **맨 위 항목**이 이 일이고 판은 `0.3.556` 이다(나갈 때 `claim_version.py` 가 옮긴다).
- `WORKLIST.md` §2 머리말과 **배포 대기 표 맨 윗줄**에 이 일이 적혀 있다.
  머리말의 미배포 범위와 표가 일치한다(`worklist.test.ts` 통과).
- `WORKLIST-HISTORY.md` 에 절이 있다 — 제목이 `(v0.3.556 · 자동 진단 방)`.
- **다른 방 줄은 손대지 않았다.** 리베이스에서 「0.3.552~0.3.555 는 나갔다」를 확인하고
  지금 참인 머리말 위에 내 줄만 끼웠다.

## 나간 뒤에 — 도장

1. `https://veo-platform-production.up.railway.app/api/health` 와 `/api/queue` 로
   **서버·워커·웹 셋을 따로** 재고, 뒤처진 워커 수를 기록에 남긴다.
2. 대기 표에서 **이 줄만** 지우고 머리말의 미배포 범위를 다시 적는다.
   **다른 방 줄은 건드리지 않는다.**
3. 사장님께는 「커밋」·「배포」 두 낱말로만 보고한다.

## 이 방이 못 잰 것

| 항목 | 상태 |
| --- | --- |
| 실서비스에서 실제로 도는지 | «—» (이 방은 운영 주소로 못 나간다) |
| 사장님 화면에서 미분류가 맨 뒤로 갔는지 | «—» (배포 뒤 확인) |

## 아직 남은 일 하나 — 규칙판 4는 **근거 대기**

강남언니·바비톡·여신티켓이 채널 규칙표에 없다. 넣으면 미분류가 크게 준다.
그런데 `citation_channels.py` 머리말이 *«짐작으로 분류하지 않는다 — 규칙에 넣은
도메인은 전부 실측 근거를 달았다»* 라고 못 박아 두었다. **미분류 178건을 펼쳐 보기
전에는 넣을 수 없다.** 콘솔 대시보드 「AI 가 어디를 보나」 → 「미분류 안에 무엇이
있나」를 펼쳐 상위 도메인을 확보하는 것이 먼저다.

관련 조사: `docs/2026-09-09-그랜드아름다운의원-AEO-진단-조사.md`
