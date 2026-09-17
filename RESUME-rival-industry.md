# RESUME (경쟁사·업종 방) — 2026-09-17

> **이 파일은 「경쟁사·업종 방」 것이다.** 루트 `RESUME.md`(진단 오진 방) ·
> `RESUME-aeo-grand.md` · `RESUME-ring-loader.md` 를 **덮지 않는다.**
> 상세는 `docs/session-logs/2026-09-17-s26.md` → `2026-09-16-s25.md` → `2026-09-15-s24.md`.

## 지금까지 (핵심만)

사장님 물음에서 시작했다 — *"여긴 병원이 아니라 마케팅인데, 왜 병원이 경쟁사로 나오지?"*
이번 판은 그 뒤에 붙은 물음이다 — *"왜 이렇게 오래 걸리지?"* (재진단이 「준비」로 9분 30초)

```
0.3.566  나갔다   빠진 답변의 이름을 업종 따라 뽑는다 + 마케팅·광고 업종 + 비교 대상 빼는 단추
0.3.585  나갔다   업종을 코드에서 자료로 + 기타면 홈페이지에서 읽는다(추정·근거)
0.3.595  나갔다   「대구병원마케팅」에서 「대구병원」이 잘리던 것 (실측 2026-09-17 · main 3efbde84)
  —      **넘겼다**  ① 도는 판이 어디 있는지 화면이 말한다  ② 기다림에 끝을 둔다
                  가지 claude/job-says-where-it-is · 머리 0d5b3a67 · 관문 전부 초록
```

## 바로 이어갈 작업

1. **넘긴 가지가 나갔는지 확인한다.**
   ```
   git -C /home/user/veo-platform fetch origin main
   git -C /home/user/veo-platform merge-base --is-ancestor 0d5b3a67 origin/main \
     && echo 나갔다 || echo 아직
   ```
   아직이면 ANSEO 방에 이 문장을 그대로 준다 —
   ```
   veo-platform 가지 claude/job-says-where-it-is 를 make deploy 로 내라.
   머리 0d5b3a67 · main(3efbde84 · 0.3.595) 위 · 뒤진 커밋 0건.
   판 둘: ① 돌기 시작한 작업이 선언한 첫 단계를 적고, 화면이 「차례를 기다리는
   중입니다」(아무도 안 집어감)와 「아직 시작하지 못했습니다」(집혔는데 안 돎)를 가른다
   ② 기다리는 잡이 까닭을 적고, 내보내기가 연속 다섯 번 실패하면 그 잡을 끝으로 보낸다.
   관문은 나갈 그 커밋에서 전부 초록(ci-local 7,711 · test-db 1,332 · 웹 313파일 2,681).
   판 번호는 안 물려 있다 — 나갈 때 정한다.
   VEO_DEPLOY_ORDER 에 사장님 문장을 그대로 넣어야 밀린다.
   ```
   나갔으면 **대기 표에서 이 방 줄 둘만** 지우고 머리말의 「번호 미정 N건」을 맞춘다.

2. **나간 뒤에 볼 두 줄** — 같은 증상이 또 나면 화면이 스스로 말한다.
   ```
   재진단을 걸고 링 아래 한 줄을 본다
     「질문 준비」          → 정상. 돌기 시작했다
     「차례를 기다리는 중」 → 아무도 안 집어갔다
     「아직 시작하지 못했습니다」 → 집혔는데 아무도 안 돌린다
     「내보내지 못했습니다 (n/5)」 → 다섯 번째에 실패로 끝난다(다시 누를 수 있다)
   ```

3. **사장님 몫 — 원인은 아직 안 잡혔다.** 이 두 판은 **보이게** 한 것이지 고친 것이 아니다.
   ```
   ① https://veo-platform-production.up.railway.app/api/queue  → workers 가 0 이면
      「보내는 곳에 아무도 없다」가 확정(브로커 어긋남 · 08-18·08-19·08-20 과 같은 사고)
   ② 화면을 20분 두어 「진행 상황을 알 수 없습니다」로 바뀌는지 본다
   ③ 거래처 「베놈」 업종 📣 마케팅·광고 · 재진단 · 표에서 병원이 사라졌는지 · /console/competitors
      에서 자동 등록된 병원 다섯을 「비교 대상에서 빼기」
   ```

4. **(보류) 대장 대기 표에 나간 줄이 남아 있다.** 가지 `claude/worklist-drop-shipped-rows`
   (`51d09cdc`)는 **낡았다**(번호가 배포마다 다시 찍힌다). 다시 하려면 최신 main 기준으로.

## 대기/차단

- **이 방은 `make deploy` 를 끝까지 못 끈다** [실측 2026-09-15 · 두 번]. **배포는 ANSEO 방 몫.**
  다만 **`make preflight` 는 이 방에서 끝까지 돈다** [실측 2026-09-17 · 두 번 · 배경 실행].
- **이 방은 운영을 못 잰다** — [실측 2026-09-17] Railway 443 egress **403**. 확인은 사장님 화면이 원천.
- **판 번호는 방 사이에서 부딪힌다.** 미리 물리지 않는다 — 대기 표에 `—` 로 쌓고
  `claim_version` 이 나갈 때 정한다.
- **§2 머리말 규칙** — 대기 표에 `—` 줄이 있으면 머리말에 「· 번호 미정 **N건**」을 적어야
  관문(`worklist.test.ts`)이 통과한다. 숫자가 어긋나도 실패한다.

## 주의·제약

- **관문을 먼저 믿는다.** 이 방에서 관문이 세운 자리는 지금까지 **전부 내가 틀린 자리**였다.
- **못 잰 것은 못 쟀다고 적는다.** 이번에도 preflight ⑤(GitHub 최근 실행)를 못 읽어 그대로 적었다.
- **사장님 몫은 지금 할 수 있는 것만 위에 둔다**(오류 대장 203).
- **화면 글자는 서버가 한 말과 빈자리를 갈라 쓴다** — 「준비」가 그 둘을 뭉개서 9분 30초를
  못 가렸다. 새 글자를 넣을 땐 「이것은 누가 말한 것인가」를 먼저 답한다.
- veo-platform 환경(컨테이너는 매번 초기화):
  ```
  PYTHON=/usr/bin/python3.12 make setup · pnpm install --frozen-lockfile
  service postgresql start          ← 세션 중에도 꺼진다. 죽으면 다시 켠다
  su postgres -c "psql -c \"CREATE ROLE root LOGIN SUPERUSER PASSWORD 'veo'\""
  PGPASSWORD=veo bash scripts/preflight.sh   ← 배경으로 돌린다(앞에서 돌리면 잘린다)
  ```
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01NDFshUT74yv9JzuQyXmQSk`.
- 이 저장소(desktop-tutorial)의 가지는 `claude/stoic-fermi-i01mg7`.

## 참고 — 이 방이 만진 자리

```
자료   packages/shared-types/industries.json   업종 추가 = 여기 한 칸
서버   industries/{registry,schema,inference}.py · observations/mention_roster.py
       jobs/service.py(begin·stage_at_start) · jobs/release.py(까닭·상한·claim)
화면   lib/industries.ts · competitors/{SiteIdentityPicker,BrandForm}.tsx
       geo/JobWatch.tsx(링 아래 한 줄)
이미지 infra/docker/{api,worker}.Dockerfile — 싣고(COPY) 가리킨다(ENV)
```
