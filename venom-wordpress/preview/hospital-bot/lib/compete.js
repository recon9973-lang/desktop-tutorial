'use strict';

// ============================================================
// compete — 경쟁사 비교(P2) "동네 순위표"
// ------------------------------------------------------------
// 같은 지역·진료과 병원들을 로컬 노출(블로그·뉴스) + GEO 언급으로 비교.
// 비용 격리: 풀 6대 진단을 N번 돌리지 않고, 값싼 신호만 병렬 수집.
//   후보 = 네이버 로컬 검색 상위 + (있으면) GEO가 대신 추천한 경쟁 병원.
// 원칙: 없는 수치는 지어내지 않음. 후보 부족 시 status 'insufficient'.
// ============================================================

const gp = require('./geo-probe'); // brandToken 재사용

function normalize(s) { return String(s || '').replace(/[^가-힣A-Za-z0-9]/g, '').toLowerCase(); }

function isSameClinic(a, b, region) {
  if (!a || !b) return false;
  if (normalize(a) === normalize(b)) return true;
  const ba = gp.brandToken(a, region), bb = gp.brandToken(b, region);
  if (ba && bb && ba.length >= 2 && (ba === bb)) return true;
  return false;
}

async function compareCompetitors(targetName, { region = '', dept = '', deps, existingCompetitors = [], max = 3 } = {}) {
  const no = deps && deps.naverOpenapi;
  if (!no) return { status: 'error', error: 'naverOpenapi 의존성 없음', rows: [] };

  // 1) 후보 수집: 로컬 검색 상위 + GEO 추천 경쟁
  const q = [region, dept].filter(Boolean).join(' ') || dept || targetName;
  const candidates = [];
  try {
    const local = await no.searchJson('local', q, { display: 5 });
    if (local && local.ok) local.items.forEach((it) => candidates.push(no.stripTags(it.title)));
  } catch (e) { /* degrade */ }
  (existingCompetitors || []).forEach((c) => { if (c && c.name) candidates.push(c.name); });

  // 2) dedup + 타깃 제외
  const seen = new Set();
  const names = [];
  candidates.forEach((n) => {
    const key = normalize(n);
    if (!key || seen.has(key)) return;
    if (isSameClinic(n, targetName, region)) return; // 타깃 본인 제외
    seen.add(key);
    names.push(n);
  });
  const competitors = names.slice(0, max);

  if (!competitors.length) {
    return { status: 'insufficient', rows: [], targetRank: null, total: 0, region, dept,
      note: '같은 지역·진료과 경쟁 병원을 충분히 찾지 못했습니다.' };
  }

  // 3) 타깃 + 경쟁: 값싼 신호(블로그·뉴스) 병렬 수집
  const all = [{ name: targetName, isTarget: true }].concat(competitors.map((n) => ({ name: n, isTarget: false })));
  const rows = await Promise.all(all.map(async (c) => {
    let blog = null, news = null;
    try { const b = await no.searchJson('blog', c.name, { display: 1 }); if (b && b.ok) blog = b.total; } catch (e) { /* */ }
    try { const n2 = await no.searchJson('news', c.name, { display: 1 }); if (n2 && n2.ok) news = n2.total; } catch (e) { /* */ }
    let geoMentions = null;
    const gc = (existingCompetitors || []).find((x) => isSameClinic(x.name, c.name, region));
    if (gc && gc.mentions != null) geoMentions = gc.mentions;
    return { name: c.name, isTarget: c.isTarget, blog, news, geoMentions };
  }));

  // 4) 점수·순위 (로컬 노출 + GEO 언급 가중)
  rows.forEach((r) => { r.score = (r.blog || 0) + (r.news || 0) * 3 + (r.geoMentions || 0) * 20; });
  rows.sort((a, b) => b.score - a.score);
  rows.forEach((r, i) => { r.rank = i + 1; });
  const targetRank = (rows.find((r) => r.isTarget) || {}).rank || null;

  return {
    status: 'ok', rows, targetRank, total: rows.length, region, dept,
    note: '네이버 로컬 노출(블로그·뉴스)' + (rows.some((r) => r.geoMentions != null) ? ' + AI 언급' : '') + ' 기준 동네 비교(참고용).',
  };
}

module.exports = { compareCompetitors, isSameClinic, normalize };
