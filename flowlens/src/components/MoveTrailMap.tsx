"use client";

import { useEffect, useRef, useState } from "react";

type MP = { x: number; y: number; session: string };

// 무브맵(블랙 궤적 스타일): 세션별 커서 경로를 가는 선으로 잇고, 머문 곳은 큰 점으로.
// 클릭맵(컬러 열지도)과 대비되는, 시선 궤적/체류 시각화.
export default function MoveTrailMap({ points, bgUrl }: { points: MP[]; bgUrl?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [w, setW] = useState(800);
  const [bgAspect, setBgAspect] = useState<number | null>(null);
  const [bgError, setBgError] = useState(false);

  const useShot = !!bgUrl && !bgError;
  const h = Math.round(w * (useShot && bgAspect ? bgAspect : 1.25));

  useEffect(() => {
    const el = wrapRef.current;
    if (el) setW(el.clientWidth);
  }, []);

  // 배경 전환(기기 변경·재캡처) 시 비율 재계산. 캐시된 이미지는 onLoad가 안 뜰 수 있어 직접 읽는다.
  useEffect(() => {
    setBgError(false);
    const im = imgRef.current;
    if (im && im.complete && im.naturalWidth) setBgAspect(im.naturalHeight / im.naturalWidth);
    else setBgAspect(null);
  }, [bgUrl]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    canvas.width = w;
    canvas.height = h;
    ctx.clearRect(0, 0, w, h);
    if (points.length === 0) return;

    // 1) 세션별 궤적: 점들을 부드러운 곡선(Catmull-Rom 스플라인)으로 이어 실제 마우스 움직임처럼.
    const runs: { x: number; y: number }[][] = [];
    let curSession: string | null = null;
    for (const p of points) {
      if (p.session !== curSession) {
        runs.push([]);
        curSession = p.session;
      }
      runs[runs.length - 1].push({ x: p.x * w, y: p.y * h });
    }
    ctx.lineWidth = 1.1;
    ctx.strokeStyle = "rgba(20,22,30,0.2)";
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    for (const pts of runs) {
      if (pts.length < 2) continue;
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      if (pts.length === 2) {
        ctx.lineTo(pts[1].x, pts[1].y);
      } else {
        // Catmull-Rom → 베지어 변환으로 각 구간을 부드럽게
        for (let i = 0; i < pts.length - 1; i++) {
          const p0 = pts[i - 1] || pts[i];
          const p1 = pts[i];
          const p2 = pts[i + 1];
          const p3 = pts[i + 2] || p2;
          const cp1x = p1.x + (p2.x - p0.x) / 6;
          const cp1y = p1.y + (p2.y - p0.y) / 6;
          const cp2x = p2.x - (p3.x - p1.x) / 6;
          const cp2y = p2.y - (p3.y - p1.y) / 6;
          ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, p2.x, p2.y);
        }
      }
      ctx.stroke();
    }

    // 2) 체류(dwell) 밀도: 셀 격자로 근접 샘플 수를 세어 점 크기에 반영 (머물수록 큰 점)
    const CELL = 0.018;
    const counts = new Map<string, number>();
    for (const p of points) {
      const key = `${Math.floor(p.x / CELL)}:${Math.floor(p.y / CELL)}`;
      counts.set(key, (counts.get(key) || 0) + 1);
    }

    // 3) 점: 오래 머문 곳일수록 크고 진하게
    for (const p of points) {
      const key = `${Math.floor(p.x / CELL)}:${Math.floor(p.y / CELL)}`;
      const c = counts.get(key) || 1;
      const r = Math.min(16, 1.6 + Math.sqrt(c) * 1.7);
      const alpha = Math.min(0.72, 0.28 + c * 0.05);
      ctx.fillStyle = `rgba(12,14,20,${alpha})`;
      ctx.beginPath();
      ctx.arc(p.x * w, p.y * h, r, 0, Math.PI * 2);
      ctx.fill();
    }
  }, [points, w, h]);

  return (
    <div>
      <div className="row small muted" style={{ marginBottom: 12, justifyContent: "flex-end" }}>
        <span className="dot-legend" style={{ background: "#c9ccd6" }} /> 지나감
        <span className="dot-legend" style={{ background: "#3a3f4d" }} />
        <span className="dot-legend" style={{ background: "#0c0e14" }} /> 오래 머묾
      </div>
      <div
        ref={wrapRef}
        style={{
          position: "relative",
          background: "#f4f5f8",
          border: "1px solid var(--border)",
          borderRadius: 12,
          overflow: "hidden",
          height: h,
        }}
      >
        {useShot ? (
          // 실제 화면은 흐리게(회색) 깔아 배경 힌트만 주고, 검은 궤적이 잘 보이게
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
            style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "auto", display: "block", opacity: 0.4, filter: "grayscale(1)" }}
          />
        ) : null}
        {useShot && <div aria-hidden style={{ position: "absolute", inset: 0, background: "rgba(255,255,255,0.35)" }} />}
        <canvas ref={canvasRef} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
      </div>
    </div>
  );
}
