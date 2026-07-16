import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { getCurrentUser } from "@/lib/session";
import { getHeatmapPoints, getScrollBands } from "@/lib/metrics";

// 크롬 확장(실사이트 히트맵 오버레이 뷰어)용 데이터 API.
// mode=heat: 클릭 좌표(0~1 상대값) / mode=scroll: 스크롤 도달 밴드.
// period(일) 지정 시 기간 필터. 개인정보 없음(좌표·집계만). 외부 오리진 → CORS 허용.
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: CORS });
}

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const siteKey = url.searchParams.get("site") || "";
  const path = url.searchParams.get("path") || undefined;
  const mode = url.searchParams.get("mode") || "heat"; // heat | scroll
  const gesture = url.searchParams.get("gesture") || "click"; // click | all (heat 전용)
  const periodDays = Number(url.searchParams.get("period") || "0"); // 0=전체

  if (!siteKey) return NextResponse.json({ ok: false, error: "site 파라미터 필요" }, { status: 400, headers: CORS });

  // 🔒 인증 필수. siteKey는 고객사 페이지 소스에 공개되므로 그것만으로는 조회할 수 없다.
  //  1) token: 크롬 확장용 사이트별 비밀 토큰 (쿠키는 SameSite=Lax라 확장에서 전달 불가 → 토큰 방식)
  //  2) 세션: 앱에 로그인한 사용자가 본인 대행사 사이트를 볼 때
  const token = url.searchParams.get("token") || "";
  let site = null;

  if (token) {
    site = await prisma.site.findFirst({ where: { siteKey, overlayToken: token } });
    if (!site) return NextResponse.json({ ok: false, error: "인증 실패 (토큰을 확인하세요)" }, { status: 401, headers: CORS });
  } else {
    const user = await getCurrentUser();
    if (!user) return NextResponse.json({ ok: false, error: "인증이 필요합니다 (토큰 또는 로그인)" }, { status: 401, headers: CORS });
    site = await prisma.site.findFirst({ where: { siteKey, client: { agencyId: user.agencyId } } });
  }
  if (!site) return NextResponse.json({ ok: false, error: "unknown site" }, { status: 200, headers: CORS });

  const range = periodDays > 0 ? { from: new Date(Date.now() - periodDays * 86400000), to: new Date() } : undefined;
  // 개인화된 응답이므로 공용 캐시 금지
  const headers = { ...CORS, "Cache-Control": "private, no-store" };

  if (mode === "scroll") {
    const { bands, avgFold } = await getScrollBands(site.id, range);
    return NextResponse.json({ ok: true, mode: "scroll", site: site.name, bands, avgFold }, { status: 200, headers });
  }

  const raw = await getHeatmapPoints(site.id, path, 4000, range);
  const points = raw
    .filter((p) => (gesture === "all" ? true : ["click", "rage_click", "dead_click", "cta_click"].includes(p.type)))
    .map((p) => ({ x: p.x, y: p.y, type: p.type }));
  return NextResponse.json({ ok: true, mode: "heat", site: site.name, count: points.length, points }, { status: 200, headers });
}
