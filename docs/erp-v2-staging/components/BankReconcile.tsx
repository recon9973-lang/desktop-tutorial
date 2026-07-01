// 목표 경로: src/components/finance/BankReconcile.tsx
//
// 입금 반자동 대사 UI. 은행내역 후보매칭 목록 → 버튼으로 확정(confirmBankMatch).
// 마케터는 재무 접근 불가(서버에서 차단). ADMIN 이상 전용 화면에 배치.
"use client";

import { useState, useTransition } from "react";
import { confirmBankMatch } from "@/server/actions/finance";

type Suggestion = {
  bankTxId: string;
  billingId: string;
  score: number;
  bankLabel: string;   // 예: "2026-06-30 · 350,000 · 홍길동"
  billingLabel: string; // 예: "A병원 2026-06 · 잔액 350,000"
};

export function BankReconcile({ suggestions }: { suggestions: Suggestion[] }) {
  const [pending, start] = useTransition();
  const [done, setDone] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  function confirm(s: Suggestion) {
    setError(null);
    start(async () => {
      const res = await confirmBankMatch({ bankTxId: s.bankTxId, billingId: s.billingId });
      if (!res.ok) setError(res.error);
      else setDone((prev) => new Set(prev).add(s.bankTxId));
    });
  }

  if (suggestions.length === 0) return <p className="text-sm text-slate-400">대사할 후보가 없습니다. 은행내역을 먼저 업로드하세요.</p>;

  return (
    <div className="space-y-2">
      {error && <p className="text-sm text-rose-600">{error}</p>}
      <table className="w-full text-sm">
        <thead><tr className="text-left text-slate-500"><th className="py-2">은행 입금내역</th><th>매칭 청구건</th><th>정확도</th><th /></tr></thead>
        <tbody>
          {suggestions.map((s) => {
            const matched = done.has(s.bankTxId);
            return (
              <tr key={`${s.bankTxId}-${s.billingId}`} className="border-t">
                <td className="py-2">{s.bankLabel}</td>
                <td>{s.billingLabel}</td>
                <td>{"★".repeat(Math.min(3, s.score))}</td>
                <td className="text-right">
                  {matched ? (
                    <span className="text-xs text-green-600">✓ 확정됨</span>
                  ) : (
                    <button onClick={() => confirm(s)} disabled={pending} className="rounded bg-[#533afd] px-2.5 py-1 text-xs text-white disabled:opacity-50">
                      대사 확정
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
