import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { getCurrentUser, hashPassword, checkPassword } from "@/lib/session";
import { audit } from "@/lib/audit";

// 로그인 사용자가 본인 비밀번호를 변경.
export async function POST(req: NextRequest) {
  const user = await getCurrentUser();
  const origin = new URL(req.url).origin;
  if (!user) return NextResponse.redirect(new URL("/login", origin), { status: 303 });

  const form = await req.formData();
  const current = String(form.get("current") || "");
  const next = String(form.get("next") || "");
  const confirm = String(form.get("confirm") || "");

  const fail = (code: string) => NextResponse.redirect(new URL(`/settings?pwerror=${code}`, origin), { status: 303 });

  if (next.length < 8) return fail("short"); // 최소 8자
  if (next !== confirm) return fail("mismatch");
  if (!checkPassword(current, user.passwordHash)) return fail("current");
  if (checkPassword(next, user.passwordHash)) return fail("same");

  await prisma.user.update({ where: { id: user.id }, data: { passwordHash: hashPassword(next) } });
  await audit(user.agencyId, "CHANGE_PASSWORD", { userId: user.id, userEmail: user.email });

  return NextResponse.redirect(new URL("/settings?pwsaved=1", origin), { status: 303 });
}
