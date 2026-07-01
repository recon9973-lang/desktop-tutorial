// 목표 경로: src/components/clients/ClientList.tsx
//
// 거래처 목록 — 업종 색상 태그 + 담당자/상태 + 상세 링크. 권한 스코프는 서버 조회에서 적용.
"use client";

import Link from "next/link";

type Row = {
  id: string;
  name: string;
  code: string;
  industryName: string | null;
  industryColor: string | null;
  assignedMarketerName: string | null;
  active: boolean;
  latestWorkStatus?: string | null;
  outstanding?: boolean;
};

export function ClientList({ rows }: { rows: Row[] }) {
  if (rows.length === 0) return <p className="text-sm text-slate-400">표시할 거래처가 없습니다.</p>;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-slate-500">
          <th className="py-2">거래처</th><th>업종</th><th>담당자</th><th>상태</th><th>미수금</th><th />
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id} className="border-t">
            <td className="py-2">
              <span className={r.active ? "" : "text-slate-400 line-through"}>{r.name}</span>
              <span className="ml-1 text-xs text-slate-400">{r.code}</span>
            </td>
            <td>
              {r.industryName ? (
                <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs"
                  style={{ background: (r.industryColor ?? "#e2e8f0") + "22", color: r.industryColor ?? "#475569" }}>
                  <span className="h-2 w-2 rounded-full" style={{ background: r.industryColor ?? "#94a3b8" }} />
                  {r.industryName}
                </span>
              ) : <span className="text-slate-300">-</span>}
            </td>
            <td>{r.assignedMarketerName ?? <span className="text-slate-300">미배정</span>}</td>
            <td>{r.active ? <span className="text-xs text-green-600">운영중</span> : <span className="text-xs text-slate-400">비활성</span>}</td>
            <td>{r.outstanding ? <span className="text-xs text-rose-600">있음</span> : <span className="text-xs text-slate-400">-</span>}</td>
            <td className="text-right"><Link href={`/clients/${r.id}`} className="text-xs text-[#533afd] underline">상세</Link></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
