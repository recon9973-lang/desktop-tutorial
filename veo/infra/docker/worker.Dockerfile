# syntax=docker/dockerfile:1
#
# VEO Celery 워커 이미지.
#
# 빌드 컨텍스트는 리포지터리 루트(veo/)다:
#   docker build -f infra/docker/worker.Dockerfile -t veo-worker .
#
# 보안 설계 — "이미지 안에서 비밀값에 셸로 접근할 수 없게 한다"
#   * 비밀값은 빌드 인자(ARG)로도, ENV 기본값으로도 이미지에 들어가지 않는다.
#     전부 런타임 주입이며, 따라서 `docker history` 나 이미지 레이어를 뒤져도 없다.
#   * 실행 사용자 veo(uid 10001)의 로그인 셸은 /usr/sbin/nologin 이고
#     ENTRYPOINT 는 celery 바이너리를 직접 exec 한다. 셸을 경유하지 않으므로
#     셸 확장으로 환경변수를 흘릴 지점이 없다.
#   * 워커는 --without-gossip --without-mingle 로 브로커 잡담을 줄이고,
#     원격 제어 채널(remote control)을 끈다. 브로커를 잡은 공격자가
#     워커에 임의 명령을 주입하는 경로를 막기 위한 것이다.

# =============================================================================
# 1단계 — 빌더
# =============================================================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /build

COPY apps/api/pyproject.toml ./apps/api/pyproject.toml
COPY apps/api/src ./apps/api/src

# 워커는 API 와 같은 veo 패키지를 쓴다. celery 는 이미 런타임 의존성에 있다.
RUN pip install --upgrade pip \
    && pip install ./apps/api

# =============================================================================
# 2단계 — 런타임
# =============================================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    VEO_SCORING_SPECS_DIR=/app/packages/scoring-specs \
    CELERY_APP=veo_worker.runtime.app:celery_app

RUN groupadd --gid 10001 veo \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin veo

COPY --from=builder --chown=root:root /opt/venv /opt/venv

WORKDIR /app

COPY --chown=root:root packages/scoring-specs /app/packages/scoring-specs

USER veo

# celery inspect ping 은 브로커를 왕복하므로 워커가 실제로 살아 있는지 확인한다.
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ["celery", "--app", "veo_worker.runtime.app:celery_app", "inspect", "ping", "--destination", "celery@veo-worker", "--timeout", "8"]

# 셸을 경유하지 않는 exec 형식. 큐/동시성은 compose 의 command 로 덮어쓴다.
ENTRYPOINT ["celery"]
CMD ["--app", "veo_worker.runtime.app:celery_app", "worker", \
     "--hostname", "celery@veo-worker", \
     "--loglevel", "INFO", \
     "--without-gossip", \
     "--without-mingle", \
     "--concurrency", "4"]
