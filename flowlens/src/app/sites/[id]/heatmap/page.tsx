import Link from "next/link";
import { redirect } from "next/navigation";
import { loadSiteForUser } from "@/lib/site";
import { prisma } from "@/lib/db";
import { getHeatmapPoints, getGesturePoints, getMovePoints, getSitePaths, getScrollData, getClickLabels } from "@/lib/metrics";
import { getSnapshotPoints } from "@/lib/rollup";
import { can } from "@/lib/plans";
import HeatmapStudio from "@/components/HeatmapStudio";

export const dynamic = "force-dynamic";

export default async function HeatmapPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ path?: string; days?: string }>;
}) {
  const { id } = await params;
  const { path, days: daysParam } = await searchParams;
  const { site, user } = await loadSiteForUser(id);
  if (!site) redirect("/dashboard");

  // 기간 필터: days 없으면 전체. 있으면 최근 N일.
  const days = Number(daysParam) > 0 ? Number(daysParam) : 0;
  const range = days > 0 ? { from: new Date(Date.now() - days * 24 * 60 * 60 * 1000), to: new Date() } : undefined;

  const shotPath = path || "/";
  const [paths, livePoints, clickLabels, gestures, liveMoves, scroll, shots, snap] = await Promise.all([
    getSitePaths(site.id),
    getHeatmapPoints(site.id, path, 4000, range),
    // 셀렉터 랭킹용 — 좌표 없는 클릭(팝업·고정 헤더)도 "무엇을 눌렀나"에는 들어가야 한다
    getClickLabels(site.id, path, 4000, range),
    getGesturePoints(site.id, path),
    getMovePoints(site.id, path, 8000, range),
    getScrollData(site.id),
    prisma.screenshot.findMany({ where: { siteId: site.id, path: shotPath }, select: { device: true, capturedAt: true } }),
    // 보관 스냅샷은 날짜정보가 없으므로 "전체" 기간일 때만 합친다
    days > 0 ? Promise.resolve({ clicks: [], moves: [] }) : getSnapshotPoints(site.id, path),
  ]);
  // 라이브(최근) + 보관 스냅샷(오래된 것 롤업본) 합쳐서 표시
  const points = [...livePoints, ...snap.clicks];
  const moves = [...liveMoves, ...snap.moves];
  const shotDevices = shots.map((s) => s.device);
  const shotInfo: Record<string, string> = {};
  for (const s of shots) shotInfo[s.device] = s.capturedAt.toISOString();

  return (
    <div className="grid" style={{ gridTemplateColumns: "220px 1fr", gap: 20 }}>
      <div>
        <div className="card card-pad" style={{ marginBottom: 14 }}>
          <h4 style={{ marginBottom: 12 }}>기간</h4>
          <div className="stack">
            {[
              { d: 0, l: "전체 기간" },
              { d: 7, l: "최근 7일" },
              { d: 30, l: "최근 30일" },
              { d: 90, l: "최근 90일" },
            ].map((o) => (
              <Link key={o.d} href={hmHref(site.id, path, o.d)} className={`btn sm ${days === o.d ? "primary" : ""}`} style={{ justifyContent: "flex-start", width: "100%" }}>
                {o.l}
              </Link>
            ))}
          </div>
          {days > 0 && <p className="muted" style={{ fontSize: 11, marginTop: 8 }}>보관 스냅샷(오래된 집계본)은 &ldquo;전체 기간&rdquo;에서만 함께 표시됩니다.</p>}
        </div>

        <div className="card card-pad">
          <h4 style={{ marginBottom: 12 }}>페이지 선택</h4>
          <div className="stack">
            <PathLink siteId={site.id} label="전체 페이지" value={undefined} active={!path} count={points.length} days={days} />
            {paths.map((p) => (
              <PathLink key={p.path} siteId={site.id} label={p.path} value={p.path} active={path === p.path} count={p.count} days={days} />
            ))}
          </div>
        </div>
        <div className="notice small" style={{ marginTop: 14 }}>
          좌표는 문서 대비 상대값(0~1)으로만 저장됩니다. 절대 픽셀·IP·입력값은 수집하지 않습니다.
        </div>
        <div className="card card-pad small" style={{ marginTop: 14 }}>
          <b>5가지 뷰</b>
          <ul className="muted" style={{ margin: "6px 0 0", paddingLeft: 16, lineHeight: 1.8 }}>
            <li><b>클릭맵</b> — 클릭 열지도</li>
            <li><b>무브맵</b> — 마우스 커서 이동(주목도)</li>
            <li><b>셀렉터</b> — 많이 클릭된 요소 랭킹</li>
            <li><b>스크롤맵</b> — 구간별 도달률</li>
            <li><b>제스처</b> — 모바일 탭·더블탭·줌·스와이프</li>
          </ul>
        </div>
      </div>

      <div>
        {path && <p className="muted small" style={{ marginBottom: 10 }}>페이지: <b>{path}</b></p>}
        {points.length === 0 && moves.length === 0 && scroll.sessions.length === 0 && (
          <div className="card card-pad" style={{ marginBottom: 14, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap", background: "#eef5ff", borderColor: "#c9dcff" }}>
            <div>
              <b>아직 표시할 데이터가 없어요</b>
              <div className="muted small" style={{ marginTop: 3 }}>추적 코드를 설치하고 방문이 생기면 클릭·이동·스크롤이 이 화면에 쌓입니다.</div>
            </div>
            <Link className="btn primary sm" href={`/sites/${site.id}/install`}>설치하기</Link>
          </div>
        )}
        <HeatmapStudio points={points} clickLabels={clickLabels} gesturePoints={gestures} movePoints={moves} scrollSessions={scroll.sessions} avgFold={scroll.avgFold} siteId={site.id} path={shotPath} shotDevices={shotDevices} shotInfo={shotInfo} mapsAll={can(user?.agency.plan, "maps_all")} />
      </div>
    </div>
  );
}

// 페이지·기간 선택을 함께 유지하는 링크 생성
function hmHref(siteId: string, path?: string, days?: number) {
  const q = new URLSearchParams();
  if (path) q.set("path", path);
  if (days) q.set("days", String(days));
  const s = q.toString();
  return `/sites/${siteId}/heatmap${s ? `?${s}` : ""}`;
}

function PathLink({ siteId, label, value, active, count, days }: { siteId: string; label: string; value?: string; active: boolean; count: number; days: number }) {
  const href = hmHref(siteId, value, days);
  return (
    <Link href={href} className={`btn sm ${active ? "primary" : ""}`} style={{ justifyContent: "space-between", width: "100%" }}>
      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{label}</span>
      <span className="small" style={{ opacity: 0.7 }}>{count}</span>
    </Link>
  );
}
