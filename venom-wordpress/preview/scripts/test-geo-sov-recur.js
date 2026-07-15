#!/usr/bin/env node
'use strict';

/**
 * lib/geo-sov.js + lib/geo-recur.js 오프라인 검증.
 * 실행:  node scripts/test-geo-sov-recur.js   (실패 시 exit 1)
 */

const SOV = require('../lib/geo-sov.js');
const REC = require('../lib/geo-recur.js');

let pass = 0, fail = 0;
function ok(name, cond) { cond ? (pass++, console.log('  ✓ ' + name)) : (fail++, console.error('  ✗ ' + name)); }

console.log('geo-sov · mentions');
{
  ok('부분일치·공백무시', JSON.stringify(SOV.mentions('포항 A정형외과 와 B통증 추천', ['A정형외과', 'C피부과'])) === JSON.stringify(['A정형외과']));
  ok('빈 텍스트', SOV.mentions('', ['A']).length === 0);
  ok('빈 이름', SOV.mentions('텍스트', []).length === 0);
}

console.log('geo-sov · buildSov');
{
  const cells = [
    { selfHit: true, compHits: [] },
    { selfHit: false, compHits: ['A정형외과'] },
    { selfHit: true, compHits: ['A정형외과', 'B통증'] },
    { selfHit: false, compHits: [] },
  ];
  const s = SOV.buildSov(cells);
  ok('self 집계', s.selfMentions === 2);
  ok('경쟁사 집계', s.totalComp === 3 && s.compMentions['A정형외과'] === 2 && s.compMentions['B통증'] === 1);
  ok('SOV% = self/(self+comp)', s.sovPct === 40); // 2/(2+3)=40%
  ok('아무 언급 없으면 null', SOV.buildSov([{ selfHit: false, compHits: [] }]).sovPct === null);
  ok('빈 입력 안전', SOV.buildSov(null).sovPct === null);
}

console.log('geo-recur · dueRecurrences');
{
  const tasks = [
    { id: 's1', clientId: 'pain', templateId: 'linkedin', channelType: 'linkedin', title: 'LinkedIn 주간 포스트', automationLevel: 'B', recurrenceRule: 'weekly' },
    { id: 's2', clientId: 'pain', templateId: 'gsc', channelType: 'gsc', title: '색인 점검', automationLevel: 'A', recurrenceRule: 'weekly' },
    { id: 'x1', clientId: 'pain', title: '일회성', status: 'done' }, // 반복 아님
  ];
  const due = REC.dueRecurrences(tasks, '2026-W28');
  ok('반복 시드만 생성', due.length === 2);
  ok('period 태그', due.every((t) => t.period === '2026-W28'));
  ok('B레벨 승인대기', due.find((t) => t.templateId === 'linkedin').approvalStatus === 'pending');
  ok('thisweek 상태', due.every((t) => t.status === 'thisweek'));

  // 이미 이번 주 인스턴스가 있으면 중복 생성 안 함
  const withInstance = tasks.concat([{ id: 'i1', clientId: 'pain', templateId: 'linkedin', channelType: 'linkedin', title: 'LinkedIn 주간 포스트', period: '2026-W28' }]);
  const due2 = REC.dueRecurrences(withInstance, '2026-W28');
  ok('기존 인스턴스 중복 방지', due2.length === 1 && due2[0].templateId === 'gsc');

  ok('period 없으면 빈 결과', REC.dueRecurrences(tasks, '').length === 0);
  ok('다음 주기엔 다시 생성', REC.dueRecurrences(withInstance, '2026-W29').length === 2);
}

console.log(`\n결과: ${pass} pass, ${fail} fail`);
process.exit(fail ? 1 : 0);
