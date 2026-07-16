import Link from "next/link";
import { redirect } from "next/navigation";
import { loadSiteForUser } from "@/lib/site";
import { prisma } from "@/lib/db";
import SessionReplay, { type ReplayEvent } from "@/components/SessionReplay";

export const dynamic = "force-dynamic";

const DEVICE_LABEL: Record<string, string> = { MOBILE: "모바일", DESKTOP: "데스크톱", TABLET: "태블릿" };
const CHANNEL_LABEL: Record<string, string> = { direct: "직접", search: "검색", ad: "광고", social: "소셜", referral: "추천" };

export default async function SessionDetail({ params }: { params: Promise<{ id: string; sessionId: string }> }) {
  const { id, sessionId } = await params;
  const { site } = await loadSiteForUser(id);
  if (!site) redirect("/dashboard");

  const session = await prisma.session.findFirst({
    where: { id: sessionId, siteId: site.id },
    include: { events: { orderBy: { ts: "asc" } } },
  });
  if (!session) redirect(`/sites/${site.id}/sessions`);

  const events: ReplayEvent[] = session.events.map((e) => ({
    type: e.type,
    xRel: e.xRel,
    yRel: e.yRel,
    scrollPct: e.scrollPct,
    path: e.path,
    targetLabel: e.targetLabel,
    ts: e.ts.getTime(),
  }));

  const duration = Math.round((session.lastEventAt.getTime() - session.startedAt.getTime()) / 1000);

  return (
    <>
      <div className="between" style={{ marginBottom: 14 }}>
        <Link href={`/sites/${site.id}/sessions`} className="muted small">← 세션 목록</Link>
        <div className="row">
          <span className="pill">{DEVICE_LABEL[session.device]}</span>
          <span className="pill">{CHANNEL_LABEL[session.channel] ?? session.channel}</span>
          <span className="pill">{session.pageCount}페이지</span>
          <span className="pill">{duration}초</span>
          {session.isBounce ? <span className="badge gray">이탈</span> : <span className="badge high">참여</span>}
        </div>
      </div>

      <SessionReplay events={events} device={session.device} siteId={site.id} path={session.events.find((e) => e.path)?.path || "/"} />
    </>
  );
}
