# ANSEO 콘솔 톤앤매너 전수 감사 — 재작업 인계 (2026-08-30 실측)

> **용도**: 화면 재작업을 진행하는 방(ANSEO 방)에 넘기는 감사 결과. 사장님 오더
> «새 화면과 톤앤매너가 안 맞는 화면은 새 화면으로 작업» 의 대상 목록.
> 실측 기준: veo-platform `main` = `21fd12b`(v0.3.386), apps/web 전 화면 코드 감사.

## 0. 두 방 조율 — 먼저 읽을 것

- **판 번호 겹침 주의**: ANSEO 방에 미배포 세 판 **0.3.387~0.3.389**(AEO 지금 현황
  재구성·곡선)가 있다고 보고됨. 단 **원격 어느 가지에도 그 판은 없다**(2026-08-30
  전 가지 fetch 실측 — `claude/anseo-ui-v3` 원격은 0.3.313에서 멈춰 있음). 그 방
  로컬에만 있는 것으로 보이므로, 새 판 번호는 **0.3.390부터** 잡는 것이 안전.
- main(=`21fd12b`, v0.3.386)까지는 운영 3자리(진단 서버·워커·웹 번들) 모두 0.3.386
  실측 확인(2026-08-30 06:01 KST, 바깥 샌드박스 curl). 사장님이 «업데이트 안 됐다»고
  보신 것은 0.3.387+ 작업분.
- 배포는 사장님 지시대로 **최종 화면 구성이 다 되면 ANSEO 방에서**.

## 1. 새 문법(정본) — 무엇에 맞추나

`components/ScanReport/ScanReport.tsx` L189~215 + 같은 폴더 `.module.css`:

- **등급이 주인공**: `.band` 3rem/bold, 점수는 `.score` font-size-500 muted로 강등, 단위 `.scoreUnit` font-size-200.
- **등급 톤**: `bandToneClass(min)` — ≥90 `bandPass` / 75~89 기본 / ≥60 `bandWarn` / 미만 `bandFail`. **항상 글자와 병용**(색으로만 말하지 않는다).
- 목표선: `SCORE_GOALS`(취약 탈출 50 warning · 관리 목표 90 pass) + `goalEta` 도달 예상(«관측값·보장 아님» 단서).
- 백분율은 분자/분모 병기.
- **현재 이 정본의 소비처는 `seo/page.tsx:487` 단 한 곳뿐** — 나머지가 전부 옛 문법이다.

## 2. VIOLATES — 재작업 대상 8곳 (우선순위순)

| 순위 | 파일 | 줄 | 현재 상태 | 비고 |
|---|---|---|---|---|
| **1** | `app/(public)/tools/checker/PublicChecker.tsx` | 336~352 | 점수 38px/900 지배, 등급 칩 11px. **칩 색이 `--veo-status-fail-*` 하드코딩 — 95점 A등급도 실패색** | `(public)/results/[token]/SharedReport.tsx:33`이 재사용 → **공개 공유 링크+PDF 인쇄본까지 같은 문법**. 단독으로도 버그급 |
| **2** | `console/geo/ReadinessReport.tsx` | 82~86 | `.rateValue` font-size-600 bold 점수 vs 분모 font-size-200, 톤 없음 | GEO 정본 자리인데 새 문법의 정확한 역상. `bandToneClass` 공용화로 즉시 해결 |
| **3** | `console/reports/[reportId]/[version]/ReportBody.tsx` | 186~253 | `HeroValue` 3.4rem mono 점수, **등급을 어디에도 안 그림** | 업체 전달 발행본. 서버가 밴드를 주는지 확인 필요. ※ L379~419의 `notation_version`/`STACK_BAND`는 **이슈 심각도 축**이지 점수 등급이 아님 — 착각 주의 |
| **4** | `console/seo/page.tsx` | 1150~1157 | 레일 게이지 점수 22px vs 등급 11px muted | 같은 화면 위쪽은 정본(ScanReport) — **한 화면 두 문법** |
| 5 | `console/dashboard/ClientRail.tsx` | 98~99 | 점수 28px bold + «점», 등급 라벨 자체가 없음 | |
| 6 | `console/dashboard/Scales.tsx` | 53~64 | conic 게이지 점수, 등급 없음 (분모는 있음 ✓) | |
| 7 | `console/customers/page.tsx` | 446·500 | `.score`·`.tickerScore` + ▲▼, 등급 없음 | |
| 8 | `console/customers/[customerId]/page.tsx` | 1306~1326 | 진단 탭 머리 `PairHead`·`.pairPlain b` 점수만 | |

**5~8 공통 선결 과제**: 목록·칩·게이지 같은 작은 자리는 3rem 규칙을 그대로 못 쓴다 —
**축소판 문법**(등급 칩 우선 + 점수 보조 + 톤 병용)을 하나 정의해 일괄 적용할 것.

## 3. TrendChart 목표선 전수

| 호출부 | goalLines | 판정 |
|---|---|---|
| `seo/page.tsx:1185` · `customers/[customerId]/page.tsx:1819` | ✓ SCORE_GOALS+bridgeBreaks | 완료 |
| `geo/VisibilityTrend.tsx:60` · `geo/MonthlyVisibilityTrend.tsx:38` | ✗ | 값이 노출률(%)이라 50/90은 부적합 — **별도 목표선 필요 여부는 사장님 판단** |
| `keywords/KeywordReport.tsx:201` | ✗ | 상대 관심도(0~100) — N/A |

## 4. 손대지 말 것 (다른 축 — 점수 등급 아님)

- `review/ReviewCard.tsx:71` · `geo/RiskReport.tsx:62` · `dashboard/page.tsx:956` — **의료광고 위험 등급**
- `issues/` 전반 · `customers/[customerId]/page.tsx:1201` «등급 구성» — **이슈 심각도**
- `geo/MentionRoster.tsx` · `geo/CitationChannels.tsx` · `competitors/ComparisonList.tsx` — 분모 병기 이미 준수

## 5. 규율 리마인더 (재작업 방에서)

- 한 판 = 한 확정, changelog.ts 맨 앞=APP_VERSION, api `__version__`·계약 동기화, WORKLIST §2+HISTORY 등재.
- 관문: readable-on-its-background(칩 색 고칠 때), no-duplicate-charts 감시 리터럴, console-boxes 대장, say-why(«사장님 지시» 어휘), two-words-only.
- formatScore만 · 못 잰 값 — · 색+글자 병용 · 등급은 서버 밴드에서(하드코딩 금지).
