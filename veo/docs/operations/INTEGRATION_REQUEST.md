# 통합 요청 (인프라 → 애플리케이션 소유자)

Phase 0 인프라 작업 중 발견한, **인프라 담당이 직접 고칠 수 없는** 항목입니다.
`apps/**`, `packages/**`, `tests/**` 는 인프라 워커의 수정 대상이 아니므로
여기에 요청으로 남깁니다.

상태 표기: `열림` / `처리중` / `완료` / `보류`

---

## 요청 #1 — `uvicorn` 을 `apps/api` 의존성에 추가

**상태:** 열림
**대상 파일:** `apps/api/pyproject.toml`
**우선순위:** 높음 (api 컨테이너가 뜨지 못함)

### 문제

`apps/api/pyproject.toml` 의 `dependencies` 에 `fastapi` 는 있지만 ASGI 서버가
없습니다. FastAPI 는 프레임워크일 뿐이라 이것만으로는 프로세스를 띄울 수
없습니다.

### 임시 조치

`infra/docker/api.Dockerfile` 빌더 단계에서 별도로 설치하고 있습니다.

```dockerfile
RUN pip install "uvicorn[standard]<1.0"
```

이건 **의존성 관리가 두 군데로 갈라진 상태**라 바람직하지 않습니다.
`pyproject.toml` 이 더 이상 실행 환경의 진실이 아니게 되고,
`pip-audit` 이 감사하는 트리와 실제 이미지 내용이 어긋납니다.

### 요청

```toml
dependencies = [
    ...
    "uvicorn[standard]>=0.30,<1.0",
]
```

반영되면 `api.Dockerfile` 의 별도 설치 줄을 지우겠습니다.

---

## 요청 #2 — FastAPI 애플리케이션 진입점 확정

**상태:** 열림
**대상 파일:** `apps/api/src/veo/api/` (신규 모듈)
**우선순위:** 높음 (api 컨테이너가 뜨지 못함)

### 문제

라우터는 있는데(`veo.api.routes.meta`, `veo.api.routes.scoring`) 이들을 묶는
`FastAPI` 애플리케이션 객체가 없습니다. 컨테이너의 실행 명령이 가리킬 대상이
없는 상태입니다.

### 임시 조치

경로를 환경변수로 빼서 이미지 재빌드 없이 바꿀 수 있게 했습니다.

```dockerfile
ENV VEO_ASGI_APP=veo.api.app:app
CMD ["sh", "-c", "exec uvicorn \"$VEO_ASGI_APP\" --host ... --port ..."]
```

### 요청

1. 애플리케이션 객체의 모듈 경로를 확정해 주세요.
   기본값을 `veo.api.app:app` 으로 잡아두었습니다. 다르면 알려주시면
   `.env.example` 과 Dockerfile 기본값을 맞추겠습니다.
2. **헬스 엔드포인트의 최종 경로**를 알려주세요.
   `veo.api.routes.meta` 의 라우터에는 prefix 가 없어 `/health` 지만,
   `settings.api_prefix`(`/api`) 아래에 마운트하면 `/api/health` 가 됩니다.
   컨테이너 HEALTHCHECK 가 이 경로를 칩니다.
   현재 기본값: `VEO_HEALTHCHECK_PATH=/health`
3. 팩토리 함수 형태(`create_app()`)로 만들 거라면 알려주세요.
   `uvicorn --factory` 플래그가 필요합니다.

---

## 요청 #3 — Celery 애플리케이션 모듈 확정

**상태:** 열림
**대상 파일:** `apps/api/src/veo/worker/` (신규) 또는 `apps/worker/`
**우선순위:** 중간

### 문제

`celery` 는 의존성에 있지만 Celery 앱 인스턴스가 없습니다.
`apps/worker/` 디렉터리는 비어 있습니다.

### 임시 조치

`infra/docker/worker.Dockerfile` 이 `veo.worker.app` 을 가정하고 있습니다.

```dockerfile
CMD ["--app", "veo.worker.app", "worker", "--hostname", "celery@veo-worker", ...]
```

### 요청

1. Celery 앱의 모듈 경로를 확정해 주세요.
2. 워커 이미지는 `apps/api` 패키지를 설치해 `veo.*` 를 씁니다.
   워커 코드를 `apps/worker/` 에 별도 파이썬 패키지로 둘 계획이면
   알려주세요. Dockerfile 의 설치 대상을 바꿔야 합니다.
3. `VEO_CELERY_BROKER_URL` / `VEO_CELERY_RESULT_BACKEND` 를 읽도록
   해주세요(`.env.example` §5). 비어 있으면 `VEO_REDIS_URL` 로 대체하는
   동작을 전제로 compose 를 구성했습니다.

---

## 요청 #4 — 설정 이름 규칙 확인

**상태:** 열림
**대상 파일:** `apps/api/src/veo/core/settings.py`
**우선순위:** 중간 (결정만 필요)

### 상황

`Settings` 와 `ProviderCredentials` 가 `env_prefix="VEO_"` 를 쓰므로
실제 환경변수 이름은 이렇게 됩니다.

| 흔히 기대하는 이름 | 실제로 읽는 이름 |
|---|---|
| `DATABASE_URL` | `VEO_DATABASE_URL` |
| `REDIS_URL` | `VEO_REDIS_URL` |
| `OPENAI_API_KEY` | `VEO_OPENAI_API_KEY` |
| `NAVER_SEARCHAD_API_KEY` | `VEO_NAVER_SEARCHAD_API_KEY` |
| `GOOGLE_PAGESPEED_API_KEY` | `VEO_GOOGLE_PAGESPEED_API_KEY` |

`.env.example` 은 **코드가 실제로 읽는 이름**(`VEO_` 접두사)으로 작성했습니다.
읽히지 않는 이름을 예시로 두면 조용히 무시되는 설정이 생기고, 그게 가장
찾기 어려운 버그이기 때문입니다.

### 확인 요청

- 이 접두사 규칙을 유지한다면 그대로 두겠습니다.
- 일부(특히 `DATABASE_URL`)를 관례적인 무접두사 이름으로도 받고 싶다면
  `Settings` 에 alias 를 추가해 주세요. 인프라 쪽에서 이름을 바꾸는 것으로는
  해결되지 않습니다.

`GOOGLE_APPLICATION_CREDENTIALS` 는 예외입니다. 이건 구글 SDK 자체가 읽는
표준 변수라 접두사를 붙이면 안 됩니다. 현재 설정은 대신
`VEO_GOOGLE_SEARCH_CONSOLE_CREDENTIALS_JSON` 을 쓰고 있어 `.env.example` 도
그쪽으로 맞췄습니다. 나중에 구글 SDK 를 직접 쓰게 되면 별도로 정리가 필요합니다.

---

## 요청 #5 — `apps/web/next.config.ts` 에 `output: "standalone"` 추가

**상태:** 열림
**대상 파일:** `apps/web/next.config.ts`
**우선순위:** 중간 (web 이미지가 빌드되지 않음)

### 문제

`infra/docker/web.Dockerfile` 은 Next.js 의 standalone 출력을 전제로
`.next/standalone` 을 복사합니다. 현재 `next.config.ts` 에 `output` 설정이
없어서 그 디렉터리가 생성되지 않고, 이미지 3단계의 `COPY` 가 실패합니다.

확인한 현재 상태:

```
apps/web/next.config.ts   → output 설정 없음
apps/web/.next/standalone → 존재하지 않음
```

### 요청

```ts
const nextConfig: NextConfig = {
  output: 'standalone',       // ← 추가
  reactStrictMode: true,
  transpilePackages: ['@veo/ui'],
  poweredByHeader: false,
  turbopack: { root: path.join(import.meta.dirname, '..', '..') },
};
```

standalone 출력은 필요한 `node_modules` 만 추려 담기 때문에 이미지 크기가
크게 줄고, 런타임에 pnpm 이나 워크스페이스 해석이 필요 없어집니다.

### 참고 — 워크스페이스 매니페스트는 해결됨

이 요청을 처음 적을 때는 워크스페이스 파일이 없었는데, 그 사이에 들어왔습니다.
`web.Dockerfile` 의 `deps` 단계가 요구하는 파일은 이제 전부 있습니다.

- `package.json`, `pnpm-workspace.yaml`, `pnpm-lock.yaml` (루트)
- `apps/web/package.json`

다만 `apps/web/` 안에 `pnpm-workspace.yaml` 과 `pnpm-lock.yaml` 이 **중복으로**
존재합니다. 워크스페이스 루트가 두 곳으로 해석될 수 있어 빌드가 환경에 따라
다르게 동작할 수 있습니다. 의도한 것이 아니라면 정리해 주세요.

---

## 요청 #6 — 자동 생성 마이그레이션 파일을 ruff 의 E501 대상에서 제외

**상태:** 열림
**대상 파일:** `apps/api/pyproject.toml` (`[tool.ruff]` 섹션)
**우선순위:** 높음 (`make ci-local` 을 막는 유일한 항목)

### 문제

`make ci-local` 이 lint 단계에서 실패합니다. 실측 결과, **오류 252건이 전부
한 파일의 `E501`(줄 길이 초과)** 입니다.

```
apps/api/alembic/versions/20260728_0241_initial_veo_schema.py    E501 × 252
```

이 파일은 `alembic revision --autogenerate` 가 만든 것입니다. autogenerate 는
`sa.Column(...)` 한 줄에 타입·제약·기본값을 몰아 쓰기 때문에 100자를 넘는 것이
정상 동작입니다. 사람이 손으로 줄바꿈을 넣어봐야 다음 autogenerate 에서
다시 원복됩니다.

즉 **이건 코드 결함이 아니라 린터 설정의 문제**이고, 지금 상태로 두면
"CI 는 원래 빨간색"이라는 인식이 굳어져 게이트가 무력화됩니다.

### 요청

`apps/api/pyproject.toml` 에 아래를 추가해 주세요.

```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S105", "S106", "S311"]
"alembic/versions/**" = ["E501"]      # ← 추가: 자동 생성 파일의 줄 길이는 검사하지 않는다
```

`E501` 만 끄는 것이 핵심입니다. 파일 전체를 `exclude` 하면 마이그레이션에
들어간 실제 문제(예: 위험한 import)까지 놓칩니다.

### 참고 — 나머지 검사는 현재 전부 통과합니다

| 검사 | 결과 (실측) |
|---|---|
| `make lint-api` | **실패** — E501 252건 (위 항목) |
| `make typecheck-api` | **통과** — 32개 파일, 오류 없음 |
| `make test-api` | **통과** — 824 passed, 4 skipped |
| `make test-db` | **통과** — 4개 테스트, 37개 테이블 up/down/재적용 검증 |
| `make test-contract` | 테스트 없음 (건너뜀) |

위 한 줄만 반영되면 `make ci-local` 이 통과 상태가 됩니다.

---

## 요청 #7 — JWT 무중단 교체를 위한 검증 키 목록 (낮음)

**상태:** 보류
**대상 파일:** `apps/api/src/veo/core/settings.py`

현재 `jwt_secret` 이 단일 값이라 교체하면 발급된 모든 토큰이 무효가 되고
전원 재로그인이 필요합니다(`runbook-credential-rotation.md` §2.2).

무중단 교체가 필요해지면 "서명은 현재 키, 검증은 현재+이전 키" 구조가
필요합니다. 지금 당장 필요한 기능은 아니라 보류로 둡니다.
운영 사용자가 늘어난 뒤 다시 판단하면 됩니다.
