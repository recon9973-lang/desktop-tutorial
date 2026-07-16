"use client";

import { useState } from "react";
import Link from "next/link";
import DiagnoseHeatmap from "./DiagnoseHeatmap";

type Check = { key: string; label: string; status: "pass" | "warn" | "fail"; detail: string };
type Platform = { key: string; name: string; how: string };
type Result =
  | { ok: true; url: string; title: string; score: number; checks: Check[]; summary: string; platform?: Platform }
  | { ok: false; error: string };

const STATUS_ICON = { pass: "✓", warn: "!", fail: "✕" } as const;
const STATUS_CLS = { pass: "high", warn: "medium", fail: "low" } as const;

// 추적 설치가 있어야만 알 수 있는 항목 — 잠금 티저로 노출해 가입 유도
const LOCKED = [
  { icon: "🖱", label: "클릭 히트맵", desc: "방문자가 실제로 어디를 누르는지" },
  { icon: "😤", label: "좌절 클릭 (Rage click)", desc: "버튼이 안 눌려 반복 클릭하는 지점" },
  { icon: "📉", label: "스크롤 이탈 지점", desc: "어디까지 읽고 떠나는지" },
  { icon: "🛒", label: "전환 퍼널", desc: "방문 → 관심 → 전환 단계별 이탈률" },
];

export default function DiagnoseWidget() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Result | null>(null);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim() || loading) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch("/api/diagnose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      setResult(await res.json());
    } catch {
      setResult({ ok: false, error: "진단 중 오류가 발생했습니다. 잠시 후 다시 시도하세요." });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <form onSubmit={run} className="diag-form">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="내 사이트 주소 입력 (예: mysite.co.kr)"
          className="diag-input"
          aria-label="진단할 사이트 주소"
        />
        <button className="btn primary" type="submit" disabled={loading} style={{ whiteSpace: "nowrap" }}>
          {loading ? "진단 중…" : "무료 진단"}
        </button>
      </form>
      <p className="small" style={{ opacity: 0.7, marginTop: 8 }}>가입 없이 즉시 확인 · 카드 필요 없음</p>

      {result && !result.ok && (
        <div className="notice" style={{ marginTop: 18, background: "#fdecec", borderColor: "#f5c2c2", color: "#c0362c" }}>
          {result.error}
        </div>
      )}

      {result && result.ok && (
        <div className="card card-pad diag-result" style={{ marginTop: 18, textAlign: "left" }}>
          <div className="between" style={{ marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
            <div>
              <div className="muted small">진단 대상</div>
              <div style={{ fontWeight: 700, wordBreak: "break-all" }}>{result.url}</div>
            </div>
            <ScoreRing score={result.score} />
          </div>

          <div className="notice" style={{ marginBottom: 18 }}>{result.summary}</div>

          {/* 플랫폼 자동 감지 → 그 플랫폼 전용 설치법만 안내 (설치 장벽 제거) */}
          {result.platform && (
            <div className="notice small" style={{ marginBottom: 18, background: "#eef5ff", borderColor: "#c9dcff" }}>
              <b>이 사이트는 &ldquo;{result.platform.name}&rdquo;로 만들어졌네요.</b>
              <br />
              설치는 이렇게 하시면 됩니다 — {result.platform.how}
            </div>
          )}

          {/* 히트맵 인포그래픽: 페이지 영역별 문제/양호를 열지도로 시각화 */}
          <div style={{ marginBottom: 10 }}>
            <div className="row" style={{ marginBottom: 12 }}>
              <span className="badge low">🔥 진단 히트맵</span>
              <span className="muted small">점검 결과를 페이지 영역 위에 열지도로 표시</span>
            </div>
            <DiagnoseHeatmap checks={result.checks} url={result.url} />
          </div>

          {/* 세부 점검 (접이식) */}
          <details style={{ margin: "16px 0 22px" }}>
            <summary className="small" style={{ cursor: "pointer", color: "var(--accent)", fontWeight: 600 }}>세부 점검 항목 {result.checks.length}개 보기</summary>
            <div className="stack" style={{ gap: 8, marginTop: 12 }}>
              {result.checks.map((c) => (
                <div key={c.key} className="row" style={{ alignItems: "flex-start", gap: 10 }}>
                  <span className={`badge ${STATUS_CLS[c.status]}`} style={{ minWidth: 20, justifyContent: "center" }}>{STATUS_ICON[c.status]}</span>
                  <div>
                    <b className="small">{c.label}</b>
                    <div className="muted small">{c.detail}</div>
                  </div>
                </div>
              ))}
            </div>
          </details>

          {/* 설치하면 보이는 것 (잠금) */}
          <div style={{ position: "relative", borderTop: "1px dashed var(--border)", paddingTop: 18 }}>
            <div className="row" style={{ marginBottom: 12 }}>
              <span className="badge low">🔒 설치하면 보이는 것</span>
              <span className="muted small">아래는 추적을 설치해야 볼 수 있는 실제 행동 데이터입니다</span>
            </div>
            <div className="grid grid-2" style={{ gap: 10 }}>
              {LOCKED.map((l) => (
                <div key={l.label} className="locked-tile">
                  <div style={{ fontSize: 20 }}>{l.icon}</div>
                  <b className="small">{l.label}</b>
                  <div className="muted small">{l.desc}</div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 18, textAlign: "center" }}>
              <Link href="/signup" className="btn primary" style={{ padding: "12px 24px" }}>
                무료로 가입하고 실제 행동 분석 시작하기 →
              </Link>
              <p className="muted small" style={{ marginTop: 8 }}>스크립트 한 줄 설치 · 며칠 뒤 자동 리포트</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ScoreRing({ score }: { score: number }) {
  const color = score >= 80 ? "#12a150" : score >= 50 ? "#d98a00" : "#e5484d";
  const deg = (score / 100) * 360;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div
        style={{
          width: 66, height: 66, borderRadius: "50%",
          background: `conic-gradient(${color} ${deg}deg, var(--surface-2) 0deg)`,
          display: "grid", placeItems: "center",
        }}
      >
        <div style={{ width: 50, height: 50, borderRadius: "50%", background: "var(--surface)", display: "grid", placeItems: "center", fontWeight: 800 }}>
          {score}
        </div>
      </div>
      <div className="small muted">기본 점수<br />(100점 만점)</div>
    </div>
  );
}
