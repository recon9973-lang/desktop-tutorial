#!/usr/bin/env node
'use strict';

/**
 * lib/geo-report.js 오프라인 검증 — 규칙 기반 주간 리포트 생성(결정적).
 * 실행:  node scripts/test-geo-report.js   (실패 시 exit 1)
 */

const R = require('../lib/geo-report.js');

let pass = 0, fail = 0;
function ok(name, cond) { cond ? (pass++, console.log('  ✓ ' + name)) : (fail++, console.error('  ✗ ' + name)); }
const has = (arr, sub) => arr.some((x) => x.includes(sub));

console.log('improved (position 역방향)');
{
  ok('clicks 증가=개선', R.improved('clicks', 5) === true);
  ok('clicks 감소=악화', R.improved('clicks', -5) === false);
  ok('position 감소=개선', R.improved('position', -1.2) === true);
  ok('position 증가=악화', R.improved('position', 1.2) === false);
  ok('delta null', R.improved('clicks', null) === null);
}

console.log('taskStats');
{
  const s = R.taskStats([{ status: 'done' }, { status: 'done' }, { status: 'doing' }, { status: 'failed' }, { status: 'review', approvalStatus: 'pending' }]);
  ok('완료율', s.total === 5 && s.done === 2 && s.completionRate === 40);
  ok('승인대기/실패', s.approvalPending === 1 && s.failed === 1);
}

console.log('buildReport');
{
  const rep = R.buildReport({
    client: { id: 'pain', name: '시원통증', region: '포항', industry: '통증의학' },
    period: '2026-W28',
    metricsSummary: [
      { metricName: 'clicks', latest: 150, prev: 120, delta: 30 },
      { metricName: 'position', latest: 7.4, prev: 8.2, delta: -0.8 },
      { metricName: 'impressions', latest: 3000, prev: 3200, delta: -200 },
    ],
    exposure: { tot_pct: 25, disc_pct: 0, errors: 2 },
    tasks: [{ status: 'done' }, { status: 'doing' }, { status: 'failed' }, { status: 'review', approvalStatus: 'pending' }],
  }, '2026-07-14T00:00:00.000Z');

  ok('id/clientId/period', rep.id === 'rpt_pain_2026-W28' && rep.clientId === 'pain' && rep.reportPeriod === '2026-W28');
  ok('clicks 개선 → win', has(rep.keyWins, '클릭 개선'));
  ok('position 개선(하락) → win', has(rep.keyWins, '평균순위 개선'));
  ok('impressions 악화 → risk', has(rep.risks, '노출 악화'));
  ok('발견형 0% → risk', has(rep.risks, '발견형(신환) 질문에서 AI 미노출'));
  ok('발견형 0% → nextAction 콘텐츠', has(rep.nextActions, '질문형 콘텐츠'));
  ok('측정불가 → risk', has(rep.risks, '측정불가 2건'));
  ok('승인대기 → nextAction', has(rep.nextActions, '승인 대기 업무 1건'));
  ok('실패 → risk', has(rep.risks, '실패/재작업 업무 1건'));
  ok('완료율 → win', has(rep.keyWins, '업무 완료율 25%'));
  ok('summary 조합', rep.summary.includes('시원통증') && rep.summary.includes('AI 노출 전체 25%'));
  ok('generatedAt 주입', rep.generatedAt === '2026-07-14T00:00:00.000Z');
  ok('data 원본 보존', rep.data.taskStats.total === 4 && rep.data.exposure.tot_pct === 25);
}

console.log('buildReport — 실측/업무 없음');
{
  const rep = R.buildReport({ client: { id: 'skin', name: '스킨' }, period: 'W1', metricsSummary: [], exposure: null, tasks: [] });
  ok('실측 없음 안내', has(rep.nextActions, 'AI 인용 실측 미실행'));
  ok('업무 없음 안내', has(rep.nextActions, '플레이북에서 업무 생성'));
  ok('빈 상태도 리포트 생성', !!rep.summary && Array.isArray(rep.keyWins));
}

console.log(`\n결과: ${pass} pass, ${fail} fail`);
process.exit(fail ? 1 : 0);
