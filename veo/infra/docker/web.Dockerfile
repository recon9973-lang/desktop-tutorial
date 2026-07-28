# syntax=docker/dockerfile:1
#
# VEO 콘솔 이미지 (Next.js, standalone 출력).
#
# 빌드 컨텍스트는 리포지터리 루트(veo/)다:
#   docker build -f infra/docker/web.Dockerfile -t veo-web .
#
# 전제조건 — apps/web/next.config 에 `output: "standalone"` 이 설정돼 있어야 한다.
# 그래야 .next/standalone 에 필요한 node_modules 만 추려진 서버 번들이 나온다.
# 현재 apps/web 은 아직 스캐폴딩 전이라 이 이미지는 빌드할 수 없다.
# docs/operations/local-development.md 의 "알려진 한계" 항목 참고.
#
# 빌드타임 비밀값 주의 — Next.js 는 NEXT_PUBLIC_* 변수를 빌드 시점에 클라이언트
# 번들에 그대로 인라인한다. 따라서 이 이미지에는 공개해도 되는 값만 들어간다.
# 서버 전용 비밀값은 ARG 로 받지 않고 런타임 ENV 로만 주입한다.

# =============================================================================
# 1단계 — 의존성 설치
# =============================================================================
FROM node:22-alpine AS deps

RUN corepack enable

WORKDIR /app

# 워크스페이스 매니페스트만 먼저 복사해 캐시를 살린다.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
COPY packages ./packages

RUN pnpm install --frozen-lockfile --filter "./apps/web..."

# =============================================================================
# 2단계 — 빌드
# =============================================================================
FROM node:22-alpine AS builder

RUN corepack enable

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules
COPY . .

# 브라우저 번들에 인라인되는 공개 설정. 비밀값을 여기 넣지 않는다.
ARG NEXT_PUBLIC_VEO_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_VEO_API_BASE_URL=${NEXT_PUBLIC_VEO_API_BASE_URL} \
    NEXT_TELEMETRY_DISABLED=1

RUN pnpm --filter "./apps/web" build

# =============================================================================
# 3단계 — 런타임
# =============================================================================
FROM node:22-alpine AS runtime

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 10001 veo \
    && adduser --system --uid 10001 --ingroup veo --shell /sbin/nologin veo

WORKDIR /app

# standalone 출력은 server.js 와 추려진 node_modules 를 함께 담고 있다.
COPY --from=builder --chown=veo:veo /app/apps/web/.next/standalone ./
COPY --from=builder --chown=veo:veo /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=veo:veo /app/apps/web/public ./apps/web/public

USER veo

EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD ["node", "-e", "require('http').get('http://127.0.0.1:' + (process.env.PORT || 3000) + '/', r => process.exit(r.statusCode < 500 ? 0 : 1)).on('error', () => process.exit(1))"]

CMD ["node", "apps/web/server.js"]
