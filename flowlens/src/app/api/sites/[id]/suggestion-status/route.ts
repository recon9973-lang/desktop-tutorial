import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { getCurrentUser } from "@/lib/session";

// 개선 과제 상태 변경 (OPEN/DOING/DONE). 사이트 소속 검증 후 upsert.
export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await getCurrentUser();
  const origin = new URL(req.url).origin;
  if (!user) return NextResponse.redirect(new URL("/login", origin), { status: 303 });

  const site = await prisma.site.findFirst({ where: { id, client: { agencyId: user.agencyId } } });
  if (!site) return NextResponse.redirect(new URL("/dashboard", origin), { status: 303 });

  const form = await req.formData();
  const ruleId = String(form.get("ruleId") || "").slice(0, 40);
  const status = String(form.get("status") || "OPEN");
  if (!ruleId || !["OPEN", "DOING", "DONE"].includes(status)) {
    return NextResponse.redirect(new URL(`/sites/${site.id}/suggestions`, origin), { status: 303 });
  }

  await prisma.suggestionStatus.upsert({
    where: { siteId_ruleId: { siteId: site.id, ruleId } },
    update: { status },
    create: { siteId: site.id, ruleId, status },
  });

  return NextResponse.redirect(new URL(`/sites/${site.id}/suggestions`, origin), { status: 303 });
}
