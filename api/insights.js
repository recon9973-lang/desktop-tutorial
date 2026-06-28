'use strict';

// 랜딩 체류시간용 인사이트 도구 3종 통합 (Vercel 함수 절약)
//   GET /api/insights?type=trend&keyword=..&keyword2=..&keyword3=..  → 네이버 데이터랩 검색어 트렌드
//   GET /api/insights?type=search&query=..                          → 네이버 검색(블로그/웹) 경쟁·노출 신호
//   GET /api/insights?type=aeo&q=..&name=..                         → AI(웹검색) 추천 가시성 (Perplexity)
//
// 필요 env: NAVER_CLIENT_ID, NAVER_CLIENT_SECRET (데이터랩·검색), PERPLEXITY_API_KEY (AEO)

const https = require('https');

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
  if (blog.status !== 200) {
    return res.status(blog.status || 500).json({ error: (blog.json && blog.json.errorMessage) || blog.error || ('HTTP ' + blog.status) });
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

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS');
  if (req.method === 'OPTIONS') return res.status(200).end();
  const type = req.query.type;
  try {
    if (type === 'trend') return await trend(req, res);
    if (type === 'search') return await search(req, res);
    if (type === 'aeo') return await aeo(req, res);
    return res.status(400).json({ error: 'unknown type (trend|search|aeo)' });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
};
