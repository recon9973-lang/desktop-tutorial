import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/session";
import { prisma } from "@/lib/db";
import { getSiteMetrics } from "@/lib/metrics";
import { generateSuggestions } from "@/lib/rules";
import TopBar from "@/components/TopBar";
import { IndustryBadge, MetricCard } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function Dashboard({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  const q = ((await searchParams).q || "").trim();
  const ql = q.toLowerCase();

  const clients = await prisma.client.findMany({
    where: { agencyId: user.agencyId },
    include: { sites: true },
    orderBy: { createdAt: "asc" },
  });

  // 검색 필터: 고객사명이 맞으면 그 고객사 전체, 아니면 사이트명/도메인 매칭만
  const filteredClients = clients
    .map((c) => {
      const clientHit = !ql || c.name.toLowerCase().includes(ql);
      const sites = clientHit ? c.sites : c.sites.filter((s) => s.name.toLowerCase().includes(ql) || s.domain.toLowerCase().includes(ql));
      return { ...c, sites };
    })
    .filter((c) => c.sites.length > 0);

  const allSites = clients.flatMap((c) => c.sites);
  const siteMetrics = await Promise.all(
    allSites.map(async (s) => {
      const m = await getSiteMetrics(s.id);
      const suggestions = generateSuggestions(m).filter((x) => x.id !== "low-data");
      return { site: s, m, suggestions };
    })
  );
  const byId = new Map(siteMetrics.map((x) => [x.site.id, x]));

  const totalSessions = siteMetrics.reduce((a, x) => a + x.m.sessions, 0);
  const totalSuggestions = siteMetrics.reduce((a, x) => a + x.suggestions.length, 0);
  const totalConversions = siteMetrics.reduce((a, x) => a + x.m.conversions, 0);

  return (
    <>
      <TopBar agencyName={user.agency.name} userName={user.name} />
      <div className="container">
        <div className="between" style={{ marginBottom: 20 }}>
          <div>
            <h1 style={{ fontSize: 22 }}>대행사 대시보드</h1>
            <p className="muted small" style={{ marginTop: 4 }}>{clients.length}개 고객사 · {allSites.length}개 사이트 관리 중</p>
          </div>
          <div className="row" style={{ gap: 8 }}>
            <Link className="btn" href="/demo" target="_blank">추적 데모 페이지 열기 ↗</Link>
            <Link className="btn primary" href="/sites/new">+ 사이트 등록</Link>
          </div>
        </div>

        {clients.length === 0 ? (
          <div className="card card-pad" style={{ textAlign: "center", padding: "48px 24px" }}>
            <div style={{ fontSize: 34, marginBottom: 8 }}>🗂️</div>
            <h3 style={{ fontSize: 17, marginBottom: 6 }}>아직 등록된 고객사가 없습니다</h3>
            <p className="muted small" style={{ marginBottom: 18 }}>첫 고객사와 사이트를 등록하고 추적 스크립트를 설치하면 분석이 시작됩니다.</p>
            <Link className="btn primary" href="/sites/new">+ 첫 고객사 등록</Link>
          </div>
        ) : (
        <>
        <div className="grid grid-4" style={{ marginBottom: 20 }}>
          <MetricCard label="총 세션 (전체 사이트)" value={totalSessions.toLocaleString()} />
          <MetricCard label="관리 사이트" value={allSites.length} sub={`고객사 ${clients.length}곳`} />
          <MetricCard label="도출된 개선 과제" value={totalSuggestions} sub="룰 엔진 자동 생성" />
          <MetricCard label="전환 이벤트" value={totalConversions.toLocaleString()} />
        </div>

        {/* 검색 */}
        <form method="get" className="between" style={{ marginBottom: 20, gap: 8 }}>
          <input name="q" defaultValue={q} placeholder="고객사·사이트·도메인 검색" className="field-inline" style={{ flex: 1, maxWidth: 360 }} />
          <button className="btn sm" type="submit">검색</button>
          {q && <Link className="btn sm" href="/dashboard">초기화</Link>}
        </form>
        {q && <p className="muted small" style={{ marginBottom: 16 }}>“{q}” 검색 결과 · 고객사 {filteredClients.length}곳</p>}

        {filteredClients.length === 0 && (
          <div className="card card-pad muted" style={{ textAlign: "center", padding: "36px" }}>“{q}”에 해당하는 고객사·사이트가 없습니다.</div>
        )}

        {filteredClients.map((client) => (
          <div key={client.id} style={{ marginBottom: 26 }}>
            <div className="row" style={{ marginBottom: 12 }}>
              <h3 style={{ fontSize: 16 }}>{client.name}</h3>
              <IndustryBadge industry={client.industry} />
              <span className="muted small">사이트 {client.sites.length}개</span>
            </div>
            <div className="grid grid-2">
              {client.sites.map((s) => {
                const data = byId.get(s.id)!;
                const attention = data.m.rageClicks + data.m.deadClicks;
                return (
                  <Link key={s.id} href={`/sites/${s.id}`} className="card card-pad" style={{ display: "block" }}>
                    <div className="between" style={{ marginBottom: 14 }}>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 15 }}>{s.name}</div>
                        <div className="muted small">{s.domain}</div>
                      </div>
                      {data.suggestions.length > 0 && (
                        <span className="badge medium">개선 {data.suggestions.length}건</span>
                      )}
                    </div>
                    <div className="grid grid-4" style={{ gap: 10 }}>
                      <MiniStat label="세션" value={data.m.sessions.toLocaleString()} />
                      <MiniStat label="이탈률" value={`${data.m.bounceRate}%`} />
                      <MiniStat label="모바일" value={`${data.m.device.mobilePct}%`} />
                      <MiniStat label="주의 클릭" value={attention.toLocaleString()} />
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
        </>
        )}
      </div>
    </>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="muted" style={{ fontSize: 11, marginBottom: 2 }}>{label}</div>
      <div style={{ fontWeight: 700, fontSize: 16 }}>{value}</div>
    </div>
  );
}
