import { NextRequest, NextResponse } from "next/server";
import { runDailyDrafts } from "@/lib/autoblog/run";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300; // 여러 편 생성 시 시간 여유

// Vercel Cron 전용: 매일 설정된 개수만큼 AI 블로그 "초안"을 생성한다.
// 보호: CRON_SECRET 필수(Bearer). Vercel Cron은 CRON_SECRET 설정 시 이 헤더를 자동으로 붙인다.
// ★ 초안(published=false)만 생성 — 자동 발행하지 않는다. ★
export async function GET(req: NextRequest) {
  const secret = process.env.CRON_SECRET;
  if (!secret) {
    return NextResponse.json({ ok: false, error: "CRON_SECRET 미설정" }, { status: 500 });
  }
  const auth = req.headers.get("authorization") || "";
  if (auth !== `Bearer ${secret}`) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }

  try {
    const out = await runDailyDrafts();
    return NextResponse.json({ ok: true, ...out });
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : "실행 오류" },
      { status: 500 }
    );
  }
}
