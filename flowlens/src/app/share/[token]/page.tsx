import { notFound } from "next/navigation";
import { prisma } from "@/lib/db";
import { getSiteMetrics } from "@/lib/metrics";
import { generateSuggestions } from "@/lib/rules";
import { generateReport } from "@/lib/report";
import { MetricCard, Bar, ConfidenceBadge } from "@/components/ui";
import ReportView from "@/components/ReportView";
import PrintButton from "@/components/PrintButton";

export const dynamic = "force-dynamic";

export default async function SharePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const link = await prisma.shareLink.findUnique({
    where: { token },
    include: { site: { include: { client: { include: { agency: true } } } } },
  });

  if (!link || !link.active) notFound();
  if (link.expiresAt && link.expiresAt < new Date()) notFound();

  const site = link.site;
  const agency = site.client.agency;
  const m = await getSiteMetrics(site.id);
  const suggestions = generateSuggestions(m).filter((s) => s.id !== "low-data");
  const report = generateReport(site.name, site.client.industry, m, suggestions);

  return (
    <>
      {/* 화이트라벨 헤더 (대행사 로고) */}
      <div className="topbar">
        <div className="brand">
          {agency.logoUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={agency.logoUrl} alt={agency.logoText} style={{ maxHeight: 30, maxWidth: 180 }} />
          ) : (
            <>
              <span className="dot" />
              {agency.logoText}
            </>
          )}
        </div>
        <div className="row">
          <span className="pill">행동 분석 리포트</span>
          <PrintButton />
        </div>
      </div>

      <div className="container">
        <p className="muted small">{site.client.name}</p>
        <h1 style={{ fontSize: 24, marginBottom: 4 }}>{site.name} 행동 분석 리포트</h1>
        <p className="muted small" style={{ marginBottom: 24 }}>
          {new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "long", day: "numeric" }).format(new Date())} 기준 · 읽기전용
        </p>

        <div style={{ marginBottom: 24 }}>
          <ReportView report={report} />
        </div>

        <div className="grid grid-4" style={{ marginBottom: 24 }}>
          <MetricCard label="세션" value={m.sessions.toLocaleString()} />
          <MetricCard label="이탈률" value={`${m.bounceRate}%`} />
          <MetricCard label="모바일 비중" value={`${m.device.mobilePct}%`} />
          <MetricCard label="전환" value={m.conversions.toLocaleString()} />
        </div>

        <div className="grid grid-2" style={{ marginBottom: 28 }}>
          <div className="card card-pad">
            <h4 style={{ marginBottom: 14 }}>스크롤 도달률</h4>
            {([["25%", m.scrollReach.p25], ["50%", m.scrollReach.p50], ["75%", m.scrollReach.p75], ["90%", m.scrollReach.p90]] as const).map(([label, v]) => (
              <div key={label} style={{ marginBottom: 12 }}>
                <div className="between small" style={{ marginBottom: 5 }}>
                  <span>{label} 지점 도달</span><span className="muted">{v}%</span>
                </div>
                <Bar value={v} max={100} color="#1d4ed8" />
              </div>
            ))}
          </div>
          <div className="card card-pad">
            <h4 style={{ marginBottom: 14 }}>클릭 품질</h4>
            <Row label="일반 클릭" value={m.clicks.toLocaleString()} />
            <Row label="반응 없는 클릭 (Dead click)" value={`${m.deadClicks.toLocaleString()} (${m.deadClickRate}%)`} />
            <Row label="좌절 클릭 (Rage click)" value={m.rageClicks.toLocaleString()} />
            <Row label="CTA 노출률" value={`${m.ctaViewRate}%`} />
          </div>
        </div>

        <h3 style={{ fontSize: 17, marginBottom: 12 }}>개선 제안</h3>
        <div className="stack" style={{ gap: 14 }}>
          {suggestions.map((s, i) => (
            <div key={s.id} className="card card-pad">
              <div className="between" style={{ marginBottom: 8 }}>
                <div className="row">
                  <span className="badge low">우선순위 {i + 1}</span>
                  <span className="pill">{s.area}</span>
                </div>
                <ConfidenceBadge c={s.confidence} />
              </div>
              <h4 style={{ marginBottom: 6 }}>{s.title}</h4>
              <p className="muted small" style={{ margin: "0 0 10px" }}>{s.detail}</p>
              <div className="small muted" style={{ background: "var(--surface-2)", padding: "8px 12px", borderRadius: 8 }}>📊 {s.evidence}</div>
            </div>
          ))}
        </div>

        <div className="hr" style={{ margin: "32px 0 16px" }} />
        <p className="muted small" style={{ textAlign: "center" }}>
          이 리포트는 {agency.logoText}가 FlowLens로 생성했습니다. · 개인정보 비수집 행동 분석
        </p>
      </div>
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="between" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
      <span className="small muted">{label}</span>
      <b className="small">{value}</b>
    </div>
  );
}
