"use server";

import { revalidatePath } from "next/cache";
import { prisma } from "@/lib/db";
import { getAdminUser } from "@/lib/admin";
import { audit } from "@/lib/audit";
import { PLANS } from "@/lib/plans";
import { syncRetentionForPlan } from "@/lib/billing";

// 모든 액션은 서버에서 실행되며, 매 호출마다 운영자 여부를 다시 확인한다.
// 클라이언트가 보낸 값은 신뢰하지 않는다(운영자 판정은 세션+화이트리스트로만).

async function assertAdmin() {
  const admin = await getAdminUser();
  if (!admin) throw new Error("forbidden");
  return admin;
}

// 요금제 변경. 유료 전환 차단(결제 우회 방지) 정책과 달리, 운영자는 결제 확인 후 수동 반영이 가능하다.
// 보관일은 syncRetentionForPlan 이 "올리기만" 한다 — 다운그레이드로 데이터가 갑자기 삭제되지 않게(docs/08 정책).
export async function adminSetPlan(formData: FormData) {
  const admin = await assertAdmin();
  const agencyId = String(formData.get("agencyId") || "");
  const plan = String(formData.get("plan") || "");
  const target = PLANS.find((p) => p.key === plan);
  if (!agencyId || !target) throw new Error("bad input");

  await prisma.$transaction(async (tx) => {
    await tx.agency.update({ where: { id: agencyId }, data: { plan: target.key } });
    await syncRetentionForPlan(tx, agencyId, target.key);
  });

  await audit(agencyId, "CHANGE_PLAN", {
    userId: admin.id,
    userEmail: admin.email,
    detail: `[ADMIN] ${plan} (보관 최소 ${target.retentionDays}일 보장, 축소 없음)`,
  });
  revalidatePath("/admin");
}

// 체험 기간 연장(+14일). 이미 만료돼 수집이 멈춘 계정을 다시 열 때 쓴다.
export async function adminExtendTrial(formData: FormData) {
  const admin = await assertAdmin();
  const agencyId = String(formData.get("agencyId") || "");
  if (!agencyId) throw new Error("bad input");
  const until = new Date(Date.now() + 14 * 24 * 60 * 60 * 1000);
  await prisma.agency.update({ where: { id: agencyId }, data: { trialEndsAt: until } });
  await audit(agencyId, "CHANGE_PLAN", { userId: admin.id, userEmail: admin.email, detail: `[ADMIN] 체험 +14일` });
  revalidatePath("/admin");
}

// 체험 제한 해제(수집 재개). trialEndsAt을 비워 "체험 아님"으로 만든다(유료 전환 시).
export async function adminClearTrial(formData: FormData) {
  const admin = await assertAdmin();
  const agencyId = String(formData.get("agencyId") || "");
  if (!agencyId) throw new Error("bad input");
  await prisma.agency.update({ where: { id: agencyId }, data: { trialEndsAt: null } });
  await audit(agencyId, "CHANGE_PLAN", { userId: admin.id, userEmail: admin.email, detail: `[ADMIN] 체험 제한 해제` });
  revalidatePath("/admin");
}
