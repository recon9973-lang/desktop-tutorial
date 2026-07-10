'use strict';

// 진단 캐시(24h) 오프라인 검증 — 주입 캐시로 hit/miss·재계산 스킵 확인(네트워크 불필요)
//   node hospital-bot/test/cache.js

const path = require('path');
const D = require(path.join(__dirname, '..', 'lib', 'diagnose'));

let fails = 0;
function assert(cond, msg) { if (!cond) { console.error('  ✗ FAIL:', msg); fails++; } else { console.log('  ✓', msg); } }

// 호출 카운터가 달린 mock — 캐시 hit 시 외부호출이 안 늘어야 함
function makeDeps() {
  const calls = { find: 0, blog: 0, kw: 0, probe: 0, compete: 0 };
  const deps = {
    calls,
    cache: (() => {
      const store = new Map();
      return {
        configured: () => true,
        async getJson(k) { return store.has(k) ? JSON.parse(store.get(k)) : null; },
        async setJson(k, v) { store.set(k, JSON.stringify(v)); return true; },
        _store: store,
      };
    })(),
    naverOpenapi: {
      stripTags: (s) => s,
      async findHospital() { calls.find++; return { found: true, name: 'OO치과의원', category: '의료,건강>치과', address: '대구광역시 수성구 용학로 54', homepage: null, candidates: [] }; },
      async searchJson(kind) { if (kind === 'blog') { calls.blog++; return { ok: true, total: 42 }; } if (kind === 'local') return { ok: true, total: 3, items: [{ title: 'OO치과의원' }, { title: '미소플러스치과' }, { title: '튼튼치과' }] }; return { ok: true, total: 0, items: [] }; },
    },
    geoProbe: {
      buildPromptSet: () => ['q1'],
      async preview() { return { status: 'ready', mode: 'preview', engines: ['perplexity'], prompts: ['q1'] }; },
      async probe() { calls.probe++; return { status: 'done', grade: 'B', citationRate: 0.5, shareOfVoice: 0.3, sentiment: 'neutral', engines: ['perplexity'], asked: 4, mentionedCount: 2, competitors: [{ name: '미소플러스치과', mentions: 3 }] }; },
    },
    compete: {
      async compareCompetitors() { calls.compete++; return { status: 'ok', total: 3, targetRank: 2, region: '수성구', dept: '치과', rows: [{ name: 'x', isTarget: true, rank: 2 }] }; },
      isSameClinic: () => false,
    },
    searchad: { toNum: (v) => parseInt(String(v).replace(/[^0-9]/g, ''), 10) || 0, async fetchKeywordTool() { calls.kw++; return { status: 200, configured: true, keywordList: [{ relKeyword: '수성구임플란트', monthlyPcQcCnt: 900, monthlyMobileQcCnt: 3400, compIdx: '높음' }] }; }, async fetchBidEstimate() { return { status: 200, configured: true, bids: null }; } },
    psi: { async fetchPsi() { return { ok: false, reason: 'no key' }; } },
    adValidator: { validateMedicalAd() { return { pass: true, forbidden: [], risky: [] }; } },
    proposal: require(path.join(__dirname, '..', 'lib', 'proposal')),
    async fetchHtml() { return { ok: true, status: 200, text: '', bytes: 0 }; },
  };
  return deps;
}

async function main() {
  console.log('== 베이스 캐시: 2회 진단, 외부호출 1회만 ==');
  const deps = makeDeps();
  const r1 = await D.diagnose('대구 수성구 OO치과', { deps, now: 1 });
  assert(r1.meta.cache.base === false, '1회차 base miss');
  assert(deps.calls.find === 1 && deps.calls.kw === 1, `1회차 외부호출(find=${deps.calls.find}, kw=${deps.calls.kw})`);

  const r2 = await D.diagnose('대구 수성구 OO치과', { deps, now: 2 });
  assert(r2.meta.cache.base === true, '2회차 base HIT');
  assert(deps.calls.find === 1 && deps.calls.kw === 1, `2회차 재계산 스킵(find 여전히 ${deps.calls.find}, kw ${deps.calls.kw})`);
  assert(r2.seo && r2.ads && r2.local, '캐시 리포트도 필드 온전');

  console.log('== GEO 캐시: full 2회, probe 1회만 ==');
  const g1 = await D.diagnose('대구 수성구 OO치과', { deps, now: 3, geoMode: 'full' });
  assert(g1.geo.status === 'done' && g1.meta.cache.geo === false, '1회차 geo miss + done');
  assert(deps.calls.probe === 1, 'probe 1회 호출');
  const g2 = await D.diagnose('대구 수성구 OO치과', { deps, now: 4, geoMode: 'full' });
  assert(g2.meta.cache.geo === true && deps.calls.probe === 1, `2회차 geo HIT(probe 여전히 ${deps.calls.probe})`);

  console.log('== compete 캐시: 2회, compareCompetitors 1회만 ==');
  const c1 = await D.diagnose('대구 수성구 OO치과', { deps, now: 5, compete: true });
  assert(c1.compete.status === 'ok' && c1.meta.cache.compete === false, '1회차 compete miss');
  assert(deps.calls.compete === 1, 'compareCompetitors 1회');
  const c2 = await D.diagnose('대구 수성구 OO치과', { deps, now: 6, compete: true });
  assert(c2.meta.cache.compete === true && deps.calls.compete === 1, `2회차 compete HIT(여전히 ${deps.calls.compete})`);

  console.log('== opts.cache=false → 캐시 무시(항상 재계산) ==');
  const d2 = makeDeps();
  await D.diagnose('대구 수성구 OO치과', { deps: d2, now: 7, cache: false });
  await D.diagnose('대구 수성구 OO치과', { deps: d2, now: 8, cache: false });
  assert(d2.calls.find === 2, `cache:false면 매번 재계산(find=${d2.calls.find})`);

  console.log('== KV 미설정 → no-op(정상 동작) ==');
  const d3 = makeDeps(); d3.cache.configured = () => false;
  const n1 = await D.diagnose('대구 수성구 OO치과', { deps: d3, now: 9 });
  assert(n1.ok === true && n1.meta.cache.enabled === false, 'KV off여도 진단 정상');

  console.log(fails ? `\n❌ ${fails}건 실패` : '\n✅ 전체 통과');
  process.exit(fails ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(1); });
