import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";
import { prisma } from "@/lib/db";
import { getCurrentUser } from "@/lib/session";
import { audit } from "@/lib/audit";
import { getPlan } from "@/lib/plans";

// 도메인 정규화: http(s)://, www., 경로/포트 제거 → 순수 호스트만 남긴다.
function normalizeDomain(input: string): string {
  return input
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .replace(/\/.*$/, "")
    .replace(/:\d+$/, "")
    .replace(/\.$/, "");
}

const INDUSTRIES = ["ECOMMERCE", "CLINIC", "EDU", "B2B", "ETC"];

// 고객사(신규 or 기존) + 사이트 생성. 대행사 범위로 격리.
export async function POST(req: NextRequest) {
  const user = await getCurrentUser();
  const origin = new URL(req.url).origin;
  if (!user) return NextResponse.redirect(new URL("/login", origin), { status: 303 });

  const form = await req.formData();
  const clientId = String(form.get("clientId") || "").trim();
  const clientName = String(form.get("clientName") || "").trim();
  const industryRaw = String(form.get("industry") || "ETC").trim().toUpperCase();
  const industry = INDUSTRIES.includes(industryRaw) ? industryRaw : "ETC";
  const siteName = String(form.get("siteName") || "").trim();
  const domain = normalizeDomain(String(form.get("domain") || ""));

  const fail = (code: string) => NextResponse.redirect(new URL(`/sites/new?error=${code}`, origin), { status: 303 });

  if (!siteName || !domain) return fail("invalid");
  // 도메인 최소 형식 검증 (점 포함, 공백 없음)
  if (!/^[a-z0-9.-]+\.[a-z]{2,}$/.test(domain)) return fail("domain");
  if (!clientId && !clientName) return fail("client");

  // 요금제 사이트 수 제한
  const plan = getPlan(user.agency.plan);
  const siteCount = await prisma.site.count({ where: { client: { agencyId: user.agencyId } } });
  if (siteCount >= plan.sites) return fail("limit");

  // 기존 고객사에 붙이거나 새로 생성 (반드시 내 대행사 범위)
  let cid = clientId;
  if (cid) {
    const c = await prisma.client.findFirst({ where: { id: cid, agencyId: user.agencyId } });
    if (!c) return fail("client");
  } else {
    const c = await prisma.client.create({
      data: { name: clientName, industry, agencyId: user.agencyId },
    });
    cid = c.id;
  }

  // 보관일은 요금제 기준으로 설정 (고지와 실제를 일치시킨다)
  // overlayToken: 크롬 확장용 비밀 토큰 (siteKey와 분리 — siteKey는 공개값이라 인증에 쓸 수 없음)
  const site = await prisma.site.create({
    data: {
      name: siteName,
      domain,
      clientId: cid,
      retentionDays: plan.retentionDays,
      overlayToken: crypto.randomBytes(24).toString("base64url"),
    },
  });
  await audit(user.agencyId, "CREATE_SITE", { userId: user.id, userEmail: user.email, detail: `${siteName} (${domain})` });

  // 등록 직후 설치 안내(스크립트/siteKey) 화면으로 이동
  return NextResponse.redirect(new URL(`/sites/${site.id}/install`, origin), { status: 303 });
}
