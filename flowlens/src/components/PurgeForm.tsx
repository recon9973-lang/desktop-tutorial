"use client";

import { useState } from "react";

// 방문자 데이터 삭제 폼 (되돌릴 수 없으므로 확인 절차 포함).
export default function PurgeForm({ siteId, paths }: { siteId: string; paths: string[] }) {
  const [scope, setScope] = useState("range");

  function confirmSubmit(e: React.FormEvent<HTMLFormElement>) {
    if (!confirm("선택한 데이터를 영구 삭제합니다. 되돌릴 수 없습니다. 진행할까요?")) {
      e.preventDefault();
    }
  }

  return (
    <form action={`/api/sites/${siteId}/purge`} method="post" onSubmit={confirmSubmit}>
      <input type="hidden" name="scope" value={scope} />
      <div className="stack" style={{ gap: 12 }}>
        <Radio v="range" scope={scope} setScope={setScope} label="기간으로 삭제" desc="지정한 날짜 범위의 이벤트 삭제">
          {scope === "range" && (
            <div className="row" style={{ gap: 8, marginTop: 8 }}>
              <input name="from" type="date" className="field-inline" /> <span className="muted">~</span>
              <input name="to" type="date" className="field-inline" />
            </div>
          )}
        </Radio>
        <Radio v="path" scope={scope} setScope={setScope} label="페이지로 삭제" desc="특정 경로의 이벤트만 삭제">
          {scope === "path" && (
            <select name="path" className="field-inline" style={{ marginTop: 8, width: "100%" }}>
              {paths.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          )}
        </Radio>
        <Radio v="session" scope={scope} setScope={setScope} label="세션키로 삭제" desc="특정 방문자 세션 삭제(삭제요청 처리용)">
          {scope === "session" && <input name="sessionKey" placeholder="세션키 (예: seed_xxx 또는 s_xxx)" className="field-inline" style={{ marginTop: 8, width: "100%" }} />}
        </Radio>
        <Radio v="all" scope={scope} setScope={setScope} label="전체 삭제" desc="이 사이트의 모든 방문자 이벤트 삭제" danger />
      </div>

      <button className="btn sm" type="submit" style={{ marginTop: 16, background: "#fdecec", borderColor: "#f5c2c2", color: "#c0362c", fontWeight: 700 }}>
        선택 데이터 영구 삭제
      </button>
    </form>
  );
}

function Radio({ v, scope, setScope, label, desc, danger, children }: { v: string; scope: string; setScope: (s: string) => void; label: string; desc: string; danger?: boolean; children?: React.ReactNode }) {
  const active = scope === v;
  return (
    <label style={{ display: "block", border: `1px solid ${active ? (danger ? "#e5484d" : "var(--accent)") : "var(--border)"}`, borderRadius: 10, padding: "12px 14px", cursor: "pointer", background: active ? (danger ? "#fdecec" : "var(--accent-soft)") : "var(--surface)" }}>
      <div className="row">
        <input type="radio" checked={active} onChange={() => setScope(v)} />
        <b className="small" style={danger ? { color: "#c0362c" } : {}}>{label}</b>
        <span className="muted small">— {desc}</span>
      </div>
      {children}
    </label>
  );
}
