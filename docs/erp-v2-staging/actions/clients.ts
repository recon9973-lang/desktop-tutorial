// 목표 경로: src/server/actions/clients.ts
//
// 거래처(Client) 쓰기 server actions.
// 모든 액션: 인증 → 권한(AccessScope) → 검증(zod) → 트랜잭션(본변경+AuditLog) → revalidate.
"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { Role, ClientAccountPlatform } from "@/domain/types";
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

function assertManagerRole(role: Role) {
  if (role !== Role.SUPER_ADMIN && role !== Role.ADMIN) {
    throw new Error("FORBIDDEN");
  }
}

const createClientSchema = z.object({
  name: z.string().trim().min(1),
  code: z.string().trim().min(1),
  businessNumber: z.string().trim().optional().nullable(),
  contactName: z.string().trim().optional().nullable(),
  contactEmail: z.string().trim().email().optional().nullable().or(z.literal("")),
  contactPhone: z.string().trim().optional().nullable(),
  contractStartDate: z.coerce.date().optional().nullable(),
  contractEndDate: z.coerce.date().optional().nullable(),
  monthlyContractFee: z.coerce.number().nonnegative().optional().nullable(),
  serviceNotes: z.string().trim().optional().nullable(),
  assignedMarketerId: z.string().trim().optional().nullable()
});

export async function createClient(input: unknown): Promise<ActionResult<{ id: string }>> {
  return runAction(async () => {
    const user = await requireUser();
    assertManagerRole(user.role);

    const parsed = createClientSchema.safeParse(input);
    if (!parsed.success) throw new Error("VALIDATION");
    const data = parsed.data;

    // ADMIN은 자신의 범위 내에서만 생성 가능 (지정 담당자 기준 검증)
    if (user.role === Role.ADMIN) {
      const scopes = await getAdminScopes(user);
      // 신규 거래처는 아직 clientId가 없으므로 담당자 범위로 검증
      assertCanAccessClient(user, "__new__", scopes, data.assignedMarketerId ?? null);
    }

    const exists = await db.client.findUnique({ where: { code: data.code } });
    if (exists) throw new Error("DUPLICATE_CLIENT_CODE");

    const meta = await requestMeta();
    const created = await db.$transaction(async (tx) => {
      const client = await tx.client.create({
        data: {
          name: data.name,
          code: data.code,
          businessNumber: data.businessNumber || null,
          contactName: data.contactName || null,
          contactEmail: data.contactEmail || null,
          contactPhone: data.contactPhone || null,
          contractStartDate: data.contractStartDate ?? null,
          contractEndDate: data.contractEndDate ?? null,
          monthlyContractFee: data.monthlyContractFee ?? null,
          serviceNotes: data.serviceNotes || null,
          assignedMarketerId: data.assignedMarketerId || null
        }
      });
      await recordAudit(tx, {
        actorId: user.id,
        action: "client.create",
        targetType: "Client",
        targetId: client.id,
        afterState: client,
        ...meta
      });
      return client;
    });

    revalidatePath("/clients");
    return { id: created.id };
  });
}

const updateClientSchema = createClientSchema.partial().extend({
  id: z.string().min(1)
});

export async function updateClient(input: unknown): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    const parsed = updateClientSchema.safeParse(input);
    if (!parsed.success) throw new Error("VALIDATION");
    const { id, ...fields } = parsed.data;

    const before = await db.client.findUnique({ where: { id } });
    if (!before) throw new Error("NOT_FOUND");

    const scopes = await getAdminScopes(user);
    assertCanAccessClient(user, id, scopes, before.assignedMarketerId);

    const meta = await requestMeta();
    await db.$transaction(async (tx) => {
      const after = await tx.client.update({
        where: { id },
        data: {
          name: fields.name ?? undefined,
          businessNumber: fields.businessNumber === undefined ? undefined : fields.businessNumber || null,
          contactName: fields.contactName === undefined ? undefined : fields.contactName || null,
          contactEmail: fields.contactEmail === undefined ? undefined : fields.contactEmail || null,
          contactPhone: fields.contactPhone === undefined ? undefined : fields.contactPhone || null,
          contractStartDate: fields.contractStartDate ?? undefined,
          contractEndDate: fields.contractEndDate ?? undefined,
          monthlyContractFee: fields.monthlyContractFee ?? undefined,
          serviceNotes: fields.serviceNotes === undefined ? undefined : fields.serviceNotes || null
        }
      });
      await recordAudit(tx, {
        actorId: user.id,
        action: "client.update",
        targetType: "Client",
        targetId: id,
        beforeState: before,
        afterState: after,
        ...meta
      });
    });

    revalidatePath("/clients");
    revalidatePath(`/clients/${id}`);
  });
}

const reassignSchema = z.object({
  clientId: z.string().min(1),
  newMarketerId: z.string().min(1)
});

/**
 * 담당자 변경. 확정 규칙:
 * - 해당 거래처의 미완 업무(status != COMPLETED)는 새 담당자로 함께 이관.
 * - 다른 거래처 업무/개인 업무는 그대로 유지 (이 액션은 clientId 범위만 건드림).
 */
export async function reassignMarketer(input: unknown): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    assertManagerRole(user.role);

    const parsed = reassignSchema.safeParse(input);
    if (!parsed.success) throw new Error("VALIDATION");
    const { clientId, newMarketerId } = parsed.data;

    const before = await db.client.findUnique({ where: { id: clientId } });
    if (!before) throw new Error("NOT_FOUND");

    const scopes = await getAdminScopes(user);
    assertCanAccessClient(user, clientId, scopes, before.assignedMarketerId);

    const marketer = await db.user.findFirst({
      where: { id: newMarketerId, role: Role.MARKETER }
    });
    if (!marketer || marketer.status !== "ACTIVE") throw new Error("INACTIVE_MARKETER");

    const meta = await requestMeta();
    await db.$transaction(async (tx) => {
      const after = await tx.client.update({
        where: { id: clientId },
        data: { assignedMarketerId: newMarketerId }
      });
      // 거래처 업무 함께 이관 (미완만). 개인 업무는 다른 clientId라 영향 없음.
      const moved = await tx.workItem.updateMany({
        where: { clientId, status: { not: "COMPLETED" } },
        data: { ownerId: newMarketerId }
      });
      await recordAudit(tx, {
        actorId: user.id,
        action: "client.reassignMarketer",
        targetType: "Client",
        targetId: clientId,
        beforeState: { assignedMarketerId: before.assignedMarketerId },
        afterState: { assignedMarketerId: after.assignedMarketerId, movedWorkItems: moved.count },
        ...meta
      });
    });

    revalidatePath("/clients");
    revalidatePath(`/clients/${clientId}`);
    revalidatePath("/work");
  });
}

/** 비활성화 확인용 정보 (차단하지 않음 — UI가 경고로 표시). */
export async function getClientDeactivationInfo(clientId: string) {
  const [unfinishedWork, outstanding, client] = await Promise.all([
    db.workItem.count({ where: { clientId, status: { not: "COMPLETED" } } }),
    db.billingRecord.count({
      where: { clientId, status: { in: ["UNPAID", "PARTIALLY_PAID", "OVERDUE"] } }
    }),
    db.client.findUnique({ where: { id: clientId }, select: { contractEndDate: true } })
  ]);
  return {
    unfinishedWork,
    hasOutstanding: outstanding > 0,
    contractEnded: client?.contractEndDate ? client.contractEndDate < new Date() : false
  };
}

const deactivateSchema = z.object({
  id: z.string().min(1),
  reason: z.string().trim().optional().nullable()
});

export async function deactivateClient(input: unknown): Promise<ActionResult> {
  return runAction(async () => {
    const user = await requireUser();
    assertManagerRole(user.role);

    const parsed = deactivateSchema.safeParse(input);
    if (!parsed.success) throw new Error("VALIDATION");
    const { id, reason } = parsed.data;

    const before = await db.client.findUnique({ where: { id } });
    if (!before) throw new Error("NOT_FOUND");

    const scopes = await getAdminScopes(user);
    assertCanAccessClient(user, id, scopes, before.assignedMarketerId);

    const meta = await requestMeta();
    await db.$transaction(async (tx) => {
      const after = await tx.client.update({ where: { id }, data: { active: false } });
      await recordAudit(tx, {
        actorId: user.id,
        action: "client.deactivate",
        targetType: "Client",
        targetId: id,
        beforeState: { active: before.active },
        afterState: { active: after.active, reason: reason ?? null },
        ...meta
      });
    });

    revalidatePath("/clients");
    revalidatePath(`/clients/${id}`);
  });
}

const addAccountSchema = z.object({
  clientId: z.string().min(1),
  platform: z.nativeEnum(ClientAccountPlatform),
  label: z.string().trim().min(1),
  handle: z.string().trim().optional().nullable(),
  externalUrl: z.string().trim().url().optional().nullable().or(z.literal("")),
  isPrimary: z.boolean().optional()
});

export async function addClientAccount(input: unknown): Promise<ActionResult<{ id: string }>> {
  return runAction(async () => {
    const user = await requireUser();

    const parsed = addAccountSchema.safeParse(input);
    if (!parsed.success) throw new Error("VALIDATION");
    const data = parsed.data;

    const client = await db.client.findUnique({ where: { id: data.clientId } });
    if (!client) throw new Error("NOT_FOUND");

    const scopes = await getAdminScopes(user);
    assertCanAccessClient(user, data.clientId, scopes, client.assignedMarketerId);

    const meta = await requestMeta();
    const created = await db.$transaction(async (tx) => {
      // platform별 primary 1개 보장
      if (data.isPrimary) {
        await tx.clientAccount.updateMany({
          where: { clientId: data.clientId, platform: data.platform, isPrimary: true },
          data: { isPrimary: false }
        });
      }
      const account = await tx.clientAccount.create({
        data: {
          clientId: data.clientId,
          platform: data.platform,
          label: data.label,
          handle: data.handle || null,
          externalUrl: data.externalUrl || null,
          isPrimary: data.isPrimary ?? false,
          managerId: client.assignedMarketerId ?? null
        }
      });
      await recordAudit(tx, {
        actorId: user.id,
        action: "clientAccount.create",
        targetType: "ClientAccount",
        targetId: account.id,
        afterState: account,
        ...meta
      });
      return account;
    });

    revalidatePath(`/clients/${data.clientId}`);
    return { id: created.id };
  });
}
