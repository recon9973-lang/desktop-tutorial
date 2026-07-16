import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { loadSiteForUser } from "@/lib/site";
import { captureFullPage } from "@/lib/screenshot";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

function cleanPath(p: string | null): string {
  if (!p) return "/";
  let s = p.trim();
  if (!s.startsWith("/")) s = "/" + s;
  return s.slice(0, 300);
}

// 모바일은 레이아웃이 달라 별도 배경이 필요. 그 외는 데스크톱 기준.
function cleanDevice(d: string | null | undefined): "DESKTOP" | "MOBILE" {
  return String(d || "").toUpperCase() === "MOBILE" ? "MOBILE" : "DESKTOP";
}

// GET: 저장된 스크린샷 이미지를 반환 (없으면 404). <img src>로 사용.
export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { site } = await loadSiteForUser(id);
  if (!site) return new NextResponse("not found", { status: 404 });

  const sp = new URL(req.url).searchParams;
  const path = cleanPath(sp.get("path"));
  const device = cleanDevice(sp.get("device"));
  const shot = await prisma.screenshot.findUnique({ where: { siteId_path_device: { siteId: site.id, path, device } } });
  if (!shot) return new NextResponse("no screenshot", { status: 404 });

  return new NextResponse(Buffer.from(shot.image), {
    status: 200,
    headers: {
      "Content-Type": shot.mime || "image/png",
      "Cache-Control": "private, max-age=300",
      "X-Shot-Width": String(shot.width),
      "X-Shot-Height": String(shot.height),
    },
  });
}

// POST: 사이트 페이지를 촬영해 저장(있으면 갱신). { path } 폼/JSON.
export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { site } = await loadSiteForUser(id);
  if (!site) return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 403 });

  let path = "/";
  let device: "DESKTOP" | "MOBILE" = "DESKTOP";
  try {
    const ct = req.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      const b = await req.json();
      path = cleanPath(b?.path ?? "/");
      device = cleanDevice(b?.device);
    } else {
      const form = await req.formData();
      path = cleanPath(String(form.get("path") || "/"));
      device = cleanDevice(String(form.get("device") || ""));
    }
  } catch {
    /* 기본값 */
  }

  // 등록 도메인 기준 URL 구성 (도용 방지: 사용자가 임의 URL 못 넣게 site.domain 사용)
  const target = `https://${site.domain}${path === "/" ? "/" : path}`;

  try {
    const { buf, width, height, mime } = await captureFullPage(target, device);
    // ArrayBuffer 기반 Uint8Array로 정규화 (Prisma Bytes 타입 요구)
    const image = Uint8Array.from(buf);
    await prisma.screenshot.upsert({
      where: { siteId_path_device: { siteId: site.id, path, device } },
      create: { siteId: site.id, path, device, image, mime, width, height },
      update: { image, mime, width, height, capturedAt: new Date() },
    });
    return NextResponse.json({ ok: true, device, width, height });
  } catch (e) {
    return NextResponse.json({ ok: false, error: (e as Error).message.slice(0, 200) }, { status: 500 });
  }
}
