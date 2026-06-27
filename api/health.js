'use strict';

// 헬스 체크 + 시스템 종합 진단(통합).
// Vercel Hobby 플랜은 배포당 Serverless Function 12개 제한이라 별도 diag 함수 대신 여기에 통합.
//  - GET /api/health            → 기본(환경변수 존재 여부)만, 외부 호출 없음(가벼움)
//  - GET /api/health?check=full → OpenAI 키/DALL-E 접근 + GitHub 토큰/쓰기권한 실제 점검

const https = require('https');

const OWNER  = process.env.GITHUB_OWNER  || 'recon9973-lang';
const REPO   = process.env.GITHUB_REPO   || 'desktop-tutorial';
const BRANCH = process.env.GITHUB_BRANCH || 'main';

function httpGet({ hostname, path, headers, timeout = 15000 }) {
  return new Promise((resolve) => {
    const req = https.request({ hostname, path, method: 'GET', headers }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        const text = Buffer.concat(chunks).toString('utf8');
        let json = null; try { json = JSON.parse(text); } catch {}
        resolve({ status: res.statusCode, json, text });
      });
    });
    req.on('error', (e) => resolve({ status: 0, error: e.message }));
    req.setTimeout(timeout, () => { req.destroy(); resolve({ status: 0, error: 'timeout' }); });
    req.end();
  });
}

async function checkOpenAI() {
  const key = process.env.OPENAI_API_KEY;
  if (!key) return { present: false, ok: false, reason: 'OPENAI_API_KEY 미설정' };
  const r = await httpGet({
    hostname: 'api.openai.com', path: '/v1/models',
    headers: { 'Authorization': `Bearer ${key}` },
  });
  if (r.status === 200 && r.json && Array.isArray(r.json.data)) {
    const ids = r.json.data.map(m => m.id);
    const hasDallE = ids.some(id => /dall-e-3/.test(id));
    const hasText = ids.some(id => /gpt-4o-mini|gpt-4o|gpt-4/.test(id));
    return {
      present: true, ok: true, keyValid: true,
      dalle3Access: hasDallE, textModelAccess: hasText,
      reason: hasDallE ? '정상' : 'DALL-E 3 접근 권한 없음 — OpenAI 결제/이미지 권한 확인 필요',
    };
  }
  const msg = r.json && r.json.error ? r.json.error.message : (r.error || `HTTP ${r.status}`);
  return { present: true, ok: false, keyValid: false, reason: `OpenAI 키 오류: ${msg}` };
}

async function checkGitHub() {
  const token = process.env.GITHUB_TOKEN;
  if (!token) return { present: false, ok: false, reason: 'GITHUB_TOKEN 미설정' };
  const r = await httpGet({
    hostname: 'api.github.com', path: `/repos/${OWNER}/${REPO}`,
    headers: { 'Authorization': `token ${token}`, 'User-Agent': 'venom-diag/1.0', 'Accept': 'application/vnd.github.v3+json' },
  });
  if (r.status === 200 && r.json) {
    const canPush = !!(r.json.permissions && r.json.permissions.push);
    return {
      present: true, ok: canPush, tokenValid: true, repo: r.json.full_name, canPush,
      reason: canPush ? '정상(쓰기 가능)' : '쓰기 권한 없음 — 토큰에 Contents: write 권한 필요',
    };
  }
  const msg = r.json && r.json.message ? r.json.message : (r.error || `HTTP ${r.status}`);
  return { present: true, ok: false, tokenValid: false, reason: `GitHub 토큰 오류: ${msg}` };
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const base = {
    ok: true,
    hasOpenAI: !!process.env.OPENAI_API_KEY,
    hasGitHub: !!process.env.GITHUB_TOKEN,
    hasAdminSecret: !!process.env.ADMIN_SECRET,
    time: new Date().toISOString(),
  };

  // 전체 점검 요청이 아니면 기본 정보만 (외부 API 호출 없음)
  const full = (req.query && (req.query.check === 'full' || req.query.full === '1'))
    || /[?&](check=full|full=1)/.test(req.url || '');
  if (!full) return res.status(200).json(base);

  const env = {
    OPENAI_API_KEY: base.hasOpenAI,
    GITHUB_TOKEN: base.hasGitHub,
    ADMIN_SECRET: base.hasAdminSecret,
    CRON_SECRET: !!process.env.CRON_SECRET,
    GITHUB_OWNER: OWNER, GITHUB_REPO: REPO, GITHUB_BRANCH: BRANCH,
    OPENAI_TEXT_MODEL: process.env.OPENAI_TEXT_MODEL || 'gpt-4o-mini(기본)',
    OPENAI_IMAGE_MODEL: process.env.OPENAI_IMAGE_MODEL || 'dall-e-3(기본)',
  };

  const [openai, github] = await Promise.all([checkOpenAI(), checkGitHub()]);

  const imageReady = !!(openai.dalle3Access && github.canPush);
  const textReady  = !!(openai.textModelAccess || openai.keyValid);

  return res.status(200).json({
    ...base,
    env, openai, github,
    verdict: {
      textGeneration: textReady ? '가능' : '불가 — ' + (openai.reason || ''),
      imageGeneration: imageReady ? '가능' : '불가 — ' + [
        !openai.dalle3Access ? 'OpenAI: ' + (openai.reason || 'DALL-E 접근 불가') : '',
        !github.canPush ? 'GitHub: ' + (github.reason || '쓰기 불가') : '',
      ].filter(Boolean).join(' / '),
    },
  });
};
