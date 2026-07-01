// 목표 경로: src/components/clients/ClientDetail.tsx
//
// 거래처 상세 — 탭(기본정보/채널계정/업무/입금/보고서). 각 탭에 기존 컴포넌트 조립.
// 재무(입금) 탭은 마케터에게 숨김.
"use client";

import { useState } from "react";
import { CredentialField } from "@/components/clients/CredentialField";

type Channel = { id: string; label: string; channelName: string; externalUrl: string | null; hasCredentials: boolean };
type WorkRow = { id: string; title: string; status: string; dueDate: string | null };
type Billing = { id: string; billingMonth: string; issuedAmount: number; paidAmount: number; status: string };

export function ClientDetail({
  client, channels, works, billings, canViewFinance
}: {
  client: { id: string; name: string; code: string; industryName: string | null; assignedMarketerName: string | null; active: boolean };
  channels: Channel[];
  works: WorkRow[];
  billings: Billing[];
  canViewFinance: boolean;
}) {
  const tabs = ["기본정보", "채널계정", "업무", ...(canViewFinance ? ["입금"] : []), "보고서"];
  const [tab, setTab] = useState(tabs[0]);

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <h1 className="text-xl font-semibold">{client.name}</h1>
        <span className="text-sm text-slate-400">{client.code}</span>
        {client.industryName && <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">{client.industryName}</span>}
        {!client.active && <span className="text-xs text-slate-400">비활성</span>}
      </div>

      <nav className="mb-4 flex gap-1 border-b">
        {tabs.map((t) => (
          <button key={t} onClick={() => setTab(t)} className={`px-3 py-2 text-sm ${tab === t ? "border-b-2 border-[#533afd] text-[#533afd]" : "text-slate-500"}`}>{t}</button>
        ))}
      </nav>

      {tab === "기본정보" && (
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div><dt className="text-slate-500">담당 마케터</dt><dd>{client.assignedMarketerName ?? "미배정"}</dd></div>
          <div><dt className="text-slate-500">업종</dt><dd>{client.industryName ?? "-"}</dd></div>
        </dl>
      )}

      {tab === "채널계정" && (
        <table className="w-full text-sm">
          <tbody>
            {channels.map((c) => (
              <tr key={c.id} className="border-t">
                <td className="py-2">{c.channelName}</td>
                <td>{c.label}</td>
                <td>{c.externalUrl ? <a href={c.externalUrl} className="text-[#533afd] underline" target="_blank" rel="noreferrer">링크</a> : "-"}</td>
                <td><CredentialField accountId={c.id} hasCredentials={c.hasCredentials} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {tab === "업무" && (
        <table className="w-full text-sm">
          <tbody>
            {works.map((w) => (
              <tr key={w.id} className="border-t"><td className="py-2">{w.title}</td><td>{w.status}</td><td className="text-right text-slate-400">{w.dueDate ?? "-"}</td></tr>
            ))}
          </tbody>
        </table>
      )}

      {tab === "입금" && canViewFinance && (
        <table className="w-full text-sm">
          <tbody>
            {billings.map((b) => (
              <tr key={b.id} className="border-t">
                <td className="py-2">{b.billingMonth}</td>
                <td className="text-right">{b.paidAmount.toLocaleString()} / {b.issuedAmount.toLocaleString()}원</td>
                <td className="text-right">{b.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {tab === "보고서" && <p className="text-sm text-slate-400">보고서 목록은 /reports 에서 관리합니다.</p>}
    </div>
  );
}
