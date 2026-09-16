# RESUME (경쟁사·업종 방) — 2026-09-16

> **이 파일은 「경쟁사·업종 방」 것이다.** 루트 `RESUME.md`(진단 오진 방) ·
> `RESUME-aeo-grand.md` · `RESUME-ring-loader.md` 를 **덮지 않는다.**
> 상세는 `docs/session-logs/2026-09-16-s25.md` → `2026-09-15-s24.md` → `2026-09-11-s23.md`.

## 지금까지 (핵심만)

사장님 물음에서 시작했다 — *"여긴 병원이 아니라 마케팅인데, 왜 병원이 경쟁사로 나오지?"*

```
0.3.566  나갔다   빠진 답변의 이름을 업종 따라 뽑는다 + 마케팅·광고 업종 + 비교 대상 빼는 단추
0.3.585  나갔다   업종을 코드에서 자료로 + 기타면 홈페이지에서 읽는다(추정·근거)
  —      **넘겼다**  「대구병원마케팅」에서 「대구병원」이 잘리던 것 (MEDICAL)
                  가지 claude/medical-name-cut-by-following-word · 끝 커밋 4313844e
```

## 바로 이어갈 작업

1. **넘긴 판이 나갔는지 확인한다.**
   ```
   git -C /home/user/veo-platform fetch origin main
   git -C /home/user/veo-platform merge-base --is-ancestor 4313844e origin/main \
     && echo 나갔다 || echo 아직
   ```
   아직이면 ANSEO 방에 이 문장을 그대로 준다 —
   ```
   veo-platform 가지 claude/medical-name-cut-by-following-word 를 make deploy 로 내라.
   끝 커밋 4313844e. 판 번호는 안 물려 있다 — 나갈 때 정한다.
   VEO_DEPLOY_ORDER 에 사장님 문장을 그대로 넣어야 밀린다.
   ```
   나갔으면 **대기 표에서 이 방 줄만** 지운다.

2. **사장님 몫 넷을 안내한다** — 0.3.566·0.3.585 로 이미 나가 있어 지금도 된다.
   ```
   ① 거래처 「베놈」 업종을 📣 마케팅·광고 로 바꾸고 저장
   ② AEO 진단을 한 판 새로 돌린다 (저장된 옛 판은 옛 셈법 그대로다)
   ③ 「우리가 빠진 답변엔 누가 나오나」에서 병원이 사라졌는지 본다
   ④ /console/competitors 에서 자동 등록된 병원 다섯 곳을 「비교 대상에서 빼기」로 끈다
   ```

3. **(보류) 대장 대기 표에 나간 줄이 남아 있다.** 가지 `claude/worklist-drop-shipped-rows`
   (`51d09cdc`)를 만들어 뒀으나 **낡았다** — 그 줄들의 번호가 배포마다 다시 찍힌다
   (0.3.585 → 0.3.588). 같은 자리를 키워드 구름 방이 손대는 중(오류 215)이라 두고 본다.
   다시 하려면 최신 main 기준으로 새로 만든다.

## 대기/차단

- **이 방은 `make deploy` 를 끝까지 못 끈다** [실측 2026-09-15 · 두 번]. 관문 재실행 도중
  프로세스가 잘린다(`setsid` 로 떼어도 같았다). **배포는 ANSEO 방 몫.**
- **판 번호는 방 사이에서 부딪힌다.** 내 판이 두 번 물러났다(0.3.582→583→585).
  물러날 때 고칠 자리 다섯: `apps/api/src/veo/__init__.py` · `changelog.ts` ·
  `WORKLIST.md` 대기 표 · `WORKLIST.md` §2 머리말 · `WORKLIST-HISTORY.md`.
  그 뒤 `export_openapi.py` + api-client 재생성.
- **§2 머리말 규칙** — 대기 표에 `—` 줄이 있으면 머리말에 「· 번호 미정 **N건**」을 적어야
  관문(`worklist.test.ts`)이 통과한다. 숫자가 어긋나도 실패한다.
- **이 방은 운영을 못 잰다** — egress 403. 확인은 사장님 화면이 원천.

## 주의·제약

- **관문을 먼저 믿는다.** 이 방에서 관문이 아홉 번 세웠고 **아홉 번 다 맞았다**(배포 이미지에
  자료 미탑재 · mypy 열 곳 · 옛 자리를 세던 시험 · 60자 문장 · 배포 오더 문장 · 변경이력 ·
  대장 갱신 · 대기 표 머리말 둘). 「관문이 깐깐하다」 싶으면 대개 내가 틀렸다.
- **사장님 몫은 지금 할 수 있는 것만 위에 둔다**(오류 대장 203). 못 하는 것은 「나간 뒤」를
  그 줄 안에 붙인다.
- **이름 뽑기를 건드릴 땐 「무엇을 안 건드리나」를 시험 절반으로 쓴다** — 병원 거래처
  전부가 걸린다. 이번 판의 「띄어 쓴 것·조사」가 그 자리다.
- veo-platform 환경(컨테이너는 매번 초기화):
  ```
  PYTHON=/usr/bin/python3.12 make setup · pnpm install --frozen-lockfile
  service postgresql start
  su postgres -c "psql -c \"CREATE ROLE root LOGIN SUPERUSER PASSWORD 'veo'\""
  PGPASSWORD=veo PGUSER=root make ci-local     ← 없으면 DB 시험이 전부 깨진다
  ```
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01NDFshUT74yv9JzuQyXmQSk`.
- 이 저장소(desktop-tutorial)의 가지는 `claude/stoic-fermi-i01mg7`.

## 참고 — 이 방이 만진 자리

```
자료   packages/shared-types/industries.json
       업종 추가 = 여기 한 칸. mention_not_followed_by 도 여기 있다
서버   industries/{registry,schema,inference}.py · observations/mention_roster.py
화면   lib/industries.ts · competitors/{SiteIdentityPicker,BrandForm}.tsx
이미지 infra/docker/{api,worker}.Dockerfile — 싣고(COPY) 가리킨다(ENV)
```
