import { prisma } from "./db";

// 민감 행위 감사 로그 기록 (법무 검토: 접속기록·접근 로그).
// 실패해도 본 기능을 막지 않도록 조용히 무시.
export async function audit(
  agencyId: string,
  action: "LOGIN" | "SIGNUP" | "DELETE_DATA" | "CREATE_SHARE" | "CHANGE_PLAN" | "CREATE_SITE" | "CHANGE_PASSWORD" | "TRIAL_REMINDER",
  opts?: { userId?: string; userEmail?: string; detail?: string }
) {
  try {
    await prisma.auditLog.create({
      data: {
        agencyId,
        action,
        userId: opts?.userId ?? null,
        userEmail: opts?.userEmail ?? "",
        detail: (opts?.detail ?? "").slice(0, 300),
      },
    });
  } catch {
    /* 감사 로그 실패는 무시 */
  }
}
