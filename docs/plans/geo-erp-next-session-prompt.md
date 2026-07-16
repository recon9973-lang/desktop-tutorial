# 다음 세션 이어가기 프롬프트 (GEO → ERP 병합 후속)

> 아래 코드블록을 다음 세션 첫 메시지로 그대로 붙여넣으면 맥락이 복원된다.
> 작성 2026-07-16 · 직전 세션 https://claude.ai/code/session_01WmD9W9g7GEVaM7TVh1xm7B

```
[이어서 작업] VENOM GEO-OS → ERP 병합 후속.

## 지금까지(직전 세션 완료분)
- desktop-tutorial GEO 운영 OS 파일럿 구축·배포 완료(venom-new-site.vercel.app/geo-ops.html).
- GEO→ERP 통합 설계서 v2 작성(ERP 실사로 v1 전제오류 정정).
- ERP(recon9973-lang/marketing-agency-erp, base=erp-v1)에 M1~M6 이식 완료 — 전부 open PR(자동 머지 안 함), 스키마 변경 0, 오프라인 52케이스 통과.
  M1 SOV #42(feat/geo-sov) / M2 cap-clamp #43(feat/geo-capclamp) / M3 주간리포트 #44(feat/geo-weekly) /
  M4 반복업무 #45(feat/geo-recur, Vercel 배포 green) / M5 온보딩체크리스트 #46(feat/geo-onboarding-checklist) /
  M6 NAS이관골격 #47(feat/geo-nas-migration).
- 문서: docs/plans/geo-erp-integration-design-v2.md(설계), geo-erp-integration-delivery.md(인도), geo-ops-session-summary.md §8·§9(TODO).

## 이번 세션에 할 것(우선순위 순 — 미완/지연 대기 오더)
1) [머지] ERP PR #42~#47을 base erp-v1로 순차 머지. 각 PR Vercel CI green 확인 후.
   ⚠️ M2(#43)와 M5(#46)가 같은 OnboardingTaskTemplate 타입에 optional 필드 추가(M2: automationLevel?/channel?, M5: phase?)
   → M2 먼저 머지, 충돌 시 양쪽 필드 모두 유지. 권장 순서 #42→#43→#44→#45→#46→#47.
2) [M6 실행 준비] scripts/migrate-nas-to-erp.ts의 상단 NAS_SCHEMA는 설계 §5 기준 추정치.
   실제 NAS SQLite 스키마(sqlite3 team.db ".schema")를 받아 테이블/컬럼명 확정 → staff-map.json 작성 → dry-run → --commit.
   (실물 DB/스키마가 없으면 나에게 스키마를 붙여달라고 먼저 요청할 것.)
3) [UI 후속, 설계 §7] 택1 이상:
   - SOV 차트: components/geo에 SovChart(M1 computeGeoSov 데이터) + GeoMatrix/KPI에 경쟁사 분해.
   - ClientDetail Phase 진행률 탭: M5 onboardingPhaseSummary 기반 진행률 UI(WorkItem 집계).
   - reports 페이지에 geo-weekly 타입: M3 assembleGeoWeekly 결과 렌더.
   - 스타일: ERP 토큰(테라코타 #d9662e + GEO emerald) 준수, 신규 디자인 토큰 금지.
4) [파일럿 자동화, 팀 의존] desktop-tutorial GitHub 저장소 Secret ADMIN_SECRET(=Vercel 값) 등록 시
   리포트·GSC수집·반복업무 워크플로 인증 해제. 병합 완료 후 desktop-tutorial GEO-OS는 파일럿 종료(설계 §6).
5) [중장기 2차·3차] 콘텐츠 초안 자동생성(B 승인큐)·Slack 승인·고객 포털·PDF 발송 / 서버 RBAC·요금제·화이트라벨·업종 벤치마크.

## 반드시 지킬 규칙
- 개발 브랜치: desktop-tutorial = claude/production-ready-planning-mpkir0. ERP 신규 작업은 feat/geo-* 브랜치.
- 커밋 트레일러 필수:
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: <이번 세션 URL>
- 커밋/PR/코드에 모델 ID 넣지 않는다. 통계·인용 지어내지 않는다(상대지표 SOV·delta만).
- 판정 로직은 순수 함수로 분리 → 오프라인 하니스로 검증(ERP node_modules 미설치, tsc/vitest/build는 Vercel CI).
- PR은 사용자가 명시적으로 요청할 때만 생성. 머지도 승인 후. 의료광고법 준수(전후사진·효과보장·최상급 배제).

먼저 ERP PR #42~#47의 현재 CI 상태를 확인하고, 머지부터 진행할지 UI 후속부터 할지 물어봐줘.
```

---

## 부록 A — 저장소·환경 빠른 참조
| 항목 | 값 |
|---|---|
| ERP 저장소 | `recon9973-lang/marketing-agency-erp` (Next.js 15 · Prisma 6 · Neon · pnpm), base `erp-v1` |
| desktop-tutorial | Vercel 배포 venom-new-site.vercel.app, 브랜치 `claude/production-ready-planning-mpkir0` |
| ERP 작업 경로(직전 세션) | `/workspace/marketing-agency-erp` |
| GitHub 접근 | `mcp__github__*` 툴 사용(gh CLI 없음) |

## 부록 B — ERP 파일 인벤토리(M1~M6)
- 신규: `server/geo-engine/sov.ts`(+test) · `server/marketing/geo-weekly.ts`(+test) · `server/work/recurrence.ts`(+test) · `server/jobs/work-recur.ts` · `scripts/migrate-nas-to-erp.ts`(+test)
- 수정: `server/repositories/geo.ts` · `app/(erp)/geo/page.tsx` · `domain/sales/geo-channels.ts` · `domain/sales/onboarding-tasks.ts` · `app/api/marketing/cron/route.ts`

## 부록 C — 검증 케이스 수(오프라인)
M1 6 · M2 7 · M3 8 · M4 10 · M5 8 · M6 13 = **52/52 통과**
