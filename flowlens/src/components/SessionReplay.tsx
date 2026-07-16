"use client";

import { useEffect, useMemo, useRef, useState } from "react";

export type ReplayEvent = {
  type: string;
  xRel: number | null;
  yRel: number | null;
  scrollPct: number | null;
  path: string;
  targetLabel: string | null;
  ts: number; // epoch ms
};

const TYPE_LABEL: Record<string, string> = {
  page_view: "페이지 진입",
  click: "클릭",
  rage_click: "좌절 클릭",
  dead_click: "반응 없는 클릭",
  scroll: "스크롤",
  form_focus: "폼 입력 시작",
  form_submit: "폼 제출",
  cta_view: "CTA 노출",
  cta_click: "CTA 클릭",
  conversion: "전환",
  session_end: "세션 종료",
  pointer_sample: "마우스 이동",
  double_tap: "더블탭",
  zoom: "확대/축소",
  swipe: "스와이프",
};
const TYPE_COLOR: Record<string, string> = {
  click: "#1d4ed8",
  rage_click: "#ef4444",
  dead_click: "#eab308",
  conversion: "#12a150",
  cta_view: "#22c55e",
};

// 개인정보 안전한 "세션 리플레이": DOM을 녹화하지 않고, 수집된 이벤트를
// 시간순으로 재생한다. 클릭 위치·스크롤 깊이·폼 신호를 스케치 위에 애니메이션.
export default function SessionReplay({ events, device, siteId, path = "/" }: { events: ReplayEvent[]; device: string; siteId: string; path?: string }) {
  const positioned = useMemo(
    () => events.filter((e) => e.xRel != null && e.yRel != null),
    [events]
  );

  // ---- 실제 사이트 화면 배경 (기기별). 없으면 자동 캡처 후 다시 시도. ----
  const wrapRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [w, setW] = useState(600);
  const [bgAspect, setBgAspect] = useState<number | null>(null);
  const [bgError, setBgError] = useState(false);
  const [shotVer, setShotVer] = useState(0);
  const [capturing, setCapturing] = useState(false);
  const autoTried = useRef(false);
  const bgDevice = device === "MOBILE" ? "MOBILE" : "DESKTOP";
  const bgUrl = `/api/sites/${siteId}/screenshot?path=${encodeURIComponent(path)}&device=${bgDevice}&v=${shotVer}`;

  useEffect(() => {
    const el = wrapRef.current;
    if (el) setW(el.clientWidth);
  }, []);

  // 배경 주소가 바뀌면 비율 재계산 (캐시 이미지는 onLoad가 안 뜰 수 있음)
  useEffect(() => {
    setBgError(false);
    const im = imgRef.current;
    if (im && im.complete && im.naturalWidth) setBgAspect(im.naturalHeight / im.naturalWidth);
    else setBgAspect(null);
  }, [bgUrl]);

  // 스크린샷이 없으면(404) 자동으로 캡처하고 재시도 (1회)
  useEffect(() => {
    if (!bgError || autoTried.current || capturing) return;
    autoTried.current = true;
    (async () => {
      setCapturing(true);
      try {
        const r = await fetch(`/api/sites/${siteId}/screenshot`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ path, device: bgDevice }),
        });
        const d = await r.json();
        if (d?.ok) setShotVer(Date.now());
      } catch {
        /* 실패 시 스케치 유지 */
      } finally {
        setCapturing(false);
      }
    })();
  }, [bgError, capturing, siteId, path, bgDevice]);

  const useShot = !bgError;
  const frameH = Math.round(w * (bgAspect ?? (device === "MOBILE" ? 16 / 9 : 5 / 4)));
  const t0 = events.length ? events[0].ts : 0;
  const duration = events.length ? Math.max(1, events[events.length - 1].ts - t0) : 1;

  const [playing, setPlaying] = useState(false);
  const [head, setHead] = useState(0); // 0~duration (ms)
  const raf = useRef<number | null>(null);
  const last = useRef<number>(0);

  useEffect(() => {
    if (!playing) return;
    last.current = performance.now();
    const tick = (now: number) => {
      const dt = (now - last.current) * 4; // 4배속 재생
      last.current = now;
      setHead((h) => {
        const nh = h + dt;
        if (nh >= duration) {
          setPlaying(false);
          return duration;
        }
        return nh;
      });
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [playing, duration]);

  const shownClicks = positioned.filter((e) => e.ts - t0 <= head);
  const currentIndex = Math.max(0, events.filter((e) => e.ts - t0 <= head).length - 1);
  const currentEvent = events[currentIndex];
  const currentScroll = [...events].filter((e) => e.ts - t0 <= head && e.scrollPct != null).pop()?.scrollPct ?? 0;

  function play() {
    if (head >= duration) setHead(0);
    setPlaying(true);
  }

  return (
    <div className="grid" style={{ gridTemplateColumns: "1fr 300px", gap: 18 }}>
      {/* 재생 화면 */}
      <div className="card card-pad">
        <div className="between" style={{ marginBottom: 12 }}>
          <div className="row">
            <button className="btn primary sm" type="button" onClick={() => (playing ? setPlaying(false) : play())}>
              {playing ? "❚❚ 일시정지" : "▶ 재생 (4배속)"}
            </button>
            <button className="btn sm" type="button" onClick={() => { setPlaying(false); setHead(0); }}>처음으로</button>
          </div>
          <span className="pill">{device === "MOBILE" ? "📱 모바일" : device === "TABLET" ? "태블릿" : "🖥 데스크톱"}</span>
        </div>

        {/* 타임라인 스크러버 */}
        <input
          type="range"
          min={0}
          max={duration}
          value={head}
          onChange={(e) => { setPlaying(false); setHead(Number(e.target.value)); }}
          style={{ width: "100%", accentColor: "var(--accent)" }}
        />
        <div className="between small muted" style={{ marginBottom: 12 }}>
          <span>{(head / 1000).toFixed(1)}초</span>
          <span>총 {(duration / 1000).toFixed(1)}초</span>
        </div>

        {capturing && (
          <p className="muted small" style={{ margin: "0 0 8px" }}>실제 {bgDevice === "MOBILE" ? "모바일" : "데스크톱"} 화면을 캡처하는 중… (최대 30초, 끝나면 자동으로 바뀝니다)</p>
        )}

        {/* 실제 화면 + 클릭 마커 */}
        <div
          ref={wrapRef}
          style={{
            position: "relative",
            maxWidth: device === "MOBILE" ? 300 : "100%",
            margin: "0 auto",
            height: frameH,
            background: "repeating-linear-gradient(180deg,#fafafa 0 1px,transparent 1px 48px), #fff",
            border: "1px solid var(--border)",
            borderRadius: 12,
            overflow: "hidden",
          }}
        >
          {useShot ? (
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
            <Sketch />
          )}
          {/* 스크롤 위치 표시선 */}
          <div style={{ position: "absolute", left: 0, right: 0, top: `${currentScroll}%`, height: 2, background: "rgba(29,78,216,0.5)" }}>
            <span className="pill" style={{ position: "absolute", right: 6, top: -20, fontSize: 10 }}>스크롤 {currentScroll}%</span>
          </div>
          {/* 클릭 마커 */}
          {shownClicks.map((e, i) => {
            const isLast = i === shownClicks.length - 1;
            const color = TYPE_COLOR[e.type] ?? "#1d4ed8";
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: `${(e.xRel as number) * 100}%`,
                  top: `${(e.yRel as number) * 100}%`,
                  width: isLast ? 22 : 12,
                  height: isLast ? 22 : 12,
                  marginLeft: isLast ? -11 : -6,
                  marginTop: isLast ? -11 : -6,
                  borderRadius: "50%",
                  background: color,
                  opacity: isLast ? 0.9 : 0.35,
                  border: isLast ? "2px solid #fff" : "none",
                  boxShadow: isLast ? `0 0 0 4px ${color}44` : "none",
                  transition: "all 0.1s",
                }}
              />
            );
          })}
        </div>
      </div>

      {/* 이벤트 로그 */}
      <div className="card card-pad" style={{ maxHeight: 520, overflowY: "auto" }}>
        <h4 style={{ marginBottom: 12 }}>이벤트 타임라인</h4>
        <div className="stack" style={{ gap: 6 }}>
          {events.map((e, i) => {
            const active = i === currentIndex;
            const color = TYPE_COLOR[e.type] ?? "#9aa2ba";
            return (
              <div
                key={i}
                onClick={() => { setPlaying(false); setHead(e.ts - t0); }}
                style={{
                  display: "flex", alignItems: "center", gap: 8, padding: "6px 8px", borderRadius: 8, cursor: "pointer",
                  background: active ? "var(--accent-soft)" : "transparent",
                }}
              >
                <span className="dot-legend" style={{ background: color, flexShrink: 0 }} />
                <span className="small" style={{ fontWeight: active ? 700 : 500 }}>{TYPE_LABEL[e.type] ?? e.type}</span>
                {e.targetLabel && <span className="small muted" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{e.targetLabel}</span>}
                <span className="small muted" style={{ marginLeft: "auto", flexShrink: 0 }}>{((e.ts - t0) / 1000).toFixed(1)}s</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Sketch() {
  const gray = "#eef0f5";
  return (
    <div style={{ position: "absolute", inset: 0, padding: "6% 8%", opacity: 0.7 }} aria-hidden>
      <div style={{ height: 28, background: gray, borderRadius: 8, marginBottom: 14 }} />
      <div style={{ height: 100, background: gray, borderRadius: 10, marginBottom: 14 }} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 14 }}>
        <div style={{ height: 70, background: gray, borderRadius: 10 }} />
        <div style={{ height: 70, background: gray, borderRadius: 10 }} />
      </div>
      <div style={{ height: 38, width: "40%", background: gray, borderRadius: 10, margin: "0 auto 18px" }} />
      <div style={{ height: 160, background: gray, borderRadius: 10 }} />
    </div>
  );
}
