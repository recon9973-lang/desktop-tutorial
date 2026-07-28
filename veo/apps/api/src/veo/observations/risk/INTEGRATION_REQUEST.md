# 통합 요청 — 위험·검수 작업자 → 통합 담당

이 작업자의 편집 범위는 네 곳입니다.

- `apps/api/src/veo/observations/risk/**`
- `apps/api/src/veo/observations/review/**`
- `apps/api/tests/observations/risk/**`
- `apps/api/tests/observations/review/**`

그 밖의 파일은 손대지 않았습니다. 특히 `veo/db/models/observation.py`,
`veo/contracts/enums.py`, `alembic/**`, `veo/api/app.py` 는 읽기만 했습니다.

상태 표기: `열림` / `처리중` / `완료` / `보류`

---

## 0. 가장 먼저 읽어야 할 사실 — 게이트가 아직 아무 데도 연결되어 있지 않습니다

`veo/observations/review/gating.py` 의 `apply_publication_gate()` 는 **어떤 라우터에서도,
어떤 리포트 생성 경로에서도 호출되지 않습니다.** `claim_assessments` 테이블을 읽는 코드는
현재 저장소 전체에 하나도 없습니다(`grep` 확인).

지금은 위험 지적을 고객에게 내보내는 경로 자체가 없으므로 실제 노출 위험은 없습니다.
그러나 **`veo/reports` 가 위험 섹션을 추가하는 순간**, 게이트를 통과시키지 않으면
검수되지 않은 자동 판정이 그대로 고객 문서에 실립니다. 요청 #5 를 그때 함께 처리해야 합니다.

---

## 요청 #1 — `claim_assessments.assessment_type` 어휘 2종 추가

**상태:** 열림
**대상 파일:** `apps/api/src/veo/db/models/observation.py`(주석), `alembic/**`
**우선순위:** 중간

방법론이 정의하는 위험 유형은 8종인데 컬럼 주석의 어휘는 7종입니다. 다음 두 쌍이 하나로
합쳐져 있습니다.

| 방법론 유형 | 현재 저장값 |
| --- | --- |
| `RECOMMENDATION_INCLUSION` (취급하지 않는 시술 추천 목록에 올랐다) | `RECOMMENDATION` |
| `RECOMMENDATION_EXCLUSION` (당연히 들어가야 할 목록에서 빠졌다) | `RECOMMENDATION` |

두 지적은 대응이 완전히 다릅니다. 전자는 정정 요청, 후자는 노출 개선입니다.

**현재 우회:** `RiskKind.storage_value` 가 저장할 때 좁히고,
`RiskKind.from_storage("RECOMMENDATION")` 은 **되읽기를 거부합니다.** 추측해서 한쪽을 고르면
"목록에서 빠졌다"가 "잘못 추천되었다"로 조용히 바뀌기 때문입니다. 즉 지금 이 컬럼은
쓰기 전용에 가깝고, 왕복이 성립하지 않습니다.

**요청:** 주석의 허용값에 `RECOMMENDATION_INCLUSION`, `RECOMMENDATION_EXCLUSION` 추가
(`SENTIMENT` → `SENTIMENT_WITH_GROUNDS` 는 이름만 다르고 정보 손실이 없으므로 선택).
`String(48)` 이라 길이는 여유가 있습니다.

---

## 요청 #2 — `ReviewState` 에 `UNDER_REVIEW`, `NEEDS_MORE_EVIDENCE` 추가

**상태:** 열림
**대상 파일:** `apps/api/src/veo/contracts/enums.py`, `packages/shared-types`
**우선순위:** 중간

지시받은 검수 상태 기계는 다섯 상태입니다.

```
PENDING_REVIEW → UNDER_REVIEW → { CONFIRMED, REJECTED, NEEDS_MORE_EVIDENCE }
```

`ReviewState` 에는 `NOT_REVIEWED / PENDING_REVIEW / HUMAN_CONFIRMED / HUMAN_REJECTED`
넷만 있습니다.

**현재 우회:** `ReviewStage.to_contract_state()` 가 아래처럼 좁힙니다.

| 내부 단계 | 저장값 |
| --- | --- |
| `PENDING_REVIEW` | `PENDING_REVIEW` |
| `UNDER_REVIEW` | `PENDING_REVIEW` |
| `NEEDS_MORE_EVIDENCE` | `PENDING_REVIEW` |
| `CONFIRMED` | `HUMAN_CONFIRMED` |
| `REJECTED` | `HUMAN_REJECTED` |

**손실은 안전한 방향입니다.** 끝나지 않은 검수가 끝난 것으로 되읽히는 일은 없습니다
(`test_only_a_confirmed_stage_maps_to_human_confirmed` 가 이를 고정합니다). 잃는 것은
운영 정보입니다 — 재기동 후 "누가 잡고 있었는지", "근거 보강 대기인지 손도 안 댄 건인지"를
행에서 복원할 수 없습니다.

---

## 요청 #3 — 검수 점유(assignment) 컬럼 3종

**상태:** 열림
**대상 파일:** `apps/api/src/veo/db/models/observation.py`, `alembic/**`
**우선순위:** 높음 (요청 #5 보다 먼저일 필요는 없으나, 다중 검수자 운영 전에는 필수)

`ReviewQueue` 의 점유·반납·만료는 **전부 인메모리**입니다. 프로세스가 재시작되면
누가 무엇을 맡고 있었는지 사라지고, 워커가 두 대면 같은 치명 등급 건을 두 사람이
각각 판정할 수 있습니다.

필요한 컬럼:

| 컬럼 | 타입 | 용도 |
| --- | --- | --- |
| `claimed_by` | `UUID FK users.id NULL` | 지금 이 건을 맡고 있는 검수자 |
| `claimed_at` | `timestamptz NULL` | 점유 시각 |
| `claim_expires_at` | `timestamptz NULL` | 만료 시각(`SYSTEM_LAPSE` 트리거의 근거) |

`reviewed_by` 로 대신할 수 없습니다. 그 컬럼은 "판단한 사람"이고 여기 필요한 것은
"아직 판단하지 않았지만 보고 있는 사람"입니다. 둘을 합치면 착수만 하고 판단하지 않은 건이
검수 완료로 읽힙니다.

---

## 요청 #4 — 검수 감사 로그를 `audit_logs` 에 남길 수 있는 경로

**상태:** 열림
**대상 파일:** `veo/db/models/identity.py`(읽기), 저장 서비스 소유자
**우선순위:** 중간

`ReviewQueue.audit_trail()` 은 enqueue·claim·release·decide 를 append-only 로 남기지만,
역시 인메모리입니다. `veo/issues/service.py` 가 상태 변경을 `audit_logs` 에 적재하듯
같은 처리가 필요합니다. 이 작업자는 `veo/db/**` 와 세션 계층을 편집할 수 없어 적재 코드를
작성하지 않았습니다.

남겨야 할 필드는 `QueueEvent.as_dict()` 가 그대로 제공합니다
(`event_type`, `assessment_id`, `at`, `reviewer_id`, `detail_ko`).

---

## 요청 #5 — 리포트 생성 경로에서 게이트를 반드시 통과시킬 것

**상태:** 열림
**대상 파일:** `apps/api/src/veo/reports/**`
**우선순위:** 최상 (위험 섹션을 추가하는 시점에)

고객용 위험 섹션은 **반드시** 아래를 거쳐야 합니다.

```python
from veo.observations.review.gating import apply_publication_gate

result = apply_publication_gate(reviewed_assessments)
payload = result.as_customer_payload()      # 고객 문서용
staff_view = result.as_internal_payload()   # 내부 화면 전용
```

- `as_customer_payload()` 는 검수되지 않은 치명·높음 지적의 **문장을 담지 않습니다.**
  건수와 심각도, 그리고 왜 보류되었는지만 한국어로 담습니다.
- `as_internal_payload()` 는 **내부 전용**입니다. 보류된 지적의 원문이 들어 있으므로
  고객 문서·공개 리포트 토큰 경로에 연결하면 안 됩니다.
- 위험 섹션에 종합 점수를 만들지 마십시오. 심각도별 건수만 보고합니다
  (`test_the_payload_contains_no_composite_score_anywhere` 가 직렬화된 payload 를 순회하며
  점수로 읽힐 수 있는 키를 전부 거부합니다).

---

## 요청 #6 — 함의 판정용 언어모델 자격증명

**상태:** 열림
**대상 파일:** `veo/credentials/**`, 배포 설정
**우선순위:** 중간

`veo/observations/risk/entailment.py` 는 `EntailmentModel` 프로토콜 뒤로만 모델에 접근하며,
이 모듈은 네트워크 호출도 자격증명 보관도 하지 않습니다. **어댑터가 아직 없습니다.**

자격증명이 없는 상태에서의 동작은 이미 고정되어 있습니다.

- 모델이 `None` 이거나 `ProviderState` 가 `ENABLED` 가 아니면 → `UNKNOWN`,
  `basis=NOT_MEASURED`, **외부 호출 없음**.
- 인용 URL 없음 / 404 는 자격증명 없이도 규칙으로 판정됩니다.
- `UNKNOWN` 판정은 게이트에서 `EXCLUDED_NOT_MEASURED` 로 빠지며, 보고서에는
  "확인하지 못한 건수"로만 나타납니다.

어댑터를 붙일 때 `model_id` 와 `prompt_version` 을 반드시 실제 값으로 제공해야 합니다.
`AutomatedJudgement` 는 둘 중 하나라도 비어 있으면 언어모델 판정을 **거부**합니다.

---

## §A. 검증하지 못한 채로 정한 것

| 항목 | 정한 값 | 근거와 한계 |
| --- | --- | --- |
| 심각도 4단계 ↔ `Severity` 대응 | 치명→`BLOCKER`, 높음→`CRITICAL`, 중간→`MAJOR`, 낮음→`MINOR` | 방법론 문서를 받지 못해 플랫폼 공통 어휘에 맞춰 정렬했습니다. `Severity.INFO` 는 의도적으로 미사용 — 조치 가치가 없는 지적은 아예 기록하지 않습니다. |
| 검수 필수 기준선 | `높음` 이상 | 치명·높음은 검수 전 게재 불가, 중간·낮음은 "자동 판정" 표기와 함께 게재. 전부 검수 필수로 하면 큐가 절대 비지 않아 아무것도 나가지 못합니다. |
| 유형별 기본 등급 | `taxonomy.py` 의 `base_band` | 규제 영역(의료·법률·가격·계약)은 유형과 무관하게 치명이므로, 기본 등급은 비규제 영역에만 적용됩니다. |
| `ClaimDomain` 8종 | 의료·법률·가격·계약·식별·연락·평판·일반 | 규제 4종은 지시에 명시된 그대로이고, 나머지 4종은 실무에서 필요한 최소 분류입니다. |

## §B. 예시 데이터에 대한 고지

`taxonomy.py` 의 실무 예시와 두 테스트 스위트의 픽스처는 **전부 가상**이며 모두
`가상 사례` 표기를 달고 있습니다(`test_every_worked_example_is_marked_fictional` 이 강제).
실재 병원에 대한 지적으로 오해될 수 있는 문장은 하나도 넣지 않았습니다. 도메인은
`example.invalid` 만 사용했습니다.
