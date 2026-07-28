# VEO API 계약

계약의 원본은 `apps/api/openapi.json`입니다. 이 문서는 그 계약을 읽는 규칙을 설명합니다.

## 생성물과 drift 검사

세 가지 산출물이 서로 어긋나면 빌드가 실패합니다.

| 산출물 | 원천 | 재생성 | 검사 |
|---|---|---|---|
| `apps/api/openapi.json` | FastAPI 앱 | `python scripts/export_openapi.py` | `--check` |
| `packages/shared-types/src/enums.ts` | `veo/contracts/enums.py` | `python scripts/export_shared_types.py` | `--check` |
| `packages/api-client/src/schema.d.ts` | `openapi.json` | `pnpm --filter @veo/api-client generate` | `pnpm --filter @veo/api-client check` |

생성물은 손으로 고치지 않습니다.

## 공통 응답 형태

성공:

```json
{
  "data": { },
  "error": null,
  "meta": {
    "request_id": "…",
    "generated_at": "2026-07-28T02:00:00Z",
    "sources": [],
    "scoring_spec_id": "veo.seo.readiness",
    "scoring_spec_version": "1.0.0",
    "scoring_spec_checksum": "…"
  }
}
```

실패도 **같은 봉투**를 씁니다:

```json
{
  "data": null,
  "error": {
    "code": "TARGET_URL_REJECTED",
    "message": "요청하신 주소는 검사할 수 없습니다.",
    "field_errors": [],
    "retryable": false,
    "retry_after_seconds": null,
    "internal_error_ref": "…"
  },
  "meta": { "request_id": "…", "generated_at": "…", "sources": [] }
}
```

- `code`는 기계용이며 번역하지 않습니다. `message`는 고객에게 그대로 보여도 안전한
  한국어입니다.
- 민감한 내용은 `message`에 담지 않고 `internal_error_ref`로 서버 로그와 연결합니다.
- `retryable`은 `RETRYABLE_ERROR_CODES`에서 자동 결정됩니다.

## 상관 ID

- 요청 헤더 `X-Request-Id`를 보내면 그대로 사용합니다. 단 **8–64자 영숫자·하이픈**만
  허용하고, 그 밖의 값은 무시하고 서버가 새로 만듭니다. 헤더를 통한 내용 주입을
  막기 위해서입니다.
- 응답 헤더와 `meta.request_id`는 **항상 같은 값**입니다.

## 페이지네이션

목록 응답은 `PagedResponse`를 씁니다: `data`(배열), `page_info`
(`page`, `page_size`, `total_items`, `total_pages`, `has_next`, `has_previous`), `meta`.
`page_size` 상한은 200입니다.

## 출처 표기

외부에서 온 값에는 `meta.sources[]`가 붙습니다: `source`, `provider_state`,
`collected_at`, `source_period`, `api_version`, `raw_response_hash`, `cache_hit`.

네이버 SearchAd(절대 검색량)와 DataLab(상대 지수)은 **서로 다른 `source`** 이며
같은 필드에 담기지 않습니다.

## 현재 엔드포인트 (Phase 0)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/health` | 서비스 상태와 제품 표기 |
| GET | `/api/providers` | 외부 제공자 연동 상태. 자격증명이 없으면 그대로 보고 |
| GET | `/api/scoring/specs` | 발행된 점수 명세 목록 |
| GET | `/api/scoring/specs/{spec_id}/{version}` | 배점·심각도·상한·게이트 전문 |
| POST | `/api/scoring/evaluate` | 검사 결과를 명세에 대입해 점수를 재현 |

## 다음 단계에서 추가될 엔드포인트

계약만 확정하고 구현은 각 Phase에서 진행합니다. 아직 없는 엔드포인트를
자리표시자 응답으로 만들어 두지 않습니다.

- Phase 1: `auth`, `users`, `roles`, `organizations`, `customers`, `projects`, `sites`
- Phase 2: `POST /api/public/v1/seo-scans`, `geo-readiness-scans`, `keyword-lookups`,
  `GET /api/public/v1/jobs/{job_id}`, `GET /api/public/v1/results/{token}`, `leads`
- Phase 3: `issues`, `fixes`, `verifications`, `reports`, `scoring-versions`
- Phase 4: `prompt-sets`, `observations`, `citations`, `competitors`, `api-usage`

## API 변경 절차

1. 계약(스키마·라우트)을 바꾼다.
2. `python scripts/export_openapi.py`
3. `pnpm --filter @veo/api-client generate`
4. 계약 테스트 실행: `pytest apps/api/tests/contract`
5. 호환성이 깨지는 변경이면 ADR을 추가하고 버전 전략을 명시한다.

생성물 갱신 없이는 병합하지 않습니다.
