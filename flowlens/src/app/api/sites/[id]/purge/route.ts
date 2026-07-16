import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { getCurrentUser } from "@/lib/session";
import { audit } from "@/lib/audit";

// 방문자 데이터 삭제 도구 (열람·삭제권 대응, 법무 4.10).
// 범위: 전체 / 기간 / 경로 / 특정 세션키. 삭제 후 빈 세션 정리 + 감사 로그.
export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await getCurrentUser();
  const origin = new URL(req.url).origin;
  if (!user) return NextResponse.redirect(new URL("/login", origin), { status: 303 });

  // 사이트 소속 검증 (멀티테넌시 격리)
  const site = await prisma.site.findFirst({ where: { id, client: { agencyId: user.agencyId } } });
  if (!site) return NextResponse.redirect(new URL("/dashboard", origin), { status: 303 });

  const form = await req.formData();
  const scope = String(form.get("scope") || "");
  const path = String(form.get("path") || "").trim();
  const sessionKey = String(form.get("sessionKey") || "").trim();
  const from = String(form.get("from") || "").trim();
  const to = String(form.get("to") || "").trim();

  const back = (n: number, extra = "") =>
    NextResponse.redirect(new URL(`/sites/${site.id}/data?deleted=${n}${extra}`, origin), { status: 303 });

  const where: Record<string, unknown> = { siteId: site.id };
  let detail = "";

  if (scope === "path") {
    if (!path) return back(0, "&err=path");
    where.path = path;
    detail = `path=${path}`;
  } else if (scope === "session") {
    if (!sessionKey) return back(0, "&err=session");
    const s = await prisma.session.findFirst({ where: { siteId: site.id, sessionKey } });
    if (!s) return back(0, "&err=nosession");
    where.sessionId = s.id;
    detail = `session=${sessionKey}`;
  } else if (scope === "range") {
    const gte = from ? new Date(from) : undefined;
    const lte = to ? new Date(to + "T23:59:59") : undefined;
    if (!gte && !lte) return back(0, "&err=range");
    where.ts = { ...(gte ? { gte } : {}), ...(lte ? { lte } : {}) };
    detail = `range=${from || "~"}..${to || "~"}`;
  } else if (scope === "all") {
    detail = "all";
  } else {
    return back(0, "&err=scope");
  }

  const res = await prisma.event.deleteMany({ where });
  // 마우스 이동 경로도 같은 범위로 삭제 (siteId/path/sessionId/ts 필드 동일)
  const resPath = await prisma.movePath.deleteMany({ where });
  // 이벤트가 사라져 비어버린 세션 정리
  await prisma.session.deleteMany({ where: { siteId: site.id, events: { none: {} } } });

  await audit(user.agencyId, "DELETE_DATA", {
    userId: user.id,
    userEmail: user.email,
    detail: `${site.name} · ${detail} · ${res.count + resPath.count}건`,
  });

  return back(res.count + resPath.count);
}
