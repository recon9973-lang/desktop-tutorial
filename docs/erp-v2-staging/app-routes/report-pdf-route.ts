// 목표 경로: src/app/api/reports/[id]/pdf/route.ts
//
// 보고서 PDF 다운로드 라우트. 권한 검사 후 renderReportPdf 로 생성.
import { NextRequest, NextResponse } from "next/server";
import { getCurrentUser } from "@/server/session";
import { renderReportPdf } from "@/server/report-pdf";

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await getCurrentUser();
  if (!user) return new NextResponse("Unauthorized", { status: 401 });

  const { id } = await params;
  try {
    const { buffer, filename } = await renderReportPdf(id);
    return new NextResponse(buffer, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename*=UTF-8''${encodeURIComponent(filename)}`
      }
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "ERROR";
    return new NextResponse(msg === "NOT_FOUND" ? "Not found" : "Failed to render", { status: msg === "NOT_FOUND" ? 404 : 500 });
  }
}
