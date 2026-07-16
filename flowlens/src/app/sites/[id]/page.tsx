import Link from "next/link";
import { redirect } from "next/navigation";
import { loadSiteForUser } from "@/lib/site";
import { getSiteMetrics } from "@/lib/metrics";
import { generateSuggestions } from "@/lib/rules";
import { MetricCard, Bar, ConfidenceBadge } from "@/components/ui";

export const dynamic = "force-dynamic";

const CHANNEL_LABEL: Record<string, string> = {
  direct: "직접 유입", search: "검색", ad: "광고", social: "소셜", referral: "추천",
};

const PERIODS = [
  { key: "0", label: "전체" },
  { key: "7", label: "최근 7일" },
  { key: "30", label: "최근 30일" },
];

export default async function SiteOverview({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ period?: string }> }) {
  const { id } = await params;
  const { site } = await loadSiteForUser(id);
  if (!site) redirect("/dashboard");

  const periodKey = (await searchParams).period || "0";
  const days = Number(periodKey);
  const range = days > 0 ? { from: new Date(Date.now() - days * 86400000), to: new Date() } : undefined;

  const m = await getSiteMetrics(site.id, range);
  const suggestions = generateSuggestions(m).filter((s) => s.id !== "low-data").slice(0, 3);
  const channelTotal = Object.values(m.channel).reduce((a, b) => a + b, 0) || 1;
  const channelEntries = Object.entries(m.channel).sort((a, b) => b[1] - a[1]);

  return (
    <>
      <div className="row" style={{ marginBottom: 14, flexWrap: "wrap" }}>
        {PERIODS.map((p) => (
          <Link key={p.key} href={`/sites/${site.id}?period=${p.key}`} className={`btn sm ${periodKey === p.key ? "primary" : ""}`}>
            {p.label}
          </Link>
        ))}
        <span className="muted small" style={{ marginLeft: "auto" }}>기간 기준 집계</span>
      </div>

      <div className="grid grid-4" style={{ marginBottom: 16 }}>
        <MetricCard label="세션" value={m.sessions.toLocaleString()} />
        <MetricCard label="이탈률" value={`${m.bounceRate}%`} sub="단일 페이지 후 이탈" />
        <MetricCard label="평균 스크롤" value={`${m.avgScroll}%`} sub="페이지 도달 깊이" />
        <MetricCard label="전환" value={m.conversions.toLocaleString()} />
      </div>

      <div className="grid grid-4" style={{ marginBottom: 24 }}>
        <MetricCard label="일반 클릭" value={m.clicks.toLocaleString()} />
        <MetricCard label="Dead click" value={m.deadClicks.toLocaleString()} sub={`전체 클릭의 ${m.deadClickRate}%`} />
        <MetricCard label="Rage click" value={m.rageClicks.toLocaleString()} sub="좌절 클릭" />
        <MetricCard label="CTA 노출률" value={`${m.ctaViewRate}%`} sub="핵심 버튼 노출" />
      </div>

      <div className="grid grid-3">
        {/* 디바이스 */}
        <div className="card card-pad">
          <h4 style={{ marginBottom: 14 }}>디바이스</h4>
          <DeviceRow label="모바일" value={m.device.MOBILE} total={m.sessions} color="#1d4ed8" />
          <DeviceRow label="데스크톱" value={m.device.DESKTOP} total={m.sessions} color="#22c55e" />
          <DeviceRow label="태블릿" value={m.device.TABLET} total={m.sessions} color="#eab308" />
        </div>

        {/* 유입 채널 */}
        <div className="card card-pad">
          <h4 style={{ marginBottom: 14 }}>유입 채널</h4>
          {channelEntries.map(([k, v]) => (
            <div key={k} style={{ marginBottom: 12 }}>
              <div className="between small" style={{ marginBottom: 5 }}>
                <span>{CHANNEL_LABEL[k] ?? k}</span>
                <span className="muted">{Math.round((v / channelTotal) * 100)}%</span>
              </div>
              <Bar value={v} max={channelTotal} />
            </div>
          ))}
        </div>

        {/* 스크롤 도달률 */}
        <div className="card card-pad">
          <h4 style={{ marginBottom: 14 }}>스크롤 도달률</h4>
          {([["25%", m.scrollReach.p25], ["50%", m.scrollReach.p50], ["75%", m.scrollReach.p75], ["90%", m.scrollReach.p90]] as const).map(([label, v]) => (
            <div key={label} style={{ marginBottom: 12 }}>
              <div className="between small" style={{ marginBottom: 5 }}>
                <span>{label} 지점 도달</span>
                <span className="muted">{v}%</span>
              </div>
              <Bar value={v} max={100} color="#1d4ed8" />
            </div>
          ))}
        </div>
      </div>

      {/* 개선 제안 미리보기 */}
      <div className="between" style={{ margin: "26px 0 12px" }}>
        <h3 style={{ fontSize: 16 }}>핵심 개선 제안</h3>
        <Link className="btn sm" href={`/sites/${site.id}/suggestions`}>전체 보기 →</Link>
      </div>
      <div className="stack">
        {suggestions.length === 0 && <div className="card card-pad muted">현재 도출된 개선 과제가 없습니다.</div>}
        {suggestions.map((s) => (
          <div key={s.id} className="card card-pad">
            <div className="between" style={{ marginBottom: 6 }}>
              <div className="row">
                <span className="pill">{s.area}</span>
                <b>{s.title}</b>
              </div>
              <ConfidenceBadge c={s.confidence} />
            </div>
            <p className="muted small" style={{ margin: 0 }}>{s.detail}</p>
          </div>
        ))}
      </div>
    </>
  );
}

function DeviceRow({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div style={{ marginBottom: 12 }}>
      <div className="between small" style={{ marginBottom: 5 }}>
        <span>{label}</span>
        <span className="muted">{pct}% · {value.toLocaleString()}</span>
      </div>
      <Bar value={pct} max={100} color={color} />
    </div>
  );
}
