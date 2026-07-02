// 목표 경로: src/components/leave/LeavePanel.tsx
//
// 휴가 신청 폼 + 승인 대기 목록(관리자). requestLeave/approveLeave/rejectLeave 호출.
"use client";

import { useState, useTransition } from "react";
import { requestLeave, approveLeave, rejectLeave } from "@/server/actions/leave";

type Pending = { id: string; requesterName: string; type: string; startDate: string; endDate: string; daysRequested: number };

export function LeavePanel({ pending, canApprove }: { pending: Pending[]; canApprove: boolean }) {
  const [isPending, start] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function submit(formData: FormData) {
    setError(null);
    start(async () => {
      const res = await requestLeave({
        type: String(formData.get("type")),
        startDate: String(formData.get("startDate")),
        endDate: String(formData.get("endDate")),
        reason: String(formData.get("reason") || "")
      });
      if (!res.ok) setError(res.error);
    });
  }

  function decide(id: string, approve: boolean) {
    start(async () => {
      const res = approve ? await approveLeave(id) : await rejectLeave({ id });
      if (!res.ok) setError(res.error);
    });
  }

  return (
    <div className="space-y-6">
      <form action={submit} className="space-y-3 rounded border p-4">
        <h3 className="font-medium">휴가 신청</h3>
        <div className="grid grid-cols-2 gap-3">
          <label className="block"><span className="text-xs text-slate-500">유형</span>
            <select name="type" className="mt-1 w-full rounded border px-2 py-1">
              <option value="ANNUAL">연차</option>
              <option value="HALF_DAY_AM">오전 반차</option>
              <option value="HALF_DAY_PM">오후 반차</option>
              <option value="SICK">병가</option>
              <option value="OTHER">기타</option>
            </select>
          </label>
          <div />
          <label className="block"><span className="text-xs text-slate-500">시작일</span><input name="startDate" type="date" required className="mt-1 w-full rounded border px-2 py-1" /></label>
          <label className="block"><span className="text-xs text-slate-500">종료일</span><input name="endDate" type="date" required className="mt-1 w-full rounded border px-2 py-1" /></label>
        </div>
        <label className="block"><span className="text-xs text-slate-500">사유</span><input name="reason" className="mt-1 w-full rounded border px-2 py-1" /></label>
        {error && <p className="text-sm text-rose-600">{error}</p>}
        <button type="submit" disabled={isPending} className="rounded bg-[#533afd] px-3 py-1.5 text-sm text-white disabled:opacity-50">신청</button>
      </form>

      {canApprove && (
        <div className="rounded border p-4">
          <h3 className="font-medium">승인 대기</h3>
          {pending.length === 0 ? (
            <p className="mt-2 text-sm text-slate-400">대기 중인 휴가 신청이 없습니다.</p>
          ) : (
            <table className="mt-2 w-full text-sm">
              <tbody>
                {pending.map((p) => (
                  <tr key={p.id} className="border-t">
                    <td className="py-2">{p.requesterName}</td>
                    <td>{p.type}</td>
                    <td>{p.startDate}~{p.endDate} ({p.daysRequested}일)</td>
                    <td className="text-right">
                      <button onClick={() => decide(p.id, true)} disabled={isPending} className="mr-2 rounded bg-green-600 px-2 py-0.5 text-xs text-white">승인</button>
                      <button onClick={() => decide(p.id, false)} disabled={isPending} className="rounded bg-rose-600 px-2 py-0.5 text-xs text-white">반려</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
