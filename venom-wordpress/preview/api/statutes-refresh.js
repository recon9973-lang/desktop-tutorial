'use strict';

/**
 * 의료법 조문 최신본 수집 엔드포인트 (Vercel에서 실행) — 최신성(법 개정) 반영용.
 *
 *  GET  /api/statutes-refresh              → law.go.kr에서 조문 수집 시도 후 결과 반환(테스트용)
 *  GET  /api/statutes-refresh?save=1       → 성공 시 chatbot/data/sources/statutes.json 로 GitHub 커밋(영속)
 *                                            (save는 ADMIN_SECRET 설정 시 Bearer 인증 필요)
 *
 * 필요 env: LAW_OC(법령API OC, open.law.go.kr 발급). save 시 GITHUB_TOKEN.
 * 이 컨테이너/차단망에서는 status=error(네트워크)로 보고 — Vercel 등 허용망에서 실제 수집됨.
 */

const https = require('https');
const { fetchStatutes } = require('../chatbot/lib/statute-fetcher');

const OWNER = process.env.GITHUB_OWNER || 'recon9973-lang';
const REPO = process.env.GITHUB_REPO || 'desktop-tutorial';
const BRANCH = process.env.GITHUB_BRANCH || 'main';
const FILEPATH = 'venom-wordpress/preview/chatbot/data/sources/statutes.json';

function gh(method, body) {
  const payload = body ? JSON.stringify(body) : undefined;
  return new Promise((resolve) => {
    const req = https.request({
      hostname: 'api.github.com',
      path: `/repos/${OWNER}/${REPO}/contents/${FILEPATH}` + (method === 'GET' ? `?ref=${BRANCH}` : ''),
      method,
      headers: {
        'Authorization': `token ${process.env.GITHUB_TOKEN}`,
        'User-Agent': 'venom-statutes/1.0',
        'Accept': 'application/vnd.github.v3+json',
        ...(payload ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) } : {}),
      },
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => { let j = null; try { j = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch {} resolve({ status: res.statusCode, json: j }); });
    });
    req.on('error', () => resolve({ status: 0 }));
    req.setTimeout(20000, () => { req.destroy(); resolve({ status: 0 }); });
    if (payload) req.write(payload);
    req.end();
  });
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Cache-Control', 'no-store');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'GET only' });

  try {
    const oc = process.env.LAW_OC || process.env.OC;
    const result = await fetchStatutes(oc);
    const save = req.query && (req.query.save === '1' || req.query.save === 'true');

    let saved = false, saveNote;
    if (save && result.status === 'ok') {
      const secret = process.env.ADMIN_SECRET || process.env.CRON_SECRET;
      // 인증: Bearer 헤더 또는 ?token= 쿼리(브라우저 편의). CRON_SECRET도 허용(향후 크론 자동 갱신).
      const provided = (req.headers['authorization'] || '').replace('Bearer ', '').trim() || (req.query && req.query.token) || '';
      const ok = !secret || provided === process.env.ADMIN_SECRET || (process.env.CRON_SECRET && provided === process.env.CRON_SECRET);
      if (!ok) return res.status(401).json({ error: 'save 인증 필요: ?save=1&token=<ADMIN_SECRET> 또는 Bearer 헤더' });
      if (!process.env.GITHUB_TOKEN) { saveNote = 'GITHUB_TOKEN 미설정 — 저장 생략'; }
      else {
        const doc = { updated: new Date().toISOString(), status: 'ok', source: 'law.go.kr DRF', mst: result.mst, statutes: result.statutes };
        const cur = await gh('GET');
        const sha = cur.status === 200 && cur.json ? cur.json.sha : undefined;
        const content = Buffer.from(JSON.stringify(doc, null, 2) + '\n').toString('base64');
        const put = await gh('PUT', { message: 'chore(chatbot): 의료법 조문 최신본 수집', content, branch: BRANCH, ...(sha ? { sha } : {}) });
        saved = put.status === 200 || put.status === 201;
        if (!saved) saveNote = `GitHub 저장 실패 ${put.status}`;
      }
    }

    return res.status(result.status === 'ok' ? 200 : 502).json({
      status: result.status,
      reason: result.reason,
      mst: result.mst,
      count: result.statutes.length,
      // ?full=1 이면 조문 전문(공개 법령)을 그대로 반환 → 인증 없이 통합 가능
      articles: (req.query && (req.query.full === '1' || req.query.full === 'true'))
        ? result.statutes.map(s => ({ article: s.article, title: s.title, text: s.text }))
        : result.statutes.map(s => ({ article: s.article, title: s.title, preview: s.text.slice(0, 120) + (s.text.length > 120 ? '…' : '') })),
      ...(result.debug ? { debug: result.debug } : {}),
      saved, saveNote,
      hint: result.status === 'ok'
        ? (save ? '저장됨 → node pipeline/build.js 재빌드로 지식베이스 통합' : '?save=1 로 저장 가능(ADMIN_SECRET 필요 시 Bearer)')
        : 'LAW_OC 설정 및 허용망(Vercel) 확인. 계속 실패 시 조문 파일을 직접 제공하세요.',
    });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
};
