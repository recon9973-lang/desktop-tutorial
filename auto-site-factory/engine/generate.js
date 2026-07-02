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

// 소상공인 메뉴·서비스 카드 --------------------------------------------------------
function buildMenu(menu, specialty) {
  const list = (menu && menu.length) ? menu
    : specialty.keywords.slice(0, 4).map(k => ({ name: k, price: '', desc: `${specialty.label} 대표 메뉴·서비스` }));
  return list.map(item => {
    const priceHtml = item.price
      ? `<div class="price">${item.price}<span>원</span></div>` : '';
    return `<div class="card">` +
      `<div class="ic">${String(item.name).trim().charAt(0)}</div>` +
      `<h3>${item.name}</h3>${priceHtml}<p>${item.desc || ''}</p></div>`;
  }).join('\n');
}

// 영업시간 테이블 ------------------------------------------------------------------
function buildHours(hours) {
  const list = (hours && hours.length) ? hours : [
    { day: '평일', time: '09:00 – 18:00' },
    { day: '주말·공휴일', time: '10:00 – 17:00' },
    { day: '정기 휴무', time: '매주 월요일' },
  ];
  return list.map(h =>
    `<div class="hour-row"><span class="day">${h.day}</span><span class="time">${h.time}</span></div>`
  ).join('\n');
}

// 로컬 후기 (별점 포함) -------------------------------------------------------------
function buildLocalReviews(reviews, specialty) {
  const list = (reviews && reviews.length) ? reviews
    : specialty.keywords.slice(0, 3).map((k, i) => ({
        author: `고객 ${i + 1}`,
        stars: 5,
        body: `${k} 덕분에 정말 만족스러웠어요. 다음에도 꼭 다시 올게요.`,
      }));
  return list.map(r => {
    const stars = '★'.repeat(Math.min(5, Math.max(1, r.stars || 5)));
    return `<div class="review-card">` +
      `<div class="stars">${stars}</div>` +
      `<p class="body">${r.body}</p>` +
      `<div class="author">— ${r.author || '익명 고객'}</div></div>`;
  }).join('\n');
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

// AggregateRating: trust 배열에서 별점/리뷰 수 추출
function extractRating(trust) {
  if (!trust || !trust.length) return null;
  const ratingItem = trust.find(t => String(t.lbl).includes('평점') || String(t.num).includes('★') || String(t.num).includes('.'));
  const countItem  = trust.find(t => String(t.lbl).includes('고객') || String(t.lbl).includes('진료') || String(t.lbl).includes('방문'));
  const ratingVal  = ratingItem ? parseFloat(String(ratingItem.num).replace(/[^\d.]/g, '')) : 4.9;
  const countStr   = countItem  ? String(countItem.num).replace(/[^\d]/g, '') : '1000';
  if (!ratingVal || isNaN(ratingVal)) return null;
  return { '@type': 'AggregateRating', ratingValue: ratingVal, bestRating: 5, worstRating: 1, reviewCount: parseInt(countStr) || 100 };
}

// OpeningHoursSpecification from hours array
function buildHoursSchema(hours) {
  if (!hours || !hours.length) return null;
  const dayMap = { '평일': ['Monday','Tuesday','Wednesday','Thursday','Friday'], '주말': ['Saturday','Sunday'], '월요일': ['Monday'], '화요일': ['Tuesday'], '수요일': ['Wednesday'], '목요일': ['Thursday'], '금요일': ['Friday'], '토요일': ['Saturday'], '일요일': ['Sunday'] };
  const specs = [];
  for (const h of hours) {
    if (!h.time || h.time.includes('휴무') || h.time.includes('정기')) continue;
    const timeMatch = String(h.time).match(/(\d{1,2}:\d{2})\s*[–\-~]\s*(\d{1,2}:\d{2})/);
    if (!timeMatch) continue;
    const [, opens, closes] = timeMatch;
    const dayKey = Object.keys(dayMap).find(k => String(h.day).includes(k));
    const days = dayKey ? dayMap[dayKey] : ['Monday','Tuesday','Wednesday','Thursday','Friday'];
    specs.push({ '@type': 'OpeningHoursSpecification', dayOfWeek: days, opens, closes });
  }
  return specs.length ? specs : null;
}

// 메인 Schema.org 블록 빌드 (AEO/GEO 완전판)
function buildMainSchema(spec, specialty, domain) {
  const address = {
    '@type': 'PostalAddress',
    streetAddress: spec.brand.address || '',
    addressLocality: spec.brand.region || '',
    addressCountry: 'KR',
  };
  const hoursSpec = spec.category === 'clinic'
    ? buildHoursSchema(spec.clinic?.hours)
    : buildHoursSchema(spec.local?.hours);
  const rating    = extractRating(spec.trust);
  const sameAs    = [spec.brand.instagram, spec.brand.naver_place, spec.brand.kakao]
    .filter(u => u && u.startsWith('http'));

  const available = (specialty.keywords || []).map(k => ({
    '@type': 'MedicalTherapy',
    name: k,
  }));

  let entity;
  if (spec.category === 'clinic') {
    entity = {
      '@context': 'https://schema.org',
      '@type': ['MedicalClinic', 'LocalBusiness'],
      name: spec.brand.name,
      image: spec.images?.hero || '',
      telephone: spec.brand.phone,
      address,
      url: `https://${domain}/`,
      description: spec.meta?.description || '',
      medicalSpecialty: specialty.label,
      availableService: available.slice(0, 5),
    };
  } else {
    entity = {
      '@context': 'https://schema.org',
      '@type': ['LocalBusiness', 'Organization'],
      name: spec.brand.name,
      image: spec.images?.hero || '',
      telephone: spec.brand.phone,
      address,
      url: `https://${domain}/`,
      description: spec.meta?.description || '',
      priceRange: '₩₩',
    };
  }
  if (rating)    entity.aggregateRating = rating;
  if (hoursSpec) entity.openingHoursSpecification = hoursSpec;
  if (sameAs.length) entity.sameAs = sameAs;

  return JSON.stringify(entity, null, 2);
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

// --- spec 검증: 필수 필드 누락 시 즉시 에러 --------------------------------
function validateSpec(spec) {
  if (!spec.category || !['clinic', 'local', 'press'].includes(spec.category))
    throw new Error(`spec.category는 'clinic' | 'local' | 'press' 중 하나여야 합니다. 현재 값: ${spec.category}`);
  if (!spec.domain)
    throw new Error('spec.domain 필드가 없습니다. (예: "example.com")');
  if (!spec.brand?.name)
    throw new Error('spec.brand.name 필드가 없습니다.');
  if (!spec.brand?.phone)
    throw new Error('spec.brand.phone 필드가 없습니다.');
  if (spec.brand.primary && !/^#[0-9a-fA-F]{3,8}$/.test(spec.brand.primary))
    throw new Error(`spec.brand.primary 색상 형식이 올바르지 않습니다: ${spec.brand.primary} (예: "#533afd")`);
  if (spec.reviews) {
    for (const r of spec.reviews) {
      if (r.stars !== undefined && (r.stars < 1 || r.stars > 5))
        throw new Error(`reviews[].stars는 1~5 사이여야 합니다. 현재 값: ${r.stars}`);
    }
  }
}

// --- prepare(): site-spec 을 풍부화하고 섹션/SEO/페이지 콘텐츠 생성 --------
// 정적 생성기와 WP 어댑터가 공유하는 단일 진실 소스.
// clinic / local 두 카테고리를 모두 지원한다.
function prepare(spec) {
  validateSpec(spec);

  const bpPath = path.join(ROOT, 'blueprints', spec.category, 'blueprint.json');
  if (!fs.existsSync(bpPath))
    throw new Error(`블루프린트를 찾을 수 없습니다: blueprints/${spec.category}/blueprint.json`);
  const blueprint = JSON.parse(fs.readFileSync(bpPath, 'utf8'));

  // 카테고리 범용: clinic → specialties, local → types
  const subCatMap = blueprint.specialties || blueprint.types || {};
  const subCatKey = spec.clinic?.specialty || spec.local?.type;
  const specialty  = subCatMap[subCatKey] || Object.values(subCatMap)[0];

  const scale   = blueprint.scales[spec.scale] || blueprint.scales.standard;
  const options = Array.from(new Set([...(blueprint.defaultOptions || []), ...(spec.options || [])]));

  spec.lang     = (spec.locale && spec.locale[0]) || 'ko';
  spec.specialty = specialty;
  spec.slug      = slugify(spec.domain || spec.brand.name);
  spec.hero      = spec.hero || {};

  // 카테고리별 기본 헤드라인·서브카피
  if (spec.category === 'clinic') {
    spec.hero.headline = spec.hero.headline ||
      `${spec.brand.region} <b>${specialty.label}</b>,<br>믿을 수 있는 ${spec.brand.name}`;
    spec.hero.sub = spec.hero.sub ||
      `${specialty.keywords.slice(0, 3).join(' · ')} — 정확한 진단과 정직한 진료로 함께합니다.`;
    spec.meta = {
      description: `${spec.brand.region} ${specialty.label} ${spec.brand.name}. ${specialty.keywords.join(', ')} 진료. 상담 ${spec.brand.phone}.`,
      keywords: [spec.brand.name, specialty.label, ...specialty.keywords].join(', '),
    };
  } else if (spec.category === 'press') {
    spec.hero.headline = spec.hero.headline ||
      `<b>${spec.brand.name}</b>,<br>${specialty.label}`;
    spec.hero.sub = spec.hero.sub ||
      `${specialty.keywords.slice(0, 3).join(' · ')} — ${spec.brand.tagline || '최신 소식을 전합니다'}`;
    spec.meta = {
      description: `${spec.brand.name} 공식 ${specialty.label}. ${specialty.keywords.join(', ')}. ${spec.brand.region}.`,
      keywords: [spec.brand.name, specialty.label, ...specialty.keywords].join(', '),
    };
    spec.brand.naver_place = spec.brand.naver_place || '';
    spec.brand.instagram   = spec.brand.instagram   || '';
  } else {
    spec.hero.headline = spec.hero.headline ||
      `${spec.brand.region} <b>${specialty.label}</b>,<br>${spec.brand.name}`;
    spec.hero.sub = spec.hero.sub ||
      `${specialty.keywords.slice(0, 3).join(' · ')} — ${spec.brand.tagline || ''}`;
    spec.meta = {
      description: `${spec.brand.region} ${specialty.label} ${spec.brand.name}. ${specialty.keywords.join(', ')}. 문의 ${spec.brand.phone}.`,
      keywords: [spec.brand.name, specialty.label, spec.brand.region, ...specialty.keywords].join(', '),
    };
    // 소상공인 전용 브랜드 필드 기본값
    spec.brand.instagram   = spec.brand.instagram   || '';
    spec.brand.naver_place = spec.brand.naver_place || '';
  }

  // 이미지: 고객 실사진(spec.images) > 업종 기본 스톡 > 자체 플레이스홀더.
  // VENOM_LOCAL_PLACEHOLDERS=1 이면 외부 URL 무시(오프라인 미리보기용).
  const localOnly = process.env.VENOM_LOCAL_PLACEHOLDERS === '1';
  const stock = localOnly ? {} : (specialty.stock || {});
  spec.images = Object.assign({}, stock, spec.images || {});
  const ph = placeholderDataUri;

  const si = require('./stock-images');
  const subKey = spec.clinic?.specialty || spec.local?.type || spec.press?.type;
  if (!spec.images.hero)  spec.images.hero  = si.getHero(spec.category, subKey, localOnly);
  if (!spec.images.intro) spec.images.intro = si.getIntro(spec.category, subKey, localOnly);
  if (!spec.images.gallery || !spec.images.gallery.length)
    spec.images.gallery = si.getGallery(spec.category, subKey, localOnly);

  spec.images.intro = spec.images.intro || ph(spec.category === 'clinic' ? '병원 내부 전경' : '매장 내부');
  if (spec.images.hero) {
    spec.images.heroBg = `url('${spec.images.hero}')`;
  } else {
    spec.images.hero   = '';
    spec.images.heroBg = `linear-gradient(135deg, var(--p), var(--bd))`;
  }

  const faq = buildFaq(spec.faq, spec.brand, specialty);

  const mainSchema = buildMainSchema(spec, specialty, spec.domain);

  if (spec.category === 'clinic') {
    spec.sections = {
      trust:       buildTrust(spec.trust),
      hours:       buildHours(spec.clinic?.hours),
      departments: buildDepartments(specialty),
      doctors:     buildDoctors(spec.clinic?.doctors, spec.images),
      reviews:     buildReviews(spec.reviews, specialty),
      gallery:     buildGallery(spec.images.gallery, ph),
      faq:         faq.html,
      faqSchema:   faq.schema,
      mainSchema,
    };
  } else if (spec.category === 'press') {
    // press: menu 섹션을 기사 카드(article cards)로 재활용
    spec.sections = {
      trust:     buildTrust(spec.trust),
      menu:      buildMenu(spec.local?.menu || spec.press?.articles, specialty),
      faq:       faq.html,
      faqSchema: faq.schema,
      mainSchema,
    };
  } else {
    spec.sections = {
      trust:   buildTrust(spec.trust),
      menu:    buildMenu(spec.local?.menu, specialty),
      hours:   buildHours(spec.local?.hours),
      reviews: buildLocalReviews(spec.reviews, specialty),
      gallery: buildGallery(spec.images.gallery, ph),
      faq:     faq.html,
      faqSchema: faq.schema,
      mainSchema,
    };
  }

  // BreadcrumbList 스키마
  const breadcrumbSchema = JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: '홈', item: `https://${spec.domain}/` },
      { '@type': 'ListItem', position: 2, name: specialty.label, item: `https://${spec.domain}/#${spec.category === 'clinic' ? 'departments' : 'menu'}` },
    ],
  }, null, 2);

  if (spec.category === 'clinic') {
    spec.sections.breadcrumbSchema = breadcrumbSchema;
  } else if (spec.category === 'local') {
    spec.sections.breadcrumbSchema = breadcrumbSchema;
  }

  // 이미지 URL만 추출 (data URI 제외 — sitemap에는 공개 URL만)
  const publicImages = {};
  if (spec.images) {
    for (const [k, v] of Object.entries(spec.images)) {
      if (typeof v === 'string' && v.startsWith('http')) publicImages[k] = v;
      if (Array.isArray(v)) {
        const publicArr = v.filter(u => typeof u === 'string' && u.startsWith('http'));
        if (publicArr.length) publicImages[k] = publicArr;
      }
    }
  }

  const seoFiles = {
    'robots.txt': robotsTxt(spec.domain),
    'sitemap.xml': sitemapXml(spec.domain, scale.pages, publicImages),
    'llms.txt':    llmsTxt(spec, specialty),
  };

  return { spec, blueprint, specialty, scale, options, seoFiles };
}

// --- 정적 HTML 출력 ----------------------------------------------------------
function generate(specPath) {
  if (!fs.existsSync(specPath))
    throw new Error(`site-spec 파일을 찾을 수 없습니다: ${specPath}`);
  const raw = JSON.parse(fs.readFileSync(specPath, 'utf8'));
  const { spec, blueprint, specialty, scale, options, seoFiles } = prepare(raw);

  const tplPath = path.join(ROOT, 'blueprints', spec.category, 'template.html');
  if (!fs.existsSync(tplPath))
    throw new Error(`템플릿 파일이 없습니다: blueprints/${spec.category}/template.html`);
  const tpl = fs.readFileSync(tplPath, 'utf8');
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

  // 대시보드용 manifest.json
  const manifest = {
    slug: spec.slug,
    domain: spec.domain,
    brandName: spec.brand.name,
    category: spec.category,
    specialtyLabel: specialty.label,
    scale: scale.label,
    options,
    generatedAt: new Date().toISOString(),
    sizeBytes: Buffer.byteLength(html),
    hasBlog: fs.existsSync(path.join(outDir, 'blog', 'index.json')),
  };
  fs.writeFileSync(path.join(outDir, 'manifest.json'), JSON.stringify(manifest, null, 2));

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

function generateFromRaw(rawSpec) {
  const { spec, blueprint, specialty, scale, options, seoFiles } = prepare(rawSpec);

  const tplPath = path.join(ROOT, 'blueprints', spec.category, 'template.html');
  if (!fs.existsSync(tplPath))
    throw new Error(`템플릿 파일이 없습니다: blueprints/${spec.category}/template.html`);
  const tpl = fs.readFileSync(tplPath, 'utf8');
  let html = render(tpl, spec);

  if (options.includes('medical_review')) {
    const { runMedicalReview } = require('./options/medical-review');
    const rv = runMedicalReview(html);
    html = rv.html;
  }

  const outDir = path.join(ROOT, 'output', spec.slug);
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'index.html'), html);
  for (const [name, content] of Object.entries(seoFiles)) {
    fs.writeFileSync(path.join(outDir, name), content);
  }

  const manifest = {
    slug: spec.slug,
    domain: spec.domain,
    brandName: spec.brand.name,
    category: spec.category,
    specialtyLabel: specialty.label,
    scale: scale.label,
    options,
    generatedAt: new Date().toISOString(),
    sizeBytes: Buffer.byteLength(html),
    hasBlog: fs.existsSync(path.join(outDir, 'blog', 'index.json')),
  };
  fs.writeFileSync(path.join(outDir, 'manifest.json'), JSON.stringify(manifest, null, 2));

  return { slug: spec.slug, domain: spec.domain, brandName: spec.brand.name, outDir };
}

if (require.main === module) {
  const specArg = process.argv[2];
  if (!specArg) {
    console.error('사용법: node engine/generate.js <site-spec.json>');
    process.exit(1);
  }
  generate(path.resolve(specArg));
}

module.exports = { generate, generateFromRaw, prepare, render, slugify };
