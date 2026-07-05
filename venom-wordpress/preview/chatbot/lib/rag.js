'use strict';

/**
 * RAG 오케스트레이션 — 의료광고심의 도우미 챗봇의 답변 생성 핵심.
 *
 *  answerQuestion(message)  : 근거 검색 → LLM이 근거 인용하며 답변(키 없으면 근거 요약 폴백)
 *  diagnoseCopy(text)       : 광고 문구 자가진단(금지·위험 표현 탐지 + 안전 대체안)
 *
 * 두뇌(LLM): Claude(Anthropic)를 우선 사용하고, 없으면 OpenAI, 둘 다 없으면 근거 요약 폴백.
 * 재사용: preview/lib/anthropic-client.js, preview/lib/openai-client.js, preview/lib/medical-ad-validator.js
 */

const fs = require('fs');
const path = require('path');
const { retrieve, stats } = require('./retriever');
let embedder = null;
try { embedder = require('../pipeline/embed'); } catch (e) {}

const KB_DIR = path.resolve(__dirname, '..', 'data', 'kb');
const RULES = JSON.parse(fs.readFileSync(path.join(KB_DIR, 'forbidden-rules.json'), 'utf8'));

// 재사용 자산(없어도 폴백 동작)
let validator = null, anthropic = null, openai = null;
try { validator = require('../../lib/medical-ad-validator'); } catch (e) {}
try { anthropic = require('../../lib/anthropic-client'); } catch (e) {}
try { openai = require('../../lib/openai-client'); } catch (e) {}

/**
 * 사용할 LLM 두뇌 선택: Claude(Anthropic) 우선 → OpenAI 폴백.
 * @returns {{provider, client, opts}|null}
 */
function pickLlm() {
  if (anthropic && process.env.ANTHROPIC_API_KEY) {
    // Opus 4.8 계열은 temperature 미지원 → max_tokens만 전달.
    return { provider: 'anthropic', client: anthropic, opts: { max_tokens: 900 } };
  }
  if (openai && process.env.OPENAI_API_KEY) {
    return { provider: 'openai', client: openai, opts: { temperature: 0.2, max_tokens: 900 } };
  }
  return null;
}

const DISCLAIMER = '※ 본 답변은 참고용 사전 진단입니다. 실제 심의 승인·반려는 자율심의기구(대한의사협회 등)의 심의 결과에 따릅니다.';

const SYSTEM_PROMPT = [
  '당신은 한국 의료광고법·의료광고심의 전문가 어시스턴트다.',
  '반드시 아래 [근거] 안의 내용만 사용해 답한다. 근거에 없으면 "제공된 자료로는 확인이 어렵다"고 말하고 추측하지 않는다.',
  '법조문·심의기준을 인용할 때는 근거의 조항(예: 의료법 제56조 제2항 제2호)을 함께 표기한다.',
  '치료효과 보장·최상급·환자 유인·비교·오인 표현을 옹호하지 않는다. 효과를 말할 땐 부작용·주의사항을 함께 안내한다.',
  '답변은 두괄식(결론 먼저)으로 간결하게. 마지막에 반드시 디스클레이머를 붙인다.',
].join('\n');

function contextBlock(hits) {
  return hits.map((h, i) =>
    `[근거 ${i + 1}] (${h.chunk.legalRefs.join(', ') || '출처: ' + h.chunk.sourceTitle})\n${h.chunk.text}`
  ).join('\n\n');
}

function sourcesOf(hits) {
  return hits.map(h => ({
    title: h.chunk.title,
    legalRefs: h.chunk.legalRefs,
    tags: h.chunk.tags,
    source: h.chunk.sourceTitle,
    score: h.score,
  }));
}

/**
 * Q&A: 근거 검색 후 LLM으로 근거 기반 답변. 키 없으면 근거 요약 폴백.
 * @returns {Promise<{answer, sources, grounded, llm}>}
 */
async function answerQuestion(message, opts = {}) {
  // 하이브리드 활성(embeddings.json + 키) 시 질의 임베딩으로 벡터 축 가중
  let queryVector = null;
  if (embedder && stats().hybrid && process.env.OPENAI_API_KEY) {
    try { queryVector = await embedder.embedText(message); } catch (e) { /* 키워드 축만 사용 */ }
  }
  const hits = retrieve(message, opts.topK || 4, queryVector);
  const sources = sourcesOf(hits);

  if (!hits.length) {
    return { answer: `제공된 자료로는 확인이 어렵습니다. 질문을 구체화해 주세요.\n\n${DISCLAIMER}`, sources, grounded: false, llm: false };
  }

  const brain = pickLlm();
  if (brain) {
    const userPrompt = `질문: ${message}\n\n[근거]\n${contextBlock(hits)}\n\n위 근거만 사용해 근거 조항을 인용하며 답하라.`;
    try {
      const { text } = await brain.client.chatComplete(SYSTEM_PROMPT, userPrompt, brain.opts);
      const answer = /디스클레이머|참고용|심의 결과/.test(text) ? text : `${text}\n\n${DISCLAIMER}`;
      return { answer, sources, grounded: true, llm: true, provider: brain.provider };
    } catch (e) {
      // LLM 실패 → 폴백으로 진행
    }
  }

  // 폴백: 근거 청크 요약(LLM 미연동/실패 시에도 유용한 답변 제공)
  const top = hits[0].chunk;
  const excerpt = top.text.replace(/\n+/g, ' ').replace(/\*\*/g, '').slice(0, 500);
  const refs = [...new Set(hits.flatMap(h => h.chunk.legalRefs))].slice(0, 6).join(', ');
  const answer =
    `가장 관련 있는 근거는 「${top.title.split(' › ').pop()}」입니다.\n\n${excerpt}${top.text.length > 500 ? '…' : ''}\n\n` +
    (refs ? `관련 근거: ${refs}\n\n` : '') +
    `(LLM 미연동 상태 — 근거 요약으로 응답. ANTHROPIC_API_KEY(Claude) 설정 시 근거 인용형 자연어 답변이 활성화됩니다.)\n\n${DISCLAIMER}`;
  return { answer, sources, grounded: true, llm: false };
}

/**
 * 문구 자가진단: 금지·위험 표현 탐지 + 안전 대체안.
 * @returns {{pass, forbidden, risky, suggestion, replacements}}
 */
function diagnoseCopy(text) {
  if (!validator) {
    return { pass: null, error: 'medical-ad-validator 미연동' };
  }
  const v = validator.validateMedicalAd(text);
  const suggestion = validator.autoFix(text);
  // 사례집 §7 대체표현 중 실제 등장한 것 매칭
  const replacements = (RULES.casebookReplacements || []).filter(r =>
    r.expression.split(/[·,\/]/).some(term => term.trim() && text.includes(term.trim()))
  );
  return {
    pass: v.pass,
    forbidden: v.forbidden,
    risky: v.risky,
    suggestion: suggestion !== text ? suggestion : null,
    replacements,
    disclaimer: DISCLAIMER,
  };
}

module.exports = { answerQuestion, diagnoseCopy, SYSTEM_PROMPT, DISCLAIMER };
