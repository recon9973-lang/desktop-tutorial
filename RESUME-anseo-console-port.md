<!-- 가지: claude/image-design-workflow-analysis-efuea7 -->
# RESUME (ANSEO 콘솔 이식 방) — 2026-09-24 확인 · **낸 것은 전부 나갔다**

## 한 줄

정본(Lovable) 화면을 ANSEO 콘솔로 이식하던 방. 그 일은 끝났고, 뒤이어 **배포 기계의
판 번호 문제**를 잡아 처방 넷을 냈다. [실측 2026-09-24 01:11 KST] **이 방이 넣은 것이
전부 main(0.3.652)에 살아 있고 실제로 돌고 있다.** 이 방에 **밀린 일감은 없다.**

## 어디에 무엇이 있나

```
veo-platform      가지 claude/anseo-console-port → **지워졌다**(내용은 main 에 들어갔다)
desktop-tutorial  가지 claude/image-design-workflow-analysis-efuea7  ← 이 방 문서가 여기 있다
```

## ⚠️ 먼저 알 것 — 배포가 ANSEO 방으로 잠겼다 (2026-09-20)

사장님 결정이 이제 **관문**이다 — `scripts/deploy_room_gate.sh`.
사본의 git 설정 `veo.deploy-room = anseo` 가 없으면 **배포가 거부된다**.
`preflight.sh` · `deploy.sh` 둘 다 이 관문을 부른다.

> **표식을 스스로 넣지 마라.** 시험(`test_deploy_refuses_rooms_other_than_anseo.py`)이
> 「넣지 마십시오」를 문구로 고정해 뒀다 — 넣는 것은 우회다.

**이 방은 이제 만들고 검사까지만 한다.** 대장 §2 대기 표에 줄을 쌓고 **ANSEO 방에
인계**한다. 2026-09-19 까지는 이 방이 직접 냈는데, 그 길은 이제 막혔다.

## 이 방이 낸 것 — main 에 살아 있음을 2026-09-24 에 확인

| 무엇 | 어디 | 확인 |
|---|---|---|
| 나가기 직전 main 재확인 | `scripts/deploy.sh` `main_still_holds` | 있음 |
| 판 물림 구멍 막기 | `scripts/deploy.sh` `version_to_claim` | 있음 |
| 배포 기록에 판 남기기 | `scripts/deploy.sh` `MARK_THE_VERSION` | **실물에서 돎** |
| 빠진 기록 세기 | `scripts/audit_deploy_records.py` · `make audit-deploys` | **실물에서 돎** |
| 시험 셋 | `apps/api/tests/release/test_deploy_{rechecks_main_before_pushing,always_claims_from_main,records_are_audited}.py` | 있음 |

**「있다」가 아니라 「일한다」는 증거** — 이후 배포 오더 기록 12줄이 전부 판 번호를
달고 있다(`docs/DEPLOY-ORDER-LOG.md`). 그리고 `make audit-deploys` 가
**기록 빈 판 11개를 전부 0.3.615~0.3.629 로** 짚는다 — 처방이 들어간 **0.3.630 이후로는
빈 것이 하나도 없다.**

화면 이식(0.3.390~0.3.466 무렵)은 훨씬 전에 나갔다. 정본 세 화면 대조도 마쳤다(새 격차 없음).

## 이 방 문서는 main 에 있다 (2026-09-24 사장님 «main에 올려»)

`RESUME-anseo-console-port.md`(이 파일) · `docs/판번호-충돌-방지.md` ·
`docs/배포-인계-현행.md` · `docs/session-logs/2026-09-19-s14.md`.

> **왜 적어 두나.** 새 컨테이너는 **main 내용으로 시작**한다. 가지에만 둔 문서는
> 다음 세션이 못 본다 — 2026-09-24 에 실제로 그랬다(훅이 이 방 인계를 못 찾았다).
> **이 방 문서를 새로 만들면 main 에도 올린다.**

## 바로 이어갈 작업

사장님 오더가 없으면 **강제로 이어갈 일은 없다.** 남은 것:

1. **후속 정리** — 캡처 계정 `capture@anseo.local` 삭제 · 조직 이름이 실제로 「LOOPEO」인지 운영 확인
2. **공유 링크 화면**(`/results/<token>` · `SharedReport.tsx`) 대조 — 대조 3차에서 유일하게 안 훑은 화면

## 판 번호 — 이 방이 하루에 열 번 부딪히고 배운 것

**낼 직전에 main+1 로 맞춘다.** 미리 박아 두고 낡은 채로 재시도하지 않는다.

```
번호 굳음 ─────────────── main 도착    이 사이에 남이 닿으면 내 번호가 낡는다
설계대로:    [1/4] → CI 9분 → main          9분 → 겹칠 확률 38%
미리 박으면:  손 → 점검 15분 → CI 9분      24분 →           71%
[실측 2026-09-19] main 도착 간격 평균 19.1분 · 이 방은 여섯 번 시도해 다섯 번 물러났다
```

- 변경이력 항목 번호는 **내 나무 안에서 유일**해야 한다(`changelog-numbers-are-unique.test.ts`).
  main 을 합치면 main 항목이 들어오므로 이 방 항목은 **main+1** 이어야 한다.
- 대기 줄은 **번호 없이 `—`** 로 쌓고 **자기 가지를 적는다**(`claim_version` 이 그걸로 내 줄을 가른다).
- 물러났다 다시 낼 때는 **그 판이 아직 필요한지부터 본다** — 그 사이 남이 고쳤을 수 있다(실제로 겪음).

전모: `docs/판번호-충돌-방지.md` (구멍 셋 · 측정 · 처방 넷 · 뒤에 배운 것 셋)

## 실측 — 이 방은 바깥이 막혀 있다(egress 403)

배포 `[5/5]` 가 늘 「못 쟀습니다」로 끝난다. **도달 못 한 것이 아니라 재지 못한 것.**
Higgsfield `sandbox_exec` 로 바깥에서 잰다:

```bash
API=https://veo-platform-production.up.railway.app
curl -fsS "$API/api/health" | jq -r '.data.version, .data.uptime_seconds'
curl -fsS "$API/api/queue"  | jq -c '.data.worker_versions, .data.stale_workers'
curl -fsS https://veo.seokorea.org/login | grep -oE '0\.3\.[0-9]+' | sort -u | head -1
```

**한 번 재고 「뒤처졌다」고 적지 않는다.** [실측 2026-09-19] 셋이 달라 보였는데 다시 재니
**롤아웃 한복판**이었다(서버 가동 9,655초 → 재시작 뒤 16초). 값이 어긋나면 **가동 시간을 함께 본다.**

## 이 방이 저지른 것 — 반복 금지

1. `make ci-local` 을 건너뛰고 배포에 들어갔다 — `pnpm verify` 와 **다른 명령**이다.
2. 점검이 도는 중에 나무를 건드렸다 — 파일 하나로 「커밋 안 된 변경」이 되어 배포가 섰다.
3. `cmd > log; echo $?` 로 성공을 보고했다 — 그 종료코드는 **`echo` 것**이다.
4. 원격 추적 ref 가 낡은 것을 보고 「안 올라갔다」고 했다 — `git ls-remote` 로 확인한다.
5. 덮개(fixture) 값을 지어냈다 — **`apps/api/openapi.json` 에서 그대로 옮긴다.**

## 주의·제약

- 커밋 트레일러: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` + `Claude-Session:`.
  **모델 ID 를 커밋/PR/코드/문서에 넣지 않는다.**
- 사장님께 나가는 글은 쉬운 말로. 「커밋」·「배포」 두 낱말만. 못 잰 값은 «—», 지어내지 않는다.
- **「내보냈다」와 「그 코드가 돈다」는 다른 사실이다.** 도장은 실측 뒤에만.
- 나간 판을 대기 표에 남기지 않는다(감사 A-07·B-07) — 다음 사람이 또 내보낸다.
- 방 간 메시지가 안 닿는다(`SendMessage` 거부). 인계는 **사장님 경유**.
- lovable.app 직접 접속 차단 — 커넥터로만. 비밀키 값은 대화에 내지 않는다.

## 참고
- 배포 절차(판 번호 없이 쓴 현행본): `docs/배포-인계-현행.md`
- 현황은 `PROJECT_STATE.md`, 지도는 `핵심두뇌_MASTER.md`
