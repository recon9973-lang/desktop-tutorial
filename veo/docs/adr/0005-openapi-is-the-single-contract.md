# ADR 0005 — OpenAPI 문서가 유일한 API 계약이다

- 상태: 채택
- 일자: 2026-07-28

## 배경

프론트엔드와 백엔드를 병렬로 개발하려면 양쪽이 같은 계약을 봐야 한다. 계약이
문서와 코드에 따로 존재하면 둘은 반드시 어긋난다.

## 결정

- `apps/api/openapi.json`을 저장소에 커밋한다. FastAPI 앱이 진실의 원천이고,
  `scripts/export_openapi.py`가 문서를 내보낸다.
- `packages/api-client/src/schema.d.ts`는 그 문서에서 생성한다. 손으로 고치지 않는다.
- `packages/shared-types/src/enums.ts`는 `veo/contracts/enums.py`에서 생성한다.
- 세 가지 drift 검사가 CI와 로컬 게이트에 들어간다:
  `export_openapi.py --check`, `export_shared_types.py --check`,
  `pnpm --filter @veo/api-client check`.

## 결과

- API를 바꾸고 생성물을 갱신하지 않으면 테스트가 실패한다.
- 프론트엔드는 백엔드 구현을 기다리지 않고 타입에 맞춰 개발할 수 있다.
