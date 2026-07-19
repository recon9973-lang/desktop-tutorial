import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { rollupExpiredEvents } from "@/lib/rollup";
import { sendEmail, trialReminderHtml } from "@/lib/email";
import { audit } from "@/lib/audit";

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

  // 체험 만료 3일 이내 리마인드 메일 (RESEND_API_KEY 설정 시에만 실제 발송). 대행사당 1회.
  let remindersSent = 0;
  const soon = new Date(Date.now() + 3 * 24 * 60 * 60 * 1000);
  const expiring = await prisma.agency.findMany({
    where: { plan: "FREE", trialEndsAt: { gte: new Date(), lte: soon } },
    include: { users: { where: { role: "OWNER" }, take: 1, select: { email: true, name: true } } },
  });
  for (const a of expiring) {
    const owner = a.users[0];
    if (!owner || !a.trialEndsAt) continue;
    const already = await prisma.auditLog.findFirst({ where: { agencyId: a.id, action: "TRIAL_REMINDER" } });
    if (already) continue; // 이미 보냈으면 건너뜀(중복 방지)
    const daysLeft = Math.max(1, Math.ceil((a.trialEndsAt.getTime() - Date.now()) / 86_400_000));
    const res = await sendEmail({
      to: owner.email,
      subject: `FlowLens 무료 체험이 ${daysLeft}일 남았어요`,
      html: trialReminderHtml(owner.name, daysLeft),
    });
    // 실제 발송에 성공했을 때만 감사로그를 남긴다 → 키 미설정(skipped)/오류면 다음 실행에서 재시도.
    if (res.ok) {
      await audit(a.id, "TRIAL_REMINDER", { userEmail: owner.email, detail: `체험 만료 ${daysLeft}일 전 리마인드` });
      remindersSent++;
    }
  }

  return NextResponse.json({ ok: true, sites: sites.length, rolledSites, deletedEvents: totalDeleted, remindersSent });
}
