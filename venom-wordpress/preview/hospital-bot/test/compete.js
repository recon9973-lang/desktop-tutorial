'use strict';

// 경쟁사 비교(P2) 오프라인 검증 — 순위 로직·diagnose 통합·카톡 렌더 (네트워크 불필요)
//   node hospital-bot/test/compete.js

const path = require('path');
const C = require(path.join(__dirname, '..', 'lib', 'compete'));
const D = require(path.join(__dirname, '..', 'lib', 'diagnose'));
const kf = require(path.join(__dirname, '..', 'lib', 'kakao-format'));

let fails = 0;
function assert(cond, msg) { if (!cond) { console.error('  ✗ FAIL:', msg); fails++; } else { console.log('  ✓', msg); } }

// 블로그/뉴스 총계를 병원명으로 매핑하는 mock
const BLOG = { 'OO치과의원': 420, '미소플러스치과': 1240, '튼튼치과': 100 };
const NEWS = { 'OO치과의원': 0, '미소플러스치과': 2, '튼튼치과': 0 };
function mockNaver(localItems) {
  return {
    stripTags: (s) => String(s).replace(/<\/?b>/g, ''),
    async searchJson(kind, query) {
      if (kind === 'local') return { ok: true, total: localItems.length, items: localItems.map((t) => ({ title: t })) };
      if (kind === 'blog') return { ok: true, total: BLOG[query] != null ? BLOG[query] : 50 };
      if (kind === 'news') return { ok: true, total: NEWS[query] != null ? NEWS[query] : 0 };
      return { ok: true, total: 0, items: [] };
    },
  };
}

async function main() {
  console.log('== compareCompetitors: 순위 ==');
  const deps = { naverOpenapi: mockNaver(['OO치과의원', '미소플러스치과', '튼튼치과']) };
  const r = await C.compareCompetitors('OO치과의원', {
    region: '수성구', dept: '치과', deps,
    existingCompetitors: [{ name: '미소플러스치과', mentions: 4 }],
  });
  assert(r.status === 'ok', 'status=ok');
  assert(r.total === 3, `타깃+경쟁 ${r.total}곳(타깃 중복 제외)`);
  assert(r.rows.filter((x) => x.isTarget).length === 1, '타깃 정확히 1행');
  assert(!r.rows.filter((x) => !x.isTarget).some((x) => C.isSameClinic(x.name, 'OO치과의원', '수성구')), '경쟁(비타깃) 목록에 타깃 중복 없음');
  // 점수: 미소 1240+2*3+4*20=1326(1위), 타깃 420(2위), 튼튼 100(3위)
  assert(r.rows[0].name === '미소플러스치과' && r.rows[0].rank === 1, `1위=${r.rows[0].name}`);
  assert(r.targetRank === 2, `우리 순위=${r.targetRank}위`);
  assert(r.rows.find((x) => x.name === '미소플러스치과').geoMentions === 4, 'GEO 언급수 반영');

  console.log('== insufficient(경쟁 없음) ==');
  const only = await C.compareCompetitors('OO치과의원', { region: '수성구', dept: '치과', deps: { naverOpenapi: mockNaver(['OO치과의원']) } });
  assert(only.status === 'insufficient' && only.rows.length === 0, '타깃만 있으면 insufficient');

  console.log('== diagnose 통합(opts.compete) ==');
  const fullDeps = {
    naverOpenapi: Object.assign(mockNaver(['OO치과의원', '미소플러스치과', '튼튼치과']), {
      async findHospital() { return { found: true, source: 'naver-local', name: 'OO치과의원', category: '의료,건강>치과', address: '대구광역시 수성구 용학로 54', homepage: null, candidates: [] }; },
    }),
    geoProbe: require(path.join(__dirname, '..', 'lib', 'geo-probe')),
    compete: C,
    searchad: { toNum: (v) => parseInt(String(v).replace(/[^0-9]/g, ''), 10) || 0, async fetchKeywordTool() { return { status: 200, configured: true, keywordList: [] }; } },
    psi: { async fetchPsi() { return { ok: false, reason: 'no key' }; } },
    adValidator: { validateMedicalAd() { return { pass: true, forbidden: [], risky: [] }; } },
    async fetchHtml() { return { ok: true, status: 200, text: '', bytes: 0 }; },
  };
  const rep = await D.diagnose('대구 수성구 OO치과', { deps: fullDeps, now: 1720000000000, compete: true });
  assert(rep.compete && rep.compete.status === 'ok' && rep.compete.targetRank === 2, `diagnose.compete 부착(순위 ${rep.compete && rep.compete.targetRank})`);

  console.log('== 카톡 renderCompete ==');
  const card = kf.render(rep, 'compete');
  assert(card.version === '2.0' && card.template.outputs[0].simpleText, 'SkillResponse 형식');
  const txt = card.template.outputs[0].simpleText.text;
  assert(/동네 순위/.test(txt) && /★/.test(txt) && /우리 병원/.test(txt), '순위표 + 우리병원 표시');
  assert(/미소플러스치과/.test(txt), '경쟁 병원 렌더');

  console.log('== 발화 파싱: compete ==');
  assert(kf.parseCommand('OO치과 순위').view === 'compete', "'순위' → compete");
  assert(kf.parseCommand('OO치과 경쟁').view === 'compete', "'경쟁' → compete");

  console.log(fails ? `\n❌ ${fails}건 실패` : '\n✅ 전체 통과');
  process.exit(fails ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(1); });
