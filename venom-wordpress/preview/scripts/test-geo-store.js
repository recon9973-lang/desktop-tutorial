#!/usr/bin/env node
'use strict';

/**
 * lib/geo-store.js 오프라인 검증 — 네트워크·GitHub 없이 인메모리 백엔드로 CRUD 로직 확인.
 * 실행:  node scripts/test-geo-store.js   (실패 시 exit 1)
 *
 * 커버:
 *   - 순수 헬퍼: genId(유일성·prefix), upsertItem(신규/갱신 병합), removeItem, matchFilter
 *   - 비동기 CRUD: upsert(id 자동생성·updatedAt), get, list(+필터), remove
 *   - 동시쓰기: withConflictRetry 경로가 getFile→putFile 재읽기로 안전한지(409 1회 주입)
 */

const geo = require('../lib/geo-store.js');

let pass = 0, fail = 0;
function ok(name, cond) { cond ? (pass++, console.log('  ✓ ' + name)) : (fail++, console.error('  ✗ ' + name)); }

// ── 인메모리 백엔드(목) — github-store 인터페이스 흉내 ──
function makeBackend() {
  const files = {}; // path → { sha, content }
  let conflictOnce = false;
  return {
    _files: files,
    _triggerConflictOnce() { conflictOnce = true; },
    async getFile(path) { return files[path] ? { sha: files[path].sha, content: JSON.parse(JSON.stringify(files[path].content)) } : null; },
    async getJsonFile(path, fallback) { return { content: files[path] ? JSON.parse(JSON.stringify(files[path].content)) : (fallback || {}) }; },
    async putFile(path, content, sha, message) {
      if (conflictOnce) { conflictOnce = false; const e = new Error('conflict'); e.status = 409; throw e; }
      const cur = files[path];
      if (cur && sha && cur.sha !== sha) { const e = new Error('sha stale'); e.status = 409; throw e; }
      files[path] = { sha: 's' + Math.random().toString(36).slice(2, 8), content: JSON.parse(JSON.stringify(content)) };
      return { ok: true };
    },
    async withConflictRetry(op, tries) {
      const max = tries || 4;
      for (let i = 0; ; i++) {
        try { return await op(); }
        catch (e) { if (e && e.status === 409 && i < max - 1) continue; throw e; }
      }
    },
  };
}

(async () => {
  // ── 순수 헬퍼 ──
  console.log('순수 헬퍼');
  {
    const a = geo.genId('cli'), b = geo.genId('cli');
    ok('genId prefix', a.startsWith('cli_'));
    ok('genId 유일', a !== b);

    const arr = [{ id: 'x', v: 1 }];
    const r1 = geo.upsertItem(arr, { id: 'y', v: 2 });
    ok('upsertItem 신규 앞에 추가', arr.length === 2 && arr[0].id === 'y' && r1.id === 'y');
    geo.upsertItem(arr, { id: 'x', v: 9 });
    ok('upsertItem 기존 병합', arr.find((i) => i.id === 'x').v === 9);

    ok('removeItem 존재', geo.removeItem(arr, 'x') === true && !arr.find((i) => i.id === 'x'));
    ok('removeItem 부재', geo.removeItem(arr, 'zzz') === false);

    ok('matchFilter null=통과', geo.matchFilter({ a: 1 }, null) === true);
    ok('matchFilter 일치', geo.matchFilter({ clientId: 'pain', active: true }, { clientId: 'pain' }) === true);
    ok('matchFilter 불일치', geo.matchFilter({ clientId: 'skin' }, { clientId: 'pain' }) === false);
  }

  // ── 비동기 CRUD ──
  console.log('비동기 CRUD');
  {
    const be = makeBackend();
    geo._setBackend(be);

    const saved = await geo.upsert('clients', { name: '테스트의원', active: true });
    ok('upsert id 자동생성', typeof saved.id === 'string' && saved.id.startsWith('cli'));
    ok('upsert updatedAt 부여', typeof saved.updatedAt === 'string');

    await geo.upsert('clients', { id: 'pain', name: '시원통증', active: true });
    await geo.upsert('clients', { id: 'skin', name: '시원스킨', active: false });

    const all = await geo.list('clients');
    ok('list 전체', all.length === 3);

    const activeOnly = await geo.list('clients', { active: true });
    ok('list 필터(active)', activeOnly.length === 2);

    const one = await geo.get('clients', 'pain');
    ok('get 단건', one && one.name === '시원통증');
    ok('get 부재 null', (await geo.get('clients', 'nope')) === null);

    // 갱신(upsert 병합)
    await geo.upsert('clients', { id: 'pain', region: '포항' });
    const merged = await geo.get('clients', 'pain');
    ok('upsert 병합 보존', merged.name === '시원통증' && merged.region === '포항');

    ok('remove 존재', (await geo.remove('clients', 'skin')) === true);
    ok('remove 후 목록', (await geo.list('clients')).length === 2);

    // 컬렉션 격리
    await geo.upsert('channels', { id: 'c1', clientId: 'pain', channelType: 'wikipedia' });
    ok('컬렉션 격리', (await geo.list('channels')).length === 1 && (await geo.list('clients')).length === 2);

    // 동시쓰기 충돌 1회 → 재시도로 성공
    be._triggerConflictOnce();
    const afterConflict = await geo.upsert('clients', { id: 'pain', assignee: '담당A' });
    ok('409 재시도 성공', afterConflict && (await geo.get('clients', 'pain')).assignee === '담당A');
  }

  // ── 알 수 없는 컬렉션 ──
  console.log('예외');
  {
    let threw = false;
    try { geo.collMeta('nope'); } catch { threw = true; }
    ok('unknown collection throw', threw);
  }

  console.log(`\n결과: ${pass} pass, ${fail} fail`);
  process.exit(fail ? 1 : 0);
})();
