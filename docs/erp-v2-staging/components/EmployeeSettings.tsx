// 목표 경로: src/components/settings/EmployeeSettings.tsx
//
// 직원 초대 + 역할 변경 + (최고관리자) 지출 정책 토글.
"use client";

import { useState, useTransition } from "react";
import { inviteEmployee, changeRole, setExpensePolicy } from "@/server/actions/employees";

type Employee = { id: string; name: string; email: string; role: string; status: string };

export function EmployeeSettings({ employees, isSuperAdmin, adminCanManageExpense }: { employees: Employee[]; isSuperAdmin: boolean; adminCanManageExpense: boolean }) {
  const [pending, start] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function invite(formData: FormData) {
    setError(null);
    start(async () => {
      const res = await inviteEmployee({ email: String(formData.get("email")), name: String(formData.get("name")), role: String(formData.get("role")) });
      if (!res.ok) setError(res.error);
    });
  }
  function setRole(userId: string, role: string) {
    start(async () => { const res = await changeRole({ userId, role }); if (!res.ok) setError(res.error); });
  }
  function toggleExpense(v: boolean) {
    start(async () => { const res = await setExpensePolicy({ adminCanManageExpense: v }); if (!res.ok) setError(res.error); });
  }

  return (
    <div className="space-y-6">
      <form action={invite} className="flex items-end gap-2 rounded border p-4">
        <label className="block"><span className="text-xs text-slate-500">이메일</span><input name="email" type="email" required className="mt-1 rounded border px-2 py-1" /></label>
        <label className="block"><span className="text-xs text-slate-500">이름</span><input name="name" required className="mt-1 rounded border px-2 py-1" /></label>
        <label className="block"><span className="text-xs text-slate-500">역할</span>
          <select name="role" className="mt-1 rounded border px-2 py-1"><option value="MARKETER">마케터</option><option value="ADMIN">관리자</option></select>
        </label>
        <button type="submit" disabled={pending} className="rounded bg-[#533afd] px-3 py-1.5 text-sm text-white disabled:opacity-50">초대</button>
      </form>
      {error && <p className="text-sm text-rose-600">{error}</p>}

      <table className="w-full text-sm">
        <thead><tr className="text-left text-slate-500"><th className="py-2">이름</th><th>이메일</th><th>상태</th><th>역할</th></tr></thead>
        <tbody>
          {employees.map((e) => (
            <tr key={e.id} className="border-t">
              <td className="py-2">{e.name}</td>
              <td>{e.email}</td>
              <td><span className="text-xs text-slate-500">{e.status}</span></td>
              <td>
                {e.role === "SUPER_ADMIN" ? (
                  <span className="text-xs text-slate-500">최고관리자</span>
                ) : (
                  <select value={e.role} onChange={(ev) => setRole(e.id, ev.target.value)} disabled={pending} className="rounded border px-2 py-0.5 text-xs">
                    <option value="MARKETER">마케터</option><option value="ADMIN">관리자</option>
                  </select>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {isSuperAdmin && (
        <label className="flex items-center gap-2 rounded border p-4">
          <input type="checkbox" defaultChecked={adminCanManageExpense} onChange={(e) => toggleExpense(e.target.checked)} disabled={pending} />
          <span className="text-sm">관리자에게 회사 지출 등록/검토 권한 허용</span>
        </label>
      )}
    </div>
  );
}
