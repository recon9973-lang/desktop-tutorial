// 목표 경로: src/components/settings/MasterManager.tsx
//
// 마스터(업무 카테고리 예시) 관리 UI. 추가/수정/색상 + 최고관리자 잠금 토글.
// 업종/채널도 동일 패턴으로 재사용 가능.
"use client";

import { useState, useTransition } from "react";
import { upsertWorkCategory, setMasterLock } from "@/server/actions/masters";

type Item = { id: string; name: string; group: string; colorTag: string | null; isLocked: boolean };

export function MasterManager({ items, isSuperAdmin }: { items: Item[]; isSuperAdmin: boolean }) {
  const [pending, start] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState({ name: "", group: "블로그", colorTag: "#533afd" });

  function add() {
    setError(null);
    start(async () => {
      const res = await upsertWorkCategory(draft);
      if (!res.ok) setError(res.error);
      else setDraft({ name: "", group: draft.group, colorTag: draft.colorTag });
    });
  }

  function toggleLock(id: string, locked: boolean) {
    start(async () => {
      const res = await setMasterLock({ kind: "workCategory", id, locked });
      if (!res.ok) setError(res.error);
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end gap-2">
        <label className="block"><span className="text-xs text-slate-500">이름</span>
          <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} className="mt-1 rounded border px-2 py-1" />
        </label>
        <label className="block"><span className="text-xs text-slate-500">그룹</span>
          <input value={draft.group} onChange={(e) => setDraft({ ...draft, group: e.target.value })} className="mt-1 rounded border px-2 py-1 w-24" />
        </label>
        <label className="block"><span className="text-xs text-slate-500">색상</span>
          <input type="color" value={draft.colorTag} onChange={(e) => setDraft({ ...draft, colorTag: e.target.value })} className="mt-1 h-8 w-10 rounded border" />
        </label>
        <button onClick={add} disabled={pending || !draft.name} className="rounded bg-[#533afd] px-3 py-1.5 text-sm text-white disabled:opacity-50">추가</button>
      </div>
      {error && <p className="text-sm text-rose-600">{error}</p>}

      <table className="w-full text-sm">
        <thead><tr className="text-left text-slate-500"><th className="py-2">카테고리</th><th>그룹</th><th>색</th><th>상태</th><th /></tr></thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.id} className="border-t">
              <td className="py-2">{it.name}</td>
              <td>{it.group}</td>
              <td><span className="inline-block h-4 w-4 rounded" style={{ background: it.colorTag ?? "#ccc" }} /></td>
              <td>{it.isLocked ? <span className="text-xs text-amber-600">🔒 잠김</span> : <span className="text-xs text-slate-400">편집가능</span>}</td>
              <td className="text-right">
                {isSuperAdmin && (
                  <button onClick={() => toggleLock(it.id, !it.isLocked)} disabled={pending} className="rounded border px-2 py-0.5 text-xs">
                    {it.isLocked ? "잠금해제" : "잠금"}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
