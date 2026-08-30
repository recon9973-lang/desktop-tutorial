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

## 6. 사장님 지시 (2026-08-30) — 라벨 교체 오더

- **대시보드의 «AEO 깨어남 — 거래처별 단계» 라벨을 교체하라.** «깨어남»은 사장님 어휘가
  아님(사장님 지시 2026-08-30 «깨어남은 내 말 아니야, 대안으로 바꾸라고 전달해줘»).
  대안 예: **«AEO 진행 단계 — 거래처별»** 또는 «AEO 시작 단계». 단계명 자체(내부 코드의
  awakening 계열 명칭)가 다른 화면·문서에도 새어 있는지 함께 전수 확인할 것.
- 같은 기준(«사장님이 물어봐야 하는 라벨 = 나쁜 라벨»)으로 이 방 시뮬은 2026-08-30
  전수 정리 완료: 질문셋→질문 집합 · 신원 관문→신원 등록 · 브랜드 신원 잇기→브랜드 정보 ·
  실행 체인→실행 흐름 · 공개면→공개 화면. 실물에 같은 계열 어휘가 있으면 함께 맞출 것.

## 7. 실물 라벨 전수 감사 (2026-08-30 · v0.3.389 실측) — 교체 후보 41건

> 기준: «사장님이 물어봐야 하는 라벨 = 나쁜 라벨». 승인 어휘(판·진단·재진단·관측·명세·발행·
> 검수·질문 집합 등)는 제외. 아래는 사용자 눈에 실제로 보이는 문자열만 — 주석·테스트·
> changelog 내 어휘는 전수 확인 결과 노출 0건(§7-라 참조).

### 7-가. 최우선 5건

1. `(public)/tools/checker/PublicChecker.tsx:414` **«· 관문»** 배지 — 공개 체커+공유 링크 노출.
   → «· 막히면 0점» 또는 «· 통과 필수»
2. `reports/[reportId]/[version]/ReportBody.tsx:437` **TAG/CONTENT/LINK/CONFIG** 원시 영문 enum이
   경영진 뷰까지 배지로 노출(한국어 매핑 부재) → 태그/본문/링크/설정
3. `dashboard/page.tsx:864` **«AEO 깨어남 — 거래처별 단계»** → «AEO 진행 단계 — 거래처별» (§6 확정 건)
4. `customers/[customerId]/MedicalFactsCard.tsx` **«C1» 규칙 코드 3곳(75·274·461) + «엔티티» 3곳(85·102·392)**
   → C1 삭제·«근거 없어 제외» / 엔티티→대상, 속성→항목 (CounterfactualCard.tsx:762 «엔티티»도 동일)
5. **«해시/체크섬» 8곳** — ReportBody 120·871·874, reports/[id]/page 72, reports/page 146,
   ScanReport 536·547, issues/[id]/page 131·161 → `CapturesSection.tsx:100`이 이미 쓰는 **«내용 지문»**으로 일괄 통일

### 7-나. 콘솔 화면 (매일 노출)

- «작업 큐» → «할 일 목록»: WorkQueue.tsx:138(h2)·ReportBody 465·468·742·759
- «관문» 잔여: WorkQueue.tsx:148 «(관문)» 괄호 삭제(ScanReport 336은 이미 괄호 없음) ·
  PagesSection.tsx:297«확인 못 한 차단 항목»·305 «· 통과 필수» ·
  customers/[id]/page.tsx:1624 «⚠ 관문 실측» → «⚠ 막힌 곳» ·
  scoring-versions/page.tsx 86·166·169·204 «관문» → «차단 검사»로 통일
- `lib/aeo-stage.ts:16` «집합 없음» → «질문 없음» (승인 어휘 «질문 집합»과 정합)
- keywords/page.tsx 342·353 «ERP» → «베놈 업무시스템»
- customers/projects/page.tsx:73 slug 원문 노출 → 숨기거나 라벨 부여
- HiraImport.tsx:302 «매핑에 없는 열» → «우리가 모르는 항목»
- CapturesSection.tsx 102·103 «보낸/받은 헤더» → «보낸 요청 정보 / 사이트가 보낸 응답 정보»
- ManualRunForm.tsx:265·CounterfactualCard.tsx:96 «잰 토큰» → «잰 사용량»
- PublicChecker.tsx 526 «SERP» 배지 삭제 · 540 «OG» → «공유 카드»

### 7-다. 설정 화면 (노출 낮음 — 후순위)

- usage: «토큰 사용량»(TokenUsageSection 59·67·91, usage/page 228·232·294·314) → «AI 처리량»·«보낸/받은 글자량»
- credentials/page.tsx 72·120 «환경변수» → «서버 설정(개발팀 문의)»

### 7-라. 깨끗함 증명 (전수 0건 계열 — 재수색 불요)

사슬·파이프라인·레일·드릴·스냅샷·카나리·훅·워커·버킷·플래그·스택·질문셋(화면은 전부
«질문 집합»)·WORKLIST/ADR 번호·fallback/cron/endpoint/webhook/payload·캐시/폴백/파싱/스키마 —
JSX 텍스트·라벨·aria·툴팁 노출 0건(주석·테스트·changelog에만 존재).
