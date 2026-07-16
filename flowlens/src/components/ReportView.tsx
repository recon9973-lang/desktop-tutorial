import type { Report } from "@/lib/report";

// AI 자동 리포트(서술형) 렌더링. 서버 컴포넌트에서 그대로 사용 가능.
export default function ReportView({ report, compact = false }: { report: Report; compact?: boolean }) {
  return (
    <div className="card card-pad" style={{ borderColor: "#cfe0fd", background: "linear-gradient(180deg,#f5f9ff, #ffffff)" }}>
      <div className="row" style={{ marginBottom: 10 }}>
        <span className="badge low">✨ 자동 리포트</span>
        <span className="muted small">자체 룰 엔진 기반 · 외부 AI 미전송</span>
      </div>
      <h3 style={{ fontSize: compact ? 16 : 18, marginBottom: 10, lineHeight: 1.4 }}>{report.headline}</h3>
      <p style={{ marginTop: 0, marginBottom: 16 }}>{report.summary}</p>

      {report.actions.length > 0 && (
        <>
          <div className="small" style={{ fontWeight: 700, color: "var(--text-2)", marginBottom: 8 }}>우선 조치</div>
          <div className="stack" style={{ gap: 10, marginBottom: 16 }}>
            {report.actions.map((a) => (
              <div key={a.priority} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: "12px 14px" }}>
                <div className="row" style={{ marginBottom: 4 }}>
                  <span className="badge low">{a.priority}</span>
                  <b>{a.title}</b>
                </div>
                <p className="small" style={{ margin: "4px 0" }}>💡 {a.how}</p>
                <p className="small muted" style={{ margin: 0 }}>📊 {a.why}</p>
              </div>
            ))}
          </div>
        </>
      )}

      <div className="notice small" style={{ marginBottom: 8 }}>{report.outlook}</div>
      <p className="muted" style={{ fontSize: 11.5, margin: 0 }}>{report.generatedNote}</p>
    </div>
  );
}
