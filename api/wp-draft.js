'use strict';

const { createWpDraft } = require('../lib/wp-client');

// 원고 스튜디오 "WordPress 자동 임시저장" 엔드포인트.
// 브라우저 → (이 서버리스) → 워드프레스 REST API 순으로 호출(CORS·키 노출 회피).
module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });

  const secret = process.env.ADMIN_SECRET;
  if (secret) {
    const auth = (req.headers['authorization'] || '').replace('Bearer ', '').trim();
    if (auth !== secret) return res.status(401).json({ error: 'ADMIN_SECRET 불일치.' });
  }

  const { siteUrl, user, appPassword, title, html, excerpt, status } = req.body || {};
  try {
    // 기본은 임시저장(draft). publish는 명시적으로 요청한 경우에만.
    const r = await createWpDraft({ siteUrl, user, appPassword, title, html, excerpt, status: status === 'publish' ? 'publish' : 'draft' });
    if (!r.ok) return res.status(400).json({ error: r.error });
    return res.status(200).json({ ok: true, id: r.id, link: r.link, editLink: r.editLink, status: r.status });
  } catch (e) {
    console.error('[wp-draft]', e);
    return res.status(500).json({ error: e.message });
  }
};
