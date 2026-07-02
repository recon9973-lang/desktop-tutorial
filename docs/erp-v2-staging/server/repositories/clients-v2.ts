// 목표 경로: src/server/repositories/clients.ts 에 병합/추가
//
// 거래처 목록/상세 조회 (V2.1: 업종 색상 + 권한 스코프). 읽기 전용.
import { Role } from "@/domain/types";
import { db } from "@/server/db";
import type { CurrentUser } from "@/server/session";

/** 역할별 거래처 where 조건 (읽기 스코프). ADMIN은 AccessScope 반영. */
async function clientScopeWhere(user: CurrentUser) {
  if (user.role === Role.SUPER_ADMIN) return {};
  if (user.role === Role.MARKETER) return { assignedMarketerId: user.id };
  // ADMIN: allClients | 지정 clientId | 지정/전체 marketer
  const scopes = await db.accessScope.findMany({ where: { adminId: user.id } });
  if (scopes.some((s) => s.allClients || s.allMarketers)) return {};
  const clientIds = scopes.map((s) => s.clientId).filter(Boolean) as string[];
  const marketerIds = scopes.map((s) => s.marketerId).filter(Boolean) as string[];
  return { OR: [{ id: { in: clientIds } }, { assignedMarketerId: { in: marketerIds } }] };
}

export async function listClientsForUser(user: CurrentUser) {
  const where = await clientScopeWhere(user);
  const clients = await db.client.findMany({
    where,
    orderBy: [{ active: "desc" }, { name: "asc" }],
    select: {
      id: true, name: true, code: true, active: true, assignedMarketerId: true,
      industryCategory: { select: { name: true, colorTag: true, parent: { select: { name: true, colorTag: true } } } },
      assignedMarketer: { select: { name: true } },
      billingRecords: { where: { status: { in: ["UNPAID", "PARTIALLY_PAID", "OVERDUE"] } }, select: { id: true }, take: 1 }
    }
  });
  return clients.map((c) => ({
    id: c.id,
    name: c.name,
    code: c.code,
    active: c.active,
    // 하위(진료과)면 그 이름/색, 아니면 대분류
    industryName: c.industryCategory?.name ?? c.industryCategory?.parent?.name ?? null,
    industryColor: c.industryCategory?.colorTag ?? c.industryCategory?.parent?.colorTag ?? null,
    assignedMarketerName: c.assignedMarketer?.name ?? null,
    outstanding: c.billingRecords.length > 0
  }));
}
