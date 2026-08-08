# =============================================================================
# VEO — SEO · GEO · Naver Keyword Intelligence Platform
# 개발자가 실제로 치는 명령 모음.
#
#   make help          사용 가능한 명령 보기
#   make setup         파이썬 가상환경 + apps/api[dev] 설치
#   make ci-local      lint → typecheck → 테스트 (푸시 전에 이것부터)
#   make deploy        배포 — 후보 가지에서 CI 를 받고, 초록불일 때만 main 으로
#
# Docker 없이 돌아가는 것과 Docker 가 필요한 것을 명확히 나눠 뒀다.
# 현재 개발 장비에는 Docker 가 없어 up/down 계열은 이 장비에서 검증되지 않았다.
# =============================================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help

# 리포지터리 루트(이 Makefile 이 있는 디렉터리)의 절대경로.
ROOT := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))

VENV        := $(ROOT)/.venv
PY          := $(VENV)/bin/python
PIP         := $(VENV)/bin/pip
RUFF        := $(VENV)/bin/ruff
MYPY        := $(VENV)/bin/mypy
ALEMBIC     := $(VENV)/bin/alembic

# venv 를 만들 때 쓸 인터프리터. 다른 버전을 쓰려면 PYTHON=... 로 덮어쓴다.
PYTHON      ?= python3

API_DIR     := $(ROOT)/apps/api
SPECS_DIR   := $(ROOT)/packages/scoring-specs

# Alembic 은 apps/api 에 있다(모델 메타데이터를 임포트해야 하고,
# apps/api/tests/db/test_migrations.py 가 그 경로를 검사한다).
# alembic.ini 의 script_location/prepend_sys_path 가 상대경로라 반드시
# apps/api 를 작업 디렉터리로 두고 실행해야 한다.
# 이유와 직접 실행법: infra/migrations/README.md

# 로컬 PostgreSQL 접속 (Homebrew 기본값: 현재 사용자, 비밀번호 없음).
PGHOST      ?= localhost
PGPORT      ?= 5432
PGUSER      ?= $(USER)
TEST_DB     ?= veo_test

# 테스트가 쓸 접속 문자열. 이미 환경에 있으면 그 값을 존중한다.
VEO_TEST_DATABASE_URL ?= postgresql+psycopg://$(PGUSER)@$(PGHOST):$(PGPORT)/$(TEST_DB)

providers: ## 외부 제공자 연결 상태 — 이름과 상태만, 값은 절대 출력하지 않는다
	@$(PY) -c "from veo.core.settings import get_provider_credentials; states = get_provider_credentials().states(); [print(f'  {k:26s} {v}') for k, v in sorted(states.items())]; print(); print('  DISABLED_NO_CREDENTIAL = 자격증명 없음. 해당 지표는 UNKNOWN(측정 불가)이 되며,'); print('  VEO 는 추정값을 실제 데이터처럼 표시하지 않습니다.')"

import-credentials: ## 다른 프로젝트 .env 에서 제공자 키를 가져온다 (값 미출력)
	@infra/scripts/import-provider-credentials.sh $(FROM)

.PHONY: help setup test-api test-db test-contract lint-api typecheck-api \
        db-test-create db-test-drop migrate migrate-down migrate-history \
        migrate-revision ci-local up down logs ps clean check-docker \
        test-worker lint-worker typecheck-worker check-contracts test-all \
        deploy

# -----------------------------------------------------------------------------
help:
	@echo ""
	@echo "VEO 개발 명령"
	@echo ""
	@echo "  로컬 (Docker 불필요)"
	@echo "    make setup             .venv 생성 후 apps/api[dev] 편집설치"
	@echo "    make test-api          API 단위 테스트 (DB 테스트는 skip)"
	@echo "    make test-db           DB 테스트까지 실행 ($(TEST_DB) 자동 생성)"
	@echo "    make test-contract     계약 테스트 (tests/contract)"
	@echo "    make test-worker       워커 런타임 테스트"
	@echo "    make test-all          api + worker 전체 (DB 포함)"
	@echo "    make lint-api          ruff 검사 (api)"
	@echo "    make lint-worker       ruff 검사 (worker)"
	@echo "    make typecheck-api     mypy 검사 (api)"
	@echo "    make typecheck-worker  mypy 검사 (worker)"
	@echo "    make check-contracts   OpenAPI·공유타입·TS클라이언트 드리프트 검사"
	@echo "    make ci-local          위 전부 실행 (푸시 전 손검사)"
	@echo "    make deploy            ★ 배포 — CI 초록불일 때만 main 에 닿는다"
	@echo "                             (2026-08 한정: 하루 2회까지. 무료 Actions 시간 보호)"
	@echo "    make db-test-create    로컬 PostgreSQL 에 $(TEST_DB) 데이터베이스 생성"
	@echo "    make db-test-drop      $(TEST_DB) 데이터베이스 삭제"
	@echo "    make migrate           마이그레이션 최신까지 적용"
	@echo "    make migrate-down      마이그레이션 한 단계 되돌리기"
	@echo "    make migrate-history   리비전 이력과 현재 위치"
	@echo "    make migrate-revision m=\"설명\"   새 리비전 파일 생성(autogenerate)"
	@echo "    make clean             캐시·빌드 산출물 정리"
	@echo ""
	@echo "  Docker 필요 (이 장비에는 Docker 가 없어 미검증)"
	@echo "    make up                전체 스택 기동"
	@echo "    make down              전체 스택 종료"
	@echo "    make logs              로그 따라가기"
	@echo "    make ps                컨테이너 상태"
	@echo ""

# =============================================================================
# 로컬 개발 — Docker 없이 동작
# =============================================================================

setup:
	@echo "==> [setup] 가상환경 확인: $(VENV)"
	@if [ ! -x "$(PY)" ]; then \
		echo "==> [setup] $(PYTHON) 로 새 가상환경을 만듭니다"; \
		$(PYTHON) -m venv "$(VENV)"; \
	else \
		echo "==> [setup] 기존 가상환경을 재사용합니다 ($$($(PY) --version))"; \
	fi
	@echo "==> [setup] pip 업그레이드"
	@$(PIP) install --quiet --upgrade pip
	@echo "==> [setup] apps/api[dev] 편집 설치"
	@$(PIP) install --quiet -e "$(API_DIR)[dev]"
	@echo "==> [setup] 완료. 다음으로 'make ci-local' 을 실행해 보세요."

test-api:
	@echo "==> [test-api] apps/api/tests 실행"
	@VEO_SCORING_SPECS_DIR="$(SPECS_DIR)" \
		$(PY) -m pytest "$(API_DIR)/tests" -q

# DB 를 실제로 쓰는 테스트까지 돌린다.
# test-api 는 VEO_TEST_DATABASE_URL 을 넘기지 않으므로 DB 테스트가 skip 된다.
# skip 은 통과가 아니라 공백이다. 마이그레이션을 건드렸으면 반드시 이 타깃을 쓴다.
test-db: db-test-create
	@echo "==> [test-db] VEO_TEST_DATABASE_URL 을 주입해 DB 테스트까지 실행"
	@VEO_SCORING_SPECS_DIR="$(SPECS_DIR)" \
	 VEO_TEST_DATABASE_URL="$(VEO_TEST_DATABASE_URL)" \
	 VEO_DATABASE_URL="$(VEO_TEST_DATABASE_URL)" \
		$(PY) -m pytest "$(API_DIR)/tests" -q -m requires_postgres

test-contract:
	@echo "==> [test-contract] tests/contract 실행"
	@if [ -z "$$(find "$(ROOT)/tests/contract" -name 'test_*.py' -print -quit 2>/dev/null)" ]; then \
		echo "==> [test-contract] tests/contract 에 테스트가 아직 없습니다. 건너뜁니다."; \
	else \
		VEO_SCORING_SPECS_DIR="$(SPECS_DIR)" \
			$(PY) -m pytest "$(ROOT)/tests/contract" -q; \
	fi

lint-api:
	@echo "==> [lint-api] ruff check apps/api"
	@$(RUFF) check "$(API_DIR)"

typecheck-api:
	@echo "==> [typecheck-api] mypy (설정: apps/api/pyproject.toml)"
	@cd "$(API_DIR)" && "$(MYPY)"


# -----------------------------------------------------------------------------
# 워커 (Celery 런타임). Redis 가 없으면 실동작 테스트는 skip 된다.
# -----------------------------------------------------------------------------

test-worker:
	@echo "==> [test-worker] apps/worker/tests 실행"
	@$(PY) -m pytest "$(ROOT)/apps/worker/tests" -q

lint-worker:
	@echo "==> [lint-worker] ruff check apps/worker"
	@$(RUFF) check "$(ROOT)/apps/worker"

typecheck-worker:
	@echo "==> [typecheck-worker] mypy apps/worker"
	@cd "$(ROOT)/apps/worker" && $(MYPY) src/veo_worker

# -----------------------------------------------------------------------------
# 생성물 드리프트. OpenAPI · 공유 타입 · TypeScript 클라이언트가 원천과 어긋나면 실패한다.
# API 를 바꾸고 생성물을 갱신하지 않은 채로는 병합할 수 없어야 한다.
# -----------------------------------------------------------------------------

check-contracts:
	@echo "==> [check-contracts] OpenAPI 문서가 앱과 일치하는지"
	@cd "$(API_DIR)" && $(PY) scripts/export_openapi.py --check
	@echo "==> [check-contracts] 공유 TypeScript 타입이 Python 계약과 일치하는지"
	@cd "$(API_DIR)" && $(PY) scripts/export_shared_types.py --check
	@echo "==> [check-contracts] 생성된 API 클라이언트가 OpenAPI 와 일치하는지"
	@if command -v pnpm >/dev/null 2>&1; then \
		cd "$(ROOT)/packages/api-client" && pnpm run --silent check; \
	else \
		echo "    pnpm 이 없어 클라이언트 드리프트 검사를 건너뜁니다 (검증되지 않음)"; \
		exit 1; \
	fi

# DB 테스트까지 포함한 전체 파이썬 스위트.
test-all: db-test-create
	@echo "==> [test-all] apps/api + apps/worker (DB 포함)"
	@VEO_TEST_DATABASE_URL="$(VEO_TEST_DATABASE_URL)" \
		VEO_SCORING_SPECS_DIR="$(SPECS_DIR)" \
		$(PY) -m pytest -q

# 푸시 전에 손으로 돌리는 검사.
#
# 예전 주석은 "veo/ 가 상위 저장소의 하위 디렉터리라 워크플로가 동작하지 않는다. 그래서
# 이 타깃이 **유일한** 게이트" 라고 적혀 있었다. 지금은 사실이 아니다 — subtree 로 밀린
# veo-platform 에서 CI 가 실제로 돈다. 그런데 그 주석을 믿고 여기만 초록이면 배포한
# 결과, CI 가 12번 연속 빨간불인 것을 아무도 보지 않았다(2026-08-04).
#
# **여기가 초록인 것과 CI 가 초록인 것은 다르다.** 이 장비에는 Docker 도 Redis 도 없고,
# 프론트엔드 빌드도 여기서 돌지 않는다. 진짜 게이트는 `make deploy` 다.
ci-local: lint-api lint-worker typecheck-api typecheck-worker check-contracts test-all
	@echo ""
	@echo "==> [ci-local] lint · typecheck · 계약 드리프트 · 전체 테스트 통과."
	@echo "    검증하지 않은 것: Docker 이미지 빌드(이 장비에 Docker 없음),"
	@echo "    Redis 실브로커 테스트(미설치), 프론트엔드(pnpm -r test 로 별도 실행)."
	@echo "    ※ 이것은 배포 관문이 아닙니다. 배포는 make deploy 로 하십시오."

# 배포 — CI 가 초록불일 때만 main 에 닿는다.
#
# 후보 가지에 먼저 밀어 채점을 받고, 통과했을 때만 같은 커밋을 main 으로 옮긴다.
# GitHub 의 가지 보호는 비공개 저장소 + 무료 요금제에서 적용되지 않으므로(403),
# 관문을 여기에 둔다. 자세한 사정은 scripts/deploy.sh 머리말에 적혀 있다.
deploy:
	@bash "$(ROOT)/scripts/deploy.sh"

# -----------------------------------------------------------------------------
# 테스트 데이터베이스 — 로컬 psql 사용 (Docker 불필요)
# -----------------------------------------------------------------------------

db-test-create:
	@echo "==> [db-test-create] $(PGHOST):$(PGPORT) 의 '$(TEST_DB)' 확인"
	@if psql -h "$(PGHOST)" -p "$(PGPORT)" -U "$(PGUSER)" -d postgres -tAc \
			"SELECT 1 FROM pg_database WHERE datname = '$(TEST_DB)'" | grep -q 1; then \
		echo "==> [db-test-create] '$(TEST_DB)' 는 이미 있습니다. 그대로 둡니다."; \
	else \
		echo "==> [db-test-create] '$(TEST_DB)' 생성"; \
		psql -h "$(PGHOST)" -p "$(PGPORT)" -U "$(PGUSER)" -d postgres -q -c \
			"CREATE DATABASE $(TEST_DB) ENCODING 'UTF8' TEMPLATE template0"; \
		echo "==> [db-test-create] 생성 완료"; \
	fi
	@echo "==> [db-test-create] VEO_TEST_DATABASE_URL=$(VEO_TEST_DATABASE_URL)"

db-test-drop:
	@echo "==> [db-test-drop] '$(TEST_DB)' 삭제 (테스트 전용 DB 만 지웁니다)"
	@psql -h "$(PGHOST)" -p "$(PGPORT)" -U "$(PGUSER)" -d postgres -q -c \
		"DROP DATABASE IF EXISTS $(TEST_DB) WITH (FORCE)"
	@echo "==> [db-test-drop] 완료"

# -----------------------------------------------------------------------------
# 마이그레이션
#
# 접속 정보는 VEO_DATABASE_URL 에서 온다 (apps/api/alembic/env.py).
# 설정하지 않으면 settings 기본값(로컬 veo DB)으로 떨어진다.
#   make migrate VEO_DATABASE_URL='postgresql+psycopg://user@localhost:5432/veo'
# -----------------------------------------------------------------------------

migrate:
	@echo "==> [migrate] alembic upgrade head  (cwd: apps/api)"
	@cd "$(API_DIR)" && "$(ALEMBIC)" upgrade head
	@echo "==> [migrate] 완료"

migrate-down:
	@echo "==> [migrate-down] alembic downgrade -1  (cwd: apps/api)"
	@cd "$(API_DIR)" && "$(ALEMBIC)" downgrade -1
	@echo "==> [migrate-down] 완료"

migrate-history:
	@echo "==> [migrate-history] alembic history"
	@cd "$(API_DIR)" && "$(ALEMBIC)" history --indicate-current

migrate-revision:
	@if [ -z "$(m)" ]; then \
		echo "==> [migrate-revision] 사용법: make migrate-revision m=\"add projects table\""; \
		exit 2; \
	fi
	@echo "==> [migrate-revision] 새 리비전 생성(자동 감지): $(m)"
	@cd "$(API_DIR)" && "$(ALEMBIC)" revision --autogenerate -m "$(m)"
	@echo "==> [migrate-revision] 생성된 파일의 downgrade() 를 반드시 확인하세요."

clean:
	@echo "==> [clean] 캐시 정리"
	@find "$(ROOT)/apps" "$(ROOT)/packages" "$(ROOT)/tests" "$(ROOT)/infra" \
		-type d \( -name '__pycache__' -o -name '.pytest_cache' -o -name '.mypy_cache' -o -name '.ruff_cache' \) \
		-prune -exec rm -rf {} + 2>/dev/null || true
	@rm -rf "$(ROOT)/.pytest_cache" "$(ROOT)/.mypy_cache" "$(ROOT)/.ruff_cache"
	@echo "==> [clean] 완료"

# =============================================================================
# Docker 스택
#
# ★ 아래 타깃은 Docker Engine 과 Compose v2.20+ 가 있어야 동작한다.
#   Phase 0 개발 장비에는 Docker 가 설치돼 있지 않아 실제 빌드/기동으로
#   검증하지 못했다. Dockerfile 과 compose 정의는 문법 수준까지만 확인됐다.
#   자세한 내용: docs/operations/local-development.md 의 "알려진 한계"
# =============================================================================

check-docker:
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "==> [docker] docker 명령을 찾을 수 없습니다."; \
		echo "    이 장비에는 Docker 가 설치돼 있지 않습니다."; \
		echo "    Docker 없이 개발하려면 'make setup' 과 'make ci-local' 을 쓰세요."; \
		echo "    설치 안내: docs/operations/local-development.md"; \
		exit 1; \
	fi
	@if [ ! -f "$(ROOT)/.env" ]; then \
		echo "==> [docker] .env 가 없습니다. 'cp .env.example .env' 후 값을 채우세요."; \
		exit 1; \
	fi

up: check-docker
	@echo "==> [up] docker compose up -d --build"
	@cd "$(ROOT)" && docker compose up -d --build
	@echo "==> [up] 상태 확인: make ps"

down: check-docker
	@echo "==> [down] docker compose down (볼륨은 유지합니다)"
	@cd "$(ROOT)" && docker compose down
	@echo "==> [down] 완료. 데이터까지 지우려면: docker compose down -v"

logs: check-docker
	@echo "==> [logs] docker compose logs -f"
	@cd "$(ROOT)" && docker compose logs -f

ps: check-docker
	@echo "==> [ps] docker compose ps"
	@cd "$(ROOT)" && docker compose ps
