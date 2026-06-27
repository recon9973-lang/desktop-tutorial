'use strict';

const { generatePost } = require('../lib/post-generator');
const { generateAndSaveImage } = require('../lib/image-generator');
const { savePost, appendLog } = require('../lib/github-store');

const DEFAULT_SETTINGS = {
  enabled: false,
  dailyCount: 1,
  categories: ['geo'],
  keywords: ['병원 GEO마케팅'],
  regions: [],
  extra: '',
};

function authCheck(req) {
  const secret = process.env.CRON_SECRET;
  if (!secret) return false; // cron secret 없으면 무조건 차단
  return (req.headers['authorization'] || '') === `Bearer ${secret}`;
}

async function loadSettings() {
  try {
    const { default: fetch } = await import('node-fetch').catch(() => ({ default: null }));
    if (!fetch) return DEFAULT_SETTINGS;
    const baseUrl = process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:3000';
    const r = await fetch(`${baseUrl}/api/posting-settings`, {
      headers: { Authorization: `Bearer ${process.env.ADMIN_SECRET || ''}` },
    });
    if (r.ok) return await r.json();
  } catch {}
  return DEFAULT_SETTINGS;
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST' && req.method !== 'GET') {
    return res.status(405).json({ error: 'POST/GET only' });
  }
  if (!authCheck(req)) return res.status(401).json({ error: '인증 실패' });

  const settings = await loadSettings();
  if (!settings.enabled) {
    return res.status(200).json({ ok: true, skipped: true, reason: '자동 포스팅 비활성화 상태' });
  }

  const results = [];
  const count = Math.min(settings.dailyCount || 1, 5);

  for (let i = 0; i < count; i++) {
    const cats = settings.categories || ['geo'];
    const keywords = settings.keywords || ['병원마케팅'];
    const regions = settings.regions || [];

    const category = cats[i % cats.length];
    const keyword = keywords[i % keywords.length];
    const region = regions.length ? regions[i % regions.length] : '';

    try {
      const post = await generatePost({ category, keyword, region, extra: settings.extra });

      // 이미지 1장 생성 후 본문 상단에 삽입
      try {
        const img = await generateAndSaveImage(post.imagePrompt, post.id, 0);
        if (img) {
          post.images = [img.url];
          const heroImg = `<figure style="margin:0 0 32px;border-radius:12px;overflow:hidden">`
            + `<img src="${img.url}" alt="${post.title}" style="width:100%;height:auto;display:block" loading="lazy">`
            + `<figcaption style="font-size:12px;color:#888;text-align:center;padding:8px">© 병원마케팅 베놈</figcaption>`
            + `</figure>`;
          post.html = heroImg + post.html;
        }
      } catch (imgErr) {
        console.warn('[cron] 이미지 생성 실패(무시):', imgErr.message);
      }

      if (post.validation.pass) {
        // 검증 통과 (자동 수정 포함) → 즉시 발행
        post.status = 'published';
        await savePost(post);
        const action = post.autoFixed ? 'cron-publish-fixed' : 'cron-publish';
        await appendLog({ action, id: post.id, title: post.title, autoFixed: post.autoFixed });
        results.push({ ok: true, id: post.id, title: post.title, autoFixed: post.autoFixed });
      } else {
        // 자동 수정 후에도 금지어 잔존 → 검수 대기
        post.status = 'review';
        await savePost(post);
        await appendLog({ action: 'cron-review', id: post.id, title: post.title, forbidden: post.validation.forbidden });
        results.push({ ok: false, id: post.id, title: post.title, reason: '의료광고 검수 필요', forbidden: post.validation.forbidden });
      }
    } catch (e) {
      results.push({ ok: false, error: e.message, category, keyword });
    }
  }

  return res.status(200).json({ ok: true, ran: count, results });
};
