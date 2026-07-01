// 목표 경로: src/components/dashboard/DashboardCards.tsx
//
// 역할별 대시보드 집계 카드(표시 전용). 집계값은 서버 repository(dashboard.ts)에서 스코프 적용해 주입.
// 재무 카드(미수금/지출)는 마케터에게 숨김.
import type { Role } from "@/domain/types";

export type DashboardStats = {
  totalWork: number;
  delayedWork: number;
  todayWork: number;
  reviewNeeded: number;
  upcomingDeadlines: number;
  assignedClients: number;
  leavePending: number;
  leaveRemaining: number;
  outstanding?: number; // 미수금 (관리자 이상)
  expenseTotal?: number; // 지출 합계 (관리자 이상)
};

function Card({ label, value, tone = "slate" }: { label: string; value: string | number; tone?: string }) {
  const toneMap: Record<string, string> = {
    slate: "text-slate-800", rose: "text-rose-600", amber: "text-amber-600", blue: "text-[#533afd]", green: "text-green-600"
  };
  return (
    <div className="rounded-lg border p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${toneMap[tone]}`}>{value}</div>
    </div>
  );
}

export function DashboardCards({ role, stats }: { role: Role; stats: DashboardStats }) {
  const showFinance = role !== "MARKETER"; // 마케터는 재무 카드 숨김
  const won = (n?: number) => (n == null ? "-" : `${n.toLocaleString()}원`);

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <Card label="전체 업무" value={stats.totalWork} tone="blue" />
      <Card label="지연 업무" value={stats.delayedWork} tone="rose" />
      <Card label="오늘 업무" value={stats.todayWork} />
      <Card label="검수 필요" value={stats.reviewNeeded} tone="amber" />
      <Card label="예정 마감" value={stats.upcomingDeadlines} />
      <Card label="배정 거래처" value={stats.assignedClients} />
      <Card label="휴가 승인대기" value={stats.leavePending} tone="amber" />
      <Card label="잔여 연차" value={`${stats.leaveRemaining}일`} tone="green" />
      {showFinance && <Card label="미수금" value={won(stats.outstanding)} tone="rose" />}
      {showFinance && <Card label="지출 합계" value={won(stats.expenseTotal)} />}
    </div>
  );
}
