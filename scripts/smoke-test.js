'use strict';

// 네트워크 없이 도는 스모크 테스트 — lib/api 모듈 로드 + 순수함수 계약 검증.
// 실행: npm test  (CI/로컬에서 회귀 방지용 안전망)

let pass = 0, fail = 0;
function ok(name, cond) {
  if (cond) { pass++; console.log('  ✅ ' + name); }
  else { fail++; console.log('  ❌ ' + name); }
}
async function main() {
  console.log('▶ tone-engine');
  const te = require('../lib/tone-engine');
  ok('buildToneDirective 빈 입력 → 빈 문자열(하위호환)', te.buildToneDirective({}) === '');
  ok('resolveTonePreset 구간', te.resolveTonePreset(10) === 'warm' && te.resolveTonePreset(50) === 'balanced' && te.resolveTonePreset(90) === 'professional');
  ok('resolveTarget 부분일치', te.resolveTarget('환자') === '환자 본인');
  const dir = te.buildToneDirective({ target: '직장인', tone: 20 });
  ok('지시 블록에 페르소나·말투 포함', dir.includes('독자 페르소나') && dir.includes('구어체') && dir.includes('문어체'));

  console.log('▶ image-generator');
  const ig = require('../lib/image-generator');
  ok('exports', typeof ig.generateImageB64 === 'function' && typeof ig.callDallE === 'function');
  ok('STYLE_PRESETS 5종', ig.STYLE_PRESETS && Object.keys(ig.STYLE_PRESETS).length >= 5);
  const noKey = await ig.generateImageB64('x', { style: 'photo' });
  ok('키 없으면 구조화 에러', noKey.b64 === null && /OPENAI_API_KEY/.test(noKey.error || ''));

  console.log('▶ wp-client');
  const wp = require('../lib/wp-client');
  const noCreds = await wp.createWpDraft({});
  ok('자격증명 없으면 에러', noCreds.ok === false && /필수/.test(noCreds.error || ''));
  const noBody = await wp.createWpDraft({ siteUrl: 'https://x.com', user: 'u', appPassword: 'p' });
  ok('본문 없으면 에러', noBody.ok === false && /필수/.test(noBody.error || ''));

  console.log('▶ keyword-research');
  const kr = require('../lib/keyword-research');
  ok('looksLikeQuestion', kr.looksLikeQuestion('거북목 병원 가야 하나요?') === true && kr.looksLikeQuestion('거북목 추천') === false);
  ok('buildResearchPrompt 빈 데이터 → 빈 문자열', kr.buildResearchPrompt({ related: [], questions: [] }) === '');

  console.log('▶ medical-ad-validator');
  const mav = require('../lib/medical-ad-validator');
  const bad = mav.validateMedicalAd('최고의 완치 100% 보장');
  ok('금지어 검출', bad.pass === false);
  const fixed = mav.autoFix('최고의 완치');
  ok('autoFix 후 통과', mav.validateMedicalAd(fixed).pass === true);

  console.log('▶ api 모듈 로드');
  ['generate-post', 'generate-image', 'keywords', 'wp-draft', 'publish-post', 'health'].forEach(n => {
    let okLoad = false;
    try { okLoad = typeof require('../api/' + n) === 'function'; } catch (e) { okLoad = false; }
    ok('api/' + n, okLoad);
  });

  console.log('▶ vercel.json');
  const vercel = require('../vercel.json');
  const fns = Object.keys(vercel.functions || {});
  ok('신규 함수 등록', ['api/generate-image.js', 'api/keywords.js', 'api/wp-draft.js'].every(f => fns.includes(f)));

  console.log('\n' + (fail === 0 ? `🎉 전부 통과 (${pass})` : `⚠️ 실패 ${fail} / 통과 ${pass}`));
  process.exit(fail === 0 ? 0 : 1);
}
main().catch(e => { console.error('스모크 테스트 예외:', e); process.exit(1); });
