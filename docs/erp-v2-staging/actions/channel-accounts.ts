// 목표 경로: src/server/actions/channel-accounts.ts
//
// 거래처 채널계정 자격증명 CRUD + 감사기록 열람.
// 저장: 암호화(crypto.ts). 열람: 권한(본인거래처/범위/전체) + AuditLog 필수.
"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { Role } from "@/domain/types";
import { assertCanAccessClient } from "@/domain/access-control";
import { db } from "@/server/db";
import { encryptSecret, decryptSecret } from "@/server/crypto";
import {
  getAdminScopes,
  recordAudit,
  requestMeta,
  requireUser,
  runAction,
  type ActionResult
} from "@/server/actions/_helpers";

const upsertSchema = z.object({
  id: z.string().optional(),
  clientId: z.string().min(1),
  channelTypeId: z.string().min(1),
  label: z.string().trim().min(1),
  handle: z.string().trim().optional().nullable(),
  externalUrl: z.string().trim().url().optional().nullable().or(z.literal("")),
  username: z.string().trim().optional().nullable(), // 평문 입력 → 암호화 저장
  password: z.string().optional().nullable(),        // 평문 입력 → 암호화 저장
  isPrimary: z.boolean().optional()
});

/** 채널계정 생성/수정. username/password는 암호화하여 저장. */
export async function upsertChannelAccount(input: unknown): Promise<ActionResult<{ id: string }>> {
  return runAction(async () => {
    const user = await requireUser();
    const parsed = upsertSchema.safeParse(input);
    if (!parsed.success) throw new Error("VALIDATION");
    const d = parsed.data;

    const client = await db.client.findUnique({ where: { id: d.clientId } });
    if (!client) throw new Error("NOT_FOUND");
    const scopes = await getAdminScopes(user);
    assertCanAccessClient(user, d.clientId, scopes, client.assignedMarketerId);

    const meta = await requestMeta();
    const data = {
      clientId: d.clientId,
      channelTypeId: d.channelTypeId,
      label: d.label,
      handle: d.handle || null,
      externalUrl: d.externalUrl || null,
      isPrimary: d.isPrimary ?? false,
      managerId: client.assignedMarketerId ?? null,
      // 값이 넘어온 경우에만 재암호화(빈 문자열이면 유지)
      ...(d.username !== undefined && d.username !== "" ? { usernameEnc: encryptSecret(d.username) } : {}),
      ...(d.password !== undefined && d.password !== "" ? { passwordEnc: encryptSecret(d.password) } : {})
    };

    const saved = await db.$transaction(async (tx) => {
      if (d.isPrimary) {
        await tx.clientAccount.updateMany({
          where: { clientId: d.clientId, channelTypeId: d.channelTypeId, isPrimary: true },
          data: { isPrimary: false }
        });
      }
      const acc = d.id
        ? await tx.clientAccount.update({ where: { id: d.id }, data })
        : await tx.clientAccount.create({ data });
      await recordAudit(tx, {
        actorId: user.id,
        action: d.id ? "channelAccount.update" : "channelAccount.create",
        targetType: "ClientAccount",
        targetId: acc.id,
        // 자격증명 평문은 감사로그에도 남기지 않음 — 변경 여부만 기록
        afterState: { label: acc.label, channelTypeId: acc.channelTypeId, credChanged: d.username !== undefined || d.password !== undefined },
        ...meta
      });
      return acc;
    });

    revalidatePath(`/clients/${d.clientId}`);
    return { id: saved.id };
  });
}

/**
 * 자격증명 평문 열람. 권한(본인거래처/범위/전체) 통과 + 열람 감사기록 필수.
 * 반환값은 호출 즉시 화면에만 사용하고 저장/로그 금지.
 */
export async function revealCredentials(accountId: string): Promise<ActionResult<{ username: string | null; password: string | null }>> {
  return runAction(async () => {
    const user = await requireUser();
    const acc = await db.clientAccount.findUnique({
      where: { id: accountId },
      include: { client: { select: { id: true, assignedMarketerId: true } } }
    });
    if (!acc) throw new Error("NOT_FOUND");

    // 마케터는 본인 배정 거래처만, 관리자는 범위, 최고관리자는 전체
    const scopes = await getAdminScopes(user);
    assertCanAccessClient(user, acc.client.id, scopes, acc.client.assignedMarketerId);

    const meta = await requestMeta();
    // 열람 자체를 감사기록 (본 변경 없이 로그만)
    await db.auditLog.create({
      data: {
        actorId: user.id,
        action: "channelAccount.revealCredentials",
        targetType: "ClientAccount",
        targetId: accountId,
        afterState: { revealedBy: user.id, role: user.role },
        ipAddress: meta.ipAddress,
        userAgent: meta.userAgent
      }
    });

    return {
      username: decryptSecret(acc.usernameEnc),
      password: decryptSecret(acc.passwordEnc)
    };
  });
}
