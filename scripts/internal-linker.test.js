'use strict';

// 의존성 없는 경량 테스트 러너:  node scripts/internal-linker.test.js
const assert = require('assert');
const L = require('../lib/internal-linker');

let pass = 0;
function test(name, fn) {
  try { fn(); pass++; console.log('  ✓ ' + name); }
  catch (e) { console.error('  ✗ ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

const posts = [
  { id: 'a', slug: 'dental-implant-daegu', cat: 'dental', region: '대구', status: 'published',
    title: '대구 임플란트 마케팅 전략', seoTitle: '대구 임플란트 광고', keywords: '대구, 임플란트, 치과, 마케팅', html: '<p>본문 A</p>' },
  { id: 'b', slug: 'dental-implant-cost', cat: 'dental', region: '대구', status: 'published',
    title: '임플란트 비용과 환자 유치', seoTitle: '임플란트 신환 유치', keywords: '임플란트, 치과, 비용, 환자', html: '<p>본문 B</p>' },
  { id: 'c', slug: 'seo-daejeon', cat: 'seo', region: '대전', status: 'published',
    title: '대전 SEO 마케팅 5가지', seoTitle: '대전 SEO 전략', keywords: '대전, SEO, 검색, C-Rank', html: '<p>본문 C</p>' },
  { id: 'd', slug: 'draft-hidden', cat: 'seo', region: '', status: 'draft',
    title: '임시 글', seoTitle: '', keywords: 'SEO, 임플란트', html: '<p>draft</p>' },
];

test('draft는 제외된다', () => {
  const r = L.suggestLinks(posts);
  assert.strictEqual(r.stats.posts, 3, '발행 글만 3개여야 함');
  assert.ok(!r.suggestions.find((s) => s.id === 'd'), 'draft가 제안에 없어야 함');
});

test('관련도: 같은 cat+region+키워드 겹치는 A↔B가 서로 최상위', () => {
  const r = L.suggestLinks(posts, { perPost: 2 });
  const a = r.suggestions.find((s) => s.id === 'a');
  assert.strictEqual(a.links[0].targetId, 'b', 'A의 1순위는 B여야 함');
});

test('관련 없는 글은 minScore로 걸러진다', () => {
  const r = L.suggestLinks(posts, { minScore: 0.9 });
  const total = r.suggestions.reduce((n, s) => n + s.links.length, 0);
  assert.strictEqual(total, 0, '높은 임계에서는 추천 0');
});

test('앵커 다양화: 한 출처에서 동일 앵커 중복 없음', () => {
  const r = L.suggestLinks(posts, { perPost: 4, minScore: 0 });
  for (const s of r.suggestions) {
    const anchors = s.links.map((l) => l.anchor.toLowerCase());
    assert.strictEqual(new Set(anchors).size, anchors.length, `${s.id}에서 앵커 중복`);
  }
});

test('고아 글 탐지: 아무도 안 가리키면 orphan', () => {
  const lonely = [
    { id: 'x', slug: 'x', cat: 'a', title: '고립된 주제 알파', keywords: '알파, 베타', status: 'published', html: '' },
    { id: 'y', slug: 'y', cat: 'b', title: '완전 다른 감마', keywords: '감마, 델타', status: 'published', html: '' },
  ];
  const r = L.suggestLinks(lonely, { minScore: 0.5 });
  assert.strictEqual(r.stats.orphanCount, 2);
});

test('injectRelatedBlock은 idempotent(두 번 넣어도 블록 1개)', () => {
  const links = [{ url: './?p=b', anchor: '임플란트 비용과 환자 유치' }];
  let html = '<p>본문</p>';
  html = L.injectRelatedBlock(html, links);
  html = L.injectRelatedBlock(html, links);
  const count = (html.match(/growthops:related:start/g) || []).length;
  assert.strictEqual(count, 1, '관련 블록은 정확히 1개');
  assert.ok(html.includes('함께 보면 좋은 글'));
});

test('removeRelatedBlock으로 깨끗이 제거', () => {
  const links = [{ url: './?p=b', anchor: 'B' }];
  const injected = L.injectRelatedBlock('<p>본문</p>', links);
  const cleaned = L.removeRelatedBlock(injected);
  assert.ok(!cleaned.includes('growthops:related'));
  assert.ok(cleaned.includes('<p>본문</p>'));
});

test('HTML 이스케이프: 앵커의 <,& 안전 처리', () => {
  const block = L.buildRelatedBlock([{ url: './?p=z', anchor: 'A & B <스크립트>' }]);
  assert.ok(block.includes('A &amp; B &lt;스크립트&gt;'));
});

console.log(`\n${pass} passed`);
