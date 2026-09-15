# RESUME (경쟁사·업종 방) — 2026-09-15

> **이 파일은 「경쟁사·업종 방」 것이다.** 루트 `RESUME.md`(진단 오진 방) ·
> `RESUME-aeo-grand.md`(자동 진단 방) · `RESUME-ring-loader.md`(링 로더 방)을 **덮지 않는다.**
> 상세는 `docs/session-logs/2026-09-15-s24.md`(이번) · `2026-09-11-s23.md`(앞선).
> 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금까지 (핵심만)

사장님 물음에서 시작했다 — *"여긴 병원이 아니라 마케팅인데, 왜 병원이 경쟁사로 나오지?"*

**판 둘이 나왔다.**

```
0.3.566  나갔다 (ANSEO 방이 냈다)
         빠진 답변의 이름을 업종 따라 뽑는다 + 마케팅·광고 업종 + 비교 대상 빼는 단추
0.3.583  **안 나갔다 — ANSEO 방에 넘겼다** (사장님 지시 2026-09-15 «ANSEO 방에 넘겨»)
         업종을 코드에서 자료로 + 기타면 홈페이지에서 읽는다
         가지 claude/industry-as-data · 끝 커밋 3f287874
```

## 바로 이어갈 작업

1. **0.3.583 이 나갔는지 확인한다.**
   ```
   git -C /home/user/veo-platform fetch origin main
   git merge-base --is-ancestor 3f287874 origin/main && echo 나갔다 || echo 아직
   ```
   아직이면 ANSEO 방에 이 문장을 그대로 준다 —
   ```
   veo-platform 가지 claude/industry-as-data 를 make deploy 로 내라.
   끝 커밋 3f287874 · 판 0.3.583 (이미 물려 있다).
   VEO_DEPLOY_ORDER 에 사장님 문장을 그대로 넣어야 밀린다.
   ```
   나갔으면 **대장 대기 표에서 내 줄만 지운다**(다른 방 줄은 안 건드린다).

2. **나간 뒤 사장님 몫 넷을 안내한다** — 1~4 는 이미 0.3.566 으로 나가 있어 지금도 된다.
   ```
   ① 거래처 「베놈」 업종을 📣 마케팅·광고 로 바꾸고 저장
   ② AEO 진단을 한 판 새로 돌린다 (저장된 옛 판은 옛 셈법 그대로다)
   ③ 「우리가 빠진 답변엔 누가 나오나」에서 병원이 사라졌는지 본다
   ④ /console/competitors 에서 자동 등록된 병원 다섯 곳을 「비교 대상에서 빼기」로 끈다
   ```

## 대기/차단

- **이 방은 `make deploy` 를 끝까지 못 끈다** [실측 2026-09-15 · 두 번]. 관문 재실행
  도중 프로세스가 잘린다(`setsid` 로 떼어도 같았다). **배포는 ANSEO 방 몫**이고,
  그것이 대장의 원래 규칙이기도 하다(사장님 지시 2026-09-09).
- **판 번호는 방 사이에서 부딪힌다** — 이번이 다섯 번째였고 내 것이 물러났다
  (0.3.582 → 0.3.583). 물러날 때 고칠 자리 다섯: `apps/api/src/veo/__init__.py` ·
  `changelog.ts` · `WORKLIST.md` 대기 표 · `WORKLIST.md` §2 미배포 줄 ·
  `WORKLIST-HISTORY.md`. 그 뒤 openapi 재생성 + api-client 재생성.
- **이 방은 운영을 못 잰다** — 운영 주소·운영 DB egress 403. 확인은 사장님 화면이 원천.

## 주의·제약

- **관문을 먼저 믿는다.** 이번에 관문이 일곱 번 세웠고 **일곱 번 다 맞았다**(배포 이미지에
  자료 미탑재 · mypy 열 곳 · 옛 자리를 세던 시험 · 60자 문장 · 배포 오더 문장 ·
  변경이력 · 대장 갱신). 「내 쪽이 맞는데 관문이 깐깐하다」고 생각되면 대개 내가 틀렸다.
- **사장님 몫을 적을 때는 지금 할 수 있는 것만 위에 둔다**(오류 대장 203). 못 하는 것은
  「나간 뒤」를 그 줄 안에 붙인다. 화면 안내는 그 화면에 그것이 있다는 것을 실측했을 때만.
- veo-platform 환경 세우기(컨테이너는 매번 초기화):
  ```
  PYTHON=/usr/bin/python3.12 make setup · pnpm install --frozen-lockfile
  service postgresql start
  su postgres -c "psql -c \"CREATE ROLE root LOGIN SUPERUSER PASSWORD 'veo'\""
  PGPASSWORD=veo PGUSER=root make ci-local     ← 이 환경변수 없으면 DB 시험이 전부 깨진다
  ```
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01NDFshUT74yv9JzuQyXmQSk`. 모델 ID 는 트레일러에만.
- 이 저장소(desktop-tutorial)의 가지는 `claude/stoic-fermi-i01mg7`. 다른 가지로 밀지 않는다.

## 참고 — 이번 판이 만진 자리

```
자료        packages/shared-types/industries.json        ← 새 업종은 여기 한 칸이 전부다
서버        industries/registry.py · schema.py · inference.py
이름 뽑기    observations/mention_roster.py (꼬리·일반명사를 자료에서 읽는다)
화면        lib/industries.ts · competitors/SiteIdentityPicker.tsx
이미지      infra/docker/{api,worker}.Dockerfile — 싣고(COPY) 가리킨다(ENV)
```
