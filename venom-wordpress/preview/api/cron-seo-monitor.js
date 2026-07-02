'use strict';

// 등록된 도메인의 SEO 점수를 매일 1회 자동 측정 → GitHub JSON에 일별 히스토리로 누적.
// 화면(SEO 점수 체크)과 100% 동일한 seo-engine으로 채점한다(정적 분석 + PSI 병합).
//  - Vercel 크론(매일) 또는 관리자 수동 호출로 실행
//  - 인증: CRON_SECRET(크론/Actions) 또는 ADMIN_SECRET(관리자 수동) Bearer 토큰
//  - GET  /api/cron-seo-monitor                 → 등록된 모든 도메인 측정(오늘 미측정분만)
//  - GET  /api/cron-seo-monitor?domain=a.com    → 특정 도메인 1건 즉시 측정(관리자 "지금 측정")
//  - GET  /api/cron-seo-monitor?force=1         → 오늘 이미 측정했어도 재측정(덮어쓰기)
//
// 저장 파일: venom-wordpress/preview/content/seo-monitor.json
//   { domains:[{url,label,addedAt}], history:{ "<domain>":[ {date,pct,total,max,grade,cats,psi, full?} ] } }
//   full(전체 리포트)은 최근 FULL_KEEP일만 보관(파일 크기 제한), 점수 포인트는 HISTORY_KEEP일 보관.

const https = require('https');
const http = require('http');
const { URL } = require('url');

const OWNER  = process.env.GITHUB_OWNER  || 'recon9973-lang';
const REPO   = process.env.GITHUB_REPO   || 'desktop-tutorial';
const BRANCH = process.env.GITHUB_BRANCH || 'main';
const TOKEN  = process.env.GITHUB_TOKEN;
const PSI_KEY = process.env.PSI_KEY;

const STORE_PATH   = 'venom-wordpress/preview/content/seo-monitor.json';
const MAX_PER_RUN  = 15;   // 1회 실행당 측정 도메인 수 상한(쿼터·실행시간 보호)
const FULL_KEEP    = 60;   // 전체 리포트(full) 보관 일수
const HISTORY_KEEP = 365;  // 점수 포인트 보관 일수
const CONCURRENCY  = 4;    // 동시 측정 수

// seo-engine을 Node에서 직접 사용(UMD: module.exports). 화면과 동일 채점 보장.
let SEOEngine = null;
try { SEOEngine = require('../venom-wordpress/preview/assets/seo-engine.js'); }
catch (e) { console.error('[seo-monitor] seo-engine 로드 실패:', e.message); }

// linkedom: 서버 측 DOM. 없으면 PSI 기준으로 강등(빌드/실행 안 깨짐).
let parseHTML = null;
try { parseHTML = require('linkedom').parseHTML; }
catch (e) { console.warn('[seo-monitor] linkedom 미설치 — PSI 기준으로 채점(정적 DOM 분석 생략).'); }

function kstDateStr() {
  return new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Seoul' })).toISOString().slice(0, 10);
}

function authCheck(req) {
  const cron = process.env.CRON_SECRET;
  const admin = process.env.ADMIN_SECRET;
  const auth = (req.headers['authorization'] || '').trim();
  if (cron && auth === `Bearer ${cron}`) return true;
  if (admin && auth === `Bearer ${admin}`) return true;
  return false;
}

// SSRF 방지(관리자 등록 도메인이라도 사설/링크로컬 차단)
function isBlockedHost(hostname) {
  const h = (hostname || '').toLowerCase();
  if (h === 'localhost' || h === '0.0.0.0' || h === '::1' || h.endsWith('.local') || h.endsWith('.internal')) return true;
  const m = h.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (m) {
    const a = +m[1], b = +m[2];
    if (a === 10 || a === 127 || a === 0) return true;
    if (a === 169 && b === 254) return true;
    if (a === 172 && b >= 16 && b <= 31) return true;
    if (a === 192 && b === 168) return true;
  }
  return false;
}

// ── GitHub Contents API (읽기/쓰기) ──
function gh(method, filePath, body) {
  const payload = body ? JSON.stringify(body) : undefined;
  return new Promise((resolve) => {
    const req = https.request({
      hostname: 'api.github.com',
      path: `/repos/${OWNER}/${REPO}/contents/${filePath}` + (method === 'GET' ? `?ref=${BRANCH}` : ''),
      method,
      headers: {
        'Authorization': `token ${TOKEN}`,
        'User-Agent': 'venom-seo-monitor/1.0',
        'Accept': 'application/vnd.github.v3+json',
        ...(payload ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) } : {}),
      },
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        let json = null; try { json = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch {}
        resolve({ status: res.statusCode, json });
      });
    });
    req.on('error', () => resolve({ status: 0 }));
    req.setTimeout(20000, () => { req.destroy(); resolve({ status: 0 }); });
    if (payload) req.write(payload);
    req.end();
  });
}

async function loadStore() {
  const r = await gh('GET', STORE_PATH);
  if (r.status === 200 && r.json && r.json.content) {
    try {
      const data = JSON.parse(Buffer.from(r.json.content, 'base64').toString('utf8'));
      return { data: normalize(data), sha: r.json.sha };
    } catch {}
  }
  return { data: { domains: [], history: {} }, sha: undefined };
}

function normalize(d) {
  d = d || {};
  if (!Array.isArray(d.domains)) d.domains = [];
  if (!d.history || typeof d.history !== 'object') d.history = {};
  return d;
}

async function saveStore(data, sha) {
  const content = Buffer.from(JSON.stringify(data, null, 2)).toString('base64');
  const put = await gh('PUT', STORE_PATH, {
    message: `seo-monitor: ${kstDateStr()} 일일 점수 갱신`,
    content, branch: BRANCH, ...(sha ? { sha } : {}),
  });
  return put.status === 200 || put.status === 201;
}

// ── 페이지 HTML + robots.txt 수집(Chrome UA, 리다이렉트 추적) ──
function fetchUrl(urlStr, redirects) {
  return new Promise((resolve, reject) => {
    if (redirects > 5) return reject(new Error('Too many redirects'));
    let parsed;
    try { parsed = new URL(urlStr); } catch (e) { return reject(e); }
    const lib = parsed.protocol === 'https:' ? https : http;
    const req = lib.request({
      hostname: parsed.hostname,
      port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
      path: parsed.pathname + parsed.search,
      method: 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'identity',
      },
      timeout: 12000,
    }, (res) => {
      if ([301, 302, 303, 307, 308].includes(res.statusCode) && res.headers.location) {
        let next = res.headers.location;
        if (!next.startsWith('http')) next = parsed.protocol + '//' + parsed.host + next;
        return resolve(fetchUrl(next, redirects + 1));
      }
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => resolve({ status: res.statusCode, body: Buffer.concat(chunks).toString('utf8') }));
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('Timeout')); });
    req.end();
  });
}

function fetchPSI(fullUrl) {
  const apiPath = '/pagespeedonline/v5/runPagespeed?url=' + encodeURIComponent(fullUrl)
    + '&key=' + PSI_KEY
    + '&strategy=mobile&category=seo&category=performance&category=best-practices&category=accessibility';
  return new Promise((resolve) => {
    https.get('https://www.googleapis.com' + apiPath, (r) => {
      const chunks = [];
      r.on('data', c => chunks.push(c));
      r.on('end', () => { try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8'))); } catch { resolve(null); } });
    }).on('error', () => resolve(null));
  });
}

// 한 도메인 측정 → 채점 결과(merged) 반환
async function measure(url) {
  const full = url.startsWith('http') ? url : 'https://' + url;
  const parsed = new URL(full);
  if (!/^https?:$/.test(parsed.protocol) || isBlockedHost(parsed.hostname)) throw new Error('허용되지 않는 주소');
  const origin = parsed.protocol + '//' + parsed.host;

  const [pageR, robotsR, psi] = await Promise.all([
    fetchUrl(full, 0).catch(() => ({ body: '', status: 0 })),
    fetchUrl(origin + '/robots.txt', 0).catch(() => ({ body: '' })),
    PSI_KEY ? fetchPSI(full) : Promise.resolve(null),
  ]);

  const html = pageR.body || '';
  const robots = robotsR.body || '';
  const isHttps = parsed.protocol === 'https:';
  let doc = null;
  if (parseHTML && html) { try { doc = parseHTML(html).document; } catch {} }

  let res = SEOEngine.analyze({ url: full, html, robots, isHttps, doc });
  if (psi && psi.lighthouseResult) res = SEOEngine.mergePSI(res, psi);
  return res;
}

function toEntry(date, res) {
  const pct = res.max ? Math.round(res.total / res.max * 100) : 0;
  return {
    date,
    pct, total: res.total, max: res.max,
    grade: res.grade ? res.grade.label : '',
    cats: (res.categories || []).map(c => ({
      key: c.key, label: c.label, score: c.score, max: c.max, pct: c.pct, pending: c.pending,
    })),
    psi: res.psi ? {
      seo: res.psi.seo, perf: res.psi.perf,
      accessibility: res.psi.accessibility, bestPractices: res.psi.bestPractices,
    } : null,
    full: res,           // 전체 리포트(날짜 클릭 시 풀버전 렌더용) — 오래되면 아래서 제거
  };
}

// full 보관 한도 + 점수 포인트 보관 한도 적용
function prune(list) {
  list.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
  if (list.length > HISTORY_KEEP) list = list.slice(list.length - HISTORY_KEEP);
  const cutoff = list.length - FULL_KEEP;
  list.forEach((e, i) => { if (i < cutoff && e.full) delete e.full; });
  return list;
}

// 동시성 제한 실행
async function runPool(items, worker, limit) {
  const out = []; let idx = 0;
  async function next() {
    while (idx < items.length) {
      const i = idx++;
      try { out[i] = await worker(items[i], i); }
      catch (e) { out[i] = { error: e.message }; }
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, next));
  return out;
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();

  if (!authCheck(req)) return res.status(401).json({ error: '인증 실패(CRON_SECRET 또는 ADMIN_SECRET 필요)' });
  if (!SEOEngine) return res.status(500).json({ error: 'seo-engine 로드 실패' });
  if (!TOKEN) return res.status(500).json({ error: 'GITHUB_TOKEN 미설정' });
  if (!PSI_KEY) console.warn('[seo-monitor] PSI_KEY 미설정 — 정적 분석만으로 채점됩니다.');

  const today = kstDateStr();
  const only = (req.query && req.query.domain) ? String(req.query.domain).replace(/^https?:\/\//i, '').split('/')[0] : null;
  const force = !!(req.query && (req.query.force === '1' || req.query.force === 'true'));

  const { data, sha } = await loadStore();
  const targets = data.domains
    .map(d => (typeof d === 'string' ? { url: d } : d))
    .filter(d => d && d.url)
    .filter(d => !only || d.url.replace(/^https?:\/\//i, '').split('/')[0] === only);

  // 오늘 이미 측정한 도메인은 건너뜀(force면 재측정). 1회 실행 상한 적용.
  const pending = targets.filter(d => {
    const key = d.url.replace(/^https?:\/\//i, '').split('/')[0];
    const hist = data.history[key] || [];
    return force || !hist.some(e => e.date === today);
  }).slice(0, only ? 1 : MAX_PER_RUN);

  if (pending.length === 0) {
    return res.status(200).json({ ok: true, today, measured: 0, note: '측정 대상 없음(오늘 이미 완료 또는 등록 도메인 없음)' });
  }

  const results = await runPool(pending, async (d) => {
    const key = d.url.replace(/^https?:\/\//i, '').split('/')[0];
    const merged = await measure(d.url);
    return { key, entry: toEntry(today, merged), pct: merged.max ? Math.round(merged.total / merged.max * 100) : 0 };
  }, CONCURRENCY);

  let measured = 0; const summary = [];
  for (const r of results) {
    if (!r || r.error) { summary.push({ error: r && r.error }); continue; }
    const list = (data.history[r.key] || []).filter(e => e.date !== today); // 같은 날 중복 제거(덮어쓰기)
    list.push(r.entry);
    data.history[r.key] = prune(list);
    measured++;
    summary.push({ domain: r.key, pct: r.pct, psi: r.entry.psi });
  }

  const saved = await saveStore(data, sha);
  return res.status(saved ? 200 : 500).json({ ok: saved, today, measured, engine: parseHTML ? 'full' : 'psi-fallback', summary });
};
