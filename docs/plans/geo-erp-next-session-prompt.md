# 다음 세션 이어가기 프롬프트 (GEO → ERP 병합 후속)

> 아래 코드블록을 다음 세션 첫 메시지로 그대로 붙여넣으면 맥락이 복원된다.
> 최종 갱신 2026-07-16 (코어 M1~M6 + UI 후속 전부 머지 완료) · 직전 세션 https://claude.ai/code/session_01WmD9W9g7GEVaM7TVh1xm7B

```
[이어서 작업] VENOM GEO-OS → ERP 병합 후속.

## 지금까지(완료분)
- desktop-tutorial GEO 운영 OS 파일럿 구축·배포(venom-new-site.vercel.app/geo-ops.html).
- 통합 설계서 v2 작성(ERP 실사로 v1 그린필드 전제오류 정정).
- ERP(recon9973-lang/marketing-agency-erp, base=erp-v1)에 코어 M1~M6 + UI 후속 3종
  = 총 9개 PR 전부 squash-merge 완료. 스키마 변경 0, 오프라인 95케이스, 전 PR Vercel green.
  코어: M1 SOV #42 / M2 cap-clamp #43 / M3 주간리포트 #44 / M4 반복업무 #45 /
        M5 온보딩체크리스트 #46 / M6 NAS이관골격 #47.
  UI(§7): SOV 차트 #48(SovChart) / Phase 진행률 탭 #49(ClientOnboardingProgress) /
          주간 리포트 UI #50(reports/geo-weekly).
  ※ M2#43↔M5#46이 OnboardingTaskTemplate 타입에 필드 추가 → phase·automationLevel·channel
    세 필드 모두 유지로 병합 해소됨(이미 처리, 재발 없음).
- 문서(desktop-tutorial docs/plans/): geo-erp-integration-design-v2.md(설계),
  geo-erp-integration-delivery.md(전체 기록·부록 A NAS가이드·부록 B 연대기),
  geo-ops-session-summary.md §8·§9(러닝 요약/TODO), 이 프롬프트.

## 이번 세션에 할 것(미완/지연 오더)
1) [M6 실행 — 최우선, 팀 자료 대기] scripts/migrate-nas-to-erp.ts는 골격만 있고 상단
   NAS_SCHEMA가 설계 §5 기준 "추정" 컬럼명이다. 실제 NAS SQLite 스키마가 있어야 확정 가능.
   - 사용자에게 NAS 백업본의 `.schema` 출력을 먼저 요청할 것(없으면 진행 불가).
     안전 백업: sqlite3 /volume1/docker/<앱>/team.db ".backup '/volume1/team-backup.db'"
     스키마 확인: sqlite3 team-backup.db ".schema"
   - `.schema`를 받으면: NAS_SCHEMA 테이블/컬럼명 확정 → 매핑 조정 → staff-map.json 양식 안내
     → dry-run(--commit 없이 건수 확인) → 사용자 승인 후 --commit.
   - NAS 접근은 상시연결 불필요(파일 1개만). LAN/온라인 무관, File Station 다운로드가 가장 간단.
2) [파일럿 종료 수순] 병합 완료로 desktop-tutorial GEO-OS는 파일럿 종료 대상(설계 §6).
   팀이 GitHub Secret ADMIN_SECRET로 잠깐 더 돌릴지 즉시 종료할지 결정 → 사용자에게 확인.
3) [중장기 2차·3차, 지시 있을 때만] 콘텐츠 초안 자동생성(B 승인큐)·Slack 승인·고객 포털·
   PDF 발송 / 서버측 RBAC·요금제·화이트라벨·업종 벤치마크.
4) [운영 심화, 선택] 거래처 competitors 등록 → SOV 실측 노출 · 프롬프트셋 콘솔 편집 UI.

## 반드시 지킬 규칙
- 개발 브랜치: desktop-tutorial = claude/production-ready-planning-mpkir0. ERP 신규작업은 feat/geo-* 브랜치.
- 커밋 트레일러 필수:
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: <이번 세션 URL>
- 커밋/PR/코드에 모델 ID 넣지 않는다. 통계·인용 지어내지 않는다(상대지표 SOV·delta만).
- 판정 로직은 순수 함수로 분리 → 오프라인 하니스로 검증(ERP node_modules 미설치, tsc/vitest/build는 Vercel CI).
- PR·머지는 사용자 승인 후. 의료광고법 준수(전후사진·효과보장·최상급 배제, 미보장 고지).
- ⚠️ 새 작업 착수 전 반드시 원격 브랜치/PR을 먼저 확인할 것 — 이 세션에서 UI 후속을
  중복 착수했다가 이미 병렬 PR(#48~#50)이 있어 폐기한 이력 있음. git ls-remote --heads
  origin 'refs/heads/feat/geo-*' + list_pull_requests(open)로 중복 방지.

먼저 M6 진행을 위해 NAS 백업본의 `.schema` 출력을 요청하고, 없으면 파일럿 종료 방향을 물어봐줘.
```

---

## 부록 A — 저장소·환경 빠른 참조
| 항목 | 값 |
|---|---|
| ERP 저장소 | `recon9973-lang/marketing-agency-erp` (Next.js 15 · Prisma 6 · Neon · pnpm), base `erp-v1` |
| desktop-tutorial | Vercel 배포 venom-new-site.vercel.app, 브랜치 `claude/production-ready-planning-mpkir0` |
| ERP 작업 경로(직전 세션) | `/workspace/marketing-agency-erp` |
| GitHub 접근 | `mcp__github__*` 툴 사용(gh CLI 없음). 머지=squash. |

## 부록 B — 병합된 PR·산출물 (erp-v1)
- 코어: `server/geo-engine/sov.ts` · `server/marketing/geo-weekly.ts` · `server/work/recurrence.ts` · `server/jobs/work-recur.ts` · `scripts/migrate-nas-to-erp.ts` (+각 test)
- UI: `components/geo/SovChart.tsx` · `components/clients/ClientOnboardingProgress.tsx` · `components/reports/GeoWeeklyReport.tsx` · `app/(erp)/reports/geo-weekly/page.tsx` · `server/marketing/week-window.ts` (+각 test)
- 수정: `repositories/geo.ts` · `app/(erp)/geo/page.tsx` · `domain/sales/geo-channels.ts` · `domain/sales/onboarding-tasks.ts` · `app/api/marketing/cron/route.ts` · `components/clients/ClientDetail.tsx` · `app/(erp)/reports/page.tsx`

## 부록 C — 검증 케이스(오프라인)
코어 M1 6·M2 7·M3 8·M4 10·M5 8·M6 13 = 52 / UI #48 13·#49 11·#50 19 = 43 → **총 95/95 통과**

## 부록 D — M6 실행 체크리스트(재확인용)
1. NAS `.backup`으로 team.db 스냅샷(앱 쓰는 중 원본 직접 복사 금지).
2. `.schema`로 실제 테이블/컬럼명 확인 → 스크립트 상단 NAS_SCHEMA 확정.
3. staff-map.json: `{ "staffIdMap": {"<nasStaffId>":"<erpUserId>"}, "fallbackUserId": "<erpUserId>", "encryptCredentials": false }`
4. dry-run: `tsx scripts/migrate-nas-to-erp.ts --db ./team-backup.db --staff-map ./staff-map.json`
5. 검토 후 반영: 위 명령에 `--commit` 추가.
6. 매핑: clients→Client / accounts→ClientAccount(평문 미이관·credentialHint) / checklist_progress→WorkItem(done→COMPLETED) / memos→Comment(CLIENT) / staff→User(선매핑).
