import dns from "dns/promises";
import net from "net";

// 무료 진단: 방문자가 입력한 URL의 HTML을 실제로 가져와 기술/UX 기본 점검을 수행한다.
// (행동 데이터 — 클릭·스크롤·이탈 — 는 추적 설치가 있어야만 알 수 있으므로 여기서는 다루지 않는다.)

export type Check = {
  key: string;
  label: string;
  status: "pass" | "warn" | "fail";
  detail: string;
};

// 설치 안내를 자동화하기 위한 플랫폼 판별 결과
export type PlatformKey = "wordpress" | "cafe24" | "imweb" | "sixshop" | "wix" | "godo" | "makeshop" | "shopify" | "gtm" | "unknown";
export type Platform = { key: PlatformKey; name: string; how: string };

const PLATFORMS: { key: PlatformKey; name: string; how: string; test: RegExp }[] = [
  { key: "wordpress", name: "워드프레스", how: "전용 플러그인을 올리고 활성화만 하면 됩니다 (코드 편집 없음).", test: /wp-content|wp-includes|content="WordPress/i },
  { key: "cafe24", name: "카페24", how: "관리자 → 디자인 → 스마트디자인 편집에서 공통 레이아웃 </head> 위에 붙여넣기.", test: /cafe24|EC_GLOBAL|\.cafe24\.com/i },
  { key: "imweb", name: "아임웹", how: "관리자 → 사이트 관리 → 고급 → head 태그 삽입 칸에 붙여넣기.", test: /imweb|\.imweb\.me/i },
  { key: "sixshop", name: "식스샵", how: "관리자 → 설정 → 고급 설정 → head 스크립트에 붙여넣기.", test: /sixshop/i },
  { key: "wix", name: "윅스(Wix)", how: "설정 → 사용자 지정 코드 → head 영역에 붙여넣기.", test: /wix\.com|X-Wix|wixstatic/i },
  { key: "godo", name: "고도몰", how: "관리자 → 디자인 → HTML 편집에서 <head>에 붙여넣기.", test: /godo|godomall/i },
  { key: "makeshop", name: "메이크샵", how: "관리자 → 디자인 → HTML 편집에서 <head>에 붙여넣기.", test: /makeshop/i },
  { key: "shopify", name: "Shopify", how: "테마 → 코드 편집 → theme.liquid의 <head>에 붙여넣기.", test: /cdn\.shopify\.com|Shopify\.theme/i },
  // GTM은 마지막에 (다른 플랫폼과 함께 쓰이므로, 플랫폼을 못 찾았을 때만 제안)
  { key: "gtm", name: "Google Tag Manager", how: "GTM에서 [태그 → 새로 만들기 → 맞춤 HTML]에 붙여넣고 트리거는 All Pages로 게시.", test: /GTM-[A-Z0-9]{4,}/ },
];

// HTML로 사이트 제작 플랫폼을 추정한다 → 그 플랫폼 전용 설치 안내만 보여주기 위함.
export function detectPlatform(html: string): Platform {
  for (const p of PLATFORMS) {
    if (p.test.test(html)) return { key: p.key, name: p.name, how: p.how };
  }
  return { key: "unknown", name: "직접 제작/기타", how: "사이트 모든 페이지의 <head> 안에 아래 한 줄을 넣어주세요." };
}

export type Diagnosis =
  | { ok: false; error: string }
  | {
      ok: true;
      url: string;
      title: string;
      score: number;
      checks: Check[];
      summary: string;
      platform: Platform;
    };

// SSRF 방어: 내부/사설/루프백 IP로의 요청 차단.
// IPv4-mapped IPv6(::ffff:127.0.0.1 등)와 CGNAT(100.64/10)까지 포함해 우회를 막는다.
function isPrivateIp(ip: string): boolean {
  let addr = ip;
  const mapped = /^::ffff:(.+)$/i.exec(addr);
  if (mapped) {
    if (net.isIPv4(mapped[1])) {
      addr = mapped[1];
    } else {
      // 16진 표기(::ffff:7f00:1)를 점 표기로 환산
      const hx = mapped[1].split(":");
      if (hx.length === 2) {
        const hi = parseInt(hx[0], 16);
        const lo = parseInt(hx[1], 16);
        if (Number.isFinite(hi) && Number.isFinite(lo)) addr = `${hi >> 8}.${hi & 255}.${lo >> 8}.${lo & 255}`;
      }
    }
  }
  if (addr === "127.0.0.1" || addr === "::1" || addr === "0.0.0.0" || addr === "::") return true;
  if (net.isIPv4(addr)) {
    const [a, b] = addr.split(".").map(Number);
    if (a === 10 || a === 127 || a === 0) return true;
    if (a === 169 && b === 254) return true; // link-local / 클라우드 메타데이터
    if (a === 192 && b === 168) return true;
    if (a === 172 && b >= 16 && b <= 31) return true;
    if (a === 100 && b >= 64 && b <= 127) return true; // CGNAT 100.64.0.0/10
    return false;
  }
  const low = addr.toLowerCase();
  if (low.startsWith("fc") || low.startsWith("fd") || low.startsWith("fe80")) return true;
  return false;
}

// 호스트의 "모든" 해석 주소가 공인일 때만 true. 하나라도 사설이면 차단(부분 우회 방지).
export async function isHostPublic(hostname: string): Promise<boolean> {
  if (!hostname) return false;
  try {
    const addrs = await dns.lookup(hostname, { all: true });
    if (!addrs.length) return false;
    return addrs.every((a) => !isPrivateIp(a.address));
  } catch {
    return false;
  }
}

// SSRF-safe fetch: 리다이렉트를 수동으로 따라가며 매 홉의 호스트를 재검증한다.
// (초기 호스트만 검사하고 redirect:follow 하면 내부망으로 우회되는 문제를 막는다.)
export async function safeFetch(
  start: URL,
  headers: Record<string, string>,
  signal: AbortSignal,
  maxRedirects = 4
): Promise<Response> {
  let current = start;
  for (let i = 0; i <= maxRedirects; i++) {
    if (!(await isHostPublic(current.hostname))) throw new Error("blocked_host");
    const res = await fetch(current.toString(), { headers, signal, redirect: "manual" });
    const loc = res.status >= 300 && res.status < 400 ? res.headers.get("location") : null;
    if (!loc) return res;
    let next: URL;
    try {
      next = new URL(loc, current);
    } catch {
      throw new Error("bad_redirect");
    }
    if (next.protocol !== "http:" && next.protocol !== "https:") throw new Error("bad_redirect_scheme");
    current = next;
  }
  throw new Error("too_many_redirects");
}

function normalizeUrl(input: string): URL | null {
  let s = input.trim();
  if (!s) return null;
  if (!/^https?:\/\//i.test(s)) s = "https://" + s;
  try {
    const u = new URL(s);
    if (u.protocol !== "http:" && u.protocol !== "https:") return null;
    return u;
  } catch {
    return null;
  }
}

// 외부 요청(스크린샷 등) 전에 쓰는 공개 URL 가드.
// 형식 검증 + DNS 해석 후 사설/루프백 IP면 null (SSRF 방어).
export async function resolvePublicUrl(input: string): Promise<URL | null> {
  const url = normalizeUrl(input);
  if (!url) return null;
  if (!(await isHostPublic(url.hostname))) return null;
  return url;
}

export async function diagnose(input: string): Promise<Diagnosis> {
  const url = normalizeUrl(input);
  if (!url) return { ok: false, error: "올바른 URL을 입력하세요. (예: example.com)" };

  // SSRF 가드: 호스트를 실제 IP로 해석해 사설/루프백이면 차단
  try {
    const { address } = await dns.lookup(url.hostname);
    if (isPrivateIp(address)) return { ok: false, error: "이 주소는 진단할 수 없습니다." };
  } catch {
    return { ok: false, error: "주소를 찾을 수 없습니다. 도메인을 확인하세요." };
  }

  // HTML 가져오기 (타임아웃 7초, 크기 제한)
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 7000);
  let html = "";
  try {
    // SSRF-safe: 리다이렉트 홉마다 호스트를 재검증한다(내부망 우회 방지).
    // 일부 사이트의 보안 설정이 봇 UA를 차단해 빈 페이지를 주므로 일반 브라우저 UA를 쓴다.
    const res = await safeFetch(url, {
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
      "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    }, controller.signal);
    if (!res.ok) return { ok: false, error: `사이트가 응답하지 않습니다 (HTTP ${res.status}).` };
    const buf = await res.arrayBuffer();
    html = new TextDecoder("utf-8").decode(buf.slice(0, 500_000)); // 최대 ~500KB만 분석
  } catch {
    return { ok: false, error: "사이트에 접속할 수 없습니다. 주소를 확인하거나 잠시 후 다시 시도하세요." };
  } finally {
    clearTimeout(timer);
  }

  // 일부 사이트는 보안 설정(WAF)이 자동 점검 요청에 빈/차단 페이지를 200으로 돌려준다.
  // 이때 그대로 채점하면 "분석 도구 없음" 같은 틀린 결과가 나오므로, 정직하게 실패로 처리한다.
  const hasTitle = /<title[^>]*>[^<]*[^\s<][^<]*<\/title>/i.test(html);
  const hasBody = /<body[\s>]/i.test(html);
  if (!hasTitle && (!hasBody || html.length < 2000)) {
    return {
      ok: false,
      error:
        "이 사이트는 보안 설정 때문에 자동 점검 요청을 차단하고 있어 진단할 수 없습니다. (사이트 자체는 정상일 수 있습니다) 설치는 아래 안내를 참고하거나 담당자에게 문의해 주세요.",
    };
  }

  const sizeKb = Math.round(html.length / 1024);
  const titleMatch = html.match(/<title[^>]*>([^<]*)<\/title>/i);
  const title = (titleMatch?.[1] || "").trim();

  const has = (re: RegExp) => re.test(html);
  const countMatches = (re: RegExp) => (html.match(re) || []).length;

  const checks: Check[] = [];

  // 1) HTTPS
  checks.push(
    url.protocol === "https:"
      ? { key: "https", label: "보안 연결(HTTPS)", status: "pass", detail: "HTTPS를 사용합니다." }
      : { key: "https", label: "보안 연결(HTTPS)", status: "fail", detail: "HTTP입니다. HTTPS로 전환하세요. 행동 추적도 HTTPS가 필요합니다." }
  );

  // 2) 모바일 대응 (viewport)
  checks.push(
    has(/<meta[^>]+name=["']viewport["']/i)
      ? { key: "viewport", label: "모바일 대응", status: "pass", detail: "viewport 설정이 있습니다." }
      : { key: "viewport", label: "모바일 대응", status: "fail", detail: "viewport 메타가 없습니다. 모바일에서 깨질 수 있습니다." }
  );

  // 3) 페이지 제목
  checks.push(
    title.length >= 5 && title.length <= 60
      ? { key: "title", label: "페이지 제목", status: "pass", detail: `"${title.slice(0, 40)}"` }
      : title
      ? { key: "title", label: "페이지 제목", status: "warn", detail: `제목 길이가 ${title.length}자입니다. 5~60자를 권장합니다.` }
      : { key: "title", label: "페이지 제목", status: "fail", detail: "제목(title)이 없습니다." }
  );

  // 4) 메타 설명
  checks.push(
    has(/<meta[^>]+name=["']description["']/i)
      ? { key: "desc", label: "메타 설명", status: "pass", detail: "검색·공유용 설명이 있습니다." }
      : { key: "desc", label: "메타 설명", status: "warn", detail: "메타 설명이 없습니다. 검색 노출에 불리합니다." }
  );

  // 5) CTA 버튼
  const ctaCount =
    countMatches(/<button[\s>]/gi) + countMatches(/<a[^>]+class=["'][^"']*btn/gi) + countMatches(/type=["']submit["']/gi);
  checks.push(
    ctaCount >= 1
      ? { key: "cta", label: "행동 유도 버튼(CTA)", status: "pass", detail: `버튼/CTA 요소 약 ${ctaCount}개를 발견했습니다.` }
      : { key: "cta", label: "행동 유도 버튼(CTA)", status: "warn", detail: "명확한 버튼/CTA를 찾지 못했습니다." }
  );

  // 6) 폼(문의/구매/예약)
  checks.push(
    has(/<form[\s>]/i)
      ? { key: "form", label: "폼(문의·예약·구매)", status: "pass", detail: "폼이 있습니다. FlowLens로 폼 이탈을 분석할 수 있습니다." }
      : { key: "form", label: "폼(문의·예약·구매)", status: "warn", detail: "폼을 찾지 못했습니다. 전환 지점이 명확한지 확인하세요." }
  );

  // 7) 이미지 alt
  const imgs = countMatches(/<img\b[^>]*>/gi);
  const imgsWithAlt = (html.match(/<img\b[^>]*\balt=/gi) || []).length;
  const altRatio = imgs > 0 ? Math.round((imgsWithAlt / imgs) * 100) : 100;
  checks.push(
    imgs === 0 || altRatio >= 80
      ? { key: "alt", label: "이미지 대체텍스트", status: "pass", detail: imgs === 0 ? "이미지가 적습니다." : `이미지 ${imgs}개 중 ${altRatio}%에 alt가 있습니다.` }
      : { key: "alt", label: "이미지 대체텍스트", status: "warn", detail: `이미지 ${imgs}개 중 alt는 ${altRatio}%뿐입니다. 접근성·SEO에 불리합니다.` }
  );

  // 8) 페이지 무게
  checks.push(
    sizeKb <= 250
      ? { key: "size", label: "첫 화면 HTML 용량", status: "pass", detail: `약 ${sizeKb}KB. 가벼운 편입니다.` }
      : { key: "size", label: "첫 화면 HTML 용량", status: "warn", detail: `약 ${sizeKb}KB. 무거우면 모바일 이탈이 늘 수 있습니다.` }
  );

  // 9) 분석/추적 도구 설치 여부
  const hasAnalytics = has(/gtag\(|googletagmanager|google-analytics|clarity\.ms|\/clarity|hotjar|mouseflow|flowlens/i);
  checks.push(
    hasAnalytics
      ? { key: "analytics", label: "분석 도구", status: "pass", detail: "분석 스크립트가 감지됩니다. 행동 분석까지 더하면 개선점이 보입니다." }
      : { key: "analytics", label: "분석 도구", status: "warn", detail: "분석 도구가 감지되지 않습니다. 방문자 행동을 놓치고 있을 수 있습니다." }
  );

  const passCount = checks.filter((c) => c.status === "pass").length;
  const score = Math.round((passCount / checks.length) * 100);

  const summary =
    score >= 80
      ? "기본기는 탄탄합니다. 이제 방문자가 '어디서 망설이고 이탈하는지'를 보면 전환을 끌어올릴 수 있습니다."
      : score >= 50
      ? "기본 점검에서 개선할 부분이 보입니다. 아래 항목을 먼저 정리하고, 행동 분석으로 실제 이탈 지점을 찾으세요."
      : "기본 항목에서 놓친 부분이 많습니다. 아래를 먼저 개선하면 광고비 대비 효율이 크게 달라질 수 있습니다.";

  return { ok: true, url: url.toString(), title, score, checks, summary, platform: detectPlatform(html) };
}
