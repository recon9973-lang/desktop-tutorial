'use strict';

const https = require('https');

const OWNER  = process.env.GITHUB_OWNER  || 'recon9973-lang';
const REPO   = process.env.GITHUB_REPO   || 'desktop-tutorial';
const BRANCH = process.env.GITHUB_BRANCH || 'main';
const TOKEN  = process.env.GITHUB_TOKEN;
const PATH   = 'venom-wordpress/preview/content/posting-settings.json';

const DEFAULT = {
  enabled: false,
  schedules: [],
  categories: ['geo'], keywords: ['병원 GEO마케팅', 'AI 병원마케팅'],
  regions: ['서울', '강남'], extra: '',
};

function ghGet(filePath) {
  return new Promise((resolve) => {
    if (!TOKEN) return resolve(null);
    const req = https.request({
      hostname: 'api.github.com',
      path: `/repos/${OWNER}/${REPO}/contents/${filePath}`,
      method: 'GET',
      headers: {
        'Authorization': `token ${TOKEN}`,
        'User-Agent': 'venom-autopost/1.0',
        'Accept': 'application/vnd.github.v3+json',
      },
    }, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try {
          const body = JSON.parse(data);
          if (res.statusCode === 200) resolve(body);
          else resolve(null);
        } catch { resolve(null); }
      });
    });
    req.on('error', () => resolve(null));
    req.end();
  });
}

function ghPut(filePath, content, sha, message) {
  return new Promise((resolve) => {
    if (!TOKEN) return resolve(false);
    const encoded = Buffer.from(JSON.stringify(content, null, 2)).toString('base64');
    const body = JSON.stringify({ message, content: encoded, branch: BRANCH, ...(sha ? { sha } : {}) });
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
    req.write(body);
    req.end();
  });
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();

  try {
    if (req.method === 'GET') {
      const file = await ghGet(PATH);
      if (file && file.content) {
        const settings = JSON.parse(Buffer.from(file.content, 'base64').toString('utf8'));
        return res.status(200).json(settings);
      }
      return res.status(200).json(DEFAULT);
    }

    if (req.method === 'POST') {
      // ADMIN_SECRET 설정 시 인증 요구 (무인증 설정 변경 차단)
      const secret = process.env.ADMIN_SECRET;
      if (secret) {
        const auth = (req.headers['authorization'] || '').replace('Bearer ', '').trim();
        if (auth !== secret) return res.status(401).json({ error: '인증 필요(ADMIN_SECRET)' });
      }
      const settings = { ...DEFAULT, ...(req.body || {}), updatedAt: new Date().toISOString() };
      const existing = await ghGet(PATH);
      const sha = existing ? existing.sha : undefined;
      const saved = await ghPut(PATH, settings, sha, 'config: 자동 포스팅 설정 업데이트');
      return res.status(200).json({ ok: true, savedToGitHub: saved, settings });
    }

    return res.status(405).json({ error: 'GET or POST only' });
  } catch (e) {
    console.error('[posting-settings]', e);
    return res.status(500).json({ error: e.message });
  }
};
