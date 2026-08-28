# ANSEO 배포 인계 — 열네 판 (0.3.356~0.3.369)

> 2026-08-28 갱신(s09). 이 문서 하나로 **다시 탐색하지 않고** 배포까지 간다.
> 구현은 전부 `veo-platform` 에 있다. 이 저장소(`desktop-tutorial`)에는 문서만 있다.
> 지난 배포(0.3.303·0.3.304, 2026-08-23)의 기록은 `docs/session-logs/2026-08-23-s08.md`.

---

## 0. 배포 전에 먼저 잴 것 — 운영이 지금 몇 판인가

[실측 2026-08-28 · git] `main` = `aaa76e4`(판 0.3.364) 이고 `deploy-candidate` 도 같다.
그런데 대장의 마지막 운영 실측(2026-08-27 01:54)은 **0.3.355** 다. 즉 **git 의 main 과
운영이 같다는 보장이 지금 없다** — 0.3.356~0.3.364 배포가 끝까지 갔는지 이 방(egress
차단)에서는 확인 못 했다. 그래서 첫 명령은 배포가 아니라 측정이다:

```bash
curl -s https://veo-platform-production.up.railway.app/api/health | head -c 300
# "version" 칸을 본다. 0.3.364 면 아홉 판은 이미 나간 것 — 남은 것은 우리 넷뿐.
# 0.3.355 면 열세 판이 전부 대기 중 — 지난 배포의 [5/5] 가 안 끝났는지 Railway 를 본다.
```

## 1. 무엇이 나가나

```
저장소   veo-platform
가지     claude/wonderful-einstein-1qiqm5     판 0.3.369 (코드 커밋 dc2696f · 그 뒤 문서 커밋이 얹힐 수 있다)
main     aaa76e4 (판 0.3.364) — 우리 가지의 조상이다(빨리감기 가능, 충돌 없음)
이 가지가 더하는 것   5커밋 · 판 0.3.365~0.3.369
```

| 커밋 | 판 | 무엇 |
| --- | --- | --- |
| `e3c08e8` | 0.3.365 | **로그인 없는 창구·안내판을 닫았다.** [실측] 운영 `GET /docs` 200 이었고 목록에 `POST /public/v1/seo-scans` 가 실려 있었다. 설정 둘 신설, 기본 꺼짐(`VEO_PUBLIC_SURFACE_ENABLED` · `VEO_API_DOCS_ENABLED`). 공유 리포트 읽기(`/results/{토큰}`)는 갈라서 살렸다 |
| `08545be` | 0.3.366 | **등급 A+~F 아홉 칸** (명세 SEO 1.11.0 · GEO 1.5.0). 점수 계산은 그대로, GEO 경계를 SEO 와 통일 |
| `dd55f6e` | 0.3.367 | **크롬 워커** — 페이지를 실제로 그려 본다. 기본 꺼짐(`VEO_RENDERER_ENABLED`). **워커 이미지가 크롬을 싣기 시작한다** ← 이번 배포의 위험 지점 |
| `9ff5ed5` | 0.3.368 | 우리 자 ↔ 구글 자 비교 도구(`scripts/compare_lab_measurements.py`) |
| `dc2696f` | 0.3.369 | 탭 전환 지연의 둘 더 — 안 보는 탭의 주간·월간 추이를 안 부른다 |

## 2. 배포 절차 — `make deploy` 가 유일한 길

```bash
cd veo-platform
git fetch origin
git checkout claude/wonderful-einstein-1qiqm5
git pull origin claude/wonderful-einstein-1qiqm5
grep __version__ apps/api/src/veo/__init__.py          # 0.3.369 인지 확인
make deploy
```

`make deploy` 는 `preflight` 를 먼저 돌리고, 통과 못 하면 시작하지 않는다:

```
[0/4] 오늘 배포 상한(2회) 검사                        ← gh 필요
[1/4] HEAD 커밋을 잡는다
[2/4] deploy-candidate 가지에 올린다                  ← main 은 아직 그대로
[3/4] CI 가 그 커밋을 채점할 때까지 기다린다 (최대 20분) ← gh 필요
[4/5] 초록불일 때만 같은 커밋을 main 에 올린다 = 배포
[5/5] 운영 진단 서버·워커가 실제로 0.3.369 를 서비스하는지 확인 (최대 15분)
```

순서를 바꾸지 않는다. CI 는 `deploy-candidate` 에서만 돈다(main 에서는 일부러 안 돈다).
가지 보호가 비공개+무료 요금제에서 403 이라 관문이 이 스크립트에 있다.

### 미리 갖춰야 할 것

```
gh          로그인된 GitHub CLI       [0/4]·[3/4] 가 이것으로 CI 를 읽는다
바깥 통신    운영 API 로 curl 가능     §0 과 [5/5] 가 쓴다
저장소      veo-platform (없으면 add_repo → clone)
파이썬·DB   아래 §6 (preflight 가 시험을 다시 돌린다)
```

## 3. ⚠ 이번 배포가 지난 배포와 다른 것 — 워커 이미지에 크롬

`infra/docker/worker.Dockerfile` 이 이번 판부터 `playwright install --with-deps chromium`
을 돌린다. 결과:

```
첫 빌드가 길다        브라우저 본체 + 시스템 의존성 내려받기
이미지가 커진다       수백 MB 증가
빌드는 안 해봤다      이 방(desktop-tutorial 세션)은 디스크 한도로 못 돌렸다 —
                      Dockerfile 층은 눈으로만 확인했다
```

**그래서 [5/5]에서 워커 도달을 평소보다 유심히 본다.** 빌드가 깨지면 Railway →
veo-worker → Deployments 의 빌드 로그부터. 크롬 설치 단계에서 깨졌으면 그 로그를
그대로 가져와서 고친다 — **렌더러는 기본 꺼짐이라, 급하면 Dockerfile 의 크롬 설치
층만 잠시 걷어내고 나가도 동작은 0.3.364 와 같다**(렌더 비교가 진단 못 함으로 남을
뿐이다). 걷어냈으면 대장에 그 사실을 적는다.

## 4. 배포 뒤 확인 — 이번 판 전용 셋

```bash
# ① 안내판이 닫혔나 (0.3.365) — 404 여야 한다. 200 이면 설정보다 코드가 낡은 것
curl -s -o /dev/null -w "docs=%{http_code}\n"  https://veo-platform-production.up.railway.app/docs
# ② 진단 창구가 닫혔나 — 404 여야 한다
curl -s -o /dev/null -w "scan=%{http_code}\n" -X POST https://veo-platform-production.up.railway.app/public/v1/seo-scans
# ③ 공유 리포트 링크는 살아 있나 — 404 가 **아니어야** 한다(없는 토큰이면 그 나름의 응답)
#    거래처에 이미 보낸 /results/{토큰} 링크 하나로 확인하는 것이 가장 확실하다
```

그리고 콘솔에서 진단 결과 하나를 열어 **등급이 A+~F 로 나오는지** 본다(0.3.366).
지난 판으로 발행된 리포트는 옛 이름(준비 완료 등) 그대로가 **정상**이다 — 표기 규칙 판.

## 5. 검증 상태 — 이 방에서 잰 것과 못 잰 것

나갈 커밋 기준(마지막 전수는 `9ff5ed5`, 0.3.369 는 웹 전용 — vitest 1,987·typecheck 0 로 검증):

```
잰 것     pytest 6,445 통과 · 0 실패     ← 단, DB 시험 제외(이 방에 DB 없음)
          ruff 0 · mypy 0 (416 파일)
          웹 vitest 1,985 통과 · typecheck 0 · 계약 일치(export_openapi --check)
못 잰 것   make ci-local 전체(DB 포함) · make test-db      ← preflight 가 다시 돈다
          워커 이미지 빌드                                  ← §3
          운영 API                                          ← §0
```

**preflight 를 동시에 두 개 돌리지 않는다** — 각자의 `test-db` 가 상대의 시험 DB 를
지운다(한 번 964건이 그렇게 빨간불이 됐다. 코드 결함이 아니었다).

**DB 가 꺼져 있으면 빨간불 셋이 한꺼번에 뜬다** — `connection refused … PGSQL.5432`.
코드가 아니라 방이 덜 갖춰진 것이다. §6 으로 켠다.

## 6. 샌드박스 재구성 (preflight 를 돌리려면)

```bash
# PostgreSQL — 기본 소켓·포트여야 백업·복원 시험까지 돈다
sudo -u postgres /usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/veo-test \
     -o '-p 5432 -k /var/run/postgresql' start
# DB 이름 veo_test

export VEO_TEST_DATABASE_URL='postgresql+psycopg://postgres@/veo_test?host=/var/run/postgresql&port=5432'
export PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
export PATH=/opt/node22/bin:$PATH        # pnpm · playwright 전역

# 파이썬 — 프로젝트가 >=3.12 를 요구한다. 3.11 로 만들면 설치가 거부된다(s09 실측)
python3.12 -m venv .venv
.venv/bin/pip install -e './apps/api[dev]'
.venv/bin/pip install -e apps/worker     # ← 빠뜨리면 ModuleNotFoundError: veo_worker
```

## 7. 어긋나면

| 어디서 | 무엇이 보이나 | 무엇을 하나 |
| --- | --- | --- |
| `[0/4]` | 「오늘 배포 상한에 이미 닿았습니다」 | 하루 2회 상한. 사장님 판단이면 `VEO_DEPLOY_LIMIT_PER_DAY=99 make deploy` |
| preflight ② | 「계약 드리프트」 | `apps/api` 에서 `scripts/export_openapi.py` → `pnpm --filter @veo/api-client generate` |
| preflight ③ | `connection refused` 여럿 동시 | DB 가 꺼진 것. §6 |
| preflight ③ | `two-words-only.test.ts` 빨간불 | 사장님 규칙 — 「커밋」·「배포」 두 단어만 |
| preflight ③ | 시험 빨간불 | **관문을 끄지 않는다.** 고친다 |
| `[3/4]` | CI 빨간불 | **main 은 안 건드려졌다.** `gh run view <id> --log-failed` 로 보고 고쳐서 다시 |
| `[5/5]` | 「워커가 도달 못 함」 | **main 에는 이미 배포됐다.** Railway → veo-worker → Deployments. 이번 판은 §3(크롬)일 확률이 가장 높다 |

## 8. 배포 뒤에 남는 것 — 사장님 몫

```
비교표 뽑기        (사장님 맥 등 바깥이 열린 자리에서)
                  python apps/api/scripts/compare_lab_measurements.py <거래처 주소> \
                      --runs 3 --key <PageSpeed 열쇠>
                  우리 자와 구글 자가 나란히 나온다. 성능 출처를 옮기는 다음 명세 판의 근거
렌더러 켜기        Railway 워커에 VEO_RENDERER_ENABLED=true — 크롬 실은 이미지가 나간 뒤,
                  비교표를 본 다음. 켜면 js_render_parity 가 판정을 받기 시작하고
                  그 항목은 관문이라 점수에 곱해진다
이월              #36 GSC env · #37 erp-v1 PR 허락 · #40 misojin v3 Drive 업로드
```

## 9. 제약 (반드시)

```
가지     veo-platform → claude/wonderful-einstein-1qiqm5
         desktop-tutorial → claude/wonderful-einstein-1qiqm5
         다른 가지에 올리지 않는다
커밋     Co-Authored-By / Claude-Session 트레일러 필수
금지     비밀키 값·모델 ID 를 커밋/PR/코드/문서/채팅에 넣지 않는다
말       사장님께 나가는 글은 「커밋」·「배포」 두 단어만
자료     실측 > 추론 > 날조 금지. 못 잰 값은 0 이 아니라 —(ADR 0002)
관문     무력화하지 않는다. 기준선을 고칠 땐 왜 바뀌었는지 그 자리에 적는다
PR       사장님이 시키지 않으면 만들지 않는다
```

## 10. 더 볼 곳

```
세션 기록    docs/session-logs/2026-08-28-s09.md   (이번 넉 판이 왜 생겼나)
veo 대장     (veo-platform) docs/WORKLIST.md §2 배포 대기 목록 — 열세 판 전체 표
판별 이력    (veo-platform) docs/WORKLIST-HISTORY.md 2026-08-28
내가 틀린 것  (veo-platform) docs/CORRECTIONS.md 165
```
