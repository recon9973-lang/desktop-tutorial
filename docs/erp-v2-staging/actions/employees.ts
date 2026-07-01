// 목표 경로: src/server/actions/employees.ts
//
// 직원 초대/역할변경 + 회사 지출 정책 토글.
// 권한: 초대/역할변경=관리자 이상(단 SUPER_ADMIN 부여 불가), 지출토글=최고관리자.
"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { Role, UserStatus } from "@/domain/types";
import { db } from "@/server/db";
import {
  recordAudit,
  requestMeta,
  requireUser,
  runAction,
  type ActionResult
} from "@/server/actions/_helpers";

const inviteSchema = z.object({
  email: z.string().trim().email(),
  name: z.string().trim().min(1),
  role: z.enum(["ADMIN", "MARKETER"]) // SUPER_ADMIN 초대 불가
});

/** 직원 초대 — INVITED 상태로 생성. 첫 로그인 시 auth 콜백에서 ACTIVE 전환. */
export async function inviteEmployee(input: unknown): Promise<ActionResult<{ id: string }>> {
  return runAction(async () => {
    const user = await requireUser();
    if (user.role !== Role.SUPER_ADMIN && user.role !== Role.ADMIN) throw new Error("FORBIDDEN");
    const p = inviteSchema.safeParse(input);
    if (!p.success) throw new Error("VALIDATION");
    const d = p.data;

    const exists = await db.user.findFirst({ where: { email: d.email.toLowerCase() } });
    if (exists) throw new Error("VALIDATION"); // 이미 존재하는 이메일

    const meta = await requestMeta();
    const created = await db.$transaction(async (tx) => {
      const u = await tx.user.create({
        data: { email: d.email.toLowerCase(), name: d.name, role: d.role as never, status: UserStatus.INVITED }
      });
      await recordAudit(tx, { actorId: user.id, action: "employee.invite", targetType: "User", targetId: u.id, afterState: { email: u.email, role: u.role }, ...meta });
      return u;
    });
    revalidatePath("/settings");
    return { id: created.id };
  });
}

const roleSchema = z.object({ userId: z.string().min(1), role: z.enum(["ADMIN", "MARKETER"]) });

/** 역할 변경 — 관리자 허용. SUPER_ADMIN 부여/강등은 불가(권한 상승 방지). */
export async function changeRole(input: unknown): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    if (user.role !== Role.SUPER_ADMIN && user.role !== Role.ADMIN) throw new Error("FORBIDDEN");
    const p = roleSchema.safeParse(input);
    if (!p.success) throw new Error("VALIDATION");

    const target = await db.user.findUnique({ where: { id: p.data.userId } });
    if (!target) throw new Error("NOT_FOUND");
    if (target.role === Role.SUPER_ADMIN) throw new Error("FORBIDDEN"); // 최고관리자 대상 변경 불가

    const meta = await requestMeta();
    await db.$transaction(async (tx) => {
      await tx.user.update({ where: { id: p.data.userId }, data: { role: p.data.role as never } });
      await recordAudit(tx, { actorId: user.id, action: "employee.changeRole", targetType: "User", targetId: p.data.userId, beforeState: { role: target.role }, afterState: { role: p.data.role }, ...meta });
    });
    revalidatePath("/settings");
  });
}

/** 회사 지출 관리 권한 토글 — 최고관리자 전용. */
export async function setExpensePolicy(input: unknown): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    if (user.role !== Role.SUPER_ADMIN) throw new Error("FORBIDDEN");
    const p = z.object({ adminCanManageExpense: z.boolean() }).safeParse(input);
    if (!p.success) throw new Error("VALIDATION");

    const meta = await requestMeta();
    await db.$transaction(async (tx) => {
      const existing = await tx.companySetting.findFirst();
      if (existing) await tx.companySetting.update({ where: { id: existing.id }, data: { adminCanManageExpense: p.data.adminCanManageExpense } });
      else await tx.companySetting.create({ data: { adminCanManageExpense: p.data.adminCanManageExpense } });
      await recordAudit(tx, { actorId: user.id, action: "setting.expensePolicy", targetType: "CompanySetting", targetId: "singleton", afterState: { adminCanManageExpense: p.data.adminCanManageExpense }, ...meta });
    });
    revalidatePath("/settings");
  });
}
