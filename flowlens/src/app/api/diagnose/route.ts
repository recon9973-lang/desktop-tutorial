import { NextRequest, NextResponse } from "next/server";
import { diagnose } from "@/lib/diagnose";

// 무료 진단 API: { url } 을 받아 실제로 해당 페이지를 점검한 결과를 반환.
export async function POST(req: NextRequest) {
  let body: { url?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ ok: false, error: "요청 형식이 올바르지 않습니다." }, { status: 400 });
  }
  if (!body.url) return NextResponse.json({ ok: false, error: "URL을 입력하세요." }, { status: 400 });

  const result = await diagnose(body.url);
  return NextResponse.json(result, { status: result.ok ? 200 : 200 });
}
