'use strict';

const https = require('https');

const BASE_URL = 'https://desktop-tutorial-chi-peach.vercel.app';
const OWNER    = process.env.GITHUB_OWNER  || 'recon9973-lang';
const REPO     = process.env.GITHUB_REPO   || 'desktop-tutorial';
const BRANCH   = process.env.GITHUB_BRANCH || 'main';

// 실제 크롤 가능한 URL만 — 홈/영문/블로그 글(/blog/<슬러그>). 해시(#geo)는 별도 URL이 아니라 제외.
// SPA의 전체 크롤러블 라우트 — index.html의 PAGE_ROUTES + DETAIL_ROUTES와 동기 유지.
// 새 페이지·라우트 추가 시 여기에도 반드시 추가할 것 (사이트맵 재생성 시 이 목록만 남는다).
const SITE_PATHS = [
  '/ai', '/geo', '/aeo', '/seo', '/hospital-marketing', '/online-marketing', '/website',
  '/about', '/blog', '/contact', '/seo-dictionary', '/diagnose', '/privacy', '/terms',
  '/dental', '/dermatology', '/orthopedics', '/oriental-medicine', '/plastic-surgery',
  '/internal-medicine', '/ophthalmology', '/medical-ad-review', '/medical-device',
  '/naver-ads', '/google-ads', '/channel-management', '/pr',
  '/online-marketing/naver', '/online-marketing/sns', '/online-marketing/youtube',
  '/dental/implant', '/dental/navigation-implant', '/dental/orthodontics', '/dental/clear-aligner',
  '/dental/cosmetic', '/dental/laminate', '/dental/conservative', '/dental/root-canal',
  '/dental/periodontal', '/dental/scaling',
  '/dermatology/pigment', '/dermatology/laser-toning', '/dermatology/elasticity',
  '/dermatology/lifting', '/dermatology/regeneration', '/dermatology/skin-booster',
  '/orthopedics/spine', '/orthopedics/herniated-disc', '/orthopedics/joint',
  '/orthopedics/knee-arthritis', '/orthopedics/rehab', '/orthopedics/manual-therapy',
  '/oriental-medicine/chuna', '/oriental-medicine/diet', '/oriental-medicine/traffic-accident',
  '/oriental-medicine/herbal-tonic', '/oriental-medicine/internal',
  '/plastic-surgery/eye-surgery', '/plastic-surgery/rhinoplasty', '/plastic-surgery/botox-filler',
  '/plastic-surgery/facelift', '/plastic-surgery/liposuction',
  '/internal-medicine/health-checkup', '/internal-medicine/chronic-disease',
  '/internal-medicine/thyroid', '/internal-medicine/endoscopy', '/internal-medicine/respiratory',
  '/ophthalmology/cataract', '/ophthalmology/vision', '/ophthalmology/lasik',
  '/ophthalmology/glaucoma', '/ophthalmology/dry-eye',
];

const STATIC_URLS = [
  { loc: `${BASE_URL}/`,    priority: '1.0', changefreq: 'weekly', hreflang: true },
  { loc: `${BASE_URL}/en/`, priority: '0.9', changefreq: 'weekly', hreflang: true },
  ...SITE_PATHS.map(p => ({ loc: `${BASE_URL}${p}`, priority: p.split('/').length > 2 ? '0.7' : '0.8', changefreq: 'monthly' })),
];

function toXmlDate(iso) {
  return iso ? String(iso).slice(0, 10) : new Date().toISOString().slice(0, 10);
}

// 저장된 slug를 그대로 사용(SPA의 /blog/<슬러그> 라우팅과 동일). 한글은 sitemap 규격상 퍼센트 인코딩.
function postLoc(p) {
  return `${BASE_URL}/blog/${encodeURIComponent(p.slug || p.id || '')}`;
}

function buildXml(posts = []) {
  const today = new Date().toISOString().slice(0, 10);
  const hreflangLinks = `    <xhtml:link rel="alternate" hreflang="ko" href="${BASE_URL}/"/>
    <xhtml:link rel="alternate" hreflang="en" href="${BASE_URL}/en/"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="${BASE_URL}/"/>`;

  const staticXml = STATIC_URLS.map(u => `  <url>
    <loc>${u.loc}</loc>
${u.hreflang ? hreflangLinks + '\n' : ''}    <lastmod>${today}</lastmod>
    <changefreq>${u.changefreq}</changefreq>
    <priority>${u.priority}</priority>
  </url>`);

  const nowMs = Date.now();
  const postUrls = posts
    // 발행됨 + slug 존재 + 예약시각(publishAt)이 지났을 때만 사이트맵에 포함
    .filter(p => p.status === 'published' && (p.slug || p.id) && (!p.publishAt || Date.parse(p.publishAt) <= nowMs))
    .map(p => `  <url>
    <loc>${postLoc(p)}</loc>
    <lastmod>${toXmlDate(p.updatedAt || p.createdAt || p.date)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>`);

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
${[...staticXml, ...postUrls].join('\n')}
</urlset>`;
}

async function updateSitemap(posts = []) {
  const TOKEN = process.env.GITHUB_TOKEN;
  if (!TOKEN) return false;

  const xml = buildXml(posts);
  const content = Buffer.from(xml).toString('base64');

  // 현재 SHA 조회 (outputDirectory: venom-wordpress/preview)
  const sha = await getFileSha('venom-wordpress/preview/sitemap.xml', TOKEN);

  const body = JSON.stringify({
    message: 'chore: auto-update sitemap.xml',
    content,
    branch: BRANCH,
    ...(sha && { sha }),
  });

  return new Promise((resolve) => {
    const req = https.request({
      hostname: 'api.github.com',
      path: `/repos/${OWNER}/${REPO}/contents/venom-wordpress/preview/sitemap.xml`,
      method: 'PUT',
      headers: {
        'Authorization': `token ${TOKEN}`,
        'User-Agent': 'venom-autopost/1.0',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
      },
    }, (res) => {
      res.on('data', () => {});
      res.on('end', () => resolve(res.statusCode === 200 || res.statusCode === 201));
    });
    req.on('error', () => resolve(false));
    req.setTimeout(20000, () => { req.destroy(); resolve(false); });
    req.write(body);
    req.end();
  });
}

function getFileSha(filePath, token) {
  return new Promise((resolve) => {
    const req = https.request({
      hostname: 'api.github.com',
      path: `/repos/${OWNER}/${REPO}/contents/${filePath}?ref=${BRANCH}`,
      method: 'GET',
      headers: {
        'Authorization': `token ${token}`,
        'User-Agent': 'venom-autopost/1.0',
        'Accept': 'application/vnd.github.v3+json',
      },
    }, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try { resolve(JSON.parse(data).sha || null); }
        catch { resolve(null); }
      });
    });
    req.on('error', () => resolve(null));
    req.end();
  });
}

module.exports = { updateSitemap, buildXml };
