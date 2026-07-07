'use strict';

/**
 * 지식베이스 검색기 (하이브리드: 키워드 + 글자 n-gram 의미축 + (선택)벡터 임베딩)
 *
 *  - 키워드 축: retrieval-index.json 역색인 + 도메인 동의어 확장(synonyms.json)
 *  - 의미 축(항상 동작·오프라인): 글자 2·3-gram TF-IDF 코사인. 질의 표현이 달라도
 *    (패러프레이즈) 글자 단위로 겹치면 매칭 → 키워드 일치만으로 놓치던 근거를 회수.
 *  - 벡터 축(선택): embeddings.json이 있으면(method=openai) 코사인 유사도를 가중합.
 *
 * API(preview/api/chatbot.js)·CLI(pipeline/retrieve.js)·감사(pipeline/audit-gold.js) 공용.
 */

const fs = require('fs');
const path = require('path');

const KB_DIR = path.resolve(__dirname, '..', 'data', 'kb');
const DATA_DIR = path.resolve(__dirname, '..', 'data');

let _kb = null, _index = null, _byId = null, _syn = null, _emb = null, _loaded = false;
let _sem = null; // 글자 n-gram 의미축 인덱스

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
  _sem = buildSemIndex(_kb.chunks);
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

// ── 글자 n-gram 의미축 ────────────────────────────────────────────
// 한국어는 형태 변화가 많아 토큰 완전일치가 자주 실패한다. 글자 2·3-gram으로
// 부분 중첩을 잡으면 "심의받지 않아도" ↔ "심의 없이" 같은 이형도 매칭된다.
function charGrams(text) {
  const s = String(text).toLowerCase().replace(/[^0-9a-z가-힣]/g, '');
  const grams = [];
  for (let n = 2; n <= 3; n++) {
    for (let i = 0; i + n <= s.length; i++) grams.push(s.slice(i, i + n));
  }
  return grams;
}

function tfMap(grams) {
  const tf = new Map();
  for (const g of grams) tf.set(g, (tf.get(g) || 0) + 1);
  return tf;
}

// 청크별 글자 n-gram TF-IDF 벡터 + IDF 사전 사전계산
function buildSemIndex(chunks) {
  const df = new Map();
  const perChunk = chunks.map(c => {
    const tf = tfMap(charGrams(`${c.title}\n${c.text}\n${(c.legalRefs || []).join(' ')}`));
    for (const g of tf.keys()) df.set(g, (df.get(g) || 0) + 1);
    return { id: c.id, tf };
  });
  const N = chunks.length || 1;
  const idf = new Map();
  for (const [g, d] of df) idf.set(g, Math.log((N + 1) / (d + 0.5)));
  // 청크 벡터를 TF-IDF로 만들고 노름 계산
  const vecs = new Map();
  for (const { id, tf } of perChunk) {
    let norm = 0; const v = new Map();
    for (const [g, f] of tf) { const w = f * (idf.get(g) || 0); v.set(g, w); norm += w * w; }
    vecs.set(id, { v, norm: Math.sqrt(norm) || 1 });
  }
  return { idf, vecs };
}

// 질의 vs 전체 청크 코사인 유사도 (id -> 0~1)
function semScores(query) {
  const out = new Map();
  if (!_sem) return out;
  const qtf = tfMap(charGrams(query));
  let qnorm = 0; const qv = new Map();
  for (const [g, f] of qtf) { const w = f * (_sem.idf.get(g) || 0); qv.set(g, w); qnorm += w * w; }
  qnorm = Math.sqrt(qnorm) || 1;
  for (const [id, { v, norm }] of _sem.vecs) {
    let dot = 0;
    for (const [g, w] of qv) { const cw = v.get(g); if (cw) dot += w * cw; } // 질의 gram 기준 순회
    if (dot) out.set(id, dot / (qnorm * norm));
  }
  return out;
}

function cosine(a, b) {
  let dot = 0, na = 0, nb = 0;
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
  return na && nb ? dot / (Math.sqrt(na) * Math.sqrt(nb)) : 0;
}

/**
 * 검색. 키워드 + 글자 n-gram 의미축을 항상 결합하고, embeddings.json + queryVector가
 * 있으면 벡터축까지 3중 하이브리드.
 * @param {string} query
 * @param {number} topK
 * @param {number[]|null} queryVector  질의 임베딩(있으면 벡터 축 가중)
 * @returns {Array<{chunk, score, kw, sem, vec}>}
 */
function retrieve(query, topK = 6, queryVector = null) {
  load();
  const weighted = expand(tokenize(query));
  const kw = new Map();
  for (const [t, w] of weighted) {
    const ids = _index.inverted[t];
    if (!ids) continue;
    for (const id of new Set(ids)) kw.set(id, (kw.get(id) || 0) + w);
  }

  // 의미 축(항상)
  const sem = semScores(query);

  // 벡터 축(선택)
  const vecById = new Map();
  if (_emb && _emb.method === 'openai' && Array.isArray(queryVector) && _emb.vectors) {
    for (const [id, v] of Object.entries(_emb.vectors)) vecById.set(id, cosine(queryVector, v));
  }

  // 후보 = 키워드 ∪ 의미 상위 ∪ 벡터 상위
  const cand = new Set([...kw.keys(), ...vecById.keys()]);
  // 의미축 상위 후보도 편입(키워드가 하나도 안 걸린 근거 회수)
  const semTop = [...sem.entries()].sort((a, b) => b[1] - a[1]).slice(0, 20);
  for (const [id] of semTop) cand.add(id);

  const maxKw = Math.max(1, ...kw.values());
  const scored = [...cand].map(id => {
    const chunk = _byId.get(id);
    const k = (kw.get(id) || 0) / maxKw;   // 0~1 정규화
    const s = sem.get(id) || 0;            // 글자 n-gram 코사인 0~1
    const v = vecById.get(id) || 0;        // 임베딩 코사인 0~1
    // 축 결합: 벡터가 있으면 3중, 없으면 키워드+의미 2중.
    let score = vecById.size ? (0.45 * k + 0.25 * s + 0.30 * v) : (0.6 * k + 0.4 * s);
    // 리랭킹: 근거조항을 보유한 청크(법령·사례집)를 30% 상향 → 근거 인용 정밀도 회복.
    // (협회 FAQ 등 근거태그 없는 청크가 법령 질의에서 사례집을 밀어내는 문제 보정)
    if (chunk && chunk.legalRefs && chunk.legalRefs.length) score *= 1.3;
    return { chunk, score, kw: kw.get(id) || 0, sem: s, vec: v };
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
    semantic: !!(_sem && _sem.vecs && _sem.vecs.size), // 글자 n-gram 의미축(항상 on)
    hybrid: !!(_emb && _emb.method === 'openai'),
    updated: _kb.updated,
  };
}

module.exports = { retrieve, tokenize, stats, expand: (q) => expand(tokenize(q)) };
