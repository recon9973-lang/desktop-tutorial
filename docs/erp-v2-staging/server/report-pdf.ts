// 목표 경로: src/server/report-pdf.ts
//
// 보고서 PDF 자동생성. 지표(metrics) + 코멘트를 HTML로 렌더 → PDF 변환.
// 변환기: Playwright(레포에 이미 devDependency 존재) 또는 puppeteer.
// 여기서는 HTML 빌드 + PDF 변환 인터페이스를 정의(런타임 변환은 renderPdf에 위임).
import { db } from "@/server/db";

function esc(s: unknown): string {
  return String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] as string));
}

/** 보고서 → 배포용 HTML 문자열. */
export async function buildReportHtml(reportId: string): Promise<{ html: string; title: string }> {
  const report = await db.report.findUnique({
    where: { id: reportId },
    include: { client: { select: { name: true } }, author: { select: { name: true } } }
  });
  if (!report) throw new Error("NOT_FOUND");

  const metrics = (report.metrics as Record<string, unknown> | null) ?? {};
  const ranks = Array.isArray((metrics as { keywordRanks?: unknown }).keywordRanks)
    ? (metrics as { keywordRanks: Array<{ keyword: string; rank: number | null }> }).keywordRanks
    : [];

  const rankRows = ranks.map((r) => `<tr><td>${esc(r.keyword)}</td><td style="text-align:right">${r.rank ?? "-"}</td></tr>`).join("");
  const otherRows = Object.entries(metrics)
    .filter(([k]) => k !== "keywordRanks" && k !== "keywordRanksCollectedAt")
    .map(([k, v]) => `<tr><td>${esc(k)}</td><td style="text-align:right">${esc(typeof v === "object" ? JSON.stringify(v) : v)}</td></tr>`)
    .join("");

  const title = `${report.client?.name ?? ""} ${esc(report.reportingMonth)} 월간 보고서`;
  const html = `<!doctype html><html lang="ko"><head><meta charset="utf-8">
<style>
  body{font-family:'Malgun Gothic',sans-serif;color:#0d253d;padding:40px;}
  h1{color:#533afd;font-size:22px;} h2{font-size:15px;margin-top:24px;border-bottom:2px solid #533afd;padding-bottom:6px;}
  table{width:100%;border-collapse:collapse;margin-top:8px;font-size:13px;}
  td{border-bottom:1px solid #e3e8ee;padding:8px;}
  .meta{color:#64748b;font-size:12px;margin-top:4px;}
</style></head><body>
  <h1>${esc(title)}</h1>
  <div class="meta">거래처: ${esc(report.client?.name)} · 작성자: ${esc(report.author?.name)} · 상태: ${esc(report.status)}</div>
  <h2>키워드 순위</h2>
  <table><tbody>${rankRows || '<tr><td colspan="2">데이터 없음</td></tr>'}</tbody></table>
  <h2>기타 성과 지표</h2>
  <table><tbody>${otherRows || '<tr><td colspan="2">데이터 없음</td></tr>'}</tbody></table>
  <h2>요약 코멘트</h2>
  <div>${esc((metrics as { summary?: string }).summary ?? "")}</div>
</body></html>`;
  return { html, title };
}

/**
 * HTML → PDF 변환. Playwright chromium 사용(레포 devDep).
 * 반환: PDF Buffer. 라우트에서 다운로드 응답으로 사용.
 */
export async function renderReportPdf(reportId: string): Promise<{ buffer: Buffer; filename: string }> {
  const { html, title } = await buildReportHtml(reportId);
  // 동적 import로 서버 런타임에서만 로드
  const { chromium } = await import("playwright");
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    await page.setContent(html, { waitUntil: "networkidle" });
    const buffer = await page.pdf({ format: "A4", printBackground: true, margin: { top: "20mm", bottom: "20mm", left: "15mm", right: "15mm" } });
    return { buffer, filename: `${title}.pdf` };
  } finally {
    await browser.close();
  }
}
