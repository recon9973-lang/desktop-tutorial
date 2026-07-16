import { redirect } from "next/navigation";
import { loadSiteForUser } from "@/lib/site";
import { can } from "@/lib/plans";
import Locked from "@/components/Locked";
import { prisma } from "@/lib/db";
import { getSiteMetrics } from "@/lib/metrics";
import { generateSuggestions } from "@/lib/rules";
import { generateReport } from "@/lib/report";
import { ConfidenceBadge } from "@/components/ui";
import ReportView from "@/components/ReportView";

export const dynamic = "force-dynamic";

const STATUS = {
  OPEN: { label: "열림", cls: "gray" },
  DOING: { label: "진행 중", cls: "medium" },
  DONE: { label: "완료", cls: "high" },
} as const;
type St = keyof typeof STATUS;

export default async function SuggestionsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { site, user } = await loadSiteForUser(id);
  if (!site) redirect("/dashboard");
  if (!can(user?.agency.plan, "suggestions")) return <Locked feature="suggestions" title="진단 · 개선 제안" desc="수집된 행동 데이터를 분석해 무엇을 고쳐야 하는지 제안합니다." />;

  const m = await getSiteMetrics(site.id);
  const suggestions = generateSuggestions(m).filter((s) => s.id !== "low-data");
  const report = generateReport(site.name, site.client.industry, m, suggestions);

  const statusRows = await prisma.suggestionStatus.findMany({ where: { siteId: site.id } });
  const statusMap = new Map(statusRows.map((r) => [r.ruleId, r.status as St]));
  const withStatus = suggestions.map((s) => ({ ...s, status: statusMap.get(s.id) ?? "OPEN" }));

  const counts = { OPEN: 0, DOING: 0, DONE: 0 };
  withStatus.forEach((s) => (counts[s.status as St] += 1));

  // 완료는 아래로 정렬
  const order = { OPEN: 0, DOING: 1, DONE: 2 };
  withStatus.sort((a, b) => order[a.status as St] - order[b.status as St]);

  return (
    <>
      <div style={{ marginBottom: 18 }}>
        <ReportView report={report} />
      </div>

      {/* 과제 보드 요약 */}
      <div className="between" style={{ marginBottom: 14, flexWrap: "wrap", gap: 10 }}>
        <h3 style={{ fontSize: 16 }}>개선 과제 보드</h3>
        <div className="row" style={{ gap: 8 }}>
          <span className="badge gray">열림 {counts.OPEN}</span>
          <span className="badge medium">진행 중 {counts.DOING}</span>
          <span className="badge high">완료 {counts.DONE}</span>
        </div>
      </div>

      <div className="stack" style={{ gap: 14 }}>
        {withStatus.map((s, i) => {
          const done = s.status === "DONE";
          return (
            <div key={s.id} className="card card-pad" style={done ? { opacity: 0.62 } : undefined}>
              <div className="between" style={{ marginBottom: 10, flexWrap: "wrap", gap: 8 }}>
                <div className="row">
                  <span className="badge low">우선순위 {i + 1}</span>
                  <span className="pill">{s.area}</span>
                  <span className={`badge ${STATUS[s.status as St].cls}`}>{STATUS[s.status as St].label}</span>
                </div>
                <ConfidenceBadge c={s.confidence} />
              </div>
              <h3 style={{ fontSize: 16, marginBottom: 8, textDecoration: done ? "line-through" : "none" }}>{s.title}</h3>
              <p style={{ marginTop: 0, marginBottom: 12 }}>{s.detail}</p>
              <div className="between" style={{ flexWrap: "wrap", gap: 10 }}>
                <div className="row small muted" style={{ background: "var(--surface-2)", padding: "8px 12px", borderRadius: 8 }}>
                  <span>📊 근거:</span> <span>{s.evidence}</span>
                </div>
                {/* 상태 변경 */}
                <div className="row" style={{ gap: 6 }}>
                  {(Object.keys(STATUS) as St[]).map((st) => (
                    <form key={st} action={`/api/sites/${site.id}/suggestion-status`} method="post">
                      <input type="hidden" name="ruleId" value={s.id} />
                      <input type="hidden" name="status" value={st} />
                      <button className={`btn sm ${s.status === st ? "primary" : ""}`} type="submit">{STATUS[st].label}</button>
                    </form>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
