'use strict';

// VENOM GrowthOps · 내부링크 리포트 CLI
//   node scripts/internal-links-report.js [--json] [--per 4]
// blog-posts.json을 읽어 고아 글·추천 내부링크를 출력. (읽기 전용, 발행물 변경 없음)

const fs = require('fs');
const path = require('path');
const { suggestLinks } = require('../lib/internal-linker');

const ROOT = path.resolve(__dirname, '..');
const POSTS = path.join(ROOT, 'venom-wordpress/preview/content/blog-posts.json');
const CLUSTERS = path.join(ROOT, 'venom-wordpress/preview/content/clusters.json');

function loadJson(p, fallback) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return fallback; }
}

const args = process.argv.slice(2);
const asJson = args.includes('--json');
const perIdx = args.indexOf('--per');
const perPost = perIdx >= 0 ? parseInt(args[perIdx + 1], 10) || 4 : 4;

const raw = loadJson(POSTS, []);
const posts = Array.isArray(raw) ? raw : (raw.posts || raw.items || []);
const clusters = loadJson(CLUSTERS, null);

const result = suggestLinks(posts, { perPost, clusters });

if (asJson) {
  process.stdout.write(JSON.stringify(result, null, 2) + '\n');
  process.exit(0);
}

const { stats, orphans, suggestions } = result;
console.log('\n=== VENOM GrowthOps · 내부링크 리포트 ===');
console.log(`발행 글: ${stats.posts} | 추천 링크 총: ${stats.totalSuggestedLinks} | 글당 평균: ${stats.avgLinksPerPost}`);
console.log(`고아 글: ${stats.orphanCount} (${(stats.orphanRate * 100).toFixed(1)}%)\n`);

if (orphans.length) {
  console.log('— 고아 글(인바운드 내부링크 0) —');
  for (const o of orphans) console.log(`  · [${o.cat || '-'}] ${o.title}  (${o.id})`);
  console.log('');
}

console.log('— 글별 추천 내부링크(상위) —');
for (const s of suggestions.slice(0, 50)) {
  console.log(`\n▸ ${s.title}  [${s.cat || '-'}]`);
  for (const l of s.links) {
    const flag = l.alreadyLinked ? ' (이미 링크됨)' : '';
    console.log(`    → ${l.anchor}  ${l.score}${flag}`);
  }
}
console.log('');
