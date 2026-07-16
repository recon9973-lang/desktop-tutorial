import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";
import { prisma } from "@/lib/db";
import { getCurrentUser } from "@/lib/session";
import { can } from "@/lib/plans";
import { audit } from "@/lib/audit";

// 화이트라벨 공유 링크 생성 (대행사 범위 검증)
export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await getCurrentUser();
  if (user && !can(user.agency.plan, "share")) return NextResponse.redirect(new URL("/billing?locked=share", new URL(req.url).origin), { status: 303 });
  const origin = new URL(req.url).origin;
  if (!user) return NextResponse.redirect(new URL("/login", origin), { status: 303 });

  // 사이트가 로그인 유저의 대행사 소속인지 확인
  const site = await prisma.site.findFirst({
    where: { id, client: { agencyId: user.agencyId } },
  });
  if (!site) return NextResponse.redirect(new URL("/dashboard", origin), { status: 303 });

  // 추측 불가한 랜덤 토큰 + 기본 만료 30일 (법무 5.5 / 4.8)
  const token = crypto.randomBytes(24).toString("base64url");
  const expiresAt = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);
  await prisma.shareLink.create({ data: { siteId: site.id, token, expiresAt } });
  await audit(user.agencyId, "CREATE_SHARE", { userId: user.id, userEmail: user.email, detail: site.name });
  return NextResponse.redirect(new URL(`/sites/${site.id}/install`, origin), { status: 303 });
}
