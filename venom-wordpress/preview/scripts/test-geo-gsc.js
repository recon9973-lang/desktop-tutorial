#!/usr/bin/env node
'use strict';

/**
 * lib/geo-gsc.js 오프라인 검증 — GSC rows → 메트릭 레코드 변환.
 * 실행:  node scripts/test-geo-gsc.js   (실패 시 exit 1)
 */

const G = require('../lib/geo-gsc.js');

let pass = 0, fail = 0;
function ok(name, cond) { cond ? (pass++, console.log('  ✓ ' + name)) : (fail++, console.error('  ✗ ' + name)); }

console.log('rowsToMetrics');
{
  const rows = [
    { keys: ['2026-07-01'], clicks: 10, impressions: 200, ctr: 0.05, position: 8.23 },
    { keys: ['2026-07-02'], clicks: 12, impressions: 240, ctr: 0.05, position: 7.5 },
  ];
  const recs = G.rowsToMetrics(rows, { clientId: 'pain', source: 'gsc' });
  ok('2일 × 4메트릭 = 8', recs.length === 8);
  const c1 = recs.find((r) => r.metricName === 'clicks' && r.metricDate === '2026-07-01');
  ok('clicks 값', c1 && c1.value === 10 && c1.source === 'gsc');
  ok('ctr 소수→% 변환', recs.find((r) => r.metricName === 'ctr' && r.metricDate === '2026-07-01').value === 5);
  ok('position 반올림(2)', recs.find((r) => r.metricName === 'position' && r.metricDate === '2026-07-01').value === 8.23);
  ok('id 결정적(중복방지)', c1.id === 'm_pain_clicks_2026-07-01');
}

console.log('방어');
{
  ok('clientId 필수', (() => { try { G.rowsToMetrics([], {}); return false; } catch { return true; } })());
  ok('빈 rows 안전', G.rowsToMetrics(null, { clientId: 'x' }).length === 0);
  // 잘못된 날짜 키 제외
  ok('비정상 날짜 제외', G.rowsToMetrics([{ keys: ['n/a'], clicks: 1 }], { clientId: 'x' }).length === 0);
  // date 필드 형태도 허용
  ok('date 필드 허용', G.rowsToMetrics([{ date: '2026-07-01', clicks: 3, impressions: 9, ctr: 0.33, position: 2 }], { clientId: 'x' }).length === 4);
}

console.log(`\n결과: ${pass} pass, ${fail} fail`);
process.exit(fail ? 1 : 0);
