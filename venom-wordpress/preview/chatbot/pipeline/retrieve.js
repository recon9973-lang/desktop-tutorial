'use strict';

/**
 * 검색 스모크 테스트 / 키워드 검색 레퍼런스 구현
 * 하이브리드 검색의 "키워드 축" — 임베딩 없이도 지식베이스에서 관련 청크를 찾아 근거로 반환한다.
 * (추후 embed.js의 벡터 유사도 점수와 가중합하여 최종 RAG 검색으로 확장)
 *
 * 사용:  node pipeline/retrieve.js "전후사진 게시 허용 요건"
 *        node pipeline/retrieve.js            # 기본 예시 질의 3종 실행
 */

const fs = require('fs');
const path = require('path');

const KB_DIR = path.resolve(__dirname, '..', 'data', 'kb');
const kb = JSON.parse(fs.readFileSync(path.join(KB_DIR, 'knowledge-base.json'), 'utf8'));
const index = JSON.parse(fs.readFileSync(path.join(KB_DIR, 'retrieval-index.json'), 'utf8'));
const byId = new Map(kb.chunks.map(c => [c.id, c]));

function tokenize(text) {
  const out = new Set();
  const re = /[가-힣]{2,}|[A-Za-z]{2,}|\d+호|\d+조|\d+항/g;
  let m;
  while ((m = re.exec(text)) !== null) out.add(m[0].toLowerCase());
  return [...out];
}

/**
 * 키워드 검색: 질의 토큰이 걸린 청크를 모아 매칭 토큰 수로 점수화.
 * @returns {Array<{chunk, score, hits}>}
 */
function retrieve(query, topK = 3) {
  const qTokens = tokenize(query);
  const score = new Map();   // id -> matched token count
  for (const t of qTokens) {
    const ids = index.inverted[t];
    if (!ids) continue;
    const uniq = new Set(ids);
    for (const id of uniq) score.set(id, (score.get(id) || 0) + 1);
  }
  return [...score.entries()]
    .map(([id, s]) => ({ chunk: byId.get(id), score: s }))
    .filter(x => x.chunk)
    .sort((a, b) => b.score - a.score || b.chunk.legalRefs.length - a.chunk.legalRefs.length)
    .slice(0, topK);
}

function demo(query) {
  console.log('\n🔎 질의:', query);
  const hits = retrieve(query);
  if (!hits.length) { console.log('  (결과 없음)'); return; }
  for (const h of hits) {
    console.log(`  [score ${h.score}] ${h.chunk.title}`);
    console.log(`     근거: ${h.chunk.legalRefs.join(', ') || '-'} | 태그: ${h.chunk.tags.join(', ')}`);
    console.log(`     ${h.chunk.text.replace(/\n+/g, ' ').slice(0, 100)}...`);
  }
}

const arg = process.argv.slice(2).join(' ').trim();
if (arg) {
  demo(arg);
} else {
  ['전후사진 게시 허용 요건', '사전심의 대상 매체 10만명 기준', '비급여 할인 광고 주의사항'].forEach(demo);
}

module.exports = { retrieve, tokenize };
