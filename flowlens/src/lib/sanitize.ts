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
// ⚠️ fail-CLOSED: 헤더가 없거나 이상하면 거부한다.
//   과거엔 헤더 부재 시 통과(fail-open)였는데, 브라우저가 아닌 클라이언트(curl 등)는 Origin/Referer를
//   생략할 수 있어 검증이 통째로 무력화됐다(보안감사 HIGH). 정상 추적 스크립트는 브라우저에서 돌아
//   Origin이 항상 붙으므로 진짜 방문자 수집에는 영향이 없다.
export function hostAllowed(reqHost: string | null, siteDomain: string): boolean {
  if (!reqHost) return false; // 헤더 부재·파싱실패 → 거부
  const h = reqHost.toLowerCase();
  if (h === "localhost" || h === "127.0.0.1" || h.endsWith(".localhost")) return true; // 개발/데모
  if (!siteDomain) return false; // 등록 도메인이 없으면 검증 불가 → 거부
  const d = siteDomain
    .replace(/^https?:\/\//, "")
    .replace(/\/.*$/, "")
    .toLowerCase();
  if (!d) return false;
  // h가 d 이거나 d의 하위 서브도메인일 때만 허용.
  // 과거의 `d.endsWith("."+h)`(역방향)은 등록도메인이 요청호스트의 하위일 때도 통과시켜
  // "com" 같은 값으로 우회가 됐다(보안감사). 제거한다.
  return h === d || h.endsWith("." + d);
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
