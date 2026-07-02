// 목표 경로: src/server/tracking.ts
//
// 추적/감사 — 로그인 이력 기록 + 최고관리자 추적 조회.
// 로그인 이벤트는 Auth.js signIn 콜백/이벤트에서 recordLogin() 호출.
import { db } from "@/server/db";
import { Role } from "@/domain/types";
import type { CurrentUser } from "@/server/session";

/** 로그인 이력 기록 (성공/실패). Auth 이벤트에서 호출. */
export async function recordLogin(params: {
  userId: string;
  success: boolean;
  ip?: string | null;
  userAgent?: string | null;
}) {
  await db.loginHistory.create({
    data: {
      userId: params.userId,
      success: params.success,
      ip: params.ip ?? null,
      userAgent: params.userAgent ?? null
    }
  });
}

/** 로그아웃 시각 기록(가장 최근 미종료 로그인에). */
export async function recordLogout(userId: string) {
  const last = await db.loginHistory.findFirst({
    where: { userId, logoutAt: null, success: true },
    orderBy: { at: "desc" }
  });
  if (last) {
    await db.loginHistory.update({ where: { id: last.id }, data: { logoutAt: new Date() } });
  }
}

/**
 * 추적 조회 — 최고관리자 전용. 로그인 이력 + 활동 이력(AuditLog) 통합.
 * 필터: 사용자/기간/대상타입.
 */
export async function queryTracking(
  viewer: CurrentUser,
  filter: { userId?: string; from?: Date; to?: Date; targetType?: string; take?: number }
) {
  if (viewer.role !== Role.SUPER_ADMIN) {
    throw new Error("FORBIDDEN"); // 추적 조회는 최고관리자만
  }
  const take = Math.min(filter.take ?? 100, 500);
  const atRange = { gte: filter.from, lte: filter.to };

  const [logins, activities] = await Promise.all([
    db.loginHistory.findMany({
      where: {
        userId: filter.userId,
        at: filter.from || filter.to ? atRange : undefined
      },
      orderBy: { at: "desc" },
      take
    }),
    db.auditLog.findMany({
      where: {
        actorId: filter.userId,
        targetType: filter.targetType,
        createdAt: filter.from || filter.to ? { gte: filter.from, lte: filter.to } : undefined
      },
      orderBy: { createdAt: "desc" },
      take
    })
  ]);

  return { logins, activities };
}
