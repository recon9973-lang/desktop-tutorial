// 서버측 개인정보 방어 (법무 검토 5.2/5.3/5.4 반영).
// SDK가 1차로 정제/마스킹하지만, 서버에서도 2차로 방어한다(신뢰 경계).

const PII_PATTERNS: RegExp[] = [
  /[\w.+-]+@[\w-]+\.[\w.-]+/g, // email
  /\b\d{2,3}[-\s]?\d{3,4}[-\s]?\d{4}\b/g, // phone
  /\b(?:\d[ -]?){13,16}\b/g, // card
  /\b\d{6}[-\s]?\d{7}\b/g, // 주민등록번호
];

export function maskPII(text: string): string {
  let t = text;
  for (const re of PII_PATTERNS) t = t.replace(re, "***");
  return t;
}

// URL: query/hash 제거하고 origin+pathname만 저장.
export function sanitizeUrl(raw: string): string {
  if (!raw) return "";
  try {
    const u = new URL(raw);
    return (u.origin + u.pathname).slice(0, 300);
  } catch {
    // URL 파싱 실패 시 ? # 이후 제거
    return raw.split(/[?#]/)[0].slice(0, 300);
  }
}

// 경로: query/hash 제거.
export function sanitizePath(raw: string): string {
  if (!raw) return "/";
  return raw.split(/[?#]/)[0].slice(0, 200);
}

// referrer: 호스트명만 저장(전체 referrer URL 미저장).
export function sanitizeReferrer(raw: string): string {
  if (!raw) return "";
  try {
    return new URL(raw).hostname.slice(0, 120);
  } catch {
    return "";
  }
}

// 클릭 라벨: 마스킹 + 길이 제한.
export function sanitizeLabel(raw: unknown): string | null {
  if (typeof raw !== "string" || !raw) return null;
  return maskPII(raw).slice(0, 80);
}

// meta: 민감 키 차단 + 값 마스킹 + allowlist. 기본은 dir(제스처 방향)만 허용.
// dir: 스와이프 방향. fixed: 팝업 등 화면 고정 레이어의 클릭(문서 좌표가 없어 히트맵에서 제외됨)
const META_KEY_ALLOW = new Set(["dir", "fixed"]);
const META_KEY_BLOCK = /pass|pwd|email|mail|phone|tel|mobile|name|addr|address|rrn|birth|ssn|card|account|token|medical|health/i;

export function sanitizeMeta(raw: unknown): string {
  if (typeof raw !== "string" || !raw) return "{}";
  let obj: Record<string, unknown>;
  try {
    obj = JSON.parse(raw);
  } catch {
    return "{}";
  }
  if (!obj || typeof obj !== "object") return "{}";
  const safe: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj)) {
    if (META_KEY_BLOCK.test(k)) continue; // 민감 키 차단
    if (!META_KEY_ALLOW.has(k)) continue; // allowlist 외 제거
    safe[k] = typeof v === "string" ? maskPII(v).slice(0, 40) : v;
  }
  return JSON.stringify(safe).slice(0, 300);
}

// 수집 요청 도메인 검증 (5.1): Origin/Referer 호스트가 등록 도메인과 일치하는지.
export function hostAllowed(reqHost: string | null, siteDomain: string): boolean {
  if (!reqHost) return true; // 헤더 부재 시 검증 불가 → 허용(잔여 리스크, 로깅 권장)
  const h = reqHost.toLowerCase();
  if (h === "localhost" || h === "127.0.0.1" || h.endsWith(".localhost")) return true; // 개발/데모
  if (!siteDomain) return true;
  const d = siteDomain
    .replace(/^https?:\/\//, "")
    .replace(/\/.*$/, "")
    .toLowerCase();
  return h === d || h.endsWith("." + d) || d.endsWith("." + h);
}

export function hostFromHeaders(origin: string | null, referer: string | null): string | null {
  const src = origin || referer;
  if (!src) return null;
  try {
    return new URL(src).hostname;
  } catch {
    return null;
  }
}
