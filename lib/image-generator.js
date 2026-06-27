'use strict';

const https = require('https');

// PNG 버퍼 → WebP 변환 (sharp 사용, 없으면 원본 반환)
async function toWebP(buffer) {
  try {
    const sharp = require('sharp');
    return await sharp(buffer).webp({ quality: 85 }).toBuffer();
  } catch {
    return buffer; // sharp 없으면 원본 반환
  }
}

/**
 * DALL-E 3로 이미지 생성 후 GitHub에 저장
 * @param {string} prompt
 * @param {string} postId
 * @param {number} index  0 or 1
 * @returns {Promise<{url:string, githubPath:string}|null>}
 */
async function generateAndSaveImage(prompt, postId, index = 0) {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) return null;

  // 병원마케팅용 프롬프트 보강
  const fullPrompt = `Professional Korean hospital marketing photography. ${prompt}.
Clean, modern, trustworthy aesthetic. No text overlay. High quality realistic photo style.
Suitable for medical marketing blog. Bright, professional lighting.`;

  // DALL-E 3 이미지 생성
  const imageUrl = await callDallE(apiKey, fullPrompt);
  if (!imageUrl) return null;

  // 이미지 다운로드
  const rawBuffer = await downloadImage(imageUrl);
  if (!rawBuffer) return { url: imageUrl, githubPath: null };

  // PNG → WebP 변환
  const imageBuffer = await toWebP(rawBuffer);

  // GitHub에 저장
  const githubPath = `venom-wordpress/preview/content/images/${postId}_${index}.webp`;
  const saved = await saveImageToGitHub(imageBuffer, githubPath);

  return {
    url: saved ? `/content/images/${postId}_${index}.webp` : imageUrl,
    githubPath: saved ? githubPath : null,
  };
}

function callDallE(apiKey, prompt) {
  const body = JSON.stringify({
    model: process.env.OPENAI_IMAGE_MODEL || 'dall-e-3',
    prompt,
    n: 1,
    size: '1024x1024',
    quality: 'standard',
    response_format: 'url',
  });

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
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          resolve(json.data?.[0]?.url || null);
        } catch { resolve(null); }
      });
    });
    req.on('error', () => resolve(null));
    req.setTimeout(55000, () => { req.destroy(); resolve(null); });
    req.write(body);
    req.end();
  });
}

function downloadImage(url) {
  return new Promise((resolve) => {
    const chunks = [];
    const urlObj = new URL(url);
    const options = {
      hostname: urlObj.hostname,
      path: urlObj.pathname + urlObj.search,
      method: 'GET',
      timeout: 30000,
    };
    https.get(options, (res) => {
      res.on('data', c => chunks.push(c));
      res.on('end', () => resolve(Buffer.concat(chunks)));
      res.on('error', () => resolve(null));
    }).on('error', () => resolve(null));
  });
}

function saveImageToGitHub(buffer, filePath) {
  const TOKEN = process.env.GITHUB_TOKEN;
  const OWNER = process.env.GITHUB_OWNER || 'recon9973-lang';
  const REPO  = process.env.GITHUB_REPO  || 'desktop-tutorial';
  const BRANCH= process.env.GITHUB_BRANCH|| 'main';
  if (!TOKEN) return Promise.resolve(false);

  const encoded = buffer.toString('base64');
  const body = JSON.stringify({
    message: `auto: 포스트 이미지 추가 ${filePath.split('/').pop()}`,
    content: encoded,
    branch: BRANCH,
  });

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
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => resolve(res.statusCode === 200 || res.statusCode === 201));
    });
    req.on('error', () => resolve(false));
    req.setTimeout(30000, () => { req.destroy(); resolve(false); });
    req.write(body);
    req.end();
  });
}

module.exports = { generateAndSaveImage };
