import { NextRequest, NextResponse } from "next/server";
import { loadSiteForUser } from "@/lib/site";
import { rollupExpiredEvents } from "@/lib/rollup";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

// 보관기간이 지난 원시 이벤트를 집계 스냅샷으로 롤업 + 삭제.
// days 미지정 시 사이트 retentionDays 사용. days=0이면 현재까지 전부 롤업(테스트용).
export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { site } = await loadSiteForUser(id);
  if (!site) return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 403 });

  const url = new URL(req.url);
  const daysParam = url.searchParams.get("days");
  const days = daysParam !== null ? Math.max(0, Number(daysParam)) : site.retentionDays;
  const olderThan = new Date(Date.now() - days * 24 * 60 * 60 * 1000);

  try {
    const result = await rollupExpiredEvents(site.id, olderThan);
    return NextResponse.json({ ok: true, days, olderThan: olderThan.toISOString(), ...result });
  } catch (e) {
    return NextResponse.json({ ok: false, error: (e as Error).message.slice(0, 200) }, { status: 500 });
  }
}
