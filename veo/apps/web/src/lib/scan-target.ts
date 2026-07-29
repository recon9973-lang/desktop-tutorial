/**
 * 입력된 주소를 진단에 쓸 수 있는 형태로 정리한다.
 *
 * 사람은 `koreahospital.com` 이라고 친다. 스킴을 요구하면 그 자체가 장벽이 되고,
 * "왜 안 되는지" 를 설명해야 하는 화면이 하나 더 생긴다. 그래서 붙여 준다.
 *
 * 여기서 거절하는 것은 **친절**이지 방어가 아니다. 진짜 SSRF 방어는 서버의 `UrlGuard`
 * 이고, 그쪽은 DNS 를 실제로 풀어 본다. 화면 검사만 믿고 서버 검사를 빼면, API 를
 * 직접 부르는 경로가 그대로 열린다.
 */

/** 명백히 내부를 가리키는 호스트. 오타로 여기 닿는 사람에게 즉시 알려 주기 위한 것. */
const OBVIOUSLY_INTERNAL =
  /^(localhost|127\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.|\[?::1\]?$|0\.0\.0\.0)/i;

export function normalizeScanTarget(typed: string): string | null {
  const trimmed = typed.trim();
  if (trimmed === '') {
    return null;
  }

  // 스킴이 없으면 https 로 읽는다. `//example.com` 같은 형태도 여기서 흡수된다.
  const withScheme = /^[a-z][a-z0-9+.-]*:/i.test(trimmed) ? trimmed : `https://${trimmed}`;

  let url: URL;
  try {
    url = new URL(withScheme);
  } catch {
    return null;
  }

  if (url.protocol !== 'https:' && url.protocol !== 'http:') {
    return null;
  }
  if (url.hostname === '' || OBVIOUSLY_INTERNAL.test(url.hostname)) {
    return null;
  }
  // 점이 없는 호스트는 사내 이름이거나 오타다. 공개된 사이트를 진단하는 도구이므로
  // 여기서 잡아 주는 편이 "알 수 없는 오류" 보다 낫다.
  if (!url.hostname.includes('.')) {
    return null;
  }

  // URL 이 한글 도메인을 punycode 로, 호스트를 소문자로 이미 정규화해 준다.
  // 경로·질의는 건드리지 않는다 — 특정 페이지를 보려는 의도를 지우면 안 된다.
  return url.toString().replace(/\/$/, url.pathname === '/' && !trimmed.endsWith('/') ? '' : '$&');
}
