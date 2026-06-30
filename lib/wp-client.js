'use strict';

// WordPress 공식 REST API로 글을 "임시저장(draft)" 또는 발행한다.
// 인증: Application Password(워드프레스 5.6+ 기본 기능) — 사용자:앱비밀번호 Basic 인증.
// 자동 임시저장은 워드프레스 공식 기능이라 약관 위반이 아니다(내 소유 사이트).
const https = require('https');
const http = require('http');

function postJSON(urlStr, headers, bodyObj) {
  return new Promise((resolve) => {
    let u;
    try { u = new URL(urlStr); } catch (e) { return resolve({ status: 0, error: '잘못된 사이트 URL' }); }
    const mod = u.protocol === 'http:' ? http : https;
    const body = JSON.stringify(bodyObj);
    const req = mod.request({
      hostname: u.hostname,
      port: u.port || (u.protocol === 'http:' ? 80 : 443),
      path: u.pathname + u.search,
      method: 'POST',
      headers: Object.assign({
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
        'User-Agent': 'manuscript-studio/1.0',
      }, headers),
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => resolve({ status: res.statusCode, body: Buffer.concat(chunks).toString('utf8') }));
    });
    req.on('error', e => resolve({ status: 0, error: e.message }));
    req.setTimeout(30000, () => { req.destroy(); resolve({ status: 0, error: '타임아웃(30초)' }); });
    req.write(body);
    req.end();
  });
}

/**
 * 워드프레스에 글을 만든다(기본: 임시저장 draft).
 * @returns {ok, id, link, editLink, status} | {ok:false, error}
 */
async function createWpDraft({ siteUrl, user, appPassword, title, html, excerpt = '', status = 'draft' }) {
  if (!siteUrl || !user || !appPassword) return { ok: false, error: 'siteUrl·user·appPassword(앱 비밀번호) 필수' };
  if (!title || !html) return { ok: false, error: 'title·content 필수' };

  const base = String(siteUrl).trim().replace(/\/+$/, '');
  const endpoint = base + '/wp-json/wp/v2/posts';
  // 앱 비밀번호는 "xxxx xxxx xxxx" 형태로 복사되는 경우가 많음 → 공백 제거
  const auth = 'Basic ' + Buffer.from(`${user}:${String(appPassword).replace(/\s+/g, '')}`).toString('base64');
  const wpStatus = status === 'publish' ? 'publish' : 'draft';

  const r = await postJSON(endpoint, { Authorization: auth }, { title, content: html, excerpt, status: wpStatus });

  if (r.status === 201 || r.status === 200) {
    try {
      const j = JSON.parse(r.body);
      return { ok: true, id: j.id, link: j.link, status: j.status, editLink: `${base}/wp-admin/post.php?post=${j.id}&action=edit` };
    } catch (e) { return { ok: false, error: '응답 파싱 실패' }; }
  }

  let msg = `HTTP ${r.status}`;
  if (r.error) { msg += ' ' + r.error; }
  else { try { const j = JSON.parse(r.body); if (j.message) msg += ' — ' + String(j.message).replace(/<[^>]+>/g, ''); if (j.code) msg += ` (${j.code})`; } catch (e) {} }
  if (r.status === 401 || r.status === 403) msg += ' · 사용자명/Application Password를 확인하세요';
  if (r.status === 404) msg += ' · 사이트 URL 또는 REST API(/wp-json) 경로를 확인하세요';
  return { ok: false, error: msg };
}

module.exports = { createWpDraft };
