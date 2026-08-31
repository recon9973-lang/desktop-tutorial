# RESUME — 다음 세션 이어가기 (2026-09-01 새벽 KST · s11 「디자인 그대로」 이식)

> 이 파일을 **가장 먼저** 읽는다. 상세는 `docs/session-logs/2026-09-01-s11.md`.

## 지금 상태 — 한눈에

```
veo-platform  main              fa2ffa9   판 0.3.446  ← 운영 도달 (삼중 실측 00:17 KST)
              deploy-candidate  278adc4   판 0.3.448  ← CI 진행 중이었다. 결과부터 확인
              작업 가지          claude/anseo-console-port (= 278adc4)
desktop-tutorial                claude/image-design-workflow-analysis-efuea7
```

**사장님 배포 승인 받았다(2026-09-01).** 0.3.447·0.3.448 이 나갈 차례다.

## 🚀 바로 이어갈 작업

1. **배포 마감.** CI run `33421381533`(sha `278adc4`) 결과 확인 →
   초록이면 `git push origin 278adc4a1989212054afae44bc3e0abf80ea4247:main` →
   6~7분 → Higgsfield `sandbox_exec` 로 삼중 실측(서버 `/api/health` · 워커
   `/api/queue` · 웹 `veo.seokorea.org/login`) → WORKLIST §2·대기 표·HISTORY 도장.
   **사장님께 결과를 알려 드린다** — 「검사 통과하면 바로 배포하고 결과 알려줘」.
2. **AEO 「우리 대 타사」 판** — 정본 `src/components/anseo/aeo-share.tsx` 의
   `MentionShareBoard` 를 거래처 상세 AEO 탭에. 질문 필터 칩 → 3칸 히어로
   (언급률·순위·대상 질문) → 순위 막대 + 회차별 다중 추이선 → 질문별 칸 수 표.
   **데이터는 이미 있다**(MentionRoster·MentionTrend·EngineModeMentions·
   RivalFindings) — 서버 확장 불필요.
3. **나머지 열일곱 화면 대조** — 리포트·검수·GEO·거래처 상세 나머지 탭 순.
4. 정본에 있는데 실물에 없는 화면 하나 — **사이트맵·파이프라인**(`/console/sitemap`).

## 이 방이 저지른 잘못 — 같은 실수 반복 금지

1. 「캡처 대조」라 말하며 **한 장도 안 찍었다** → 이제 `shoot.mjs` 로만 화면을 말한다.
2. 정본 판이 바뀐 걸 못 봤다 → 판독 전 **`get_project` 로 `latest_commit_sha` 확인**.
3. 사장님께 **이 방이 다시 그린 그림**을 보여 드렸고 문구를 바꿨다 → 실물 PNG 만 낸다.
4. 「격차」를 **세 번** 잘못 보고 → 빈 표본으로 접힌 화면을 「기능 없음」으로 읽었다.
5. 정산 누락 **두 번** → 판 올릴 때 창구 문서 재생성 · 토큰 고칠 때 `pnpm -r test`.
6. 오더 중 **옆길로 샜다**(대시보드 → 검사 화면).

## 일하는 법 (이 순서 고정)

```
① 서버 창구에 값이 있나 (apps/api/openapi.json · 154개)   ← 없을 때만 서버 판
② 값을 그리는 화면이 있나 (소스)
③ 표본 채워 찍어서 눈으로 (shoot.mjs)                     ← 여기서만 «다르다»
```
**찍기 전에는 «없다»고 말하지 않는다.**

## 도구 (이 세션이 만든 것)

```bash
# 화면 찍기 (표본 덮개·클릭 후·서버 로그까지)
cd apps/web && PATH=/opt/node22/bin:$PATH PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
  SHOOT_FIXTURE=<덮개.json> SHOOT_CLICK='2 · 구조' \
  node test/smoke/shoot.mjs <출력폴더> /console/dashboard
# 덮개 예시: apps/web/test/smoke/fixtures-dashboard.sample.json
```
- 관문: `apps/web/src/app/styles-are-not-undefined.test.ts` (부르는 CSS 클래스 실재)
- 지도: `docs/ANSEO-데이터-유무-조사.md` (화면별 서버값 유무 — 서버 확장 필요 0건)
- 격차표: `docs/ANSEO-화면구성-격차표-v2.md` (V1~V12 전량 소화됨)

## 사장님 확정 (되묻지 말 것)

- **디자인은 정본 그대로. 기능은 양쪽 다 살려 작동하게.** 확인 없이 바꾸지 않는다.
- 작업 흐름 각주의 단계 번호는 **실제로 막힌 단계**로(정본은 「1단계에」 고정).
- 검사 목록의 영역별 접힘은 **지금대로 유지**(08-19 결정 그대로).
- 사장님께 나가는 글은 「커밋」·「배포」 두 낱말만. 못 잰 값은 —, 지어내지 않는다.

## 주의·제약

- 커밋 트레일러: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` +
  `Claude-Session: <자기 세션 URL>`. 모델 ID 를 커밋/PR/코드/문서에 넣지 않는다.
- 배포 사이클: `pnpm -r test` → `pnpm verify`(web) → deploy-candidate 푸시 →
  CI 초록 → main ff → 6~7분 → 삼중 실측 → 도장. **CI 도는 중 재푸시 금지.**
- 판 올릴 때: changelog prepend → `__version__` → **openapi.json 판 문자열** →
  WORKLIST §2·대기 표 → HISTORY → DEPLOY-ORDER-LOG.
- 정본 프리뷰는 **브라우저로 못 연다**(실행 환경 권한 차단). 커넥터 소스 판독만.
  캡처 계정 capture@anseo.local 존치(비밀번호 미설정 · 삭제는 후속).
- /console/geo AEO 독립 화면·의료 규정은 다른 방 소관.
