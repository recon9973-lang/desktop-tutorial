'use strict';

const { generatePost } = require('../lib/post-generator');
const { savePost, appendLog } = require('../lib/github-store');

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });

  // ADMIN_SECRET 설정된 경우만 검증, 미설정이면 통과
  const secret = process.env.ADMIN_SECRET;
  if (secret) {
    const auth = (req.headers['authorization'] || '').replace('Bearer ', '').trim();
    if (auth !== secret) {
      return res.status(401).json({ error: 'ADMIN_SECRET 불일치. 관리자 페이지 → API 인증 토큰을 확인하세요.' });
    }
  }

  if (!process.env.OPENAI_API_KEY) {
    return res.status(500).json({ error: 'OPENAI_API_KEY 환경변수가 Vercel에 설정되지 않았습니다. Vercel 대시보드 → Settings → Environment Variables에서 추가하세요.' });
  }

  const body = req.body || {};
  const { category, keyword, region, extra, save } = body;

  if (!category || !keyword) {
    return res.status(400).json({ error: 'category, keyword 필수' });
  }

  try {
    const post = await generatePost({ category, keyword, region, extra });

    if (save && post.validation.pass) {
      post.status = 'draft';
      try {
        await savePost(post);
        await appendLog({ action: 'generate', id: post.id, title: post.title, category, keyword });
      } catch (storeErr) {
        // GitHub 저장 실패는 무시하고 생성 결과는 반환
        post._storeError = storeErr.message;
      }
    }

    return res.status(200).json({ ok: true, post });
  } catch (e) {
    console.error('[generate-post]', e);
    return res.status(500).json({ error: e.message });
  }
};
