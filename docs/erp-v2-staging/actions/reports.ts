// 목표 경로: src/server/actions/reports.ts
//
// 월간 보고서 — 작성/성과지표(JSON)/검토·전달 + 상태전이.
// 상태: DRAFT → REVIEW_NEEDED → APPROVED → DELIVERED.
// 권한: 작성/지표=담당 가능자, 검토·전달=관리자 이상.
"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { Role } from "@/domain/types";
import { assertCanAccessClient } from "@/domain/access-control";
import { db } from "@/server/db";
import {
  getAdminScopes,
  recordAudit,
  requestMeta,
  requireUser,
  runAction,
  type ActionResult
} from "@/server/actions/_helpers";
import type { CurrentUser } from "@/server/session";

async function assertClient(user: CurrentUser, clientId: string, assignedMarketerId: string | null) {
  const scopes = await getAdminScopes(user);
  assertCanAccessClient(user, clientId, scopes, assignedMarketerId);
}
function assertReviewer(role: Role) {
  if (role !== Role.SUPER_ADMIN && role !== Role.ADMIN) throw new Error("FORBIDDEN");
}

const createSchema = z.object({
  clientId: z.string().min(1),
  reportingMonth: z.string().regex(/^\d{4}-\d{2}$/),
  title: z.string().trim().min(1),
  workItemId: z.string().optional().nullable()
});

export async function createReport(input: unknown): Promise<ActionResult<{ id: string }>> {
  return runAction(async () => {
    const user = await requireUser();
    const p = createSchema.safeParse(input);
    if (!p.success) throw new Error("VALIDATION");
    const d = p.data;
    const client = await db.client.findUnique({ where: { id: d.clientId } });
    if (!client) throw new Error("NOT_FOUND");
    await assertClient(user, d.clientId, client.assignedMarketerId);

    const meta = await requestMeta();
    const saved = await db.$transaction(async (tx) => {
      const rep = await tx.report.create({
        data: {
          clientId: d.clientId,
          authorId: user.id,
          reportingMonth: d.reportingMonth,
          title: d.title,
          status: "DRAFT",
          workItemId: d.workItemId || null
        }
      });
      await recordAudit(tx, { actorId: user.id, action: "report.create", targetType: "Report", targetId: rep.id, afterState: rep, ...meta });
      return rep;
    });
    revalidatePath("/reports");
    return { id: saved.id };
  });
}

/** 성과 지표 저장 (JSON). 키워드 순위 자동수집분 + 수기분 병합. */
export async function updateReportMetrics(input: unknown): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    const p = z.object({ id: z.string().min(1), metrics: z.record(z.any()), attachmentUrl: z.string().url().optional().nullable().or(z.literal("")) }).safeParse(input);
    if (!p.success) throw new Error("VALIDATION");
    const rep = await db.report.findUnique({ where: { id: p.data.id }, include: { client: { select: { assignedMarketerId: true } } } });
    if (!rep) throw new Error("NOT_FOUND");
    await assertClient(user, rep.clientId, rep.client.assignedMarketerId);

    const meta = await requestMeta();
    await db.$transaction(async (tx) => {
      await tx.report.update({ where: { id: p.data.id }, data: { metrics: p.data.metrics as never, attachmentUrl: p.data.attachmentUrl || undefined } });
      await recordAudit(tx, { actorId: user.id, action: "report.metrics", targetType: "Report", targetId: p.data.id, afterState: { keys: Object.keys(p.data.metrics) }, ...meta });
    });
    revalidatePath("/reports");
  });
}

/** 상태전이: DRAFT→REVIEW_NEEDED(작성자), REVIEW_NEEDED→APPROVED, APPROVED→DELIVERED(검토자). */
const transitionMap: Record<string, { from: string; to: string; reviewer: boolean }> = {
  submit:  { from: "DRAFT", to: "REVIEW_NEEDED", reviewer: false },
  approve: { from: "REVIEW_NEEDED", to: "APPROVED", reviewer: true },
  deliver: { from: "APPROVED", to: "DELIVERED", reviewer: true }
};

export async function transitionReport(input: unknown): Promise<ActionResult<{ status: string }>> {
  return runAction(async () => {
    const user = await requireUser();
    const p = z.object({ id: z.string().min(1), action: z.enum(["submit", "approve", "deliver"]) }).safeParse(input);
    if (!p.success) throw new Error("VALIDATION");
    const rule = transitionMap[p.data.action];

    const rep = await db.report.findUnique({ where: { id: p.data.id }, include: { client: { select: { assignedMarketerId: true } } } });
    if (!rep) throw new Error("NOT_FOUND");
    if (rep.status !== rule.from) throw new Error("ILLEGAL_TRANSITION");
    if (rule.reviewer) assertReviewer(user.role);
    else await assertClient(user, rep.clientId, rep.client.assignedMarketerId);

    const meta = await requestMeta();
    await db.$transaction(async (tx) => {
      await tx.report.update({
        where: { id: p.data.id },
        data: {
          status: rule.to as never,
          reviewerId: rule.reviewer ? user.id : undefined,
          deliveredAt: rule.to === "DELIVERED" ? new Date() : undefined
        }
      });
      await recordAudit(tx, { actorId: user.id, action: `report.${p.data.action}`, targetType: "Report", targetId: p.data.id, beforeState: { status: rep.status }, afterState: { status: rule.to }, ...meta });
    });
    revalidatePath("/reports");
    return { status: rule.to };
  });
}
