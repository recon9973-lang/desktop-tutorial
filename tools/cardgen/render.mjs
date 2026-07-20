// VENOM 자동블로그 카드뉴스 렌더러 (CI/로컬 공용)
// blog-posts.json을 읽어, content/images/에 카드 파일이 '없는' 글만 골라 HTML→PNG로 렌더한다(멱등).
// PNG는 out/ 에 저장하고 out/jobs.json(파일 매핑)을 남긴다 → convert.py가 jpg+webp로 변환.
//
// 사용: NODE_PATH=... node render.mjs [blogPostsJson] [imagesDir] [outDir]
//   기본값: ../../venom-wordpress/preview/content/{blog-posts.json,images}, ./out
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const HERE = path.dirname(new URL(import.meta.url).pathname);
const PREVIEW = path.resolve(HERE, '../../venom-wordpress/preview');
const BLOG_JSON = process.argv[2] || path.join(PREVIEW, 'content/blog-posts.json');
const IMAGES_DIR = process.argv[3] || path.join(PREVIEW, 'content/images');
const OUT_DIR = process.argv[4] || path.join(HERE, 'out');
const FORCE = process.env.CARD_FORCE === '1'; // 1이면 이미 있어도 전부 재렌더

const b64 = f => fs.readFileSync(path.join(HERE, 'fonts', f)).toString('base64');
const FONT = {
  black: b64('Pretendard-Black.woff2'), eb: b64('Pretendard-ExtraBold.woff2'),
  bold: b64('Pretendard-Bold.woff2'), semi: b64('Pretendard-SemiBold.woff2'),
};

const THEME = {
  geo:      { label:'GEO/AI 마케팅', c1:'#241f66', c2:'#533afd', ac:'#c3bcff', glyph:'GEO' },
  seo:      { label:'SEO 마케팅',    c1:'#0a3324', c2:'#16a34a', ac:'#8ff0c0', glyph:'SEO' },
  dental:   { label:'치과 마케팅',   c1:'#0a3247', c2:'#0ea5e9', ac:'#9fdcff', glyph:'치과' },
  skin:     { label:'피부과 마케팅', c1:'#5c1a3f', c2:'#ec4899', ac:'#fbbcdd', glyph:'피부' },
  oriental: { label:'한의원 마케팅', c1:'#4d2c0d', c2:'#d97706', ac:'#ffd9a3', glyph:'한방' },
  ortho:    { label:'정형외과 마케팅', c1:'#0a3532', c2:'#14b8a6', ac:'#83f0e2', glyph:'정형' },
  plastic:  { label:'성형외과 마케팅', c1:'#4d1646', c2:'#c026d3', ac:'#f4b6ee', glyph:'성형' },
  naegwa:   { label:'내과 마케팅',   c1:'#4d1212', c2:'#dc2626', ac:'#ffb0b0', glyph:'내과' },
  angwa:    { label:'안과 마케팅',   c1:'#20225c', c2:'#6366f1', ac:'#b7c0ff', glyph:'안과' },
  shimui:   { label:'의료광고 심의', c1:'#1a2536', c2:'#51617a', ac:'#cdd8e6', glyph:'심의' },
  geo_local:{ label:'지역 마케팅',   c1:'#5c0f2a', c2:'#ea2261', ac:'#ffb3cc', glyph:'지역' },
};
const ALIAS = { '한의원':'oriental','치과':'dental','피부과':'skin','정형외과':'ortho',
  '성형외과':'plastic','내과':'naegwa','안과':'angwa','지역마케팅':'geo_local',
  '의료광고심의':'shimui','의료광고 심의':'shimui','GEO/AI':'geo','GEO':'geo','SEO':'seo' };
const catCode = c => THEME[c] ? c : (ALIAS[c] || 'geo');
const esc = s => String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

function buildHTML(post) {
  const t = THEME[catCode(post.cat)] || THEME.geo;
  const region = post.region ? esc(post.region) : '';
  const kicker = (region ? region + ' · ' : '') + t.label;
  const title = esc(post.title || '');
  return `<!doctype html><html><head><meta charset="utf-8"><style>
  @font-face{font-family:P;font-weight:900;src:url(data:font/woff2;base64,${FONT.black}) format('woff2')}
  @font-face{font-family:P;font-weight:800;src:url(data:font/woff2;base64,${FONT.eb}) format('woff2')}
  @font-face{font-family:P;font-weight:700;src:url(data:font/woff2;base64,${FONT.bold}) format('woff2')}
  @font-face{font-family:P;font-weight:600;src:url(data:font/woff2;base64,${FONT.semi}) format('woff2')}
  *{margin:0;padding:0;box-sizing:border-box}
  html,body{width:1200px;height:1200px}
  .card{width:1200px;height:1200px;position:relative;overflow:hidden;font-family:P;
    background:linear-gradient(145deg,${t.c1} 0%,${t.c2} 118%)}
  .card::before{content:"";position:absolute;inset:0;
    background:radial-gradient(120% 90% at 78% 8%,rgba(255,255,255,.20),rgba(255,255,255,0) 46%),
               radial-gradient(120% 120% at 50% 120%,rgba(0,0,0,.34),rgba(0,0,0,0) 60%)}
  .glyph{position:absolute;right:-40px;bottom:-140px;font-weight:900;font-size:520px;line-height:.8;
    color:rgba(255,255,255,.09);letter-spacing:-8px}
  .topbar{position:absolute;top:70px;left:88px;right:88px;display:flex;align-items:center;gap:18px}
  .dot{width:52px;height:52px;border-radius:14px;background:rgba(255,255,255,.16);
    border:1px solid rgba(255,255,255,.28);display:flex;align-items:center;justify-content:center;
    font-weight:800;font-size:20px;color:#fff}
  .kick{font-weight:700;font-size:32px;color:${t.ac};letter-spacing:-.5px}
  .wrap{position:absolute;left:88px;right:88px;top:300px;height:560px;display:flex;flex-direction:column;justify-content:center}
  .accentline{width:96px;height:12px;border-radius:8px;background:${t.ac};margin-bottom:34px}
  .headline{font-weight:900;color:#fff;font-size:112px;line-height:1.12;letter-spacing:-3px;
    text-shadow:0 4px 30px rgba(0,0,0,.28);word-break:keep-all}
  .foot{position:absolute;left:88px;right:88px;bottom:78px;display:flex;align-items:center;justify-content:space-between}
  .brand{font-weight:800;font-size:34px;color:#fff;letter-spacing:2px}
  .brand small{font-weight:600;color:rgba(255,255,255,.7);letter-spacing:1px;font-size:24px;margin-left:12px}
  .tag{font-weight:700;font-size:26px;color:#fff;background:rgba(255,255,255,.14);
    border:1px solid rgba(255,255,255,.26);padding:12px 26px;border-radius:999px}
  </style></head><body>
  <div class="card">
    <div class="glyph">${esc(t.glyph)}</div>
    <div class="topbar"><div class="dot">V</div><div class="kick">${kicker}</div></div>
    <div class="wrap"><div class="accentline"></div><div class="headline" id="hl">${title}</div></div>
    <div class="foot"><div class="brand">VENOM<small>MARKETING BLOG</small></div>
      <div class="tag">병원 마케팅 인사이트</div></div>
  </div></body></html>`;
}

function baseOf(u) { return String(u).split('/').pop().replace(/\.(jpg|jpeg|png|webp)$/i, ''); }

async function main() {
  const raw = JSON.parse(fs.readFileSync(BLOG_JSON, 'utf8'));
  const posts = Array.isArray(raw) ? raw : (raw.posts || []);
  // 카드 파일이 없는(또는 FORCE) 글만 렌더 대상으로
  const jobs = [];
  for (const x of posts) {
    const imgs = (x.images || []).filter(Boolean);
    if (!imgs.length) continue;
    const bases = imgs.map(baseOf);
    const firstJpg = path.join(IMAGES_DIR, bases[0] + '.jpg');
    if (!FORCE && fs.existsSync(firstJpg)) continue; // 이미 카드 있음 → 스킵
    jobs.push({ id: x.id, cat: x.cat, region: x.region || '', title: x.title || '', out: bases[0], files: bases });
  }
  if (!jobs.length) { console.log('렌더 대상 없음(모든 글이 카드 보유).'); fs.mkdirSync(OUT_DIR, { recursive: true }); fs.writeFileSync(path.join(OUT_DIR, 'jobs.json'), '[]'); return; }

  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 1200 }, deviceScaleFactor: 1 });
  for (const post of jobs) {
    await page.setContent(buildHTML(post), { waitUntil: 'load' });
    await page.evaluate(async () => { if (document.fonts && document.fonts.ready) await document.fonts.ready; });
    await page.evaluate(() => {
      const hl = document.getElementById('hl'); let size = 112; hl.style.fontSize = size + 'px';
      while (hl.getBoundingClientRect().height > 470 && size > 52) { size -= 4; hl.style.fontSize = size + 'px'; }
    });
    await page.screenshot({ path: path.join(OUT_DIR, post.out + '.png'), clip: { x: 0, y: 0, width: 1200, height: 1200 } });
    console.log(`  ✓ ${post.out}.png (${post.cat})`);
  }
  await browser.close();
  fs.writeFileSync(path.join(OUT_DIR, 'jobs.json'), JSON.stringify(jobs, null, 2));
  console.log(`렌더 완료: ${jobs.length}장 → ${OUT_DIR}`);
}
main().catch(e => { console.error(e); process.exit(1); });
