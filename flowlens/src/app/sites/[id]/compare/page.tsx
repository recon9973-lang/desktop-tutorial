import { redirect } from "next/navigation";
import { loadSiteForUser } from "@/lib/site";
import { can } from "@/lib/plans";
import Locked from "@/components/Locked";
import { prisma } from "@/lib/db";
import { getComparison, getHeatmapPoints } from "@/lib/metrics";
import type { SiteMetrics } from "@/lib/metrics";
import CompareVisual from "@/components/CompareVisual";

export const dynamic = "force-dynamic";

type Dir = "up" | "down"; // 좋은 방향
type Row = { label: string; get: (m: SiteMetrics) => number; unit: string; good: Dir };

const ROWS: Row[] = [
  { label: "세션", get: (m) => m.sessions, unit: "", good: "up" },
  { label: "이탈률", get: (m) => m.bounceRate, unit: "%", good: "down" },
  { label: "평균 스크롤", get: (m) => m.avgScroll, unit: "%", good: "up" },
  { label: "50% 스크롤 도달률", get: (m) => m.scrollReach.p50, unit: "%", good: "up" },
  { label: "Dead click 비율", get: (m) => m.deadClickRate, unit: "%", good: "down" },
  { label: "Rage click", get: (m) => m.rageClicks, unit: "건", good: "down" },
  { label: "CTA 노출률", get: (m) => m.ctaViewRate, unit: "%", good: "up" },
  { label: "폼 완료율", get: (m) => m.formCompletionRate, unit: "%", good: "up" },
  { label: "전환", get: (m) => m.conversions, unit: "건", good: "up" },
];

export default async function ComparePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { site, user } = await loadSiteForUser(id);
  if (!site) redirect("/dashboard");
  if (!can(user?.agency.plan, "compare")) return <Locked feature="compare" title="전 / 후 비교" desc="개선 조치 전후의 지표 변화를 비교해 성과를 증명합니다." />;

  const { prev, curr, prevLabel, currLabel } = await getComparison(site.id, 14);

  // 화면 위 전후 비교: 홈("/") 화면에 기간별 클릭을 좌우로 비교
  const days = 14;
  const now = new Date();
  const mid = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
  const start = new Date(now.getTime() - days * 2 * 24 * 60 * 60 * 1000);
  const [prevPts, currPts, shot] = await Promise.all([
    getHeatmapPoints(site.id, "/", 4000, { from: start, to: mid }),
    getHeatmapPoints(site.id, "/", 4000, { from: mid, to: now }),
    prisma.screenshot.findUnique({ where: { siteId_path_device: { siteId: site.id, path: "/", device: "DESKTOP" } }, select: { id: true } }),
  ]);
  const toXY = (arr: { x: number; y: number; type: string }[]) => arr.map((p) => ({ x: p.x, y: p.y, type: p.type }));

  let improved = 0;
  let worsened = 0;
  const rows = ROWS.map((r) => {
    const a = r.get(prev);
    const b = r.get(curr);
    const delta = b - a;
    const isImproved = r.good === "up" ? delta > 0 : delta < 0;
    const isWorse = r.good === "up" ? delta < 0 : delta > 0;
    if (delta !== 0 && isImproved) improved++;
    if (delta !== 0 && isWorse) worsened++;
    return { ...r, a, b, delta, isImproved, isWorse };
  });

  return (
    <>
      <div className="notice" style={{ marginBottom: 18 }}>
        <b>{prevLabel}</b>과 <b>{currLabel}</b>의 지표를 비교합니다. 개선 조치를 적용한 뒤 효과를 수치로 증명할 때 사용하세요.
        (초록 = 개선, 빨강 = 악화)
      </div>

      <div className="grid grid-3" style={{ marginBottom: 18 }}>
        <div className="card metric"><div className="label">개선된 지표</div><div className="value" style={{ color: "var(--green)" }}>{improved}</div></div>
        <div className="card metric"><div className="label">악화된 지표</div><div className="value" style={{ color: "var(--red)" }}>{worsened}</div></div>
        <div className="card metric"><div className="label">변화 없음</div><div className="value">{ROWS.length - improved - worsened}</div></div>
      </div>

      <CompareVisual
        siteId={site.id}
        path="/"
        prev={toXY(prevPts)}
        curr={toXY(currPts)}
        prevLabel={prevLabel}
        currLabel={currLabel}
        hasScreenshot={!!shot}
      />

      <div className="card" style={{ overflow: "hidden" }}>
        <table className="table">
          <thead>
            <tr>
              <th>지표</th>
              <th>{prevLabel}</th>
              <th>{currLabel}</th>
              <th>변화</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const color = r.delta === 0 ? "var(--text-3)" : r.isImproved ? "var(--green)" : "var(--red)";
              const arrow = r.delta === 0 ? "–" : r.delta > 0 ? "▲" : "▼";
              return (
                <tr key={r.label}>
                  <td><b>{r.label}</b></td>
                  <td className="muted">{r.a.toLocaleString()}{r.unit}</td>
                  <td><b>{r.b.toLocaleString()}{r.unit}</b></td>
                  <td style={{ color, fontWeight: 700 }}>
                    {arrow} {Math.abs(r.delta).toLocaleString()}{r.unit}
                    {r.delta !== 0 && <span className="small" style={{ marginLeft: 6 }}>{r.isImproved ? "개선" : "악화"}</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="muted small" style={{ marginTop: 12 }}>
        * 비교 기간은 데이터 수집 시점 기준 최근 14일과 그 이전 14일입니다. 실제 운영에서는 개선 배포일을 기준선으로 지정할 수 있습니다.
      </p>
    </>
  );
}
