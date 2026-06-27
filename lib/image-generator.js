'use strict';

const https = require('https');
const sharp = require('sharp');

const OWNER  = process.env.GITHUB_OWNER  || 'recon9973-lang';
const REPO   = process.env.GITHUB_REPO   || 'desktop-tutorial';
const BRANCH = process.env.GITHUB_BRANCH || 'main';

async function generateAndSaveImage(prompt, postId, index = 0, title = '') {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) return null;

  const fullPrompt = `Professional Korean hospital marketing photography. ${prompt}. Clean, modern, trustworthy aesthetic. No text overlay. High quality realistic photo style. Bright, professional lighting.`;

  // DALL-E → base64 PNG → WebP 변환 → GitHub 저장
  const b64 = await callDallE(apiKey, fullPrompt);
  if (!b64) return null;

  const webpBuffer = await sharp(Buffer.from(b64, 'base64')).webp({ quality: 85 }).toBuffer();

  const slug = title
    ? title.replace(/[^\w가-힣]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '').slice(0, 60)
    : postId;
  const filename = index === 0 ? `${slug}.webp` : `${slug}-${index}.webp`;
  const githubPath = `venom-wordpress/preview/content/images/${filename}`;
  const saved = await saveToGitHub(webpBuffer, githubPath);

  return {
    url: saved ? `/content/images/${filename}` : null,
    githubPath: saved ? githubPath : null,
  };
}

function callDallE(apiKey, prompt) {
  const body = JSON.stringify({
    model: process.env.OPENAI_IMAGE_MODEL || 'dall-e-3',
    prompt,
    n: 1,
    size: '1792x1024',
    quality: 'standard',
    response_format: 'b64_json',
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
        try { resolve(JSON.parse(data).data?.[0]?.b64_json || null); }
        catch { resolve(null); }
      });
    });
    req.on('error', () => resolve(null));
    req.setTimeout(55000, () => { req.destroy(); resolve(null); });
    req.write(body);
    req.end();
  });
}

function saveToGitHub(buffer, filePath) {
  const TOKEN = process.env.GITHUB_TOKEN;
  if (!TOKEN) return Promise.resolve(false);

  const body = JSON.stringify({
    message: `auto: 포스트 이미지 ${filePath.split('/').pop()}`,
    content: buffer.toString('base64'),
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
      res.on('data', () => {});
      res.on('end', () => resolve(res.statusCode === 200 || res.statusCode === 201));
    });
    req.on('error', () => resolve(false));
    req.setTimeout(30000, () => { req.destroy(); resolve(false); });
    req.write(body);
    req.end();
  });
}

module.exports = { generateAndSaveImage };
