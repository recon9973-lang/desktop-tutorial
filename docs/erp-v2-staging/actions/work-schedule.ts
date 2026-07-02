// 목표 경로: src/server/actions/work-schedule.ts
//
// 캘린더 스케줄러 — 업무 예정시간 배치/이동 + 세분화(하위업무) + 워크로드.
// scheduledStart/End 는 마감(dueDate)과 별개. CalendarEvent(TASK) 동기화.
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

async function assertCanAccessWork(
  user: CurrentUser,
  work: { clientId: string; ownerId: string },
  assignedMarketerId: string | null
) {
  if (user.role === Role.MARKETER && work.ownerId === user.id) return;
  const scopes = await getAdminScopes(user);
  assertCanAccessClient(user, work.clientId, scopes, assignedMarketerId);
}

/** CalendarEvent(TASK) 를 예정시간(우선) 또는 마감으로 동기화. */
async function syncTaskEvent(
  tx: Parameters<Parameters<typeof db.$transaction>[0]>[0],
  work: { id: string; title: string; clientId: string; scheduledStart: Date | null; scheduledEnd: Date | null; dueDate: Date | null }
) {
  const start = work.scheduledStart ?? work.dueDate;
  const end = work.scheduledEnd ?? work.dueDate;
  const existing = await tx.calendarEvent.findFirst({ where: { workItemId: work.id, kind: "TASK" } });
  if (!start) {
    if (existing) await tx.calendarEvent.delete({ where: { id: existing.id } });
    return;
  }
  if (existing) {
    await tx.calendarEvent.update({ where: { id: existing.id }, data: { startsAt: start, endsAt: end ?? start, title: work.title } });
  } else {
    await tx.calendarEvent.create({
      data: { title: work.title, startsAt: start, endsAt: end ?? start, provider: "INTERNAL", kind: "TASK", clientId: work.clientId, workItemId: work.id }
    });
  }
}

const scheduleSchema = z.object({
  id: z.string().min(1),
  scheduledStart: z.coerce.date(),
  scheduledEnd: z.coerce.date(),
  estimatedMinutes: z.coerce.number().int().positive().optional()
});

/** 드래그 배치/이동 — 예정시간 세팅 + 캘린더 동기화. */
export async function scheduleWorkItem(input: unknown): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    const p = scheduleSchema.safeParse(input);
    if (!p.success) throw new Error("VALIDATION");
    const d = p.data;
    if (d.scheduledEnd < d.scheduledStart) throw new Error("VALIDATION");

    const work = await db.workItem.findUnique({
      where: { id: d.id },
      include: { client: { select: { assignedMarketerId: true } } }
    });
    if (!work) throw new Error("NOT_FOUND");
    await assertCanAccessWork(user, work, work.client.assignedMarketerId);

    const meta = await requestMeta();
    await db.$transaction(async (tx) => {
      const after = await tx.workItem.update({
        where: { id: d.id },
        data: { scheduledStart: d.scheduledStart, scheduledEnd: d.scheduledEnd, estimatedMinutes: d.estimatedMinutes ?? undefined }
      });
      await syncTaskEvent(tx, after);
      await recordAudit(tx, {
        actorId: user.id, action: "work.schedule",
        targetType: "WorkItem", targetId: d.id,
        afterState: { scheduledStart: after.scheduledStart, scheduledEnd: after.scheduledEnd }, ...meta
      });
    });
    revalidatePath("/calendar");
    revalidatePath("/work");
  });
}

/** 예정시간 해제(미배치 트레이로). */
export async function unscheduleWorkItem(id: string): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    const work = await db.workItem.findUnique({ where: { id }, include: { client: { select: { assignedMarketerId: true } } } });
    if (!work) throw new Error("NOT_FOUND");
    await assertCanAccessWork(user, work, work.client.assignedMarketerId);

    const meta = await requestMeta();
    await db.$transaction(async (tx) => {
      const after = await tx.workItem.update({ where: { id }, data: { scheduledStart: null, scheduledEnd: null } });
      await syncTaskEvent(tx, after);
      await recordAudit(tx, { actorId: user.id, action: "work.unschedule", targetType: "WorkItem", targetId: id, ...meta });
    });
    revalidatePath("/calendar");
    revalidatePath("/work");
  });
}

const subtaskSchema = z.object({
  parentId: z.string().min(1),
  title: z.string().trim().min(1),
  ownerId: z.string().optional(),
  dueDate: z.coerce.date().optional().nullable()
});

/** 하위 업무 생성 — 부모 속성 상속(거래처/카테고리). */
export async function createSubtask(input: unknown): Promise<ActionResult<{ id: string }>> {
  return runAction(async () => {
    const user = await requireUser();
    const p = subtaskSchema.safeParse(input);
    if (!p.success) throw new Error("VALIDATION");
    const d = p.data;

    const parent = await db.workItem.findUnique({
      where: { id: d.parentId },
      include: { client: { select: { assignedMarketerId: true } } }
    });
    if (!parent) throw new Error("NOT_FOUND");
    await assertCanAccessWork(user, parent, parent.client.assignedMarketerId);

    const count = await db.workItem.count({ where: { parentId: d.parentId } });
    const meta = await requestMeta();
    const saved = await db.$transaction(async (tx) => {
      const sub = await tx.workItem.create({
        data: {
          clientId: parent.clientId,
          ownerId: d.ownerId || parent.ownerId,
          createdById: user.id,
          parentId: d.parentId,
          sequence: count,
          title: d.title,
          category: parent.category,
          workCategoryId: parent.workCategoryId ?? undefined,
          priority: parent.priority,
          dueDate: d.dueDate ?? null
        }
      });
      if (sub.dueDate) await syncTaskEvent(tx, sub);
      await recordAudit(tx, { actorId: user.id, action: "work.subtask.create", targetType: "WorkItem", targetId: sub.id, afterState: sub, ...meta });
      return sub;
    });
    revalidatePath("/work");
    return { id: saved.id };
  });
}

/** 담당자 하루 워크로드(예정 분 합계) 조회 — 과부하 경고용. */
export async function getDailyWorkload(input: unknown): Promise<ActionResult<{ minutes: number; capacity: number; over: boolean }>> {
  return runAction(async () => {
    await requireUser();
    const p = z.object({ ownerId: z.string().min(1), day: z.coerce.date() }).safeParse(input);
    if (!p.success) throw new Error("VALIDATION");
    const start = new Date(p.data.day); start.setHours(0, 0, 0, 0);
    const end = new Date(start); end.setDate(end.getDate() + 1);

    const items = await db.workItem.findMany({
      where: { ownerId: p.data.ownerId, scheduledStart: { gte: start, lt: end } },
      select: { estimatedMinutes: true, scheduledStart: true, scheduledEnd: true }
    });
    const minutes = items.reduce((sum, w) => {
      if (w.estimatedMinutes) return sum + w.estimatedMinutes;
      if (w.scheduledStart && w.scheduledEnd) return sum + Math.round((+w.scheduledEnd - +w.scheduledStart) / 60000);
      return sum;
    }, 0);
    const setting = await db.companySetting.findFirst();
    const capacity = setting?.workloadDailyMinutes ?? 480;
    return { minutes, capacity, over: minutes > capacity };
  });
}
