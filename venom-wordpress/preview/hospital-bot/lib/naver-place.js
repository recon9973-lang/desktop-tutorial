'use strict';

// ============================================================
// naver-place — 네이버 플레이스 상세에서 '실제 홈페이지' best-effort 탐색
// ------------------------------------------------------------
// 배경: 네이버 검색 OpenAPI(local)는 링크를 1개만 준다. 플레이스에 블로그가 맨 위면
//       블로그가 대표로 와서 정식 홈페이지를 못 받는다. 플레이스 상세페이지(pcmap)는
//       여러 링크를 담지만 공식 API가 없어 스크래핑해야 한다(불안정 → best-effort).
// 원칙: 실패해도 절대 throw 안 함(null 반환). 짧은 타임아웃. blog-only일 때만 호출(희소·캐시).
// 반환: 정식 홈페이지 URL(string) | null.
// ============================================================

// 홈페이지가 '아닌' 호스트(블로그·SNS·네이버 내부·검색엔진·디렉토리·정적 CDN 등)
const NON_SITE_HOST = /(^|\.)(naver\.com|naver\.net|pstatic\.net|blog\.me|instagram\.com|facebook\.com|fb\.com|youtube\.com|youtu\.be|band\.us|kakao\.com|kakaocdn\.net|daum\.net|tistory\.com|brunch\.co\.kr|blogspot\.com|twitter\.com|x\.com|threads\.net|tiktok\.com|google\.com|gstatic\.com|goo\.gl|apple\.com|bing\.com|microsoft\.com|msn\.com|live\.com|wikipedia\.org|wikimedia\.org|mangoplate\.com|diningcode\.com|yelp\.com|w3\.org|schema\.org)$/i;
const IMG_EXT = /\.(png|jpe?g|gif|webp|svg|ico|css|js|woff2?|ttf|mp4)(\?|$)/i;

function hostOf(url) {
  try { return new URL(url).host.toLowerCase().replace(/^www\./, ''); }
  catch (e) { return ''; }
}
function isSiteUrl(url) {
  if (!url || !/^https?:\/\//i.test(url)) return false;
  if (IMG_EXT.test(url)) return false;
  // 검색결과의 잘린 표시 URL(말줄임·공백·따옴표 등) 거부 — "https://…" 같은 쓰레기값 차단
  if (/[……\s"'<>()]/.test(url)) return false;
  const h = hostOf(url);
  // 유효한 도메인만: 영숫자·하이픈·점 + 2자 이상 TLD, 연속점(..) 없음(잘린 호스트 방지)
  if (!h || /\.\./.test(h) || !/^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$/i.test(h)) return false;
  return !NON_SITE_HOST.test(h);
}

// 상세 HTML/JSON 문자열에서 홈페이지 후보 추출.
//  1순위: "homepage"/"url"/"홈페이지" 키 근처의 URL(구조화 신호)
//  2순위: 문서 내 첫 외부 사이트 URL(네이버·블로그·SNS·이미지 제외)
function cleanUrl(raw) {
  return String(raw || '')
    .replace(/[)\]}>,.]+$/, '') // 문장부호 꼬리 제거
    .replace(/\/$/, '');        // 끝 슬래시 정규화
}
function extractHomepage(text) {
  // JSON 상태의 escaped slash(\/)를 먼저 복원해 URL이 중간에 잘리지 않게 한다.
  const s = String(text || '').replace(/\\\//g, '/');
  // 1순위: "homepage"/"url"/"website" 키의 URL(구조화 신호)
  const keyed = s.match(/"(?:homepage|homePage|home_page|url|website|siteUrl|link)"\s*:\s*"(https?:\/\/[^"\\]+)"/gi) || [];
  for (const m of keyed) {
    const url = cleanUrl((m.match(/"(https?:\/\/[^"\\]+)"/) || [])[1]);
    if (isSiteUrl(url)) return url;
  }
  // 2순위(폴백): 전체에서 외부 사이트 URL 첫 번째(네이버·블로그·SNS·이미지 제외)
  const all = s.match(/https?:\/\/[^"'\s\\)<>]+/g) || [];
  for (const raw of all) {
    const url = cleanUrl(raw);
    if (isSiteUrl(url)) return url;
  }
  return null;
}

// 플레이스 목록 HTML에서 첫 place id 추출
function extractPlaceId(text) {
  const s = String(text || '');
  const m = s.match(/\/(?:place|restaurant|hairshop|hospital|place)\/(\d{6,})/) ||
            s.match(/"id"\s*:\s*"(\d{6,})"/) ||
            s.match(/place(?:Id)?["':\s]+(\d{6,})/i);
  return m ? m[1] : '';
}

// 네트워크 탐색(best-effort). deps.fetchHtml 주입(원본 HTML 반환).
async function resolveHomepage(name, opts) {
  opts = opts || {};
  const deps = opts.deps || {};
  const fetchHtml = deps.fetchHtml;
  if (typeof fetchHtml !== 'function' || !name) return null;
  const q = [opts.region, name].filter(Boolean).join(' ').trim() || name;
  const enc = encodeURIComponent(q);
  const H = { timeout: 2500, maxBytes: 1200000 }; // 동기 응답(5초) 안에 들도록 짧게
  try {
    // 1) 목록 검색 → 홈페이지가 있으면 즉시, 없으면 place id
    const list = await fetchHtml(`https://pcmap.place.naver.com/place/list?query=${enc}`, H);
    const listHtml = (list && list.ok && list.html) || '';
    const direct = extractHomepage(listHtml);
    if (direct) return direct;
    const id = extractPlaceId(listHtml);
    if (!id) return null;
    // 2) 상세(home 탭) 1회만 — 지연 최소화
    const detail = await fetchHtml(`https://pcmap.place.naver.com/place/${id}/home`, H);
    return extractHomepage((detail && detail.ok && detail.html) || '');
  } catch (e) { return null; }
}

// 검색엔진 폴백(best-effort): 상호+지역+'홈페이지'로 검색해 첫 외부 사이트 추출.
// 검색·디렉토리·SNS는 제외되므로 대개 공식 홈페이지가 첫 후보. 잘못 잡힐 수 있어 '추정'으로 취급.
async function searchHomepage(name, opts) {
  opts = opts || {};
  const deps = opts.deps || {};
  const fetchHtml = deps.fetchHtml;
  if (typeof fetchHtml !== 'function' || !name) return null;
  const q = [opts.region, name, '홈페이지'].filter(Boolean).join(' ');
  const enc = encodeURIComponent(q);
  const H = { timeout: 2500, maxBytes: 1200000 };
  // Bing이 서버측 스크래핑에 비교적 관대. 지연 최소화 위해 1개 엔진만.
  try {
    const r = await fetchHtml(`https://www.bing.com/search?q=${enc}`, H);
    return extractHomepage((r && r.ok && r.html) || '');
  } catch (e) { return null; }
}

// 통합: 플레이스 상세 → 검색엔진 순으로 실제 홈페이지 best-effort 탐색.
async function findHomepage(name, opts) {
  const viaPlace = await resolveHomepage(name, opts).catch(() => null);
  if (viaPlace) return { url: viaPlace, source: 'naver-place' };
  const viaSearch = await searchHomepage(name, opts).catch(() => null);
  if (viaSearch) return { url: viaSearch, source: 'search' };
  return null;
}

module.exports = { findHomepage, resolveHomepage, searchHomepage, extractHomepage, extractPlaceId, isSiteUrl, hostOf };
