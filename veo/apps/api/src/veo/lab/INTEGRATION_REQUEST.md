# VEO-LAB — 통합 요청 (Integration Requests)

`veo.lab`는 VEO-LAB이 측정 방법론(점수 명세)을 관리하는 워크플로입니다. 이 패키지는
`veo.api.app`을 건드리지 않으므로, 아래 항목은 통합 담당자의 확인이 필요합니다.

---

## 1. 라우터 마운트 (필수)

`veo.lab.router.router`는 어디에도 마운트되어 있지 않습니다.

```python
# veo/api/app.py
from veo.lab.router import router as lab_router
...
app.include_router(lab_router, prefix=api_prefix)
```

- 경로 접두사: `/lab/scoring-versions`
- 태그: `lab`
- `tests/contract/test_router_mounting.py::EXPECTED_MOUNTS`에
  `"lab": "/api/lab/scoring-versions"` 추가가 필요합니다.
- 마운트하면 `openapi.json`이 변경되므로 `scripts/export_openapi.py` 재실행과
  `packages/shared-types` 재생성이 함께 필요합니다.

현재는 `apps/api/tests/lab/conftest.py`가 `create_app()` 뒤에 이 라우터를 직접
포함시켜 테스트합니다. 통합 후에는 그 fixture에서 `include_router` 한 줄을 지우면
됩니다.

## 2. 예외 핸들러 (선택, 권장)

`veo.lab.errors.LabError` 하위 예외는 모두 라우터 안에서 HTTP로 번역됩니다
(`_translated`). 다른 곳(워커, 관리 명령)에서 이 서비스를 호출할 계획이 있다면
애플리케이션 수준 핸들러로 옮기는 편이 낫습니다. 매핑은 다음과 같습니다.

| 예외 | 상태 | ErrorCode |
| --- | --- | --- |
| `VersionNotFoundError` | 404 | `NOT_FOUND` |
| `ChecksumMismatchError` | 409 | `CONFLICT` (+ `veo.lab` 로거에 error 기록) |
| `ImmutableVersionError` | 409 | `CONFLICT` |
| `IllegalTransitionError` | 409 | `CONFLICT` |
| `GoldenFixtureError` | 409 | `CONFLICT` |
| `DuplicateVersionError` | 409 | `CONFLICT` |
| `SpecificationRejectedError` | 422 | `SCORING_SPEC_INVALID` |

## 3. 스키마 변경 요청 — 없음

`ScoringVersion`과 `ScoreResult`의 컬럼만으로 충분했습니다. 마이그레이션 요청은
없습니다. 다만 운영에 들어가기 전에 검토를 권하는 것이 두 가지 있습니다.

1. **`scoring_versions`에 `PUBLISHED` 유일성 제약이 없습니다.** 서비스가 발행 시
   같은 `spec_id`의 기존 발행본을 자동으로 `RETIRED` 처리하지만, 이는 애플리케이션
   레벨 보장입니다. 부분 유니크 인덱스
   (`UNIQUE (spec_id) WHERE status = 'PUBLISHED'`)가 있으면 구조적으로 보장됩니다.
2. **`scoring_versions` 행은 DB 권한으로는 여전히 UPDATE 가능합니다.** 불변성은
   서비스 경계에서만 강제됩니다. 아래 5번 항목을 참고해 주세요.

## 4. 골든 픽스처 위치

`veo.lab.golden.golden_directory()`는 `veo.scoring.find_specs_root() / "golden"`을
읽습니다. 즉 `VEO_SCORING_SPECS_DIR` 환경변수가 골든 픽스처의 위치도 함께
결정합니다. 배포 환경에서 이 변수를 쓰고 있다면, 해당 디렉터리에 `golden/`이
포함되어 있어야 발행이 가능합니다(픽스처가 0건이면 발행이 차단됩니다).

## 5. 남는 위험 — 발행된 방법론이 새 버전 없이 바뀔 수 있는 경로

설계상 막았지만, 이 패키지 바깥에 남아 있는 경로입니다. 통합 담당자가 알고
있어야 합니다.

1. **데이터베이스 직접 UPDATE.** `veo.lab.service`를 거치지 않고
   `scoring_versions.specification`을 바꾸면 저장된 문서는 바뀝니다. 다만
   `checksum` 컬럼까지 함께 고치지 않는 한, 그 행을 읽는 모든 경로가
   `ChecksumMismatchError`로 거부합니다(테스트로 고정되어 있습니다). 체크섬까지
   같이 고치면 탐지되지 않습니다 — 이는 DB 쓰기 권한 관리 문제이며, 애플리케이션
   레벨에서 더 막을 수 없습니다. 운영 DB의 쓰기 계정 분리를 권합니다.
2. **`packages/scoring-specs/` 파일 수정.** 디스크의 발행본은 이 워크플로 바깥에
   있고 `veo.scoring.load_spec`이 그대로 읽습니다. 여기서 YAML을 고치면 새 버전
   없이 방법론이 바뀝니다. 저장소 차원의 CODEOWNERS/보호 규칙이 필요합니다.
3. **골든 픽스처 수정.** 기대값을 후보에 맞춰 고치면 발행 게이트를 통과할 수
   있습니다. 이는 의도된 동작입니다(방법론을 바꾸면 기대값도 바뀌므로) — 다만
   그 수정이 리뷰되는 변경이어야 합니다. 위 2번과 같은 보호가 필요합니다.
