// 목표 경로: src/server/actions/masters.ts
//
// 마스터(업종/업무카테고리/채널) 관리.
// 거버넌스: ADMIN 추가/수정/삭제(잠기지 않은 항목), SUPER_ADMIN 잠금 토글 + 전체.
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
import type { CurrentUser } from "@/server/session";

function assertManager(user: CurrentUser) {
  if (user.role !== Role.SUPER_ADMIN && user.role !== Role.ADMIN) {
    throw new Error("FORBIDDEN");
  }
}

/** 잠긴 항목은 최고관리자만 변경/삭제 가능. */
function assertCanMutateLocked(user: CurrentUser, isLocked: boolean) {
  if (isLocked && user.role !== Role.SUPER_ADMIN) {
    throw new Error("FORBIDDEN"); // 잠긴 항목은 관리자 불가
  }
}

const baseFields = {
  name: z.string().trim().min(1),
  colorTag: z.string().trim().optional().nullable(),
  sortOrder: z.coerce.number().int().optional(),
  isActive: z.boolean().optional()
};

// ── 업종 (2단: parentId) ──────────────────────
const industrySchema = z.object({
  id: z.string().optional(),
  parentId: z.string().optional().nullable(),
  ...baseFields
});

export async function upsertIndustry(input: unknown): Promise<ActionResult<{ id: string }>> {
  return runAction(async () => {
    const user = await requireUser();
    assertManager(user);
    const p = industrySchema.safeParse(input);
    if (!p.success) throw new Error("VALIDATION");
    const d = p.data;

    if (d.id) {
      const before = await db.industryCategory.findUnique({ where: { id: d.id } });
      if (!before) throw new Error("NOT_FOUND");
      assertCanMutateLocked(user, before.isLocked);
    }

    const meta = await requestMeta();
    const saved = await db.$transaction(async (tx) => {
      const row = d.id
        ? await tx.industryCategory.update({
            where: { id: d.id },
            data: {
              name: d.name,
              parentId: d.parentId ?? undefined,
              colorTag: d.colorTag ?? undefined,
              sortOrder: d.sortOrder ?? undefined,
              isActive: d.isActive ?? undefined
            }
          })
        : await tx.industryCategory.create({
            data: {
              name: d.name,
              parentId: d.parentId || null,
              colorTag: d.colorTag || null,
              sortOrder: d.sortOrder ?? 0
            }
          });
      await recordAudit(tx, {
        actorId: user.id,
        action: d.id ? "master.industry.update" : "master.industry.create",
        targetType: "IndustryCategory",
        targetId: row.id,
        afterState: row,
        ...meta
      });
      return row;
    });
    revalidatePath("/settings");
    return { id: saved.id };
  });
}

export async function deleteIndustry(id: string): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    assertManager(user);
    const before = await db.industryCategory.findUnique({ where: { id } });
    if (!before) throw new Error("NOT_FOUND");
    assertCanMutateLocked(user, before.isLocked);

    const meta = await requestMeta();
    await db.$transaction(async (tx) => {
      // 자식(진료과) 존재 시 소프트 비활성 권장 — 여기선 비활성 처리
      await tx.industryCategory.update({ where: { id }, data: { isActive: false } });
      await recordAudit(tx, {
        actorId: user.id, action: "master.industry.deactivate",
        targetType: "IndustryCategory", targetId: id, beforeState: before, ...meta
      });
    });
    revalidatePath("/settings");
  });
}

// ── 업무 카테고리 ─────────────────────────────
const workCatSchema = z.object({
  id: z.string().optional(),
  group: z.string().trim().min(1),
  ...baseFields
});

export async function upsertWorkCategory(input: unknown): Promise<ActionResult<{ id: string }>> {
  return runAction(async () => {
    const user = await requireUser();
    assertManager(user);
    const p = workCatSchema.safeParse(input);
    if (!p.success) throw new Error("VALIDATION");
    const d = p.data;

    if (d.id) {
      const before = await db.workCategoryMaster.findUnique({ where: { id: d.id } });
      if (!before) throw new Error("NOT_FOUND");
      assertCanMutateLocked(user, before.isLocked);
    }

    const meta = await requestMeta();
    const saved = await db.$transaction(async (tx) => {
      const row = d.id
        ? await tx.workCategoryMaster.update({
            where: { id: d.id },
            data: {
              name: d.name, group: d.group,
              colorTag: d.colorTag ?? undefined,
              sortOrder: d.sortOrder ?? undefined,
              isActive: d.isActive ?? undefined
            }
          })
        : await tx.workCategoryMaster.create({
            data: { name: d.name, group: d.group, colorTag: d.colorTag || null, sortOrder: d.sortOrder ?? 0 }
          });
      await recordAudit(tx, {
        actorId: user.id,
        action: d.id ? "master.workCategory.update" : "master.workCategory.create",
        targetType: "WorkCategoryMaster", targetId: row.id, afterState: row, ...meta
      });
      return row;
    });
    revalidatePath("/settings");
    return { id: saved.id };
  });
}

// ── 채널 종류 ─────────────────────────────────
const channelSchema = z.object({ id: z.string().optional(), ...baseFields });

export async function upsertChannelType(input: unknown): Promise<ActionResult<{ id: string }>> {
  return runAction(async () => {
    const user = await requireUser();
    assertManager(user);
    const p = channelSchema.safeParse(input);
    if (!p.success) throw new Error("VALIDATION");
    const d = p.data;

    const meta = await requestMeta();
    const saved = await db.$transaction(async (tx) => {
      const row = d.id
        ? await tx.channelType.update({
            where: { id: d.id },
            data: { name: d.name, colorTag: d.colorTag ?? undefined, sortOrder: d.sortOrder ?? undefined, isActive: d.isActive ?? undefined }
          })
        : await tx.channelType.create({ data: { name: d.name, colorTag: d.colorTag || null, sortOrder: d.sortOrder ?? 0 } });
      await recordAudit(tx, {
        actorId: user.id,
        action: d.id ? "master.channel.update" : "master.channel.create",
        targetType: "ChannelType", targetId: row.id, afterState: row, ...meta
      });
      return row;
    });
    revalidatePath("/settings");
    return { id: saved.id };
  });
}

/** 잠금 토글 — 최고관리자 전용. */
export async function setMasterLock(
  input: unknown
): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    if (user.role !== Role.SUPER_ADMIN) throw new Error("FORBIDDEN");
    const p = z.object({
      kind: z.enum(["industry", "workCategory"]),
      id: z.string().min(1),
      locked: z.boolean()
    }).safeParse(input);
    if (!p.success) throw new Error("VALIDATION");
    const { kind, id, locked } = p.data;

    const meta = await requestMeta();
    await db.$transaction(async (tx) => {
      if (kind === "industry") {
        await tx.industryCategory.update({ where: { id }, data: { isLocked: locked } });
      } else {
        await tx.workCategoryMaster.update({ where: { id }, data: { isLocked: locked } });
      }
      await recordAudit(tx, {
        actorId: user.id, action: `master.${kind}.lock`,
        targetType: kind === "industry" ? "IndustryCategory" : "WorkCategoryMaster",
        targetId: id, afterState: { locked }, ...meta
      });
    });
    revalidatePath("/settings");
  });
}
