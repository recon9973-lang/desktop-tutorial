// 목표 경로: src/components/work/WorkStatusButtons.tsx
//
// 업무 상태전이 버튼. 현재 상태에서 허용된 액션만 노출(도메인 transitionMap 일치).
// changeWorkStatus(server action) 호출.
"use client";

import { useState, useTransition } from "react";
import { changeWorkStatus } from "@/server/actions/work";

type WorkStatus = "NOT_STARTED" | "IN_PROGRESS" | "WAITING" | "REVIEW_NEEDED" | "COMPLETED" | "BLOCKED";
type Action = "start" | "submit_for_review" | "approve" | "block" | "resume";

// 도메인 transitionMap과 동일한 허용표(현재 상태 → 가능한 액션)
const allowed: Record<WorkStatus, { action: Action; label: string; tone: string }[]> = {
  NOT_STARTED: [
    { action: "start", label: "시작", tone: "bg-blue-600" },
    { action: "block", label: "차단", tone: "bg-rose-600" }
  ],
  WAITING: [
    { action: "start", label: "시작", tone: "bg-blue-600" },
    { action: "block", label: "차단", tone: "bg-rose-600" }
  ],
  IN_PROGRESS: [
    { action: "submit_for_review", label: "검수요청", tone: "bg-amber-600" },
    { action: "block", label: "차단", tone: "bg-rose-600" }
  ],
  REVIEW_NEEDED: [
    { action: "approve", label: "완료승인", tone: "bg-green-600" },
    { action: "block", label: "차단", tone: "bg-rose-600" }
  ],
  BLOCKED: [{ action: "resume", label: "재개", tone: "bg-blue-600" }],
  COMPLETED: []
};

export function WorkStatusButtons({ workId, status }: { workId: string; status: WorkStatus }) {
  const [pending, start] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const actions = allowed[status] ?? [];

  if (actions.length === 0) return <span className="text-xs text-slate-400">완료됨</span>;

  function run(action: Action) {
    setError(null);
    start(async () => {
      const res = await changeWorkStatus({ id: workId, action });
      if (!res.ok) setError(res.error);
    });
  }

  return (
    <div className="flex items-center gap-2">
      {actions.map((a) => (
        <button
          key={a.action}
          onClick={() => run(a.action)}
          disabled={pending}
          className={`rounded px-2.5 py-1 text-xs text-white disabled:opacity-50 ${a.tone}`}
        >
          {a.label}
        </button>
      ))}
      {error && <span className="text-xs text-rose-600">{error}</span>}
    </div>
  );
}
