// 목표 경로: src/components/clients/CredentialField.tsx
//
// 채널계정 자격증명 열람 UI. 기본은 마스킹, "보기" 클릭 시 revealCredentials 호출(감사기록).
// 권한 없는 사용자에겐 버튼이 실패 메시지를 반환.
"use client";

import { useState, useTransition } from "react";
import { revealCredentials } from "@/server/actions/channel-accounts";

export function CredentialField({ accountId, hasCredentials }: { accountId: string; hasCredentials: boolean }) {
  const [pending, start] = useTransition();
  const [creds, setCreds] = useState<{ username: string | null; password: string | null } | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!hasCredentials) return <span className="text-xs text-slate-400">저장된 로그인정보 없음</span>;

  function reveal() {
    setError(null);
    start(async () => {
      const res = await revealCredentials(accountId);
      if (res.ok && res.data) setCreds(res.data);
      else setError(res.ok ? "데이터 없음" : res.error);
    });
  }

  if (creds) {
    return (
      <div className="space-y-1 text-sm">
        <div>아이디: <code className="rounded bg-slate-100 px-1">{creds.username ?? "-"}</code></div>
        <div>비밀번호: <code className="rounded bg-slate-100 px-1">{creds.password ?? "-"}</code></div>
        <button onClick={() => setCreds(null)} className="text-xs text-slate-500 underline">숨기기</button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-slate-400">••••••••</span>
      <button onClick={reveal} disabled={pending} className="rounded border px-2 py-0.5 text-xs disabled:opacity-50">
        {pending ? "확인 중..." : "보기"}
      </button>
      {error && <span className="text-xs text-rose-600">{error}</span>}
    </div>
  );
}
