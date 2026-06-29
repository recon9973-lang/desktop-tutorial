#!/usr/bin/env node
/**
 * VENOM Site Factory — 자동생성 엔진 (MVP)
 *
 * 사용법:  node engine/generate.js samples/site-spec.example.json
 *
 * 흐름:  site-spec.json + 카테고리 블루프린트  →  완성된 정적 사이트 폴더
 *        (index.html + robots.txt + sitemap.xml + llms.txt)
 *
 * 이 정적 출력은 즉시 미리보기 가능하며, 동일 site-spec을 WP-CLI/REST 어댑터에
 * 넘기면 멀티사이트에 그대로 생성된다(2차 작업).
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
    `<div class="card"><h3>${k}</h3><p>${specialty.label} 전문 의료진의 ${k} 진료</p></div>`
  ).join('\n');
}

function buildDoctors(doctors) {
  const list = (doctors && doctors.length) ? doctors
    : [{ name: '대표원장', role: '전문의', desc: '풍부한 임상 경험' }];
  return list.map(d =>
    `<div class="card"><h3>${d.name}</h3><p><b>${d.role || '전문의'}</b><br>${d.desc || ''}</p></div>`
  ).join('\n');
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

// --- 메인 --------------------------------------------------------------------
function generate(specPath) {
  const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));

  const blueprint = JSON.parse(
    fs.readFileSync(path.join(ROOT, 'blueprints', spec.category, 'blueprint.json'), 'utf8')
  );
  const specialty = blueprint.specialties[spec.clinic?.specialty] || blueprint.specialties.dental;
  const scale = blueprint.scales[spec.scale] || blueprint.scales.standard;

  // 옵션 = 블루프린트 기본값 + 고객 선택 (중복 제거)
  const options = Array.from(new Set([...(blueprint.defaultOptions || []), ...(spec.options || [])]));

  // 파생 데이터
  spec.lang = (spec.locale && spec.locale[0]) || 'ko';
  spec.specialty = specialty;
  spec.hero = spec.hero || {};
  spec.hero.headline = spec.hero.headline ||
    `${spec.brand.region} <b>${specialty.label}</b>,<br>믿을 수 있는 ${spec.brand.name}`;
  spec.hero.sub = spec.hero.sub ||
    `${specialty.keywords.slice(0, 3).join(' · ')} — 정확한 진단과 정직한 진료로 함께합니다.`;
  spec.meta = {
    description: `${spec.brand.region} ${specialty.label} ${spec.brand.name}. ${specialty.keywords.join(', ')} 진료. 상담 ${spec.brand.phone}.`,
    keywords: [spec.brand.name, specialty.label, ...specialty.keywords].join(', '),
  };

  const faq = buildFaq(spec.faq, spec.brand, specialty);
  spec.sections = {
    trust: buildTrust(spec.trust),
    departments: buildDepartments(specialty),
    doctors: buildDoctors(spec.clinic?.doctors),
    reviews: buildReviews(spec.reviews, specialty),
    faq: faq.html,
    faqSchema: faq.schema,
  };

  // 렌더
  const tpl = fs.readFileSync(path.join(ROOT, 'blueprints', spec.category, 'template.html'), 'utf8');
  const html = render(tpl, spec);

  // 출력
  const slug = slugify(spec.domain || spec.brand.name);
  const outDir = path.join(ROOT, 'output', slug);
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'index.html'), html);
  fs.writeFileSync(path.join(outDir, 'robots.txt'), robotsTxt(spec.domain));
  fs.writeFileSync(path.join(outDir, 'sitemap.xml'), sitemapXml(spec.domain, scale.pages));
  fs.writeFileSync(path.join(outDir, 'llms.txt'), llmsTxt(spec, specialty));

  // 리포트
  console.log('\n✅ 사이트 생성 완료');
  console.log('────────────────────────────────');
  console.log(`  브랜드   : ${spec.brand.name}`);
  console.log(`  카테고리 : ${blueprint.label} / ${specialty.label} (${scale.label})`);
  console.log(`  도메인   : ${spec.domain}`);
  console.log(`  페이지   : ${scale.pages.join(', ')}`);
  console.log(`  옵션 팩  : ${options.join(', ')}`);
  console.log(`  출력 위치: auto-site-factory/output/${slug}/`);
  console.log(`  생성 파일: index.html, robots.txt, sitemap.xml, llms.txt`);
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

module.exports = { generate, render };
