import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { getCurrentUser } from "@/lib/session";

// 설치 확인: 해당 siteKey의 수집 이벤트 수를 반환.
// siteKey는 공개값(추적 스크립트에 노출)이라, 이벤트 수 같은 트래픽 지표는
// 사이트 소유자(로그인 + 본인 대행사)에게만 준다(교차 노출 방지).
export async function GET(_req: NextRequest, { params }: { params: Promise<{ siteKey: string }> }) {
  const { siteKey } = await params;
  const site = await prisma.site.findUnique({
    where: { siteKey },
    include: { client: { select: { agencyId: true } } },
  });
  if (!site) return NextResponse.json({ installed: false, found: false });

  const user = await getCurrentUser();
  if (!user || user.agencyId !== site.client.agencyId) {
    // 소유자가 아니면 수치를 노출하지 않는다.
    return NextResponse.json({ installed: false, found: false });
  }

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
