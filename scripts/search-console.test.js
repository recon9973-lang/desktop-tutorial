'use strict';

// node scripts/search-console.test.js
const assert = require('assert');
const crypto = require('crypto');
const G = require('../venom-wordpress/preview/lib/search-console');

let pass = 0;
function test(n, fn){ try{ fn(); pass++; console.log('  ✓ '+n); }catch(e){ console.error('  ✗ '+n+'\n    '+e.message); process.exitCode=1; } }

test('loadConfig: 개별 env(클라이언트/키/사이트)', () => {
  const cfg = G.loadConfig({ GSC_CLIENT_EMAIL: 'a@b.iam', GSC_PRIVATE_KEY: 'k', GSC_SITE_URL: 'https://x/' });
  assert.ok(cfg);
  assert.strictEqual(cfg.clientEmail, 'a@b.iam');
  assert.strictEqual(cfg.siteUrl, 'https://x/');
});

test('loadConfig: \\n 이스케이프 복원', () => {
  const cfg = G.loadConfig({ GSC_CLIENT_EMAIL: 'a@b', GSC_PRIVATE_KEY: 'line1\\nline2', GSC_SITE_URL: 's' });
  assert.ok(cfg.privateKey.includes('\n'));
  assert.ok(!cfg.privateKey.includes('\\n'));
});

test('loadConfig: JSON 서비스계정', () => {
  const json = JSON.stringify({ client_email: 'svc@p.iam', private_key: 'PK' });
  const cfg = G.loadConfig({ GSC_SERVICE_ACCOUNT_JSON: json, GSC_SITE_URL: 'sc-domain:x' });
  assert.strictEqual(cfg.clientEmail, 'svc@p.iam');
  assert.strictEqual(cfg.siteUrl, 'sc-domain:x');
});

test('loadConfig: 미설정이면 null + isConfigured false', () => {
  assert.strictEqual(G.loadConfig({}), null);
  assert.strictEqual(G.isConfigured({}), false);
});

test('buildJwtClaims: 필수 필드 + 1시간 만료', () => {
  const c = G.buildJwtClaims('svc@p.iam', 1000);
  assert.strictEqual(c.iss, 'svc@p.iam');
  assert.strictEqual(c.aud, 'https://oauth2.googleapis.com/token');
  assert.ok(c.scope.includes('webmasters.readonly'));
  assert.strictEqual(c.exp - c.iat, 3600);
});

test('signJwt: RS256 서명이 공개키로 검증된다', () => {
  const { privateKey, publicKey } = crypto.generateKeyPairSync('rsa', { modulusLength: 2048 });
  const claims = G.buildJwtClaims('svc@p.iam', 1000);
  const jwt = G.signJwt(claims, privateKey);
  const parts = jwt.split('.');
  assert.strictEqual(parts.length, 3);
  const signingInput = parts[0] + '.' + parts[1];
  const sig = Buffer.from(parts[2].replace(/-/g, '+').replace(/_/g, '/'), 'base64');
  const ok = crypto.verify('RSA-SHA256', Buffer.from(signingInput), publicKey, sig);
  assert.strictEqual(ok, true);
  // payload 디코딩 확인
  const payload = JSON.parse(Buffer.from(parts[1].replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf8'));
  assert.strictEqual(payload.iss, 'svc@p.iam');
});

test('parseSearchAnalytics: rows 합계/필드', () => {
  const r = G.parseSearchAnalytics({ rows: [
    { keys: ['임플란트'], clicks: 10, impressions: 100, ctr: 0.1, position: 4.2 },
    { keys: ['치과'], clicks: 5, impressions: 100, ctr: 0.05, position: 8 },
  ]});
  assert.strictEqual(r.rows.length, 2);
  assert.strictEqual(r.totals.clicks, 15);
  assert.strictEqual(r.totals.impressions, 200);
  assert.ok(Math.abs(r.totals.ctr - 0.075) < 1e-9);
});

test('parseSearchAnalytics: 빈 응답 안전', () => {
  const r = G.parseSearchAnalytics({});
  assert.deepStrictEqual(r.rows, []);
  assert.strictEqual(r.totals.clicks, 0);
  assert.strictEqual(r.totals.ctr, 0);
});

console.log(`\n${pass} passed`);
