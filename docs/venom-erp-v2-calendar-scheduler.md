# 베놈 ERP V2 — 담당자 업무 세분화 + 캘린더 스케줄러 설계

작성일: 2026-06-30
선행 문서: `docs/venom-erp-v2-plan.md`, `docs/venom-erp-v2-sprint1-wbs.md`
대상 코드: `recon9973-lang/marketing-agency-erp` (`erp-v1`)
요청 배경: ① 담당자 업무 세분화 ② 캘린더 기능 업데이트 ③ **캘린더가 담당자 업무 스케줄러 역할**

> 핵심 전환: V1의 캘린더는 "일정 목록 조회"였다. V2에서는 **마케터가 자기 업무를 직접 배치·관리하는 일일/주간 스케줄러**로 격상한다.

---

## 0. 개념 정리 — 마감일 ≠ 작업 예정시간

지금 `WorkItem`에는 `dueDate`(마감)만 있다. 스케줄러가 되려면 **"언제 마감"과 "언제 작업"을 분리**해야 한다.

| 필드 | 의미 | 예 |
|---|---|---|
| `dueDate` | 마감 기한 (고객 약속) | A병원 블로그 6/30까지 |
| `scheduledStart` / `scheduledEnd` | 실제 작업 예정 시간 (마케터가 배치) | 6/27 10:00–11:30 작성 |

→ 캘린더는 `scheduledStart/End`로 블록을 그린다. 마감만 있고 예정시간이 없으면 "미배치(unscheduled)"로 표시해 배치를 유도.

---

## 1. 업무 세분화 (Work Subdivision)

### 1.1 모델 방식 — 자기참조(WorkItem.parentId) 채택 ✅(권장)

별도 Subtask 모델 대신 **`WorkItem`에 `parentId` 자기참조**를 추가한다.

이유:
- 기존 상태전이·권한가드·감사로그·캘린더 연동 로직을 **하위 업무가 그대로 재사용**.
- 하위 업무도 독립된 owner/status/일정을 가질 수 있음(마케터별 분담 가능).
- 부모는 "묶음"(예: 브랜드블로그 10건), 자식은 "낱개"(블로그 1건).

```prisma
model WorkItem {
  // ...기존 필드...
  parentId        String?
  parent          WorkItem?  @relation("WorkSubtasks", fields: [parentId], references: [id])
  subtasks        WorkItem[] @relation("WorkSubtasks")
  sequence        Int        @default(0)   // 정렬/순번
  scheduledStart  DateTime?                 // 작업 예정 시작
  scheduledEnd    DateTime?                 // 작업 예정 종료
  estimatedMinutes Int?                     // 예상 소요(분) — 워크로드 계산용
  @@index([parentId])
  @@index([ownerId, scheduledStart])
}
```
> ⚠️ 이 변경은 **Prisma migration이 필요**하다(기존 "신규 모델 불필요" 전제에서 예외). 컬럼 추가형 마이그레이션이라 기존 데이터 무손실.

### 1.2 부모/자식 규칙
- 부모 상태 = 자식들의 집계(모든 자식 완료 → 부모 완료 가능). 1차는 수동, 2차에 자동 롤업 옵션.
- 자식 owner는 부모 owner 기본값, 개별 변경 가능(분담).
- 마감/예정시간은 자식 단위로 배치(스케줄러는 자식 블록 중심).

### 1.3 반복 업무 → 세분화 자동 생성
- `WorkTemplate`(cadenceDays, estimatedHours 존재)로 부모 1개 + 자식 N개 자동 생성.
- 예: "브랜드블로그 월 10건" 템플릿 → 부모 1 + 자식 10개(마감 분산).

---

## 2. 캘린더 스케줄러 (Calendar as Scheduler)

### 2.1 뷰
| 뷰 | 용도 | 비고 |
|---|---|---|
| **일(Day)** | 마케터 오늘 작업 타임라인 | 시간 블록, 미배치 트레이 |
| **주(Week)** | 한 주 업무 배치/조정 | 드래그 리스케줄 |
| **월(Month)** | 마감 분포·과부하 파악 | 기존 V1 월 목록 확장 |
| **담당자 레인(Resource)** | 마케터별 가로 레인 | 관리자가 팀 부하 한눈에 |

### 2.2 핵심 인터랙션
- **드래그로 배치/이동**: 미배치 업무를 시간대로 끌어다 놓으면 `scheduledStart/End` 세팅.
- **리사이즈**: 블록 길이 = 소요시간 조정.
- **미배치 트레이**: 마감은 있는데 예정시간 없는 업무 모음 → 배치 유도.
- **상태 색상**: 대기/진행중/검수필요/완료/차단/지연 색 구분.

### 2.3 워크로드(과부하) 가드
- 마케터별 하루 `estimatedMinutes` 합계 vs 가용시간(예: 480분) → 초과 시 경고 배지.
- 관리자 레인 뷰에서 팀 부하 분산 판단.

### 2.4 CalendarEvent 연동(기존 모델 재사용)
- `CalendarEvent(kind=TASK, workItemId)`를 `scheduledStart/End` 기준으로 생성/갱신(없으면 dueDate fallback).
- 휴가 승인 → `kind=LEAVE` 자동 블록(2차), 보고서 마감 → `REPORT_DEADLINE`.
- 외부(Google/Naver) 양방향 sync는 V3.

---

## 3. 신규/수정 server actions

| 액션 | 입력 | 동작 |
|---|---|---|
| `scheduleWorkItem` | id, scheduledStart, scheduledEnd | 드래그 배치/이동 → 시간 세팅 + CalendarEvent 동기화 + Audit |
| `unscheduleWorkItem` | id | 예정시간 해제(미배치로) |
| `createSubtask` | parentId, title, ownerId?, dueDate? | 하위 업무 생성(부모 상속) |
| `splitWorkItem` | id, count 또는 항목들 | 부모를 N개 자식으로 분할 |
| `generateScheduleFromTemplate` | templateId, clientId, 월 | 부모+자식 자동 생성 및 마감 분산 |
| `reorderSubtasks` | parentId, 순서배열 | sequence 갱신 |

모든 액션: 기존 `_helpers.ts`(인증→권한→검증→트랜잭션→Audit→revalidate) 패턴 그대로.

---

## 4. 권한
- 마케터: **본인 owner 업무/하위업무만** 배치·이동.
- 관리자: 범위 내 거래처 업무를 배치·재분담(레인 뷰에서 마케터 간 이동).
- 최고관리자: 전체.
- 기존 `assertCanAccessWork` 재사용.

---

## 5. UI 범위
- `/calendar`: 일/주/월/레인 뷰 + 드래그 + 미배치 트레이 + 워크로드 배지.
- `/work`: 부모-자식 트리 표시, 행에서 "캘린더에 배치" 빠른 액션.
- 라이브러리: 드래그 캘린더는 직접 구현(그리드+HTML5 DnD) 또는 경량 라이브러리 도입 여부 결정 필요 ❓.

---

## 6. 스프린트 반영안

이 기능은 1차(업무+거래처)의 **연장선**이므로 두 가지 배치안:

- **(A) 1차 확장**: 1차에 세분화+스케줄러 기본(일/주 뷰, 드래그, scheduledStart/End)을 포함. 1차 범위가 커짐.
- **(B) 1.5차 분리**(권장): 1차(업무 CRUD+거래처)를 먼저 끝내 운영 투입 → 곧바로 **1.5차 "캘린더 스케줄러"**로 세분화+드래그 추가.

> 권장 (B): 빨리 쓸 수 있는 ERP를 먼저 띄우고, 스케줄러를 바로 다음에 얹는다.

---

## 7. 결정 필요 ❓

1. **세분화 모델**: 자기참조(parentId) 채택 OK? (권장) vs 별도 Subtask 모델 vs 체크리스트(JSON, 가장 가벼움).
2. **스케줄 단위**: 시간 블록(시:분)까지 vs 날짜 단위(하루)만. 병원마케팅 업무 특성상 어느 쪽?
3. **배치 시점**: 1차에 포함(A) vs 1.5차 분리(B, 권장).
4. **드래그 캘린더**: 직접 구현 vs 라이브러리 도입.
5. **워크로드 기준**: 마케터 1일 가용시간 기본값(예: 480분/8시간) 확정.

위 5개가 정해지면 1.5차 WBS + 마이그레이션 + server action 코드까지 작성한다.
