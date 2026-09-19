# RESUME — 다음 세션 이어가기 (2026-09-19 저녁 KST · s14 「배포 · 판 번호 구멍 막기」)

> 이 파일을 **가장 먼저** 읽는다. 상세는 `docs/session-logs/2026-09-19-s14.md`.

## 지금 상태 — 한눈에

```
veo-platform  main                    판 0.3.628  ← 운영 도달 (삼중 실측 18:40 KST)
              claude/anseo-console-port  4c7e331a (main 과 같은 판 · 미배포 없음)
desktop-tutorial  claude/image-design-workflow-analysis-efuea7
```

**배포 대기 없음.** 이 방이 낸 것: 0.3.624 · 0.3.625 · 0.3.628 (셋 다 실측 확인).

## 🚀 바로 이어갈 작업

사장님이 새 오더를 주시기 전까지 **강제로 이어갈 일은 없다.** 남은 것은 아래 둘.

1. **ANSEO 방에 인계 전달** — 이 방에서 다른 방으로 메시지가 **안 닿는다**(확인됨).
   사장님이 직접 넣으셔야 한다. 붙여 넣을 글은
   `docs/ANSEO-배포-인계-0.3.620.md` (판 번호만 지금 것으로 고칠 것 — 본문 절차는 유효).
2. **도장 가지 둘의 원문** — `same-page-same-verdict` · `compassionate-newton-kyz1sm`.
   내용이 낡아 **일부러 안 냈다**(냈으면 대장이 뒤로 간다). 두 방 원문이 필요하면 따로 판을 잡는다.

## ⚠️ 배포할 때 — 오늘 배운 것 (가장 중요)

**판 번호는 «낼 직전에 main+1»** — 미리 박아 두고 낡은 채로 재시도하지 마라.
(앞 세션에 「손대지 마라」로 적었던 것은 너무 넓었다. 변경이력 항목의 번호는
**내 나무 안에서 유일**해야 해서(`changelog-numbers-are-unique.test.ts`) main 과
같은 번호로 두면 점검에서 선다.) 그리고 `make deploy` 의 `[1/4]` 가
**점검 직후에** 물린다. 손으로 미리 박으면 번호가 점검 전에 굳어 노출 창이
9분 → 24분이 되고, 겹칠 확률이 38% → 71% 로 뛴다.

```
[실측 2026-09-19] main 도착 간격 평균 19.1분 · 이 방은 여섯 번 시도해 다섯 번 물러났다
```

0.3.628 부터는 `version_to_claim` 이 **언제나 main+1** 을 찍는다(미리 박아도 끌어내린다).

**절차**
```
pnpm -r test (packages 건드리면) → cd apps/web && pnpm verify
→ make ci-local  ← 건너뛰지 마라. CI 와 같은 명령이다(verify 와 다르다)
→ VEO_DEPLOY_ORDER="<오더 원문>" make deploy
→ [5/5] 는 이 방에서 늘 「못 쟀습니다」 — 바깥 자리에서 직접 잰다
→ 대장 도장(미배포 없음 + 실측값) → 대기 줄 지움
```

**점검이 도는 중에 나무를 건드리지 마라** — 「커밋 안 된 변경」으로 배포가 선다(오늘 겪음).

**재시도 충돌**은 늘 같은 네 곳이다. 도구가 있다(스크래치패드 `resolve-deploy-merge.py`).
없으면 규칙만 기억: `__init__.py`=이 방 것 · `changelog.ts`=이 방 위/main 아래 둘 다 ·
`openapi.json`=다시 뽑기 · `WORKLIST.md`=이 방 것 · `HISTORY`=양쪽 다.

## 삼중 실측 (이 방은 바깥이 막혀 있다)

Higgsfield `sandbox_exec` 로:
```bash
API=https://veo-platform-production.up.railway.app
curl -fsS "$API/api/health" | jq -r '.data.version'
curl -fsS "$API/api/queue"  | jq -c '.data.worker_versions, .data.stale_workers'
curl -fsS https://veo.seokorea.org/login | grep -oE '0\.3\.[0-9]+' | sort -u | head -1
```

## 대기/차단

- **방 간 메시지 전달 불가** — `SendMessage` 가 클라우드 세션에 안 닿는다. 사장님 경유.
- **DB**: 이 컨테이너는 postgres 를 직접 띄워야 한다(`pg_ctlcluster 16 main start`).
  접속 정보는 `~/.pgpass` 에 둔다 — **명령줄에 비밀번호를 쓰면 막힌다**(정당한 차단).
- 후속 정리(TODO #52): 캡처 계정 삭제 · 조직 이름 확인.

## 주의·제약

- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` + `Claude-Session:`.
  **모델 ID 를 커밋/PR/코드/문서에 넣지 않는다.**
- 사장님께 나가는 글은 「커밋」·「배포」 두 낱말만. 못 잰 값은 «—», 지어내지 않는다.
- **「내보냈다」와 「그 코드가 돈다」는 다른 사실이다.** 도장은 실측 뒤에만.
- 나간 판을 대기 표에 남기지 않는다(감사 A-07·B-07) — 다음 사람이 또 내보낸다.

## 참고
- 판 번호 충돌 전모: `docs/판번호-충돌-방지.md` (구멍 셋·측정·처방 넷)
- 현황은 `PROJECT_STATE.md`, 지도 위치는 `핵심두뇌_MASTER.md`
