"use client";

import { useEffect, useRef, useState } from "react";

type Point = { x: number; y: number; type: string };

// 클릭 좌표(0~1 상대값)를 캔버스에 열지도로 렌더링.
// 표준 heatmap 기법: 알파 누적 → 팔레트 색상 매핑.
export default function Heatmap({ points, hideFilters = false, bgUrl, hideControls = false }: { points: Point[]; hideFilters?: boolean; bgUrl?: string; hideControls?: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [filter, setFilter] = useState<"all" | "click" | "dead_click" | "rage_click">("all");
  const [w, setW] = useState(800);
  const [bgAspect, setBgAspect] = useState<number | null>(null); // 배경이미지 높이/폭
  const [bgError, setBgError] = useState(false);
  const [heatOpacity, setHeatOpacity] = useState(0.9); // 히트맵 진하기(오버레이 투명도)
  const [dim, setDim] = useState(false); // 집중 모드: 배경을 어둡게 깔아 핫스팟 강조

  // 배경이 실제 스크린샷이면 그 비율(높이/폭)로, 아니면 기본 세로형(1.25)로 컨테이너 높이 결정.
  // 좌표(0~1)를 이 높이에 곱하므로, 스크린샷 실제 높이에 맞아야 점이 요소 위에 정확히 앉는다.
  const useShot = !!bgUrl && !bgError;
  const h = Math.round(w * (useShot && bgAspect ? bgAspect : 1.25));

  useEffect(() => {
    const el = wrapRef.current;
    if (el) setW(el.clientWidth);
  }, []);

  // 배경이 바뀌면(기기 전환·재캡처) 비율을 다시 계산한다.
  // 캐시된 이미지는 onLoad가 안 뜰 수 있어, 이미 로드됐으면 여기서 직접 읽는다.
  useEffect(() => {
    setBgError(false);
    const im = imgRef.current;
    if (im && im.complete && im.naturalWidth) {
      setBgAspect(im.naturalHeight / im.naturalWidth);
    } else {
      setBgAspect(null);
    }
  }, [bgUrl]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    canvas.width = w;
    canvas.height = h;
    ctx.clearRect(0, 0, w, h);

    const pts = points.filter((p) => filter === "all" || p.type === filter);
    if (pts.length === 0) return;

    const radius = Math.max(16, w * 0.03);

    // 1) 알파 누적 (그레이스케일). 점당 알파를 낮춰 겹칠수록 뜨거워지는 강약을 만든다.
    for (const p of pts) {
      const px = p.x * w;
      const py = p.y * h;
      const g = ctx.createRadialGradient(px, py, 0, px, py, radius);
      g.addColorStop(0, "rgba(0,0,0,0.07)");
      g.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(px, py, radius, 0, Math.PI * 2);
      ctx.fill();
    }

    // 2) 알파 → 색상 팔레트 매핑
    const img = ctx.getImageData(0, 0, w, h);
    const d = img.data;
    for (let i = 0; i < d.length; i += 4) {
      const a = d[i + 3];
      if (a === 0) continue;
      const t = Math.min(1, a / 255);
      const [r, gg, b] = palette(t);
      d[i] = r;
      d[i + 1] = gg;
      d[i + 2] = b;
      d[i + 3] = Math.min(215, 60 + a * 1.6);
    }
    ctx.putImageData(img, 0, 0);
  }, [points, filter, w, h]);

  const counts = {
    all: points.length,
    click: points.filter((p) => p.type === "click").length,
    dead_click: points.filter((p) => p.type === "dead_click").length,
    rage_click: points.filter((p) => p.type === "rage_click").length,
  };

  return (
    <div>
      <div className="row" style={{ marginBottom: 14, flexWrap: "wrap" }}>
        {!hideFilters && (
          <>
            <FilterBtn active={filter === "all"} onClick={() => setFilter("all")}>전체 {counts.all}</FilterBtn>
            <FilterBtn active={filter === "click"} onClick={() => setFilter("click")}>일반 클릭 {counts.click}</FilterBtn>
            <FilterBtn active={filter === "dead_click"} onClick={() => setFilter("dead_click")}>Dead click {counts.dead_click}</FilterBtn>
            <FilterBtn active={filter === "rage_click"} onClick={() => setFilter("rage_click")}>Rage click {counts.rage_click}</FilterBtn>
          </>
        )}
        {useShot && !hideControls && (
          <div className="row small" style={{ gap: 12, alignItems: "center", marginLeft: hideFilters ? 0 : 12 }}>
            <label className="muted" style={{ display: "flex", alignItems: "center", gap: 6 }}>
              진하기
              <input
                type="range"
                min={20}
                max={100}
                value={Math.round(heatOpacity * 100)}
                onChange={(e) => setHeatOpacity(Number(e.currentTarget.value) / 100)}
                style={{ width: 90 }}
              />
            </label>
            <button type="button" className={`btn sm ${dim ? "primary" : ""}`} onClick={() => setDim((v) => !v)}>
              {dim ? "집중 모드 ✓" : "집중 모드"}
            </button>
          </div>
        )}
        <div style={{ marginLeft: "auto" }} className="row small muted">
          <span className="dot-legend" style={{ background: "#3b82f6" }} /> 낮음
          <span className="dot-legend" style={{ background: "#22c55e" }} />
          <span className="dot-legend" style={{ background: "#eab308" }} />
          <span className="dot-legend" style={{ background: "#ef4444" }} /> 높음
        </div>
      </div>
      <div
        ref={wrapRef}
        style={{
          position: "relative",
          background: "repeating-linear-gradient(180deg,#fafafa 0 1px,transparent 1px 60px), #ffffff",
          border: "1px solid var(--border)",
          borderRadius: 12,
          overflow: "hidden",
          height: h,
        }}
      >
        {useShot ? (
          // 실제 사이트 전체페이지 스크린샷을 배경으로. 자연 비율(높이/폭)로 컨테이너를 맞춘다.
          <img
            ref={imgRef}
            src={bgUrl}
            alt=""
            aria-hidden
            onLoad={(e) => {
              const im = e.currentTarget;
              if (im.naturalWidth) setBgAspect(im.naturalHeight / im.naturalWidth);
            }}
            onError={() => setBgError(true)}
            style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "auto", display: "block" }}
          />
        ) : (
          // 스크린샷이 아직 없으면 페이지 스케치로 대체
          <PageSketch />
        )}
        {useShot && dim && (
          // 집중 모드: 배경을 어둡게 깔아 히트(핫스팟)가 도드라지게
          <div aria-hidden style={{ position: "absolute", inset: 0, background: "rgba(8,10,18,0.62)" }} />
        )}
        <canvas ref={canvasRef} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: heatOpacity }} />
      </div>
    </div>
  );
}

function FilterBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button className={`btn sm ${active ? "primary" : ""}`} onClick={onClick} type="button">
      {children}
    </button>
  );
}

// 파랑→청록→초록→노랑→빨강 팔레트
function palette(t: number): [number, number, number] {
  const stops: [number, [number, number, number]][] = [
    [0.0, [59, 130, 246]],
    [0.35, [34, 197, 94]],
    [0.65, [234, 179, 8]],
    [1.0, [239, 68, 68]],
  ];
  for (let i = 1; i < stops.length; i++) {
    if (t <= stops[i][0]) {
      const [t0, c0] = stops[i - 1];
      const [t1, c1] = stops[i];
      const f = (t - t0) / (t1 - t0);
      return [c0[0] + (c1[0] - c0[0]) * f, c0[1] + (c1[1] - c0[1]) * f, c0[2] + (c1[2] - c0[2]) * f].map(Math.round) as [number, number, number];
    }
  }
  return stops[stops.length - 1][1];
}

// 실제 사이트 화면처럼 보이는 배경 목업 — 히트맵이 진짜 페이지 위에 얹힌 것처럼 어우러진다.
function PageSketch() {
  const line = "#dfe3ec";
  const soft = "#eef1f7";
  const bar = (w: string, h = 10, c = line) => <div style={{ width: w, height: h, background: c, borderRadius: 4 }} />;
  return (
    <div style={{ position: "absolute", inset: 0, opacity: 0.85 }} aria-hidden>
      {/* 상단 내비게이션 */}
      <div style={{ height: 46, borderBottom: `1px solid ${line}`, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 5%" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 18, height: 18, borderRadius: 5, background: "#1d4ed8" }} />
          {bar("54px", 9)}
        </div>
        <div style={{ display: "flex", gap: 14 }}>{bar("28px", 8)}{bar("28px", 8)}{bar("28px", 8)}{bar("28px", 8)}</div>
        <div style={{ width: 54, height: 22, borderRadius: 6, background: "#1d4ed8", opacity: 0.85 }} />
      </div>
      {/* 히어로 */}
      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: 20, padding: "7% 6% 5%" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {bar("70%", 20)}{bar("90%", 20)}{bar("55%", 20)}
          <div style={{ height: 8 }} />
          {bar("95%", 8, soft)}{bar("88%", 8, soft)}
          <div style={{ width: 120, height: 34, borderRadius: 8, background: "#22c55e", opacity: 0.6, marginTop: 6 }} />
        </div>
        <div style={{ borderRadius: 14, background: "linear-gradient(135deg,#e4ecfb,#dbe8ff)", minHeight: 150 }} />
      </div>
      {/* 카드 그리드 */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, padding: "0 6% 6%" }}>
        {[0, 1, 2].map((i) => (
          <div key={i} style={{ border: `1px solid ${line}`, borderRadius: 10, padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ height: 46, background: soft, borderRadius: 8 }} />
            {bar("80%", 9)}{bar("60%", 8, soft)}
          </div>
        ))}
      </div>
      {/* 하단 배너 */}
      <div style={{ margin: "0 6%", height: 70, borderRadius: 12, background: "linear-gradient(135deg,#1e3a8a,#1d4ed8)", opacity: 0.18 }} />
    </div>
  );
}
