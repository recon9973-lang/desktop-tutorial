"use client";

import { useEffect, useRef, useState } from "react";
import Heatmap from "./Heatmap";

type P = { x: number; y: number; type: string };

// 개선 전/후 시각 비교: 같은 홈 화면(스크린샷) 위에 기간별 클릭 히트맵을 좌우로 나란히.
export default function CompareVisual({
  siteId,
  path,
  prev,
  curr,
  prevLabel,
  currLabel,
  hasScreenshot,
}: {
  siteId: string;
  path: string;
  prev: P[];
  curr: P[];
  prevLabel: string;
  currLabel: string;
  hasScreenshot: boolean;
}) {
  const [shotReady, setShotReady] = useState(hasScreenshot);
  const [shotVer, setShotVer] = useState(0);
  const [capturing, setCapturing] = useState(false);
  const [err, setErr] = useState("");

  // 전후비교는 데스크톱 화면 기준
  const bgUrl = shotReady ? `/api/sites/${siteId}/screenshot?path=${encodeURIComponent(path)}&device=DESKTOP&v=${shotVer}` : undefined;

  async function capture() {
    setCapturing(true);
    setErr("");
    try {
      const r = await fetch(`/api/sites/${siteId}/screenshot`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ path, device: "DESKTOP" }),
      });
      const d = await r.json();
      if (!r.ok || !d.ok) throw new Error(d.error || "캡처 실패");
      setShotReady(true);
      setShotVer(Date.now());
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setCapturing(false);
    }
  }

  // 배경이 없으면 자동으로 캡처 (사용자가 버튼 누를 필요 없음). 실패 시 반복 안 함.
  const autoTried = useRef(false);
  useEffect(() => {
    if (shotReady || capturing || autoTried.current) return;
    autoTried.current = true;
    capture();
  }, [shotReady, capturing]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="card card-pad" style={{ marginBottom: 18 }}>
      <div className="between" style={{ marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
        <div>
          <b>화면 위 전후 비교</b>{" "}
          <span className="muted small">홈 화면 기준 · 기간별 클릭이 어디로 옮겨갔는지 눈으로 비교</span>
        </div>
        <span className="row" style={{ gap: 8 }}>
          {err && <span className="small" style={{ color: "var(--red)" }}>{err}</span>}
          <button type="button" className="btn sm" onClick={capture} disabled={capturing}>
            {capturing ? "캡처 중… (최대 30초)" : shotReady ? "화면 새로 캡처" : "실제 화면 캡처"}
          </button>
        </span>
      </div>

      {!shotReady && (
        <div className="notice small" style={{ marginBottom: 12 }}>
          {capturing ? "실제 홈 화면을 캡처하는 중… (최대 30초, 끝나면 자동으로 바뀝니다)" : "실제 화면을 준비하는 중입니다."}
        </div>
      )}

      <div className="grid grid-2" style={{ gap: 16 }}>
        <div>
          <div className="badge gray" style={{ marginBottom: 8 }}>← {prevLabel} · {prev.length.toLocaleString()} 클릭</div>
          <Heatmap points={prev} bgUrl={bgUrl} hideFilters hideControls />
        </div>
        <div>
          <div className="badge high" style={{ marginBottom: 8 }}>{currLabel} → · {curr.length.toLocaleString()} 클릭</div>
          <Heatmap points={curr} bgUrl={bgUrl} hideFilters hideControls />
        </div>
      </div>
    </div>
  );
}
