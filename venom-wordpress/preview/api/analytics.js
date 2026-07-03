'use strict';

// 자체 방문자 분석 — Vercel KV(Upstash Redis) 기반. 외부 의존성 없이 REST API 직접 호출.
//  - POST /api/analytics  {path, ref, nv}  → 페이지뷰 1건 집계(공개 사이트가 비콘 전송)
//  - GET  /api/analytics                    → 관리자 대시보드용 집계(일별·채널별·총계) 반환
// 필요 env: KV_REST_API_URL, KV_REST_API_TOKEN (Vercel KV 또는 Upstash 무료 연동 시 자동 주입)
// env 미설정이면 configured:false 로 응답 → 관리자/공개 사이트 모두 안전하게 '연동 대기' 처리.

const https = require('https');

const KV_URL   = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
const KV_TOKEN = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;

const CHANNELS = ['direct', 'naver', 'google', 'daum', 'instagram', 'facebook', 'youtube', 'bing', 'other'];
const DAY_TTL = 60 * 60 * 24 * 120; // 일별 키 120일 보관

// SEO 점수 리더보드 공개 방식: 'full'(그대로) | 'mask'(일부 가림) | 'curated'(노출 안 함)
// 환경변수 LB_DISCLOSURE 로 무중단 전환 가능. 기본은 프라이버시 안전한 mask.
const LB_DISCLOSURE = process.env.LB_DISCLOSURE || 'mask';
const LB_TTL = 60 * 60 * 24 * 400; // 주간/월간 키 보관(약 13개월)

// KST(한국시간) 기준 날짜 문자열 — 한국 사이트라 자정 경계를 KST로 맞춤
function ymdKST(offsetDays) {
  const ms = Date.now() + 9 * 3600 * 1000 - (offsetDays || 0) * 86400000;
  return new Date(ms).toISOString().slice(0, 10);
}

// Upstash REST 파이프라인: [["INCR","k"],["MGET","a","b"],...] → [{result},...]
function kv(commands) {
  return new Promise((resolve) => {
    if (!KV_URL || !KV_TOKEN) return resolve(null);
    let u; try { u = new URL(KV_URL); } catch { return resolve(null); }
    const payload = JSON.stringify(commands);
    const req = https.request({
      hostname: u.hostname,
      path: (u.pathname === '/' ? '' : u.pathname.replace(/\/$/, '')) + '/pipeline',
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + KV_TOKEN,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload),
      },
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        let json = null; try { json = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch {}
        resolve({ status: res.statusCode, json });
      });
    });
    req.on('error', () => resolve(null));
    req.setTimeout(15000, () => { req.destroy(); resolve(null); });
    req.write(payload); req.end();
  });
}

function channelOf(ref, selfHost) {
  if (!ref) return 'direct';
  let h; try { h = new URL(ref).hostname.replace(/^www\./, ''); } catch { return 'direct'; }
  if (selfHost && h === String(selfHost).replace(/^www\./, '')) return 'direct';
  if (/naver\./.test(h)) return 'naver';
  if (/google\./.test(h)) return 'google';
  if (/(daum\.|kakao)/.test(h)) return 'daum';
  if (/instagram/.test(h)) return 'instagram';
  if (/(facebook|fb\.com)/.test(h)) return 'facebook';
  if (/(youtube|youtu\.be)/.test(h)) return 'youtube';
  if (/bing\./.test(h)) return 'bing';
  return 'other';
}

function n(v) { const x = parseInt(v, 10); return isNaN(x) ? 0 : x; }
function sum(arr) { return arr.reduce((a, b) => a + n(b), 0); }

// ── SEO 점수 리더보드 ──────────────────────────────────────────
function ymKST() { return ymdKST(0).slice(0, 7); } // YYYY-MM (KST)
function hourKST() { return new Date(Date.now() + 9 * 3600 * 1000).getUTCHours(); } // 0-23 (KST)
function deviceOf(ua) { ua = String(ua || ''); if (/ipad|tablet/i.test(ua)) return 'tablet'; if (/mobile|android|iphone|ipod/i.test(ua)) return 'mobile'; return 'desktop'; }
function isoWeekKST() {
  const d = new Date(Date.now() + 9 * 3600 * 1000);
  d.setUTCHours(0, 0, 0, 0);
  const day = (d.getUTCDay() + 6) % 7;            // 월=0
  d.setUTCDate(d.getUTCDate() - day + 3);          // 해당 주 목요일
  const firstThu = new Date(Date.UTC(d.getUTCFullYear(), 0, 4));
  const week = 1 + Math.round(((d - firstThu) / 86400000 - 3 + ((firstThu.getUTCDay() + 6) % 7)) / 7);
  return d.getUTCFullYear() + '-W' + ('0' + week).slice(-2);
}
function cleanDomain(s) {
  let h = String(s || '').trim().toLowerCase();
  h = h.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0].split('?')[0].split(':')[0];
  if (!/^[a-z0-9.-]+\.[a-z]{2,}$/.test(h) || h.length > 80) return '';
  return h;
}
function maskDomain(h) { // aiops.ai.kr → ai***.kr
  const parts = h.split('.');
  const head = parts[0] || '';
  return head.slice(0, 2) + '***.' + parts.slice(-1)[0];
}
function lbKey(period) {
  return period === 'week' ? 'seo:lb:' + isoWeekKST()
    : period === 'month' ? 'seo:lb:' + ymKST() : 'seo:lb:all';
}

async function recordScore(req, res) {
  const b = req.body || {};
  const domain = cleanDomain(b.domain);
  const score = Math.max(0, Math.min(100, n(b.score)));
  if (!domain || !score) return res.status(200).json({ ok: false, reason: 'invalid' });
  if (!KV_URL || !KV_TOKEN) return res.status(200).json({ ok: false, configured: false });
  const wk = lbKey('week'), mo = lbKey('month');
  await kv([
    ['ZADD', 'seo:lb:all', 'GT', score, domain],
    ['ZADD', mo, 'GT', score, domain], ['EXPIRE', mo, LB_TTL],
    ['ZADD', wk, 'GT', score, domain], ['EXPIRE', wk, LB_TTL],
  ]);
  return res.status(200).json({ ok: true });
}

async function topScores(req, res) {
  res.setHeader('Cache-Control', 'public, max-age=60');
  if (LB_DISCLOSURE === 'curated') return res.status(200).json({ configured: true, mode: 'curated', items: [] });
  if (!KV_URL || !KV_TOKEN) return res.status(200).json({ configured: false, items: [] });
  const period = req.query.period === 'week' || req.query.period === 'month' ? req.query.period : 'all';
  const r = await kv([['ZREVRANGE', lbKey(period), '0', '4', 'WITHSCORES']]);
  const flat = (r && r.json && r.json[0] && r.json[0].result) || [];
  const items = [];
  for (let i = 0; i < flat.length; i += 2) {
    items.push({ domain: LB_DISCLOSURE === 'mask' ? maskDomain(flat[i]) : flat[i], score: n(flat[i + 1]) });
  }
  return res.status(200).json({ configured: true, mode: LB_DISCLOSURE, period, items });
}

// 상담신청(리드) 집계 — analytics KV 패턴 재사용, 별도 저장소·의존성 0
async function recordLead(req, res) {
  if (!KV_URL || !KV_TOKEN) return res.status(200).json({ ok: false, configured: false });
  const today = ymdKST(0);
  await kv([
    ['INCR', 'va:lead:total'],
    ['INCR', 'va:lead:' + today],
    ['EXPIRE', 'va:lead:' + today, DAY_TTL],
  ]);
  return res.status(200).json({ ok: true });
}

async function track(req, res) {
  const b = req.body || {};
  const h = req.headers || {};

  // 전환 퍼널 이벤트(상담 클릭/카카오 클릭) — 별도 비콘 {ev:'cta'|'kakao'}
  if (b.ev === 'cta' || b.ev === 'kakao') {
    await kv([['INCR', 'va:fn:' + b.ev]]);
    return res.status(200).json({ ok: true });
  }

  const ref = (b.ref || '').slice(0, 300);
  const selfHost = h.host || '';
  const ch = channelOf(ref, selfHost);
  const today = ymdKST(0);
  const isNew = !!b.nv;
  const dev = deviceOf(h['user-agent']);
  const hour = hourKST();
  // 경로: 쿼리·해시 제거, 길이 제한
  let path = String(b.path || '/').split('?')[0].split('#')[0].slice(0, 120) || '/';
  // 지역: Vercel geo 헤더(도시 우선, 없으면 리전 코드). 미배포 환경엔 없음 → 스킵
  let region = '';
  try { region = decodeURIComponent(h['x-vercel-ip-city'] || '').slice(0, 40); } catch (e) {}
  if (!region) region = String(h['x-vercel-ip-country-region'] || '').slice(0, 40);

  const cmds = [
    ['INCR', 'va:pv:total'],
    ['INCR', 'va:pv:' + today],
    ['EXPIRE', 'va:pv:' + today, DAY_TTL],
    ['INCR', 'va:src:' + ch],
    ['INCR', 'va:dev:' + dev],
    ['INCR', 'va:hour:' + hour],
    ['ZINCRBY', 'va:path', 1, path],
  ];
  if (region) cmds.push(['ZINCRBY', 'va:region', 1, region]);
  if (isNew) {
    cmds.push(['INCR', 'va:uv:total']);
    cmds.push(['INCR', 'va:uv:' + today]);
    cmds.push(['EXPIRE', 'va:uv:' + today, DAY_TTL]);
  }
  await kv(cmds);
  return res.status(200).json({ ok: true });
}

async function read(req, res) {
  res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
  if (!KV_URL || !KV_TOKEN) {
    return res.status(200).json({ configured: false, note: 'KV 미설정 — Vercel KV(Upstash) 연동 후 실데이터 표시' });
  }
  const days = [];
  for (let i = 29; i >= 0; i--) days.push(ymdKST(i)); // 과거→오늘 순

  const r = await kv([
    ['MGET', ...days.map(d => 'va:pv:' + d)],
    ['MGET', ...days.map(d => 'va:uv:' + d)],
    ['MGET', ...CHANNELS.map(c => 'va:src:' + c)],
    ['GET', 'va:pv:total'],
    ['GET', 'va:uv:total'],
    ['MGET', ...days.map(d => 'va:lead:' + d)], // r.json[5]
    ['GET', 'va:lead:total'],                    // r.json[6]
    ['MGET', 'va:dev:mobile', 'va:dev:desktop', 'va:dev:tablet'], // [7]
    ['MGET', ...Array.from({ length: 24 }, (_, i) => 'va:hour:' + i)], // [8]
    ['ZREVRANGE', 'va:path', 0, 4, 'WITHSCORES'],   // [9]
    ['ZREVRANGE', 'va:region', 0, 5, 'WITHSCORES'], // [10]
    ['GET', 'va:fn:cta'],                            // [11]
    ['GET', 'va:fn:kakao'],                          // [12]
  ]);
  if (!r || !r.json || !Array.isArray(r.json)) {
    return res.status(200).json({ configured: true, error: 'KV 응답 오류', daily: [], channels: [] });
  }
  const pvArr = (r.json[0] && r.json[0].result) || [];
  const uvArr = (r.json[1] && r.json[1].result) || [];
  const srcArr = (r.json[2] && r.json[2].result) || [];
  const pvTotal = n(r.json[3] && r.json[3].result);
  const uvTotal = n(r.json[4] && r.json[4].result);

  const leadArr = (r.json[5] && r.json[5].result) || [];
  const leadTotal = n(r.json[6] && r.json[6].result);

  const daily = days.map((d, i) => ({ date: d, pv: n(pvArr[i]), uv: n(uvArr[i]), lead: n(leadArr[i]) }));
  const channels = CHANNELS.map((c, i) => ({ key: c, pageviews: n(srcArr[i]) }))
    .filter(c => c.pageviews > 0).sort((a, b) => b.pageviews - a.pageviews);

  const last = (k, days2) => sum(daily.slice(-days2).map(x => x[k]));

  // 확장 지표: 디바이스·시간대·인기페이지·지역·전환퍼널
  const devArr = (r.json[7] && r.json[7].result) || [];
  const device = { mobile: n(devArr[0]), desktop: n(devArr[1]), tablet: n(devArr[2]) };
  const hourArr = (r.json[8] && r.json[8].result) || [];
  const hourly = Array.from({ length: 24 }, (_, i) => n(hourArr[i]));
  const zpairs = (arr) => { const out = []; for (let i = 0; i < arr.length; i += 2) out.push({ name: arr[i], count: n(arr[i + 1]) }); return out; };
  const topPaths = zpairs((r.json[9] && r.json[9].result) || []);
  const regions = zpairs((r.json[10] && r.json[10].result) || []);
  const funnel = { views: pvTotal, cta: n(r.json[11] && r.json[11].result), kakao: n(r.json[12] && r.json[12].result), leads: leadTotal };

  return res.status(200).json({
    configured: true,
    totals: { pageviews: pvTotal, visitors: uvTotal, leads: leadTotal },
    today: { pageviews: last('pv', 1), visitors: last('uv', 1), leads: last('lead', 1) },
    week: { pageviews: last('pv', 7), visitors: last('uv', 7), leads: last('lead', 7) },
    month: { pageviews: last('pv', 30), visitors: last('uv', 30), leads: last('lead', 30) },
    daily, channels, device, hourly, topPaths, regions, funnel,
  });
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  try {
    if (req.method === 'POST') {
      if (req.body && req.body.lead) return await recordLead(req, res); // 상담신청(리드) 집계
      if (req.body && req.body.lb) return await recordScore(req, res); // SEO 점수 기록
      return await track(req, res);
    }
    if (req.method === 'GET') {
      if (req.query && req.query.lb === 'top') return await topScores(req, res); // 리더보드 조회
      return await read(req, res);
    }
    return res.status(405).json({ error: 'GET/POST only' });
  } catch (e) {
    return res.status(200).json({ ok: false, error: e.message });
  }
};
