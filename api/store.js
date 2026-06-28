'use strict';

// 통합 서버 저장소 — 관리자 데이터(설정·로고·미디어·카드뉴스)를 GitHub JSON으로 영속.
// 그동안 localStorage(브라우저 한정)라 교차 기기·사용자에게 안 보이던 문제를 해결.
//  - GET  /api/store?type=settings        → 저장된 JSON 반환(없으면 기본값)
//  - POST /api/store  {type, data}        → 해당 type JSON을 GitHub에 저장(덮어쓰기)
// Vercel Hobby 함수 12개 한도 때문에 메뉴별 엔드포인트 대신 type 파라미터로 통합.

const https = require('https');

const OWNER  = process.env.GITHUB_OWNER  || 'recon9973-lang';
const REPO   = process.env.GITHUB_REPO   || 'desktop-tutorial';
const BRANCH = process.env.GITHUB_BRANCH || 'main';
const TOKEN  = process.env.GITHUB_TOKEN;

// 허용 type → 저장 경로 (화이트리스트: 임의 경로 쓰기 방지)
const TYPES = {
  settings: 'venom-wordpress/preview/content/settings.json',
  logos:    'venom-wordpress/preview/content/logos.json',
  media:    'venom-wordpress/preview/content/media.json',
  cardnews: 'venom-wordpress/preview/content/cardnews.json',
};
const DEFAULTS = { settings: {}, logos: [], media: [], cardnews: [] };

function gh(method, filePath, body) {
  const payload = body ? JSON.stringify(body) : undefined;
  return new Promise((resolve) => {
    const req = https.request({
      hostname: 'api.github.com',
      path: `/repos/${OWNER}/${REPO}/contents/${filePath}` + (method === 'GET' ? `?ref=${BRANCH}` : ''),
      method,
      headers: {
        'Authorization': `token ${TOKEN}`,
        'User-Agent': 'venom-store/1.0',
        'Accept': 'application/vnd.github.v3+json',
        ...(payload ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) } : {}),
      },
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        const text = Buffer.concat(chunks).toString('utf8');
        let json = null; try { json = JSON.parse(text); } catch {}
        resolve({ status: res.statusCode, json });
      });
    });
    req.on('error', () => resolve({ status: 0 }));
    req.setTimeout(20000, () => { req.destroy(); resolve({ status: 0 }); });
    if (payload) req.write(payload);
    req.end();
  });
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const type = (req.query && req.query.type) || (req.body && req.body.type);
  if (!type || !TYPES[type]) return res.status(400).json({ error: 'type 필수(settings|logos|media|cardnews)' });
  const filePath = TYPES[type];

  // 읽기: 누구나(공개 사이트도 읽음). 캐시 방지.
  if (req.method === 'GET') {
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    if (!TOKEN) return res.status(200).json({ ok: true, data: DEFAULTS[type], note: 'GITHUB_TOKEN 미설정 — 기본값' });
    const r = await gh('GET', filePath);
    if (r.status === 404) return res.status(200).json({ ok: true, data: DEFAULTS[type] });
    if (r.status === 200 && r.json && r.json.content) {
      try {
        const data = JSON.parse(Buffer.from(r.json.content, 'base64').toString('utf8'));
        return res.status(200).json({ ok: true, data });
      } catch { return res.status(200).json({ ok: true, data: DEFAULTS[type] }); }
    }
    return res.status(200).json({ ok: true, data: DEFAULTS[type], note: `GitHub ${r.status}` });
  }

  // 쓰기: ADMIN_SECRET 설정 시 인증 요구.
  if (req.method === 'POST') {
    const secret = process.env.ADMIN_SECRET;
    if (secret) {
      const auth = (req.headers['authorization'] || '').replace('Bearer ', '').trim();
      if (auth !== secret) return res.status(401).json({ error: 'ADMIN_SECRET 불일치' });
    }
    if (!TOKEN) return res.status(500).json({ error: 'GITHUB_TOKEN 미설정' });
    const data = req.body && req.body.data;
    if (data === undefined) return res.status(400).json({ error: 'data 필수' });

    // 기존 sha 조회(덮어쓰기용)
    const cur = await gh('GET', filePath);
    const sha = (cur.status === 200 && cur.json) ? cur.json.sha : undefined;
    const content = Buffer.from(JSON.stringify(data, null, 2)).toString('base64');
    const put = await gh('PUT', filePath, { message: `admin: ${type} 설정 업데이트`, content, branch: BRANCH, ...(sha ? { sha } : {}) });
    if (put.status === 200 || put.status === 201) return res.status(200).json({ ok: true });
    return res.status(500).json({ error: `GitHub 저장 실패 ${put.status}` + (put.json && put.json.message ? `: ${put.json.message}` : '') });
  }

  return res.status(405).json({ error: 'GET/POST only' });
};
