import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/session";
import { prisma } from "@/lib/db";
import { PLANS, getPlan, ANNUAL_DISCOUNT, annualPrice, annualMonthly, annualSaving } from "@/lib/plans";
import TopBar from "@/components/TopBar";
import { Bar } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function BillingPage({ searchParams }: { searchParams: Promise<{ changed?: string; error?: string; cycle?: string }> }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  const { changed, cycle } = await searchParams;
  const annual = cycle === "annual"; // 연간 결제 보기

  const current = getPlan(user.agency.plan);
  const now = new Date();
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

  const [sessionsThisMonth, sitesCount] = await Promise.all([
    prisma.session.count({ where: { site: { client: { agencyId: user.agencyId } }, startedAt: { gte: startOfMonth } } }),
    prisma.site.count({ where: { client: { agencyId: user.agencyId } } }),
  ]);

  const sessionPct = Math.min(100, Math.round((sessionsThisMonth / current.sessionsPerMonth) * 100));

  return (
    <>
      <TopBar agencyName={user.agency.name} userName={user.name} />
      <div className="container">
        <h1 style={{ fontSize: 22, marginBottom: 4 }}>요금제 · 사용량</h1>
        <p className="muted small" style={{ marginBottom: 20 }}>현재 요금제와 이번 달 사용량을 확인하고 변경할 수 있습니다.</p>

        {changed && <div className="notice" style={{ marginBottom: 18 }}>요금제가 변경되었습니다. (데모: 실제 결제 없이 적용)</div>}

        {/* 현재 요금제 & 사용량 */}
        <div className="grid grid-2" style={{ marginBottom: 14 }}>
          <div className="card card-pad">
            <div className="muted small">현재 요금제</div>
            <div className="row" style={{ margin: "6px 0 14px" }}>
              <span style={{ fontSize: 24, fontWeight: 800 }}>{current.name}</span>
              <span className="badge low">{current.priceLabel}/월</span>
            </div>
            <div className="small muted">사이트 {sitesCount} / {current.sites}개 · 보관 {current.retentionDays}일</div>
          </div>
          <div className="card card-pad">
            <div className="between" style={{ marginBottom: 6 }}>
              <span className="muted small">이번 달 세션</span>
              <span className="small"><b>{sessionsThisMonth.toLocaleString()}</b> / {current.sessionsPerMonth.toLocaleString()}</span>
            </div>
            <Bar value={sessionPct} max={100} color={sessionPct >= 90 ? "var(--red)" : "var(--accent)"} />
            <div className="small muted" style={{ marginTop: 8 }}>
              {sessionPct >= 90 ? "한도에 근접했습니다. 상위 요금제를 검토하세요." : `한도의 ${sessionPct}% 사용 중`}
            </div>
          </div>
        </div>

        <div className="notice small" style={{ marginBottom: 16 }}>
          ⚠️ 데모 환경에서는 <b>실제 결제(PG) 연동 없이</b> 요금제가 즉시 변경됩니다. 운영에서는 국내 PG(토스) 결제 후 반영됩니다.
        </div>

        {/* 월간 / 연간 결제 전환 */}
        <div className="between" style={{ marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
          <div className="row" style={{ gap: 0, border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
            <Link href="/billing" className="btn sm" style={{ borderRadius: 0, border: "none", background: annual ? "transparent" : "var(--accent)", color: annual ? "var(--text-2)" : "#fff" }}>월간 결제</Link>
            <Link href="/billing?cycle=annual" className="btn sm" style={{ borderRadius: 0, border: "none", background: annual ? "var(--accent)" : "transparent", color: annual ? "#fff" : "var(--text-2)" }}>연간 결제</Link>
          </div>
          <span className="badge" style={{ background: "var(--good)", color: "#fff" }}>연간 결제 시 {Math.round(ANNUAL_DISCOUNT * 100)}% 할인 · 약 1개월치 아낌</span>
        </div>

        {/* 요금제 목록 */}
        <div className="grid grid-3">
          {PLANS.map((p) => {
            const isCurrent = p.key === current.key;
            const paid = p.price > 0;
            return (
              <div key={p.key} className="card card-pad" style={{ borderColor: isCurrent ? "var(--accent)" : "var(--border)", borderWidth: isCurrent ? 2 : 1 }}>
                <div className="between" style={{ marginBottom: 8 }}>
                  <b style={{ fontSize: 16 }}>{p.name}</b>
                  {isCurrent && <span className="badge low">현재</span>}
                </div>
                {annual && paid ? (
                  <>
                    <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 2 }}>{annualMonthly(p).toLocaleString()}원<span className="muted" style={{ fontSize: 12, fontWeight: 500 }}> /월 꼴</span></div>
                    <div className="small" style={{ color: "var(--green)", fontWeight: 700, marginBottom: 2 }}>
                      연 {annualPrice(p).toLocaleString()}원 · {annualSaving(p).toLocaleString()}원 절약
                    </div>
                    <div className="muted small" style={{ marginBottom: 12 }}>{p.target}</div>
                  </>
                ) : (
                  <>
                    <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 2 }}>{p.priceLabel}<span className="muted" style={{ fontSize: 12, fontWeight: 500 }}> /월</span></div>
                    <div className="muted small" style={{ marginBottom: 12 }}>{p.target}</div>
                  </>
                )}
                <ul className="small muted" style={{ margin: "0 0 14px", paddingLeft: 16, lineHeight: 1.9 }}>
                  {p.highlights.map((h) => <li key={h}>{h}</li>)}
                </ul>
                {isCurrent ? (
                  <button className="btn sm" disabled style={{ width: "100%", justifyContent: "center", opacity: 0.6 }}>이용 중</button>
                ) : p.price === 0 ? (
                  <form action="/api/billing/change-plan" method="post">
                    <input type="hidden" name="plan" value={p.key} />
                    <button className="btn sm" type="submit" style={{ width: "100%", justifyContent: "center" }} disabled={user.role !== "OWNER"}>
                      무료 요금제로 변경
                    </button>
                  </form>
                ) : (
                  <Link
                    href={user.role === "OWNER" ? `/billing/checkout?plan=${p.key}${annual ? "&cycle=annual" : ""}` : "#"}
                    className="btn primary sm"
                    style={{ width: "100%", justifyContent: "center", ...(user.role !== "OWNER" ? { opacity: 0.5, pointerEvents: "none" } : {}) }}
                  >
                    {p.price > current.price ? "업그레이드 →" : "이 요금제로 변경 →"}
                    {annual ? " (연간)" : ""}
                  </Link>
                )}
              </div>
            );
          })}
        </div>
        {user.role !== "OWNER" && <p className="muted small" style={{ marginTop: 12 }}>요금제 변경은 OWNER 권한만 가능합니다.</p>}
      </div>
    </>
  );
}
