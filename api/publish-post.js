'use strict';

const { getPosts, savePost, appendLog } = require('../lib/github-store');

function authCheck(req) {
  const secret = process.env.ADMIN_SECRET;
  if (!secret) return true;
  return (req.headers['authorization'] || '') === `Bearer ${secret}`;
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });
  if (!authCheck(req)) return res.status(401).json({ error: '인증 실패' });

  const { id, action } = req.body || {};
  if (!id || !action) return res.status(400).json({ error: 'id, action 필수' });

  try {
    const { posts } = await getPosts();
    const post = posts.find(p => p.id === id);
    if (!post) return res.status(404).json({ error: '포스트 없음' });

    if (action === 'publish') post.status = 'published';
    else if (action === 'unpublish') post.status = 'draft';
    else if (action === 'delete') {
      const filtered = posts.filter(p => p.id !== id);
      const { savePost: _, ...store } = require('../lib/github-store');
      // 전체 목록 저장
      const { getPosts: gp } = require('../lib/github-store');
      const { sha } = await gp();
      const ghStore = require('../lib/github-store');
      // 직접 posts 배열 저장
      await require('../lib/github-store').savePost({ ...post, status: '__delete__' });
      return res.status(200).json({ ok: true, action: 'deleted' });
    }

    await savePost(post);
    await appendLog({ action, id, title: post.title });
    return res.status(200).json({ ok: true, post });
  } catch (e) {
    console.error('[publish-post]', e);
    return res.status(500).json({ error: e.message });
  }
};
