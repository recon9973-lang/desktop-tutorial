import { PrismaClient } from "@prisma/client";

// 개발 중 핫리로드로 커넥션이 폭증하지 않도록 전역 싱글턴 사용.
const globalForPrisma = globalThis as unknown as { prisma?: PrismaClient };

export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === "development" ? ["error", "warn"] : ["error"],
  });

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;
