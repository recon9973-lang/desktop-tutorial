#!/usr/bin/env node
'use strict';

/**
 * api/geo-ops.js 오프라인 검증 — 배포 없이 mock req/res + 인메모리 백엔드로 라우팅/인증/집계 확인.
 * 실행:  node scripts/test-geo-ops-api.js   (실패 시 exit 1)
 *
 * 커버: module 라우팅, GET list/get, POST upsert/delete/move, 인증 게이트(ADMIN_SECRET),
 *       dashboard 집계, unknown module/action 처리.
 */

const geo = require('../lib/geo-store.js');
const tpl = require('../lib/geo-templates.js');
const handler = require('../api/geo-ops.js');

let pass = 0, fail = 0;
function ok(name, cond) { cond ? (pass++, console.log('  ✓ ' + name)) : (fail++, console.error('  ✗ ' + name)); }

function makeBackend() {
  const files = {};
  return {
    async getFile(p) { return files[p] ? { sha: files[p].sha, content: JSON.parse(JSON.stringify(files[p].content)) } : null; },
    async getJsonFile(p, fb) { return { content: files[p] ? JSON.parse(JSON.stringify(files[p].content)) : (fb || {}) }; },
    async putFile(p, content, sha, msg) { files[p] = { sha: 's' + Math.random().toString(36).slice(2, 7), content: JSON.parse(JSON.stringify(content)) }; return { ok: true }; },
    async withConflictRetry(op) { return op(); },
  };
}

// mock req/res
function mockReq({ method = 'GET', query = {}, body = null, auth = null } = {}) {
  return { method, query, body, headers: auth ? { authorization: 'Bearer ' + auth } : {} };
}
function mockRes() {
  const r = { _status: 200, _json: null, headers: {} };
  r.setHeader = (k, v) => { r.headers[k] = v; };
  r.status = (s) => { r._status = s; return r; };
  r.json = (j) => { r._json = j; return r; };
  r.end = () => r;
  return r;
}
async function call(opts) { const res = mockRes(); await handler(mockReq(opts), res); return res; }

(async () => {
  geo._setBackend(makeBackend());
  delete process.env.ADMIN_SECRET; // 인증 미설정 경로 먼저

  console.log('엔티티 CRUD 라우팅');
  {
    let res = await call({ method: 'POST', query: { module: 'clients', action: 'upsert' }, body: { client: { id: 'pain', name: '시원통증', active: true, lifecycleStage: '최적화' } } });
    ok('clients upsert 200', res._status === 200 && res._json.ok && res._json.data.id === 'pain');

    await call({ method: 'POST', query: { module: 'clients', action: 'upsert' }, body: { client: { id: 'skin', name: '시원스킨', active: false, lifecycleStage: '기반구축' } } });

    res = await call({ method: 'GET', query: { module: 'clients', action: 'list' } });
    ok('clients list 2건', res._json.count === 2);

    res = await call({ method: 'GET', query: { module: 'clients', action: 'list', active: 'true' } });
    ok('clients list 필터 active=1', res._json.count === 1 && res._json.data[0].id === 'pain');

    res = await call({ method: 'GET', query: { module: 'clients', action: 'get', id: 'pain' } });
    ok('clients get 단건', res._status === 200 && res._json.data.name === '시원통증');

    res = await call({ method: 'GET', query: { module: 'clients', action: 'get', id: 'none' } });
    ok('clients get 404', res._status === 404 && res._json.ok === false);
  }

  console.log('tasks move(칸반)');
  {
    await call({ method: 'POST', query: { module: 'tasks', action: 'upsert' }, body: { task: { id: 't1', clientId: 'pain', title: '위키 초안', status: 'backlog' } } });
    let res = await call({ method: 'POST', query: { module: 'tasks', action: 'move' }, body: { id: 't1', to: 'doing' } });
    ok('tasks move 성공', res._json.ok && res._json.data.status === 'doing');
    res = await call({ method: 'POST', query: { module: 'tasks', action: 'move' }, body: { id: 't1', to: '이상한상태' } });
    ok('tasks move 잘못된 상태 400', res._status === 400);
  }

  console.log('dashboard 집계');
  {
    await call({ method: 'POST', query: { module: 'channels', action: 'upsert' }, body: { channel: { id: 'ch1', clientId: 'pain', channelType: 'gsc', healthStatus: '오류', riskLevel: 'high' } } });
    const res = await call({ method: 'GET', query: { module: 'dashboard' } });
    const d = res._json.data;
    ok('dashboard clientsTotal', d.clientsTotal === 2);
    ok('dashboard clientsActive', d.clientsActive === 1);
    ok('dashboard riskCount', d.riskCount === 1);
    ok('dashboard lifecycleBreakdown', d.lifecycleBreakdown['최적화'] === 1 && d.lifecycleBreakdown['기반구축'] === 1);
  }

  console.log('delete / unknown');
  {
    let res = await call({ method: 'POST', query: { module: 'clients', action: 'delete' }, body: { id: 'skin' } });
    ok('clients delete', res._json.ok && res._json.removed === true);
    ok('삭제 후 1건', (await call({ method: 'GET', query: { module: 'clients', action: 'list' } }))._json.count === 1);

    res = await call({ method: 'GET', query: { module: 'nope' } });
    ok('unknown module 400', res._status === 400);
    res = await call({ method: 'POST', query: { module: 'clients', action: 'weird' }, body: {} });
    ok('unknown action 400', res._status === 400);
  }

  console.log('templates 모듈 + tasks generate/approve');
  {
    // geo-templates 백엔드 주입(작은 시드)
    const seed = { templates: [
      { id: 'wikipedia', channelType: 'wikipedia', cap: 'C', steps: [{ step: '초안', level: 'C' }, { step: '게시', level: 'D', guard: '자동금지' }] },
      { id: 'linkedin', channelType: 'linkedin', cap: 'B', steps: [{ step: 'Post', level: 'B' }] },
    ] };
    tpl._setBackend({ async getJsonFile() { return { content: seed }; } });

    let res = await call({ method: 'GET', query: { module: 'templates' } });
    ok('templates list', res._json.ok && res._json.count === 2 && res._json.data[0].steps === 2);

    res = await call({ method: 'POST', query: { module: 'tasks', action: 'generate' }, body: { clientId: 'pain', templateId: 'wikipedia' } });
    ok('generate 2 Task', res._json.ok && res._json.count === 2);
    ok('generate 게시단계 D 유지', res._json.data.some((t) => /게시/.test(t.title) && t.automationLevel === 'D'));

    res = await call({ method: 'POST', query: { module: 'tasks', action: 'generate' }, body: { clientId: 'pain', templateId: 'linkedin' } });
    const bTask = res._json.data[0];
    ok('linkedin B단계 승인대기', bTask.approvalStatus === 'pending' && bTask.status === 'backlog');

    // 승인 → thisweek
    res = await call({ method: 'POST', query: { module: 'tasks', action: 'approve' }, body: { id: bTask.id, decision: 'approved' } });
    ok('approve → thisweek', res._json.ok && res._json.data.approvalStatus === 'approved' && res._json.data.status === 'thisweek');

    // 반려 → hold
    res = await call({ method: 'POST', query: { module: 'tasks', action: 'generate' }, body: { clientId: 'skin2', templateId: 'linkedin' } });
    const rTask = res._json.data[0];
    res = await call({ method: 'POST', query: { module: 'tasks', action: 'approve' }, body: { id: rTask.id, decision: 'rejected' } });
    ok('reject → hold', res._json.data.approvalStatus === 'rejected' && res._json.data.status === 'hold');

    res = await call({ method: 'POST', query: { module: 'tasks', action: 'generate' }, body: { clientId: 'pain' } });
    ok('generate templateId 누락 400', res._status === 400);
    res = await call({ method: 'POST', query: { module: 'tasks', action: 'generate' }, body: { clientId: 'pain', templateId: 'nope' } });
    ok('generate 없는 템플릿 404', res._status === 404);

    // 생성된 Task 가 tasks 컬렉션에 존재(clientId 필터)
    res = await call({ method: 'GET', query: { module: 'tasks', action: 'list', clientId: 'pain' } });
    ok('pain Task 목록 누적', res._json.count >= 3);
  }

  console.log('metrics ingest/series/summary');
  {
    // CSV 적재
    const csv = 'Date,Clicks,Impressions\n2026-07-01,10,100\n2026-07-02,20,150';
    let res = await call({ method: 'POST', query: { module: 'metrics', action: 'ingest' }, body: { clientId: 'pain', source: 'gsc', csv } });
    ok('metrics ingest CSV', res._json.ok && res._json.count === 4);

    res = await call({ method: 'GET', query: { module: 'metrics', action: 'series', clientId: 'pain', metricName: 'clicks' } });
    ok('metrics series 정렬', res._json.ok && res._json.data.length === 2 && res._json.data[0].date === '2026-07-01' && res._json.data[1].value === 20);

    res = await call({ method: 'GET', query: { module: 'metrics', action: 'summary', clientId: 'pain' } });
    const clk = res._json.data.find((x) => x.metricName === 'clicks');
    ok('metrics summary delta', clk.latest === 20 && clk.delta === 10);

    // 재적재 시 중복 없이 덮어씀(같은 날짜 값 갱신)
    res = await call({ method: 'POST', query: { module: 'metrics', action: 'ingest' }, body: { clientId: 'pain', source: 'gsc', csv: 'Date,Clicks\n2026-07-02,25' } });
    res = await call({ method: 'GET', query: { module: 'metrics', action: 'series', clientId: 'pain', metricName: 'clicks' } });
    ok('재적재 중복없이 갱신', res._json.data.length === 2 && res._json.data[1].value === 25);

    // rows 배열 경로
    res = await call({ method: 'POST', query: { module: 'metrics', action: 'ingest' }, body: { clientId: 'pain', rows: [{ metricName: 'sessions', metricDate: '2026-07-02', value: 42 }] } });
    ok('metrics ingest rows', res._json.ok && res._json.count === 1);

    res = await call({ method: 'POST', query: { module: 'metrics', action: 'ingest' }, body: { source: 'x', csv: 'a' } });
    ok('clientId 누락 400', res._status === 400);
  }

  console.log('metrics collect (GSC 자동수집, SC 목킹)');
  {
    const SC = require('../lib/search-console.js');
    const _isConf = SC.isConfigured, _query = SC.querySearchAnalytics;

    // gscProperty 없는 거래처 → configured:false
    await call({ method: 'POST', query: { module: 'clients', action: 'upsert' }, body: { client: { id: 'pain', name: '시원통증', active: true } } });
    let res = await call({ method: 'POST', query: { module: 'metrics', action: 'collect' }, body: { clientId: 'pain' } });
    ok('gscProperty 미설정 configured:false', res._json.ok === false && res._json.configured === false);

    // gscProperty 설정 + SC 목킹
    await call({ method: 'POST', query: { module: 'clients', action: 'upsert' }, body: { client: { id: 'pain', name: '시원통증', active: true, gscProperty: 'sc-domain:example.com' } } });
    SC.isConfigured = () => false;
    res = await call({ method: 'POST', query: { module: 'metrics', action: 'collect' }, body: { clientId: 'pain' } });
    ok('자격증명 미설정 configured:false', res._json.configured === false);

    SC.isConfigured = () => true;
    SC.querySearchAnalytics = async () => ({ ok: true, rows: [
      { keys: ['2026-07-01'], clicks: 10, impressions: 200, ctr: 0.05, position: 8 },
      { keys: ['2026-07-02'], clicks: 14, impressions: 220, ctr: 0.06, position: 7 },
    ] });
    res = await call({ method: 'POST', query: { module: 'metrics', action: 'collect' }, body: { clientId: 'pain', days: 14 } });
    ok('collect 적재(2일×4=8)', res._json.ok && res._json.count === 8);

    res = await call({ method: 'GET', query: { module: 'metrics', action: 'summary', clientId: 'pain' } });
    ok('collect 후 summary clicks', res._json.data.find((x) => x.metricName === 'clicks').latest === 14);
    ok('collect 후 ctr %', res._json.data.find((x) => x.metricName === 'ctr').latest === 6);

    // GSC 쿼리 실패 → 502
    SC.querySearchAnalytics = async () => ({ ok: false, reason: 'GSC 쿼리 실패: 403' });
    res = await call({ method: 'POST', query: { module: 'metrics', action: 'collect' }, body: { clientId: 'pain' } });
    ok('GSC 실패 502', res._status === 502);

    SC.isConfigured = _isConf; SC.querySearchAnalytics = _query; // 복원
  }

  console.log('report generate/list/get');
  {
    // pain 거래처는 앞 블록에서 생성됨 + metrics/tasks 존재
    let res = await call({ method: 'POST', query: { module: 'report', action: 'generate' }, body: { clientId: 'pain', period: '2026-W28' } });
    ok('report generate 200', res._json.ok && res._json.data.clientId === 'pain');
    ok('report id 규칙', res._json.data.id === 'rpt_pain_2026-W28');
    ok('report 구조', Array.isArray(res._json.data.keyWins) && Array.isArray(res._json.data.nextActions) && typeof res._json.data.summary === 'string');
    const rid = res._json.data.id;

    res = await call({ method: 'GET', query: { module: 'report', action: 'list', clientId: 'pain' } });
    ok('report list', res._json.ok && res._json.count >= 1);

    res = await call({ method: 'GET', query: { module: 'report', action: 'get', id: rid } });
    ok('report get', res._json.ok && res._json.data.id === rid);

    res = await call({ method: 'POST', query: { module: 'report', action: 'generate' }, body: { period: 'x' } });
    ok('report clientId 누락 400', res._status === 400);
    res = await call({ method: 'POST', query: { module: 'report', action: 'generate' }, body: { clientId: 'ghost' } });
    ok('report 없는 거래처 404', res._status === 404);
  }

  console.log('tasks recur');
  {
    // 반복 시드 2개 등록
    await call({ method: 'POST', query: { module: 'tasks', action: 'upsert' }, body: { task: { id: 'seedA', clientId: 'pain', templateId: 'linkedin', channelType: 'linkedin', title: 'LinkedIn 주간', automationLevel: 'B', recurrenceRule: 'weekly' } } });
    await call({ method: 'POST', query: { module: 'tasks', action: 'upsert' }, body: { task: { id: 'seedB', clientId: 'pain', templateId: 'gsc', channelType: 'gsc', title: '색인 점검', automationLevel: 'A', recurrenceRule: 'weekly' } } });
    let res = await call({ method: 'POST', query: { module: 'tasks', action: 'recur' }, body: { period: '2026-W28', clientId: 'pain' } });
    ok('recur 2건 생성', res._json.ok && res._json.count === 2 && res._json.data.every((t) => t.period === '2026-W28'));
    // 재실행 → 중복 없음
    res = await call({ method: 'POST', query: { module: 'tasks', action: 'recur' }, body: { period: '2026-W28', clientId: 'pain' } });
    ok('recur 재실행 0건(중복방지)', res._json.count === 0);
    // period 누락 400
    res = await call({ method: 'POST', query: { module: 'tasks', action: 'recur' }, body: { clientId: 'pain' } });
    ok('recur period 누락 400', res._status === 400);
  }

  console.log('automation log');
  {
    let res = await call({ method: 'POST', query: { module: 'automations', action: 'log' }, body: { automation: { name: 'AI Exposure Check', workflowType: 'exposure', status: 'ok' } } });
    ok('automation log 200', res._json.ok && res._json.data.id === 'atm_AI_Exposure_Check' && res._json.data.lastRunAt);
    // 같은 name 재기록 → 갱신(중복 없음)
    res = await call({ method: 'POST', query: { module: 'automations', action: 'log' }, body: { automation: { name: 'AI Exposure Check', status: 'error', errorMessage: 'timeout' } } });
    ok('automation 재기록 갱신', res._json.data.status === 'error');
    res = await call({ method: 'GET', query: { module: 'automations', action: 'list' } });
    ok('automation list 1건(중복없음)', res._json.data.filter((a) => a.name === 'AI Exposure Check').length === 1);
    res = await call({ method: 'POST', query: { module: 'automations', action: 'log' }, body: { automation: {} } });
    ok('name 누락 400', res._status === 400);
  }

  console.log('인증 게이트');
  {
    process.env.ADMIN_SECRET = 'sesame';
    let res = await call({ method: 'POST', query: { module: 'clients', action: 'upsert' }, body: { client: { id: 'x' } } }); // no auth
    ok('시크릿 설정 시 무인증 POST 401', res._status === 401);
    res = await call({ method: 'GET', query: { module: 'clients', action: 'list' } }); // no auth GET
    ok('시크릿 설정 시 무인증 GET 401', res._status === 401);
    res = await call({ method: 'GET', query: { module: 'clients', action: 'list' }, auth: 'sesame' });
    ok('올바른 시크릿 통과', res._status === 200);
    delete process.env.ADMIN_SECRET;
  }

  console.log(`\n결과: ${pass} pass, ${fail} fail`);
  process.exit(fail ? 1 : 0);
})();
