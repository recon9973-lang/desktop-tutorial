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

  const { category, keyword, region, extra, save, publish, withImage = true } = req.body || {};
  if (!category || !keyword) {
    return res.status(400).json({ error: 'category, keyword 필수' });
  }

  try {
    // 1. 글 생성
    const post = await generatePost({ category, keyword, region, extra });

    // 2. 이미지 생성 (글 생성 성공 후) — 실패 사유를 응답에 담아 화면에 표시
    const images = [];
    let imageError = null;
    if (withImage && post.imagePrompt) {
      try {
        const img1 = await generateAndSaveImage(post.imagePrompt, post.id, 0, post.title);
        if (img1 && img1.url) {
          images.push(img1.url);
          // SEO용 alt(제목+키워드+브랜드, 속성 깨짐 방지 위해 큰따옴표 이스케이프)
          const safe = (s) => String(s || '').replace(/"/g, '&quot;').replace(/</g, '&lt;');
          const altText = `${safe(post.title)} | ${safe(keyword)} - 병원마케팅 베놈`;
          const LOGO = 'https://raw.githubusercontent.com/recon9973-lang/desktop-tutorial/main/logo_venomad_hospital%20marketing.png';
          const heroImg = `<figure style="position:relative;margin:0 0 32px;border-radius:12px;overflow:hidden">
  <img src="${img1.url}" alt="${altText}" style="width:100%;height:auto;display:block" loading="lazy">
  <img src="${LOGO}" alt="병원마케팅 베놈 로고" style="position:absolute;right:14px;bottom:36px;width:104px;height:auto;opacity:.95;filter:drop-shadow(0 2px 8px rgba(0,0,0,.45))">
  <figcaption style="font-size:12px;color:#888;text-align:center;padding:8px">© 병원마케팅 베놈</figcaption>
</figure>`;
          post.html = heroImg + post.html;
        } else {
          imageError = (img1 && img1.error) || '알 수 없는 이미지 생성 오류';
          console.warn('[generate-post] 이미지 생성 실패:', imageError);
        }
      } catch (imgErr) {
        imageError = imgErr.message;
        console.warn('[generate-post] 이미지 생성 예외:', imgErr.message);
      }
    }

    post.images = images;
    post.imageStatus = images.length ? 'ok' : (imageError || 'skipped');

    // 3. 저장 요청 시 GitHub에 저장 (의료광고 검증 + 콘텐츠 오류 검수 통과 시에만)
    if (save && post.publishable) {
      post.status = publish ? 'published' : 'draft';
      try {
        await savePost(post);
        await appendLog({
          action: 'generate', id: post.id, title: post.title, category, keyword,
          tokenUsage: post.tokenUsage || null,
          imageGenerated: !!(post.images && post.images.length),
        });
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
