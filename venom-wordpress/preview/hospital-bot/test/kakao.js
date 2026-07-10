'use strict';

// 카카오 연동(#2) 오프라인 검증 — 발화 파싱·화이트리스트·SkillResponse 렌더
//   node hospital-bot/test/kakao.js

const path = require('path');
const kf = require(path.join(__dirname, '..', 'lib', 'kakao-format'));
const wl = require(path.join(__dirname, '..', 'lib', 'whitelist'));
const D = require(path.join(__dirname, '..', 'lib', 'diagnose'));

let fails = 0;
function assert(cond, msg) { if (!cond) { console.error('  ✗ FAIL:', msg); fails++; } else { console.log('  ✓', msg); } }

// 진단서 mock (diagnose 출력형과 동일)
const mockDeps = {
  geoProbe: require(path.join(__dirname, '..', 'lib', 'geo-probe')),
  naverOpenapi: {
    async findHospital() { return { found: true, source: 'naver-local', name: 'OO치과의원', category: '의료,건강>병원>치과', telephone: '053-000', address: '대구광역시 수성구 용학로 54', homepage: 'https://ex.co.kr', candidates: [] }; },
    async searchJson(kind) { return kind === 'blog' ? { ok: true, total: 42, items: [] } : kind === 'news' ? { ok: true, total: 0, items: [] } : { ok: true, total: 1, items: [{ title: 'OO치과' }] }; },
  },
  searchad: {
    toNum: (v) => parseInt(String(v).replace(/[^0-9]/g, ''), 10) || 0,
    async fetchKeywordTool() { return { status: 200, configured: true, error: null, keywordList: [ { relKeyword: '수성구임플란트', monthlyPcQcCnt: 900, monthlyMobileQcCnt: 3400, compIdx: '높음', plAvgDepth: 15 } ] }; },
    async fetchBidEstimate() { return { status: 200, configured: true, error: null, device: 'MOBILE', position: 2, bids: { '수성구임플란트': 3900 } }; },
  },
  psi: { async fetchPsi(url) { return { ok: true, url, strategy: 'mobile', scores: { performance: 48, seo: 83, accessibility: 76, bestPractices: 92 }, lab: { lcpMs: 4200 }, field: null }; } },
  adValidator: { validateMedicalAd(t) { const f = /최고/.test(t) ? ['최고'] : []; return { pass: !f.length, forbidden: f, risky: [] }; } },
  async fetchHtml() { return { ok: true, status: 200, text: '수성구 최고의 임플란트', bytes: 20 }; },
};

function isValidSkill(r) {
  return r && r.version === '2.0' && r.template && Array.isArray(r.template.outputs) && r.template.outputs.length > 0;
}

async function main() {
  console.log('== 발화 파싱 ==');
  assert(kf.parseCommand('대구 수성구 OO치과').view === 'summary', '기본=종합');
  assert(kf.parseCommand('OO치과 seo').view === 'seo' && kf.parseCommand('OO치과 seo').hospital === 'OO치과', 'seo 뷰 + 병원명 분리');
  assert(kf.parseCommand('OO치과 광고').view === 'ads', '광고 뷰');
  assert(kf.parseCommand('OO치과 geo').view === 'geo', 'geo 뷰');
  assert(kf.parseCommand('OO치과 플레이스').view === 'local', '플레이스 뷰');
  assert(kf.parseCommand('OO치과 심의').view === 'law', '심의 뷰');
  assert(kf.parseCommand('상담').view === 'contact', '상담=CTA');
  assert(kf.parseCommand('seo').view === 'summary', '병원명 없는 seo → 종합(빈 병원명 방지)');

  console.log('== 화이트리스트 ==');
  delete process.env.VENOMI_WHITELIST;
  assert(wl.check('anyone').allowed === true && wl.check('anyone').mode === 'open', '미설정 → open 허용');
  process.env.VENOMI_WHITELIST = 'staff-1, staff-2';
  assert(wl.isConfigured() === true, '설정 시 configured');
  assert(wl.check('staff-1').allowed === true, '목록 내 허용');
  assert(wl.check('outsider').allowed === false && wl.check('outsider').mode === 'enforced', '목록 외 거절');
  delete process.env.VENOMI_WHITELIST;

  console.log('== SkillResponse 렌더 ==');
  const report = await D.diagnose('대구 수성구 OO치과', { deps: mockDeps, now: 1720000000000 });

  const sum = kf.render(report, 'summary');
  assert(isValidSkill(sum), '종합 SkillResponse 형식 유효');
  const sumText = sum.template.outputs[0].simpleText.text;
  assert(/종합등급/.test(sumText) && /66\/100/.test(sumText), '종합 카드에 등급·SEO점수 포함');
  assert(sum.template.quickReplies && sum.template.quickReplies.length >= 4, `quickReplies ${sum.template.quickReplies.length}개`);
  assert(sum.template.quickReplies.every((q) => q.action === 'message' && q.messageText), 'quickReply 액션 유효');

  const seo = kf.render(report, 'seo');
  assert(isValidSkill(seo) && /개선 우선순위/.test(seo.template.outputs[0].simpleText.text), 'SEO 상세 렌더');

  const ads = kf.render(report, 'ads');
  assert(isValidSkill(ads) && /수성구임플란트/.test(ads.template.outputs[0].simpleText.text), '광고 상세 렌더');
  assert(/₩3,900/.test(ads.template.outputs[0].simpleText.text) && /2위 노출 추정/.test(ads.template.outputs[0].simpleText.text), '광고: CPC 입찰가 표시');

  const geo = kf.render(report, 'geo');
  assert(isValidSkill(geo) && /(AI 엔진|실측|GEO)/.test(geo.template.outputs[0].simpleText.text), 'GEO 뷰 렌더(미설정 안내)');

  const contact = kf.renderContact();
  assert(isValidSkill(contact) && contact.template.outputs[0].textCard, '상담 CTA textCard');
  assert(contact.template.outputs[0].textCard.buttons.some((b) => b.webLinkUrl === kf.CHANNEL_URL), '상담 카드에 카카오 채널 링크');

  const ref = kf.renderRefusal();
  assert(isValidSkill(ref) && /직원 전용/.test(ref.template.outputs[0].simpleText.text), '거절 메시지');

  const ack = kf.ackData('OO치과');
  assert(ack.text && /진단 중/.test(ack.text), 'ack 데이터');

  console.log('== 웹 리포트 링크(VENOMI_SITE_BASE) ==');
  delete process.env.VENOMI_SITE_BASE;
  assert(kf.reportUrl('OO치과') === null, '미설정 시 링크 없음');
  const sumNoLink = kf.render(report, 'summary');
  assert(sumNoLink.template.outputs.length === 1, '미설정 시 요약 출력 1개(링크 카드 없음)');
  process.env.VENOMI_SITE_BASE = 'https://venomi.example.com/';
  assert(/venomi\.example\.com\/hospital-bot\/report\.html\?hospital=/.test(kf.reportUrl('대구 OO치과')), '리포트 URL 생성');
  const sumLink = kf.render(report, 'summary');
  assert(sumLink.template.outputs.length === 2 && sumLink.template.outputs[1].textCard, '설정 시 링크 카드 추가');
  assert(sumLink.template.outputs[1].textCard.buttons[0].webLinkUrl.indexOf('report.html') > 0, '웹링크 버튼');
  delete process.env.VENOMI_SITE_BASE;

  console.log('== 핸들러 감지 로직 ==');
  const api = require(path.join(__dirname, '..', '..', 'api', 'hospital-bot'));
  assert(api._internal.isKakaoSkill({ userRequest: {}, action: {} }) === true, '카카오 페이로드 감지');
  assert(api._internal.isKakaoSkill({ hospital: 'x' }) === false, '순수 API 페이로드 구분');
  assert(typeof api._internal.getQuery === 'function' && api._internal.getQuery({ url: '/api/hospital-bot?hospital=abc&geo=1' }).hospital === 'abc', 'GET 쿼리 파싱(웹 리포트)');

  console.log(fails ? `\n❌ ${fails}건 실패` : '\n✅ 전체 통과');
  process.exit(fails ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(1); });
