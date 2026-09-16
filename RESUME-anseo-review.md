# RESUME (검수 방 · ANSEO 96항목) — 2026-09-15 s26 마감

> **이 저장소에 인계가 여럿이다 — 이 방 것은 이 파일이다.**
> 루트 `RESUME.md`(진단 오진 방) · `RESUME-aeo-grand.md` · `RESUME-ring-loader.md` ·
> `RESUME-motion-port.md` 는 **다른 방** 것이다.
> 상세는 `docs/session-logs/2026-09-15-s26-anseo-review.md`(그 앞은 `…-s25-…`). 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)

96항목 검수는 **끝났다**(s24). 판 둘이 나갔고 표에 남은 것은 사장님 몫뿐이다.

```
0.3.576   veo-platform main 9c35d958   수집기 넷 + 배포 도구 둘
0.3.577   veo-platform main 1a801344   명세 개정 셋 + 작업 단계 표
```

큰 것 셋 — **GEO 1.9.0**(붉은 「노출 차단」 띠와 점수가 반대로 말하던 것. 멀쩡한 사이트
100.000 → 100.000 · noindex 95.062 → **0.000**) · **SEO 1.13.0**(제목 중복 이중 감점.
겹침 53.96 → 64.06) · **제목 길이를 폭으로**(`veo/common/text_width.py` 하나로).

s25 는 묵은 것을 치웠다(s23·s24 기록을 main 에 담고 · 열린 PR 6건을 다 닫고 ·
`effective_at` 이 스위치가 아니라는 것을 찾았다).

**s26 이 한 것 넷** — 판 셋이 나갔고(0.3.581·0.3.582·0.3.584) **이 방이 도는 판을
처음으로 «—» 없이 적었다**(러너로 쟀다).

- **연동 없이 소유권을 잰다** (사장님 «서치콘솔은 연결하지 않고 별도로 진단»).
  소유 확인 태그는 콘솔이 아니라 사이트의 `<head>` 에 있고 우리는 그 HTML 을 이미
  가져온다 — `gsc_verified`·`naver_swa_registered` 가 「영원히 진단 못 함」에서
  벗어났다. 네이버는 공개 API 가 없어 **이것이 유일한 길**이다. 태그가 없으면
  **실패가 아니라 진단 못 함**이다(확인 방법이 넷인데 우리가 보는 것은 하나).
  [실측] 태그 유무로 종합 89.24 → 89.24 · 시험 10.
- **판 물리기가 이미 나간 기록에 새 번호를 달던 것** — 아래 ⓐ. 기록을 되돌려 채우고
  관문을 세웠다.
- **「연결하면 잴 수 있다」를 못 재는 자리에 쓰지 않는다**(사장님 «ⓐ») — 명세 SEO
  **1.14.0** `NOT_OBTAINABLE`. [실측] 89.24 → 89.24 로 **점수는 안 움직이고 문구만** 바뀐다.
  곁들여 **`REFERENCE_ONLY` 가 2026-08 부터 화면에서 접히던 것**(참고 항목이 배점 안으로
  들어와 있었다)을 고쳤다.
- **도는 판 확인이 명세 판도 읽는다**(사장님 «니가 확인해줘»·«워크플로도 같이 내보내») —
  러너로 `/api/scoring/specs` 까지 읽는다. **판 번호만으로는 「명세가 먹는지」를 못 말한다.**

## 지금 상태 — 판 넷이 나갔다 (0.3.581 · 0.3.582 · 0.3.584)

```
[실측 2026-09-16 00:0x KST · git + 러너]
veo-platform       main eadacd49 = 0.3.584 · 내 커밋 전부 main 의 조상
                   가지가 1커밋 앞(도장) · 대기 표 번호 미정 2건
desktop-tutorial   미커밋 0 · main 보다 앞선 커밋 있음(기록·인계)
가지: desktop-tutorial claude/friendly-mendel-mlvpsa
      veo-platform     claude/same-page-same-verdict
```

```
0.3.581   연동 없이 소유권 재기 + 판 물리기 관문        오더 «지금 내보낸다»
0.3.582   명세 SEO 1.14.0 NOT_OBTAINABLE + 참고 항목    오더 «내보내»
0.3.584   도는 판 확인이 명세 판도 읽는다               오더 «워크플로도 같이 내보내»
          (0.3.583 은 다른 방 몫)
```

**도는 판을 이 방이 잰다 — 러너로.** 배포 [5/5] 는 여전히 「못 쟀습니다」지만(egress 403)
그 자리를 워크플로가 메운다.

```
[실측 2026-09-15 23:46 KST · 러너]
  /api/health 200 → 0.3.584 · /api/queue 200 → 워커 ["0.3.584"] · stale 0
  /api/scoring/specs 200 → GEO 1.9.0 · SEO 1.14.0
  커밋 14:31:10Z → 서비스 14:42:59Z (11분 49초 뒤 = 같은 코드)
```

**대기 표 번호 미정 2건** — ① 판 물리기가 남의 대기 줄에도 번호를 달던 것(옮긴 줄을
찍게 했다) ② 키워드 구름 방 몫 하나. **배포 오더는 없다.**

## ⓐ s26 이 찾은 것 — 나간 판 넷이 변경이력에 없었다

[실측 2026-09-15 · git] 변경이력 **맨 위 항목 하나가 네 번 이름을 갈았다**.

```
f7293bd0   0.3.573 으로 적힘 · 그 내용이 그 번호로 나갔다
a8589c42 → 0.3.574     81ee22a5 → 0.3.575
9c35d958 → 0.3.576     1a801344 → 0.3.577
```

`claim_version` 은 「변경이력 맨 위 항목은 아직 안 나간 것」을 전제로 자리를 고른다.
**배포하는 방이 자기 항목을 안 쓰면 그 전제가 깨진다** — 이미 나간 항목이 새 번호를
받는다. 0.3.574~0.3.577 네 판은 무엇이 나갔는지 적힌 곳이 없었고, 사장님이 읽는
변경이력은 0.3.577 이라는 이름으로 **09-13 에 나간 일**을 적고 있었다.

되돌려 채웠다 — 09-13 항목은 0.3.573 으로, 이 방이 낸 **0.3.575·576·577** 세 판의
항목을 적었고, 날짜별 기록에 `2026-09-14` 절을 넣었다. **0.3.574 는 비워 두었다**
(이 방 것이 아니다 — 남의 방 몫을 그 방 말투로 지어 적지 않는다).

관문: `origin/main` 의 맨 위 기록과 **같으면** 번호를 옮기지 않고 선다. main 을 못
읽으면 「못 쟀습니다」를 적고 지나간다. 시험 4 · 반증 확인(고치기 전 저장소에서 실제로
걸렸다).

## 바로 이어갈 작업

0. **크롤 한도 — 사장님이 답했다(2026-09-16 · 예정 확인).** 세 갈래 중
   **「한도를 올린다」는 버린다. 나머지 둘을 같이 한다.**

   ```
   부분 크롤을 기록한다   어디까지 쟀는지 화면에 적는다 (예: 120쪽 중 50쪽을 쟀습니다)
   못 잰 항목은 «—»       「해당 없음」이 아니라 「못 쟀다」로 적는다
   ```

   **근거는 이 저장소가 비싸게 배운 것** — 오류 135·192. 못 읽은 것을 실패로 적었다가
   멀쩡한 사이트를 BLOCKER 로 내보낸 건이다. **안 잰 것과 결함인 것은 다르다.**
   한도를 올리지 않는 까닭: 남의 서버를 더 때린다(s20 진단 비용 보고서 — 30분 텀은
   돈이 아니라 남의 서버와 「잘린 진단」을 막는 장치다). 「해당 없음」이 아닌 까닭:
   그 항목은 **해당되는데 우리가 못 잰 것**이라 거짓이 된다.

   **판정을 부분 크롤에서 지어내지 않는다** — 50쪽만 보고 「전체가 통과」라고 적지 않는다.
   분모를 화면에 적고 못 본 자리는 «—» 로 둔다.

   ⚠️ **이 결정은 점수를 돌려주지 않는다.** 진단 못 함은 절대 평가에서 0 이므로
   201장 넘는 사이트의 −10.49점은 **그대로 남는다.** 이 판이 고치는 것은 **왜 그런지가
   화면에 보이지 않던 것**이다. 점수를 돌려주려면 「우리 한도 때문에 못 봄」을 배점에서
   빼는 새 갈래가 필요하고, 그것은 또 하나의 결정이다(SEO 1.14.0 의 `NOT_OBTAINABLE` 과
   같은 모양).

   함께: **렌더러도 같은 원칙으로** — 못 그린 것은 못 그렸다고 적고 지어내지 않는다.


1. ~~**1.9.0 이 실제로 먹는지 확인**~~ → **끝났다**(위 실측 · 러너). 남은 것은 하나뿐 —
   **막힌 거래처에 진단을 한 번 새로 돌려** 0.000 이 나오는지 보는 것이다(옛 리포트는
   설계대로 안 바뀐다). 아래 옛 설명은 그때의 것이다.

   ~~**막힌 거래처의 GEO 리포트를 연다.**~~
   이 방은 못 잰다(운영 주소 egress 403). **이것 하나로 0.3.577 이 도는지까지 같이 답이 난다.**
   ```
   noindex 거래처의 GEO 점수
     0.000  → 1.9.0 이 돈다. 끝.
     95.062 → 화면에 1.9.0 이라 적혀 있어도 워커가 옛 판이다.
   ```
   **⚠️ `effective_at` 에 속지 말 것.** `1.9.0.yaml` 에 `effective_at: 2026-09-15` 가 적혀
   있지만 **날짜는 스위치가 아니다.** `latest_published()` 는 `status: PUBLISHED` 중 가장
   높은 판을 고를 뿐 날짜를 **보지 않는다**(`apps/api/src/veo/scoring/spec.py`).
   **1.9.0 은 0.3.577 이 도는 순간부터 이미 적용 중이다.** SEO 1.13.0 도 같다.

   곁길 둘 — 콘솔 `/console/scoring-versions`(「지금 적용 중인 명세」) · `GET /api/scoring/specs`.
   둘은 「명세가 있다」까지만 말한다. **점수가 움직이는지**는 리포트로 봐야 한다.

2. ~~**조치 문구 — 사장님 결정**~~ → **끝났다**(0.3.582 · 사장님 «ⓐ 명세에 새 availability
   값»). 명세 SEO **1.14.0** 이 `NOT_OBTAINABLE` 을 두고 네이버 등록 검사에 물렸다 — 화면은
   「공개 조회 창구가 없어 자격증명으로도 확인할 수 없습니다」로 적는다. [실측] 점수는
   89.24 → 89.24 로 **한 점도 안 움직인다**. **계약은 안 움직였다**(화면 계약의
   `availability` 가 이미 `string` 이라 ⓑ 였으면 움직였을 자리다).
   곁들여 **`REFERENCE_ONLY` 가 2026-08 부터 화면에서 접히던 것**을 고쳤다 — 모르는 값은
   `SELF_SERVICE`(우리가 재는 항목)로 접히므로 **참고 항목이 배점 안으로 들어와 있었다.**

   ~~아래 옛 설명~~ — 태그가 없는 네이버 자리에서
   화면이 이렇게 나간다 — 앞 문장이 **있지도 않은 열쇠**를 찾아 나서게 한다.

   ```
   사이트 소유자가 권한을 연결해야 측정됩니다. … (공개 API 가 없어 자격증명을
   받아도 이 값은 조회할 수 없습니다)
   ```

   문구가 명세의 `availability` 별로 정해지고 값이 셋뿐(`CUSTOMER_GRANTED`·
   `PAID_PROVIDER`·`REFERENCE_ONLY`)이라 그 자리를 가리킬 이름이 없다. [실측 2026-09-15]
   `CheckOutcome` 은 `extra="forbid"` 에 칸이 다 차 있어 **그냥 실어 보낼 자리도 없다.**

   ```
   ⓐ 명세에 새 `availability` 값 (권함)  SEO 1.14.0 발행 · 계약·생성 클라이언트 무변경
   ⓑ `CheckOutcome` 에 한 칸            계약 개정 → openapi·생성 클라이언트·웹 타입까지
   ```

   **ⓐ 를 권한다** — 「열쇠를 받아도 못 잰다」는 그 검사의 성질이고 한 관측의 성질이
   아니다. 어느 쪽이든 판을 올리는 일이라 오더를 받고 한다.

3. ~~**서치콘솔을 진단에 배선**~~ — **배선하지 않는다**(사장님 2026-09-15). 연동 없이 잴
   수 있던 둘은 태그로 열었고, 나머지 넷은 **페이지에서 잴 길이 없다**:
   `sitemap_submitted`(제출·처리는 콘솔만 안다 — robots.txt 의 `Sitemap:` 줄은 이미
   `seo.sitemap.discoverable` 이 세므로 여기서 또 읽으면 한 사실을 두 번 세는 것) ·
   `impressions_available`·`data_freshness`(성과 자료) · `indexnow_configured`(키 파일
   이름을 모른다). `index_coverage_healthy` 는 **진단 못 함으로 남는 것이 정확하다** —
   색인된 페이지 수는 검색엔진만 아는 값이다.

## 대기/차단 — 사장님 몫

- **방 사이 약속 하나 — 대기 표의 「내 줄」을 기계가 가를 수 있게 할지.** [실측 2026-09-15]
  0.3.584 배포가 `claim_version` 을 돌릴 때 **키워드 구름 방의 번호 없는 줄에도** 그 번호를
  달았다(그 도구는 번호 없는 줄을 전부 이번 판으로 본다). 대장이 **나가지 않은 일감을
  나갔다고** 말한 것이고, 도장 찍을 때 사람이 알아채 되돌렸다. 지금은 **옮긴 줄을 전부
  찍어** 사람이 가르게 해 뒀다. 기계로 가르려면 「대기 줄에 자기 방 이름을 반드시 적는다」
  같은 약속이 필요하고, 그것은 방 셋이 함께 지켜야 하는 규칙이라 사장님 몫이다.

- **렌더러를 켤지** — Railway **`veo-worker`** → Variables → `VEO_RENDERER_ENABLED=true`.
  **순수한 이득이 아니다** — 켜면 `seo.content.js_render_parity` 가 SEO 관문 항목이라 점수에
  곱해지고, **자바스크립트로 본문을 그리는 거래처 점수가 내려간다.** 못 보던 것이 보이는
  것이지만 화면에는 「점수가 떨어졌다」로 보인다. 사전 대조는 이 컨테이너에서 못 돌린다.
- **배포 상한 재설정** — 상한 기간(2026-09-01)이 지나 `deploy.sh` 가 더 이상 세지 않는다.
  배포 관문 ⑤ 는 여전히 「오늘 2건 — 상한을 다 썼다」고 말하지만 **막지는 않는다.**
- **CI 를 필수 검사로** — `Settings → Branches → main → Require status checks`.
  이게 없어 빨간불 PR 이 main 에 들어온 적이 있다(다른 방에서 올라온 오래된 건).

## 닫은 PR 6건 — 되살리는 법 (s25)

내용이 사라진 것이 아니다. **가지가 전부 그대로 남아 있다.** 다시 열면 살아난다.

| PR | 무엇 | 가지 |
|---|---|---|
| #228 | scoring-versions 고침 | `claude/youthful-lalande-056fd4` ← **이미 해결됨**(veo-platform 에 들어가 있다) |
| #4 | 마스터클래스 발표자료 | `claude/claude-design-ppt-8rn123` |
| #5 | 디자인 리소스 페이지 | `claude/design-resources-repo-bn1108` |
| #6 | Auto-Site Factory | `claude/auto-website-generator-qz1azp` |
| #7 | ERP V2 기획·WBS | `claude/venom-erp-planning-brgkp6` |
| #12 | 원고 스튜디오 | `claude/manuscript-prompt-creation-i0a3g7` |

#228 외 다섯은 **내용이 아직 main 에 없다** — 되살릴 값이 있으면 지금 코드 위에서 다시
세우는 편이 빠를 수 있다(특히 #12, 31파일·4,501줄).

## 주의·제약

- **개발 환경 세우기**(컨테이너는 매 세션 초기화된다):
  ```
  PYTHON=/usr/bin/python3.12 make setup
  pnpm install --frozen-lockfile        # ← cd 가 백그라운드 첫 작업에만 걸린다, 주의
  service postgresql start
  su postgres -c "psql -c \"CREATE ROLE root LOGIN SUPERUSER PASSWORD 'veo'\""
  PGPASSWORD=veo make db-test-create
  ```
  관문은 `VEO_TEST_DATABASE_URL="postgresql+psycopg://root:veo@localhost:5432/veo_test" \
  PGPASSWORD=veo bash scripts/preflight.sh`.
  [실측 2026-09-15 · s26] **여섯 단계 전부 초록 — 「준비됨」** (ci-local **7,614** · 웹 2,578 ·
  오늘 CI 상한 2회 중 1회 남음). 배포 오더만 없다.
- **이 방이 못 재는 운영 값은 러너로 잰다** — 프록시가 운영 주소 CONNECT 를 403 으로
  막지만(`curl -sS "$HTTPS_PROXY/__agentproxy/status"` 가 「policy denial」로 적는다)
  GitHub 러너는 나간다. `rollout-check.yml`(도는 판·명세) · `engine-check.yml`(엔진 열쇠)
  를 **`mcp__github__actions_run_trigger`** 로 부른다 — 옛 인계의 「dispatch 403」은 `gh`
  이야기고 MCP 도구로는 뜬다. **`ref` 로 가지의 워크플로 파일을 돌릴 수 있다** — main 에
  넣기 전에 재 볼 수 있다. 로그는 `mcp__github__get_job_logs`(job_id 는
  `gh api repos/.../actions/runs/<run>/jobs`).
  **응답을 자를 때 조심한다** — 명세 목록은 수만 자라 `head -c 1200` 이 맨 앞의 옛 판만
  남긴다. 2026-09-15 에 그것을 「1.0.0 이 돈다」로 읽을 뻔했다.
- **컨테이너의 Postgres 가 세션 중에 죽는다** — [실측 2026-09-15] 하루에 **두 번**.
  `preflight ③` 이 빨간불이면 **먼저 `service postgresql status`** 를 본다(`down` 이면
  `service postgresql start`). 죽은 까닭은 **못 쟀다** — 로그에 종료·PANIC 기록이 없고
  OOM 도 디스크도 아니었다. 크래시가 아니라 바깥에서 멈춘 것으로 보인다(단정 안 한다).
- **배포는 채점 8분 동안 다른 방과 경주한다** — [실측 2026-09-15] `[4/5]` 거절 **두 번**.
  창이 겹치면 늘 나중 것이 물러난다. 그래서 **다른 방 채점이 빈 것을 보고** 들어간다:
  `gh run list` 에 `deploy-candidate-*` 가 `in_progress` 면 기다린다(20초 간격 폴링).
  기다리는 스크립트 — **컨테이너에만 있었으므로 여기에 남긴다**(방을 지우면 사라진다):
  ```bash
  #!/bin/bash
  # 다른 방 채점이 끝나기를 기다린다 — 내 채점 창(8분)이 저쪽 창과 겹치면 [4/5] 에서 진다.
  for i in $(seq 1 60); do
      running="$(gh run list --limit 10 --json headBranch,status --jq \
          '[.[] | select(.status != "completed")
                | select(.headBranch | startswith("deploy-candidate"))
                | select(.headBranch != "deploy-candidate-<내 가지>")] | length' 2>/dev/null)"
      [ "$running" = "0" ] && { echo "비었다 — 지금이 창이다"; exit 0; }
      echo "  대기 $((i * 20))초 · 도는 방 $running"; sleep 20
  done
  echo "10분 기다려도 안 비었다 — 사람이 정할 일이다"; exit 1
  ```

- **선 배포는 판을 반쪽 물려 놓고 죽는다.** [실측 2026-09-15] `[1/4]` 이 `bump-version` 으로
  판 셋(`__init__.py`·`openapi.json`·`changelog.ts`)을 올리고 대장에서 섰다. `git add -A` 로
  쓸어담으면 **반쪽 판이 커밋된다** — s24 에 겪고 여기 적어 뒀는데 **또 밟았다.**
  대장 관문이 잡았다. 되돌릴 때 `bump-version` 은 내리는 것을 막으므로(옳다) `__init__.py` 를
  손으로 되돌리고 계약은 `export_openapi.py` 로 다시 뽑는다.
- **`make test-api` 와 `make ci-local` 은 범위가 다르다.** 커밋 전에 좁은 쪽만 돌리면
  배포 관문에서 걸린다. `ci-local` 을 직접 돌릴 땐 DB 주소를 줘야 한다(안 주면 오류 1,240건).
- **판 목록은 `available_specs()` 로 본다.** `ls | tail` 은 사전순이라 `1.10.0` 이 `1.9.2`
  보다 앞에 온다 — s24 에 그것에 속아 **이미 발행된 1.10.0 을 덮어썼다**(되돌렸다).
  발행본은 불변이다(ADR 0012).
- **판 번호는 나갈 때 물린다.** 선 배포가 실패하면 `__init__.py`·`openapi.json`·
  `changelog.ts` 에 새 판을 적어 놓고 죽는다 — `git add -A` 로 쓸어담지 말고 되돌린다.
- **배포는 `make deploy` 만.** `VEO_DEPLOY_ORDER` 에 **사장님 원문 그대로.** 「진행해」류는
  배포 오더가 아니다. 초록불이어도 주문 없이 밀지 않는다.
- **이 방은 실서비스를 못 잰다** — `veo.seokorea.org`·Railway 전부 egress 403.
  못 잰 값은 `0` 이 아니라 `—`. 지어낸 수치 금지.
- 가지: veo-platform `claude/same-page-same-verdict` · desktop-tutorial `claude/friendly-mendel-mlvpsa`.
  **다른 가지로 커밋 금지.**
- **다른 방 줄은 건드리지 않는다** — `RESUME.md`·`STATE.md`·`WORKLIST.md` 충돌은 저쪽을
  살리고 내 줄만. `PROJECT_STATE.md` 충돌은 **손으로 고치지 말고 재생성**한다
  (`node scripts/gen-project-state.mjs`).
- 대장·변경이력에 「민다·푸시」 금지(`two-words-only` 관문) — 「커밋」·「배포」 두 낱말만.
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01JLjPMtA7oQ2LnbA8hrS79J`.
  **커밋·PR·코드에 모델 ID 를 넣지 않는다.** 의료광고법 준수.

## 참고

- veo-platform 은 `add_repo`(owner `recon9973-lang`) → `/home/user/veo-platform`.
- 검수 보고서 `docs/2026-09-13-ANSEO-96항목-수집진단제안-검수.md`.
- s24 에 세운 관문 넷: `test_deploy_says_what_it_could_not_measure.py` ·
  `test_one_ruler_measures_the_title.py` · `test_one_defect_is_charged_once.py` ·
  `test_the_gate_and_the_band_agree.py`.
- 명세 판 이력: `packages/scoring-specs/specs/veo.{seo,geo}.readiness/` ·
  근거 대장은 `basis/external-basis.yaml`.
