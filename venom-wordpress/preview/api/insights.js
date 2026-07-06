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
const sa = require('../lib/naver-searchad'); // 검색광고 키워드도구 단일 소스

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

// ── C. AEO 가시성 — 멀티 AI 엔진 실질문 (perplexity | openai | gemini | claude) ──
// 각 엔진에 "환자 입장 질문"을 실제로 던져 답변·인용을 받아온다. 키 없는 엔진은 자동 비활성.
const AI_SYSTEM = '너는 한국 사용자에게 병원·의원을 추천하는 검색 도우미다. 실제 검색 결과를 근거로 구체적인 병원명과 이유를 답하라.';

function engineKeys() {
  return {
    perplexity: !!process.env.PERPLEXITY_API_KEY,
    openai: !!process.env.OPENAI_API_KEY,
    gemini: !!(process.env.GEMINI_API_KEY || process.env.GOOGLE_AI_KEY),
    claude: !!process.env.ANTHROPIC_API_KEY,
  };
}

async function askOpenAI(q) {
  const key = process.env.OPENAI_API_KEY;
  const body = JSON.stringify({
    model: process.env.OPENAI_SEARCH_MODEL || 'gpt-4o-mini',
    tools: [{ type: 'web_search_preview' }],
    input: [{ role: 'system', content: AI_SYSTEM }, { role: 'user', content: q }],
  });
  const r = await httpReq({
    hostname: 'api.openai.com', path: '/v1/responses', method: 'POST',
    headers: { 'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json' }, bodyStr: body,
  });
  if (r.status !== 200 || !r.json) throw new Error((r.json && r.json.error && r.json.error.message) || ('OpenAI HTTP ' + r.status));
  let answer = '', citations = [];
  (r.json.output || []).forEach(o => {
    if (o.type === 'message') (o.content || []).forEach(c => {
      if (c.type === 'output_text') {
        answer += c.text || '';
        (c.annotations || []).forEach(a => { if (a.type === 'url_citation' && a.url) citations.push(a.url); });
      }
    });
  });
  return { answer, citations };
}

async function askGemini(q) {
  const key = process.env.GEMINI_API_KEY || process.env.GOOGLE_AI_KEY;
  const model = process.env.GEMINI_MODEL || 'gemini-2.0-flash';
  const body = JSON.stringify({
    contents: [{ role: 'user', parts: [{ text: AI_SYSTEM + '\n\n' + q }] }],
    tools: [{ google_search: {} }],
  });
  const r = await httpReq({
    hostname: 'generativelanguage.googleapis.com',
    path: '/v1beta/models/' + model + ':generateContent?key=' + encodeURIComponent(key),
    method: 'POST', headers: { 'Content-Type': 'application/json' }, bodyStr: body,
  });
  if (r.status !== 200 || !r.json || !r.json.candidates) throw new Error((r.json && r.json.error && r.json.error.message) || ('Gemini HTTP ' + r.status));
  const cand = r.json.candidates[0] || {};
  const answer = ((cand.content || {}).parts || []).map(p => p.text || '').join('');
  const gm = cand.groundingMetadata || {};
  const citations = (gm.groundingChunks || []).map(c => (c.web && c.web.uri) || '').filter(Boolean);
  return { answer, citations };
}

async function askClaude(q) {
  const key = process.env.ANTHROPIC_API_KEY;
  const body = JSON.stringify({
    model: process.env.ANTHROPIC_MODEL || 'claude-haiku-4-5-20251001',
    max_tokens: 1024, system: AI_SYSTEM,
    messages: [{ role: 'user', content: q }],
    tools: [{ type: 'web_search_20250305', name: 'web_search', max_uses: 3 }],
  });
  const r = await httpReq({
    hostname: 'api.anthropic.com', path: '/v1/messages', method: 'POST',
    headers: { 'x-api-key': key, 'anthropic-version': '2023-06-01', 'Content-Type': 'application/json' }, bodyStr: body,
  });
  if (r.status !== 200 || !r.json || !r.json.content) throw new Error((r.json && r.json.error && r.json.error.message) || ('Claude HTTP ' + r.status));
  let answer = '', citations = [];
  (r.json.content || []).forEach(b => {
    if (b.type === 'text') {
      answer += b.text || '';
      (b.citations || []).forEach(c => { if (c.url) citations.push(c.url); });
    }
  });
  return { answer, citations };
}

async function askPerplexity(q) {
  const key = process.env.PERPLEXITY_API_KEY;
  const body = JSON.stringify({
    model: process.env.PERPLEXITY_MODEL || 'sonar',
    messages: [
      { role: 'system', content: AI_SYSTEM },
      { role: 'user', content: q },
    ],
  });
  const r = await httpReq({
    hostname: 'api.perplexity.ai', path: '/chat/completions', method: 'POST',
    headers: { 'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json' }, bodyStr: body,
  });
  if (r.status !== 200 || !r.json || !r.json.choices) throw new Error((r.json && r.json.error && (r.json.error.message || r.json.error)) || ('Perplexity HTTP ' + r.status));
  return {
    answer: r.json.choices[0].message.content || '',
    citations: r.json.citations || (r.json.search_results || []).map(x => x.url) || [],
  };
}

async function aeo(req, res) {
  const engine = String(req.query.engine || 'perplexity').toLowerCase();
  const avail = engineKeys();
  if (!avail[engine]) return res.status(500).json({ error: engine + ' 키 미설정', engine });
  const q = (req.query.q || '').trim();
  const name = (req.query.name || '').trim();
  if (!q) return res.status(400).json({ error: 'q(질문) 필요' });
  const ASK = { perplexity: askPerplexity, openai: askOpenAI, gemini: askGemini, claude: askClaude };
  try {
    const out = await ASK[engine](q);
    const answer = out.answer || '';
    const mentioned = name ? answer.toLowerCase().includes(name.toLowerCase()) : null;
    return res.status(200).json({ engine, answer, mentioned, name, citations: out.citations || [] });
  } catch (e) {
    return res.status(502).json({ error: e.message, engine });
  }
}

// (구 단일 perplexity 구현은 askPerplexity로 이관)
async function _legacyAeoUnused(req, res) {
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
// 인증·원시호출은 lib/naver-searchad 단일 소스 사용. 여기선 정규화·정렬만 담당.
async function keywordtool(req, res) {
  const q = (req.query.q || req.query.query || '').trim();
  if (!q) return res.status(400).json({ error: 'q(키워드) 필요' });
  const hints = q.split(/[,\s]+/).filter(Boolean).slice(0, 5);
  const r = await sa.fetchKeywordTool(hints);
  if (r.configured === false) {
    return res.status(501).json({
      configured: false,
      error: '네이버 검색광고 API 미설정 — NAVER_AD_API_KEY(또는 NAVER_ACCESS_LICENSE), NAVER_AD_SECRET(또는 NAVER_SECRET_KEY), NAVER_AD_CUSTOMER_ID(또는 NAVER_CUSTOMER_ID) 필요',
    });
  }
  if (!r.keywordList) {
    return res.status(r.status || 502).json({ configured: true, error: r.error || '네이버 검색광고 응답 오류' });
  }
  const list = r.keywordList.map(k => {
    // 네이버 공식 필드명은 monthlyPcQcCnt/monthlyMobileQcCnt — 구 표기는 폴백으로 유지
    const pc = sa.toNum(k.monthlyPcQcCnt != null ? k.monthlyPcQcCnt : k.monthlyPcQcnt);
    const mo = sa.toNum(k.monthlyMobileQcCnt != null ? k.monthlyMobileQcCnt : k.monthlyMobileQcnt);
    return {
      keyword: k.relKeyword,
      monthlyVolume: pc + mo,
      pc, mobile: mo,
      competition: k.compIdx || '-',            // 높음/중간/낮음
      avgClicks: sa.toNum(k.monthlyAvePcClkCnt) + sa.toNum(k.monthlyAveMobileClkCnt),
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
    if (type === 'engines') return res.status(200).json(engineKeys());
    if (type === 'keywordtool') return await keywordtool(req, res);
    return res.status(400).json({ error: 'unknown type (trend|search|aeo|engines|keywordtool)' });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
};
