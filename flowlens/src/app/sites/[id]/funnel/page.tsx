import { redirect } from "next/navigation";
import { loadSiteForUser } from "@/lib/site";
import { can } from "@/lib/plans";
import Locked from "@/components/Locked";
import { getFunnel } from "@/lib/metrics";

export const dynamic = "force-dynamic";

export default async function FunnelPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { site, user } = await loadSiteForUser(id);
  if (!site) redirect("/dashboard");
  if (!can(user?.agency.plan, "funnel")) return <Locked feature="funnel" title="퍼널 분석" desc="방문자가 어느 단계에서 이탈하는지 단계별로 확인합니다." />;

  const funnel = await getFunnel(site.id);
  const biggestDrop = [...funnel].sort((a, b) => b.dropFromPrev - a.dropFromPrev)[0];

  return (
    <>
      <div className="notice" style={{ marginBottom: 18 }}>
        방문부터 전환까지 각 단계에 <b>도달한 세션 비율</b>과 단계별 이탈률을 보여줍니다. 이탈이 가장 큰 구간이 우선 개선 지점입니다.
      </div>

      <div className="card card-pad" style={{ marginBottom: 18 }}>
        <h4 style={{ marginBottom: 18 }}>전환 퍼널</h4>
        <div className="stack" style={{ gap: 14 }}>
          {funnel.map((step, i) => (
            <div key={step.key}>
              <div className="between" style={{ marginBottom: 6 }}>
                <div className="row">
                  <span className="badge gray">{i + 1}</span>
                  <b>{step.label}</b>
                </div>
                <div className="row">
                  <span className="muted small">{step.sessions.toLocaleString()}세션</span>
                  <span className="pill">전체의 {step.pctOfTop}%</span>
                </div>
              </div>
              <div
                style={{
                  height: 40,
                  width: `${Math.max(4, step.pctOfTop)}%`,
                  background: i === funnel.length - 1 ? "var(--green)" : "linear-gradient(90deg,#1d4ed8,#2563eb)",
                  borderRadius: 8,
                  transition: "width .3s",
                }}
              />
              {i > 0 && step.dropFromPrev > 0 && (
                <div className="small" style={{ color: step.dropFromPrev >= 50 ? "var(--red)" : "var(--text-2)", marginTop: 4 }}>
                  ↓ 이전 단계 대비 {step.dropFromPrev}% 이탈
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {biggestDrop && biggestDrop.dropFromPrev > 0 && (
        <div className="card card-pad">
          <div className="row" style={{ marginBottom: 6 }}>
            <span className="badge medium">가장 큰 이탈 구간</span>
            <b>{biggestDrop.label}</b>
          </div>
          <p className="muted small" style={{ margin: 0 }}>
            이 단계에서 {biggestDrop.dropFromPrev}%가 이탈합니다. 이 구간의 히트맵과 세션 리플레이를 함께 보면 원인을 빠르게 찾을 수 있습니다.
          </p>
        </div>
      )}
    </>
  );
}
