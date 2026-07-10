'use strict';

// ============================================================
// cache — Upstash(Vercel KV) REST 기반 JSON 캐시(TTL)
// ------------------------------------------------------------
// KV 미설정 시 전부 no-op(캐시 없이 정상 동작). 실패해도 throw하지 않음.
// env: KV_REST_API_URL / KV_REST_API_TOKEN (또는 UPSTASH_* / *_REST_API_*)
// (api/analytics.js의 kv() 패턴과 동일 규격)
// ============================================================
const https = require('https');

function _pickEnv(reList, extraSkip) {
  for (const re of reList) {
    for (const k of Object.keys(process.env)) {
      if (extraSkip && extraSkip.test(k)) continue;
      if (re.test(k) && process.env[k]) return process.env[k];
    }
  }
  return '';
}
function kvUrl() { return _pickEnv([/(^|_)KV_REST_API_URL$/, /(^|_)UPSTASH_REDIS_REST_URL$/, /REST_API_URL$/, /REDIS_REST_URL$/]); }
function kvToken() { return _pickEnv([/(^|_)KV_REST_API_TOKEN$/, /(^|_)UPSTASH_REDIS_REST_TOKEN$/, /REST_API_TOKEN$/, /REDIS_REST_TOKEN$/], /READ_ONLY/); }

function configured() { return !!(kvUrl() && kvToken()); }

// Upstash REST 파이프라인: [["GET","k"],["SET","k","v","EX","86400"]] → [{result},...]
function kv(commands) {
  return new Promise((resolve) => {
    const URL_ = kvUrl(), TOK = kvToken();
    if (!URL_ || !TOK) return resolve(null);
    let u; try { u = new URL(URL_); } catch (e) { return resolve(null); }
    const payload = JSON.stringify(commands);
    const req = https.request({
      hostname: u.hostname,
      path: (u.pathname === '/' ? '' : u.pathname.replace(/\/$/, '')) + '/pipeline',
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + TOK, 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) },
    }, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => { let json = null; try { json = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch (e) { /* */ } resolve({ status: res.statusCode, json }); });
    });
    req.on('error', () => resolve(null));
    req.setTimeout(10000, () => { req.destroy(); resolve(null); });
    req.write(payload); req.end();
  });
}

async function getJson(key) {
  if (!configured()) return null;
  const r = await kv([['GET', key]]);
  const v = r && r.json && r.json[0] && r.json[0].result;
  if (v == null) return null;
  try { return JSON.parse(v); } catch (e) { return null; }
}

async function setJson(key, val, ttlSec) {
  if (!configured()) return false;
  const r = await kv([['SET', key, JSON.stringify(val), 'EX', String(ttlSec || 86400)]]);
  return !!(r && r.json);
}

module.exports = { configured, getJson, setJson, kv };
