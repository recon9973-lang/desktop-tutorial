'use strict';

const { generatePost } = require('../lib/post-generator');
const { generateAndSaveImage } = require('../lib/image-generator');
const { savePost, appendLog, getPosts } = require('../lib/github-store');
const { updateSitemap } = require('../lib/sitemap-builder');

const DEFAULT_SETTINGS = {
  enabled: false,
  schedules: [],
  categories: ['geo'],
  keywords: ['병원 GEO마케팅'],
  regions: [],
  extra: '',
};

// 오늘 날짜(KST)에 해당하는 스케줄 찾기
function getTodayCount(settings) {
  const today = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  const todayStr = today.toISOString().slice(0, 10);

  // schedules 배열 방식
  if (Array.isArray(settings.schedules) && settings.schedules.length) {
    for (const s of settings.schedules) {
      if (s.from && s.to && todayStr >= s.from && todayStr <= s.to) {
        return Math.max(1, parseInt(s.dailyCount) || 1);
      }
    }
    return 0; // 오늘에 해당하는 스케줄 없으면 발행 안 함
  }

  // 레거시: dailyCount 단일 값
  return Math.max(1, parseInt(settings.dailyCount) || 1);
}

function authCheck(req) {
  const secret = process.env.CRON_SECRET;
  if (!secret) return false; // cron secret 없으면 무조건 차단
  return (req.headers['authorization'] || '') === `Bearer ${secret}`;
}

async function loadSettings() {
  try {
    // Node 18+ Vercel 런타임의 전역 fetch 사용 (node-fetch 의존 제거 — 조용한 무력화 방지)
    const f = (typeof fetch !== 'undefined') ? fetch : null;
    if (!f) return DEFAULT_SETTINGS;
    const baseUrl = process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:3000';
    const r = await f(`${baseUrl}/api/posting-settings`, {
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
  const count = getTodayCount(settings);
  if (count === 0) {
    return res.status(200).json({ ok: true, skipped: true, reason: '오늘은 발행 스케줄이 없습니다.' });
  }

  for (let i = 0; i < count; i++) {
    const cats = settings.categories || ['geo'];
    const keywords = settings.keywords || ['병원마케팅'];
    const regions = settings.regions || [];

    const category = cats[i % cats.length];
    const keyword = keywords[i % keywords.length];
    const region = regions.length ? regions[i % regions.length] : '';

    try {
      const post = await generatePost({ category, keyword, region, extra: settings.extra });

      // 이미지 1~2장 생성: 1번째=본문 최상단 히어로, 2번째=첫 h2 뒤 본문 삽입
      let imageError = null;
      try {
        const imgUrls = [];
        const fig = (url, cap) => `<figure style="margin:24px 0 32px;border-radius:12px;overflow:hidden">`
          + `<img src="${url}" alt="${post.title}" style="width:100%;height:auto;display:block" loading="lazy">`
          + `<figcaption style="font-size:12px;color:#888;text-align:center;padding:8px">${cap}</figcaption>`
          + `</figure>`;

        // 1·2번째 이미지를 병렬 생성(타임아웃 여유 확보) — 서로 다른 파일명이라 충돌 없음
        const [img1, img2] = await Promise.all([
          generateAndSaveImage(post.imagePrompt, post.id, 0, post.title),
          generateAndSaveImage(post.imagePrompt, post.id, 1, post.title),
        ]);
        if (img1 && img1.url) {
          imgUrls.push(img1.url);
          post.html = fig(img1.url, '© 병원마케팅 베놈') + post.html;
        } else if (img1 && img1.error) {
          imageError = img1.error;
        }

        // 2번째 이미지(베스트 에포트) — 실패해도 무시
        if (img2 && img2.url) {
          imgUrls.push(img2.url);
          const second = fig(img2.url, '병원마케팅 베놈 — 데이터 기반 전략');
          // 첫 번째 </h2> 뒤에 삽입, 없으면 본문 끝에 추가
          const h2End = post.html.indexOf('</h2>');
          post.html = h2End > -1
            ? post.html.slice(0, h2End + 5) + second + post.html.slice(h2End + 5)
            : post.html + second;
        }

        if (imgUrls.length) post.images = imgUrls;
      } catch (imgErr) {
        imageError = imgErr.message;
        console.warn('[cron] 이미지 생성 예외:', imgErr.message);
      }
      if (imageError) console.warn('[cron] 이미지 생성 실패:', imageError);

      const logBase = {
        id: post.id,
        title: post.title,
        tokenUsage: post.tokenUsage || null,
        imageGenerated: !!(post.images && post.images.length),
        imageError: imageError || undefined,
      };

      if (post.publishable) {
        // 의료광고 검증 통과 + 콘텐츠 오류 없음 → 즉시 발행
        post.status = 'published';
        await savePost(post);
        const action = post.autoFixed ? 'cron-publish-fixed' : 'cron-publish';
        await appendLog({ action, ...logBase, autoFixed: post.autoFixed });
        results.push({ ok: true, id: post.id, title: post.title, autoFixed: post.autoFixed });
      } else {
        // 금지어 잔존 또는 콘텐츠 오류(깨짐·잘림 등) → 검수 대기
        post.status = 'review';
        await savePost(post);
        const reason = !post.validation.pass ? '의료광고 검수 필요' : '콘텐츠 오류 검수 필요';
        await appendLog({
          action: 'cron-review', ...logBase,
          forbidden: post.validation.forbidden,
          contentErrors: (post.contentErrors || []).map(e => e.msg),
        });
        results.push({
          ok: false, id: post.id, title: post.title, reason,
          forbidden: post.validation.forbidden,
          contentErrors: (post.contentErrors || []).map(e => e.msg),
        });
      }
    } catch (e) {
      results.push({ ok: false, error: e.message, category, keyword });
    }
  }

  // 사이트맵 자동 갱신
  try {
    const { posts: allPosts } = await getPosts();
    await updateSitemap(allPosts);
  } catch (e) {
    console.warn('[cron] sitemap 갱신 실패(무시):', e.message);
  }

  return res.status(200).json({ ok: true, ran: count, results });
};
