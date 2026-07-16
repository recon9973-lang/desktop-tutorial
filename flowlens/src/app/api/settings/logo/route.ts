import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { getCurrentUser } from "@/lib/session";
import { can } from "@/lib/plans";

// 화이트라벨 로고/이름 저장. 로고는 클라이언트에서 축소한 data URL(작게).
export async function POST(req: NextRequest) {
  const user = await getCurrentUser();
  const origin = new URL(req.url).origin;
  if (!user) return NextResponse.redirect(new URL("/login", origin), { status: 303 });
  if (user.role !== "OWNER") return NextResponse.redirect(new URL("/settings?error=role", origin), { status: 303 });
  if (!can(user.agency.plan, "whitelabel")) return NextResponse.redirect(new URL("/settings?error=plan", origin), { status: 303 });

  const form = await req.formData();
  const logoText = String(form.get("logoText") || "").trim().slice(0, 40);
  const logoUrl = String(form.get("logoUrl") || "");
  const remove = form.get("remove");

  const data: { logoText?: string; logoUrl?: string } = {};
  if (logoText) data.logoText = logoText;
  if (remove) data.logoUrl = "";
  else if (logoUrl.startsWith("data:image/") && logoUrl.length < 300_000) data.logoUrl = logoUrl;

  await prisma.agency.update({ where: { id: user.agencyId }, data });
  return NextResponse.redirect(new URL("/settings?saved=1", origin), { status: 303 });
}
