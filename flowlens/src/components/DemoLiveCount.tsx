"use client";

import { useEffect, useState } from "react";

// 데모 페이지에서 "방문자 자신의 행동"이 실시간으로 감지되는 것을 보여준다.
// (특정 사이트의 전체 이벤트 수를 노출하지 않도록, 브라우저에서 내 상호작용만 센다.)
export default function DemoLiveCount() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let n = 0;
    const bump = () => setCount(++n);
    let lastMove = 0;
    let lastScroll = 0;
    const onMove = () => {
      const now = Date.now();
      if (now - lastMove > 300) {
        lastMove = now;
        bump();
      }
    };
    const onScroll = () => {
      const now = Date.now();
      if (now - lastScroll > 300) {
        lastScroll = now;
        bump();
      }
    };
    document.addEventListener("click", bump);
    document.addEventListener("mousemove", onMove);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      document.removeEventListener("click", bump);
      document.removeEventListener("mousemove", onMove);
      window.removeEventListener("scroll", onScroll);
    };
  }, []);

  return (
    <div className="card card-pad between">
      <div>
        <div className="muted small">이 데모에서 감지된 내 행동</div>
        <div style={{ fontSize: 26, fontWeight: 800 }}>{count.toLocaleString()}</div>
      </div>
      <span className="badge high">● 실시간 감지 중</span>
    </div>
  );
}
