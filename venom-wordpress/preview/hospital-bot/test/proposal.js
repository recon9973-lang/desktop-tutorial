'use strict';

// 제안서 자동 초안(P3) 오프라인 검증 — 규칙 매칭·광고비 추정·마크다운·diagnose통합·카톡
//   node hospital-bot/test/proposal.js

const path = require('path');
const P = require(path.join(__dirname, '..', 'lib', 'proposal'));
const D = require(path.join(__dirname, '..', 'lib', 'diagnose'));
const kf = require(path.join(__dirname, '..', 'lib', 'kakao-format'));

let fails = 0;
function assert(cond, msg) { if (!cond) { console.error('  ✗ FAIL:', msg); fails++; } else { console.log('  ✓', msg); } }

const REPORT = {
  ok: true, query: { name: 'OO치과' },
  resolved: { region: '수성구', dept: '치과', place: { found: true, name: 'OO치과의원' } },
  summary: { grade: 'C', score: 66, urgent: ['의료광고법 위반 소지 문구 수정', '홈페이지 속도 개선'] },
  seo: { status: 'ok', score100: 62, topFixes: ['모바일 속도 개선', '구조화데이터 보강'] },
  geo: { status: 'done', grade: 'D', citationRate: 0.1 },
  local: { blog: { total: 12 }, news: { total: 0 } },
  ads: { status: 'ok', cpc: { status: 'ok' }, keywords: [
    { keyword: '수성구임플란트', volume: 4300, cpc: 3900 },
    { keyword: '수성구치아교정', volume: 1500, cpc: 2100 },
    { keyword: '수성구충치', volume: 800, cpc: 1200 } ] },
  adLaw: { status: 'ok', pass: false, forbidden: ['최고'] },
  compete: { status: 'ok', region: '수성구', dept: '치과', total: 4, targetRank: 3, rows: [] },
};

function main() {
  console.log('== buildProposal: 규칙 매칭 ==');
  const p = P.buildProposal(REPORT);
  const areas = p.recommendations.map((r) => r.area);
  assert(areas.includes('SEO'), 'SEO 저점수 → 개선 제안');
  assert(areas.includes('GEO'), 'GEO 등급 D → GEO 최적화');
  assert(areas.includes('광고'), '검색 수요 → 파워링크');
  assert(areas.includes('의료광고법'), '위반 소지 → 심의 교정');
  assert(areas.includes('경쟁'), '하위권 순위 → 통합 마케팅');
  assert(p.recommendations[0].priority === 'high', 'high 우선순위가 먼저');

  console.log('== 광고비 추정(실 CPC×검색량, 가정 명시) ==');
  const b = p.budget;
  // 상위 3키워드: (4300*0.04*3900)+(1500*0.04*2100)+(800*0.04*1200)
  const expect = Math.round(4300 * 0.04) * 3900 + Math.round(1500 * 0.04) * 2100 + Math.round(800 * 0.04) * 1200;
  assert(b.status === 'ok' && b.monthlyRec === expect, `월 광고비 추정=₩${b.monthlyRec} (기대 ₩${expect})`);
  assert(b.monthlyMin < b.monthlyRec && b.monthlyRec < b.monthlyMax, '밴드 min<rec<max');
  assert(b.ctrAssumed === P.AD_CTR, `클릭률 가정 명시(${b.ctrAssumed})`);

  console.log('== 광고비: CPC 없으면 도달만(허위 없음) ==');
  const noCpc = P.estimateAdBudget({ status: 'ok', keywords: [{ keyword: 'k', volume: 1000 }] });
  assert(noCpc.status === 'partial' && noCpc.monthlyRec == null, 'CPC 없으면 월광고비 null');

  console.log('== 마크다운 ==');
  assert(/# .*제안 초안/.test(p.markdown) && /## 제안 솔루션/.test(p.markdown) && /## 예상 광고비/.test(p.markdown), '마크다운 섹션');
  assert(/별도 협의/.test(p.markdown) && /의료법/.test(p.markdown), '대행수수료 협의 + 의료법 준수 명시(허위가격 없음)');

  console.log('== diagnose 통합(opts.proposal) ==');
  const mockDeps = {
    naverOpenapi: { async findHospital() { return { found: true, name: 'OO치과의원', category: '의료,건강>치과', address: '대구광역시 수성구', homepage: null, candidates: [] }; }, async searchJson() { return { ok: true, total: 0, items: [] }; }, stripTags: (s) => s },
    geoProbe: require(path.join(__dirname, '..', 'lib', 'geo-probe')),
    compete: require(path.join(__dirname, '..', 'lib', 'compete')),
    proposal: P,
    searchad: { toNum: (v) => parseInt(String(v).replace(/[^0-9]/g, ''), 10) || 0, async fetchKeywordTool() { return { status: 200, configured: true, keywordList: [] }; } },
    psi: { async fetchPsi() { return { ok: false, reason: 'no key' }; } },
    adValidator: { validateMedicalAd() { return { pass: true, forbidden: [], risky: [] }; } },
    async fetchHtml() { return { ok: true, status: 200, text: '', bytes: 0 }; },
  };
  return D.diagnose('대구 수성구 OO치과', { deps: mockDeps, now: 1720000000000, proposal: true }).then((rep) => {
    assert(rep.proposal && rep.proposal.title && Array.isArray(rep.proposal.recommendations), 'diagnose.proposal 부착');

    console.log('== 카톡 renderProposal ==');
    const card = kf.render(Object.assign({}, REPORT, { proposal: p }), 'proposal');
    const txt = card.template.outputs[0].simpleText.text;
    assert(card.version === '2.0' && /제안 초안/.test(txt), 'SkillResponse + 제안 초안');
    assert(/핵심 제안/.test(txt) && /광고비/.test(txt), '핵심 제안 + 광고비 라인');
    assert(/대행 수수료 별도 협의/.test(txt), '수수료 협의 고지');

    console.log('== 발화 파싱: proposal ==');
    assert(kf.parseCommand('OO치과 제안서').view === 'proposal', "'제안서' → proposal");
    assert(kf.parseCommand('OO치과 견적').view === 'proposal', "'견적' → proposal");
    assert(kf.parseCommand('상담').view === 'contact', "'상담'은 여전히 contact");

    console.log(fails ? `\n❌ ${fails}건 실패` : '\n✅ 전체 통과');
    process.exit(fails ? 1 : 0);
  });
}

main();
