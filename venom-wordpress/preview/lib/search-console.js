'use strict';

// ─────────────────────────────────────────────────────────────────────────
// VENOM GrowthOps · M3+ Google Search Console (Search Analytics) 실측 연동
// ─────────────────────────────────────────────────────────────────────────
// 서비스계정(JWT RS256)으로 OAuth 토큰을 받아 검색 성과(클릭·노출·CTR·순위)를
// 조회한다. 외부 의존성 없음(Node crypto). 자격증명 미설정/실패 시 throw 없이
// { ok:false, reason } 로 안전 반환(PSI와 동일 정책).
//
// 필요한 env (둘 중 하나):
//   1) GSC_SERVICE_ACCOUNT_JSON = 서비스계정 키 JSON 전체
//   2) GSC_CLIENT_EMAIL + GSC_PRIVATE_KEY  (PEM, \n 이스케이프 허용)
//   + GSC_SITE_URL = 등록된 속성 (예: "https://example.com/" 또는 "sc-domain:example.com")
// 서비스계정 이메일을 Search Console 속성에 "전체/제한 사용자"로 추가해야 한다.
// ─────────────────────────────────────────────────────────────────────────

const https = require('https');
const crypto = require('crypto');

const TOKEN_HOST = 'oauth2.googleapis.com';
const GSC_HOST = 'searchconsole.googleapis.com';
const SCOPE = 'https://www.googleapis.com/auth/webmasters.readonly';

function b64url(buf) {
  return Buffer.from(buf).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/** env → { clientEmail, privateKey, siteUrl } | null (순수). */
function loadConfig(env) {
  const e = env || process.env;
  let clientEmail = e.GSC_CLIENT_EMAIL;
  let privateKey = e.GSC_PRIVATE_KEY;
  if (e.GSC_SERVICE_ACCOUNT_JSON) {
    try {
      const j = JSON.parse(e.GSC_SERVICE_ACCOUNT_JSON);
      clientEmail = clientEmail || j.client_email;
      privateKey = privateKey || j.private_key;
    } catch { /* 무시 */ }
  }
  const siteUrl = e.GSC_SITE_URL || e.SITE_URL || '';
  if (!clientEmail || !privateKey || !siteUrl) return null;
  // env에 \n 이 이스케이프되어 들어온 경우 복원
  privateKey = String(privateKey).replace(/\\n/g, '\n');
  return { clientEmail, privateKey, siteUrl };
}

/** JWT 클레임 생성(순수). now=초 단위. */
function buildJwtClaims(clientEmail, now, scope) {
  const iat = Math.floor(now);
  return {
    iss: clientEmail,
    scope: scope || SCOPE,
    aud: `https://${TOKEN_HOST}/token`,
    iat,
    exp: iat + 3600,
  };
}

/** 서명된 JWT 문자열 생성(RS256). */
function signJwt(claims, privateKey) {
  const header = { alg: 'RS256', typ: 'JWT' };
  const signingInput = b64url(JSON.stringify(header)) + '.' + b64url(JSON.stringify(claims));
  const sig = crypto.sign('RSA-SHA256', Buffer.from(signingInput), privateKey);
  return signingInput + '.' + b64url(sig);
}

function httpPost(host, path, headers, bodyStr, timeout) {
  return new Promise((resolve) => {
    const opts = { hostname: host, path, method: 'POST', headers: Object.assign({ 'Content-Length': Buffer.byteLength(bodyStr) }, headers) };
    const req = https.request(opts, (r) => {
      const chunks = [];
      r.on('data', (c) => chunks.push(c));
      r.on('end', () => {
        const text = Buffer.concat(chunks).toString('utf8');
        let json = null; try { json = JSON.parse(text); } catch {}
        resolve({ status: r.statusCode, json, text });
      });
    });
    req.on('error', (e) => resolve({ status: 0, error: e.message }));
    req.setTimeout(timeout || 20000, () => { req.destroy(); resolve({ status: 0, error: 'timeout' }); });
    req.write(bodyStr); req.end();
  });
}

/** 액세스 토큰 발급. now 주입 가능(테스트). */
async function getAccessToken(cfg, now) {
  const claims = buildJwtClaims(cfg.clientEmail, now == null ? Date.now() / 1000 : now);
  let assertion;
  try { assertion = signJwt(claims, cfg.privateKey); }
  catch (e) { return { ok: false, reason: 'JWT 서명 실패: ' + e.message }; }
  const body = 'grant_type=' + encodeURIComponent('urn:ietf:params:oauth:grant-type:jwt-bearer') + '&assertion=' + encodeURIComponent(assertion);
  const r = await httpPost(TOKEN_HOST, '/token', { 'Content-Type': 'application/x-www-form-urlencoded' }, body);
  if (r.status === 200 && r.json && r.json.access_token) return { ok: true, token: r.json.access_token };
  return { ok: false, reason: 'token 발급 실패: ' + (r.error || (r.json && r.json.error_description) || r.status) };
}

/** Search Analytics 응답 파싱(순수). */
function parseSearchAnalytics(json) {
  const rows = (json && json.rows) || [];
  const out = rows.map((r) => ({
    keys: r.keys || [],
    clicks: r.clicks || 0,
    impressions: r.impressions || 0,
    ctr: r.ctr || 0,
    position: r.position || 0,
  }));
  const totals = out.reduce((a, r) => ({ clicks: a.clicks + r.clicks, impressions: a.impressions + r.impressions }), { clicks: 0, impressions: 0 });
  totals.ctr = totals.impressions ? totals.clicks / totals.impressions : 0;
  return { rows: out, totals };
}

/** Search Analytics 쿼리. dimensions 예: ['query'] | ['page'] | []. */
async function querySearchAnalytics(opts) {
  const cfg = loadConfig(opts && opts.env);
  if (!cfg) return { ok: false, reason: 'GSC 자격증명 미설정' };
  const tok = await getAccessToken(cfg, opts && opts.now);
  if (!tok.ok) return tok;

  const payload = JSON.stringify({
    startDate: opts.startDate,
    endDate: opts.endDate,
    dimensions: opts.dimensions || [],
    rowLimit: opts.rowLimit || 25,
  });
  const path = `/webmasters/v3/sites/${encodeURIComponent(cfg.siteUrl)}/searchAnalytics/query`;
  const r = await httpPost(GSC_HOST, path, { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + tok.token }, payload);
  if (r.status !== 200) return { ok: false, reason: 'GSC 쿼리 실패: ' + (r.error || (r.json && r.json.error && r.json.error.message) || r.status) };
  return Object.assign({ ok: true, siteUrl: cfg.siteUrl }, parseSearchAnalytics(r.json));
}

function isConfigured(env) { return !!loadConfig(env); }

module.exports = {
  loadConfig, buildJwtClaims, signJwt, parseSearchAnalytics, getAccessToken, querySearchAnalytics, isConfigured,
  _const: { SCOPE, TOKEN_HOST, GSC_HOST },
};
