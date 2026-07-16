"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Heatmap from "./Heatmap";
import MoveTrailMap from "./MoveTrailMap";

type Point = { x: number; y: number; type: string; device: string; label: string | null; dir?: string };
type MovePt = { x: number; y: number; device: string; session: string };
type ScrollSession = { device: string; maxScrollPct: number };

const DEVICES = [
  { key: "ALL", label: "전체" },
  { key: "DESKTOP", label: "🖥 데스크톱" },
  { key: "MOBILE", label: "📱 모바일" },
  { key: "TABLET", label: "태블릿" },
];
const MODES = [
  { key: "click", label: "클릭맵" },
  { key: "move", label: "무브맵" },
  { key: "selector", label: "셀렉터" },
  { key: "scroll", label: "스크롤맵" },
  { key: "gesture", label: "제스처" },
];

export default function HeatmapStudio({
  points,
  gesturePoints = [],
  movePoints = [],
  scrollSessions,
  avgFold,
  siteId,
  path = "/",
  shotDevices = [],
  mapsAll = true,
}: {
  points: Point[];
  gesturePoints?: Point[];
  movePoints?: MovePt[];
  scrollSessions: ScrollSession[];
  avgFold: number;
  siteId: string;
  path?: string;
  shotDevices?: string[]; // 이 페이지에 스크린샷이 있는 기기 목록
  mapsAll?: boolean; // 요금제가 히트맵 5종 전부를 허용하는지 (false면 클릭맵만)
}) {
  const [device, setDevice] = useState("ALL");
  const [mode, setMode] = useState("click");
  const [captured, setCaptured] = useState<Record<string, number>>({}); // 기기별 캡처 버전(캐시버스터)
  const [capturing, setCapturing] = useState(false);
  const [shotErr, setShotErr] = useState("");

  // 모바일 클릭 좌표는 모바일 레이아웃 기준 → 배경도 모바일 캡처를 써야 정확히 얹힌다.
  // 제스처(탭·더블탭·줌·스와이프)는 모바일 전용 동작이므로 항상 모바일 화면을 배경으로.
  const bgDevice = device === "MOBILE" || mode === "gesture" ? "MOBILE" : "DESKTOP";
  const shotReady = shotDevices.includes(bgDevice) || !!captured[bgDevice];
  const bgUrl = shotReady
    ? `/api/sites/${siteId}/screenshot?path=${encodeURIComponent(path)}&device=${bgDevice}&v=${captured[bgDevice] || 0}`
    : undefined;

  async function captureShot() {
    setCapturing(true);
    setShotErr("");
    try {
      const r = await fetch(`/api/sites/${siteId}/screenshot`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ path, device: bgDevice }),
      });
      const d = await r.json();
      if (!r.ok || !d.ok) throw new Error(d.error || "캡처 실패");
      setCaptured((c) => ({ ...c, [bgDevice]: Date.now() }));
    } catch (e) {
      setShotErr((e as Error).message);
    } finally {
      setCapturing(false);
    }
  }

  // 배경이 없으면 사용자가 버튼을 누르지 않아도 자동으로 캡처한다(기기별 1회 시도).
  // 실패해도 반복 호출하지 않도록 시도 여부를 기록.
  const autoTried = useRef<Record<string, boolean>>({});
  useEffect(() => {
    if (mode !== "click" && mode !== "move") return;
    if (shotReady || capturing) return;
    if (autoTried.current[bgDevice]) return;
    autoTried.current[bgDevice] = true;
    captureShot();
  }, [mode, bgDevice, shotReady, capturing]); // eslint-disable-line react-hooks/exhaustive-deps

  const fPoints = useMemo(() => (device === "ALL" ? points : points.filter((p) => p.device === device)), [points, device]);
  const fGestures = useMemo(
    () => (device === "ALL" ? gesturePoints : gesturePoints.filter((p) => p.device === device)),
    [gesturePoints, device]
  );
  const fMoves = useMemo(
    () => (device === "ALL" ? movePoints : movePoints.filter((p) => p.device === device)),
    [movePoints, device]
  );
  const fSessions = useMemo(
    () => (device === "ALL" ? scrollSessions : scrollSessions.filter((s) => s.device === device)),
    [scrollSessions, device]
  );

  const deviceCounts = useMemo(() => {
    const c: Record<string, number> = { ALL: points.length, DESKTOP: 0, MOBILE: 0, TABLET: 0 };
    for (const p of points) c[p.device] = (c[p.device] ?? 0) + 1;
    return c;
  }, [points]);

  return (
    <div className="card card-pad">
      {/* 디바이스 필터 */}
      <div className="row" style={{ flexWrap: "wrap", marginBottom: 12 }}>
        {DEVICES.map((d) => (
          <button key={d.key} type="button" className={`btn sm ${device === d.key ? "primary" : ""}`} onClick={() => setDevice(d.key)}>
            {d.label} <span style={{ opacity: 0.7 }}>{(deviceCounts[d.key] ?? 0).toLocaleString()}</span>
          </button>
        ))}
      </div>

      {/* 모드 탭 — 요금제에 따라 클릭맵 외에는 잠김 */}
      <div className="tabs" style={{ margin: "0 0 18px" }}>
        {MODES.map((m) => {
          const locked = !mapsAll && m.key !== "click";
          return (
            <button
              key={m.key}
              type="button"
              className={`tab ${mode === m.key ? "active" : ""}`}
              onClick={() => (locked ? undefined : setMode(m.key))}
              title={locked ? "그로우 요금제부터 사용할 수 있습니다" : undefined}
              style={{
                background: "none",
                border: "none",
                borderBottom: mode === m.key ? "2px solid var(--accent)" : "2px solid transparent",
                opacity: locked ? 0.45 : 1,
                cursor: locked ? "not-allowed" : "pointer",
              }}
            >
              {locked ? `🔒 ${m.label}` : m.label}
            </button>
          );
        })}
      </div>
      {!mapsAll && (
        <div className="notice small" style={{ marginBottom: 14 }}>
          무료 체험은 <b>클릭맵</b>만 제공합니다. 무브맵·셀렉터·스크롤맵·제스처는 <b>그로우</b> 요금제부터 사용할 수 있습니다.
        </div>
      )}

      {/* 배경(실제 사이트 화면) 캡처 컨트롤 — 클릭맵·무브맵에서 히트맵이 실제 화면 위에 얹힌다 */}
      {(mode === "click" || mode === "move") && (
        <div style={{ marginBottom: 12 }}>
          <div className="between" style={{ flexWrap: "wrap", gap: 8 }}>
            <span className="muted small">
              {shotReady
                ? `배경: 실제 ${bgDevice === "MOBILE" ? "모바일" : "데스크톱"} 화면 위에 히트맵 표시 중`
                : capturing
                  ? `실제 ${bgDevice === "MOBILE" ? "모바일" : "데스크톱"} 화면을 캡처하는 중… (최대 30초, 끝나면 자동으로 바뀝니다)`
                  : shotErr
                    ? "화면 캡처에 실패했습니다. 다시 시도해 주세요."
                    : `${bgDevice === "MOBILE" ? "모바일" : "데스크톱"} 화면 준비 중…`}
            </span>
            <span className="row" style={{ gap: 8 }}>
              {shotErr && <span className="small" style={{ color: "var(--red)" }}>{shotErr}</span>}
              <button type="button" className="btn sm" onClick={captureShot} disabled={capturing}>
                {capturing ? "캡처 중…" : shotReady ? "화면 새로 캡처" : "다시 시도"}
              </button>
            </span>
          </div>
          {device === "ALL" && (deviceCounts.MOBILE ?? 0) > 0 && (
            <div className="notice small" style={{ marginTop: 8, background: "#fef9e7", borderColor: "#f0d98a", color: "#8a6d00" }}>
              전체 보기는 <b>데스크톱 화면</b>을 배경으로 씁니다. 모바일은 화면 구성이 달라 위치가 어긋날 수 있으니, 위에서 <b>📱 모바일</b>을 선택하면 모바일 화면 위에 정확히 표시됩니다.
            </div>
          )}
        </div>
      )}

      {mode === "click" && <Heatmap points={fPoints.map((p) => ({ x: p.x, y: p.y, type: p.type }))} bgUrl={bgUrl} />}
      {mode === "move" && (
        fMoves.length === 0 ? (
          <div className="muted small" style={{ padding: 24, textAlign: "center" }}>
            마우스 이동 데이터가 아직 없습니다. 데스크톱 방문자의 커서 움직임이 쌓이면 &ldquo;시선 궤적&rdquo;이 표시됩니다.
          </div>
        ) : (
          <>
            <p className="muted small" style={{ margin: "0 0 10px" }}>
              커서가 지나간 <b>궤적(가는 선)</b>과 <b>머문 지점(검은 점)</b> — 클릭 안 해도 사용자의 시선 흐름·체류를 파악. 총 {fMoves.length.toLocaleString()} 샘플
            </p>
            <MoveTrailMap points={fMoves.map((p) => ({ x: p.x, y: p.y, session: p.session }))} bgUrl={bgUrl} />
          </>
        )
      )}
      {mode === "selector" && <SelectorRanking points={fPoints} />}
      {mode === "scroll" && <ScrollMap sessions={fSessions} avgFold={avgFold} />}
      {mode === "gesture" && <GestureView taps={fPoints} gestures={fGestures} bgUrl={bgUrl} />}
    </div>
  );
}

// ---- 모바일 제스처 (탭 / 더블탭 / 줌 / 스와이프) ----
function GestureView({ taps, gestures, bgUrl }: { taps: Point[]; gestures: Point[]; bgUrl?: string }) {
  const [g, setG] = useState<"tap" | "double_tap" | "zoom" | "swipe">("tap");
  const doubleTaps = useMemo(() => gestures.filter((p) => p.type === "double_tap"), [gestures]);
  const zooms = useMemo(() => gestures.filter((p) => p.type === "zoom"), [gestures]);
  const swipes = useMemo(() => gestures.filter((p) => p.type === "swipe"), [gestures]);

  const TABS = [
    { key: "tap", label: "탭", n: taps.length },
    { key: "double_tap", label: "더블탭", n: doubleTaps.length },
    { key: "zoom", label: "줌", n: zooms.length },
    { key: "swipe", label: "스와이프", n: swipes.length },
  ] as const;

  const current = g === "tap" ? taps : g === "double_tap" ? doubleTaps : g === "zoom" ? zooms : swipes;

  const zoomIn = zooms.filter((z) => z.dir === "in").length;
  const zoomOut = zooms.filter((z) => z.dir === "out").length;
  const swipeDir = { up: 0, down: 0, left: 0, right: 0 } as Record<string, number>;
  swipes.forEach((s) => { if (s.dir && s.dir in swipeDir) swipeDir[s.dir]++; });

  return (
    <div>
      <div className="notice small" style={{ marginBottom: 12 }}>
        📱 모바일 제스처 히트맵. <b>탭</b>은 콘텐츠 선택, <b>줌</b>은 자세히 보려는 관심, <b>스와이프</b>는 탐색 노력을 나타냅니다.
      </div>
      <div className="row" style={{ flexWrap: "wrap", marginBottom: 14 }}>
        {TABS.map((t) => (
          <button key={t.key} type="button" className={`btn sm ${g === t.key ? "primary" : ""}`} onClick={() => setG(t.key)}>
            {t.label} <span style={{ opacity: 0.7 }}>{t.n.toLocaleString()}</span>
          </button>
        ))}
      </div>

      {g === "zoom" && (
        <div className="row" style={{ gap: 8, marginBottom: 12 }}>
          <span className="badge low">줌 인 {zoomIn}</span>
          <span className="badge gray">줌 아웃 {zoomOut}</span>
          <span className="muted small">확대(줌 인)가 많은 곳은 이미지·글자가 작아 확대해 보려는 지점입니다.</span>
        </div>
      )}
      {g === "swipe" && (
        <div className="row" style={{ gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
          <span className="badge gray">↑ 위 {swipeDir.up}</span>
          <span className="badge gray">↓ 아래 {swipeDir.down}</span>
          <span className="badge gray">← 왼쪽 {swipeDir.left}</span>
          <span className="badge gray">→ 오른쪽 {swipeDir.right}</span>
          <span className="muted small">좌우 스와이프가 많으면 캐러셀·가로 콘텐츠 탐색 신호입니다.</span>
        </div>
      )}

      {current.length === 0 ? (
        <div className="muted small" style={{ padding: 20, textAlign: "center" }}>이 제스처 데이터가 아직 없습니다. (모바일/태블릿 방문에서 수집됩니다)</div>
      ) : (
        <Heatmap points={current.map((p) => ({ x: p.x, y: p.y, type: p.type }))} bgUrl={bgUrl} hideFilters />
      )}
    </div>
  );
}

// ---- 셀렉터 랭킹 (가장 많이 클릭된 요소) ----
function SelectorRanking({ points }: { points: Point[] }) {
  const ranked = useMemo(() => {
    const map = new Map<string, number>();
    let total = 0;
    for (const p of points) {
      const label = (p.label || "").trim();
      if (!label || label.startsWith("[")) continue; // 입력요소 placeholder 제외
      map.set(label, (map.get(label) ?? 0) + 1);
      total++;
    }
    const arr = [...map.entries()].map(([label, count]) => ({ label, count, pct: total ? (count / total) * 100 : 0 }));
    arr.sort((a, b) => b.count - a.count);
    return { list: arr.slice(0, 12), total };
  }, [points]);

  if (ranked.list.length === 0) return <div className="muted small">클릭된 요소 라벨이 아직 없습니다.</div>;

  return (
    <div>
      <div className="between" style={{ marginBottom: 12 }}>
        <b>가장 많이 클릭된 요소</b>
        <span className="muted small">{ranked.total.toLocaleString()} clicks 기준</span>
      </div>
      <div className="stack" style={{ gap: 4 }}>
        {ranked.list.map((r, i) => (
          <div key={r.label} className="row" style={{ gap: 10, padding: "8px 4px", borderBottom: "1px solid var(--border)" }}>
            <span className="badge low" style={{ minWidth: 24, justifyContent: "center" }}>{i + 1}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="between">
                <b className="small" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.label}</b>
                <span className="small muted" style={{ flexShrink: 0 }}>{r.count.toLocaleString()} · {r.pct.toFixed(1)}%</span>
              </div>
              <div className="bar-track" style={{ marginTop: 5, height: 6 }}>
                <div className="bar-fill" style={{ width: `${r.pct}%` }} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---- 스크롤맵 (구간별 도달률 + Average Fold) ----
function ScrollMap({ sessions, avgFold }: { sessions: ScrollSession[]; avgFold: number }) {
  const bands = useMemo(() => {
    const total = sessions.length || 1;
    const out = [];
    for (let d = 0; d < 100; d += 10) {
      const reached = sessions.filter((s) => s.maxScrollPct >= d).length;
      out.push({ from: d, to: d + 10, pct: Math.round((reached / total) * 100) });
    }
    return out;
  }, [sessions]);

  // 평균 폴드가 페이지에서 차지하는 대략 위치(첫 화면). 전체를 1000px 가정 스케일로 표시(참고용).
  const foldPctOfView = Math.min(90, Math.max(8, Math.round((avgFold / 1600) * 100)));

  function heat(pct: number) {
    // 도달률 높음=따뜻함(주황), 낮음=옅음
    const t = pct / 100;
    const r = Math.round(255);
    const g = Math.round(120 + (1 - t) * 110);
    const b = Math.round(60 + (1 - t) * 150);
    const a = 0.25 + t * 0.6;
    return `rgba(${r},${g},${b},${a})`;
  }

  return (
    <div className="grid" style={{ gridTemplateColumns: "1fr 260px", gap: 18 }}>
      <div style={{ position: "relative", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
        {bands.map((band) => (
          <div key={band.from} style={{ position: "relative", height: 48, background: heat(band.pct), display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 14px", borderBottom: "1px solid rgba(255,255,255,0.5)" }}>
            <span className="small" style={{ fontWeight: 600 }}>{band.from}~{band.to}% 지점</span>
            <span className="small" style={{ fontWeight: 700 }}>{band.pct}% 도달</span>
          </div>
        ))}
        {/* Average Fold 라인 */}
        <div style={{ position: "absolute", left: 0, right: 0, top: `${foldPctOfView}%`, borderTop: "2px dashed #12141d" }}>
          <span className="pill" style={{ position: "absolute", right: 10, top: -12, background: "#12141d", color: "#fff" }}>Average Fold ≈ {avgFold}px</span>
        </div>
      </div>
      <div>
        <div className="notice small" style={{ marginBottom: 12 }}>
          위에서 아래로 갈수록 도달하는 방문자가 줄어듭니다. <b>Average Fold</b>(평균 첫 화면) 아래로 급감한다면 핵심 콘텐츠를 위로 올리세요.
        </div>
        <div className="stack" style={{ gap: 8 }}>
          <Stat label="분석 세션" value={sessions.length.toLocaleString()} />
          <Stat label="50% 지점 도달" value={`${bands[5]?.pct ?? 0}%`} />
          <Stat label="90% 지점 도달" value={`${bands[9]?.pct ?? 0}%`} />
          <Stat label="평균 첫 화면 높이" value={`${avgFold}px`} />
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="between" style={{ background: "var(--surface-2)", padding: "8px 12px", borderRadius: 8 }}>
      <span className="small muted">{label}</span>
      <b className="small">{value}</b>
    </div>
  );
}
