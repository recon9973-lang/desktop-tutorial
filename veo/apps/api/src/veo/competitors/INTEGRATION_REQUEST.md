# 통합 요청 — 경쟁사 비교 작업자 → 통합 담당

이 작업자의 편집 범위는 세 곳입니다.

- `apps/api/src/veo/competitors/**`
- `apps/api/tests/competitors/**`
- `tests/fixtures/competitors/**`

그 밖의 파일은 손대지 않았습니다. 특히 `veo/compare/**`, `veo/authz/**`,
`veo/db/**`, `veo/api/app.py` 는 읽기만 했습니다.

상태 표기: `열림` / `처리중` / `완료` / `보류`

---

## 0. 먼저 알아야 할 사실 — 비교 결과를 저장할 테이블이 없습니다

스키마에 `competitor_comparisons` 에 해당하는 테이블이 없고, 이 작업자는 테이블을
추가할 수 없습니다(`alembic/**`, `veo/db/**` 범위 밖).

**현재 동작:** `veo/competitors/router.py` 의 모듈 전역 `_STORE`
(`InMemoryComparisonStore`) 에 보관합니다. 결과적으로 다음이 사실입니다.

- 프로세스가 재시작되면 **생성한 비교 결과가 사라집니다.**
- 워커가 여러 개면 **A 워커가 만든 결과를 B 워커가 읽지 못합니다.**
- 목록·상세는 조직·프로젝트로 걸러지지만, 그 격리는 SQL 이 아니라 파이썬 딕셔너리가
  보장합니다.

이 상태로는 **운영에 올리면 안 됩니다.** 요청 #2 가 처리될 때까지는 라우터를
마운트하지 않는 편이 안전합니다. 계산 엔진(`comparison.py`, `sov.py`,
`conditions.py`)은 저장소와 무관하게 완성되어 있고, 워커·서비스에서
`veo.competitors.comparison.compare` 로 바로 쓸 수 있습니다.

---

## 요청 #1 — `veo.api.app` 에 competitors 라우터 마운트

**상태:** 열림 (요청 #2 이후 처리 권장)
**대상 파일:** `apps/api/src/veo/api/app.py`
**우선순위:** 중간

```python
from veo.competitors.router import router as competitors_router
...
app.include_router(competitors_router, prefix=api_prefix)
```

`tests/competitors/test_competitor_router.py::test_the_router_is_not_mounted_by_the_application`
이 "아직 마운트되지 않았음"을 지키고 있습니다. 마운트하면 그 테스트를 함께
갱신해야 하고, `openapi.json` 재생성도 필요합니다.

추가되는 경로:

| 메서드 | 경로 | 권한 |
| --- | --- | --- |
| POST | `/competitors/comparisons` | `COMPETITOR_WRITE` |
| GET | `/competitors/comparisons` | `COMPETITOR_READ` |
| GET | `/competitors/comparisons/{comparison_id}` | `COMPETITOR_READ` |

권한 매트릭스는 그대로 충분합니다. 새 권한을 요청하지 않습니다.
비교 생성은 고객에게 나가는 산출물을 만드는 행위라서 `COMPETITOR_WRITE` 로 두었고,
`COMPETITOR_READ` 만 가진 역할(`SALES_VIEWER`, `CLIENT_VIEWER`)은 생성에서 403 을
받습니다(`test_competitor_read_cannot_create_a_comparison`).

---

## 요청 #2 — `competitor_comparisons` 테이블 신설

**상태:** 열림
**대상 파일:** `apps/api/src/veo/db/models/analysis.py`, `alembic/**`
**우선순위:** 높음 (이것 없이는 운영 불가 — §0 참조)

제안 형태입니다. 컬럼 이름은 통합 담당이 정해 주십시오.

```python
class CompetitorComparison(Base, OrganizationScopedMixin, ImmutableMixin):
    """한 번의 경쟁사 비교. 만들어진 뒤에는 수정하지 않습니다."""

    __tablename__ = "competitor_comparisons"

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    spec_id: Mapped[str] = mapped_column(String(120), nullable=False)
    spec_version: Mapped[str] = mapped_column(String(32), nullable=False)
    spec_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    allow_scope_variance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    comparable_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    refused_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary_ko: Mapped[str] = mapped_column(Text, nullable=False)
    competitor_ids: Mapped[JsonArray] = json_column()
    document: Mapped[JsonObject] = json_column()
```

세 가지만 지켜 주시면 됩니다.

1. **`allow_scope_variance` 는 별도 컬럼**이어야 합니다. 예외를 허용하고 만든
   비교인지 여부는 `document` JSON 안에만 있으면 목록·감사에서 걸러낼 수 없습니다.
2. **`confidence` 는 nullable** 이어야 합니다. 비교 가능한 상대가 하나도 없으면
   신뢰도는 0 이 아니라 **없음**입니다. `NOT NULL DEFAULT 0` 으로 만들면 "신뢰도
   0%인 비교"라는 존재하지 않는 상태가 생깁니다.
3. **불변(`ImmutableMixin`)** 이어야 합니다. 재계산은 새 행이지 수정이 아닙니다.

반영되면 `veo/competitors/service.py` 의 `ComparisonStore` 프로토콜에
`SqlComparisonStore` 구현만 추가하고 `router.py` 의 `_STORE` 를 지우겠습니다.
서비스·엔진은 손댈 필요가 없습니다.

---

## 요청 #3 — `CollectionContext` 에 측정 조건 3종 추가 (가장 중요한 정합성 구멍)

**상태:** 열림
**대상 파일:** `apps/api/src/veo/collect/contract.py`
**우선순위:** 높음

`MeasurementConditions` 의 10개 필드 가운데 **7개는 측정 결과에서 읽어 냅니다.**

| 필드 | 출처 |
| --- | --- |
| `spec_id` · `spec_version` · `spec_checksum` | `ScoreResult` |
| `pages_examined` | `len(context.documents)` — 실제로 받아 온 문서 수 |
| `locale` | `context.locale` |
| `enabled_providers` | `context.provider_states` 중 `ENABLED` 만 |
| `measured_at` | `context.collected_at` |

**나머지 3개는 `CollectionContext` 에 자리가 없습니다.**

- `collector_version`
- `device` (`ScanRun.device_profile` 에는 있으나 컨텍스트에는 없음)
- `renderer` (`rendered_dom` 이 비었는지로 추론할 수는 있지만, "렌더러가 돌지
  않았다"와 "돌았는데 아무것도 못 냈다"를 구분할 수 없어 추론하지 않았습니다)

**현재 대응:** 이 셋은 `conditions_from_score(...)` 의 **기본값 없는 키워드
인자**이고, 공백이면 `MissingConditionError` 로 거부합니다. 임의 기본값을 넣지
않은 이유는 하나입니다 — 기본값이 들어가는 순간, 조건이 다른 두 측정이 같은
조건인 것처럼 비교되고 그 사실을 아무도 알아채지 못합니다.

**요청:**

```python
# CollectionContext 에 추가
collector_version: str = ""      # 빈 문자열 금지, 수집 파이프라인이 채움
device_profile: str = ""         # MOBILE | DESKTOP
renderer: str = ""               # NONE | HEADLESS_CHROME | ...
```

반영되면 `conditions.py` 의 세 인자를 지우고 컨텍스트에서 읽겠습니다.
`veo/competitors/conditions.py` 한 파일, 세 줄짜리 변경입니다.

**남는 위험 (반영 전까지, 정직하게 적습니다):** 위 표의 "출처"는 **인프로세스
경로**(`conditions_from_seo_scan` / `conditions_from_geo_report`)에만 해당합니다.
HTTP 로 들어오는 `POST /competitors/comparisons` 에는 `CollectionContext` 가
없으므로 **`spec_checksum` 을 뺀 모든 조건을 호출자가 선언**합니다.

- 발행본과 대조해 **검증되는 것:** `spec_id` · `spec_version` · `spec_checksum`
  (`load_verified_spec`). 감사할 수 없는 문서로 계산된 점수는 거부됩니다.
- **선언을 그대로 믿는 것:** `collector_version` · `device` · `renderer` ·
  `pages_examined` · `locale` · `enabled_providers` · `measured_at`.

즉 호출자가 데스크톱으로 잰 경쟁사를 `device: "MOBILE"`, 4페이지만 수집한
측정을 `pages_examined: 30` 이라고 적어 보내면 VEO 는 알아챌 수 없고, 비교는
정상적으로 성립합니다. **이것이 이 패키지에 남아 있는 유일한 오도 경로입니다.**
빈 값·공백은 거부하므로 "실수로 비는" 경우는 막히지만, "틀리게 채우는" 경우는
막을 방법이 지금 구조에는 없습니다.

요청 #4 처럼 측정을 VEO 가 저장한 `scan_runs` 참조로 받게 바꾸면 이 구멍이
완전히 닫힙니다. 그때까지는 이 엔드포인트를 **VEO 파이프라인만 호출하도록**
운영에서 제한하시길 권합니다.

---

## 요청 #4 — 측정을 `scan_runs` 참조로 받을 수 있게 (권고, 지금은 불가)

**상태:** 열림
**대상 파일:** 결정 사항 + `veo/db/**`
**우선순위:** 중간

지금 `POST /competitors/comparisons` 는 SEO·GEO 라우터와 같은 방식으로 **끝난
측정을 본문으로** 받습니다. 더 안전한 형태는 이것입니다.

```json
{ "project_id": "...", "baseline_scan_run_id": "...",
  "competitors": [{"competitor_id": "...", "scan_run_id": "..."}] }
```

이러면 측정 조건을 호출자가 아니라 **VEO 가 저장한 행에서** 읽으므로 요청 #3 의
잔여 위험이 사라집니다. 다만 지금은 다음이 없어서 구현할 수 없습니다.

- 경쟁사 사이트의 스캔을 `scan_runs` 에 남기는 파이프라인 (경쟁사는 `sites` 가
  아니라 `competitors` 이고, `scans.site_id` 는 `sites` 를 가리킵니다)
- `scan_runs` 에 `locale` · `renderer` 컬럼 (지금은 `device_profile` 과
  `collector_version` 만 있습니다)

**결정이 필요한 지점:** 경쟁사 스캔을 `scans`/`scan_runs` 에 넣을지, 아니면
경쟁사 전용 실행 테이블을 둘지. 전자라면 `scans` 에 `competitor_id` 가
필요합니다. 이 작업자가 단독으로 정할 문제가 아니라고 판단해 요청으로 남깁니다.

---

## 요청 #5 — 관측 SOV 입력을 만들어 줄 집계 (관측 엔진 담당)

**상태:** 열림
**대상 파일:** GEO 관측 엔진 (이 작업자 범위 밖)
**우선순위:** 중간

`veo/competitors/sov.py` 는 **숫자를 세지 않습니다.** 이미 센 값을 받습니다.

```python
ParticipantVisibility(
    key=..., label_ko=..., is_own_brand=...,
    cited_answer_count=...,      # 이 브랜드가 인용된 '응답 수'
    mentioned_answer_count=...,  # 이 브랜드가 언급된 '응답 수'
    won_prompt_count=...,        # 이 브랜드가 이긴 프롬프트 수
)
```

세 값은 `citations`, `entity_mentions`, `ai_answers` 에서 나와야 합니다.
주의할 점 두 가지를 미리 적어 둡니다.

1. **응답 수이지 등장 횟수가 아닙니다.** `entity_mentions` 는
   `UniqueConstraint(ai_answer_id, entity_key)` 로 이미 응답당 1건이니 그대로
   세면 되고, `raw_occurrence_count` 를 더하면 안 됩니다.
2. **`is_valid_execution=False` 인 답변은 분모에서 빠져야 합니다.**
   `observed_answer_count` 는 유효 실행만 세 주십시오.
3. `won_prompt_count` 의 "승자" 정의(첫 인용? 최다 인용?)는 관측 엔진이
   정하고 응답에 명시해 주십시오. SOV 는 정의를 만들지 않고 그대로 나눕니다.
   합이 `decided_prompt_count` 를 넘으면 거부합니다.

`needs_human_disambiguation=True` 인 언급을 어느 쪽으로 셀지도 관측 엔진의
결정입니다. 개인적으로는 **분자에서 빼고 별도로 표시**하는 쪽을 권합니다.

---

## 요청 #6 — `JobType.COMPETITOR_COMPARISON` 은 아직 필요 없습니다 (알림)

`veo/contracts/enums.py` 에 이미 있습니다. 다만 비교 계산은 외부 호출이 없고
입력이 이미 끝난 측정이라 **동기 요청 안에서 끝납니다.** 지금 워커로 뺄 이유가
없다고 판단했습니다. 요청 #4 처럼 `scan_runs` 를 읽어 오게 바뀌면 그때 다시
검토하는 편이 맞습니다.

---

## 요청 #7 — 새 의존성 없음 (알림)

이 패키지는 표준 라이브러리와 이미 설치된 `fastapi` · `pydantic` · `sqlalchemy`
만 씁니다. `pyproject.toml` 변경을 요청하지 않습니다.

---

## 부록 — 이 패키지가 지키기로 한 규칙 (검토 시 확인해 주십시오)

바꾸려면 테스트가 먼저 막을 것입니다. 의도적으로 그렇게 만들었습니다.

1. **조건이 다르면 비교하지 않습니다.** 모든 쌍이
   `veo.compare.assert_comparable` 을 통과해야 하고, 막히면 델타를 **하나도**
   만들지 않습니다. 부분 비교는 없습니다.
   (`test_a_refused_comparison_carries_no_deltas_at_all`)
2. **거부는 200 입니다.** "이 둘은 같은 조건에서 잰 게 아닙니다"는 오류가 아니라
   답입니다. 어떤 필드가 막았는지 한국어로 함께 돌려줍니다.
3. **예외는 페이지 수 차이 하나뿐이고, 기본값이 아니며, 허용해도 결과에 남습니다.**
   (`test_the_waiver_cannot_wave_through_a_methodology_difference`)
4. **한쪽만 측정한 항목은 격차가 아닙니다.** `UNKNOWN` · `NOT_APPLICABLE` 은
   분모에서 빠지고 `NOT_COMPARABLE` 로 표시됩니다. 0점으로 치환하지 않습니다.
5. **신뢰도는 약한 쪽을 따르고 격차만큼 더 내려갑니다.**
   `min(a, b) * (1 - |a - b|)`. 0.4 대 0.9 는 0.2 이고, 근거 문장에 두 값이
   그대로 적힙니다.
6. **분모가 0인 점유율은 `데이터 없음` 입니다.** 아무도 인용되지 않은 것은
   "우리 점유율 0%"가 아닙니다.
7. **SOV 는 준비도 점수를 모릅니다.** `sov.py` 소스에 `veo.scoring` ·
   `veo.compare` · `overall_score` 문자열이 없는지 테스트가 검사합니다.
   (`test_the_module_knows_nothing_about_readiness_scores`)
8. **다른 조직의 경쟁사·비교 결과는 404 입니다.** 없는 id 와 글자 하나까지 같은
   응답이라 존재 확인용으로 쓸 수 없습니다.
