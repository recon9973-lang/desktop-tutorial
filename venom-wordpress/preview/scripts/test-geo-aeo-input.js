#!/usr/bin/env node
'use strict';

/**
 * lib/geo-aeo-input.js 오프라인 검증 — 거래처+프롬프트셋 → businesses[] 변환 로직.
 * 실행:  node scripts/test-geo-aeo-input.js   (실패 시 exit 1)
 */

const AEO = require('../lib/geo-aeo-input.js');

let pass = 0, fail = 0;
function ok(name, cond) { cond ? (pass++, console.log('  ✓ ' + name)) : (fail++, console.error('  ✗ ' + name)); }

console.log('buildBusinesses');
{
  const clients = [
    { id: 'pain', name: '시원통증', coreKeywords: ['시원마취통증'], active: true },
    { id: 'skin', name: '시원스킨', coreKeywords: [], active: true },       // cores 비면 name 사용
    { id: 'off', name: '비활성', active: false },                            // 비활성 제외
    { id: 'noq', name: '질문없음', active: true },                           // 질문 없어 제외
  ];
  const sets = [
    { clientId: 'pain', questions: [{ id: 'q0', text: '포항 정형외과 추천', type: 'discovery' }, { id: 'q1', text: '시원통증 어때', type: 'brand' }] },
    { clientId: 'skin', questions: ['포항 피부과 추천'] }, // 문자열 배열도 허용
  ];
  const biz = AEO.buildBusinesses(clients, sets);

  ok('활성+질문 있는 거래처만', biz.length === 2);
  ok('pain 매핑(key=id)', biz[0].key === 'pain' && biz[0].name === '시원통증');
  ok('질문 텍스트 추출', biz[0].questions.length === 2 && biz[0].questions[0] === '포항 정형외과 추천');
  ok('cores 지정 유지', JSON.stringify(biz[0].cores) === JSON.stringify(['시원마취통증']));
  const skin = biz.find((b) => b.key === 'skin');
  ok('cores 비면 name 대체', skin && JSON.stringify(skin.cores) === JSON.stringify(['시원스킨']));
  ok('문자열 질문 허용', skin && skin.questions[0] === '포항 피부과 추천');
  ok('비활성 제외', !biz.find((b) => b.key === 'off'));
  ok('질문없음 제외', !biz.find((b) => b.key === 'noq'));
  ok('빈 입력 안전', AEO.buildBusinesses(null, null).length === 0);
}

console.log('loadInput (fs 주입)');
{
  // 신규 소스 정상 → geo
  const fsGeo = {
    readFileSync(p) {
      if (p.includes('clients.json')) return JSON.stringify({ clients: [{ id: 'a', name: 'A', active: true }] });
      if (p.includes('prompt-sets.json')) return JSON.stringify({ sets: [{ clientId: 'a', questions: ['q'] }] });
      throw new Error('no fallback needed');
    },
  };
  let r = AEO.loadInput(fsGeo, {});
  ok('신규 소스 사용(source=geo)', r.source === 'geo' && r.businesses.length === 1);

  // 신규 비어있음 → fallback
  const fsFallback = {
    readFileSync(p) {
      if (p.includes('clients.json')) return JSON.stringify({ clients: [] });
      if (p.includes('prompt-sets.json')) return JSON.stringify({ sets: [] });
      if (p.includes('ai-expose-input.json')) return JSON.stringify({ businesses: [{ key: 'x', name: 'X', cores: ['X'], questions: ['q'] }] });
      throw new Error('unexpected');
    },
  };
  r = AEO.loadInput(fsFallback, {});
  ok('신규 비면 폴백(source=fallback)', r.source === 'fallback' && r.businesses.length === 1 && r.businesses[0].key === 'x');

  // 실제 시드 파일 로드(리포지토리 현재 상태 정합성)
  const realFs = require('fs');
  const real = AEO.loadInput(realFs, {
    clientsPath: __dirname + '/../content/geo/clients.json',
    setsPath: __dirname + '/../content/geo/prompt-sets.json',
    fallbackPath: __dirname + '/../content/ai-expose-input.json',
  });
  ok('실제 시드 2거래처 로드', real.source === 'geo' && real.businesses.length === 2);
  ok('실제 시드 질문 5개', real.businesses[0].questions.length === 5);
}

console.log(`\n결과: ${pass} pass, ${fail} fail`);
process.exit(fail ? 1 : 0);
