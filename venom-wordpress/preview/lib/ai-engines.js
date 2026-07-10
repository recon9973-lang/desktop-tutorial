'use strict';

// ============================================================
// ai-engines — 멀티 AI 검색엔진 실질문 단일 소스
// ------------------------------------------------------------
// perplexity | openai | gemini | claude 에 "환자 입장 질문"을 실제로 던져
// 답변·인용을 받아온다. 키 없는 엔진은 자동 비활성.
// (api/insights.js의 인라인 구현을 이 모듈로 통합 — GEO/AEO 공용)
// 필요 env: PERPLEXITY_API_KEY / OPENAI_API_KEY / GEMINI(GOOGLE_AI)_API_KEY / ANTHROPIC(CLAUDE)_API_KEY
// ============================================================
const https = require('https');

const AI_SYSTEM = '너는 한국 사용자에게 병원·의원을 추천하는 검색 도우미다. 실제 검색 결과를 근거로 구체적인 병원명과 이유를 답하라.';

function httpReq({ hostname, path, method, headers, bodyStr }) {
  return new Promise((resolve) => {
    const opts = { hostname, path, method: method || 'GET', headers: headers || {} };
    if (bodyStr) opts.headers['Content-Length'] = Buffer.byteLength(bodyStr);
    const req = https.request(opts, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => {
        const text = Buffer.concat(chunks).toString('utf8');
        let json = null; try { json = JSON.parse(text); } catch (e) { /* null */ }
        resolve({ status: res.statusCode, json, text });
      });
    });
    req.on('error', (e) => resolve({ status: 0, error: e.message }));
    req.setTimeout(25000, () => { req.destroy(); resolve({ status: 0, error: 'timeout' }); });
    if (bodyStr) req.write(bodyStr);
    req.end();
  });
}

// AI 키 접두사·별칭 관대 인식(Vercel/마켓플레이스 접두사 대응)
function pickAI(reList) {
  for (const re of reList) {
    for (const k of Object.keys(process.env)) {
      if (re.test(k) && process.env[k]) return process.env[k];
    }
  }
  return '';
}
function anthropicKey() { return pickAI([/^ANTHROPIC_API_KEY$/, /ANTHROPIC.*KEY$/, /^CLAUDE_API_KEY$/, /CLAUDE.*API.*KEY$/]); }
function geminiKey() { return pickAI([/^GEMINI_API_KEY$/, /^GOOGLE_AI_KEY$/, /GEMINI.*API.*KEY$/]); }

function engineKeys() {
  return {
    perplexity: !!process.env.PERPLEXITY_API_KEY,
    openai: !!process.env.OPENAI_API_KEY,
    gemini: !!geminiKey(),
    claude: !!anthropicKey(),
  };
}
function availableEngines() {
  const k = engineKeys();
  return Object.keys(k).filter((e) => k[e]);
}

async function askOpenAI(q) {
  const key = process.env.OPENAI_API_KEY;
  const body = JSON.stringify({
    model: process.env.OPENAI_SEARCH_MODEL || 'gpt-4o-mini',
    tools: [{ type: 'web_search_preview' }],
    input: [{ role: 'system', content: AI_SYSTEM }, { role: 'user', content: q }],
  });
  const r = await httpReq({ hostname: 'api.openai.com', path: '/v1/responses', method: 'POST',
    headers: { 'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json' }, bodyStr: body });
  if (r.status !== 200 || !r.json) throw new Error((r.json && r.json.error && r.json.error.message) || ('OpenAI HTTP ' + r.status));
  let answer = ''; const citations = [];
  (r.json.output || []).forEach((o) => {
    if (o.type === 'message') (o.content || []).forEach((c) => {
      if (c.type === 'output_text') {
        answer += c.text || '';
        (c.annotations || []).forEach((a) => { if (a.type === 'url_citation' && a.url) citations.push(a.url); });
      }
    });
  });
  return { answer, citations };
}

async function askGemini(q) {
  const key = geminiKey();
  const models = [];
  [process.env.GEMINI_MODEL, 'gemini-2.5-flash', 'gemini-flash-latest', 'gemini-2.0-flash', 'gemini-1.5-flash']
    .forEach((m) => { if (m && models.indexOf(m) < 0) models.push(m); });
  let lastErr = 'Gemini 호출 실패';
  for (let i = 0; i < models.length; i++) {
    const model = models[i];
    for (let g = 0; g < 2; g++) {
      const payload = { contents: [{ role: 'user', parts: [{ text: AI_SYSTEM + '\n\n' + q }] }] };
      if (g === 0) payload.tools = [{ google_search: {} }];
      const r = await httpReq({ hostname: 'generativelanguage.googleapis.com',
        path: '/v1beta/models/' + model + ':generateContent?key=' + encodeURIComponent(key),
        method: 'POST', headers: { 'Content-Type': 'application/json' }, bodyStr: JSON.stringify(payload) });
      if (r.status === 200 && r.json && r.json.candidates) {
        const cand = r.json.candidates[0] || {};
        const answer = ((cand.content || {}).parts || []).map((p) => p.text || '').join('');
        const gm = cand.groundingMetadata || {};
        const citations = (gm.groundingChunks || []).map((c) => (c.web && c.web.uri) || '').filter(Boolean);
        return { answer, citations };
      }
      lastErr = (r.json && r.json.error && r.json.error.message) || ('Gemini HTTP ' + r.status);
      if (r.status !== 429 && r.status !== 404 && !/quota|not found|billing|exceeded/i.test(lastErr)) throw new Error(lastErr);
    }
  }
  throw new Error(lastErr);
}

async function askClaude(q) {
  const key = anthropicKey();
  const body = JSON.stringify({
    model: process.env.ANTHROPIC_MODEL || 'claude-haiku-4-5-20251001',
    max_tokens: 1024, system: AI_SYSTEM,
    messages: [{ role: 'user', content: q }],
    tools: [{ type: 'web_search_20250305', name: 'web_search', max_uses: 3 }],
  });
  const r = await httpReq({ hostname: 'api.anthropic.com', path: '/v1/messages', method: 'POST',
    headers: { 'x-api-key': key, 'anthropic-version': '2023-06-01', 'Content-Type': 'application/json' }, bodyStr: body });
  if (r.status !== 200 || !r.json || !r.json.content) throw new Error((r.json && r.json.error && r.json.error.message) || ('Claude HTTP ' + r.status));
  let answer = ''; const citations = [];
  (r.json.content || []).forEach((b) => {
    if (b.type === 'text') {
      answer += b.text || '';
      (b.citations || []).forEach((c) => { if (c.url) citations.push(c.url); });
    }
  });
  return { answer, citations };
}

async function askPerplexity(q) {
  const key = process.env.PERPLEXITY_API_KEY;
  const body = JSON.stringify({
    model: process.env.PERPLEXITY_MODEL || 'sonar',
    messages: [{ role: 'system', content: AI_SYSTEM }, { role: 'user', content: q }],
  });
  const r = await httpReq({ hostname: 'api.perplexity.ai', path: '/chat/completions', method: 'POST',
    headers: { 'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json' }, bodyStr: body });
  if (r.status !== 200 || !r.json || !r.json.choices) throw new Error((r.json && r.json.error && (r.json.error.message || r.json.error)) || ('Perplexity HTTP ' + r.status));
  return { answer: r.json.choices[0].message.content || '', citations: r.json.citations || (r.json.search_results || []).map((x) => x.url) || [] };
}

const ASK = { perplexity: askPerplexity, openai: askOpenAI, gemini: askGemini, claude: askClaude };

// engine 이름으로 실질문 → { answer, citations }
async function ask(engine, q) {
  const fn = ASK[String(engine || '').toLowerCase()];
  if (!fn) throw new Error('알 수 없는 엔진: ' + engine);
  return fn(q);
}

module.exports = { AI_SYSTEM, engineKeys, availableEngines, ask, askOpenAI, askGemini, askClaude, askPerplexity, httpReq };
