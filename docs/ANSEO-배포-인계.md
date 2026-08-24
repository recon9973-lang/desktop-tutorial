# ANSEO 개편 배포 인계 — ANSEO 방에서 함께 배포하기

> 2026-08-23 작성. 이 문서 하나로 **다시 탐색하지 않고** 배포까지 간다.
> 구현은 전부 `veo-platform` 에 있다. 이 저장소(`desktop-tutorial`)에는 문서만 있다.

---

## 1. 무엇이 나가나

> **앞의 열 판(0.3.303~0.3.312)은 이미 나갔다.** 2026-08-24, main `8f7ea8d` ·
> `deploy-candidate` 도 같은 SHA. 이 문서는 **그다음 한 판**을 위한 것이다.

```
저장소   veo-platform
가지     claude/anseo-ui-v3
판       0.3.313                    ← main 은 0.3.312 (8f7ea8d)
커밋     1개  016c2bb
```

사장님이 시키신 **화면 항목 전수 조사**에서 나온 둘이다. 제안서·시안·요구 9건을
원본에서 뽑아 코드와 대조했고, 대부분 적용돼 있었다.

```
요구 9건      8건 적용 · 요구 1 미적용   → 이 판에서 고침
축별 첫 그림   7/7 적용
시안 M1~M5    M2~M5 적용 · M1 한 조각 빠짐 → 이 판에서 고침
색·확정       전부 적용
```

### ① 요구 1 — 진단 결과에서 리포트로 가는 길이 없었다

제안서가 「남은 일」로 적어 둔 자리인데 실제로 안 만들어져 있었다.
[실측] 진단·AEO 화면에서 `/console/reports` 로 가는 링크 **0건**.

```
그전   진단 → 결과 → 메뉴로 나감 → 회차를 다시 찾아 고름
지금   결과 맨 아래 「이 결과로 리포트 만들기 →」 → 그 회차를 달고 감(?run=)
```

**회차를 다시 고르게 하면 다른 회차를 고를 수 있고, 그러면 화면에서 본 숫자와
문서의 숫자가 달라진다.** 목록에 없는 값이면 최신으로 떨어진다.

### ② 머리줄 스탬프가 거짓이었다

```js
const measuredAt = new Date().toLocaleTimeString('ko-KR', { ... });
<span className={styles.stamp}>{measuredAt} 기준</span>
```

「기준」이라 적혀 있었지만 **화면을 그린 시각**이다. 자료가 언제 것이든 지금 시계를
찍었다. 실측 원칙에 정면으로 어긋난 값이 상시 떠 있었다.

**관문 하나가 그 결함을 정답으로 굳히고 있었다** — 「시각이 없으면 지금 값으로
읽는다」. 뒤집어서 **잰 값이 없으면 그 줄을 안 그린다**를 재게 했다.

서버가 `first_at` 을 낸다. 화면은 「8/1부터 · 마지막 8/23 14:00」. 하나도 없으면
줄을 안 그린다 — 오늘 날짜로 채우면 안 잰 기간을 잰 것처럼 말한다(ADR 0002).

---

## 2. 배포 절차 — `make deploy` 가 유일한 길

```bash
cd veo-platform
git checkout claude/anseo-ui-v3
git pull origin claude/anseo-ui-v3      # 016c2bb 인지 확인
make deploy
```

`make deploy` 는 `preflight` 를 **먼저** 돌리고, 통과 못 하면 시작하지 않는다.
그다음 순서가 이 스크립트의 전부다:

```
[0/4] 오늘 배포 상한(2회) 검사        ← gh 필요
[1/4] HEAD 커밋을 잡는다
[2/4] 그 커밋을 deploy-candidate 가지에 올린다   ← main 은 아직 그대로
[3/4] CI 가 그 커밋을 채점할 때까지 기다린다 (최대 20분)   ← gh 필요
[4/5] 초록불일 때만 같은 커밋을 main 에 올린다 = 배포
[5/5] 운영 진단 서버·워커가 실제로 0.3.294 를 서비스하는지 확인 (최대 15분)
```

**순서를 바꾸지 않는다.** CI 는 `deploy-candidate` 에서만 돈다 — main 에서는 일부러
안 돈다. 그래서 **PR #1 자체에는 CI 기록이 없다.** 지금 있는 증거는 로컬 preflight 다.
가지 보호로 막으려 했으나 비공개 저장소 + 무료 요금제에서는 규칙이 적용되지 않아
(403), 관문을 이 스크립트에 두었다.

### 미리 갖춰야 할 것

```
gh          로그인된 GitHub CLI      [0/4]·[3/4] 가 이것으로 CI 를 읽는다
바깥 통신    운영 API 로 curl 가능     [5/5] 가 /api/health · /api/queue 를 부른다
저장소      veo-platform 이 붙어 있을 것 (없으면 add_repo → clone)
파이썬·DB   아래 §6 (preflight 가 시험을 다시 돌린다)
```

---

## 3. `gh` 가 없는 방이면 — 이 방이 그랬다

**이 방(desktop-tutorial 세션)에서는 배포를 끝까지 못 한다.** 실측:

```
gh                 없음 (command -v gh → 없음)
운영 API curl      403 (샌드박스 프록시가 막는다)
```

그래서 이 방의 preflight 는 두 줄을 **못 잰 채로 지나간다.** 그 두 줄을 초록으로
읽으면 안 된다:

```
⑤ GitHub 최근 실행의 잡이 떴나   → gh 가 없어 "못 읽었다" 경고
  오늘 CI 실행 수                → gh 출력이 비어 0 으로 세어진다.
                                   「상한 2회 중 2회 남음」은 **측정값이 아니다**
```

**배포하는 방에서 반드시 다시 잰다.** `make deploy` 의 `[0/4]` 가 같은 것을 gh 로 제대로
세므로, gh 가 있는 방에서 돌리면 저절로 해결된다.

**gh 없이 손으로 배포하지 않는다.** GitHub MCP 로 흉내 낼 수는 있지만(후보 가지에 올리고 →
`actions_list` 로 그 SHA 실행이 초록인지 확인 → main push), 그러면 `[5/5]` 가 빠져
「main 에 올라갔다」와 「그 코드가 실제로 돈다」를 다시 못 가른다. 2026-08-20 에 정확히
그 자리에서 진단 서버 0.3.237 · 워커 0.3.236 이 났다. **gh 있는 방에서 `make deploy`.**

---

## 4. 마지막 검증 결과 (실측)

**나갈 바로 그 커밋 `016c2bb` 에서** `scripts/preflight.sh` 전체 초록:

```
준비됨 — make deploy 로 나갈 수 있습니다.

① 나무    미커밋 0건 · 미배포 1 커밋 · main 0.3.312 → 0.3.313
② 계약    openapi.json 이 앱과 일치 · 계약 판 0.3.313 = 서버 판 0.3.313
③ 관문    make ci-local     6,645 passed
          make test-db      통과
          pnpm -r typecheck · pnpm -r lint
          pnpm -r test      1,870 passed
          pnpm build · pnpm smoke (화면이 실제로 뜨나)
④ 리눅스  파일 이름 대소문자 이상 없음
⑤ GitHub  ! 최근 실행을 못 읽었다 — 지출 한도 상태를 모른다
          ✓ 오늘(KST) CI 0건 · 상한 2회 중 2회 남음   ← §3. 측정값이 아니다
```

**⑤ 의 초록 한 줄은 믿지 않는다.** `gh` 가 없어서 나온 0 이다. 그 바로 위 줄이
「못 읽었다」라고 말하고 있는데 아래 줄만 초록인 것이 그 증거다.

**배포하는 방에서 preflight 를 한 번 더 돌린다** — `make deploy` 가 알아서 돌린다.

> ⚠ **판을 고르기 전에 `git fetch`.** 이번에도 main 이 0.3.302 → **0.3.312** 로
> 움직여 있었고 이 가지는 21 커밋 뒤였다. 다른 방이 같은 저장소에 배포한다.
> §2 머리말도 그때마다 낡아 있다 — **세 번 연속 그랬다.**

> ⚠ **preflight 를 동시에 두 개 돌리지 않는다.** 각자의 `test-db` 단계가 상대의
> 시험 DB 를 지운다 — 한 번 964건이 그렇게 빨간불이 됐다. 코드 결함이 아니었다.

> ⚠ **DB 가 꺼져 있으면 빨간불 셋이 한꺼번에 뜬다.** `make ci-local` · `make test-db` 가
> `connection refused … /var/run/postgresql/.s.PGSQL.5432` 로 죽는다. 코드 결함이
> **아니라** 방이 덜 갖춰진 것이다 — §6 으로 PostgreSQL 을 먼저 켠다. 세션이 바뀌면
> 꺼진다(이 방에서 두 번 겪었다).

## 5. 어긋나면

| 어디서 | 무엇이 보이나 | 무엇을 하나 |
| --- | --- | --- |
| `[0/4]` | 「오늘 배포 상한에 이미 닿았습니다」 | 하루 2회 상한(무료 Actions 분 보호). 사장님 판단이면 `VEO_DEPLOY_LIMIT_PER_DAY=99 make deploy` |
| preflight ② | 「계약 드리프트」 | `apps/api` 에서 `scripts/export_openapi.py` → `pnpm --filter @veo/api-client generate` |
| preflight ③ | `connection refused` (ci-local·test-db 동시에) | 코드가 아니라 DB 가 꺼진 것. §6 으로 켠다 |
| preflight ③ | `two-words-only.test.ts` 빨간불 | 사장님 규칙 — 「커밋」과 「배포」 두 단어만 쓴다. 「민다·푸시」 계열을 쓰면 걸린다 |
| preflight ③ | 시험 빨간불 | **관문을 끄지 않는다.** 고친다 |
| preflight ⑤ | 「지출 한도로 막혔다」 | GitHub Settings → Billing → Budgets and alerts 에서 Actions 예산 |
| `[3/4]` | CI 빨간불 | **main 은 안 건드려졌다.** `gh run view <id> --log-failed` 로 원인을 보고 고쳐서 다시 |
| `[5/5]` | 「워커가 도달 못 함」 | **main 에는 이미 배포됐다.** Railway → veo-worker → Deployments 에서 최근 빌드. 네트워크로 실패했으면 다시 굽는다 |

---

## 6. 샌드박스 재구성 (preflight 를 돌리려면)

```bash
# PostgreSQL — 기본 소켓·포트여야 백업·복원 시험까지 돈다
sudo -u postgres /usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/veo-test \
     -o '-p 5432 -k /var/run/postgresql' start
# DB 이름 veo_test

export VEO_TEST_DATABASE_URL='postgresql+psycopg://postgres@/veo_test?host=/var/run/postgresql&port=5432'
export PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
export PATH=/opt/node22/bin:$PATH        # pnpm · playwright 전역

# 파이썬 — .venv 는 /home/user/veo-platform/.venv
pip install -e apps/worker               # ← 이걸 빠뜨리면 ModuleNotFoundError: veo_worker
                                         #    코드 결함이 아니라 방이 덜 갖춰진 것이다
```

---

## 7. 남은 것 · 일부러 안 한 것

**앞 인계에서 「남았다」고 적었던 둘은 이번에 끝났다.**

```
발행본 등급 색   0.3.303 에서 판 개념과 함께 고쳤다 (화면 · 인쇄본 둘 다)
툴팁            0.3.303 에서 현황판 썸네일에 하나 더 붙였다
```

**툴팁을 더 넓히지 않은 것은 판단이다.** 전수로 다시 보니 값이 이미 글자로 나와
있었다 — 산점도는 점 옆에 이름과 두 값, 막대점은 오른쪽 칸이 값, 깎인 배점은 진짜
표, 기울기는 선 끝에 비율, 구성비는 범례가 이름과 건수. **이미 화면에 있는 값을
손을 올려야 다시 보여 주는 것은 정보가 아니라 장식이다.**

이월은 **전부 정리됐다**(2026-08-23). #36 GSC 는 사장님 판단으로 접었고(거래처마다
초대 절차가 필요해 복잡하다 — 코드는 그대로 둔다), #37 은 이미 라이브였으며,
#40 은 원본이 없어 지웠다. **남은 것은 배포뿐이다.**

## 8. 사장님 확정 (2026-08-23) — 되묻지 말 것

```
메뉴 구조   지금 탭 구조 유지. SEO·GEO·AEO 는 거래처 상세의 탭이고 최상위로 안 올린다
툴팁        붙인다 · 추이 그래프부터
자사 색     지금 강조색 유지. 참고 화면(GPTO)은 흰색이지만 밝은 판에서 묻힌다
```

## 9. 제약 (반드시)

```
가지     veo-platform → claude/anseo-ui-v3
         desktop-tutorial → claude/anseo-screenshot-analysis-9qkxno
         다른 가지에 올리지 않는다
커밋     Co-Authored-By / Claude-Session 트레일러 필수
금지     비밀키 값·모델 ID 를 커밋/PR/코드/문서/채팅에 넣지 않는다
자료     실측 > 추론 > 통계 날조 금지. 못 잰 값은 0 이 아니라 —(ADR 0002)
관문     무력화하지 않는다. 기준선을 고칠 땐 왜 바뀌었는지 그 자리에 적는다
계약     서버 창구를 더하면 export_openapi.py → @veo/api-client generate
PR       사장님이 시키지 않으면 만들지 않는다
```

## 10. 더 볼 곳

```
세션 기록   docs/session-logs/2026-08-23-s05.md · -s06.md
GPTO 역설계  docs/GPTO-벤치마크-ANSEO-적용리포트.md
제안서      docs/ANSEO-개편-비교제안서.md
veo 대장    (veo-platform) docs/WORKLIST.md §1-C3~§1-C13 · §2 배포 대기
판별 이력   (veo-platform) docs/WORKLIST-HISTORY.md 2026-08-23
```
