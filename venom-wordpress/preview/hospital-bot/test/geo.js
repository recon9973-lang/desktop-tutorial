'use strict';

// GEO 프로빙(P1) 오프라인 검증 — mock AI 엔진으로 집계 로직 확인(네트워크 불필요)
//   node hospital-bot/test/geo.js

const path = require('path');
const G = require(path.join(__dirname, '..', 'lib', 'geo-probe'));

let fails = 0;
function assert(cond, msg) { if (!cond) { console.error('  ✗ FAIL:', msg); fails++; } else { console.log('  ✓', msg); } }
function approx(a, b, eps = 1e-6) { return Math.abs(a - b) <= eps; }

// mock ai-engines: 2개 엔진, 답변은 프롬프트에 따라 병원 언급/미언급
const NAME = '수성구 서울로열치과의원';
const mockAi = {
  availableEngines: () => ['perplexity', 'openai'],
  async ask(engine, q) {
    // 일반 추천/유명 질문엔 우리 병원 언급(긍정), 그 외엔 경쟁 병원만 언급.
    // (기본 maxPrompts=4는 첫 4개 일반 프롬프트만 사용 — 브랜드 질의 제외로 인용률 부풀림 방지)
    if (/추천|유명/.test(q)) {
      return { answer: `${engine} 결과: 서울로열치과의원이 친절하고 추천할 만합니다. 근처 미소플러스치과도 있습니다.`, citations: ['https://x'] };
    }
    return { answer: `${engine} 결과: 미소플러스치과, 튼튼정형외과가 유명합니다.`, citations: [] };
  },
};

async function main() {
  console.log('== 유닛: brandToken / mention / grade ==');
  assert(G.brandToken('수성구 서울로열치과의원', '수성구') === '서울로열', `브랜드 토큰 추출: ${G.brandToken('수성구 서울로열치과의원', '수성구')}`);
  assert(G.mentionInText('서울로열치과 추천합니다', NAME, '수성구') === true, '브랜드 부분매칭 언급 인식');
  assert(G.mentionInText('그냥 치과 갔어요', NAME, '수성구') === false, "'치과'만으로는 오탐 안 함");
  assert(G.gradeFromRate(0.7) === 'A' && G.gradeFromRate(0.5) === 'B' && G.gradeFromRate(0) === 'F', '등급 경계');

  console.log('== preview(호출 없음) ==');
  const noKey = G.preview(NAME, { category: '치과', region: '수성구', deps: { ai: { availableEngines: () => [] } } });
  assert(noKey.status === 'unconfigured' && noKey.prompts.length > 0, '엔진 없으면 unconfigured + 프롬프트');
  const ready = G.preview(NAME, { category: '치과', region: '수성구', deps: { ai: mockAi } });
  assert(ready.status === 'ready' && ready.engines.length === 2, 'ready + 엔진 목록');

  console.log('== probe(실 프로빙, mock) ==');
  const r = await G.probe(NAME, { category: '치과', region: '수성구', deps: { ai: mockAi }, maxPrompts: 4, maxEngines: 2 });
  assert(r.status === 'done', 'status=done');
  // 4 프롬프트 × 2 엔진 = 8건, 그중 추천·유명 프롬프트(2개)×2엔진 = 4건 언급
  assert(r.asked === 8, `질의 ${r.asked}건`);
  assert(r.mentionedCount === 4 && approx(r.citationRate, 4 / 8), `언급 ${r.mentionedCount}건, 인용률 ${(r.citationRate * 100).toFixed(0)}%`);
  assert(r.grade === 'B' && r.grade === G.gradeFromRate(4 / 8), `등급 ${r.grade}`);
  assert(r.perEngine.perplexity.asked === 4 && r.perEngine.openai.mentioned === 2, '엔진별 집계');
  assert(r.shareOfVoice != null && r.shareOfVoice > 0 && r.shareOfVoice < 1, `SoV ${(r.shareOfVoice * 100).toFixed(0)}%`);
  assert(r.competitors.some((c) => /미소플러스치과/.test(c.name)), '경쟁 병원 추출');
  assert(r.sentiment === 'positive', `감성=${r.sentiment}(추천·친절)`);
  assert(r.samples.length > 0 && /엔진|결과/.test(r.samples[0].excerpt), '샘플 발췌');

  console.log('== probe: 엔진 실패 가드 ==');
  const flaky = { availableEngines: () => ['perplexity'], async ask() { throw new Error('429 rate limit'); } };
  const rf = await G.probe(NAME, { category: '치과', region: '수성구', deps: { ai: flaky }, maxPrompts: 2 });
  assert(rf.status === 'done' && rf.asked === 0 && rf.errors.length === 2, '전건 실패해도 done + 에러 기록');
  assert(rf.citationRate === null && rf.grade === null, '유효 0건이면 수치 null(허위 없음)');

  console.log(fails ? `\n❌ ${fails}건 실패` : '\n✅ 전체 통과');
  process.exit(fails ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(1); });
