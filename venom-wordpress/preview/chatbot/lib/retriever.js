'use strict';

/**
 * 지식베이스 검색기 (하이브리드 검색의 키워드 축)
 * knowledge-base.json + retrieval-index.json을 로드해 질의에 대한 근거 청크를 반환.
 * 벡터 임베딩(embed.js, 추후)이 붙으면 여기서 점수를 가중합한다.
 *
 * API 함수(preview/api/chatbot.js)와 CLI(pipeline/retrieve.js) 양쪽에서 재사용.
 */

const fs = require('fs');
const path = require('path');

const KB_DIR = path.resolve(__dirname, '..', 'data', 'kb');

let _kb = null, _index = null, _byId = null;

function load() {
  if (_kb) return;
  _kb = JSON.parse(fs.readFileSync(path.join(KB_DIR, 'knowledge-base.json'), 'utf8'));
  _index = JSON.parse(fs.readFileSync(path.join(KB_DIR, 'retrieval-index.json'), 'utf8'));
  _byId = new Map(_kb.chunks.map(c => [c.id, c]));
}

function tokenize(text) {
  const out = new Set();
  const re = /[가-힣]{2,}|[A-Za-z]{2,}|\d+호|\d+조|\d+항/g;
  let m;
  while ((m = re.exec(text)) !== null) out.add(m[0].toLowerCase());
  return [...out];
}

/**
 * 키워드 검색.
 * @param {string} query
 * @param {number} topK
 * @returns {Array<{chunk, score}>}
 */
function retrieve(query, topK = 4) {
  load();
  const qTokens = tokenize(query);
  const score = new Map();
  for (const t of qTokens) {
    const ids = _index.inverted[t];
    if (!ids) continue;
    for (const id of new Set(ids)) score.set(id, (score.get(id) || 0) + 1);
  }
  return [...score.entries()]
    .map(([id, s]) => ({ chunk: _byId.get(id), score: s }))
    .filter(x => x.chunk)
    .sort((a, b) => b.score - a.score || b.chunk.legalRefs.length - a.chunk.legalRefs.length)
    .slice(0, topK);
}

function stats() {
  load();
  return { chunks: _kb.chunkCount, tokens: _index.tokenCount, updated: _kb.updated };
}

module.exports = { retrieve, tokenize, stats };
