// 목표 경로: src/components/reports/ReportEditor.tsx
//
// 보고서 지표 입력(키워드순위 자동수집분 표시 + 수기 지표) + 상태전이 + PDF 다운로드.
"use client";

import { useState, useTransition } from "react";
import { updateReportMetrics, transitionReport } from "@/server/actions/reports";

type Report = {
  id: string;
  status: string;
  metrics: Record<string, unknown> | null;
};

const nextAction: Record<string, { action: "submit" | "approve" | "deliver"; label: string } | null> = {
  DRAFT: { action: "submit", label: "검수요청" },
  REVIEW_NEEDED: { action: "approve", label: "승인" },
  APPROVED: { action: "deliver", label: "전달완료" },
  DELIVERED: null
};

export function ReportEditor({ report }: { report: Report }) {
  const [pending, start] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const metrics = report.metrics ?? {};
  const ranks = Array.isArray((metrics as { keywordRanks?: unknown }).keywordRanks)
    ? (metrics as { keywordRanks: Array<{ keyword: string; rank: number | null }> }).keywordRanks : [];
  const [summary, setSummary] = useState<string>(String((metrics as { summary?: string }).summary ?? ""));
  const [manual, setManual] = useState<string>(JSON.stringify(
    Object.fromEntries(Object.entries(metrics).filter(([k]) => !["keywordRanks", "keywordRanksCollectedAt", "summary"].includes(k))), null, 2
  ));

  function save() {
    setError(null);
    let parsedManual: Record<string, unknown> = {};
    try { parsedManual = manual.trim() ? JSON.parse(manual) : {}; } catch { setError("수기 지표 JSON 형식 오류"); return; }
    const merged = { ...metrics, ...parsedManual, summary };
    start(async () => { const res = await updateReportMetrics({ id: report.id, metrics: merged }); if (!res.ok) setError(res.error); });
  }

  function transition() {
    const na = nextAction[report.status];
    if (!na) return;
    start(async () => { const res = await transitionReport({ id: report.id, action: na.action }); if (!res.ok) setError(res.error); });
  }

  const na = nextAction[report.status];

  return (
    <div className="space-y-4">
      <section>
        <h3 className="font-medium">키워드 순위 (자동수집)</h3>
        <table className="mt-2 w-full text-sm">
          <tbody>
            {ranks.length ? ranks.map((r, i) => (
              <tr key={i} className="border-t"><td className="py-1">{r.keyword}</td><td className="text-right">{r.rank ?? "-"}위</td></tr>
            )) : <tr><td className="py-1 text-slate-400">수집된 데이터 없음</td></tr>}
          </tbody>
        </table>
      </section>

      <label className="block"><span className="text-sm text-slate-600">수기 지표 (JSON)</span>
        <textarea value={manual} onChange={(e) => setManual(e.target.value)} rows={6} className="mt-1 w-full rounded border px-3 py-2 font-mono text-xs" />
      </label>
      <label className="block"><span className="text-sm text-slate-600">요약 코멘트</span>
        <textarea value={summary} onChange={(e) => setSummary(e.target.value)} rows={3} className="mt-1 w-full rounded border px-3 py-2" />
      </label>

      {error && <p className="text-sm text-rose-600">{error}</p>}
      <div className="flex items-center gap-2">
        <button onClick={save} disabled={pending} className="rounded bg-[#533afd] px-4 py-2 text-sm text-white disabled:opacity-50">저장</button>
        {na && <button onClick={transition} disabled={pending} className="rounded bg-green-600 px-4 py-2 text-sm text-white disabled:opacity-50">{na.label}</button>}
        <a href={`/api/reports/${report.id}/pdf`} className="rounded border px-4 py-2 text-sm">PDF 다운로드</a>
        <span className="text-xs text-slate-400">상태: {report.status}</span>
      </div>
    </div>
  );
}
