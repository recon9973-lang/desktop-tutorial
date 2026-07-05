'use strict';

/**
 * 지식베이스 검색기 (하이브리드: 키워드 + (선택)벡터 임베딩)
 *
 *  - 키워드 축: retrieval-index.json 역색인 + 도메인 동의어 확장(synonyms.json)
 *  - 벡터 축(선택): embeddings.json이 있으면(method=openai) 코사인 유사도를 가중합
 *
 * embeddings.json이 없으면 키워드 축만으로 동작(기본·항상 가능).
 * API(preview/api/chatbot.js)·CLI(pipeline/retrieve.js) 공용.
 */

const fs = require('fs');
const path = require('path');

const KB_DIR = path.resolve(__dirname, '..', 'data', 'kb');
const DATA_DIR = path.resolve(__dirname, '..', 'data');

let _kb = null, _index = null, _byId = null, _syn = null, _emb = null, _loaded = false;

function loadJson(p, fallback) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) { return fallback; }
}

function load() {
  if (_loaded) return;
  _kb = JSON.parse(fs.readFileSync(path.join(KB_DIR, 'knowledge-base.json'), 'utf8'));
  _index = JSON.parse(fs.readFileSync(path.join(KB_DIR, 'retrieval-index.json'), 'utf8'));
  _byId = new Map(_kb.chunks.map(c => [c.id, c]));
  _syn = buildSynMap(loadJson(path.join(DATA_DIR, 'synonyms.json'), { groups: [] }));
  _emb = loadJson(path.join(KB_DIR, 'embeddings.json'), null); // 있으면 하이브리드
  _loaded = true;
}

// 동의어 그룹 → 토큰별 확장 집합
function buildSynMap(syn) {
  const map = new Map();
  for (const group of (syn.groups || [])) {
    const norm = group.map(g => g.toLowerCase());
    for (const w of norm) {
      const set = map.get(w) || new Set();
      norm.forEach(x => { if (x !== w) set.add(x); });
      map.set(w, set);
    }
  }
  return map;
}

function tokenize(text) {
  const out = new Set();
  const re = /[가-힣]{2,}|[A-Za-z]{2,}|\d+호|\d+조|\d+항/g;
  let m;
  while ((m = re.exec(text)) !== null) out.add(m[0].toLowerCase());
  return [...out];
}

// 질의 토큰 + 동의어 확장(확장 토큰은 가중치 0.6로 낮춤)
function expand(tokens) {
  const weighted = new Map();
  for (const t of tokens) weighted.set(t, Math.max(weighted.get(t) || 0, 1));
  for (const t of tokens) {
    const syns = _syn.get(t);
    if (!syns) continue;
    for (const s of syns) weighted.set(s, Math.max(weighted.get(s) || 0, 0.6));
  }
  return weighted; // token -> weight
}

function cosine(a, b) {
  let dot = 0, na = 0, nb = 0;
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
  return na && nb ? dot / (Math.sqrt(na) * Math.sqrt(nb)) : 0;
}

/**
 * 검색. embeddings.json + queryVector가 있으면 하이브리드.
 * @param {string} query
 * @param {number} topK
 * @param {number[]|null} queryVector  질의 임베딩(있으면 벡터 축 가중)
 * @returns {Array<{chunk, score, kw, vec}>}
 */
function retrieve(query, topK = 4, queryVector = null) {
  load();
  const weighted = expand(tokenize(query));
  const kw = new Map();
  for (const [t, w] of weighted) {
    const ids = _index.inverted[t];
    if (!ids) continue;
    for (const id of new Set(ids)) kw.set(id, (kw.get(id) || 0) + w);
  }

  // 벡터 축(선택)
  const vecById = new Map();
  if (_emb && _emb.method === 'openai' && Array.isArray(queryVector) && _emb.vectors) {
    for (const [id, v] of Object.entries(_emb.vectors)) vecById.set(id, cosine(queryVector, v));
  }

  // 후보 = 키워드 매칭 ∪ 벡터 상위
  const cand = new Set([...kw.keys(), ...vecById.keys()]);
  const maxKw = Math.max(1, ...kw.values());
  const scored = [...cand].map(id => {
    const k = (kw.get(id) || 0) / maxKw;         // 0~1 정규화
    const v = vecById.get(id) || 0;               // 코사인 0~1
    const score = vecById.size ? (0.6 * k + 0.4 * v) : k;
    return { chunk: _byId.get(id), score, kw: kw.get(id) || 0, vec: v };
  }).filter(x => x.chunk);

  return scored
    .sort((a, b) => b.score - a.score || b.chunk.legalRefs.length - a.chunk.legalRefs.length)
    .slice(0, topK);
}

function stats() {
  load();
  return {
    chunks: _kb.chunkCount,
    tokens: _index.tokenCount,
    synonymGroups: _syn ? new Set([..._syn.keys()]).size : 0,
    hybrid: !!(_emb && _emb.method === 'openai'),
    updated: _kb.updated,
  };
}

module.exports = { retrieve, tokenize, stats, expand: (q) => expand(tokenize(q)) };
