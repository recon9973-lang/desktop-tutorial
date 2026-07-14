#!/usr/bin/env node
'use strict';

/**
 * lib/geo-metrics.js 오프라인 검증 — CSV 파싱·정규화·시계열·요약.
 * 실행:  node scripts/test-geo-metrics.js   (실패 시 exit 1)
 */

const M = require('../lib/geo-metrics.js');

let pass = 0, fail = 0;
function ok(name, cond) { cond ? (pass++, console.log('  ✓ ' + name)) : (fail++, console.error('  ✗ ' + name)); }

console.log('parseCsv / splitCsvLine');
{
  ok('따옴표 내 콤마', JSON.stringify(M.splitCsvLine('a,"1,234",b')) === JSON.stringify(['a', '1,234', 'b']));
  const p = M.parseCsv('Date,Clicks\n2026-07-01,10\n2026-07-02,20');
  ok('헤더/행', p.headers.length === 2 && p.rows.length === 2 && p.rows[0].Clicks === '10');
  ok('빈 텍스트 안전', M.parseCsv('').rows.length === 0);
}

console.log('normDate / toNum');
{
  ok('ISO 통과', M.normDate('2026-07-01') === '2026-07-01');
  ok('슬래시 변환', M.normDate('2026/7/1') === '2026-07-01');
  ok('잘못된 날짜 null', M.normDate('없음') === null);
  ok('숫자 콤마/% 제거', M.toNum('"1,234"') === 1234 && M.toNum('3.5%') === 3.5);
}

console.log('csvToMetrics (GSC Dates 형식)');
{
  const csv = 'Date,Clicks,Impressions,CTR,Position\n2026-07-01,10,100,"10%",5.2\n2026-07-02,20,150,13%,4.1';
  const recs = M.csvToMetrics(csv, { clientId: 'pain', source: 'gsc' });
  ok('날짜×메트릭 전개', recs.length === 8); // 2일 × 4메트릭
  const c1 = recs.find((r) => r.metricName === 'clicks' && r.metricDate === '2026-07-01');
  ok('clicks 매핑', c1 && c1.value === 10 && c1.source === 'gsc');
  ok('CTR % 제거', recs.find((r) => r.metricName === 'ctr' && r.metricDate === '2026-07-02').value === 13);
  ok('id 결정적(중복방지)', c1.id === 'm_pain_clicks_2026-07-01');
  ok('clientId 필수', (() => { try { M.csvToMetrics(csv, {}); return false; } catch { return true; } })());
}

console.log('csvToMetrics (한글/일반형)');
{
  const kor = '날짜,클릭,노출\n2026-07-01,5,50';
  const r1 = M.csvToMetrics(kor, { clientId: 'skin' });
  ok('한글 헤더 매핑', r1.length === 2 && r1.find((r) => r.metricName === 'clicks').value === 5);

  const generic = 'metricName,metricDate,value\nsessions,2026-07-01,42\nconversions,2026-07-01,3';
  const r2 = M.csvToMetrics(generic, { clientId: 'skin' });
  ok('일반형 파싱', r2.length === 2 && r2.find((r) => r.metricName === 'sessions').value === 42);
}

console.log('seriesFrom / summarize');
{
  const metrics = [
    { clientId: 'pain', metricName: 'clicks', metricDate: '2026-07-02', value: 20 },
    { clientId: 'pain', metricName: 'clicks', metricDate: '2026-07-01', value: 10 },
    { clientId: 'pain', metricName: 'clicks', metricDate: '2026-07-03', value: 35 },
    { clientId: 'pain', metricName: 'impressions', metricDate: '2026-07-03', value: 300 },
    { clientId: 'skin', metricName: 'clicks', metricDate: '2026-07-03', value: 99 },
  ];
  const s = M.seriesFrom(metrics, { clientId: 'pain', metricName: 'clicks' });
  ok('시계열 정렬·필터', s.length === 3 && s[0].date === '2026-07-01' && s[2].value === 35);
  const sum = M.summarize(metrics, { clientId: 'pain' });
  const clk = sum.find((x) => x.metricName === 'clicks');
  ok('요약 최신값', clk.latest === 35 && clk.date === '2026-07-03');
  ok('요약 delta', clk.delta === 15); // 35 - 20
  ok('메트릭 2종', sum.length === 2);
  ok('타 거래처 격리', !sum.find((x) => x.latest === 99));
}

console.log(`\n결과: ${pass} pass, ${fail} fail`);
process.exit(fail ? 1 : 0);
