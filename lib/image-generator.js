'use strict';

const https = require('https');
const sharp = require('sharp');

const OWNER  = process.env.GITHUB_OWNER  || 'recon9973-lang';
const REPO   = process.env.GITHUB_REPO   || 'desktop-tutorial';
const BRANCH = process.env.GITHUB_BRANCH || 'main';

// 항상 { url, githubPath, error } 형태로 반환 — 실패 시 error에 사유를 담아
// 호출부(API 응답)에서 화면에 표시할 수 있게 한다(조용한 실패 방지).
async function generateAndSaveImage(prompt, postId, index = 0, title = '') {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) return { url: null, githubPath: null, error: 'OPENAI_API_KEY 미설정(Vercel 환경변수)' };

  const fullPrompt = `Professional Korean hospital marketing photography. ${prompt}. Clean, modern, trustworthy aesthetic. No text overlay. High quality realistic photo style. Bright, professional lighting.`;

  // DALL-E → base64 PNG → WebP 변환 → GitHub 저장
  const dalle = await callDallE(apiKey, fullPrompt);
  if (!dalle.b64) return { url: null, githubPath: null, error: 'DALL-E 생성 실패: ' + (dalle.error || '알 수 없음') };

  let webpBuffer;
  try {
    webpBuffer = await sharp(Buffer.from(dalle.b64, 'base64')).webp({ quality: 85 }).toBuffer();
  } catch (e) {
    return { url: null, githubPath: null, error: 'WebP 변환(sharp) 실패: ' + e.message };
  }

  const slug = title
    ? title.replace(/[^\w가-힣]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '').slice(0, 60)
    : postId;
  const filename = index === 0 ? `${slug}.webp` : `${slug}-${index}.webp`;
  const githubPath = `venom-wordpress/preview/content/images/${filename}`;
  const saved = await saveToGitHub(webpBuffer, githubPath);
  if (!saved.ok) return { url: null, githubPath: null, error: 'GitHub 저장 실패: ' + (saved.error || '') };

  return { url: `/content/images/${filename}`, githubPath, error: null };
}

function callDallE(apiKey, prompt) {
  // 기본 모델을 gpt-image-1로 (dall-e-3는 2026년 폐기됨). 환경변수로 override 가능.
  const model = process.env.OPENAI_IMAGE_MODEL || 'gpt-image-1';
  const reqBody = {
    model,
    prompt,
    n: 1,
    size: process.env.OPENAI_IMAGE_SIZE || '1024x1024', // gpt-image: 1024x1024|1536x1024|1024x1536|auto
  };
  if (/^dall-e/.test(model)) {
    // 구형 DALL-E 계열: response_format/standard 사용
    reqBody.response_format = 'b64_json';
    reqBody.quality = 'standard';
  } else {
    // gpt-image 계열: 항상 b64 반환(response_format 미지원), quality는 low|medium|high|auto
    reqBody.quality = process.env.OPENAI_IMAGE_QUALITY || 'medium';
  }
  const body = JSON.stringify(reqBody);

  // { b64, error } 반환
  return new Promise((resolve) => {
    const req = https.request({
      hostname: 'api.openai.com',
      path: '/v1/images/generations',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
        'Content-Length': Buffer.byteLength(body),
      },
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        const data = Buffer.concat(chunks).toString('utf8');
        try {
          const json = JSON.parse(data);
          if (json.error) return resolve({ b64: null, error: `${res.statusCode} ${json.error.message || json.error.code || ''}`.trim() });
          const b64 = json.data?.[0]?.b64_json;
          resolve(b64 ? { b64, error: null } : { b64: null, error: `HTTP ${res.statusCode} 응답에 이미지 데이터 없음` });
        } catch (e) {
          resolve({ b64: null, error: `응답 파싱 실패(HTTP ${res.statusCode})` });
        }
      });
    });
    req.on('error', (e) => resolve({ b64: null, error: '네트워크 오류: ' + e.message }));
    req.setTimeout(55000, () => { req.destroy(); resolve({ b64: null, error: 'DALL-E 타임아웃(55초)' }); });
    req.write(body);
    req.end();
  });
}

// GitHub Contents API GET — 기존 파일 sha 조회(없으면 null). 덮어쓰기에 필요.
function getExistingSha(filePath) {
  const TOKEN = process.env.GITHUB_TOKEN;
  return new Promise((resolve) => {
    const req = https.request({
      hostname: 'api.github.com',
      path: `/repos/${OWNER}/${REPO}/contents/${filePath}?ref=${BRANCH}`,
      method: 'GET',
      headers: {
        'Authorization': `token ${TOKEN}`,
        'User-Agent': 'venom-autopost/1.0',
        'Accept': 'application/vnd.github.v3+json',
      },
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')).sha || null); }
        catch { resolve(null); }
      });
    });
    req.on('error', () => resolve(null));
    req.setTimeout(15000, () => { req.destroy(); resolve(null); });
    req.end();
  });
}

// { ok, error } 반환. 같은 경로 파일이 있으면 sha로 덮어쓰기.
async function saveToGitHub(buffer, filePath) {
  const TOKEN = process.env.GITHUB_TOKEN;
  if (!TOKEN) return { ok: false, error: 'GITHUB_TOKEN 미설정(Vercel 환경변수)' };

  const sha = await getExistingSha(filePath);
  const payload = {
    message: `auto: 포스트 이미지 ${filePath.split('/').pop()}`,
    content: buffer.toString('base64'),
    branch: BRANCH,
  };
  if (sha) payload.sha = sha; // 기존 파일 덮어쓰기
  const body = JSON.stringify(payload);

  return new Promise((resolve) => {
    const req = https.request({
      hostname: 'api.github.com',
      path: `/repos/${OWNER}/${REPO}/contents/${filePath}`,
      method: 'PUT',
      headers: {
        'Authorization': `token ${TOKEN}`,
        'User-Agent': 'venom-autopost/1.0',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
      },
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        if (res.statusCode === 200 || res.statusCode === 201) return resolve({ ok: true, error: null });
        let msg = `HTTP ${res.statusCode}`;
        try { const j = JSON.parse(Buffer.concat(chunks).toString('utf8')); if (j.message) msg += ` ${j.message}`; } catch {}
        resolve({ ok: false, error: msg });
      });
    });
    req.on('error', (e) => resolve({ ok: false, error: '네트워크 오류: ' + e.message }));
    req.setTimeout(30000, () => { req.destroy(); resolve({ ok: false, error: 'GitHub 저장 타임아웃(30초)' }); });
    req.write(body);
    req.end();
  });
}

module.exports = { generateAndSaveImage };
