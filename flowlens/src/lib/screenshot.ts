import chromium from "@sparticuz/chromium";
import puppeteer from "puppeteer-core";

// 사이트 전체 페이지를 헤드리스 크롬으로 캡처한다.
// 반환: PNG 버퍼 + 캡처 폭/전체 높이(px). 히트맵 좌표(0~1)를 이 이미지 위에 정확히 정렬하는 데 사용.
// device에 따라 뷰포트·UA를 바꿔 캡처한다. 모바일은 레이아웃이 달라 별도 배경이 필요.
const PROFILES = {
  DESKTOP: {
    width: 1280,
    height: 900,
    ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    isMobile: false,
  },
  MOBILE: {
    width: 390, // iPhone 14 기준
    height: 844,
    ua: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    isMobile: true,
  },
} as const;

// 경로 비교용 정규화: 중복 슬래시를 하나로, 끝 슬래시 제거. ("//a/b/" → "/a/b")
export function normPath(p: string): string {
  return ("/" + String(p || "").replace(/^\/+/, "").replace(/\/+/g, "/")).replace(/\/+$/, "") || "/";
}

export async function captureFullPage(
  url: string,
  device: "DESKTOP" | "MOBILE" = "DESKTOP"
): Promise<{ buf: Uint8Array; width: number; height: number; mime: string; finalUrl: string; dialog: string | null }> {
  const p = PROFILES[device] ?? PROFILES.DESKTOP;
  const width = p.width;
  const browser = await puppeteer.launch({
    args: [...chromium.args, "--hide-scrollbars", "--disable-web-security"],
    defaultViewport: { width, height: p.height },
    executablePath: await chromium.executablePath(),
    headless: true,
  });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width, height: p.height, deviceScaleFactor: 1, isMobile: p.isMobile, hasTouch: p.isMobile });
    await page.setUserAgent(p.ua);

    // ⚠️ alert/confirm 이 뜨면 헤드리스 크롬은 응답할 사람이 없어 goto가 끝나지 않는다.
    // (good-tour.kr은 쿼리 없이 상세페이지를 열면 alert('잘못된 접근 방식입니다')를 띄운다
    //  → 45초 타임아웃 → 캡처가 영영 500. 반드시 닫아줘야 한다.)
    let dialog: string | null = null;
    page.on("dialog", async (d) => {
      if (!dialog) dialog = `${d.type()}: ${d.message().slice(0, 80)}`;
      try {
        await d.dismiss();
      } catch {
        /* 이미 닫힘 */
      }
    });

    // networkidle2는 채팅위젯·폴링 트래커가 있는 사이트에서 영영 오지 않는다.
    // 로드만 기다린 뒤, 잠잠해지면 좋고 아니면 그냥 진행한다(못 찍는 것보다 낫다).
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 25000 });
    await page.waitForNetworkIdle({ idleTime: 500, timeout: 8000 }).catch(() => {});
    // 지연 로딩 이미지·팝업 애니메이션이 자리잡도록 잠깐 대기
    await new Promise((r) => setTimeout(r, 1500));

    const finalUrl = page.url();
    const height = await page.evaluate(() => document.documentElement.scrollHeight);
    // WebP로 저장 (PNG 대비 약 8배 작음 → 저장·전송 비용 절감)
    const raw = await page.screenshot({ type: "webp", quality: 80, fullPage: true });
    // Prisma Bytes는 ArrayBuffer 기반 Uint8Array를 요구 → 새 배열로 복사
    return { buf: new Uint8Array(raw), width, height, mime: "image/webp", finalUrl, dialog };
  } finally {
    await browser.close();
  }
}
