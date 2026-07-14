#!/usr/bin/env node
'use strict';

/**
 * lib/geo-templates.js 오프라인 검증 — 템플릿 → Task 변환 + cap 클램프.
 * 실행:  node scripts/test-geo-templates.js   (실패 시 exit 1)
 */

const T = require('../lib/geo-templates.js');

let pass = 0, fail = 0;
function ok(name, cond) { cond ? (pass++, console.log('  ✓ ' + name)) : (fail++, console.error('  ✗ ' + name)); }

console.log('clampLevel (cap 상한)');
{
  ok('wikipedia cap C → A 강등', T.clampLevel('A', 'C') === 'C');
  ok('wikipedia cap C → B 강등', T.clampLevel('B', 'C') === 'C');
  ok('cap C → C 유지', T.clampLevel('C', 'C') === 'C');
  ok('cap C → D 유지(더 낮음)', T.clampLevel('D', 'C') === 'D');
  ok('cap A → A 유지', T.clampLevel('A', 'A') === 'A');
  ok('cap A → C 유지(더 낮음)', T.clampLevel('C', 'A') === 'C');
}

console.log('buildTasksFromTemplate (steps)');
{
  const wiki = {
    id: 'wikipedia', channelType: 'wikipedia', cap: 'C',
    steps: [
      { step: '계정 신뢰도', level: 'D', evidence: '스샷' },
      { step: '초안', level: 'C', evidence: '샌드박스' },
      { step: '게시', level: 'D', guard: '자동 금지' },
    ],
  };
  const tasks = T.buildTasksFromTemplate(wiki, 'pain');
  ok('단계 수만큼 Task', tasks.length === 3);
  ok('clientId 주입', tasks.every((t) => t.clientId === 'pain'));
  ok('templateId/taskType', tasks[0].templateId === 'wikipedia' && tasks[0].taskType === 'wikipedia');
  ok('title 조합', tasks[0].title === 'wikipedia · 계정 신뢰도');
  ok('상태 backlog', tasks.every((t) => t.status === 'backlog'));
  ok('guard 보존', tasks[2].guard === '자동 금지');
  ok('evidenceField 매핑', tasks[0].evidenceField === '스샷');

  // cap C 인 템플릿에 B 단계가 있으면 C 로 강등되어야
  const capped = T.buildTasksFromTemplate({ id: 'reddit', channelType: 'reddit', cap: 'C', steps: [{ step: 'x', level: 'B' }] }, 'c1');
  ok('cap 초과 단계 강등', capped[0].automationLevel === 'C' && capped[0].approvalStatus === 'none');
}

console.log('buildTasksFromTemplate (승인 큐 · variants · 방어)');
{
  // B 레벨(반자동)은 approvalStatus=pending
  const linkedin = T.buildTasksFromTemplate({ id: 'linkedin', channelType: 'linkedin', cap: 'B', steps: [{ step: 'Post', level: 'B' }, { step: '프로필', level: 'B' }] }, 'c1');
  ok('B레벨 승인 대기', linkedin.every((t) => t.approvalStatus === 'pending'));

  // variants(naver_ugc) 지원
  const naver = T.buildTasksFromTemplate({ id: 'naver_ugc', channelType: 'naver_blog', cap: 'B', variants: [
    { channelType: 'naver_blog', cap: 'B', step: '롱폼', level: 'B' },
    { channelType: 'naver_kin', cap: 'C', step: '지식인 답변', level: 'C' },
  ] }, 'c1');
  ok('variants → Task', naver.length === 2 && naver[1].channelType === 'naver_kin' && naver[1].automationLevel === 'C');

  ok('빈 입력 안전', T.buildTasksFromTemplate(null, 'c').length === 0 && T.buildTasksFromTemplate({ id: 'x' }, null).length === 0);
}

console.log('loadTemplates (실제 시드)');
(async () => {
  // 인메모리 백엔드로 시드 파일 읽기 흉내
  const fs = require('fs');
  const seed = JSON.parse(fs.readFileSync(__dirname + '/../content/geo/checklist-templates.json', 'utf8'));
  T._setBackend({ async getJsonFile() { return { content: seed }; } });
  const templates = await T.loadTemplates();
  ok('시드 템플릿 로드', templates.length === 10);
  const wiki = templates.find((x) => x.id === 'wikipedia');
  ok('wikipedia cap C', wiki && wiki.cap === 'C');
  const built = T.buildTasksFromTemplate(wiki, 'pain');
  ok('실제 wikipedia 게시 단계 D 유지', built.some((t) => /게시/.test(t.title) && t.automationLevel === 'D'));

  console.log(`\n결과: ${pass} pass, ${fail} fail`);
  process.exit(fail ? 1 : 0);
})();
