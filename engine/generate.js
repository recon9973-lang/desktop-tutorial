#!/usr/bin/env node
/**
 * VENOM Site Factory — 자동생성 엔진 (MVP)
 *
 * 사용법:  node engine/generate.js samples/site-spec.example.json
 *
 * 흐름:  site-spec.json + 카테고리 블루프린트  →  완성된 정적 사이트 폴더
 *        (index.html + robots.txt + sitemap.xml + llms.txt)
 *
 * prepare() 는 정적 생성기와 WP 어댑터(wp-adapter.js)가 공유한다 —
 * 동일한 site-spec 에서 동일한 콘텐츠가 정적/워드프레스 양쪽으로 나간다.
 */
const fs = require('fs');
const path = require('path');
const { robotsTxt, sitemapXml, llmsTxt } = require('./seo');

const ROOT = path.join(__dirname, '..');

// --- 작은 토큰 치환기: {{a.b.c}} → 값 -------------------------------------
function render(tpl, data) {
  return tpl.replace(/\{\{\s*([\w.]+)\s*\}\}/g, (_, key) => {
    const val = key.split('.').reduce((o, k) => (o == null ? o : o[k]), data);
    return val == null ? '' : String(val);
  });
}

function slugify(s) {
  return String(s).toLowerCase().replace(/[^\w가-힣]+/g, '-').replace(/^-+|-+$/g, '');
}

// --- 섹션 빌더 (반복 영역은 코드에서 HTML 생성) ---------------------------
function buildDepartments(specialty) {
  return (specialty.keywords || []).map(k =>
    `<div class="card"><div class="ic">${String(k).trim().charAt(0)}</div><h3>${k}</h3><p>${specialty.label} 전문 의료진의 ${k} 진료</p></div>`
  ).join('\n');
}

function buildDoctors(doctors, img) {
  const list = (doctors && doctors.length) ? doctors
    : [{ name: '대표원장', role: '전문의', desc: '풍부한 임상 경험' }];
  return list.map(d => {
    const visual = d.photo
      ? `<img src="${d.photo}" alt="${d.name}">`
      : `<div class="avatar">${String(d.name).trim().charAt(0)}</div>`;
    return `<div class="doc"><div class="ph">${visual}</div>` +
      `<div class="info"><h3>${d.name}</h3><div class="role">${d.role || '전문의'}</div><p>${d.desc || ''}</p></div></div>`;
  }).join('\n');
}

// 진료 환경 갤러리 (실사 3컷). 캡션은 순서 기본값.
function buildGallery(gallery, placeholder) {
  const caps = ['진료실', '편안한 대기 공간', '리셉션'];
  const imgs = [0, 1, 2].map(i => (gallery && gallery[i]) || placeholder(caps[i]));
  return imgs.map((src, i) =>
    `<figure><img src="${src}" alt="${caps[i]}"><figcaption>${caps[i]}</figcaption></figure>`
  ).join('\n');
}

// 외부 이미지가 없거나(샌드박스) 스톡 미지정 시 자체 SVG 플레이스홀더 — 자급자족 렌더.
function placeholderDataUri(label) {
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 600'>` +
    `<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>` +
    `<stop offset='0' stop-color='#dfe6ee'/><stop offset='1' stop-color='#c4d0dd'/></linearGradient></defs>` +
    `<rect width='800' height='600' fill='url(#g)'/>` +
    `<text x='400' y='290' font-family='sans-serif' font-size='54' fill='#8b9bad' text-anchor='middle'>📷</text>` +
    `<text x='400' y='350' font-family='sans-serif' font-size='30' font-weight='700' fill='#6c7d90' text-anchor='middle'>${label}</text>` +
    `<text x='400' y='392' font-family='sans-serif' font-size='19' fill='#8b9bad' text-anchor='middle'>실사진 영역 · 고객 사진으로 교체</text></svg>`;
  return 'data:image/svg+xml,' + encodeURIComponent(svg);
}

function buildReviews(reviews, specialty) {
  const list = (reviews && reviews.length) ? reviews
    : specialty.keywords.slice(0, 3).map(k => ({ title: `${k} 진료 사례`, body: `${k} 진료 과정과 관리 안내` }));
  return list.map(r =>
    `<div class="card"><h3>${r.title}</h3><p>${r.body}</p></div>`
  ).join('\n');
}

function buildTrust(stats) {
  const list = stats && stats.length ? stats : [
    { num: '20년+', lbl: '진료 경력' },
    { num: '98%', lbl: '환자 만족도' },
    { num: '10,000+', lbl: '누적 진료' },
    { num: '연중무휴', lbl: '진료 안내' },
  ];
  return list.map(s => `<div><div class="num">${s.num}</div><div class="lbl">${s.lbl}</div></div>`).join('\n');
}

function buildFaq(faq, brand, specialty) {
  const list = (faq && faq.length) ? faq : [
    { q: `${specialty.label} 진료는 예약이 필요한가요?`, a: '카카오 채널 또는 전화로 편하게 예약하실 수 있습니다.' },
    { q: '주차가 가능한가요?', a: '건물 내 주차가 가능하며 자세한 안내는 상담 시 도와드립니다.' },
    { q: '진료 시간은 어떻게 되나요?', a: '평일 진료를 기본으로 하며 자세한 시간은 전화로 안내드립니다.' },
  ];
  const html = list.map(f =>
    `<div class="faq-item"><h3>${f.q}</h3><p>${f.a}</p></div>`
  ).join('\n');
  const schema = JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: list.map(f => ({
      '@type': 'Question', name: f.q,
      acceptedAnswer: { '@type': 'Answer', text: f.a },
    })),
  }, null, 2);
  return { html, schema };
}

// --- prepare(): site-spec 을 풍부화하고 섹션/SEO/페이지 콘텐츠 생성 --------
// 정적 생성기와 WP 어댑터가 공유하는 단일 진실 소스.
function prepare(spec) {
  const blueprint = JSON.parse(
    fs.readFileSync(path.join(ROOT, 'blueprints', spec.category, 'blueprint.json'), 'utf8')
  );
  const specialty = blueprint.specialties[spec.clinic?.specialty] || blueprint.specialties.dental;
  const scale = blueprint.scales[spec.scale] || blueprint.scales.standard;
  const options = Array.from(new Set([...(blueprint.defaultOptions || []), ...(spec.options || [])]));

  spec.lang = (spec.locale && spec.locale[0]) || 'ko';
  spec.specialty = specialty;
  spec.slug = slugify(spec.domain || spec.brand.name);
  spec.hero = spec.hero || {};
  spec.hero.headline = spec.hero.headline ||
    `${spec.brand.region} <b>${specialty.label}</b>,<br>믿을 수 있는 ${spec.brand.name}`;
  spec.hero.sub = spec.hero.sub ||
    `${specialty.keywords.slice(0, 3).join(' · ')} — 정확한 진단과 정직한 진료로 함께합니다.`;
  spec.meta = {
    description: `${spec.brand.region} ${specialty.label} ${spec.brand.name}. ${specialty.keywords.join(', ')} 진료. 상담 ${spec.brand.phone}.`,
    keywords: [spec.brand.name, specialty.label, ...specialty.keywords].join(', '),
  };

  // 이미지: 고객 실사진(spec.images) > 진료과목 기본 스톡 > 자체 플레이스홀더.
  // VENOM_LOCAL_PLACEHOLDERS=1 이면 외부 URL 무시(오프라인 미리보기/스크린샷용).
  const localOnly = process.env.VENOM_LOCAL_PLACEHOLDERS === '1';
  const stock = localOnly ? {} : (specialty.stock || {});
  spec.images = Object.assign({}, stock, spec.images || {});
  const ph = placeholderDataUri;
  spec.images.intro = spec.images.intro || ph('병원 내부 전경');
  // 히어로/CTA: 실사진이 있으면 그 사진을 배경으로, 없으면 브랜드 그라데이션(글자 가독성 확보).
  if (spec.images.hero) {
    spec.images.heroBg = `url('${spec.images.hero}')`;
  } else {
    spec.images.hero = '';
    spec.images.heroBg = `linear-gradient(135deg, var(--p), var(--bd))`;
  }

  const faq = buildFaq(spec.faq, spec.brand, specialty);
  spec.sections = {
    trust: buildTrust(spec.trust),
    departments: buildDepartments(specialty),
    doctors: buildDoctors(spec.clinic?.doctors, spec.images),
    reviews: buildReviews(spec.reviews, specialty),
    gallery: buildGallery(spec.images.gallery, ph),
    faq: faq.html,
    faqSchema: faq.schema,
  };

  const seoFiles = {
    'robots.txt': robotsTxt(spec.domain),
    'sitemap.xml': sitemapXml(spec.domain, scale.pages),
    'llms.txt': llmsTxt(spec, specialty),
  };

  return { spec, blueprint, specialty, scale, options, seoFiles };
}

// --- 정적 HTML 출력 ----------------------------------------------------------
function generate(specPath) {
  const raw = JSON.parse(fs.readFileSync(specPath, 'utf8'));
  const { spec, blueprint, specialty, scale, options, seoFiles } = prepare(raw);

  const tpl = fs.readFileSync(path.join(ROOT, 'blueprints', spec.category, 'template.html'), 'utf8');
  let html = render(tpl, spec);

  // 의료광고 검수 (medical_review 옵션)
  let medReviewLine = '';
  if (options.includes('medical_review')) {
    const { runMedicalReview } = require('./options/medical-review');
    const rv = runMedicalReview(html);
    html = rv.html;
    if (rv.fixed) {
      const n = rv.report.before.forbidden.length;
      medReviewLine = `  의료광고 검수  : ⚠ 금지어 ${n}개 자동 수정 완료`;
    } else {
      medReviewLine = '  의료광고 검수  : ✅ 이상 없음';
    }
  }

  const outDir = path.join(ROOT, 'output', spec.slug);
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'index.html'), html);
  for (const [name, content] of Object.entries(seoFiles)) {
    fs.writeFileSync(path.join(outDir, name), content);
  }

  console.log('\n✅ 사이트 생성 완료 (정적)');
  console.log('────────────────────────────────');
  console.log(`  브랜드   : ${spec.brand.name}`);
  console.log(`  카테고리 : ${blueprint.label} / ${specialty.label} (${scale.label})`);
  console.log(`  도메인   : ${spec.domain}`);
  console.log(`  페이지   : ${scale.pages.join(', ')}`);
  console.log(`  옵션 팩  : ${options.join(', ')}`);
  if (medReviewLine) console.log(medReviewLine);
  console.log(`  출력 위치: auto-site-factory/output/${spec.slug}/`);
  console.log(`  생성 파일: index.html, ${Object.keys(seoFiles).join(', ')}`);
  console.log('────────────────────────────────\n');
  return outDir;
}

if (require.main === module) {
  const specArg = process.argv[2];
  if (!specArg) {
    console.error('사용법: node engine/generate.js <site-spec.json>');
    process.exit(1);
  }
  generate(path.resolve(specArg));
}

module.exports = { generate, prepare, render, slugify };
