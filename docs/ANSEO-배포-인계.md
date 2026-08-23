# ANSEO 개편 배포 인계 — ANSEO 방에서 함께 밀기

> 2026-08-23 작성. 이 문서 하나로 **다시 탐색하지 않고** 배포까지 간다.
> 구현은 전부 `veo-platform` 에 있다. 이 저장소(`desktop-tutorial`)에는 문서만 있다.

---

## 1. 무엇이 나가나

**ANSEO 콘솔 개편 한 판.** 사장님이 GPTO(경쟁 제품) 화면 13장을 주시고 오더하신
요구 9건 + 화면 전수 마감 + 그림 문법 정리 + 툴팁.

```
저장소   veo-platform
가지     claude/anseo-ui-v3          (PR #1)
판       0.3.294                     ← main 은 0.3.293
커밋     13개  a905da5 … b806623     (main 과의 차이)
분량     90파일 · +7,979 / −162
```

| 커밋 | 무엇 |
| --- | --- |
| `a905da5` | 화면 판을 컴퓨터 설정과 잇고, 누적을 답변 개수로 |
| `deae51d` | 질문을 직접 적어 넣는 줄 · hydration 경고 수리 |
| `5d307f1` | 지도 등록 넷 — 올라감·없음·모름을 뭉개지 않는다 |
| `45a6cef` | 질문의 첫 낱말을 등록된 자료(심평원 진료과목·업종)에서 |
| `4ff627c` | 축의 탭을 「깎인 배점」으로 — 레이더를 뺐다 |
| `aa8d53c` | AI 가 어디를 보나 — 인용 채널을 조직 단위로 |
| `9014692` | 인용에 나온 회사 → 경쟁 브랜드 등록까지 한 번에 |
| `f475547` | 브랜드 식별 화면 첫 그림 |
| `a3dc831` | 이슈·리포트·검수 첫 그림 |
| `55818ce` | 그림을 자료의 성질에 맞게 고침 (셋을 되돌려 고쳤다) |
| `2bb076f` | 사용량·프로젝트 첫 그림 · 등급 색 색각 수정 |
| `77ed01d` | 추이 그래프 칸에 손 올리면 그 시점의 전부 |
| `b806623` | **판 0.3.294** — changelog · `__version__` · openapi · 대장 |

**마지막 커밋이 왜 있나.** 12커밋이 전부 사용자 눈에 보이는 개편인데 판이 0.3.293
그대로였다. 그대로 나갔으면 ① 화면의 버전 표시가 옛 판을 말하고, ② 배포 스크립트의
마지막 확인 단계(`[5/5]`)가 **헛돈다** — 운영이 이미 0.3.293 을 서비스 중이라, 아무것도
안 나가도 「도달했다」고 찍힌다. 판을 올려야 그 관문이 실제로 잰다.

---

## 2. 배포 절차 — `make deploy` 가 유일한 길

```bash
cd veo-platform
git checkout claude/anseo-ui-v3
git pull origin claude/anseo-ui-v3      # b806623 인지 확인
make deploy
```

`make deploy` 는 `preflight` 를 **먼저** 돌리고, 통과 못 하면 시작하지 않는다.
그다음 순서가 이 스크립트의 전부다:

```
[0/4] 오늘 배포 상한(2회) 검사        ← gh 필요
[1/4] HEAD 커밋을 잡는다
[2/4] 그 커밋을 deploy-candidate 로 민다   ← main 은 아직 그대로
[3/4] CI 가 그 커밋을 채점할 때까지 기다린다 (최대 20분)   ← gh 필요
[4/5] 초록불일 때만 같은 커밋을 main 으로 민다
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

**이 방(desktop-tutorial 세션)에서는 배포를 끝까지 못 민다.** 실측:

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

**미는 방에서 반드시 다시 잰다.** `make deploy` 의 `[0/4]` 가 같은 것을 gh 로 제대로
세므로, gh 가 있는 방에서 돌리면 저절로 해결된다.

**gh 없이 손으로 밀지 않는다.** GitHub MCP 로 흉내 낼 수는 있지만(후보 가지 push →
`actions_list` 로 그 SHA 실행이 초록인지 확인 → main push), 그러면 `[5/5]` 가 빠져
「main 에 밀었다」와 「그 코드가 실제로 돈다」를 다시 못 가른다. 2026-08-20 에 정확히
그 자리에서 진단 서버 0.3.237 · 워커 0.3.236 이 났다. **gh 있는 방에서 `make deploy`.**

---

## 4. 마지막 검증 결과 (실측)

`b806623` 직전 커밋 `77ed01d` 에서 `scripts/preflight.sh` 전체 초록:

```
준비됨 — make deploy 로 나갈 수 있습니다.

① 나무    미커밋 0건 · 미배포 12커밋
② 계약    openapi 드리프트 0 · 계약 판 = 서버 판
③ 관문    make ci-local     6,541 passed
          pnpm -r test      1,777 passed
          test-db · typecheck · lint · next build · smoke  전부 통과
④ 리눅스  파일 이름 대소문자 이상 없음
⑤ GitHub  (이 방에서 못 잼 — §3)
```

`b806623` 은 판 번호·문서만 건드렸고, 그 판에서 관문 시험
(`apps/web/src/lib/worklist.test.ts` 6건 — 대장·changelog·배포대기 표 정합)을 다시
돌려 통과했다. **미는 방에서 preflight 를 한 번 더 돌린다** — `make deploy` 가 알아서
돌리므로 따로 칠 필요는 없다. 관문 규칙 그대로다: *앞에서 초록이었던 것은 그때의
나무다. 배포는 지금의 나무를 내보낸다.*

> ⚠ **preflight 를 동시에 두 개 돌리지 않는다.** 각자의 `test-db` 단계가 상대의
> 시험 DB 를 지운다 — 한 번 964건이 그렇게 빨간불이 됐다. 코드 결함이 아니었다.

---

## 5. 어긋나면

| 어디서 | 무엇이 보이나 | 무엇을 하나 |
| --- | --- | --- |
| `[0/4]` | 「오늘 배포 상한에 이미 닿았습니다」 | 하루 2회 상한(무료 Actions 분 보호). 사장님 판단이면 `VEO_DEPLOY_LIMIT_PER_DAY=99 make deploy` |
| preflight ② | 「계약 드리프트」 | `apps/api` 에서 `scripts/export_openapi.py` → `pnpm --filter @veo/api-client generate` |
| preflight ③ | 시험 빨간불 | **관문을 끄지 않는다.** 고친다 |
| preflight ⑤ | 「지출 한도로 막혔다」 | GitHub Settings → Billing → Budgets and alerts 에서 Actions 예산 |
| `[3/4]` | CI 빨간불 | **main 은 안 건드려졌다.** `gh run view <id> --log-failed` 로 원인을 보고 고쳐서 다시 |
| `[5/5]` | 「워커가 도달 못 함」 | **main 에는 이미 밀렸다.** Railway → veo-worker → Deployments 에서 최근 빌드. 네트워크로 실패했으면 다시 굽는다 |

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

## 7. 이번 배포에 **일부러** 안 넣은 것

```
① 발행 리포트 본문의 등급 3색
   reports/[reportId]/[version]/ReportBody.tsx
   콘솔 쪽은 밝기 단으로 고쳤지만 발행본은 그대로 두었다 — 못 고치는 문서라
   CSS 를 바꾸면 **지난 판의 그림까지 바뀐다.** 「이 판부터 새 색」이라는 판
   개념이 먼저 있어야 한다. 같은 색각 결함이 남아 있다(호박↔빨강 deutan ΔE 1.0)

② 툴팁을 다른 그림으로 넓히는 일
   지금은 추이 그래프(MultiTrendChart)만. 사장님 확정이 「추이 그래프부터」였다
```

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
