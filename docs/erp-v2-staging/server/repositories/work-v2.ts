// 목표 경로: src/server/repositories/work.ts 에 병합/추가
//
// 업무 목록 + 캘린더 스케줄러용 일간 조회 (V2.1: 세분화/예정시간). 읽기 전용.
import { Role } from "@/domain/types";
import { db } from "@/server/db";
import type { CurrentUser } from "@/server/session";

/** 마케터=본인 업무, 그 외=거래처 스코프(단순화: 여기선 owner/거래처 기준). */
function workScopeWhere(user: CurrentUser) {
  if (user.role === Role.MARKETER) return { ownerId: user.id };
  return {}; // SUPER_ADMIN 전체 / ADMIN은 상위에서 clientId 필터와 결합 권장
}

/** 담당자 일간 스케줄러 데이터: 그 날 예정된 업무 + 미배치(마감만 있는) 업무. */
export async function getSchedulerDay(user: CurrentUser, ownerId: string, day: Date) {
  const start = new Date(day); start.setHours(0, 0, 0, 0);
  const end = new Date(start); end.setDate(end.getDate() + 1);

  const items = await db.workItem.findMany({
    where: {
      ownerId,
      status: { not: "COMPLETED" },
      OR: [
        { scheduledStart: { gte: start, lt: end } },
        { scheduledStart: null, dueDate: { not: null } } // 미배치 트레이 후보
      ]
    },
    orderBy: [{ scheduledStart: "asc" }, { sequence: "asc" }],
    select: { id: true, title: true, scheduledStart: true, scheduledEnd: true, estimatedMinutes: true }
  });
  return items.map((i) => ({
    id: i.id,
    title: i.title,
    scheduledStart: i.scheduledStart?.toISOString() ?? null,
    scheduledEnd: i.scheduledEnd?.toISOString() ?? null,
    estimatedMinutes: i.estimatedMinutes
  }));
}

/** 부모-자식 트리(세분화) 목록. */
export async function listWorkTree(user: CurrentUser, clientId?: string) {
  const scope = workScopeWhere(user);
  const parents = await db.workItem.findMany({
    where: { ...scope, parentId: null, ...(clientId ? { clientId } : {}) },
    orderBy: [{ dueDate: "asc" }],
    select: {
      id: true, title: true, status: true, dueDate: true, category: true,
      subtasks: { orderBy: { sequence: "asc" }, select: { id: true, title: true, status: true, dueDate: true, ownerId: true } }
    }
  });
  return parents;
}
