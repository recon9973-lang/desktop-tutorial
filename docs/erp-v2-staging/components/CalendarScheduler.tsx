// 목표 경로: src/components/calendar/CalendarScheduler.tsx
//
// 담당자 일간 스케줄러(참고 구현). 미배치 트레이 + 시간 배치 + 워크로드 표시.
// HTML5 드래그로 미배치 업무를 시간대에 놓으면 scheduleWorkItem 호출.
"use client";

import { useState, useTransition } from "react";
import { scheduleWorkItem, unscheduleWorkItem } from "@/server/actions/work-schedule";

type Item = { id: string; title: string; scheduledStart: string | null; scheduledEnd: string | null; estimatedMinutes: number | null };

const HOURS = Array.from({ length: 11 }, (_, i) => i + 9); // 9:00~19:00

export function CalendarScheduler({ day, items, capacityMinutes = 480 }: { day: string; items: Item[]; capacityMinutes?: number }) {
  const [pending, start] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const scheduled = items.filter((i) => i.scheduledStart);
  const unscheduled = items.filter((i) => !i.scheduledStart);
  const usedMinutes = scheduled.reduce((s, i) => s + (i.estimatedMinutes ?? (i.scheduledStart && i.scheduledEnd ? Math.round((+new Date(i.scheduledEnd) - +new Date(i.scheduledStart)) / 60000) : 60)), 0);
  const over = usedMinutes > capacityMinutes;

  function dropAt(hour: number, workId: string) {
    setError(null);
    const s = new Date(`${day}T${String(hour).padStart(2, "0")}:00:00`);
    const e = new Date(s); e.setHours(e.getHours() + 1);
    start(async () => {
      const res = await scheduleWorkItem({ id: workId, scheduledStart: s.toISOString(), scheduledEnd: e.toISOString(), estimatedMinutes: 60 });
      if (!res.ok) setError(res.error);
    });
  }

  function remove(workId: string) {
    start(async () => { const res = await unscheduleWorkItem(workId); if (!res.ok) setError(res.error); });
  }

  return (
    <div className="grid grid-cols-[200px_1fr] gap-4">
      <aside className="rounded border p-3">
        <h3 className="text-sm font-medium">미배치 업무</h3>
        <div className="mt-2 space-y-1">
          {unscheduled.length === 0 && <p className="text-xs text-slate-400">없음</p>}
          {unscheduled.map((i) => (
            <div key={i.id} draggable onDragStart={(e) => e.dataTransfer.setData("text/plain", i.id)}
              className="cursor-grab rounded bg-slate-100 px-2 py-1 text-xs">{i.title}</div>
          ))}
        </div>
        <div className={`mt-4 rounded px-2 py-1 text-xs ${over ? "bg-rose-100 text-rose-700" : "bg-slate-100 text-slate-600"}`}>
          워크로드 {Math.round(usedMinutes / 60 * 10) / 10}h / {capacityMinutes / 60}h {over && "⚠️ 과부하"}
        </div>
      </aside>

      <div className="rounded border">
        {error && <p className="p-2 text-sm text-rose-600">{error}</p>}
        {HOURS.map((h) => {
          const at = scheduled.filter((i) => i.scheduledStart && new Date(i.scheduledStart).getHours() === h);
          return (
            <div key={h} onDragOver={(e) => e.preventDefault()} onDrop={(e) => dropAt(h, e.dataTransfer.getData("text/plain"))}
              className="flex min-h-[44px] items-center gap-2 border-b px-2">
              <span className="w-12 text-xs text-slate-400">{h}:00</span>
              {at.map((i) => (
                <span key={i.id} className="rounded bg-[#533afd] px-2 py-0.5 text-xs text-white">
                  {i.title}
                  <button onClick={() => remove(i.id)} disabled={pending} className="ml-1 opacity-70">✕</button>
                </span>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
