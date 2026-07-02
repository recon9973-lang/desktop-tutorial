'use strict';

// 랜딩 체류시간용 인사이트 도구 3종 통합 (Vercel 함수 절약)
//   GET /api/insights?type=trend&keyword=..&keyword2=..&keyword3=..  → 네이버 데이터랩 검색어 트렌드
//   GET /api/insights?type=search&query=..                          → 네이버 검색(블로그/웹) 경쟁·노출 신호
//   GET /api/insights?type=aeo&q=..&name=..                         → AI(웹검색) 추천 가시성 (Perplexity)
//   GET /api/insights?type=keywordtool&q=..                         → 네이버 검색광고 키워드 도구(월 검색량·경쟁도)
//
// 필요 env: NAVER_CLIENT_ID, NAVER_CLIENT_SECRET (데이터랩·검색), PERPLEXITY_API_KEY (AEO),
//          NAVER_AD_API_KEY, NAVER_AD_SECRET, NAVER_AD_CUSTOMER_ID (검색광고 키워드도구)

const https = require('https');
const crypto = require('crypto');

function httpReq({ hostname, path, method, headers, bodyStr }) {
  return new Promise((resolve) => {
    const opts = { hostname, path, method: method || 'GET', headers: headers || {} };
    if (bodyStr) opts.headers['Content-Length'] = Buffer.byteLength(bodyStr);
    const req = https.request(opts, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        const text = Buffer.concat(chunks).toString('utf8');
        let json = null; try { json = JSON.parse(text); } catch {}
        resolve({ status: res.statusCode, json, text });
      });
    });
    req.on('error', (e) => resolve({ status: 0, error: e.message }));
    req.setTimeout(25000, () => { req.destroy(); resolve({ status: 0, error: 'timeout' }); });
    if (bodyStr) req.write(bodyStr);
    req.end();
  });
}

function naverHeaders(extra) {
  return Object.assign({
    'X-Naver-Client-Id': (process.env.NAVER_CLIENT_ID || '').trim(),
    'X-Naver-Client-Secret': (process.env.NAVER_CLIENT_SECRET || '').trim(),
  }, extra || {});
}

function ymd(d) { return d.toISOString().slice(0, 10); }

// ── A. 데이터랩 검색어 트렌드 ──
async function trend(req, res) {
  if (!process.env.NAVER_CLIENT_ID || !process.env.NAVER_CLIENT_SECRET) {
    return res.status(500).json({ error: 'NAVER_CLIENT_ID/SECRET 미설정' });
  }
  const kws = [req.query.keyword, req.query.keyword2, req.query.keyword3].filter(Boolean).slice(0, 3);
  if (!kws.length) return res.status(400).json({ error: 'keyword 필요' });
  const end = new Date();
  const start = new Date(); start.setFullYear(start.getFullYear() - 1);
  const body = JSON.stringify({
    startDate: ymd(start), endDate: ymd(end), timeUnit: 'month',
    keywordGroups: kws.map(k => ({ groupName: k, keywords: [k] })),
  });
  const r = await httpReq({
    hostname: 'openapi.naver.com', path: '/v1/datalab/search', method: 'POST',
    headers: naverHeaders({ 'Content-Type': 'application/json' }), bodyStr: body,
  });
  if (r.status === 200 && r.json) return res.status(200).json(r.json);
  return res.status(r.status || 500).json({ error: (r.json && r.json.errorMessage) || r.error || ('HTTP ' + r.status) });
}

// ── B. 네이버 검색(블로그/웹) 경쟁·노출 신호 ──
async function search(req, res) {
  if (!process.env.NAVER_CLIENT_ID || !process.env.NAVER_CLIENT_SECRET) {
    return res.status(500).json({ error: 'NAVER_CLIENT_ID/SECRET 미설정' });
  }
  const q = (req.query.query || '').trim();
  if (!q) return res.status(400).json({ error: 'query 필요' });
  const eq = encodeURIComponent(q);
  const [blog, web] = await Promise.all([
    httpReq({ hostname: 'openapi.naver.com', path: `/v1/search/blog.json?query=${eq}&display=3&sort=date`, headers: naverHeaders() }),
    httpReq({ hostname: 'openapi.naver.com', path: `/v1/search/webkr.json?query=${eq}&display=1`, headers: naverHeaders() }),
  ]);
  if (blog.status !== 200 || !blog.json) {
    return res.status(blog.status && blog.status !== 200 ? blog.status : 502).json({ error: (blog.json && blog.json.errorMessage) || blog.error || '네이버 검색 응답 오류' });
  }
  return res.status(200).json({
    query: q,
    blogTotal: blog.json.total || 0,
    webTotal: (web.json && web.json.total) || 0,
    recent: (blog.json.items || []).map(i => ({
      title: (i.title || '').replace(/<\/?b>/g, ''),
      date: i.postdate || '', link: i.link || '',
    })),
  });
}

// ── C. AEO 가시성 (Perplexity 웹검색 — 실제 AI 답변 기반) ──
async function aeo(req, res) {
  const key = process.env.PERPLEXITY_API_KEY;
  if (!key) return res.status(500).json({ error: 'PERPLEXITY_API_KEY 미설정 — 실제 AI검색 결과 확인에 필요합니다.' });
  const q = (req.query.q || '').trim();
  const name = (req.query.name || '').trim();
  if (!q) return res.status(400).json({ error: 'q(질문) 필요' });
  const body = JSON.stringify({
    model: process.env.PERPLEXITY_MODEL || 'sonar',
    messages: [
      { role: 'system', content: '너는 한국 사용자에게 병원·의원을 추천하는 검색 도우미다. 실제 검색 결과를 근거로 구체적인 병원명과 이유를 답하라.' },
      { role: 'user', content: q },
    ],
  });
  const r = await httpReq({
    hostname: 'api.perplexity.ai', path: '/chat/completions', method: 'POST',
    headers: { 'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json' }, bodyStr: body,
  });
  if (r.status !== 200 || !r.json || !r.json.choices) {
    return res.status(r.status || 500).json({ error: (r.json && r.json.error && (r.json.error.message || r.json.error)) || r.error || ('HTTP ' + r.status) });
  }
  const answer = r.json.choices[0].message.content || '';
  const mentioned = name ? answer.toLowerCase().includes(name.toLowerCase()) : null;
  return res.status(200).json({
    answer, mentioned, name,
    citations: r.json.citations || (r.json.search_results || []).map(s => s.url) || [],
  });
}

// ── D. 네이버 검색광고 키워드 도구 (실제 월 검색량·경쟁도·클릭수) ──
// 검색광고 API는 데이터랩/검색과 별개(host: api.searchad.naver.com, HMAC 서명 인증).
function searchAdHeaders(method, apiPath) {
  const ts = String(Date.now());
  const ad = adCreds();
  const sign = crypto
    .createHmac('sha256', ad.secret)
    .update(`${ts}.${method}.${apiPath}`)
    .digest('base64');
  return {
    'X-Timestamp': ts,
    'X-API-KEY': ad.key,
    'X-Customer': ad.customer,
    'X-Signature': sign,
  };
}

// 검색광고 API 자격증명 — 신·구 변수명 모두 허용 (저장소 통합 전 등록분 호환)
function adCreds() {
  return {
    key: (process.env.NAVER_AD_API_KEY || process.env.NAVER_ACCESS_LICENSE || '').trim(),
    secret: (process.env.NAVER_AD_SECRET || process.env.NAVER_SECRET_KEY || '').trim(),
    customer: (process.env.NAVER_AD_CUSTOMER_ID || process.env.NAVER_CUSTOMER_ID || '').trim(),
  };
}

function toNum(v) {
  // 네이버는 검색량이 적으면 "< 10" 문자열로 줌 → 5로 근사
  if (typeof v === 'number') return v;
  if (typeof v === 'string') {
    if (/<\s*10/.test(v)) return 5;
    const n = parseInt(v.replace(/[^\d]/g, ''), 10);
    return isNaN(n) ? 0 : n;
  }
  return 0;
}

async function keywordtool(req, res) {
  const ad = adCreds();
  if (!ad.key || !ad.secret || !ad.customer) {
    return res.status(501).json({
      configured: false,
      error: '네이버 검색광고 API 미설정 — NAVER_AD_API_KEY(또는 NAVER_ACCESS_LICENSE), NAVER_AD_SECRET(또는 NAVER_SECRET_KEY), NAVER_AD_CUSTOMER_ID(또는 NAVER_CUSTOMER_ID) 필요',
    });
  }
  const q = (req.query.q || req.query.query || '').trim();
  if (!q) return res.status(400).json({ error: 'q(키워드) 필요' });
  // 검색광고 키워드도구: 공백 제거한 힌트키워드(최대 5개, 쉼표 구분)
  const hint = q.split(/[,\s]+/).filter(Boolean).slice(0, 5).map(k => k.replace(/\s+/g, '')).join(',');
  const apiPath = '/keywordstool';
  const r = await httpReq({
    hostname: 'api.searchad.naver.com',
    path: `${apiPath}?hintKeywords=${encodeURIComponent(hint)}&showDetail=1`,
    method: 'GET',
    headers: searchAdHeaders('GET', apiPath),
  });
  if (r.status !== 200 || !r.json || !Array.isArray(r.json.keywordList)) {
    return res.status(r.status || 502).json({
      configured: true,
      error: (r.json && (r.json.title || r.json.message)) || r.error || ('네이버 검색광고 응답 오류 HTTP ' + r.status),
    });
  }
  const list = r.json.keywordList.map(k => {
    const pc = toNum(k.monthlyPcQcnt);
    const mo = toNum(k.monthlyMobileQcnt);
    return {
      keyword: k.relKeyword,
      monthlyVolume: pc + mo,
      pc, mobile: mo,
      competition: k.compIdx || '-',            // 높음/중간/낮음
      avgClicks: toNum(k.monthlyAvePcClkCnt) + toNum(k.monthlyAveMobileClkCnt),
      avgDepth: k.plAvgDepth != null ? k.plAvgDepth : null, // 평균 노출 광고 개수(경쟁 신호)
    };
  }).sort((a, b) => b.monthlyVolume - a.monthlyVolume);
  return res.status(200).json({ configured: true, query: q, count: list.length, keywords: list.slice(0, 20) });
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS');
  if (req.method === 'OPTIONS') return res.status(200).end();
  const type = req.query.type;
  try {
    if (type === 'trend') return await trend(req, res);
    if (type === 'search') return await search(req, res);
    if (type === 'aeo') return await aeo(req, res);
    if (type === 'keywordtool') return await keywordtool(req, res);
    return res.status(400).json({ error: 'unknown type (trend|search|aeo|keywordtool)' });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
};
