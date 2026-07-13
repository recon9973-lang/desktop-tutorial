#!/usr/bin/env node
'use strict';

/**
 * sitemap 표류(drift) 검증기 — roadmap ① 검증 파트.
 *
 * 검사 항목:
 *   1) 콘텐츠 표류: content/blog-posts.json 의 라이브 글 수 ↔ sitemap.xml 의 /blog/ URL 수
 *   2) 도메인 일관성: sitemap.xml 이 canonical 도메인(venom-new-site) 만 쓰는지
 *   3) robots.txt 의 Sitemap 선언 URL 과 실제 도메인 일치 여부
 *
 * 사용:  node scripts/check-sitemap.js         (검증만, 표류 있으면 exit 1)
 *        node scripts/check-sitemap.js --fix   (표류 발견 시 sitemap.xml 재생성)
 */

const fs = require('fs');
const path = require('path');
const { buildXml } = require('../lib/sitemap-builder.js');

const ROOT = path.join(__dirname, '..');
const CANON = 'https://venom-new-site.vercel.app';
const FIX = process.argv.includes('--fix');

function read(rel) {
  try { return fs.readFileSync(path.join(ROOT, rel), 'utf8'); }
  catch { return ''; }
}

function loadPosts() {
  const raw = JSON.parse(read('content/blog-posts.json') || '[]');
  return Array.isArray(raw) ? raw : (raw.posts || raw.items || []);
}

function liveCount(posts) {
  const now = Date.now();
  return posts.filter(p =>
    p.status === 'published' && (p.slug || p.id) && (!p.publishAt || Date.parse(p.publishAt) <= now)
  ).length;
}

function main() {
  const problems = [];
  const posts = loadPosts();
  const live = liveCount(posts);

  const sitemap = read('sitemap.xml');
  const blogInMap = (sitemap.match(/\/blog\//g) || []).length;
  const hosts = [...new Set((sitemap.match(/https:\/\/[a-z0-9.-]+/g) || []))];

  // 1) 콘텐츠 표류
  if (blogInMap !== live) {
    problems.push(`콘텐츠 표류: 라이브 글 ${live}건 ≠ sitemap /blog/ ${blogInMap}건`);
  }
  // 2) 도메인 일관성
  const badHosts = hosts.filter(h => h !== CANON);
  if (badHosts.length) {
    problems.push(`도메인 불일치: sitemap 에 canonical(${CANON}) 외 도메인 존재 → ${badHosts.join(', ')}`);
  }
  // 3) robots.txt Sitemap 선언 일치
  const robots = read('robots.txt');
  const m = robots.match(/Sitemap:\s*(\S+)/i);
  if (m && !m[1].startsWith(CANON)) {
    problems.push(`robots.txt Sitemap 선언(${m[1]})이 canonical 도메인과 불일치`);
  }

  if (!problems.length) {
    console.log(`✅ sitemap OK — 라이브 글 ${live}건 = sitemap /blog/ ${blogInMap}건, 도메인 ${CANON} 일치`);
    process.exit(0);
  }

  console.error('❌ sitemap 표류 감지:');
  problems.forEach(p => console.error('  - ' + p));

  if (FIX) {
    fs.writeFileSync(path.join(ROOT, 'sitemap.xml'), buildXml(posts));
    console.log(`🔧 sitemap.xml 재생성 완료 (라이브 글 ${live}건 반영).`);
    process.exit(0);
  }
  console.error('\n→ 재생성하려면:  node scripts/check-sitemap.js --fix');
  process.exit(1);
}

main();
