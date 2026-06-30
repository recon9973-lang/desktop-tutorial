// 목표 경로: src/server/actions/work.ts
//
// 업무(WorkItem) 쓰기 server actions.
// 상태 전이는 반드시 도메인 nextWorkStatus()를 통과 (불법 전이 차단).
"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { Role, WorkCategory } from "@/domain/types";
import { assertCanAccessClient } from "@/domain/access-control";
import { nextWorkStatus, type WorkStatusAction } from "@/domain/work";
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

/** 업무 접근 권한: 작성/소유자 본인이거나, 거래처 접근 범위를 통과. */
async function assertCanAccessWork(
  user: CurrentUser,
  work: { clientId: string; ownerId: string },
  assignedMarketerId: string | null
) {
  if (user.role === Role.MARKETER && work.ownerId === user.id) return;
  const scopes = await getAdminScopes(user);
  assertCanAccessClient(user, work.clientId, scopes, assignedMarketerId);
}

const createWorkSchema = z.object({
  clientId: z.string().min(1),
  ownerId: z.string().min(1),
  title: z.string().trim().min(1),
  category: z.nativeEnum(WorkCategory),
  priority: z.coerce.number().int().min(1).max(5).optional(),
  dueDate: z.coerce.date().optional().nullable(),
  attachmentUrl: z.string().trim().url().optional().nullable().or(z.literal(""))
});

export async function createWorkItem(input: unknown): Promise<ActionResult<{ id: string }>> {
  return runAction(async () => {
    const user = await requireUser();
    const parsed = createWorkSchema.safeParse(input);
    if (!parsed.success) throw new Error("VALIDATION");
    const data = parsed.data;

    const client = await db.client.findUnique({ where: { id: data.clientId } });
    if (!client) throw new Error("NOT_FOUND");

    const scopes = await getAdminScopes(user);
    assertCanAccessClient(user, data.clientId, scopes, client.assignedMarketerId);

    const meta = await requestMeta();
    const created = await db.$transaction(async (tx) => {
      const work = await tx.workItem.create({
        data: {
          clientId: data.clientId,
          ownerId: data.ownerId,
          createdById: user.id,
          title: data.title,
          category: data.category,
          priority: data.priority ?? 3,
          dueDate: data.dueDate ?? null,
          attachmentUrl: data.attachmentUrl || null
        }
      });
      // 마감일이 있으면 캘린더 이벤트 자동 생성
      if (work.dueDate) {
        await tx.calendarEvent.create({
          data: {
            title: work.title,
            startsAt: work.dueDate,
            endsAt: work.dueDate,
            provider: "INTERNAL",
            kind: "TASK",
            clientId: work.clientId,
            workItemId: work.id
          }
        });
      }
      await recordAudit(tx, {
        actorId: user.id,
        action: "work.create",
        targetType: "WorkItem",
        targetId: work.id,
        afterState: work,
        ...meta
      });
      return work;
    });

    revalidatePath("/work");
    revalidatePath("/calendar");
    return { id: created.id };
  });
}

const changeStatusSchema = z.object({
  id: z.string().min(1),
  action: z.enum(["start", "submit_for_review", "approve", "block", "resume"])
});

export async function changeWorkStatus(input: unknown): Promise<ActionResult<{ status: string }>> {
  return runAction(async () => {
    const user = await requireUser();
    const parsed = changeStatusSchema.safeParse(input);
    if (!parsed.success) throw new Error("VALIDATION");
    const { id, action } = parsed.data;

    const work = await db.workItem.findUnique({
      where: { id },
      include: { client: { select: { assignedMarketerId: true } } }
    });
    if (!work) throw new Error("NOT_FOUND");

    await assertCanAccessWork(user, work, work.client.assignedMarketerId);

    const target = nextWorkStatus(work.status, action as WorkStatusAction);
    if (target === work.status) throw new Error("ILLEGAL_TRANSITION");

    const meta = await requestMeta();
    const updated = await db.$transaction(async (tx) => {
      const after = await tx.workItem.update({
        where: { id },
        data: {
          status: target,
          startedAt: action === "start" && !work.startedAt ? new Date() : undefined,
          completedAt:
            target === "COMPLETED" ? new Date() : action === "resume" ? null : undefined
        }
      });
      await recordAudit(tx, {
        actorId: user.id,
        action: `work.status.${action}`,
        targetType: "WorkItem",
        targetId: id,
        beforeState: { status: work.status },
        afterState: { status: after.status },
        ...meta
      });
      return after;
    });

    revalidatePath("/work");
    return { status: updated.status };
  });
}

const noteSchema = z.object({
  id: z.string().min(1),
  note: z.string().trim().min(1)
});

export async function addProgressNote(input: unknown): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    const parsed = noteSchema.safeParse(input);
    if (!parsed.success) throw new Error("VALIDATION");
    const { id, note } = parsed.data;

    const work = await db.workItem.findUnique({
      where: { id },
      include: { client: { select: { assignedMarketerId: true } } }
    });
    if (!work) throw new Error("NOT_FOUND");

    await assertCanAccessWork(user, work, work.client.assignedMarketerId);

    const stamp = new Date().toISOString().slice(0, 16).replace("T", " ");
    const line = `[${stamp}] ${user.name}: ${note}`;
    const merged = work.progressNotes ? `${work.progressNotes}\n${line}` : line;

    const meta = await requestMeta();
    await db.$transaction(async (tx) => {
      await tx.workItem.update({ where: { id }, data: { progressNotes: merged } });
      await recordAudit(tx, {
        actorId: user.id,
        action: "work.addNote",
        targetType: "WorkItem",
        targetId: id,
        afterState: { note: line },
        ...meta
      });
    });

    revalidatePath("/work");
  });
}

const updateWorkSchema = z.object({
  id: z.string().min(1),
  title: z.string().trim().min(1).optional(),
  category: z.nativeEnum(WorkCategory).optional(),
  priority: z.coerce.number().int().min(1).max(5).optional(),
  dueDate: z.coerce.date().optional().nullable(),
  attachmentUrl: z.string().trim().url().optional().nullable().or(z.literal(""))
});

export async function updateWorkItem(input: unknown): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    const parsed = updateWorkSchema.safeParse(input);
    if (!parsed.success) throw new Error("VALIDATION");
    const { id, ...fields } = parsed.data;

    const work = await db.workItem.findUnique({
      where: { id },
      include: { client: { select: { assignedMarketerId: true } } }
    });
    if (!work) throw new Error("NOT_FOUND");

    await assertCanAccessWork(user, work, work.client.assignedMarketerId);

    const meta = await requestMeta();
    await db.$transaction(async (tx) => {
      const after = await tx.workItem.update({
        where: { id },
        data: {
          title: fields.title ?? undefined,
          category: fields.category ?? undefined,
          priority: fields.priority ?? undefined,
          dueDate: fields.dueDate ?? undefined,
          attachmentUrl:
            fields.attachmentUrl === undefined ? undefined : fields.attachmentUrl || null
        }
      });
      // 마감일 변경 시 캘린더 이벤트 동기화
      if (fields.dueDate !== undefined) {
        if (after.dueDate) {
          const existing = await tx.calendarEvent.findFirst({
            where: { workItemId: id, kind: "TASK" }
          });
          if (existing) {
            await tx.calendarEvent.update({
              where: { id: existing.id },
              data: { startsAt: after.dueDate, endsAt: after.dueDate, title: after.title }
            });
          } else {
            await tx.calendarEvent.create({
              data: {
                title: after.title,
                startsAt: after.dueDate,
                endsAt: after.dueDate,
                provider: "INTERNAL",
                kind: "TASK",
                clientId: after.clientId,
                workItemId: after.id
              }
            });
          }
        } else {
          await tx.calendarEvent.deleteMany({ where: { workItemId: id, kind: "TASK" } });
        }
      }
      await recordAudit(tx, {
        actorId: user.id,
        action: "work.update",
        targetType: "WorkItem",
        targetId: id,
        beforeState: {
          title: work.title,
          category: work.category,
          priority: work.priority,
          dueDate: work.dueDate
        },
        afterState: after,
        ...meta
      });
    });

    revalidatePath("/work");
    revalidatePath("/calendar");
  });
}

const reassignOwnerSchema = z.object({
  id: z.string().min(1),
  newOwnerId: z.string().min(1)
});

export async function reassignWorkOwner(input: unknown): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    if (user.role !== Role.SUPER_ADMIN && user.role !== Role.ADMIN) {
      throw new Error("FORBIDDEN");
    }
    const parsed = reassignOwnerSchema.safeParse(input);
    if (!parsed.success) throw new Error("VALIDATION");
    const { id, newOwnerId } = parsed.data;

    const work = await db.workItem.findUnique({
      where: { id },
      include: { client: { select: { assignedMarketerId: true } } }
    });
    if (!work) throw new Error("NOT_FOUND");

    const scopes = await getAdminScopes(user);
    assertCanAccessClient(user, work.clientId, scopes, work.client.assignedMarketerId);

    const owner = await db.user.findUnique({ where: { id: newOwnerId } });
    if (!owner || owner.status !== "ACTIVE") throw new Error("INACTIVE_MARKETER");

    const meta = await requestMeta();
    await db.$transaction(async (tx) => {
      await tx.workItem.update({ where: { id }, data: { ownerId: newOwnerId } });
      await recordAudit(tx, {
        actorId: user.id,
        action: "work.reassignOwner",
        targetType: "WorkItem",
        targetId: id,
        beforeState: { ownerId: work.ownerId },
        afterState: { ownerId: newOwnerId },
        ...meta
      });
    });

    revalidatePath("/work");
  });
}
