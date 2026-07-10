'use strict';

// 베노미 코어 엔진 오프라인 검증 (네트워크·키 불필요)
//   node hospital-bot/test/run.js          → mock 의존성으로 진단서 구조 검증
//   node hospital-bot/test/run.js --live "대구 수성구 OO치과"  → 실 API(키 필요)
//
// mock은 각 lib의 실제 반환형을 흉내내 diagnose()가 6대 진단을 올바르게 조립하는지 확인한다.

const path = require('path');
const D = require(path.join(__dirname, '..', 'lib', 'diagnose'));

function assert(cond, msg) { if (!cond) { console.error('  ✗ FAIL:', msg); process.exitCode = 1; } else { console.log('  ✓', msg); } }

const mockDeps = {
  geoProbe: require(path.join(__dirname, '..', 'lib', 'geo-probe')), // 순수 스텁 — 그대로 사용
  naverOpenapi: {
    async findHospital() {
      return { found: true, source: 'naver-local', name: 'OO치과의원', category: '의료,건강>병원>치과',
        telephone: '053-000-0000', address: '대구광역시 수성구 용학로 54', homepage: 'https://example-clinic.co.kr', candidates: [] };
    },
    async searchJson(kind) {
      if (kind === 'local') return { ok: true, total: 1, items: [{ title: 'OO치과' }] };
      if (kind === 'blog') return { ok: true, total: 42, items: [] };
      if (kind === 'news') return { ok: true, total: 0, items: [] };
      return { ok: true, total: 0, items: [] };
    },
  },
  searchad: {
    toNum: (v) => (v == null || v === '< 10' ? (v === '< 10' ? 5 : 0) : parseInt(String(v).replace(/[^0-9]/g, ''), 10) || 0),
    async fetchKeywordTool(seeds) {
      return { status: 200, configured: true, error: null, keywordList: [
        { relKeyword: '수성구임플란트', monthlyPcQcCnt: 900, monthlyMobileQcCnt: 3400, compIdx: '높음', plAvgDepth: 15 },
        { relKeyword: '수성구치아교정', monthlyPcQcCnt: 300, monthlyMobileQcCnt: 1200, compIdx: '중간', plAvgDepth: 8 },
      ] };
    },
  },
  psi: {
    async fetchPsi(url) {
      return { ok: true, url, strategy: 'mobile',
        scores: { performance: 48, seo: 83, accessibility: 76, bestPractices: 92 },
        lab: { lcpMs: 4200, cls: 0.02, tbtMs: 300 }, field: null };
    },
  },
  adValidator: {
    validateMedicalAd(text) {
      const forbidden = /최고/.test(text) ? ['최고'] : [];
      return { pass: forbidden.length === 0, forbidden, risky: [] };
    },
  },
  async fetchHtml() { return { ok: true, status: 200, text: '수성구 최고의 임플란트 치과입니다. 신뢰할 수 있는 진료.', bytes: 100 }; },
};

async function main() {
  const live = process.argv.includes('--live');
  if (live) {
    const name = process.argv[process.argv.indexOf('--live') + 1] || '대구 수성구 치과';
    console.log('LIVE 진단:', name);
    const r = await D.diagnose(name, { now: Date.now() });
    console.log(JSON.stringify(r, null, 2));
    return;
  }

  console.log('== 유닛: parseInput ==');
  const p = D.parseInput('대구 수성구 OO치과');
  assert(p.region === '수성구', `지역 파싱: ${p.region}`);
  assert(/치과/.test(p.name), `병원명 파싱: ${p.name}`);
  assert(D.parseInput('대구 중구 △△의원').region === '중구', '1음절 자치구(중구) 파싱');
  assert(D.parseInput('서울 강남구 □□피부과').region === '강남구', '광역시 제외+자치구(강남구)');
  assert(D.parseInput('대구광역시 수성구 OO치과').region === '수성구', '광역시 풀네임 제외');
  assert(D.parseInput('그냥병원').region === '', '지역 없으면 빈 문자열');

  console.log('== 유닛: keywordSeeds ==');
  const seeds = D.keywordSeeds('치과', '수성구');
  assert(seeds.length > 0 && seeds.length <= 5, `시드 ${seeds.length}개: ${seeds.join(', ')}`);
  assert(seeds[0] === '수성구치과', '지역+진료과 결합');

  console.log('== 통합: diagnose (mock) ==');
  const r = await D.diagnose('대구 수성구 OO치과', { deps: mockDeps, now: 1720000000000 });
  assert(r.ok === true, 'ok=true');
  assert(r.resolved.region === '수성구', `resolved.region=${r.resolved.region}`);
  assert(r.resolved.dept === '치과', `resolved.dept=${r.resolved.dept}`);
  assert(r.seo.status === 'ok' && r.seo.score100 === Math.round((48 + 83) / 2), `SEO score100=${r.seo.score100}`);
  assert(r.seo.topFixes.length > 0, `SEO 개선항목 ${r.seo.topFixes.length}건`);
  assert(r.local.blog.total === 42, `블로그 total=${r.local.blog.total}`);
  assert(r.local.news.total === 0 && r.local.signals.some(s => /PR/.test(s)), '뉴스 0 → PR 기회 신호');
  assert(r.ads.status === 'ok' && r.ads.keywords[0].volume === 4300, `광고 최상위 키워드 검색량=${r.ads.keywords[0].volume}`);
  assert(r.ads.cpc.status === 'p1-pending', 'CPC는 P1 표기(허위수치 없음)');
  assert(r.adLaw.status === 'ok' && r.adLaw.pass === false && r.adLaw.forbidden.includes('최고'), '광고법: "최고" 위반 탐지');
  assert(['ready', 'unconfigured'].includes(r.geo.status) && Array.isArray(r.geo.prompts) && r.geo.prompts.length > 0, `GEO light(preview) 상태=${r.geo.status}, 프롬프트 ${r.geo.prompts.length}개`);
  assert(r.summary.grade && r.summary.urgent.length > 0, `종합등급=${r.summary.grade}, 우선개선=${r.summary.urgent.length}`);

  console.log('\n── 진단서 요약 ──');
  console.log('종합:', r.summary.headline);
  console.log('우선 개선:', r.summary.urgent.join(' / '));
  console.log(process.exitCode ? '\n❌ 일부 실패' : '\n✅ 전체 통과');
}

main().catch((e) => { console.error(e); process.exit(1); });
