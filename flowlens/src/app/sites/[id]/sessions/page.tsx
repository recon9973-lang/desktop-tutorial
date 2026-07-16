import Link from "next/link";
import { redirect } from "next/navigation";
import { loadSiteForUser } from "@/lib/site";
import { can } from "@/lib/plans";
import Locked from "@/components/Locked";
import { prisma } from "@/lib/db";

export const dynamic = "force-dynamic";

const DEVICE_LABEL: Record<string, string> = { MOBILE: "모바일", DESKTOP: "데스크톱", TABLET: "태블릿" };
const CHANNEL_LABEL: Record<string, string> = { direct: "직접", search: "검색", ad: "광고", social: "소셜", referral: "추천" };

function fmtDuration(ms: number) {
  const s = Math.max(0, Math.round(ms / 1000));
  if (s < 60) return `${s}초`;
  return `${Math.floor(s / 60)}분 ${s % 60}초`;
}
function fmtTime(d: Date) {
  return new Intl.DateTimeFormat("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(d);
}

export default async function SessionsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { site, user } = await loadSiteForUser(id);
  if (!site) redirect("/dashboard");
  if (!can(user?.agency.plan, "replay")) return <Locked feature="replay" title="세션 리플레이" desc="개별 방문자의 행동 흐름을 순서대로 재생합니다." />;

  const sessions = await prisma.session.findMany({
    where: { siteId: site.id },
    orderBy: { lastEventAt: "desc" },
    take: 40,
    include: { _count: { select: { events: true } } },
  });

  return (
    <div className="card" style={{ overflow: "hidden" }}>
      <div className="card-pad between">
        <h4>최근 세션</h4>
        <span className="muted small">최근 40개 · 개인 식별 정보 없음</span>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>시작 시각</th>
            <th>디바이스</th>
            <th>유입</th>
            <th>페이지</th>
            <th>최대 스크롤</th>
            <th>체류</th>
            <th>이벤트</th>
            <th>상태</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr key={s.id}>
              <td>{fmtTime(s.startedAt)}</td>
              <td>{DEVICE_LABEL[s.device] ?? s.device}</td>
              <td><span className="pill">{CHANNEL_LABEL[s.channel] ?? s.channel}</span></td>
              <td>{s.pageCount}</td>
              <td>{s.maxScrollPct}%</td>
              <td>{fmtDuration(s.lastEventAt.getTime() - s.startedAt.getTime())}</td>
              <td>{s._count.events}</td>
              <td>{s.isBounce ? <span className="badge gray">이탈</span> : <span className="badge high">참여</span>}</td>
              <td><Link className="btn sm" href={`/sites/${site.id}/sessions/${s.id}`}>▶ 재생</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
