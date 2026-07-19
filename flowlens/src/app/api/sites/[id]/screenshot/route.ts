import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { loadSiteForUser } from "@/lib/site";
import { captureFullPage, normPath } from "@/lib/screenshot";
import { resolvePublicUrl } from "@/lib/diagnose";
import { rateLimit } from "@/lib/ratelimit";

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
  const { site, user } = await loadSiteForUser(id);
  if (!site || !user) return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 403 });

  // 캡처는 헤드리스 크롬을 띄우는 무거운 작업(1회 수십 초·고메모리)이다.
  // 인증이 있어도 횟수 제한이 없으면 계정 하나로 함수 비용을 태울 수 있다(보안감사 HIGH).
  // 대행사당 1분에 10회로 제한. 정상 사용(페이지별 배경 캡처)에는 충분하다.
  const rl = await rateLimit(`shot:${user.agencyId}`, 10, 60_000);
  if (!rl.ok) {
    return NextResponse.json(
      { ok: false, error: `캡처 요청이 너무 많습니다. ${rl.retryAfterSec}초 후 다시 시도하세요.` },
      { status: 429, headers: { "Retry-After": String(rl.retryAfterSec) } }
    );
  }

  let path = "/";
  let device: "DESKTOP" | "MOBILE" = "DESKTOP";
  let dismissPopups = false;
  let sampleUrl = ""; // 파라미터 필요 페이지(상세·주문·게시글)의 대표 주소
  try {
    const ct = req.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      const b = await req.json();
      path = cleanPath(b?.path ?? "/");
      device = cleanDevice(b?.device);
      dismissPopups = b?.dismissPopups === true;
      sampleUrl = String(b?.sampleUrl || "").trim();
    } else {
      const form = await req.formData();
      path = cleanPath(String(form.get("path") || "/"));
      device = cleanDevice(String(form.get("device") || ""));
      dismissPopups = String(form.get("dismissPopups") || "") === "1";
      sampleUrl = String(form.get("sampleUrl") || "").trim();
    }
  } catch {
    /* 기본값 */
  }

  const dHost = site.domain.replace(/^https?:\/\//, "").replace(/\/.*$/, "").replace(/^www\./, "").toLowerCase();

  // 캡처 대상 URL 결정.
  //  - 기본: 등록 도메인 + 경로 (도용 방지)
  //  - 대표 주소(sampleUrl): 상세페이지처럼 ?상품번호=… 가 있어야 열리는 페이지의 실제 주소.
  //    같은 도메인·같은 경로만 허용하고, 그 화면을 이 경로 그룹의 대표 배경으로 저장한다.
  let target: string;
  if (sampleUrl) {
    let u: URL;
    try {
      u = new URL(/^https?:\/\//i.test(sampleUrl) ? sampleUrl : `https://${sampleUrl}`);
    } catch {
      return NextResponse.json({ ok: false, error: "주소 형식이 올바르지 않습니다." }, { status: 400 });
    }
    const sHost = u.hostname.replace(/^www\./, "").toLowerCase();
    if (sHost !== dHost) {
      return NextResponse.json({ ok: false, error: `등록한 도메인(${dHost})의 주소만 넣을 수 있습니다.` }, { status: 400 });
    }
    if (normPath(u.pathname) !== normPath(path)) {
      return NextResponse.json({ ok: false, error: `이 페이지(${normPath(path)})와 경로가 다른 주소입니다.` }, { status: 400 });
    }
    const safe = await resolvePublicUrl(u.toString());
    if (!safe) {
      return NextResponse.json({ ok: false, error: "이 주소는 열 수 없습니다." }, { status: 400 });
    }
    target = safe.toString();
  } else {
    target = `https://${site.domain}${path === "/" ? "/" : path}`;
  }

  try {
    const { buf, width, height, mime, finalUrl, dialog, popupsHidden } = await captureFullPage(target, device, { dismissPopups });

    // 요청한 경로와 실제 도착지가 다르면 저장하지 않는다.
    // 추적기는 개인정보 보호를 위해 쿼리(?상품번호=…)를 떼고 경로만 저장하는데,
    // 상세페이지는 그 쿼리가 있어야 열린다. 쿼리 없이 열면 홈·목록으로 튕기므로
    // 그 화면을 배경으로 쓰면 "상세페이지 클릭"을 엉뚱한 그림 위에 뿌리게 된다.
    // 틀린 배경보다 정직한 실패가 낫다(문서 5-⑥ 원칙).
    let landed = "";
    try {
      landed = normPath(new URL(finalUrl).pathname);
    } catch {
      /* 파싱 실패 시 검사 생략 */
    }
    if (landed && landed !== normPath(path)) {
      return NextResponse.json(
        {
          ok: false,
          reason: "redirected",
          landed,
          dialog,
          error: `이 페이지는 주소만으로 열리지 않아 배경을 만들 수 없습니다. (${normPath(path)} → ${landed}로 이동${dialog ? `, 경고창: ${dialog}` : ""})`,
        },
        { status: 422 }
      );
    }

    // ArrayBuffer 기반 Uint8Array로 정규화 (Prisma Bytes 타입 요구)
    const image = Uint8Array.from(buf);
    await prisma.screenshot.upsert({
      where: { siteId_path_device: { siteId: site.id, path, device } },
      create: { siteId: site.id, path, device, image, mime, width, height },
      update: { image, mime, width, height, capturedAt: new Date() },
    });
    return NextResponse.json({ ok: true, device, width, height, popupsHidden });
  } catch (e) {
    return NextResponse.json({ ok: false, error: (e as Error).message.slice(0, 200) }, { status: 500 });
  }
}
