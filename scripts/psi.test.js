'use strict';

// node scripts/psi.test.js
const assert = require('assert');
const { parsePsi } = require('../lib/psi');

let pass = 0;
function test(n, fn){ try{ fn(); pass++; console.log('  ✓ '+n); }catch(e){ console.error('  ✗ '+n+'\n    '+e.message); process.exitCode=1; } }

const FIX = {
  id: 'https://example.com/',
  loadingExperience: { metrics: {
    LARGEST_CONTENTFUL_PAINT_MS: { percentile: 2100, category: 'AVERAGE' },
    CUMULATIVE_LAYOUT_SHIFT_SCORE: { percentile: 5, category: 'GOOD' },
  } },
  lighthouseResult: {
    finalUrl: 'https://example.com/',
    configSettings: { formFactor: 'mobile' },
    categories: {
      performance: { score: 0.92 }, seo: { score: 1 },
      accessibility: { score: 0.88 }, 'best-practices': { score: 0.95 },
    },
    audits: {
      'largest-contentful-paint': { numericValue: 2450.7 },
      'cumulative-layout-shift': { numericValue: 0.03 },
      'total-blocking-time': { numericValue: 120 },
      'first-contentful-paint': { numericValue: 1100 },
      'speed-index': { numericValue: 3000 },
    },
  },
};

test('parsePsi: 카테고리 점수 0~100 변환', () => {
  const r = parsePsi(FIX);
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.scores.performance, 92);
  assert.strictEqual(r.scores.seo, 100);
  assert.strictEqual(r.scores.accessibility, 88);
  assert.strictEqual(r.scores.bestPractices, 95);
});

test('parsePsi: 랩 지표 추출', () => {
  const r = parsePsi(FIX);
  assert.strictEqual(Math.round(r.lab.lcpMs), 2451);
  assert.strictEqual(r.lab.cls, 0.03);
  assert.strictEqual(r.lab.tbtMs, 120);
  assert.strictEqual(r.lab.inpMs, null); // 없는 지표는 null
});

test('parsePsi: 필드데이터(CrUX) 추출', () => {
  const r = parsePsi(FIX);
  assert.strictEqual(r.field.lcp.p75, 2100);
  assert.strictEqual(r.field.cls.category, 'GOOD');
});

test('parsePsi: 에러/빈 응답 안전 처리', () => {
  assert.strictEqual(parsePsi(null).ok, false);
  assert.strictEqual(parsePsi({ error: { message: 'quota' } }).ok, false);
  assert.strictEqual(parsePsi({}).ok, false);
});

console.log(`\n${pass} passed`);
