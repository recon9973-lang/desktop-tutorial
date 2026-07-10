'use strict';

// ============================================================
// naver-openapi — 네이버 검색 OpenAPI(로컬/블로그/뉴스) 최소 래퍼
// ------------------------------------------------------------
// 베노미 병원 탐지·로컬 진단용. 검색광고 API(lib/naver-searchad)와는 별개 인증.
// 필요 env: NAVER_CLIENT_ID, NAVER_CLIENT_SECRET  (api/insights.js와 동일)
// 모든 호출은 짧은 타임아웃 + 실패해도 throw하지 않고 {ok:false} 반환(비파괴).
// ============================================================
const https = require('https');

function creds() {
  return {
    id: (process.env.NAVER_CLIENT_ID || '').trim(),
    secret: (process.env.NAVER_CLIENT_SECRET || '').trim(),
  };
}
function isConfigured() {
  const c = creds();
  return !!(c.id && c.secret);
}

function stripTags(s) {
  return String(s || '').replace(/<\/?b>/g, '').replace(/<[^>]+>/g, '').trim();
}

// GET https://openapi.naver.com/v1/search/<kind>.json?...
function searchJson(kind, query, { display = 5, sort = 'random', timeout = 7000 } = {}) {
  return new Promise((resolve) => {
    const c = creds();
    if (!c.id || !c.secret) {
      return resolve({ ok: false, configured: false, error: 'NAVER_CLIENT_ID/SECRET 미설정', items: [], total: 0 });
    }
    const q = encodeURIComponent(String(query || '').trim());
    const path = `/v1/search/${kind}.json?query=${q}&display=${display}&sort=${sort}`;
    const req = https.get(
      { hostname: 'openapi.naver.com', path, method: 'GET',
        headers: { 'X-Naver-Client-Id': c.id, 'X-Naver-Client-Secret': c.secret } },
      (res) => {
        const chunks = [];
        res.on('data', (d) => chunks.push(d));
        res.on('end', () => {
          let json = null;
          try { json = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch (e) { /* null */ }
          if (res.statusCode !== 200 || !json) {
            return resolve({ ok: false, configured: true, status: res.statusCode,
              error: (json && json.errorMessage) || ('HTTP ' + res.statusCode), items: [], total: 0 });
          }
          resolve({ ok: true, configured: true, status: 200,
            total: json.total || 0, items: Array.isArray(json.items) ? json.items : [] });
        });
      }
    );
    req.on('error', (e) => resolve({ ok: false, configured: true, error: e.message, items: [], total: 0 }));
    req.setTimeout(timeout, () => { req.destroy(); resolve({ ok: false, configured: true, error: 'timeout', items: [], total: 0 }); });
  });
}

// 병원 탐지: local 검색 상위 1건을 정규화해서 반환
async function findHospital(query, opts) {
  const r = await searchJson('local', query, Object.assign({ display: 5, sort: 'random' }, opts));
  if (!r.ok || !r.items.length) return { found: false, source: 'naver-local', error: r.error || '검색 결과 없음', raw: r };
  const it = r.items[0];
  return {
    found: true,
    source: 'naver-local',
    name: stripTags(it.title),
    category: it.category || '',
    telephone: it.telephone || '',
    address: it.roadAddress || it.address || '',
    homepage: (it.link || '').trim() || null,   // 공식 홈페이지 후보(없을 수 있음)
    mapx: it.mapx || null,
    mapy: it.mapy || null,
    candidates: r.items.slice(0, 5).map((x) => ({ name: stripTags(x.title), category: x.category, address: x.roadAddress || x.address })),
  };
}

module.exports = { creds, isConfigured, stripTags, searchJson, findHospital };
