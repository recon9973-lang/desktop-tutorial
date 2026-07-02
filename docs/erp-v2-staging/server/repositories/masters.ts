// 목표 경로: src/server/repositories/masters.ts
//
// 마스터/설정 조회 (폼·목록·설정 화면에서 사용). 읽기 전용.
import { db } from "@/server/db";

/** 업종 트리(대분류+하위) — 활성만, 정렬순. ClientForm 캐스케이드용. */
export async function getIndustryTree() {
  return db.industryCategory.findMany({
    where: { isActive: true },
    orderBy: [{ sortOrder: "asc" }, { name: "asc" }],
    select: { id: true, name: true, parentId: true, colorTag: true, isLocked: true }
  });
}

/** 업무 카테고리 — 활성만, 그룹/정렬순. */
export async function getWorkCategories() {
  return db.workCategoryMaster.findMany({
    where: { isActive: true },
    orderBy: [{ sortOrder: "asc" }],
    select: { id: true, name: true, group: true, colorTag: true, isLocked: true }
  });
}

/** 채널 종류 — 활성만. */
export async function getChannelTypes() {
  return db.channelType.findMany({
    where: { isActive: true },
    orderBy: [{ sortOrder: "asc" }],
    select: { id: true, name: true, colorTag: true }
  });
}

/** 회사 설정(싱글턴). 없으면 기본값 관점으로 null. */
export async function getCompanySetting() {
  return db.companySetting.findFirst();
}

/** 지출 관리 권한: 최고관리자 항상, 관리자는 설정 토글에 따름. */
export async function canManageExpense(role: string): Promise<boolean> {
  if (role === "SUPER_ADMIN") return true;
  if (role !== "ADMIN") return false;
  const setting = await db.companySetting.findFirst();
  return setting?.adminCanManageExpense ?? false;
}
