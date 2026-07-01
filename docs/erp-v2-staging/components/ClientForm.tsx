// 목표 경로: src/components/clients/ClientForm.tsx
//
// 거래처 등록/수정 폼. 업종 2단(대분류→진료과) + "기타" 수기 + 담당자 배정.
// createClient/updateClient(server action) 호출. 기존 UI shell/스타일에 맞게 조정할 것.
"use client";

import { useState, useTransition } from "react";
import { createClient, updateClient } from "@/server/actions/clients";

type IndustryNode = { id: string; name: string; parentId: string | null; colorTag: string | null };
type Marketer = { id: string; name: string };

export function ClientForm({
  industries,
  marketers,
  initial
}: {
  industries: IndustryNode[];
  marketers: Marketer[];
  initial?: { id: string; name: string; code: string; industryCategoryId?: string | null; industryCustom?: string | null; assignedMarketerId?: string | null };
}) {
  const parents = industries.filter((i) => i.parentId === null);
  const [pending, start] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const initialParent = initial?.industryCategoryId
    ? industries.find((i) => i.id === initial.industryCategoryId)?.parentId ?? initial.industryCategoryId
    : "";
  const [parentId, setParentId] = useState<string>(initialParent ?? "");
  const [childId, setChildId] = useState<string>(
    initial?.industryCategoryId && industries.find((i) => i.id === initial.industryCategoryId)?.parentId ? initial.industryCategoryId : ""
  );
  const children = industries.filter((i) => i.parentId === parentId);
  const isEtc = parents.find((p) => p.id === parentId)?.name === "기타";

  function onSubmit(formData: FormData) {
    setError(null);
    const payload = {
      id: initial?.id,
      name: String(formData.get("name") || ""),
      code: String(formData.get("code") || ""),
      // 하위(진료과)가 있으면 그 id, 없으면 대분류 id
      industryCategoryId: childId || parentId || null,
      industryCustom: isEtc ? String(formData.get("industryCustom") || "") : null,
      assignedMarketerId: String(formData.get("assignedMarketerId") || "") || null,
      contactName: String(formData.get("contactName") || "") || null,
      contactPhone: String(formData.get("contactPhone") || "") || null,
      monthlyContractFee: formData.get("monthlyContractFee") ? Number(formData.get("monthlyContractFee")) : null
    };
    start(async () => {
      const res = initial?.id ? await updateClient(payload) : await createClient(payload);
      if (!res.ok) setError(res.error);
    });
  }

  return (
    <form action={onSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <label className="block">
          <span className="text-sm text-slate-600">거래처명 *</span>
          <input name="name" defaultValue={initial?.name} required className="mt-1 w-full rounded border px-3 py-2" />
        </label>
        <label className="block">
          <span className="text-sm text-slate-600">거래처 코드 *</span>
          <input name="code" defaultValue={initial?.code} required className="mt-1 w-full rounded border px-3 py-2" />
        </label>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <label className="block">
          <span className="text-sm text-slate-600">업종 대분류 *</span>
          <select value={parentId} onChange={(e) => { setParentId(e.target.value); setChildId(""); }} required className="mt-1 w-full rounded border px-3 py-2">
            <option value="">선택</option>
            {parents.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </label>
        {children.length > 0 && (
          <label className="block">
            <span className="text-sm text-slate-600">진료과목 *</span>
            <select value={childId} onChange={(e) => setChildId(e.target.value)} required className="mt-1 w-full rounded border px-3 py-2">
              <option value="">선택</option>
              {children.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
        )}
        {isEtc && (
          <label className="block">
            <span className="text-sm text-slate-600">업종 직접입력 *</span>
            <input name="industryCustom" defaultValue={initial?.industryCustom ?? ""} required className="mt-1 w-full rounded border px-3 py-2" />
          </label>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <label className="block">
          <span className="text-sm text-slate-600">담당 마케터</span>
          <select name="assignedMarketerId" defaultValue={initial?.assignedMarketerId ?? ""} className="mt-1 w-full rounded border px-3 py-2">
            <option value="">미배정</option>
            {marketers.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="text-sm text-slate-600">월 계약금</span>
          <input name="monthlyContractFee" type="number" min="0" className="mt-1 w-full rounded border px-3 py-2" />
        </label>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <label className="block"><span className="text-sm text-slate-600">담당자명</span><input name="contactName" className="mt-1 w-full rounded border px-3 py-2" /></label>
        <label className="block"><span className="text-sm text-slate-600">연락처</span><input name="contactPhone" className="mt-1 w-full rounded border px-3 py-2" /></label>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}
      <button type="submit" disabled={pending} className="rounded bg-[#533afd] px-4 py-2 text-white disabled:opacity-50">
        {pending ? "저장 중..." : initial?.id ? "수정" : "등록"}
      </button>
    </form>
  );
}
