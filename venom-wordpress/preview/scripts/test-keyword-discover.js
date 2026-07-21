'use strict';

// 키워드 발굴기 코어 회귀 테스트 (네트워크 X — 순수 로직 + 핸들러 오케스트레이션 목 검증)
//   node scripts/test-keyword-discover.js
// 검증: ① 조합 시드 생성 ② 티어 분류(목표 실사용 키워드) ③ 노이즈 제외
//       ④ 기회점수 랭킹 ⑤ 핸들러 end-to-end(검색광고 목) ⑥ graceful 폴백

const assert = require('assert');
const path = require('path');
const kd = require(path.join(__dirname, '..', 'lib', 'keyword-discover'));

let pass = 0;
function ok(name, cond) { assert.ok(cond, name); console.log('  ✓ ' + name); pass++; }

console.log('① 조합 시드');
const b = kd.buildSeeds('대구', '한의원');
const seedKw = b.seeds.map((s) => s.kw);
ok('대표 조합 대구한의원 포함', seedKw.indexOf('대구한의원') >= 0);
ok('세부지역 대구북구한의원 포함', seedKw.indexOf('대구북구한의원') >= 0);
ok('증상 조합 대구교통사고한의원 포함', seedKw.indexOf('대구교통사고한의원') >= 0);
ok('시술 단독 대구추나 포함', seedKw.indexOf('대구추나') >= 0);
ok('sub가 지역명 포함 시 중복 방지(동대구역한의원)', kd.buildSeeds('대구', '한의원', { maxSub: 12 }).seeds.some((s) => s.kw === '동대구역한의원'));

console.log('② 분류(목표 실사용 키워드)');
const ctx = b.ctx;
ok('대구한의원 → representative', kd.classify('대구한의원', ctx) === 'representative');
ok('대구북구한의원 → subregion', kd.classify('대구북구한의원', ctx) === 'subregion');
ok('대구교통사고한의원 → procedure', kd.classify('대구교통사고한의원', ctx) === 'procedure');
ok('대구통증치료 → procedure', kd.classify('대구통증치료', ctx) === 'procedure');
ok('대구다이어트한의원 → procedure', kd.classify('대구다이어트한의원', ctx) === 'procedure');

console.log('③ 노이즈 제외');
ok('대구맛집 → null(진료과 무관)', kd.classify('대구맛집', ctx) === null);
ok('한의원 → null(지역 무관)', kd.classify('한의원', ctx) === null);
ok('서울성형외과 → null(지역 불일치)', kd.classify('서울성형외과', ctx) === null);

console.log('④ 기회점수 랭킹(검색량÷경쟁)');
const tiers = kd.rankTiers([
  { keyword: '대구다이어트한의원', volume: 800, compIdx: '낮음', tier: 'procedure' },
  { keyword: '대구교통사고한의원', volume: 1200, compIdx: '중간', tier: 'procedure' },
  { keyword: '검색량0', volume: 0, compIdx: '낮음', tier: 'procedure' },
]);
ok('검색량0 제외', tiers.procedure.every((x) => x.volume > 0));
ok('낮은경쟁(800/낮음=800)이 높은검색량(1200/중간=600)보다 상위', tiers.procedure[0].keyword === '대구다이어트한의원');

console.log('⑤ 핸들러 end-to-end (검색광고 목)');
const sa = require(path.join(__dirname, '..', 'lib', 'naver-searchad'));
const sample = {
  '대구한의원': { v: 5300, c: '높음' }, '대구북구한의원': { v: 720, c: '낮음' },
  '대구교통사고한의원': { v: 1400, c: '중간' }, '대구다이어트한의원': { v: 880, c: '낮음' },
  '대구통증치료': { v: 150, c: '낮음' }, '한의원': { v: 9000, c: '높음' }, '대구맛집': { v: 50000, c: '높음' },
};
sa.fetchKeywordTool = function () {
  const list = Object.keys(sample).map((k) => ({
    relKeyword: k, monthlyPcQcCnt: Math.round(sample[k].v * 0.4),
    monthlyMobileQcCnt: Math.round(sample[k].v * 0.6), compIdx: sample[k].c,
  }));
  return Promise.resolve({ status: 200, configured: true, keywordList: list, json: { keywordList: list } });
};
sa.isConfigured = function () { return true; };
require.cache[require.resolve(path.join(__dirname, '..', 'lib', 'keyword-research'))] = {
  exports: { researchKeywords: function () { return Promise.resolve({ related: [] }); } },
};
const handler = require(path.join(__dirname, '..', 'api', 'keyword-discover'));
function mockRes() { const o = { _s: 200, _j: null }; o.setHeader = () => {}; o.status = (s) => { o._s = s; return o; }; o.json = (j) => { o._j = j; return o; }; o.end = () => o; return o; }

(async () => {
  const res = mockRes();
  await handler({ method: 'GET', query: { region: '대구', dept: '한의원' } }, res);
  ok('200 OK', res._s === 200 && res._j.ok === true);
  const j = JSON.stringify(res._j);
  ['대구한의원', '대구북구한의원', '대구교통사고한의원', '대구다이어트한의원'].forEach((k) => ok('결과에 ' + k + ' 포함', j.indexOf(k) >= 0));
  ok('노이즈 대구맛집 제외', j.indexOf('대구맛집') < 0);
  ok('bare 한의원 flat 제외', res._j.flat.every((x) => x.keyword !== '한의원'));

  console.log('⑥ graceful 폴백(미설정)');
  sa.fetchKeywordTool = () => Promise.resolve({ status: 501, configured: false, keywordList: null, json: null });
  sa.isConfigured = () => false;
  const r2 = mockRes();
  await handler({ method: 'GET', query: { region: '대구', dept: '한의원' } }, r2);
  ok('폴백 200 + seeds 노출', r2._s === 200 && r2._j.ok === false && (r2._j.seeds || []).length > 0);
  const r3 = mockRes();
  await handler({ method: 'GET', query: { region: '대구' } }, r3);
  ok('파라미터 누락 400', r3._s === 400);

  console.log('\n통과: ' + pass + '개');
})().catch((e) => { console.error('✗ 실패:', e.message); process.exit(1); });
