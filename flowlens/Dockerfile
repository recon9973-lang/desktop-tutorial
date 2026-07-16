# FlowLens 프로덕션 이미지 (Next.js standalone + Prisma)
FROM node:22-alpine AS base
RUN apk add --no-cache libc6-compat openssl

# 의존성 설치
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# 빌드
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npx prisma generate
RUN npm run build

# 실행 (standalone)
FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=4311

RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
# Prisma 스키마/엔진과 마이그레이션 (컨테이너에서 migrate deploy 실행용)
COPY --from=builder /app/prisma ./prisma
COPY --from=builder /app/node_modules/.prisma ./node_modules/.prisma
COPY --from=builder /app/node_modules/@prisma ./node_modules/@prisma

USER nextjs
EXPOSE 4311

# 시작 시 스키마 동기화 후 서버 실행.
# (MVP: db push로 스키마 반영. 팀/운영 규모가 커지면 prisma migrate 로 전환 — DEPLOY.md 참고)
CMD ["sh", "-c", "npx prisma db push --skip-generate && node server.js"]
