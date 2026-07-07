'use strict';

/**
 * 골드 회귀 검사기 — 실제 오답·까다로운 질문(data/eval/gold.json)에 대해
 * 기대 근거조항(조 단위)이 top-K 검색결과에 포함되는지 검증한다.
 *
 * 검색 단계가 정답 근거를 LLM에 넘겨주지 못하면(이번 '심의 예외' 오답의 원인)
 * 여기서 실패로 잡아 배포 전에 차단한다. 오답 사례가 나오면 gold.json에 추가한다.
 *
 * 실행:  node pipeline/audit-gold.js
 * 종료코드: 실패 케이스가 있으면 1 (CI/빌드 게이트로 사용 가능)
 */

const fs = require('fs');
const path = require('path');
const { retrieve } = require('../lib/retriever');

const GOLD = path.resolve(__dirname, '..', 'data', 'eval', 'gold.json');
const joNum = s => (String(s).match(/제\s*(\d+)\s*조/) || [])[1];

function main() {
  const gold = JSON.parse(fs.readFileSync(GOLD, 'utf8'));
  const topK = gold.topK || 6;
  let pass = 0; const fails = [];

  for (const c of gold.cases) {
    const hits = retrieve(c.q, topK);
    const got = new Set(hits.flatMap(h => h.chunk.legalRefs.map(joNum)).filter(Boolean));
    const ok = (c.anyOf || []).some(j => got.has(String(j)));
    if (ok) { pass++; }
    else {
      fails.push({ id: c.id, q: c.q, want: c.anyOf, got: [...got], top: hits.slice(0, 3).map(h => h.chunk.title.split(' › ').pop()) });
    }
  }

  const total = gold.cases.length;
  console.log(`골드 회귀: ${pass}/${total} 통과 (top-${topK})`);
  for (const f of fails) {
    console.log(`  ✗ [${f.id}] ${f.q}`);
    console.log(`     기대 조=${JSON.stringify(f.want)}  검색된 조=${JSON.stringify(f.got)}`);
    console.log(`     상위: ${f.top.join(' | ')}`);
  }
  if (fails.length) { console.log(`\n❌ ${fails.length}건 실패 — 근거·동의어·검색 보강 필요`); process.exit(1); }
  console.log('✅ 전 케이스 통과 — 기대 근거가 모두 검색 상위에 포함됨');
}

main();
