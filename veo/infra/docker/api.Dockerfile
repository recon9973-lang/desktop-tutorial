# syntax=docker/dockerfile:1
#
# VEO API 이미지 (FastAPI).
#
# 빌드 컨텍스트는 리포지터리 루트(veo/)다:
#   docker build -f infra/docker/api.Dockerfile -t veo-api .
#
# 설계 원칙
#   * 멀티스테이지: 빌드 도구는 최종 이미지에 남기지 않는다.
#   * 비루트 실행: uid/gid 10001 고정(호스트 볼륨 권한을 예측 가능하게).
#   * 비밀값을 이미지에 굽지 않는다. 전부 런타임 환경변수로 주입한다.
#   * /health 를 치는 HEALTHCHECK 로 compose 의 의존 순서를 실제로 보장한다.

# =============================================================================
# 1단계 — 빌더: 가상환경을 만들고 apps/api 를 설치한다.
# =============================================================================
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 일부 의존성이 소스 배포판만 제공할 때를 대비한 컴파일러. 빌더에만 남는다.
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /build

# 의존성 메타데이터를 먼저 복사해 레이어 캐시를 살린다.
COPY apps/api/pyproject.toml ./apps/api/pyproject.toml
COPY apps/api/src ./apps/api/src

RUN pip install --upgrade pip \
    && pip install ./apps/api

# ASGI 서버는 배포 관심사라 apps/api 의 런타임 의존성에 아직 없다.
# apps/api/pyproject.toml 은 이 워커의 수정 대상이 아니므로 여기서 설치하고,
# docs/operations/INTEGRATION_REQUEST.md 에 이관 요청을 남겼다.
# uvicorn now ships as a declared dependency of veo-api, so the image and the
# audited dependency tree cannot drift apart.

# =============================================================================
# 2단계 — 런타임
# =============================================================================
FROM python:3.14-slim AS runtime

# ASGI 애플리케이션 경로와 헬스체크 경로는 환경변수로 뺀다.
# 앱 팩토리 모듈(veo.api.app)은 아직 구현 전이라, 이름이 확정되면 이미지를
# 다시 빌드하지 않고 compose 에서 덮어쓸 수 있어야 한다.
# 라우터를 VEO_API_PREFIX 아래에 마운트하면 헬스체크 경로도 /api/health 로 바꾼다.
# docs/operations/INTEGRATION_REQUEST.md 요청 #2 참고.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    VEO_API_HOST=0.0.0.0 \
    VEO_API_PORT=8000 \
    VEO_SCORING_SPECS_DIR=/app/packages/scoring-specs \
    VEO_ASGI_APP=veo.api.app:app \
    VEO_HEALTHCHECK_PATH=/api/health

RUN groupadd --gid 10001 veo \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin veo

COPY --from=builder --chown=root:root /opt/venv /opt/venv

WORKDIR /app

# 스코어링 명세는 코드가 아니라 데이터다. 읽기 전용으로만 필요하므로
# root 소유로 두고 veo 사용자에게는 읽기 권한만 준다.
COPY --chown=root:root packages/scoring-specs /app/packages/scoring-specs

USER veo

EXPOSE 8000

# curl 을 설치하지 않기 위해 표준 라이브러리로 확인한다.
# 200 이 아니면 비정상 종료 코드가 나가고 compose 가 unhealthy 로 표시한다.
#
# 포트는 아래 CMD 와 **같은 규칙**으로 고른다. 예전에는 여기만 VEO_API_PORT 를 봤는데,
# 플랫폼이 PORT 를 주입하면 서버는 그 포트로 뜨고 헬스체크는 8000 을 두드려, 멀쩡한
# 컨테이너가 스스로를 unhealthy 로 보고했다. 두 곳이 갈라지면 증상이 "배포는 되는데
# 계속 재시작" 으로 나타나서 원인을 앱에서 찾게 된다.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import os, sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:' + (os.environ.get('PORT') or os.environ.get('VEO_API_PORT', '8000')) + os.environ.get('VEO_HEALTHCHECK_PATH', '/api/health'), timeout=4).status == 200 else 1)"]

# 포트는 플랫폼이 정한다. Railway·Render 등은 PORT 를 주입하고 그 포트로만 트래픽을
# 보내므로, 컨테이너가 다른 포트를 열면 배포는 성공하고 접속만 안 되는 상태가 된다.
# PORT 가 없으면(compose·로컬) 기존 VEO_API_PORT 로 떨어진다.
CMD ["sh", "-c", "exec uvicorn \"$VEO_ASGI_APP\" --host \"$VEO_API_HOST\" --port \"${PORT:-$VEO_API_PORT}\" --proxy-headers"]
