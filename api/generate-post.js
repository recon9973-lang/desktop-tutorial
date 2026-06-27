'use strict';

const { generatePost } = require('../lib/post-generator');
const { savePost, appendLog } = require('../lib/github-store');

function authCheck(req) {
  const secret = process.env.ADMIN_SECRET;
  if (!secret) return true; // 미설정 시 통과 (개발 편의)
  const auth = req.headers['authorization'] || '';
  return auth === `Bearer ${secret}`;
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });
  if (!authCheck(req)) return res.status(401).json({ error: '인증 실패' });

  const { category, keyword, region, extra, save } = req.body || {};
  if (!category || !keyword) {
    return res.status(400).json({ error: 'category, keyword 필수' });
  }

  try {
    const post = await generatePost({ category, keyword, region, extra });

    if (save && post.validation.pass) {
      post.status = 'draft';
      await savePost(post);
      await appendLog({ action: 'generate', id: post.id, title: post.title, category, keyword });
    }

    return res.status(200).json({ ok: true, post });
  } catch (e) {
    console.error('[generate-post]', e);
    return res.status(500).json({ error: e.message });
  }
};
