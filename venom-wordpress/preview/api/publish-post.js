'use strict';

const { getPosts, savePost, appendLog, deletePost } = require('../lib/github-store');

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
      await deletePost(id);
      await appendLog({ action: 'delete', id, title: post.title });
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
