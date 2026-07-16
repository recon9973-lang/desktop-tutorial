import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { rollupExpiredEvents } from "@/lib/rollup";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 120;

// Vercel Cron 전용: 전 사이트의 보관기간 초과 데이터를 롤업(스냅샷) 후 삭제.
// 보호: CRON_SECRET 환경변수가 있으면 Authorization: Bearer <CRON_SECRET> 필수.
// (Vercel Cron은 CRON_SECRET 설정 시 이 헤더를 자동으로 붙여 호출한다.)
export async function GET(req: NextRequest) {
  const secret = process.env.CRON_SECRET;
  if (!secret) {
    return NextResponse.json({ ok: false, error: "CRON_SECRET 미설정 — 환경변수에 설정 후 사용하세요." }, { status: 500 });
  }
  const auth = req.headers.get("authorization") || "";
  if (auth !== `Bearer ${secret}`) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }

  const sites = await prisma.site.findMany({ select: { id: true, name: true, retentionDays: true } });
  let rolledSites = 0;
  let totalDeleted = 0;

  for (const site of sites) {
    const cutoff = new Date(Date.now() - site.retentionDays * 24 * 60 * 60 * 1000);
    const r = await rollupExpiredEvents(site.id, cutoff);
    if (r.clickGroups || r.moveGroups) rolledSites++;
    totalDeleted += r.deleted;
    // 롤업 대상 외 오래된 이벤트(page_view/scroll 등)도 삭제
    const res = await prisma.event.deleteMany({ where: { siteId: site.id, ts: { lt: cutoff } } });
    totalDeleted += res.count;
    await prisma.session.deleteMany({ where: { siteId: site.id, lastEventAt: { lt: cutoff }, events: { none: {} } } });
  }

  return NextResponse.json({ ok: true, sites: sites.length, rolledSites, deletedEvents: totalDeleted });
}
