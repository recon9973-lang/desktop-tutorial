import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";
import { prisma } from "@/lib/db";
import { checkPassword, createSession } from "@/lib/session";
import { audit } from "@/lib/audit";

// 무차별 대입 방어: 같은 IP에서 15분 내 10회 실패하면 15분 잠금.
const WINDOW_MS = 15 * 60 * 1000;
const MAX_FAILS = 10;
const LOCK_MS = 15 * 60 * 1000;

// 원문 IP는 저장하지 않는다(개인정보 최소수집). 시크릿을 섞어 해시만 보관.
function ipHashOf(req: NextRequest): string {
  const ip = (req.headers.get("x-forwarded-for") || "").split(",")[0].trim() || req.headers.get("x-real-ip") || "unknown";
  return crypto.createHash("sha256").update(ip + "|" + (process.env.FLOWLENS_SECRET || "dev")).digest("hex").slice(0, 40);
}

export async function POST(req: NextRequest) {
  const form = await req.formData();
  const email = String(form.get("email") || "").trim().toLowerCase();
  const password = String(form.get("password") || "");
  const url = new URL(req.url);

  const ipHash = ipHashOf(req);
  const now = new Date();

  // 잠금 확인
  const throttle = await prisma.loginThrottle.findUnique({ where: { ipHash } });
  if (throttle?.lockUntil && throttle.lockUntil > now) {
    return NextResponse.redirect(new URL("/login?error=locked", url.origin), { status: 303 });
  }

  const user = await prisma.user.findUnique({ where: { email } });
  const ok = !!user && checkPassword(password, user.passwordHash);

  if (!ok) {
    // 실패 누적 (시간창이 지났으면 리셋)
    const fresh = !throttle || now.getTime() - throttle.windowAt.getTime() > WINDOW_MS;
    const fails = fresh ? 1 : throttle.fails + 1;
    const lock = fails >= MAX_FAILS ? new Date(now.getTime() + LOCK_MS) : null;
    await prisma.loginThrottle.upsert({
      where: { ipHash },
      create: { ipHash, fails, windowAt: now, lockUntil: lock },
      update: { fails, windowAt: fresh ? now : throttle!.windowAt, lockUntil: lock },
    });
    // 계정 존재 여부를 드러내지 않도록 실패 응답은 항상 동일
    return NextResponse.redirect(new URL("/login?error=1", url.origin), { status: 303 });
  }

  // 성공 → 실패 기록 초기화
  if (throttle) await prisma.loginThrottle.delete({ where: { ipHash } }).catch(() => {});

  await createSession(user!.id);
  await audit(user!.agencyId, "LOGIN", { userId: user!.id, userEmail: user!.email });
  return NextResponse.redirect(new URL("/dashboard", url.origin), { status: 303 });
}
