'use strict';

/**
 * 의료광고심의 도우미 챗봇 API — RAG 응답 + 문구 자가진단
 *
 *  POST /api/chatbot  { message, mode }
 *    mode: 'qa'(기본)       → 근거 검색 후 근거 인용 답변  { answer, sources, grounded, llm }
 *          'diagnose'       → 광고 문구 위반 소지 진단     { diagnosis }
 *  GET  /api/chatbot        → 상태(지식베이스 통계·LLM 연동 여부)
 *
 * 근거: 의료법 제56·57조, 표시광고법. 지식베이스: preview/chatbot/data/kb/
 */

const path = require('path');
const CB = path.join(__dirname, '..', 'chatbot', 'lib');
const rag = require(path.join(CB, 'rag'));
const { stats } = require(path.join(CB, 'retriever'));

async function readBody(req) {
  let body = req.body;
  if (body && typeof body === 'object' && !Array.isArray(body)) return body;
  const chunks = [];
  await new Promise((resolve, reject) => {
    req.on('data', c => chunks.push(c));
    req.on('end', resolve);
    req.on('error', reject);
  });
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch (e) { return {}; }
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }

  try {
    if (req.method === 'GET') {
      const provider = process.env.ANTHROPIC_API_KEY ? 'anthropic'
        : process.env.OPENAI_API_KEY ? 'openai' : null;
      return res.status(200).json({
        service: '의료광고심의 도우미 챗봇',
        kb: stats(),
        llm: !!provider,
        provider,
        model: provider === 'anthropic' ? (process.env.ANTHROPIC_MODEL || 'claude-opus-4-8')
          : provider === 'openai' ? (process.env.OPENAI_TEXT_MODEL || 'gpt-4o-mini') : null,
        modes: ['qa', 'diagnose'],
      });
    }
    if (req.method !== 'POST') { res.status(405).json({ error: 'Method not allowed' }); return; }

    const body = await readBody(req);
    const message = (body.message || '').toString().trim();
    const mode = (body.mode || 'qa').toString();
    if (!message) return res.status(400).json({ error: 'message가 필요합니다.' });
    if (message.length > 4000) return res.status(400).json({ error: 'message가 너무 깁니다(최대 4000자).' });

    if (mode === 'diagnose') {
      return res.status(200).json({ mode, diagnosis: rag.diagnoseCopy(message) });
    }
    const result = await rag.answerQuestion(message);
    return res.status(200).json({ mode: 'qa', ...result });
  } catch (e) {
    console.error('chatbot handler error:', e.message);
    return res.status(500).json({ error: e.message });
  }
};
