'use strict';

// ─────────────────────────────────────────────────────────────────────────
// VENOM GEO-OS · AEO 인용(citation) 판정 단일 소스
//   문제: 기존 판정은 "citation URL 문자열에 한글 core 키워드 포함"이었다.
//         실제 출처 URL은 blog.naver.com/xxx/223…, place.map.kakao.com/… 처럼
//         한글 상호를 담지 않아 cited가 구조적으로 성립하지 않았다(실측 40셀 중 cited 0건).
//   개선: ① 자사 출처(홈페이지·블로그·플레이스)를 호스트+경로로 매칭
//         ② 퍼센트 인코딩된 한글 URL을 디코드한 뒤 core 키워드 매칭(네이버 검색형 URL 대응)
//   모두 순수 함수 → 오프라인 단위 테스트.
// ─────────────────────────────────────────────────────────────────────────

function norm(s) { return String(s || '').replace(/\s+/g, '').toLowerCase(); }

// 퍼센트 인코딩된 URL을 최대한 사람이 읽는 형태로. 실패 시 원문.
function decodeUrl(u) {
  const s = String(u || '');
  try { return decodeURIComponent(s); } catch (e) { return s; }
}

// URL/도메인 문자열 → 비교 키 "호스트+경로"(소문자, www·끝슬래시 제거). 실패 시 ''
//   blog.naver.com 처럼 공용 호스트에 자사 블로그가 얹히는 경우가 많아
//   호스트만이 아니라 경로까지 포함해 비교해야 오탐이 없다.
function urlKey(u) {
  let s = String(u || '').trim();
  if (!s) return '';
  if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(s)) s = 'https://' + s;
  try {
    const x = new URL(s);
    const host = x.hostname.toLowerCase().replace(/^www\./, '');
    const p = decodeUrl(x.pathname || '').toLowerCase().replace(/\/+$/, '');
    return host + p;
  } catch (e) { return ''; }
}

// 거래처 설정(websiteUrl + citationDomains[]) → 판정용 출처 키 목록
function siteDomains(client) {
  client = client || {};
  const raw = [].concat(client.websiteUrl || [], client.citationDomains || []);
  const out = [];
  raw.forEach((v) => { const k = urlKey(v); if (k && out.indexOf(k) < 0) out.push(k); });
  return out;
}

// 출처 URL이 등록된 자사 출처에 속하는가 (경계 검사로 /abc2 가 /abc 에 걸리지 않게)
function domainMatch(url, domains) {
  const k = urlKey(url);
  if (!k) return false;
  return (domains || []).some((d) => {
    if (!d) return false;
    if (k === d) return true;
    if (k.indexOf(d) !== 0) return false;
    const rest = k.slice(d.length);
    return rest.charAt(0) === '/' || rest.charAt(0) === '?';
  });
}

// 디코드한 URL에 core 키워드가 들어있는가 (네이버 검색형 URL 등)
function coreInUrl(url, cores) {
  const t = norm(decodeUrl(url));
  if (!t) return false;
  return (cores || []).some((c) => c && t.includes(norm(c)));
}

function isCited(url, domains, cores) {
  return domainMatch(url, domains) || coreInUrl(url, cores);
}

// 인용 목록에서 첫 매칭 URL 반환(근거 표기용). 없으면 null.
function citedBy(citations, domains, cores) {
  const hit = (citations || []).filter((u) => isCited(u, domains, cores));
  return hit.length ? hit[0] : null;
}

module.exports = { norm, decodeUrl, urlKey, siteDomains, domainMatch, coreInUrl, isCited, citedBy };
