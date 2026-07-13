# VENOM MarketerOps — Phase 1 상세 설계 (감시와 자동원고)

> 상위 기획: [`PLAN-marketer-workflow.md`](PLAN-marketer-workflow.md)
> 범위: **M1 거래처 특이사항 노트 · M2 노출 트래커+월보장 알림 · M3 원고 프리셋 자동생성**
> 구현 타깃: `marketing-agency-erp`(브랜치 `erp-v1`, Next.js + Prisma + Neon)
> 작성일: 2026-07-13 · 우선순위: Must · 예상 기간 2~3주

이 문서는 후속 세션이 **바로 코딩에 착수**할 수 있도록, 데이터모델(Prisma)·API 계약·스케줄러 로직·화면 스펙을 확정한다.

---

## 0. Phase 1을 먼저 하는 이유

담당자가 가장 아프다고 명시한 3가지 — **월보장 순위하락을 뒤늦게 앎(P3)**, **원고 수작업(P1)**, **인수인계 유실(P9)** — 을 해결한다. 셋 다 기존 ERP 자산 재사용 비중이 높아 2~3주 내 체감 가능하다.

---

## 1. 데이터 모델 (Prisma) — 기존 `Client`에 최소 확장

```prisma
// ── 기존 Client 모델에 관계만 추가 (필드 파괴 없음) ──
model Client {
  id            String   @id @default(cuid())
  name          String
  // ... 기존 필드 유지 ...
  placeId       String?          // 네이버 플레이스 ID (노출 조회용)
  depts         String[]         // 진료과 태그
  keywords      Keyword[]
  handoffNotes  HandoffNote[]
  promptPresets PromptPreset[]
  channels      Json?            // { naverBrand, naverDist, tistory, insta } 계정 메타(비밀X)
}

// ── M2: 키워드 & 노출 ──
model Keyword {
  id           String             @id @default(cuid())
  clientId     String
  client       Client             @relation(fields: [clientId], references: [id], onDelete: Cascade)
  text         String
  dept         String?            // 진료과/카테고리
  searchVolume Int?               // insights.js(네이버 키워드도구)로 자동 채움
  isGuaranteed Boolean            @default(false)  // 월보장 여부
  targetRank   Int?               // 월보장 목표 순위(예: 상단통합 1위 → 1)
  targetArea   ExposureArea?      // 어느 영역을 보장하는지
  active       Boolean            @default(true)
  snapshots    ExposureSnapshot[]
  createdAt    DateTime           @default(now())

  @@index([clientId, isGuaranteed])
}

enum ExposureArea {
  PLACE          // 플레이스
  TOP_UNIFIED    // 상단통합
  CLIP           // 클립
  BRAND_CONTENT  // 브랜드콘텐츠
  HOT_POST       // 인기글
  BOTTOM_UNIFIED // 하단통합
  IMAGE          // 이미지
  POWER_PLACE    // 파워플레이스
  POWER_LINK     // 파워링크
}

model ExposureSnapshot {
  id         String       @id @default(cuid())
  keywordId  String
  keyword    Keyword      @relation(fields: [keywordId], references: [id], onDelete: Cascade)
  capturedAt DateTime     @default(now())
  area       ExposureArea
  rank       Int?         // 해당 영역 노출 순위. null = 미노출
  detail     String?      // 예: "달서2", "베놈 블로그"
  source     String       // "manual" | "datalab" | "search-console" | "serp"

  @@index([keywordId, area, capturedAt])
}

// ── M2: 알림 ──
model Alert {
  id        String     @id @default(cuid())
  type      AlertType
  level     AlertLevel @default(WARN)
  clientId  String?
  keywordId String?
  title     String
  body      String
  area      ExposureArea?
  fromRank  Int?
  toRank    Int?       // null = 미노출로 이탈
  sentTo    String[]   // 담당자/대표 식별자
  channel   String     @default("kakao")   // kakao | inapp
  status    AlertStatus @default(OPEN)     // OPEN | ACK | RESOLVED
  createdAt DateTime   @default(now())

  @@index([status, createdAt])
}

enum AlertType  { RANK_DROP  DEADLINE  UNEXPOSED }
enum AlertLevel { INFO  WARN  CRIT }
enum AlertStatus { OPEN  ACK  RESOLVED }

// ── M1: 인수인계 특이사항 ──
model HandoffNote {
  id       String   @id @default(cuid())
  clientId String
  client   Client   @relation(fields: [clientId], references: [id], onDelete: Cascade)
  author   String
  body     String
  pinned   Boolean  @default(false)
  tag      String?  // 계약/주의/원장성향/의료광고 등
  createdAt DateTime @default(now())

  @@index([clientId, pinned, createdAt])
}

// ── M3: 원고 프롬프트 프리셋 ──
model PromptPreset {
  id        String     @id @default(cuid())
  clientId  String
  client    Client     @relation(fields: [clientId], references: [id], onDelete: Cascade)
  type      PresetType
  roleSetup String     // "너는 OO치과 서영석 원장이야 ..."
  rules     String[]   // 13필수규칙 등
  slots     Json       // { keyword, hospital, detail } 기본값/설명
  updatedAt DateTime   @updatedAt
}

enum PresetType { BRAND  INFO  RECEIPT }  // 브랜드블로그 / 정보성 배포 / 영수증
```

> Neon 반영: `prisma db push`(핵심두뇌 배포규칙). 기존 필드는 건드리지 않고 관계/모델만 추가 → 무중단.

---

## 2. API 계약 (Vercel 함수 12개 한도 → `?type=` 라우팅으로 통합)

기존 `insights`/`seo-proxy` 패턴을 따라 **엔드포인트 3개**로 묶는다.

### 2.1 `POST /api/marketer?type=exposure` — 노출 스냅샷 기록/조회
```jsonc
// 기록(수동 or 스케줄러)
{ "action":"snapshot", "keywordId":"...", "entries":[
  { "area":"TOP_UNIFIED", "rank":1, "detail":"베놈 블로그", "source":"manual" },
  { "area":"PLACE", "rank":null, "detail":"미노출", "source":"serp" }
]}
// 조회
{ "action":"list", "clientId":"...", "range":"30d" }
// → 키워드 × 영역 매트릭스 + 추세
```

### 2.2 `GET /api/marketer?type=guard-scan` — 월보장 감시 (크론)
- Vercel Cron 일 1회(KST 08:00) 호출. `isGuaranteed=true` 키워드 전수.
- 각 키워드의 `targetArea` 순위를 **공식 소스만**으로 조회: 네이버 데이터랩 관심도 급락 + Search Console 순위 + (가능 시 플레이스 API). SERP 스크래핑은 하지 않음(리스크).
- 판정 로직:
```
최신순위 = snapshot(area=targetArea).rank
if 최신순위 == null:                 level=CRIT  type=UNEXPOSED   // 이탈
elif 최신순위 > targetRank:          level=WARN  type=RANK_DROP
elif 최신순위 > 직전순위 + 3:        level=INFO  type=RANK_DROP   // 하락 조짐
→ Alert 생성 + Make 웹훅 → 카카오 알림톡(담당자+대표)
```
- 중복 억제: 동일 키워드·동일 level 24h 내 재알림 금지(디바운스).

### 2.3 `POST /api/marketer?type=manuscript` — 프리셋 원고 생성
```jsonc
{ "presetId":"...", "slots":{ "keyword":"수성구 도수치료",
  "hospital":"OO정형외과", "detail":"교통사고 후 재활 프로그램" } }
// 서버: roleSetup + rules + slots 합성 → post-generator(OpenAI)
//   → medical-ad-validator(의료광고법) → content-validator(정리)
// 응답:
{ "body":"...(2500자, 핵심요약+목차6+FAQ)...",
  "medicalAdPass":true, "violations":[],
  "similarityRisk":"low", "outline":["...","..."],
  "snippets": { "naverFormatted":"<서식 적용 HTML>" } }  // P5 발행 서식
```

---

## 3. 화면 스펙 (Next.js App Router)

### 3.1 거래처 워크스페이스 `/(erp)/clients/[id]` — M1
- 헤더: 병원명·진료과·플레이스·담당자. 탭: **개요 / 키워드·노출 / 원고 / 특이사항**.
- **특이사항 탭**: 상단 고정(pinned) + 시간순 노트. 각 노트에 작성자·날짜·태그. "담당 교체" 버튼 → 승계(소유자만 변경, 노트 보존).
- 캘린더/작업카드 **호버 요약**(P8)에 이 거래처의 pinned 노트 1줄을 노출.

### 3.2 노출 트래커 `/(erp)/clients/[id]?tab=exposure` — M2
- **매트릭스 그리드**: 행=키워드, 열=9개 영역. 셀=순위 배지(1~3 초록 / 4~10 노랑 / 미노출 회색). 월보장 키워드는 좌측 🔒 + 목표순위 표시.
- 셀 클릭 → 추세 스파크라인(최근 30일 스냅샷). 상단 "검색량 새로고침"(insights).
- **경보 배너**: OPEN Alert를 상단에 CRIT>WARN 순 정렬. ACK/해결 버튼.

### 3.3 원고 프리셋 & 생성기 `/(erp)/manuscript?client=[id]` — M3
- 좌: 프리셋 선택(브랜드/정보성/영수증) + 슬롯 폼(키워드·병원·상세). "원고 생성".
- 우: 결과 뷰어 — 본문 + **의료광고 통과 배지**(위반 시 빨강+사유) + 유사문서 리스크 + "네이버 서식 복사" 버튼(P5).
- 프리셋 편집: roleSetup·13규칙을 거래처별로 저장(개인 파일 → ERP 승격).

---

## 4. 월보장 알림 — 카카오 알림톡 페이로드(예)

```
[베놈 월보장 경보] 🔴
거래처: OO정형외과
키워드: '수성구 도수치료' (상단통합 보장 1위)
상태: 1위 → 미노출 (07-13 08:00 감지)
담당: 신현지 · ERP에서 확인 → {링크}
```

Make 시나리오: `guard-scan` 웹훅 → 필터(level≥WARN) → 카카오 알림톡 모듈 → ERP `Alert.status=OPEN`.

---

## 5. 마이그레이션 & 롤아웃

1. **스키마 push** → 시드: 기존 거래처 1곳으로 파일럿.
2. **CSV 임포트**: 현행 "노출현황"·"발행" 시트 → Keyword/ExposureSnapshot. 컬럼 매핑 스크립트 제공.
3. **프리셋 이관**: 담당자 프롬프트(스크린샷의 13규칙)를 PromptPreset로 등록.
4. **병행운영 2주**: 시트와 ERP 동시 기록 → 정합성 확인 후 시트 폐기.
5. 크론 활성화(guard-scan) → 알림 임계값 튜닝.

---

## 6. 완료 기준 (Definition of Done)

- [ ] 월보장 키워드 이탈 시 24h 내 카카오 알림 도달(디바운스 동작).
- [ ] 프리셋+슬롯 입력만으로 의료광고법 통과 원고 1건 생성.
- [ ] 담당 교체 후에도 특이사항 노트 100% 승계.
- [ ] 노출 매트릭스가 시트와 1:1 대응(파일럿 거래처).
- [ ] 신규 API가 함수 3개 이내(한도 준수).
