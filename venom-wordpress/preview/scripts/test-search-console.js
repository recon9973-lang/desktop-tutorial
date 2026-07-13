#!/usr/bin/env node
'use strict';

/**
 * lib/search-console.js 오프라인 검증 — 자격증명·네트워크 없이 순수 로직만 확인.
 * 실행:  node scripts/test-search-console.js   (실패 시 exit 1)
 *
 * 커버:
 *   - loadConfig: env 파싱(개별 키 / SERVICE_ACCOUNT_JSON / \n 복원 / 미설정)
 *   - buildJwtClaims: iss·aud·scope·exp(=iat+3600)
 *   - signJwt: RS256 서명 → 공개키로 검증 왕복(진짜 서명인지)
 *   - parseSearchAnalytics: rows 매핑 + totals(ctr 재계산)
 *   - isConfigured: 설정 유무 판정
 */

const crypto = require('crypto');
const SC = require('../lib/search-console.js');

let pass = 0, fail = 0;
function ok(name, cond) { cond ? (pass++, console.log('  ✓ ' + name)) : (fail++, console.error('  ✗ ' + name)); }

// 테스트용 RSA 키쌍(런타임 생성 — 저장소에 비밀키 없음)
const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', { modulusLength: 2048 });
const PEM = privateKey.export({ type: 'pkcs1', format: 'pem' });

console.log('loadConfig');
{
  ok('개별 키 파싱', (() => {
    const c = SC.loadConfig({ GSC_CLIENT_EMAIL: 'a@b.iam', GSC_PRIVATE_KEY: 'k', GSC_SITE_URL: 'sc-domain:x.com' });
    return c && c.clientEmail === 'a@b.iam' && c.siteUrl === 'sc-domain:x.com';
  })());
  ok('SERVICE_ACCOUNT_JSON 파싱', (() => {
    const j = JSON.stringify({ client_email: 'svc@p.iam', private_key: 'PK' });
    const c = SC.loadConfig({ GSC_SERVICE_ACCOUNT_JSON: j, GSC_SITE_URL: 'https://x.com/' });
    return c && c.clientEmail === 'svc@p.iam' && c.privateKey === 'PK';
  })());
  ok('\\n 이스케이프 복원', (() => {
    const c = SC.loadConfig({ GSC_CLIENT_EMAIL: 'a@b', GSC_PRIVATE_KEY: 'l1\\nl2', GSC_SITE_URL: 'x' });
    return c && c.privateKey === 'l1\nl2';
  })());
  ok('미설정 시 null', SC.loadConfig({}) === null);
  ok('siteUrl 없으면 null', SC.loadConfig({ GSC_CLIENT_EMAIL: 'a', GSC_PRIVATE_KEY: 'k' }) === null);
}

console.log('buildJwtClaims');
{
  const c = SC.buildJwtClaims('svc@p.iam', 1000, undefined);
  ok('iss = clientEmail', c.iss === 'svc@p.iam');
  ok('aud = token endpoint', /oauth2\.googleapis\.com\/token$/.test(c.aud));
  ok('scope = webmasters.readonly', /webmasters\.readonly$/.test(c.scope));
  ok('exp = iat + 3600', c.exp === c.iat + 3600 && c.iat === 1000);
}

console.log('signJwt (RS256 왕복 검증)');
{
  const claims = SC.buildJwtClaims('a@b.iam', 1234, undefined);
  const jwt = SC.signJwt(claims, PEM);
  const parts = jwt.split('.');
  ok('3-파트 구조', parts.length === 3);
  const signingInput = parts[0] + '.' + parts[1];
  const sig = Buffer.from(parts[2].replace(/-/g, '+').replace(/_/g, '/'), 'base64');
  ok('공개키로 서명 검증 통과', crypto.verify('RSA-SHA256', Buffer.from(signingInput), publicKey, sig));
  const decodedHeader = JSON.parse(Buffer.from(parts[0].replace(/-/g, '+').replace(/_/g, '/'), 'base64'));
  ok('header alg=RS256', decodedHeader.alg === 'RS256');
}

console.log('parseSearchAnalytics');
{
  const p = SC.parseSearchAnalytics({ rows: [
    { keys: ['구미치과'], clicks: 10, impressions: 100, ctr: 0.1, position: 3.2 },
    { keys: ['임플란트'], clicks: 5, impressions: 300, ctr: 0.0167, position: 8.1 },
  ] });
  ok('rows 매핑', p.rows.length === 2 && p.rows[0].keys[0] === '구미치과');
  ok('totals.clicks 합산', p.totals.clicks === 15);
  ok('totals.impressions 합산', p.totals.impressions === 400);
  ok('totals.ctr 재계산', Math.abs(p.totals.ctr - 15 / 400) < 1e-9);
  const empty = SC.parseSearchAnalytics({});
  ok('빈 응답 안전', empty.rows.length === 0 && empty.totals.ctr === 0);
}

console.log('isConfigured');
{
  ok('설정됨 → true', SC.isConfigured({ GSC_CLIENT_EMAIL: 'a', GSC_PRIVATE_KEY: 'k', GSC_SITE_URL: 'x' }) === true);
  ok('미설정 → false', SC.isConfigured({}) === false);
}

console.log(`\n${fail === 0 ? '✅' : '❌'} search-console: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
