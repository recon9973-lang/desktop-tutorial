"use client";

import { useEffect, useState } from "react";

// 데모 페이지에서 수집 이벤트 수가 실시간으로 늘어나는 것을 보여준다.
export default function DemoLiveCount({ siteKey }: { siteKey: string }) {
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    async function poll() {
      try {
        const r = await fetch(`/api/health/${siteKey}`, { cache: "no-store" });
        const d = await r.json();
        if (alive) setCount(d.eventCount ?? 0);
      } catch {}
    }
    poll();
    const t = setInterval(poll, 2000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [siteKey]);

  return (
    <div className="card card-pad between">
      <div>
        <div className="muted small">이 사이트에 수집된 총 이벤트</div>
        <div style={{ fontSize: 26, fontWeight: 800 }}>{count === null ? "…" : count.toLocaleString()}</div>
      </div>
      <span className="badge high">● 실시간 수집 중</span>
    </div>
  );
}
