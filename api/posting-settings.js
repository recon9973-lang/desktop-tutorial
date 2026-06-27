'use strict';

// 설정을 GitHub에 JSON으로 저장/조회
const https = require('https');

const OWNER = process.env.GITHUB_OWNER || 'recon9973-lang';
const REPO  = process.env.GITHUB_REPO  || 'desktop-tutorial';
const BRANCH= process.env.GITHUB_BRANCH|| 'main';
const TOKEN = process.env.GITHUB_TOKEN;
const SETTINGS_PATH = 'venom-wordpress/preview/content/posting-settings.json';

function authCheck(req) {
  const secret = process.env.ADMIN_SECRET;
  if (!secret) return true;
  return (req.headers['authorization'] || '') === `Bearer ${secret}`;
}

function ghRequest(method, filePath, body) {
  const payload = body ? JSON.stringify(body) : undefined;
  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: 'api.github.com',
      path: `/repos/${OWNER}/${REPO}/contents/${filePath}`,
      method,
      headers: {
        'Authorization': `token ${TOKEN}`,
        'User-Agent': 'venom-autopost/1.0',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        ...(payload ? { 'Content-Length': Buffer.byteLength(payload) } : {}),
      },
    }, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(data) }); }
        catch(e) { resolve({ status: res.statusCode, body: data }); }
      });
    });
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });
}

const DEFAULT_SETTINGS = {
  enabled: false,
  dailyCount: 1,
  categories: ['geo'],
  keywords: ['병원 GEO마케팅', 'AI 병원마케팅'],
  regions: ['서울', '강남'],
  extra: '',
  schedule: '0 9 * * *',
};

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (!authCheck(req)) return res.status(401).json({ error: '인증 실패' });

  if (req.method === 'GET') {
    if (!TOKEN) return res.status(200).json(DEFAULT_SETTINGS);
    const r = await ghRequest('GET', SETTINGS_PATH);
    if (r.status === 404) return res.status(200).json(DEFAULT_SETTINGS);
    try {
      const content = JSON.parse(Buffer.from(r.body.content, 'base64').toString('utf8'));
      return res.status(200).json(content);
    } catch(e) {
      return res.status(200).json(DEFAULT_SETTINGS);
    }
  }

  if (req.method === 'POST') {
    if (!TOKEN) return res.status(200).json({ ok: true, saved: false, note: 'GITHUB_TOKEN 없음 — 설정이 서버에 저장되지 않습니다.' });
    const settings = { ...DEFAULT_SETTINGS, ...req.body, updatedAt: new Date().toISOString() };
    // 기존 sha 가져오기
    const existing = await ghRequest('GET', SETTINGS_PATH);
    const sha = existing.status === 200 ? existing.body.sha : undefined;
    const encoded = Buffer.from(JSON.stringify(settings, null, 2)).toString('base64');
    const putBody = { message: 'config: 자동 포스팅 설정 업데이트', content: encoded, branch: BRANCH };
    if (sha) putBody.sha = sha;
    const r = await ghRequest('PUT', SETTINGS_PATH, putBody);
    if (r.status !== 200 && r.status !== 201) {
      return res.status(500).json({ error: 'GitHub 저장 실패', detail: r.body });
    }
    return res.status(200).json({ ok: true, settings });
  }

  return res.status(405).json({ error: 'GET or POST only' });
};
