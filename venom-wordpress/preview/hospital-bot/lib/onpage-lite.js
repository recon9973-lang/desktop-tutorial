'use strict';

// ============================================================
// onpage-lite — 의존성 0 온페이지 SEO 스코어러(정규식 기반)
// ------------------------------------------------------------
// seo-engine.js(+linkedom)가 최선이지만, 서버 런타임에 DOM 파서(linkedom)가
// 없을 때를 위한 폴백. HTML 문자열만 있으면 항상 채점한다.
// 반환형은 diagnose.js가 소비하는 seo-engine 결과의 부분집합과 호환:
//   { total, max, grade:{label}, summary:{passed,failed}, categories:[{key,items:[{name,points,pass}]}], renderSuspect, lite:true }
// 평가 근거: Google Search Central(title/description/H1/alt/viewport/canonical/
//   구조화데이터/HTTPS/robots/sitemap 등). 순위 보장 아님(참고용).
// ============================================================

function stripToText(html) {
  return String(html || '')
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

// 태그 문자열에서 속성값 추출 — 큰따옴표·작은따옴표·따옴표 없음 모두 지원.
function attr(tag, name) {
  const m = String(tag).match(new RegExp('\\b' + name + '\\s*=\\s*("([^"]*)"|\'([^\']*)\'|([^\\s"\'>]+))', 'i'));
  if (!m) return '';
  return (m[2] != null ? m[2] : m[3] != null ? m[3] : m[4] != null ? m[4] : '');
}

// 모든 <meta ...> 태그를 {name/property → content}로 파싱(속성 순서·따옴표 무관).
function parseMetas(html) {
  const byName = {}, byProp = {};
  const tags = String(html || '').match(/<meta\b[^>]*>/gi) || [];
  for (const tag of tags) {
    const name = attr(tag, 'name');
    const prop = attr(tag, 'property');
    const content = attr(tag, 'content');
    if (name) byName[name.toLowerCase()] = content;
    if (prop) byProp[prop.toLowerCase()] = content;
  }
  return { byName, byProp };
}

// <link ...> 태그들에서 rel 속성 목록(따옴표 무관).
function linkRels(html) {
  return (String(html || '').match(/<link\b[^>]*>/gi) || []).map((t) => attr(t, 'rel').toLowerCase());
}

function analyze(input) {
  input = input || {};
  const html = String(input.html || '');
  const robots = String(input.robots || '');
  const url = input.url || '';
  const isHttps = (typeof input.isHttps === 'boolean') ? input.isHttps : /^https:/i.test(url);
  const { byName, byProp } = parseMetas(html);
  const rels = linkRels(html);
  const text = stripToText(html);

  // title
  const titleRaw = (html.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [])[1] || '';
  const title = titleRaw.replace(/\s+/g, ' ').trim();
  const titleLen = title.length;
  const titleOk = !!title && titleLen >= 10 && titleLen <= 60;

  // meta description
  const desc = (byName.description || '').trim();
  const descOk = !!desc && desc.length >= 20 && desc.length <= 160;

  // H1
  const h1Count = (html.match(/<h1[\s>]/gi) || []).length;
  const h1Ok = h1Count === 1;

  // 이미지 alt 커버리지(추적 픽셀 제외 없이 관대하게) — alt 누락 ≤10%
  const imgs = html.match(/<img\b[^>]*>/gi) || [];
  const imgNoAlt = imgs.filter((t) => !/\balt\s*=/i.test(t)).length;
  const imgOk = imgs.length === 0 || (imgNoAlt / imgs.length) <= 0.1;

  const httpsOk = !!isHttps;
  const viewportOk = !!byName.viewport;
  const canonicalOk = rels.indexOf('canonical') >= 0;
  const noindexOk = !/noindex/i.test(byName.robots || byName.googlebot || '');
  const langOk = /<html\b[^>]*\blang\s*=/i.test(html);
  const ldOk = /<script\b[^>]*application\/ld\+json/i.test(html);
  const ogOk = !!(byProp['og:title'] && byProp['og:description']);
  const faviconOk = rels.some((r) => r.indexOf('icon') >= 0);
  const sitemapOk = /^\s*sitemap\s*:/im.test(robots);
  const robotsTxtOk = robots.trim().length > 0;
  const contentOk = text.length >= 800;

  // JS 렌더링/봇 차단 정황 — 본문 빈약 + 스크립트 다수 + 제목 없음
  const scriptCount = (html.match(/<script\b[^>]*\bsrc\s*=/gi) || []).length;
  const renderSuspect = (text.length < 150 && scriptCount >= 2 && !title && h1Count === 0);

  // 배점(합계 100) — Google 우선순위 반영(기술·핵심 콘텐츠 신호 가중)
  const items = [
    ['제목(title) 태그', 14, titleOk],
    ['메타 디스크립션', 10, descOk],
    ['H1 대표 제목', 8, h1Ok],
    ['이미지 ALT 텍스트', 8, imgOk],
    ['HTTPS 보안 연결', 10, httpsOk],
    ['Viewport(모바일)', 8, viewportOk],
    ['Canonical 태그', 6, canonicalOk],
    ['인덱싱 허용', 8, noindexOk],
    ['HTML lang 속성', 4, langOk],
    ['구조화 데이터', 8, ldOk],
    ['Open Graph 태그', 4, ogOk],
    ['파비콘', 3, faviconOk],
    ['sitemap.xml 선언', 4, sitemapOk],
    ['robots.txt 존재', 3, robotsTxtOk],
    ['본문 콘텐츠 분량', 2, contentOk],
  ].map((it) => ({ name: it[0], points: it[1], pass: it[2] }));

  const max = items.reduce((s, it) => s + it.points, 0);
  const total = items.reduce((s, it) => s + (it.pass ? it.points : 0), 0);
  const passed = items.filter((it) => it.pass).length;
  const failed = items.length - passed;
  const pct = max ? total / max : 0;
  const label = pct >= 0.9 ? '플래티넘' : pct >= 0.8 ? '골드' : pct >= 0.7 ? '실버' : pct >= 0.6 ? '브론즈' : '개선필요';

  return {
    lite: true,
    total, max,
    grade: { label },
    summary: { passed, failed },
    categories: [{ key: 'onpage', items }],
    renderSuspect,
  };
}

module.exports = { analyze, parseMetas, stripToText };
