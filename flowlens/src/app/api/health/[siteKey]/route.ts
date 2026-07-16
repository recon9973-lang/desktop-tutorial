import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";

// 설치 확인: 해당 siteKey로 수집된 이벤트가 있는지 반환.
export async function GET(_req: NextRequest, { params }: { params: Promise<{ siteKey: string }> }) {
  const { siteKey } = await params;
  const site = await prisma.site.findUnique({ where: { siteKey } });
  if (!site) return NextResponse.json({ installed: false, found: false });

  const [count, last] = await Promise.all([
    prisma.event.count({ where: { siteId: site.id } }),
    prisma.event.findFirst({ where: { siteId: site.id }, orderBy: { ts: "desc" }, select: { ts: true } }),
  ]);

  return NextResponse.json({
    installed: count > 0,
    found: true,
    eventCount: count,
    lastEventAt: last?.ts ?? null,
  });
}
