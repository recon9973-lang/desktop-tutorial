import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { hashPassword, createSession } from "@/lib/session";
import { audit } from "@/lib/audit";
import { getPlan } from "@/lib/plans";

// 실제 자체 회원가입: 대행사(워크스페이스) + OWNER 계정을 생성하고 로그인시킨다.
export async function POST(req: NextRequest) {
  const form = await req.formData();
  const agencyName = String(form.get("agencyName") || "").trim();
  const name = String(form.get("name") || "").trim();
  const email = String(form.get("email") || "").trim().toLowerCase();
  const password = String(form.get("password") || "");
  const origin = new URL(req.url).origin;

  const fail = (code: string) => NextResponse.redirect(new URL(`/signup?error=${code}`, origin), { status: 303 });

  if (!agencyName || !name || !email || password.length < 8) return fail("invalid");

  const existing = await prisma.user.findUnique({ where: { email } });
  if (existing) return fail("email");

  // 무료는 14일 체험 — 만료 시각을 기록해 이후 수집을 중단한다.
  const trial = getPlan("FREE").trialDays;
  const agency = await prisma.agency.create({
    data: {
      name: agencyName,
      logoText: agencyName,
      plan: "FREE",
      trialEndsAt: trial > 0 ? new Date(Date.now() + trial * 24 * 60 * 60 * 1000) : null,
      users: {
        create: { email, name, role: "OWNER", passwordHash: hashPassword(password) },
      },
    },
    include: { users: true },
  });

  await createSession(agency.users[0].id);
  await audit(agency.id, "SIGNUP", { userId: agency.users[0].id, userEmail: email });
  return NextResponse.redirect(new URL("/dashboard", origin), { status: 303 });
}
