import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { getCurrentUser } from "@/lib/session";
import { PLANS } from "@/lib/plans";
import { audit } from "@/lib/audit";
import { syncRetentionForPlan } from "@/lib/billing";

// 요금제 변경.
// ⚠️ MVP 스텁: 실제 결제(PG) 연동 없이 요금제만 즉시 변경한다.
// 운영에서는 이 지점에서 국내 PG/Stripe 결제 세션을 생성하고, 결제 성공 웹훅에서 plan을 반영해야 한다.
export async function POST(req: NextRequest) {
  const user = await getCurrentUser();
  const origin = new URL(req.url).origin;
  if (!user) return NextResponse.redirect(new URL("/login", origin), { status: 303 });
  if (user.role !== "OWNER") return NextResponse.redirect(new URL("/billing?error=role", origin), { status: 303 });

  const form = await req.formData();
  const plan = String(form.get("plan") || "");
  const target = PLANS.find((p) => p.key === plan);
  if (!target) return NextResponse.redirect(new URL("/billing?error=plan", origin), { status: 303 });

  // 🔒 유료 플랜은 결제 검증 없이 부여하지 않는다.
  // (이전에는 누구나 즉시 AGENCY로 올려 모든 기능을 무단 사용할 수 있었음 — 결제 우회)
  // 다운그레이드(무료로 내리기)만 셀프 허용하고, 업그레이드는 결제 완료 후에만 반영한다.
  if (target.price > 0) {
    const paymentReady = !!process.env.TOSS_SECRET_KEY;
    // 결제 연동 전에는 자동 부여 금지. 연동 후에도 이 라우트가 아니라
    // 결제 성공 웹훅에서 plan을 반영해야 한다.
    return NextResponse.redirect(
      new URL(`/billing?error=${paymentReady ? "checkout_required" : "payment_unavailable"}`, origin),
      { status: 303 }
    );
  }

  // 셀프 다운그레이드(무료로 내리기). 보관일은 즉시 줄이지 않는다(데이터 삭제 방지) —
  // 관리자 경로와 동일하게 syncRetentionForPlan 이 올리기만 한다. docs/08 정책.
  await prisma.agency.update({ where: { id: user.agencyId }, data: { plan } });
  await syncRetentionForPlan(prisma, user.agencyId, plan);
  await audit(user.agencyId, "CHANGE_PLAN", { userId: user.id, userEmail: user.email, detail: plan });
  return NextResponse.redirect(new URL("/billing?changed=1", origin), { status: 303 });
}
