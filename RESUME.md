# RESUME — 다음 세션 이어가기 (2026-09-10 · s21 마감 · AEO 진단 방)

> 새 세션은 이 파일을 **먼저** 읽는다. 상세는 `docs/session-logs/2026-09-10-s21.md`.
> 현황 `PROJECT_STATE.md`, 지도 `핵심두뇌_MASTER.md`.

## 지금 사장님이 답을 주실 것 둘 (이게 제일 위다)

1. **SerpAPI 월 한도 숫자** — `https://veo.seokorea.org/console/dashboard` 맨 아래
   「사용량 · 한도 — 관측 창구」 첫 줄의 **「/ 월 ○○○」**.
   - **2,000 이상** → 아무것도 안 해도 된다.
   - **1,000(Starter)** → 한 단계 올려야 한다. [계산] 필요량 **월 1,650~1,980**
     (11곳 × 질문 5~6 × 월 10판 × **질문당 3회** — 오버뷰 2 + 네이버 1).
   - 바닥나면 그 **두 AI 가 «—»(못 잼)** 이 되어 일곱짜리 진단이 **다섯짜리**가 된다.
2. **배포 승인** — 대기 4건(`37387a3c`·`57d48f32`·`939c7ef2`·`5558e36a`).
   승인 오시면 veo-platform 가지에서 `make deploy`.

**GitHub 구독은 안 한다** — 「필수 검사」는 무료+비공개에서 GitHub 이 안 주는 기능이고
(403 · [실측 2026-09-10]), `make deploy` 가 CI 초록불에서만 main 에 닿으므로 이미 막고 있다.
구멍은 **웹에서 PR 을 손으로 합치는 경로** 하나 — 그건 「PR 로 합치지 않는다」는 규칙으로 막는다.

## 이번 세션에 끝낸 것

```
v0.3.559  모든 숫자가 제 범위를 말한다(한 판=날짜 · 합산=기간) ·
          진단 탭 도장이 정직해졌다(「이 판이 부른 AI n종」) ·
          **정기든 일회성이든 AI 일곱을 다 부른다**(엔진 고르는 자리를 하나로)
v0.3.561  gh 없는 방에서도 배포가 끝까지 간다(REST 흉내) · 판 물림 도구 수리
대기 4건   잔여 경고 복구 · 합산 섞임 표시 · 「요금제」 업체 이름 관문 · 대장 정리
```

**결함의 정체**(사장님 첫 물음의 뿌리): 엔진 고르는 자리가 **둘**이었다 —
정기는 `schedule.py`, 수동은 폼의 `engine` **단수**(기본 ChatGPT 하나). 판 종류는
체크박스에서 따로 왔으므로 **「AI 하나만 물은 정기 판」**이 만들어졌고 합산에 섞였다.
지금은 `engine_choices_of()` 하나로 합쳤고 「정기인데 엔진 지정」은 422 로 거절한다.

## 주의·제약

- 이 가지 외로 푸시 금지(veo-platform: `claude/aeo-graph-ai-mention-diff-ioo4bz`).
- 배포는 **`make deploy` 만**. 오더 없이 밀지 않는다. `VEO_DEPLOY_ORDER` 에 사장님 원문 인용.
- `deploy-candidate` 는 `--force` 정상. main 은 절대 force 금지.
- 대장·변경이력에 **「민다·푸시」 금지**(`two-words-only`) — 「커밋」·「배포」 두 낱말만.
- **돈 이야기는 업체 이름을 댄다**(`money-says-whose`) — 「요금제」만 쓰면 관문이 잡는다.
- 대장 `WORKLIST.md` 는 **1,200줄 상한**(`ledger-stays-current`). 지금 1,198줄 — **여유 2줄**.
  줄을 늘리지 말고 기존 줄 안에서 고칠 것.
- 대기 표와 §2 머리말의 미배포 범위가 일치해야 한다(`worklist.test.ts`).
- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01M2Z4aZUvu9XDna8jx9EH3A`. 모델 ID 는 트레일러에만.
- 사장님께는 「커밋」·「배포」 두 낱말만. 못 잰 값 «—», 지어낸 수치 금지, 의료광고법 준수.
- **이 방은 실서비스로 못 나간다**(프록시 CONNECT 403) — 잔여·판 실측은 화면이나
  `rollout-check.yml` 로 잰다.

## 아직 사장님 몫으로 남은 것 (대장 §5)

네이버 열쇠(최근 이레 실패 3건 · 만료 의심) · 진단 서버 무응답 · 공공데이터 인증키 ·
심평원 적재(Neon 플랜 판단) · Sentry · 배포 상한(GitHub Actions 무료 분량).

## 참고

- veo-platform 환경: `PYTHON=/usr/bin/python3.12 make setup` · `pnpm install` ·
  로컬 PostgreSQL(`service postgresql start`, role `root`/비번 `veo`, DB `veo_test`) ·
  `gh` 없으면 `scripts/gh_fallback.sh` 가 대신한다.
- preflight: `PGPASSWORD=veo VEO_TEST_DATABASE_URL="postgresql+psycopg://root:veo@localhost:5432/veo_test" make preflight`
