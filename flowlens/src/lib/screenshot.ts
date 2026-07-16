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

export async function captureFullPage(url: string, device: "DESKTOP" | "MOBILE" = "DESKTOP"): Promise<{ buf: Uint8Array; width: number; height: number; mime: string }> {
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
    await page.goto(url, { waitUntil: "networkidle2", timeout: 45000 });
    // 지연 로딩 이미지·팝업 애니메이션이 자리잡도록 잠깐 대기
    await new Promise((r) => setTimeout(r, 2000));
    const height = await page.evaluate(() => document.documentElement.scrollHeight);
    // WebP로 저장 (PNG 대비 약 8배 작음 → 저장·전송 비용 절감)
    const raw = await page.screenshot({ type: "webp", quality: 80, fullPage: true });
    // Prisma Bytes는 ArrayBuffer 기반 Uint8Array를 요구 → 새 배열로 복사
    return { buf: new Uint8Array(raw), width, height, mime: "image/webp" };
  } finally {
    await browser.close();
  }
}
