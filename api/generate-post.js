'use strict';

const { generatePost } = require('../lib/post-generator');
const { generateAndSaveImage } = require('../lib/image-generator');
const { savePost, appendLog } = require('../lib/github-store');

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });

  const secret = process.env.ADMIN_SECRET;
  if (secret) {
    const auth = (req.headers['authorization'] || '').replace('Bearer ', '').trim();
    if (auth !== secret) {
      return res.status(401).json({ error: 'ADMIN_SECRET 불일치.' });
    }
  }

  if (!process.env.OPENAI_API_KEY) {
    return res.status(500).json({ error: 'OPENAI_API_KEY 환경변수가 Vercel에 설정되지 않았습니다.' });
  }

  const { category, keyword, region, extra, save, withImage = true } = req.body || {};
  if (!category || !keyword) {
    return res.status(400).json({ error: 'category, keyword 필수' });
  }

  try {
    // 1. 글 생성
    const post = await generatePost({ category, keyword, region, extra });

    // 2. 이미지 생성 (글 생성 성공 후 병렬로 1~2장)
    const images = [];
    if (withImage && post.imagePrompt) {
      try {
        // 이미지 1장 (필수)
        const img1 = await generateAndSaveImage(post.imagePrompt, post.id, 0);
        if (img1) {
          images.push(img1);
          // 이미지 삽입: 본문 첫 번째 <h2> 앞에 헤더 이미지 추가
          const heroImg = `<figure style="margin:0 0 32px;border-radius:12px;overflow:hidden">
  <img src="${img1.url}" alt="${post.title}" style="width:100%;height:auto;display:block" loading="lazy">
  <figcaption style="font-size:12px;color:#888;text-align:center;padding:8px">© 병원마케팅 베놈</figcaption>
</figure>`;
          post.html = heroImg + post.html;
        }
      } catch (imgErr) {
        console.warn('[generate-post] 이미지 생성 실패(무시):', imgErr.message);
      }
    }

    post.images = images.map(i => i.url);

    // 3. 저장 요청 시 GitHub에 저장 (자동 수정 후 검증 통과 시)
    if (save && post.validation.pass) {
      post.status = 'draft';
      try {
        await savePost(post);
        await appendLog({ action: 'generate', id: post.id, title: post.title, category, keyword, autoFixed: post.autoFixed });
      } catch (storeErr) {
        post._storeError = storeErr.message;
      }
    }

    return res.status(200).json({ ok: true, post });
  } catch (e) {
    console.error('[generate-post]', e);
    return res.status(500).json({ error: e.message });
  }
};
