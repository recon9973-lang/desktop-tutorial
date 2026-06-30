#!/usr/bin/env node
/**
 * VENOM Site Factory — 블로그 자동 생성기
 *
 * site-spec.json 을 읽어 진료과 키워드 기반 초기 블로그 포스트를 생성한다.
 * (blog_auto 옵션 팩의 Node.js 실행 계층)
 *
 * 사용법:
 *   node engine/blog-gen.js samples/site-spec.example.json
 *   node engine/blog-gen.js samples/site-spec.example.json --count=5
 *
 * 요구 환경변수:
 *   OPENAI_API_KEY  — 없으면 종료(오류 없이 0으로)
 *
 * 출력:
 *   output/<slug>/blog/<slug>.html   (각 포스트 HTML)
 *   output/<slug>/blog/index.json    (포스트 목록 메니페스트)
 */
'use strict';

const fs   = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');

// site-spec specialty → post-generator category 매핑
const SPEC_TO_CAT = {
  dental:   'dental',
  skin:     'skin',
  ortho:    'ortho',
  oriental: 'oriental',
  plastic:  'plastic',
  naegwa:   'naegwa',
  angwa:    'angwa',
};

// 소상공인 로컬 type → post-generator category 매핑
const LOCAL_TYPE_TO_CAT = {
  cafe:       'cafe',
  restaurant: 'restaurant',
  beauty:     'beauty',
  nail:       'beauty',
  fitness:    'fitness',
  bakery:     'cafe',
  retail:     'retail',
};

async function run(specPath, count) {
  if (!process.env.OPENAI_API_KEY) {
    console.log('[blog_auto] OPENAI_API_KEY 없음 — 건너뜁니다.');
    return;
  }

  const { generatePost } = require('../../lib/post-generator');
  const { prepare, slugify } = require('./generate');

  const raw = JSON.parse(fs.readFileSync(specPath, 'utf8'));

  if (!raw.options || !raw.options.includes('blog_auto')) {
    console.log('[blog_auto] site-spec에 blog_auto 옵션이 없습니다.');
    return;
  }

  const { spec, specialty } = prepare(raw);
  let category;
  if (raw.category === 'local') {
    const localType = raw.local && raw.local.type;
    category = LOCAL_TYPE_TO_CAT[localType] || 'local';
  } else {
    const clinicSpecialty = raw.clinic && raw.clinic.specialty;
    category = SPEC_TO_CAT[clinicSpecialty] || 'geo';
  }
  const region   = spec.brand && spec.brand.region ? spec.brand.region : '';
  const keywords = (specialty.keywords || []).slice(0, count);

  const outDir  = path.join(ROOT, 'output', spec.slug);
  const blogDir = path.join(outDir, 'blog');
  fs.mkdirSync(blogDir, { recursive: true });

  const manifest = [];

  console.log(`\n📝 블로그 포스트 생성 시작 (${spec.brand.name} / ${specialty.label})`);
  console.log(`   키워드 ${keywords.length}개: ${keywords.join(', ')}`);
  console.log('────────────────────────────────');

  for (const keyword of keywords) {
    process.stdout.write(`  생성 중: ${keyword} ... `);
    try {
      const post = await generatePost({ category, keyword, region });
      const file = `${post.slug}.html`;
      fs.writeFileSync(path.join(blogDir, file), post.html, 'utf8');
      manifest.push({
        slug:     post.slug,
        title:    post.title,
        seoTitle: post.seoTitle,
        metaDesc: post.metaDesc,
        keywords: post.keywords,
        date:     post.date,
        status:   post.status,
        file,
      });
      const tokens = post.tokenUsage ? post.tokenUsage.totalTokens : '?';
      const status = post.status === 'draft' ? '✅ draft' : '⚠ review';
      console.log(`${status}  (${tokens} tokens)`);
      if (post.autoFixed) console.log(`    → 의료광고 금지어 자동 수정`);
    } catch (e) {
      console.log(`❌ 실패 — ${e.message}`);
    }
  }

  fs.writeFileSync(path.join(blogDir, 'index.json'), JSON.stringify(manifest, null, 2), 'utf8');

  console.log('────────────────────────────────');
  console.log(`✅ 완료: output/${spec.slug}/blog/  (${manifest.length}개 포스트)`);
  console.log(`   목록: output/${spec.slug}/blog/index.json\n`);
}

if (require.main === module) {
  const specArg = process.argv[2];
  const countArg = parseInt((process.argv.find(a => a.startsWith('--count=')) || '').split('=')[1], 10) || 3;
  if (!specArg) {
    console.error('사용법: node engine/blog-gen.js <site-spec.json> [--count=N]');
    process.exit(1);
  }
  run(path.resolve(specArg), countArg).catch(e => {
    console.error(e.message);
    process.exit(1);
  });
}

module.exports = { run };
