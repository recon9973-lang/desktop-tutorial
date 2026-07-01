// 목표 경로: src/server/actions/leave.ts
//
// 연차/휴가 — 신청/승인/반려/취소 + 잔여일 차감 + 승인 시 캘린더 반영.
// 권한: 신청=전원(본인), 승인/반려=관리자 이상.
"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { Role } from "@/domain/types";
import { db } from "@/server/db";
import {
  recordAudit,
  requestMeta,
  requireUser,
  runAction,
  type ActionResult
} from "@/server/actions/_helpers";

/** 휴가 유형별 소요 일수. 반차=0.5. */
function leaveDays(type: string, start: Date, end: Date): number {
  if (type === "HALF_DAY_AM" || type === "HALF_DAY_PM") return 0.5;
  const ms = +new Date(end.toDateString()) - +new Date(start.toDateString());
  return Math.floor(ms / 86400000) + 1;
}

const requestSchema = z.object({
  type: z.enum(["ANNUAL", "HALF_DAY_AM", "HALF_DAY_PM", "SICK", "OTHER"]),
  startDate: z.coerce.date(),
  endDate: z.coerce.date(),
  reason: z.string().trim().optional().nullable()
});

/** 휴가 신청 (본인). 잔여 연차 검증은 승인 시점에 최종 반영. */
export async function requestLeave(input: unknown): Promise<ActionResult<{ id: string }>> {
  return runAction(async () => {
    const user = await requireUser();
    const p = requestSchema.safeParse(input);
    if (!p.success) throw new Error("VALIDATION");
    const d = p.data;
    if (d.endDate < d.startDate) throw new Error("VALIDATION");

    const days = leaveDays(d.type, d.startDate, d.endDate);
    const meta = await requestMeta();
    const saved = await db.$transaction(async (tx) => {
      const req = await tx.leaveRequest.create({
        data: {
          requesterId: user.id,
          type: d.type as never,
          status: "REQUESTED",
          startDate: d.startDate,
          endDate: d.endDate,
          daysRequested: days,
          reason: d.reason || null
        }
      });
      await recordAudit(tx, { actorId: user.id, action: "leave.request", targetType: "LeaveRequest", targetId: req.id, afterState: req, ...meta });
      return req;
    });
    revalidatePath("/leave");
    return { id: saved.id };
  });
}

function assertApprover(role: Role) {
  if (role !== Role.SUPER_ADMIN && role !== Role.ADMIN) throw new Error("FORBIDDEN");
}

/** 승인 — 잔여 연차 차감(ANNUAL/반차) + 캘린더 LEAVE 이벤트 생성. */
export async function approveLeave(id: string): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    assertApprover(user.role);
    const req = await db.leaveRequest.findUnique({ where: { id } });
    if (!req) throw new Error("NOT_FOUND");
    if (req.status !== "REQUESTED") throw new Error("ILLEGAL_TRANSITION");

    const meta = await requestMeta();
    const consumesAnnual = req.type === "ANNUAL" || req.type === "HALF_DAY_AM" || req.type === "HALF_DAY_PM";
    await db.$transaction(async (tx) => {
      await tx.leaveRequest.update({ where: { id }, data: { status: "APPROVED", approverId: user.id } });
      if (consumesAnnual) {
        const year = new Date(req.startDate).getFullYear();
        const policy = await tx.leavePolicy.findFirst({ where: { userId: req.requesterId, year } });
        if (policy) {
          await tx.leavePolicy.update({ where: { id: policy.id }, data: { usedDays: Number(policy.usedDays) + Number(req.daysRequested) } });
        }
      }
      await tx.calendarEvent.create({
        data: {
          title: `휴가 (${req.type})`,
          startsAt: req.startDate,
          endsAt: req.endDate,
          provider: "INTERNAL",
          kind: "LEAVE",
          leaveRequestId: req.id
        }
      });
      await recordAudit(tx, {
        actorId: user.id, action: "leave.approve", targetType: "LeaveRequest", targetId: id,
        beforeState: { status: req.status }, afterState: { status: "APPROVED", approverId: user.id }, ...meta
      });
    });
    revalidatePath("/leave");
    revalidatePath("/calendar");
  });
}

export async function rejectLeave(input: unknown): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    assertApprover(user.role);
    const p = z.object({ id: z.string().min(1), reason: z.string().trim().optional().nullable() }).safeParse(input);
    if (!p.success) throw new Error("VALIDATION");
    const req = await db.leaveRequest.findUnique({ where: { id: p.data.id } });
    if (!req) throw new Error("NOT_FOUND");
    if (req.status !== "REQUESTED") throw new Error("ILLEGAL_TRANSITION");

    const meta = await requestMeta();
    await db.$transaction(async (tx) => {
      await tx.leaveRequest.update({ where: { id: p.data.id }, data: { status: "REJECTED", approverId: user.id } });
      await recordAudit(tx, {
        actorId: user.id, action: "leave.reject", targetType: "LeaveRequest", targetId: p.data.id,
        afterState: { status: "REJECTED", reason: p.data.reason ?? null }, ...meta
      });
    });
    revalidatePath("/leave");
  });
}

/** 취소 — 본인의 미승인 건 취소, 또는 승인건 취소 시 잔여일 복구 + 캘린더 제거. */
export async function cancelLeave(id: string): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    const req = await db.leaveRequest.findUnique({ where: { id } });
    if (!req) throw new Error("NOT_FOUND");
    const isOwner = req.requesterId === user.id;
    const isManager = user.role === Role.SUPER_ADMIN || user.role === Role.ADMIN;
    if (!isOwner && !isManager) throw new Error("FORBIDDEN");
    if (req.status === "CANCELED" || req.status === "REJECTED") throw new Error("ILLEGAL_TRANSITION");

    const meta = await requestMeta();
    const wasApproved = req.status === "APPROVED";
    const consumesAnnual = req.type === "ANNUAL" || req.type === "HALF_DAY_AM" || req.type === "HALF_DAY_PM";
    await db.$transaction(async (tx) => {
      await tx.leaveRequest.update({ where: { id }, data: { status: "CANCELED" } });
      if (wasApproved) {
        if (consumesAnnual) {
          const year = new Date(req.startDate).getFullYear();
          const policy = await tx.leavePolicy.findFirst({ where: { userId: req.requesterId, year } });
          if (policy) await tx.leavePolicy.update({ where: { id: policy.id }, data: { usedDays: Math.max(0, Number(policy.usedDays) - Number(req.daysRequested)) } });
        }
        await tx.calendarEvent.deleteMany({ where: { leaveRequestId: id } });
      }
      await recordAudit(tx, { actorId: user.id, action: "leave.cancel", targetType: "LeaveRequest", targetId: id, beforeState: { status: req.status }, afterState: { status: "CANCELED" }, ...meta });
    });
    revalidatePath("/leave");
    revalidatePath("/calendar");
  });
}
