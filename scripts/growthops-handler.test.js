'use strict';

// node scripts/growthops-handler.test.js
// github-store를 인메모리로 모킹해 api/growthops.js 라우팅/인증을 검증(네트워크 없음).
const assert = require('assert');
const path = require('path');

// 1) github-store를 require 캐시에서 인메모리 구현으로 교체
const storePath = require.resolve('../lib/github-store');
const mem = { files: {} }; // path -> content
require.cache[storePath] = {
  id: storePath, filename: storePath, loaded: true, exports: {
    getPosts: async () => ({ sha: 'x', posts: mem.posts || [] }),
    getJsonFile: async (p, fallback) => ({ sha: mem.files[p] ? 's' : null, content: mem.files[p] || fallback }),
    saveJsonFile: async (p, content) => { mem.files[p] = content; return { ok: true }; },
  },
};

const handler = require('../api/growthops');

mem.posts = [
  { id: 'a', slug: 'a', cat: 'dental', region: '대구', status: 'published', title: '대구 임플란트 마케팅', keywords: '대구,임플란트,치과', html: '' },
  { id: 'b', slug: 'b', cat: 'dental', region: '대구', status: 'published', title: '임플란트 비용 정리', keywords: '임플란트,치과,비용', html: '' },
];

function mockRes() {
  return {
    _status: 0, _json: null, headers: {},
    setHeader(k, v) { this.headers[k] = v; },
    status(c) { this._status = c; return this; },
    json(o) { this._json = o; return this; },
    end() { return this; },
  };
}
function mockReq(method, query, body, auth) {
  return { method, query, body, headers: auth ? { authorization: 'Bearer ' + auth } : {} };
}

let pass = 0;
async function test(name, fn) {
  try { await fn(); pass++; console.log('  ✓ ' + name); }
  catch (e) { console.error('  ✗ ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

(async () => {
  await test('linkhealth: 통계 반환', async () => {
    const res = mockRes();
    await handler(mockReq('GET', { module: 'linkhealth' }), res);
    assert.strictEqual(res._status, 200);
    assert.strictEqual(res._json.ok, true);
    assert.strictEqual(res._json.posts, 2);
    assert.ok('orphanCount' in res._json);
  });

  await test('outreach list: 빈 목록 + 요약', async () => {
    const res = mockRes();
    await handler(mockReq('GET', { module: 'outreach', action: 'list' }), res);
    assert.strictEqual(res._json.ok, true);
    assert.strictEqual(res._json.summary.total, 0);
    assert.deepStrictEqual(res._json.contacts, []);
  });

  await test('outreach upsert: ADMIN_SECRET 없으면 401', async () => {
    process.env.ADMIN_SECRET = 'secret123';
    const res = mockRes();
    await handler(mockReq('POST', { module: 'outreach', action: 'upsert' }, { contact: { name: '대구일보' } }), res);
    assert.strictEqual(res._status, 401);
  });

  await test('outreach upsert: 인증되면 저장', async () => {
    const res = mockRes();
    await handler(mockReq('POST', { module: 'outreach', action: 'upsert' }, { contact: { name: '대구일보', type: 'pr' } }, 'secret123'), res);
    assert.strictEqual(res._status, 200);
    assert.strictEqual(res._json.contact.name, '대구일보');
    // 저장 후 목록에 반영
    const res2 = mockRes();
    await handler(mockReq('GET', { module: 'outreach', action: 'list' }), res2);
    assert.strictEqual(res2._json.contacts.length, 1);
    delete process.env.ADMIN_SECRET;
  });

  await test('snapshot: 계산+저장', async () => {
    const res = mockRes();
    await handler(mockReq('POST', { module: 'snapshot' }, {}), res);
    assert.strictEqual(res._status, 200);
    assert.strictEqual(res._json.ok, true);
    assert.strictEqual(res._json.snapshot.posts, 2);
  });

  await test('cluster build: 인증+related 제공 시 생성/저장', async () => {
    process.env.ADMIN_SECRET = 'secret123';
    const res = mockRes();
    await handler(mockReq('POST', { module: 'cluster', action: 'build' },
      { category: 'dental', region: '대구', pillar: '임플란트', related: ['임플란트 비용', '임플란트 가격'], questions: [] }, 'secret123'), res);
    assert.strictEqual(res._status, 200);
    assert.strictEqual(res._json.ok, true);
    assert.ok(res._json.cluster.id.startsWith('cl_'));
    assert.strictEqual(res._json.cluster.subtopics.length, 2);
    delete process.env.ADMIN_SECRET;
  });

  await test('cluster list: posts 매칭 + 요약', async () => {
    // mem.posts에 dental 글이 있으므로 빈칸이 채워질 수 있음
    const res = mockRes();
    await handler(mockReq('GET', { module: 'cluster', action: 'list' }), res);
    assert.strictEqual(res._json.ok, true);
    assert.ok(res._json.summary.clusters >= 1);
    assert.ok('completion' in res._json.summary);
  });

  await test('cluster build: 인증 없으면 401', async () => {
    process.env.ADMIN_SECRET = 'secret123';
    const res = mockRes();
    await handler(mockReq('POST', { module: 'cluster', action: 'build' }, { category: 'x', pillar: 'y', related: ['z'] }), res);
    assert.strictEqual(res._status, 401);
    delete process.env.ADMIN_SECRET;
  });

  await test('cwv: PSI_KEY/모니터URL 없으면 빈 결과로 안전 응답', async () => {
    delete process.env.GROWTHOPS_MONITOR_URLS; delete process.env.SITE_URL;
    const res = mockRes();
    await handler(mockReq('GET', { module: 'cwv' }), res);
    assert.strictEqual(res._status, 200);
    assert.strictEqual(res._json.ok, true);
    assert.deepStrictEqual(res._json.results, []);
  });

  await test('cwv: url 주어지면 PSI_KEY 없을 때 ok:false 결과', async () => {
    delete process.env.PSI_KEY;
    const res = mockRes();
    await handler(mockReq('GET', { module: 'cwv', url: 'https://example.com/' }), res);
    assert.strictEqual(res._json.ok, true);
    assert.strictEqual(res._json.results[0].ok, false);
    assert.match(res._json.results[0].reason, /PSI_KEY/);
  });

  await test('알 수 없는 module: 400', async () => {
    const res = mockRes();
    await handler(mockReq('GET', { module: 'nope' }), res);
    assert.strictEqual(res._status, 400);
  });

  console.log(`\n${pass} passed`);
})();
