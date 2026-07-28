# VEO 로컬 개발 환경

VEO 를 내 컴퓨터에서 띄우고, 고치고, 검증하는 방법입니다.

두 갈래가 있습니다.

- **A. Docker 없이** — 지금 이 프로젝트의 기본 경로입니다. 실제로 검증했습니다.
- **B. Docker 로** — 전체 스택(Postgres·Redis·MinIO·API·워커·웹)을 한 번에 띄웁니다.
  **현재 개발 장비에는 Docker 가 설치돼 있지 않아 실행 검증을 하지 못했습니다.**
  자세한 내용은 맨 아래 "알려진 한계"를 읽어주세요.

---

## 0. 준비물

| 도구 | 필요 버전 | 현재 장비에서 확인된 값 |
|---|---|---|
| Python | 3.12 이상 | 3.14.6 |
| PostgreSQL | 16 | 16.14 (Homebrew) |
| Node.js | 22 이상 | 26.4.0 |
| pnpm | 9 이상 | 11.10.0 |
| Redis | 7 | **미설치** |
| Docker | 24 이상 + Compose v2.20 이상 | **미설치** |

`apps/api/pyproject.toml` 은 `requires-python = ">=3.12"` 이고 도구 설정
(ruff·mypy)의 target 은 3.12 입니다. 로컬 가상환경은 3.14 로 만들어져 있고
현재까지 문제없이 동작하지만, CI 는 3.12 로 돌립니다. 즉 **로컬에서 통과한 것이
CI 에서 반드시 통과한다는 보장은 없습니다.** 3.12 전용 문법 차이가 의심되면
`make setup PYTHON=python3.12` 로 가상환경을 다시 만들어 확인하세요.

---

## A. Docker 없이 개발하기 (권장 경로)

### A-1. 최초 설정

```bash
cd veo
make setup
```

`.venv` 를 만들고 `apps/api` 를 개발 의존성까지 포함해 편집 설치(`pip install -e`)합니다.
이미 `.venv` 가 있으면 재사용합니다.

### A-2. 환경변수

```bash
cp .env.example .env
```

`.env.example` 의 주석을 그대로 따라 값을 채웁니다. 중요한 두 가지만 짚습니다.

**(1) 설정 이름에는 `VEO_` 접두사가 붙습니다.**
`apps/api/src/veo/core/settings.py` 의 pydantic-settings 가 `env_prefix="VEO_"` 로
고정돼 있습니다. 그래서 `DATABASE_URL` 은 **읽히지 않고** `VEO_DATABASE_URL` 만
적용됩니다. 흔한 관례라는 이유로 접두사를 빼면 조용히 무시되며, 그게 가장 찾기
어려운 종류의 버그입니다.

**(2) 외부 제공자 키는 비워두는 것이 정상 상태입니다.**
네이버·구글·OpenAI 키가 없어도 VEO 는 정상 동작합니다. 해당 제공자를
`DISABLED_NO_CREDENTIAL` 로 표시하고, 그 제공자에 의존하는 지표를
**UNKNOWN(측정 불가)** 으로 보고합니다. 값을 추정하거나 지어내지 않습니다.
현재 상태는 API 의 `GET /providers` 에서 그대로 확인할 수 있습니다.

### A-3. 검사 돌리기

```bash
make ci-local      # lint → typecheck → 단위 테스트 (푸시 전 필수)
```

개별로는 이렇게 씁니다.

```bash
make lint-api       # ruff check apps/api
make typecheck-api  # mypy
make test-api       # pytest apps/api/tests  (DB 테스트는 skip)
make test-contract  # tests/contract
```

`make ci-local` 이 **현재 이 프로젝트의 실질적인 유일한 게이트**입니다.
`.github/workflows/ci.yml` 은 아직 동작하지 않습니다(아래 "알려진 한계" 참고).

### A-4. 데이터베이스

로컬 PostgreSQL 에 테스트용 DB 를 만듭니다.

```bash
make db-test-create     # veo_test 생성 (이미 있으면 그대로 둠)
make db-test-drop       # veo_test 삭제
```

접속 사용자·호스트를 바꾸려면 변수로 덮어씁니다.

```bash
make db-test-create PGUSER=someone PGPORT=5433 TEST_DB=veo_scratch
```

### A-5. 마이그레이션

Alembic 은 `apps/api/alembic/` 에 있습니다(`infra/` 가 아닙니다. 이유는
`infra/migrations/README.md` 에 적어두었습니다).

```bash
export VEO_DATABASE_URL='postgresql+psycopg://'"$USER"'@localhost:5432/veo'

make migrate            # upgrade head
make migrate-down       # downgrade -1
make migrate-history    # 리비전 이력과 현재 위치
make migrate-revision m="add competitor snapshot table"
```

`make migrate-revision` 은 `--autogenerate` 로 돕니다. **생성된 파일의
`downgrade()` 를 반드시 눈으로 확인하세요.** 자동 생성은 되돌리기를 자주 틀립니다.
되돌릴 수 없는 마이그레이션은 배포 사고 때 롤백 경로를 통째로 막습니다.

### A-6. DB 를 실제로 쓰는 테스트

`make test-api` 는 `VEO_TEST_DATABASE_URL` 을 넘기지 않으므로 DB 테스트가
**skip** 됩니다. **skip 은 통과가 아니라 공백입니다.** 마이그레이션이나 모델을
건드렸다면 반드시 이걸 돌리세요.

```bash
make test-db      # veo_test 를 만들고 requires_postgres 테스트까지 실행
```

이 안에는 모델과 마이그레이션이 어긋났는지 보는 드리프트 검사가 들어 있습니다.
모델만 고치고 마이그레이션을 안 만들면 여기서 잡힙니다.

---

## B. Docker 로 전체 스택 띄우기

```bash
cp .env.example .env     # POSTGRES_PASSWORD, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD 를 채운다
make up                  # docker compose up -d --build
make ps                  # 상태 확인
make logs                # 로그 따라가기
make down                # 종료 (볼륨 유지)
```

데이터까지 지우려면 `docker compose down -v` 를 씁니다.

### 구성

| 서비스 | 이미지 | 호스트 포트 |
|---|---|---|
| postgres | `postgres:16` | `POSTGRES_HOST_PORT` (기본 5432) |
| redis | `redis:7` | `REDIS_HOST_PORT` (기본 6379) |
| minio | `minio/minio:latest` | 9000(API) / 9001(콘솔) |
| api | 로컬 빌드 | `API_HOST_PORT` (기본 8000) |
| worker | 로컬 빌드 | 없음 |
| web | 로컬 빌드 | `WEB_HOST_PORT` (기본 3000) |

호스트에서 이미 PostgreSQL 이 5432 를 쓰고 있으면(이 장비가 그렇습니다)
`.env` 에서 `POSTGRES_HOST_PORT=5433` 처럼 바꿔야 충돌하지 않습니다.

### MinIO 버킷 만들기

컨테이너가 뜬 뒤 `http://localhost:9001` 콘솔에 `MINIO_ROOT_USER` /
`MINIO_ROOT_PASSWORD` 로 로그인해 `VEO_S3_BUCKET`(기본 `veo-artifacts`) 버킷을
만듭니다. 버킷 자동 생성 서비스는 넣지 않았습니다. 스토리지 생성은 조용히
일어나면 안 되는 종류의 작업이라, 사람이 한 번 보고 만들게 두었습니다.

### 렌더러 네트워크 격리 (SSRF 심층 방어)

`infra/docker/docker-compose.yml` 에 `veo-renderer` 네트워크를 미리 만들어
두었습니다. 아직 렌더러 서비스 자체는 없지만, 추가할 때 지킬 규칙은 정해져 있습니다.

Playwright 렌더러는 **고객이 입력한 임의의 URL** 을 실제 브라우저로 엽니다.
즉 적대적인 페이지의 자바스크립트가 렌더러 컨테이너 안에서 실행됩니다.
그 페이지가 `http://postgres:5432`, `http://minio:9000`,
`http://169.254.169.254/`(클라우드 메타데이터) 로 요청을 쏘면 애플리케이션
계층의 URL 검증만으로는 늦습니다.

그래서:

1. 렌더러는 **`veo-renderer` 네트워크에만** 붙습니다. `veo-backend` 에 절대
   붙이지 않습니다. DNS 상으로도 라우팅 상으로도 데이터스토어에 닿지 못합니다.
2. 워커가 양쪽에 걸쳐서 렌더러를 호출합니다. 호출은 워커 → 렌더러 단방향이고,
   렌더러는 DB 자격증명을 전혀 알지 못합니다.
3. 운영에서는 여기에 더해 egress 프록시 allowlist 를 걸고,
   `VEO_URL_BLOCKED_CIDRS` 대역을 방화벽에서 한 번 더 막습니다.
4. **애플리케이션 계층 검증은 그대로 유지합니다.** 네트워크 분리는 그 검증의
   대체재가 아니라 두 번째 방어선입니다. 리디렉션 이후 최종 IP 를 매번 다시
   확인하는 것은 여전히 `veo.common.security.url_guard` 의 책임입니다.

---

## 알려진 한계

솔직하게 적습니다. 여기 적힌 것은 "나중에 하자"가 아니라 **지금 검증되지 않은
사실**입니다.

### 1. Docker 관련 산출물은 전부 미검증입니다

이 장비에 Docker 가 설치돼 있지 않습니다(`docker`, `docker compose` 모두 없음).
따라서 다음은 **한 번도 빌드하거나 실행해 본 적이 없습니다.**

- `infra/docker/api.Dockerfile`
- `infra/docker/worker.Dockerfile`
- `infra/docker/web.Dockerfile`
- `infra/docker/docker-compose.yml`
- `docker-compose.yml`
- `make up` / `make down` / `make logs` / `make ps`

검증한 것은 다음 두 가지뿐입니다.

- compose 파일 2개가 **유효한 YAML** 인지 (`yaml.safe_load` 통과)
- Dockerfile 3개의 **명령어 문법·스테이지 참조·JSON exec 형식** 이 올바른지
  (자체 정적 파서로 확인)

이미지가 실제로 빌드되는지, 컨테이너가 뜨는지, 헬스체크가 통과하는지는
**모릅니다.** Docker 가 있는 환경에서 처음 돌릴 때는 실패를 예상하고 시작하세요.

### 2. Redis 가 설치돼 있지 않습니다

`VEO_TEST_REDIS_URL` 을 필요로 하는 테스트(`requires_redis` 마커)는 이 장비에서
돌려본 적이 없습니다. Celery 워커의 실제 동작도 마찬가지입니다.
설치하려면 `brew install redis && brew services start redis` 입니다.

### 3. GitHub Actions 워크플로가 활성화돼 있지 않습니다

`veo/` 는 현재 더 큰 리포지터리(`desktop-tutorial`)의 하위 디렉터리입니다.
GitHub Actions 는 **리포지터리 루트**의 `.github/workflows/` 만 읽으므로,
`veo/.github/workflows/ci.yml` 은 실행되지 않습니다.
`veo/` 가 자체 리포지터리의 루트가 되는 순간 활성화됩니다.
그전까지 실질적인 게이트는 `make ci-local` 입니다. 파일 맨 위 주석에 이관 절차를
적어두었습니다.

### 4. API 애플리케이션 진입점이 아직 없습니다

라우터(`veo.api.routes.meta`, `veo.api.routes.scoring`)는 있지만 이들을 묶는
FastAPI 애플리케이션 객체가 아직 없습니다. 그래서 `api` 이미지의 실행 명령은
`VEO_ASGI_APP` 환경변수로 빼두었고 기본값을 `veo.api.app:app` 으로 두었습니다.
**이 모듈이 생기기 전까지 api 컨테이너는 기동에 실패합니다.**
확정되면 이미지를 다시 빌드하지 않고 compose 에서 값만 덮어쓰면 됩니다.
관련 요청: `docs/operations/INTEGRATION_REQUEST.md` 요청 #2.

### 5. ASGI 서버가 의존성에 없습니다

`apps/api/pyproject.toml` 에 `uvicorn` 이 없습니다. 컨테이너가 아예 못 뜨는 것을
피하려고 `api.Dockerfile` 에서 별도로 설치하고 있는데, 이건 의존성 관리가 두
군데로 갈라진 상태라 바람직하지 않습니다. `pyproject.toml` 로 옮겨야 합니다.
관련 요청: `INTEGRATION_REQUEST.md` 요청 #1.

### 6. `apps/web` 에 standalone 출력이 꺼져 있습니다

`apps/web/` 과 워크스페이스 매니페스트는 들어왔지만, `next.config.ts` 에
`output: "standalone"` 이 없습니다. 그래서 `.next/standalone` 이 생성되지 않고
`web.Dockerfile` 의 3단계 `COPY` 가 실패합니다. **web 이미지는 현재 상태로
빌드할 수 없습니다.**

`apps/web/` 안에 `pnpm-workspace.yaml` 과 `pnpm-lock.yaml` 이 루트와 중복으로
존재하는 것도 확인했습니다. 워크스페이스 루트가 두 곳으로 해석될 수 있어
빌드 결과가 환경에 따라 달라질 수 있습니다.

관련 요청: `INTEGRATION_REQUEST.md` 요청 #5.

### 7. MinIO 이미지 태그가 고정돼 있지 않습니다

MinIO 는 semver major 태그를 발행하지 않고 날짜형
`RELEASE.YYYY-MM-DDThh-mm-ssZ` 태그만 냅니다. 확인하지 않은 릴리스 문자열을
지어내지 않으려고 로컬 개발용으로만 `:latest` 를 썼습니다.
**스테이징·운영에 올리기 전에 반드시 확인된 RELEASE 태그로 고정해야 합니다.**
`docs/operations/release-checklist.md` 에 항목으로 올려두었습니다.

### 8. `make ci-local` 이 lint 단계에서 막혀 있습니다

작성 시점 실측 결과입니다.

| 검사 | 결과 |
|---|---|
| `make lint-api` | **실패** — 252건, 전부 한 파일의 `E501` |
| `make typecheck-api` | 통과 (32개 파일) |
| `make test-api` | 통과 (824 passed, 4 skipped) |
| `make test-db` | 통과 (4개 테스트, 37개 테이블 up/down 검증) |

실패 원인은 코드 결함이 아니라 **린터 설정**입니다. 오류 252건이 전부
`apps/api/alembic/versions/20260728_0241_initial_veo_schema.py` 한 파일의
줄 길이 초과이고, 이 파일은 `alembic revision --autogenerate` 가 생성한
것입니다. autogenerate 는 원래 긴 줄을 만듭니다.

`apps/api/pyproject.toml` 의 ruff 설정에 한 줄을 추가하면 해결됩니다.

```toml
[tool.ruff.lint.per-file-ignores]
"alembic/versions/**" = ["E501"]
```

`pyproject.toml` 은 인프라 워커의 수정 대상이 아니라
`INTEGRATION_REQUEST.md` 요청 #6 으로 올려두었습니다.
이 한 줄이 반영되면 `make ci-local` 은 통과합니다.

`make test-api` 의 skip 4건은 `requires_postgres` 테스트입니다.
`make test-db` 로 실행하면 실제로 돌고 통과합니다.
