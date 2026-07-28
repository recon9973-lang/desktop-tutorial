# 통합 요청 — 리포트 작업자 → 통합 담당

이 작업자의 편집 범위는 두 곳입니다.

- `apps/api/src/veo/reports/**`
- `apps/api/tests/reports/**`

그 밖의 파일은 **하나도 손대지 않았습니다.** `veo/api/app.py`, `alembic/**`,
`openapi.json`, `pyproject.toml`, `db/models/**`, `authz/**` 모두 그대로입니다.
필요한 변경은 전부 아래 요청으로 남깁니다.

상태 표기: `열림` / `처리중` / `완료` / `보류`

---

## 0. 먼저 알아야 할 사실 — 스캔 실행 결과가 저장되지 않습니다

`POST /seo/scan` 과 `POST /geo/readiness` 는 **무상태**입니다. 채점 결과를 남기는
테이블(`scan_runs`, `score_results`)은 모델에는 있지만 이 두 엔드포인트는 쓰지
않습니다. 즉 **"run_id 로 리포트를 만들어라"를 지금은 구현할 수 없습니다.**
없는 행을 가리키는 API 를 만드는 대신, `POST /reports` 가 `/seo/scan` 과 같은
방식으로 **완료된 진단을 본문으로 받습니다**(`CreateReportRequest`).

`included_run_ids` 는 요청이 준 문자열을 그대로 보관만 합니다. `observation_runs`
와 대조하지 않습니다 — 대조할 수 있게 되면 요청 #4 를 봐 주십시오.

---

## 요청 #1 — `veo.api.app` 에 reports 라우터 마운트

**상태:** 열림
**대상 파일:** `apps/api/src/veo/api/app.py` (이 작업자의 편집 범위 밖)
**우선순위:** 중간

`veo/reports/router.py` 의 `router` 는 **의도적으로 마운트하지 않았습니다.**
테스트는 `create_app()` 에 라우터를 붙여 실제 오류 핸들러를 통과시키는 방식으로
검증합니다(`tests/reports/conftest.py`).

```python
from veo.reports.router import router as reports_router
...
app.include_router(reports_router, prefix=settings.api_prefix)
```

마운트하면 `openapi.json` 이 바뀌므로 계약 테스트 재생성이 함께 필요합니다.

추가되는 경로:

| 메서드 | 경로 | 권한 |
| --- | --- | --- |
| POST | `/reports` | `REPORT_READ` + `SCAN_RUN` |
| POST | `/reports/{report_id}/versions` | `REPORT_READ` + `SCAN_RUN` |
| GET | `/reports/{report_id}/versions` | `REPORT_READ` |
| GET | `/reports/{report_id}/versions/{version_number}` | `REPORT_READ` |
| GET | `/reports/{report_id}/versions/{version_number}/export` | `REPORT_READ` + `REPORT_EXPORT` |

`EVIDENCE_READ` 는 라우트 의존성이 **아닙니다.** 권한이 없는 호출자는 403 이 아니라
원문 발췌만 빠진 리포트를 200 으로 받습니다(`test_a_caller_without_evidence_read_gets_full_scores_and_no_excerpts`).

---

## 요청 #2 — `report_versions` 불변성을 DB 트리거로 승격

**상태:** 열림
**대상 파일:** `alembic/**` (이 작업자의 편집 범위 밖)
**우선순위:** 높음

`ReportVersion` 은 `ImmutableMixin` 이지만, 이는 `updated_at` 컬럼이 없다는 뜻일 뿐
**DB 가 UPDATE 를 막지는 않습니다.** 확인했습니다 — 마이그레이션에 트리거가 없습니다.

**현재 대응:** `reports/repository.py` 에 SQLAlchemy `before_update` 리스너를 걸어
`report_versions` 에 대한 모든 UPDATE 를 `ReportVersionImmutableError` 로 거부합니다
(`test_a_stored_version_cannot_be_edited`, `test_even_a_harmless_looking_field_cannot_be_edited`).

**이 대응의 한계 — 정직하게 적습니다:**

- ORM 을 거치지 않은 `UPDATE report_versions SET ...` 는 **막지 못합니다.**
- 리스너는 `veo.reports.repository` 를 import 해야 등록됩니다. 다른 모듈이 이
  패키지를 거치지 않고 `ReportVersion` 을 수정하면 보호가 없습니다.

**요청:**

```sql
CREATE OR REPLACE FUNCTION veo_reject_report_version_update()
RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION '발행된 리포트 버전은 수정할 수 없습니다 (id=%)', OLD.id;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER report_versions_are_immutable
BEFORE UPDATE ON report_versions
FOR EACH ROW EXECUTE FUNCTION veo_reject_report_version_update();
```

같은 이유로 `ai_answers`, `observation_runs`, `citations`, `entity_mentions`,
`audit_logs` 에도 필요해 보이지만 그쪽은 이 작업자의 판단 범위가 아닙니다.

트리거가 들어오면 `repository.py` 의 리스너는 그대로 두겠습니다 — 파이썬 쪽에서
먼저 실패하는 편이 오류 메시지가 낫고, 두 겹이 서로를 대체하지 않습니다.

---

## 요청 #3 — 리포트 발행 권한 결정 (`REPORT_WRITE` 부재)

**상태:** 열림
**대상 파일:** `apps/api/src/veo/authz/permissions.py` (이 작업자의 편집 범위 밖)
**우선순위:** 중간

권한 매트릭스에는 `REPORT_READ` 와 `REPORT_EXPORT` 만 있고 **발행 권한이 없습니다.**

**현재 판단:** 버전 발행에 `REPORT_READ` + `SCAN_RUN` 을 요구했습니다. 근거는
"버전은 측정 기록이고, 측정을 실행할 수 없는 사람이 측정 기록을 발행할 수는 없다"
입니다. 결과적으로 `ANALYST`·`DEVELOPER` 는 발행할 수 있고 `SALES_VIEWER`·
`CLIENT_VIEWER` 는 못 합니다(`test_a_reader_without_run_permission_cannot_create_a_version`).

`DEVELOPER` 가 고객 리포트를 발행할 수 있는 것이 의도와 다르면 `REPORT_WRITE`
(또는 `REPORT_GENERATE`) 를 추가해 주십시오. 추가되면 `router.py` 의 의존성 한 줄만
바꾸면 됩니다.

---

## 요청 #4 — run_id 기반 발행으로 전환할지 결정

**상태:** 열림
**대상 파일:** 결정 사항 (구현은 이 작업자 범위)
**우선순위:** 중간

스캔 실행이 저장되기 시작하면 `POST /reports` 본문은 지금의 통짜 진단 페이로드
대신 `{"project_id": ..., "run_ids": [...]}` 로 줄어들 수 있습니다. 그 편이
낫다고 봅니다 — 지금 구조는 **클라이언트가 보낸 숫자를 그대로 동결**하므로,
클라이언트가 잘못 보낸 숫자도 그대로 동결됩니다.

**지금 방어하고 있는 것과 못 하는 것:**

- 방어함 — 스냅샷은 content hash 로 봉인되고, 저장 후 변조는 읽을 때 발견됩니다
  (`ReportTamperedError`). 측정 조건이 다른 두 점수는 빼지 않습니다.
- 방어 못 함 — 애초에 **틀린 숫자를 보내는 것**. 서버는 그 숫자가 실제 스캔에서
  나왔는지 확인할 방법이 지금 없습니다. `SCAN_RUN` 권한 요구가 유일한 방어선입니다.

이것이 이 모듈에서 가장 큰 미해결 위험입니다.

---

## 요청 #5 — `report_versions` 공개 링크 컬럼의 주인이 없습니다

**상태:** 열림 (알림)
**대상 파일:** 결정 사항

`report_versions.public_token_hash` 와 `public_expires_at` 은 **쓰지 않았습니다.**
공개 공유 링크는 인증 없는 표면이라 auth 쪽 설계(토큰 발급·만료·폐기·감사)와
맞물리고, 이 작업자가 단독으로 정할 사안이 아니라고 판단했습니다. 두 컬럼은
NULL 로 남습니다. 담당이 정해지면 알려 주십시오 — 구현은 이 패키지 안에서
가능합니다.

---

## 요청 #6 — `reports.audience` 와 실제 동작의 차이

**상태:** 알림 (변경 요청 아님)

`reports.audience` 는 `BUSINESS | MARKETING | DEVELOPER` **한 값**을 가집니다.
그런데 한 버전은 세 관점을 **모두** 담습니다. 하나의 측정을 세 번 렌더링하면
세 문서가 서로 다른 숫자를 말할 수 있기 때문입니다 — 그 위험을 막는 것이 이
모듈의 존재 이유입니다.

그래서 `audience` 는 **기본 관점(어느 화면을 먼저 펼칠지)** 으로만 쓰고, 응답에는
`views.executive` / `views.marketing` / `views.developer` 가 항상 함께 나갑니다.
컬럼의 의도가 "이 리포트는 경영진용만이다" 였다면 알려 주십시오.

---

## 요청 #7 — PDF 는 만들지 않았습니다 (의존성 추가 요청 아님)

**상태:** 알림

PDF 렌더러(`weasyprint`, `reportlab` 등)는 설치되어 있지 않고, 새 의존성은 요청
사항이므로 추가하지 않았습니다.

**대신:** `render/html.py` 가 **인쇄를 전제로 한 단일 HTML 파일**을 만듭니다.
외부 자원을 하나도 참조하지 않고(`test_the_html_references_no_external_url_at_all`),
`@media print` 로 페이지 나눔·표 분리 방지를 지정했습니다. 브라우저의
"PDF 로 저장"이 그대로 배포 가능한 문서를 만듭니다.

한국어 폰트를 **임베드하지 않았습니다.** 시스템 폰트 스택으로 지정했으므로,
한글 폰트가 없는 환경에서 인쇄하면 글자가 깨질 수 있습니다. 폰트를 base64 로
넣으면 파일이 수 MB 가 되고, 폰트 라이선스는 이 작업자가 판단할 사안이 아닙니다.
필요하다고 판단되면 알려 주십시오.

---

## 요청 #8 — XLSX 의존성 (권고: 추가하지 않아도 됨)

**상태:** 알림

`openpyxl` 과 `xlsxwriter` 모두 없습니다(확인함). `veo/keywords/export.py` 가
이미 표준 라이브러리만으로 최소 OOXML 워크북을 만들고 있어 **같은 방식을 따랐습니다**
(`render/xlsx.py`). 시트 1개, inline string, 서식 없음.
`test_the_xlsx_is_a_valid_readable_ooxml_package` 가 zip 구성과 모든 파트의 XML
파싱을 검사합니다.

**한계:** 키워드 작업자와 동일합니다 — **실제 Excel / LibreOffice / 넘버스에서
열어 본 적이 없습니다.** 자동 검증은 zip 구조와 XML 파싱까지입니다.

---

## 요청 #9 — 테스트 헬퍼 모듈 이름을 `report_support.py` 로 지었습니다

**상태:** 알림

`tests/seo/support.py` 와 `tests/geo/support.py` 가 이미 있고, 루트 `conftest.py`
가 모든 하위 디렉터리를 `sys.path` 에 올리기 때문에 `tests/reports/support.py` 는
**이름이 충돌해 다른 스위트의 모듈로 해석됩니다**(실제로 그렇게 깨졌습니다).
같은 이유로 `conftest` 도 직접 import 할 수 없어, 라우터 테스트가 공유하는
`Tenant` · `REPORTS` · `API_PREFIX` 는 `report_support.py` 에 두었습니다.

키워드 작업자의 요청 #8(`--import-mode=importlib` 를 `apps/api/pyproject.toml` 에도
추가)이 처리되면 이 우회는 불필요해집니다. 레포 루트 `pytest.ini` 에는 이미
들어 있어서 루트에서 돌리면 정상 수집됩니다.

---

# 부록 A — 이 모듈이 보장하는 것과 보장하지 못하는 것

정직하게 적습니다.

## 보장하는 것 (테스트로 고정됨)

1. **발행된 버전은 ORM 을 통해 수정되지 않습니다.** 시도하면 flush 가 실패합니다.
2. **같은 숫자는 세 관점·세 형식에서 완전히 같은 문자열로 나옵니다.** 구조적으로
   그렇습니다 — 스냅샷이 `metrics` 라는 **평평한 목록 하나**에 모든 수치를 담고,
   관점과 렌더러는 그중 일부를 **고르기만** 합니다. 사본이 없으므로 어긋날 수
   없습니다(`test_every_metric_a_view_shows_is_the_identical_row_from_the_snapshot`).
3. **`측정 불가` · `해당 없음` 은 그 자체로 표기되고 사유가 붙습니다.** `MeasuredValue`
   가 숫자 없는 값에 사유를 강제하고, 상태가 `MEASURED` 가 아닌 값에 숫자를 담지
   못하게 막습니다. 표 형식에서 숫자 칸은 빈 칸이고, 바로 옆 칸이 `측정 불가` 라고
   말합니다. 0 이 되는 경로가 없습니다.
4. **HTML 은 외부 URL 을 전혀 참조하지 않습니다.** 테스트가 HTML 을 파싱해
   `src`·`href`·`srcset` 등 브라우저가 실제로 요청하는 속성 전부를 검사합니다.
   측정 대상 URL 은 링크가 아니라 **텍스트**로 찍습니다.
5. **`EVIDENCE_READ` 없는 호출자는 점수를 전부 받고 원문만 못 받습니다.** 403 이
   아닙니다. 근거의 존재·종류·URL·내용 해시는 남고 발췌만 빠집니다.
6. **다른 조직의 리포트는 404 입니다.** 403 이 아닙니다.
7. **모든 내보내기가 방법론 버전과 체크섬을 적습니다.** CSV·XLSX 는 행마다
   `report_methodology` 열에, HTML 은 머리글과 공시 블록에 적습니다.
8. **측정 조건이 다른 두 점수는 빼지 않습니다.** 경쟁사 격차와 이전 버전 대비
   변화량 모두 `veo.compare.conditions` 를 통과해야만 계산되고, 막히면 `측정 불가`
   와 **차단 사유 원문**이 남습니다.

## 보장하지 못하는 것

1. **클라이언트가 보낸 숫자의 진위** (요청 #4). 서버는 그 숫자가 실제 스캔에서
   나왔는지 확인할 수 없습니다.
2. **ORM 밖의 UPDATE** (요청 #2). DB 트리거가 필요합니다.
3. **XLSX 를 실제 스프레드시트 앱에서 열어 본 것** (요청 #8).
4. **한국어 폰트가 없는 환경의 인쇄 품질** (요청 #7).
5. **스냅샷 포맷 변경 시의 하위 호환.** `format_version` 필드를 넣어 두었지만
   마이그레이션 경로는 아직 없습니다. 지금 포맷을 바꾸면 기존 버전은
   `ReportSnapshot.model_validate` 에서 실패합니다 — 조용히 잘못 읽히는 것보다
   낫다고 판단했으나, 포맷을 바꿔야 할 때가 오면 변환기가 필요합니다.
6. **동시 발행 경합.** `UniqueConstraint(report_id, version_number)` 가 막고 409 로
   돌려주지만, 재시도는 클라이언트 몫입니다.

---

# 부록 B — 스냅샷 안에서 숫자가 사는 곳

리뷰할 때 가장 먼저 확인해야 할 구조입니다.

```
ReportSnapshot
├── metrics: [MetricRow, ...]      ← 이 리포트의 모든 숫자. 사본 없음.
│     └── value: MeasuredValue     ← 숫자 또는 (사유 + 측정 불가/해당 없음)
├── provenance: {key: Provenance}  ← 각 숫자가 가리키는 출처·명세·측정 조건
├── domains: [DomainSnapshot]      ← 구조. 숫자는 안 갖고 metric_key 로 가리킴
├── competitors: [...]             ← 비교. 조건 차이 원문을 함께 보관
└── changes: [...]                 ← 이전 버전 대비. 조건이 다르면 계산 안 함
```

`DomainSnapshot.categories[i]` 는 점수를 **갖지 않고** `metric_key` 를 갖습니다.
숫자의 사본을 하나 더 만드는 순간 두 값이 갈라질 수 있기 때문입니다. 리뷰에서
이 규칙을 깨는 변경을 발견하면 그것이 이 모듈의 유일한 치명적 결함 유형입니다.
