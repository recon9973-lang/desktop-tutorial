#!/usr/bin/env node
/**
 * VENOM Site Factory — 워드프레스 멀티사이트 어댑터
 *
 * 같은 site-spec.json 을 받아 WordPress 멀티사이트에 새 사이트를 생성하는
 * WP-CLI 프로비저닝 스크립트를 만들어낸다. (정적 엔진과 콘텐츠 동일 — prepare() 공유)
 *
 * 사용법:
 *   node engine/wp-adapter.js samples/site-spec.example.json            # 스크립트만 출력(dry-run)
 *   node engine/wp-adapter.js samples/site-spec.example.json --write    # output/<slug>/provision.sh 저장
 *
 * 생성된 provision.sh 는 멀티사이트가 떠 있는 환경(venom-wordpress/docker)에서
 *   docker compose run --rm wp-cli bash < output/<slug>/provision.sh
 * 로 실행하면 실제 사이트가 만들어진다.
 */
const fs = require('fs');
const path = require('path');
const { prepare } = require('./generate');

const ROOT = path.join(__dirname, '..');

// 옵션 팩 → 워드프레스 플러그인 매핑 (베놈 도구 재활용 연결 지점)
const OPTION_PLUGINS = {
  seo_pack:       ['venom-seo'],          // SEO/AEO/GEO + llms.txt 발행 (lib/sitemap-builder.js 기반)
  blog_auto:      ['venom-autoblog'],     // 블로그 자동발행 (lib/post-generator.js 기반)
  image_pack:     ['venom-image'],        // AI 이미지 + WebP (lib/image-generator.js 기반)
  medical_review: ['venom-medreview'],    // 의료광고 검수 (lib/medical-ad-validator.js 기반)
  translate:      ['venom-i18n'],         // 다국어 (lib/translate.js 기반)
  analytics:      ['venom-analytics'],    // 분석 (api/analytics.js 기반)
};

const esc = s => String(s == null ? '' : s).replace(/'/g, "'\\''");

// 홈페이지 콘텐츠(구텐베르크 custom-HTML 블록) — 정적 섹션 재사용
function homeContent(spec) {
  const s = spec.sections;
  return [
    `<!-- wp:html --><section class="vn-hero"><span class="vn-badge">${spec.brand.region} ${spec.specialty.label}</span>`,
    `<h1>${spec.hero.headline}</h1><p>${spec.hero.sub}</p>`,
    `<a class="vn-btn" href="${spec.brand.kakao}">카카오 상담신청</a></section><!-- /wp:html -->`,
    `<!-- wp:html --><section class="vn-trust">${s.trust}</section><!-- /wp:html -->`,
    `<!-- wp:heading --><h2>진료 안내</h2><!-- /wp:heading -->`,
    `<!-- wp:html --><div class="vn-grid">${s.departments}</div><!-- /wp:html -->`,
    `<!-- wp:heading --><h2>의료진 소개</h2><!-- /wp:heading -->`,
    `<!-- wp:html --><div class="vn-grid">${s.doctors}</div><!-- /wp:html -->`,
    `<!-- wp:heading --><h2>진료 사례</h2><!-- /wp:heading -->`,
    `<!-- wp:html --><div class="vn-grid">${s.reviews}</div><!-- /wp:html -->`,
    `<!-- wp:heading --><h2>자주 묻는 질문</h2><!-- /wp:heading -->`,
    `<!-- wp:html -->${s.faq}<!-- /wp:html -->`,
  ].join('\n');
}

function buildScript(rawSpec) {
  const { spec, blueprint, specialty, scale, options, seoFiles } = prepare(rawSpec);
  const slug = spec.slug;
  const L = []; // 스크립트 라인
  const wp = 'wp --allow-root';

  L.push('#!/usr/bin/env bash');
  L.push('set -euo pipefail');
  L.push(`# VENOM Site Factory — provision: ${spec.brand.name} (${specialty.label}/${scale.label})`);
  L.push('');
  L.push('# 1) 네트워크에 새 사이트 생성');
  L.push(`SITE_URL=$(${wp} site create --slug='${slug}' --title='${esc(spec.brand.name)}' --porcelain 2>/dev/null || ${wp} site list --field=url --url='${slug}')`);
  L.push(`SITE='${slug}'`);
  L.push('');
  L.push('# 2) 브랜드 디자인 토큰 저장');
  L.push(`${wp} option update --url="$SITE" venom_primary   '${esc(spec.brand.primary)}'`);
  L.push(`${wp} option update --url="$SITE" venom_phone     '${esc(spec.brand.phone || '')}'`);
  L.push(`${wp} option update --url="$SITE" venom_address   '${esc(spec.brand.address || '')}'`);
  L.push(`${wp} option update --url="$SITE" venom_region    '${esc(spec.brand.region || '')}'`);
  L.push(`${wp} option update --url="$SITE" venom_specialty '${esc(spec.clinic && spec.clinic.specialty || '')}'`);
  L.push(`${wp} option update --url="$SITE" venom_keywords  '${esc((specialty.keywords || []).join(','))}'`);
  L.push(`${wp} option update --url="$SITE" blogdescription '${esc(spec.brand.tagline)}'`);
  L.push('');
  L.push('# 3) 베놈 플러그인 설치 + 활성화');
  // 플러그인 소스 경로 (Docker 마운트 기준: /app = 리포지토리 루트)
  L.push('VENOM_PLUGINS_SRC="${VENOM_PLUGINS_SRC:-/app/venom-plugins}"');
  L.push('WP_PLUGINS_DIR="${WP_PLUGINS_DIR:-/var/www/html/wp-content/plugins}"');
  const plugins = options.flatMap(o => OPTION_PLUGINS[o] || []);
  // 필요한 플러그인만 복사 (멱등: 이미 있으면 덮어쓰기)
  for (const plugin of plugins) {
    L.push(`[ -d "$VENOM_PLUGINS_SRC/${plugin}" ] && cp -r "$VENOM_PLUGINS_SRC/${plugin}" "$WP_PLUGINS_DIR/" || true`);
  }
  if (plugins.length) {
    L.push(`${wp} plugin activate --network ${plugins.join(' ')} || true`);
  }
  L.push('');
  L.push('# 4) 페이지 생성');
  // 홈
  L.push(`HOME_ID=$(${wp} post create --url="$SITE" --post_type=page --post_status=publish --post_title='홈' --porcelain - <<'VNHTML'`);
  L.push(homeContent(spec));
  L.push('VNHTML');
  L.push(`)`);
  L.push(`${wp} option update --url="$SITE" show_on_front page`);
  L.push(`${wp} option update --url="$SITE" page_on_front "$HOME_ID"`);
  // 서브 페이지 (규모별)
  const titleMap = { departments: '진료안내', doctors: '의료진', reviews: '진료사례', blog: '블로그', directions: '오시는길', contact: '상담신청' };
  for (const p of scale.pages.filter(p => p !== 'home')) {
    L.push(`${wp} post create --url="$SITE" --post_type=page --post_status=publish --post_title='${titleMap[p] || p}' --porcelain >/dev/null`);
  }
  L.push('');
  L.push('# 5) SEO 파일 (robots/sitemap/llms.txt) — venom-seo 옵션으로 동적 발행');
  for (const name of Object.keys(seoFiles)) {
    L.push(`${wp} option update --url="$SITE" venom_seo_${name.replace(/\W/g, '_')} 1`);
  }
  L.push('');
  L.push(`echo "✅ 생성 완료: $SITE  (${spec.brand.name} / ${specialty.label})"`);

  return { slug, script: L.join('\n') + '\n', spec, specialty, scale, options, plugins };
}

function run(specPath, write) {
  const rawSpec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
  const { slug, script, spec, specialty, scale, options, plugins } = buildScript(rawSpec);

  if (write) {
    const outDir = path.join(ROOT, 'output', slug);
    fs.mkdirSync(outDir, { recursive: true });
    const file = path.join(outDir, 'provision.sh');
    fs.writeFileSync(file, script, { mode: 0o755 });
    console.log('\n✅ 워드프레스 프로비저닝 스크립트 생성');
    console.log('────────────────────────────────');
    console.log(`  브랜드   : ${spec.brand.name} (${specialty.label} / ${scale.label})`);
    console.log(`  사이트   : 멀티사이트 slug = ${slug}`);
    console.log(`  플러그인 : ${plugins.join(', ') || '(없음)'}`);
    console.log(`  스크립트 : auto-site-factory/output/${slug}/provision.sh`);
    console.log('  실행     : docker compose run --rm wp-cli bash < ' + `output/${slug}/provision.sh`);
    console.log('────────────────────────────────\n');
  } else {
    console.log(script);
  }
}

if (require.main === module) {
  const specArg = process.argv[2];
  const write = process.argv.includes('--write');
  if (!specArg) {
    console.error('사용법: node engine/wp-adapter.js <site-spec.json> [--write]');
    process.exit(1);
  }
  run(path.resolve(specArg), write);
}

module.exports = { buildScript };
