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

function httpPost({ hostname, path, headers, body, timeout = 18000 }) {
  return new Promise((resolve) => {
    const payload = JSON.stringify(body);
    const req = https.request({ hostname, path, method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) } }, (res) => {
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
    req.write(payload); req.end();
  });
}

// 이미지 생성 정밀 진단: 접근 가능한 이미지 모델 목록 + 실제 생성 시도 후 OpenAI의 정확한 에러 수집
async function probeImage() {
  const key = process.env.OPENAI_API_KEY;
  if (!key) return { error: 'OPENAI_API_KEY 미설정' };
  const auth = { 'Authorization': `Bearer ${key}` };

  // 1) 키가 접근 가능한 이미지 관련 모델 목록
  const models = await httpGet({ hostname: 'api.openai.com', path: '/v1/models', headers: auth });
  let imageModels = [];
  if (models.status === 200 && models.json && Array.isArray(models.json.data)) {
    imageModels = models.json.data.map(m => m.id).filter(id => /dall-e|gpt-image|image/.test(id)).sort();
  }

  // 2) 설정된 이미지 모델로 실제 1장 생성 시도 → 정확한 에러/성공 확인
  const model = process.env.OPENAI_IMAGE_MODEL || 'gpt-image-1';
  const genBody = { model, prompt: 'a plain white square, minimal test', n: 1, size: '1024x1024' };
  if (/^dall-e/.test(model)) genBody.response_format = 'b64_json'; else genBody.quality = 'medium';
  const gen = await httpPost({
    hostname: 'api.openai.com', path: '/v1/images/generations', headers: auth, body: genBody,
  });
  let test;
  if (gen.status === 200 && gen.json && gen.json.data) {
    test = { ok: true, status: 200, note: '이미지 생성 성공 — 이미지 기능 정상 동작 가능' };
  } else {
    const err = gen.json && gen.json.error ? gen.json.error : {};
    test = {
      ok: false, status: gen.status,
      errorType: err.type || null, errorCode: err.code || null,
      message: err.message || gen.error || gen.text?.slice(0, 300) || '알 수 없음',
    };
  }

  return { testedModel: model, accessibleImageModels: imageModels, testGeneration: test };
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
    const configured = process.env.OPENAI_IMAGE_MODEL || 'gpt-image-1';
    const hasImage = ids.includes(configured) || ids.some(id => /gpt-image|dall-e-3/.test(id));
    const hasText = ids.some(id => /gpt-4o-mini|gpt-4o|gpt-4/.test(id));
    return {
      present: true, ok: true, keyValid: true,
      imageModelAccess: hasImage, dalle3Access: hasImage, // dalle3Access는 하위호환 별칭
      textModelAccess: hasText, configuredImageModel: configured,
      reason: hasImage ? '정상' : '사용 가능한 이미지 모델 없음 — OpenAI 결제/모델 권한 확인 필요',
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
    ver: 'phase2-deploy-2026-06-28o', // 배포 반영 확인용 마커(이 값이 보이면 최신 코드 라이브)
    hasOpenAI: !!process.env.OPENAI_API_KEY,
    hasGitHub: !!process.env.GITHUB_TOKEN,
    hasAdminSecret: !!process.env.ADMIN_SECRET,
    hasKV: !!((process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL) && (process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN)),
    hasNaverAd: !!((process.env.NAVER_AD_API_KEY || process.env.NAVER_ACCESS_LICENSE) && (process.env.NAVER_AD_SECRET || process.env.NAVER_SECRET_KEY) && (process.env.NAVER_AD_CUSTOMER_ID || process.env.NAVER_CUSTOMER_ID)),
    hasNaverOpen: !!(process.env.NAVER_CLIENT_ID && process.env.NAVER_CLIENT_SECRET),
    hasPerplexity: !!process.env.PERPLEXITY_API_KEY,
    hasPSI: !!process.env.PSI_KEY,
    time: new Date().toISOString(),
  };

  const wantImage = (req.query && req.query.check === 'image') || /[?&]check=image\b/.test(req.url || '');
  // 전체 파이프라인 진단(생성→WASM변환→GitHub저장)을 실제로 1회 실행
  const wantImageFull = (req.query && req.query.check === 'imagefull') || /[?&]check=imagefull\b/.test(req.url || '');
  const full = (req.query && (req.query.check === 'full' || req.query.full === '1'))
    || /[?&](check=full|full=1)/.test(req.url || '');

  // 심층 점검(full/image)은 외부 API 호출(비용 발생)이므로 ADMIN_SECRET 설정 시 인증 요구.
  // 미설정이면 기존처럼 허용(초기 진단 편의). 설정되면 관리자 토큰 필요.
  if ((wantImage || wantImageFull || full) && process.env.ADMIN_SECRET) {
    const auth = (req.headers['authorization'] || '').replace('Bearer ', '').trim();
    if (auth !== process.env.ADMIN_SECRET) {
      return res.status(401).json({ ...base, error: '심층 점검은 인증 필요(ADMIN_SECRET)' });
    }
  }

  // 이미지 정밀 진단(?check=image): 실제 생성 시도로 OpenAI의 정확한 사유 확인
  if (wantImage) {
    const image = await probeImage();
    return res.status(200).json({ ...base, image });
  }

  // 전체 파이프라인 진단(?check=imagefull): 실제 코드(generateAndSaveImage)를 그대로 1회 실행.
  // OpenAI 생성 → WASM WebP 변환 → GitHub 커밋까지 전 과정을 검증하고, 실패 시 정확한 단계/사유를 반환.
  if (wantImageFull) {
    const t0 = Date.now();
    let out;
    try {
      const { generateAndSaveImage } = require('../lib/image-generator');
      const r = await generateAndSaveImage(
        'modern clean hospital reception area, pipeline diagnostic',
        'diag_' + t0, 0, 'diag-pipeline-test');
      out = { ...r, ms: Date.now() - t0,
        verdict: r && r.url ? '성공 — 이 URL이 보이면 전체 파이프라인 정상' : '실패 — error 사유 확인' };
    } catch (e) {
      out = { url: null, error: '예외: ' + (e && e.message), stack: (e && e.stack || '').split('\n').slice(0,4).join(' | '), ms: Date.now() - t0 };
    }
    return res.status(200).json({ ...base, imageFull: out });
  }

  // 전체 점검 요청이 아니면 기본 정보만 (외부 API 호출 없음)
  if (!full) return res.status(200).json(base);

  const env = {
    OPENAI_API_KEY: base.hasOpenAI,
    GITHUB_TOKEN: base.hasGitHub,
    ADMIN_SECRET: base.hasAdminSecret,
    CRON_SECRET: !!process.env.CRON_SECRET,
    GITHUB_OWNER: OWNER, GITHUB_REPO: REPO, GITHUB_BRANCH: BRANCH,
    OPENAI_TEXT_MODEL: process.env.OPENAI_TEXT_MODEL || 'gpt-4o-mini(기본)',
    OPENAI_IMAGE_MODEL: process.env.OPENAI_IMAGE_MODEL || 'gpt-image-1(기본)',
  };

  const [openai, github] = await Promise.all([checkOpenAI(), checkGitHub()]);

  const imageReady = !!(openai.imageModelAccess && github.canPush);
  const textReady  = !!(openai.textModelAccess || openai.keyValid);

  return res.status(200).json({
    ...base,
    env, openai, github,
    verdict: {
      textGeneration: textReady ? '가능' : '불가 — ' + (openai.reason || ''),
      imageGeneration: imageReady ? '가능' : '불가 — ' + [
        !openai.imageModelAccess ? 'OpenAI: ' + (openai.reason || '이미지 모델 접근 불가') : '',
        !github.canPush ? 'GitHub: ' + (github.reason || '쓰기 불가') : '',
      ].filter(Boolean).join(' / '),
    },
  });
};
