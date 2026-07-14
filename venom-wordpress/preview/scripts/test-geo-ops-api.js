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
