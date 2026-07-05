'use strict';

/**
 * 검색 스모크 테스트 / CLI — 공유 검색기(lib/retriever.js) 사용.
 * 동의어 확장 + (임베딩 있으면)하이브리드 검색을 그대로 확인한다.
 *
 * 사용:  node pipeline/retrieve.js "전후사진 게시 허용 요건"
 *        node pipeline/retrieve.js            # 기본 예시 질의 실행
 */

const { retrieve, stats } = require('../lib/retriever');

function demo(query) {
  console.log('\n🔎 질의:', query);
  const hits = retrieve(query);
  if (!hits.length) { console.log('  (결과 없음)'); return; }
  for (const h of hits) {
    console.log(`  [score ${h.score.toFixed(2)} | kw ${h.kw}${h.vec ? ' vec ' + h.vec.toFixed(2) : ''}] ${h.chunk.title}`);
    console.log(`     근거: ${h.chunk.legalRefs.join(', ') || '-'} | 태그: ${h.chunk.tags.join(', ')}`);
    console.log(`     ${h.chunk.text.replace(/\n+/g, ' ').replace(/\*\*/g, '').slice(0, 100)}...`);
  }
}

const arg = process.argv.slice(2).join(' ').trim();
console.log('검색기:', stats());
if (arg) {
  demo(arg);
} else {
  ['전후사진 게시 허용 요건', '환자 후기 올려도 되나요', '사전심의 대상 매체 10만명 기준', '비급여 할인 이벤트 주의사항'].forEach(demo);
}
