import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";
import { prisma } from "@/lib/db";
import { resolvePublicUrl } from "@/lib/diagnose";
import { captureFullPage } from "@/lib/screenshot";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

// 도메인 정규화 (www 제거, 소문자)
function toDomain(u: URL): string {
  return u.hostname.toLowerCase().replace(/^www\./, "").slice(0, 200);
}

// 원문 IP는 저장하지 않는다. 시크릿을 섞어 해시만 보관(남용 횟수 카운트 용도).
function ipHashOf(req: NextRequest): string {
  const ip = (req.headers.get("x-forwarded-for") || "").split(",")[0].trim() || req.headers.get("x-real-ip") || "unknown";
  return crypto.createHash("sha256").update(ip + "|" + (process.env.FLOWLENS_SECRET || "dev")).digest("hex").slice(0, 40);
}

// GET: 저장된 데모 배경 이미지 서빙 (?domain=)
export async function GET(req: NextRequest) {
  const domain = (new URL(req.url).searchParams.get("domain") || "").toLowerCase().replace(/^www\./, "");
  if (!domain) return new NextResponse("bad request", { status: 400 });
  const shot = await prisma.demoScreenshot.findUnique({ where: { domain } });
  if (!shot) return new NextResponse("not found", { status: 404 });
  return new NextResponse(Buffer.from(shot.image), {
    status: 200,
    headers: {
      "Content-Type": shot.mime || "image/png",
      "Cache-Control": "public, max-age=86400", // 데모 배경은 하루 캐시
      "X-Shot-Width": String(shot.width),
      "X-Shot-Height": String(shot.height),
    },
  });
}

// POST { url }: 데모 배경 준비.
//  - 같은 도메인이 이미 있으면 재사용(캡처 안 함)
//  - 없으면 IP당 1회만 캡처 허용 (남용/비용 방지)
export async function POST(req: NextRequest) {
  let input = "";
  try {
    input = String((await req.json())?.url || "");
  } catch {
    return NextResponse.json({ ok: false, error: "bad request" }, { status: 400 });
  }

  const url = await resolvePublicUrl(input);
  if (!url) return NextResponse.json({ ok: false, ready: false, reason: "invalid" }, { status: 400 });
  const domain = toDomain(url);

  // 1) 이미 캡처된 도메인이면 그대로 재사용
  const existing = await prisma.demoScreenshot.findUnique({ where: { domain }, select: { id: true } });
  if (existing) return NextResponse.json({ ok: true, ready: true, cached: true, domain });

  // 2) IP당 1회 제한 — 이미 캡처를 쓴 IP면 새 캡처 불가
  const ipHash = ipHashOf(req);
  const quota = await prisma.diagnoseQuota.findUnique({ where: { ipHash } });
  if (quota) {
    await prisma.diagnoseQuota.update({ where: { ipHash }, data: { count: { increment: 1 } } });
    return NextResponse.json({ ok: true, ready: false, reason: "quota", domain });
  }
  await prisma.diagnoseQuota.create({ data: { ipHash } });

  // 3) 캡처 후 저장
  try {
    const { buf, width, height, mime } = await captureFullPage(url.toString(), "DESKTOP");
    await prisma.demoScreenshot.create({
      data: { domain, image: Uint8Array.from(buf), mime, width, height },
    });
    return NextResponse.json({ ok: true, ready: true, cached: false, domain });
  } catch (e) {
    return NextResponse.json({ ok: false, ready: false, reason: "capture_failed", error: (e as Error).message.slice(0, 120) }, { status: 500 });
  }
}
