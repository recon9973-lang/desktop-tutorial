'use strict';

// node scripts/topic-cluster.test.js
const assert = require('assert');
const T = require('../venom-wordpress/preview/lib/topic-cluster');

let pass = 0;
function test(n, fn){ try{ fn(); pass++; console.log('  ✓ '+n); }catch(e){ console.error('  ✗ '+n+'\n    '+e.message); process.exitCode=1; } }

const AT = '2026-06-30T00:00:00.000Z';

test('buildCluster: 필러 제외, size 컷, open 상태', () => {
  const c = T.buildCluster({ category:'dental', region:'대구', pillar:'임플란트',
    related:['임플란트 비용','임플란트 가격','임플란트'], questions:['임플란트 아파요?'], size:3, at:AT });
  assert.strictEqual(c.subtopics.length, 3);
  assert.ok(!c.subtopics.find(s=>s.kw==='임플란트')); // 필러와 동일 → 제외
  assert.ok(c.subtopics.every(s=>s.status==='open' && s.postId===null));
  assert.ok(c.id.startsWith('cl_'));
});

test('buildCluster: category/pillar 누락 시 throw', () => {
  assert.throws(()=>T.buildCluster({ pillar:'x' }));
  assert.throws(()=>T.buildCluster({ category:'x' }));
});

test('mergePosts: 같은 과목 빈칸을 가장 잘 맞는 글로 채움', () => {
  let obj = { clusters:[ T.buildCluster({ category:'dental', pillar:'임플란트',
    related:['임플란트 비용','교정 장치'], size:2, at:AT }) ] };
  const posts = [
    { id:'p1', cat:'dental', title:'임플란트 비용 총정리', keywords:'임플란트,비용' },
    { id:'p2', cat:'skin', title:'여드름 흉터', keywords:'여드름' }, // 과목 다름 → 매칭 안 됨
  ];
  obj = T.mergePostsIntoClusters(obj, posts);
  const subs = obj.clusters[0].subtopics;
  const filled = subs.find(s=>s.kw==='임플란트 비용');
  assert.strictEqual(filled.postId, 'p1');
  assert.strictEqual(filled.status, 'filled');
});

test('mergePosts: 삭제된 글이면 칸을 비운다', () => {
  let obj = { clusters:[ { id:'c', category:'dental', pillar:'p', region:'',
    subtopics:[ { kw:'임플란트 비용', postId:'gone', status:'filled' } ] } ] };
  obj = T.mergePostsIntoClusters(obj, [{ id:'other', cat:'dental', title:'무관', keywords:'무관' }]);
  assert.strictEqual(obj.clusters[0].subtopics[0].postId, null);
  assert.strictEqual(obj.clusters[0].subtopics[0].status, 'open');
});

test('nextGap: 첫 빈칸 반환, 다 차면 null', () => {
  const obj = { clusters:[ T.buildCluster({ category:'dental', pillar:'임플란트', related:['A','B'], size:2, at:AT }) ] };
  const g = T.nextGap(obj);
  assert.strictEqual(g.category, 'dental');
  assert.ok(g.kw);
  const full = T.fillSubtopic(T.fillSubtopic(obj, obj.clusters[0].id, 'A', 'p1'), obj.clusters[0].id, 'B', 'p2');
  assert.strictEqual(T.nextGap(full), null);
});

test('fillSubtopic: 해당 kw만 채움', () => {
  const obj = { clusters:[ T.buildCluster({ category:'dental', pillar:'임플란트', related:['A','B'], size:2, at:AT }) ] };
  const id = obj.clusters[0].id;
  const out = T.fillSubtopic(obj, id, 'A', 'p1');
  const a = out.clusters[0].subtopics.find(s=>s.kw==='A');
  const b = out.clusters[0].subtopics.find(s=>s.kw==='B');
  assert.strictEqual(a.postId, 'p1');
  assert.strictEqual(b.postId, null);
});

test('upsertCluster: 재구성해도 채움 상태 보존', () => {
  let obj = { clusters:[ T.buildCluster({ category:'dental', pillar:'임플란트', related:['A','B'], size:2, at:AT }) ] };
  const id = obj.clusters[0].id;
  obj = T.fillSubtopic(obj, id, 'A', 'p1');
  // 같은 클러스터를 새 related로 재생성해 upsert
  const rebuilt = T.buildCluster({ category:'dental', pillar:'임플란트', related:['A','C'], size:2, at:AT });
  obj = T.upsertCluster(obj, rebuilt);
  const a = obj.clusters[0].subtopics.find(s=>s.kw==='A');
  assert.strictEqual(a.postId, 'p1', 'A의 채움 상태 보존');
});

test('summary: 완성도 계산', () => {
  let obj = { clusters:[ T.buildCluster({ category:'dental', pillar:'임플란트', related:['A','B','C'], size:3, at:AT }) ] };
  obj = T.fillSubtopic(obj, obj.clusters[0].id, 'A', 'p1');
  const s = T.summary(obj);
  assert.strictEqual(s.totalSubtopics, 3);
  assert.strictEqual(s.filled, 1);
  assert.ok(Math.abs(s.completion - 0.333) < 0.01);
});

console.log(`\n${pass} passed`);
