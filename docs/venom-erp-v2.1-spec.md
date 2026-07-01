# 베놈 ERP V2.1 — 통합 구현 스펙 (Single Source of Truth)

작성일: 2026-07-01
근거: `venom-erp-v2-structure-brainstorm.md`(안건 1~7 확정) + `venom-erp-v2-plan.md` + `venom-erp-v2-sprint1-wbs.md` + `venom-erp-v2-calendar-scheduler.md`
대상 코드: `recon9973-lang/marketing-agency-erp` (`erp-v1`)
스택: Next.js 15 App Router · Prisma 6 · PostgreSQL · Auth.js · zod · Tailwind

> 이 문서는 브레인스토밍 결정들을 **구현용 단일 스펙**으로 통합한 것이다. 개별 결정 근거는 브레인스토밍 문서 참조.

---

## 1. 정보구조(IA) — 2기둥

내비게이션을 두 그룹으로 재편(개념 틀):

```
🤝 거래처단 (Client)
  ├ 거래처 목록/등록/상세   (업종·채널계정·계약)
  ├ 업무 (거래처별, 세분화)
  ├ 캘린더 스케줄러
  ├ 입금현황 (청구/입금/대사)
  └ 보고서/성과

🏢 베놈단 (Internal)
  ├ 대시보드 (회사 전체)
  ├ 직원/권한
  ├ 연차/휴가
  ├ 회사 지출 · 계좌/카드
  ├ 추적 (로그인·활동 이력)   ← 최고관리자
  └ 설정 (마스터·연동·정책)
```
- 마케터: 거래처단 중심 + 베놈단은 본인 휴가/일정.
- 관리자: 범위 내 거래처단 + 일부 베놈단.
- 최고관리자: 전체.

---

## 2. 데이터 모델 변경 (= 마이그레이션 목록)

### 2.1 신규 모델

| 모델 | 목적 | 핵심 필드 |
|---|---|---|
| `IndustryCategory` | 업종 마스터(2단) | id, name, parentId(자기참조: 대분류/진료과), colorTag, isLocked, isActive, sortOrder |
| `WorkCategoryMaster` | 업무 카테고리 마스터 | id, name, group(블로그/검색광고/지도/SNS/웹/운영), colorTag, isLocked, isActive, sortOrder |
| `ChannelType` | 채널 종류 마스터 | id, name, colorTag, isActive, sortOrder |
| `LoginHistory` | 로그인 이력 | id, userId, at, ip, userAgent, success, logoutAt |
| `BankTransaction` | 입금 반자동 대사용 임포트 내역 | id, importedAt, txDate, amount, counterpartyName, memo, matchedBillingId?, matchStatus |
| `CompanySetting` | 회사 정책 토글 | id(singleton), adminCanManageExpense(bool), 기타 정책 |

### 2.2 기존 모델 필드 추가

| 모델 | 추가 필드 |
|---|---|
| `Client` | `industryCategoryId`(FK), `industryCustom`(String?), (진료과는 IndustryCategory 자식 참조) |
| `WorkItem` | `parentId`(자기참조, 세분화), `sequence`, `scheduledStart`, `scheduledEnd`, `estimatedMinutes`, `workCategoryId`(마스터 FK; 기존 enum 대체/병행) |
| `ClientAccount` | `channelTypeId`(FK), `usernameEnc`, `passwordEnc`(암호화), `credentialViewedLog` 연동 |
| `AuditLog` | (활용 확대: 민감 열람·로그인 이벤트 기록. 필드 추가 없음) |

### 2.3 인증 변경
- **Kakao OAuth → 이메일 인증(verification) 가입**으로 변경. Auth.js Email/Credentials + 인증메일. (Kakao 병행은 추후 결정)

### 2.4 보안
- 자격증명: **AES-256-GCM** 대칭암호, 키 `CREDENTIAL_ENC_KEY`(env). 평문 로그/응답 금지.
- 자격증명 열람 시 **AuditLog 필수 기록**.

---

## 3. 모듈별 스펙

### 3.1 거래처 (Client)
- 등록 폼: 기본정보 + **업종 대분류 → (의료면) 진료과 → 기타 수기** + 계약(기간/월계약금) + 담당자 배정.
- 목록: 업종 **색상 태그** 표시, 필터(업종/담당자/상태).
- 상세: 기본정보 / 채널계정 / 업무 / 입금 / 보고서 탭.
- 비활성화: 차단 없이 가능, 미수금·미완업무·계약종료 **표시 후 확인**.
- 담당자 변경: 거래처 업무 함께 이관, 개인 업무 유지.

### 3.2 업종/카테고리/채널 마스터 (설정)
- 관리자: 추가/수정/삭제. 최고관리자: **잠금(lock)** — 잠긴 항목은 관리자 변경 불가.
- 색상 지정. 정렬. 활성/비활성.

### 3.3 업무 (WorkItem) + 세분화
- 카테고리 13종(6그룹). 부모(묶음)-자식(낱개) 세분화(`parentId`).
- 상태전이: V1 transitionMap(start/submit_for_review/approve/block/resume) 유지. 불법전이 차단.
- 진행메모, 첨부(URL 링크 방식), 소유자 재배정.

### 3.4 캘린더 스케줄러
- 마감(`dueDate`) ≠ 작업예정(`scheduledStart/End`) 분리.
- 일/주/월/담당자레인 뷰, 드래그 배치·이동, 미배치 트레이, 워크로드 과부하 경고.
- 업무 마감/예정 → CalendarEvent(TASK) 자동 동기화.

### 3.5 입금현황 (반자동)
- 1차: 청구 생성 + 수기 입금기록 + 상태 자동계산.
- 반자동: 은행 거래내역 CSV 업로드 → `BankTransaction` → 금액·거래처명 후보매칭 → 버튼 확정 → 청구상태 변경 + Audit.
- 카드 5%: 수기. PG/오픈뱅킹 자동은 V3.
- **마케터 열람 불가**(재무 격리).

### 3.6 보고서/성과
- `Report.metrics`(JSON): 키워드 순위 **자동수집(B)** + 나머지 수기.
- 검토/전달 상태(DRAFT/REVIEW_NEEDED/APPROVED/DELIVERED).
- **PDF 자동생성**(지표 표/그래프 + 코멘트) + 공유 링크.

### 3.7 추적/감사 (최고관리자)
- 로그인 이력 + 활동 이력(민감 열람 포함) 통합 뷰. 사용자·기간·대상 필터.
- 보존 기간 정책(예: 1년, 추후 확정).

### 3.8 베놈단 운영
- 직원 초대/역할변경: 관리자 허용(단 SUPER_ADMIN 부여 불가).
- 회사 지출 등록/검토: 최고관리자 토글로 관리자 허용 여부 결정(기본 OFF).
- 휴가 신청(전원) / 승인·반려(관리자까지).

---

## 4. 최종 권한 매트릭스

| 기능 | 최고관리자 | 관리자 | 마케터 |
|---|---|---|---|
| 거래처 등록/수정/비활성화 | 전체 | 범위 | 조회 |
| 업무 CRUD/상태/메모 | 전체 | 범위 | 본인거래처 |
| 채널계정 관리 | 전체 | 범위 | 본인거래처 |
| 비밀번호 열람 | 전체 | 범위 | 본인거래처(감사기록) |
| 입금/청구 입력·대사 | ✅ | 범위 | ❌ 열람불가 |
| 보고서 작성/지표 | ✅ | 범위 | 본인거래처 |
| 보고서 검토/전달 | ✅ | 범위 | ❌ |
| 직원 초대/역할변경 | ✅ | ✅(≤관리자) | ❌ |
| AccessScope 설정 | ✅ | ❌ | ❌ |
| 마스터 관리 | ✅+잠금 | ✅(잠금제외) | ❌ |
| 회사 지출 등록/검토 | ✅ | 🔧토글 | ❌ |
| 휴가 신청 | ✅ | ✅ | ✅본인 |
| 휴가 승인/반려 | ✅ | ✅ | ❌ |
| 추적 조회 | ✅ | ❌ | ❌ |
| 설정 전체 | ✅ | ❌ | ❌ |

---

## 5. 스프린트 재편 (로드맵)

| 스프린트 | 범위 | 마이그레이션 |
|---|---|---|
| **0. 셋업** | ERP 레포 세션, 운영 DB, 이메일 인증 Auth, 초기 SUPER_ADMIN, 쓰기 공통 인프라(withAction/감사) | — |
| **1. 거래처+업무 코어** | 업종 마스터·거래처 CRUD·업무 CRUD/상태/메모, 마스터 관리 UI | IndustryCategory, WorkCategoryMaster, ChannelType, Client/WorkItem 필드 |
| **1.5 캘린더 스케줄러** | 세분화(parentId)·예정시간·드래그·워크로드 | WorkItem scheduled/parent 필드 |
| **2. 채널계정+보안** | 채널계정 CRUD, 자격증명 암호화 저장/열람, 감사 | ClientAccount 암호화 필드 |
| **3. 입금현황** | 청구/입금 입력 + 반자동 대사(CSV) | BankTransaction |
| **4. 보고서/성과** | 작성·키워드순위 자동수집(B)·PDF·검토/전달 | (Report 활용) |
| **5. 추적/감사 + 정책** | 로그인/활동 이력, 추적 화면, 지출 토글 | LoginHistory, CompanySetting |
| **6(V3)** | PG·오픈뱅킹·세금계산서·외부 캘린더·성과 자동수집 확대 | — |

---

## 6. 착수 조건 (변동 없음)
- ERP 코드(`marketing-agency-erp`)는 이 세션 권한 밖 → **해당 레포로 스코프된 새 세션**에서 구현.
- staging 코드(`docs/erp-v2-staging/`)의 공통 인프라·거래처/업무 액션이 스프린트 0~1의 출발점.

---

## 7. 미결/추후 확정
- Kakao 로그인 병행 여부(현재 이메일 인증으로 결정).
- 추적 로그 보존 기간.
- 워크로드 1일 가용시간 기본값.
- 드래그 캘린더: 직접 구현 vs 라이브러리.
- 지출 토글 기본값(권장 OFF).
