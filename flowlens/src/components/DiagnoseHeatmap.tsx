"use client";

import { useEffect, useState } from "react";

type Check = { key: string; label: string; status: "pass" | "warn" | "fail"; detail: string };

// 진단 결과를 "실제 홈페이지 화면 위 히트맵"으로 시각화한다.
// 방금 수행한 기술/UX 점검 결과를 페이지 레이아웃 위에 열지도(문제=뜨거움/빨강, 주의=주황)로
// 얹어, 어디를 손봐야 하는지 실제 화면 맥락에서 보여준다. (클릭 데이터가 아니라 점검 결과)

const RANK = { pass: 0, warn: 1, fail: 2 } as const;
const WORD = { pass: "양호", warn: "주의", fail: "문제" } as const;
const DOT = { pass: "#0e7c50", warn: "#b7791f", fail: "#d1343f" } as const;

// 페이지 영역 → 화면 좌표(%)와 관련 점검 항목
type Zone = { id: string; label: string; checks: string[]; x: number; y: number; r: number };
const ZONES: Zone[] = [
  { id: "nav", label: "상단 · 보안", checks: ["https", "analytics"], x: 84, y: 8, r: 60 },
  { id: "hero", label: "첫 화면 · 모바일", checks: ["viewport", "size"], x: 32, y: 34, r: 92 },
  { id: "headline", label: "제목 · 설명", checks: ["title", "desc"], x: 30, y: 30, r: 66 },
  { id: "cta", label: "행동 버튼(CTA)", checks: ["cta"], x: 26, y: 52, r: 58 },
  { id: "content", label: "콘텐츠 · 이미지", checks: ["alt"], x: 50, y: 76, r: 84 },
  { id: "form", label: "폼 · 전환", checks: ["form"], x: 78, y: 68, r: 66 },
];

export default function DiagnoseHeatmap({ checks, url }: { checks: Check[]; url?: string }) {
  // 실제 사이트 화면을 배경으로 (도메인당 1회만 캡처해 재사용, IP당 1회 캡처 제한).
  // 준비되면 배경이 바뀌고, 안 되면 목업(SitePage)을 유지한다.
  const [bgDomain, setBgDomain] = useState<string | null>(null);
  const [preparing, setPreparing] = useState(false);

  useEffect(() => {
    if (!url) return;
    let alive = true;
    setPreparing(true);
    setBgDomain(null);
    (async () => {
      try {
        const r = await fetch("/api/diagnose/screenshot", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ url }),
        });
        const d = await r.json();
        if (alive && d?.ok && d?.ready && d?.domain) setBgDomain(d.domain);
      } catch {
        /* 실패 시 목업 유지 */
      } finally {
        if (alive) setPreparing(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [url]);

  const bgUrl = bgDomain ? `/api/diagnose/screenshot?domain=${encodeURIComponent(bgDomain)}` : null;

  const byKey = new Map(checks.map((c) => [c.key, c]));
  const zones = ZONES.map((z) => {
    const zChecks = z.checks.map((k) => byKey.get(k)).filter(Boolean) as Check[];
    let status: "pass" | "warn" | "fail" = "pass";
    for (const c of zChecks) if (RANK[c.status] > RANK[status]) status = c.status;
    return { ...z, status, zChecks };
  });

  const counts = {
    pass: checks.filter((c) => c.status === "pass").length,
    warn: checks.filter((c) => c.status === "warn").length,
    fail: checks.filter((c) => c.status === "fail").length,
  };
  const hottest = [...zones].sort((a, b) => RANK[b.status] - RANK[a.status])[0];

  // 문제/주의 영역만 열로 표시 (양호는 시원하게)
  function blob(status: "pass" | "warn" | "fail") {
    if (status === "fail") return "radial-gradient(circle, rgba(239,68,68,0.62), rgba(234,179,8,0.32) 45%, transparent 72%)";
    if (status === "warn") return "radial-gradient(circle, rgba(234,179,8,0.5), rgba(234,179,8,0.18) 55%, transparent 76%)";
    return "radial-gradient(circle, rgba(34,197,94,0.28), transparent 70%)";
  }

  return (
    <div>
      {/* 요약 칩 */}
      <div className="row" style={{ gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
        <span className="badge high">양호 {counts.pass}</span>
        <span className="badge medium">주의 {counts.warn}</span>
        <span className="badge low" style={{ background: "#fdecec", color: "#d1343f" }}>문제 {counts.fail}</span>
        <span className="muted small" style={{ marginLeft: "auto" }}>
          <span className="dot-legend" style={{ background: "#22c55e" }} /> 양호
          <span className="dot-legend" style={{ background: "#eab308", marginLeft: 8 }} />
          <span className="dot-legend" style={{ background: "#ef4444", marginLeft: 4 }} /> 뜨거움(문제)
        </span>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 300px", gap: 16 }}>
        {/* 실제 홈페이지 화면 위 히트맵 */}
        <div>
        <div className="diag-browser">
          <div className="diag-browser-bar"><span className="diag-dot" /><span className="diag-dot" /><span className="diag-dot" /></div>
          <div style={{ position: "relative", height: 320 }}>
            {bgUrl ? (
              // 실제 사이트 상단 화면 (브라우저 창처럼 보이도록 위쪽 기준으로 맞춤)
              <img
                src={bgUrl}
                alt=""
                aria-hidden
                onError={() => setBgDomain(null)}
                style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", objectPosition: "top" }}
              />
            ) : (
              <SitePage />
            )}
            {preparing && (
              <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", background: "rgba(255,255,255,0.72)", zIndex: 2 }}>
                <span className="small muted">화면을 준비 중입니다…</span>
              </div>
            )}
            {zones.map((z) => (
              <div key={z.id} style={{ position: "absolute", left: `${z.x}%`, top: `${z.y}%`, width: z.r, height: z.r, transform: "translate(-50%,-50%)", borderRadius: "50%", background: blob(z.status), filter: "blur(6px)", pointerEvents: "none" }} />
            ))}
          </div>
        </div>
        <p className="muted" style={{ fontSize: 11, marginTop: 8, lineHeight: 1.6 }}>
          ※ <b>데모 화면입니다.</b> 배경은 실제 사이트지만, 위에 표시된 열지도는 <b>페이지 점검 결과를 예시로 표현한 것</b>이며
          실제 방문자의 클릭 데이터가 아닙니다. 실제 방문자 히트맵은 추적 스크립트를 설치하면 볼 수 있습니다.
        </p>
        </div>

        {/* 영역별 상태 */}
        <div>
          {hottest && hottest.status !== "pass" && (
            <div className="notice" style={{ marginBottom: 12, background: "#fdecec", borderColor: "#f5c2c2", color: "#c0362c" }}>
              🔥 가장 뜨거운 영역: <b>{hottest.label}</b> — 여기부터 개선하세요.
            </div>
          )}
          <div className="stack" style={{ gap: 8 }}>
            {zones.map((z) => {
              const worst = z.zChecks.find((c) => c.status === z.status);
              return (
                <div key={z.id} className="row" style={{ alignItems: "flex-start", gap: 10 }}>
                  <span className="badge" style={{ background: `${DOT[z.status]}22`, color: DOT[z.status], minWidth: 44, justifyContent: "center" }}>{WORD[z.status]}</span>
                  <div>
                    <b className="small">{z.label}</b>
                    <div className="muted small">{worst?.detail ?? "양호합니다."}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// 실제 홈페이지처럼 보이는 배경 (내비 · 히어로 · CTA · 카드 그리드)
function SitePage() {
  const line = "#e2e6ee";
  const soft = "#eef1f7";
  const bar = (w: string, h = 9, c = line) => <div style={{ width: w, height: h, background: c, borderRadius: 4 }} />;
  return (
    <div style={{ position: "absolute", inset: 0, opacity: 0.9 }} aria-hidden>
      <div style={{ height: 40, borderBottom: `1px solid ${line}`, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 5%" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}><div style={{ width: 16, height: 16, borderRadius: 5, background: "#1d4ed8" }} />{bar("46px", 8)}</div>
        <div style={{ display: "flex", gap: 12 }}>{bar("24px", 7)}{bar("24px", 7)}{bar("24px", 7)}</div>
        <div style={{ width: 46, height: 20, borderRadius: 6, background: "#1d4ed8", opacity: 0.85 }} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: 16, padding: "6% 6% 4%" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {bar("72%", 16)}{bar("90%", 16)}{bar("52%", 16)}
          <div style={{ height: 6 }} />{bar("94%", 7, soft)}{bar("84%", 7, soft)}
          <div style={{ width: 96, height: 28, borderRadius: 8, background: "#22c55e", opacity: 0.55, marginTop: 4 }} />
        </div>
        <div style={{ borderRadius: 12, background: "linear-gradient(135deg,#e4ecfb,#dbe8ff)", minHeight: 110 }} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, padding: "0 6%" }}>
        {[0, 1, 2].map((i) => (
          <div key={i} style={{ border: `1px solid ${line}`, borderRadius: 9, padding: 10, display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ height: 34, background: soft, borderRadius: 6 }} />{bar("80%", 8)}{bar("55%", 7, soft)}
          </div>
        ))}
      </div>
    </div>
  );
}
