#!/usr/bin/env node
/**
 * VENOM Site Factory — 미리보기 서버
 *
 * 사용법: node auto-site-factory/server.js
 * 접속:  http://localhost:3737
 *
 * 엔드포인트
 *   GET  /                → intake/index.html
 *   POST /api/preview     → spec JSON → 완성된 HTML 반환 (iframe 미리보기용)
 *   GET  /output/<slug>/  → 생성된 정적 사이트 제공
 */
const http  = require('http');
const https = require('https');
const fs    = require('fs');
const path  = require('path');

const { prepare, render, generateFromRaw } = require('./engine/generate');

const PORT     = parseInt(process.env.PORT  || '3737', 10);
const AI_MODEL = process.env.AI_MODEL || 'claude-haiku-4-5-20251001';
const ROOT = __dirname;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css':  'text/css',
  '.js':   'application/javascript',
  '.json': 'application/json',
  '.txt':  'text/plain',
  '.xml':  'application/xml',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.svg':  'image/svg+xml',
  '.ico':  'image/x-icon',
};

function serveFile(res, filePath) {
  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    return res.end('404 Not found');
  }
  const ext = path.extname(filePath).toLowerCase();
  res.writeHead(200, { 'Content-Type': MIME[ext] || 'text/plain' });
  res.end(fs.readFileSync(filePath));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let buf = '';
    req.on('data', d => { buf += d; if (buf.length > 8 * 1024 * 1024) reject(new Error('body too large')); });
    req.on('end',  () => resolve(buf));
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');

  // OPTIONS preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204); return res.end();
  }

  // ── POST /api/preview ──────────────────────────────────────────────────────
  if (req.method === 'POST' && req.url === '/api/preview') {
    try {
      const body = await readBody(req);
      const spec = JSON.parse(body);

      const { spec: enriched } = prepare(spec);
      const tplPath = path.join(ROOT, 'blueprints', enriched.category, 'template.html');
      const tpl = fs.readFileSync(tplPath, 'utf8');
      let html = render(tpl, enriched);

      // 미리보기 배너 삽입 (실제 deploy 결과물이 아님을 표시)
      const banner = `<div style="position:fixed;bottom:0;left:0;right:0;background:#533afd;color:#fff;
        text-align:center;padding:8px;font-family:sans-serif;font-size:13px;font-weight:600;
        z-index:99999;letter-spacing:.02em">
        🔍 VENOM 미리보기 — 실제 사이트와 100% 동일하지 않을 수 있습니다
      </div>`;
      html = html.replace('</body>', banner + '</body>');

      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      return res.end(html);
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      return res.end(JSON.stringify({ error: e.message }));
    }
  }

  // ── POST /api/generate ────────────────────────────────────────────────────
  if (req.method === 'POST' && req.url === '/api/generate') {
    try {
      const body = await readBody(req);
      const rawSpec = JSON.parse(body);
      const result = generateFromRaw(rawSpec);
      // blog_auto: fire-and-forget (requires OPENAI_API_KEY)
      if (rawSpec.options && rawSpec.options.includes('blog_auto')) {
        const { runFromRaw } = require('./engine/blog-gen');
        runFromRaw(rawSpec).catch(e => console.error('[blog_auto]', e.message));
      }
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      return res.end(JSON.stringify({ ok: true, ...result }));
    } catch (e) {
      res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
      return res.end(JSON.stringify({ ok: false, error: e.message }));
    }
  }

  // ── POST /api/ai-fill ──────────────────────────────────────────────────────
  if (req.method === 'POST' && req.url === '/api/ai-fill') {
    if (!process.env.ANTHROPIC_API_KEY) {
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      return res.end(JSON.stringify({ error: 'ANTHROPIC_API_KEY_MISSING' }));
    }
    try {
      const body = await readBody(req);
      const { category, specialty, type, name, region } = JSON.parse(body);
      const subLabel = specialty || type || '';
      const catLabel = category === 'clinic' ? '병원·의원' : '소상공인';
      const subField = category === 'clinic' ? '진료과목' : '업종';
      const isClinic = category === 'clinic';
      const prompt = [
        '당신은 한국 소상공인·병원 홈페이지 전문 카피라이터입니다.',
        '아래 업체 정보를 바탕으로 홈페이지 문구를 작성하고 JSON만 반환하세요 (다른 텍스트 없이).',
        '',
        `업체명: ${name}`,
        `카테고리: ${catLabel}`,
        `${subField}: ${subLabel}`,
        `지역: ${region}`,
        '',
        isClinic ? [
          '의료광고법 준수 필수:',
          '- 최상급 표현 금지 (최고·최선·최대·유일·1등)',
          '- 효과·완치 보증 표현 금지 (100% 효과·완치·반드시·무조건)',
          '- 타 병원 비교·비하 금지',
          '- 부작용 없음·통증 없음 단정 표현 금지',
        ].join('\n') : '소비자기본법 준수: 과장·허위 광고 금지, 최저가 보장 금지',
        '',
        '작성 기준:',
        '- tagline: 20자 이내, 지역명 또는 업종 특성 반영, 신뢰감 있는 어조',
        `- metaDesc: 70자 이내, ${subLabel} 키워드 포함, 연락처/위치 힌트`,
        '- faq: 실제 고객이 자주 묻는 질문 3개 (예약·위치·가격·시간 중심)',
        '',
        '반환 형식 (JSON만, 마크다운 없이):',
        '{',
        '  "tagline": "...",',
        '  "metaDesc": "...",',
        '  "faq": [',
        '    {"q": "...", "a": "..."},',
        '    {"q": "...", "a": "..."},',
        '    {"q": "...", "a": "..."}',
        '  ]',
        '}',
      ].join('\n');
      const payload = JSON.stringify({
        model: AI_MODEL,
        max_tokens: 700,
        messages: [{ role: 'user', content: prompt }],
      });
      const aiResp = await new Promise((resolve, reject) => {
        const options = {
          hostname: 'api.anthropic.com',
          path: '/v1/messages',
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': process.env.ANTHROPIC_API_KEY,
            'anthropic-version': '2023-06-01',
            'Content-Length': Buffer.byteLength(payload),
          },
        };
        const r = https.request(options, res2 => {
          let buf = '';
          res2.on('data', d => { buf += d; });
          res2.on('end', () => {
            try { resolve(JSON.parse(buf)); }
            catch (e) { reject(new Error('API 파싱 실패: ' + buf.slice(0, 200))); }
          });
        });
        r.on('error', reject);
        r.write(payload);
        r.end();
      });
      const text = (aiResp.content && aiResp.content[0] && aiResp.content[0].text) || '{}';
      const m = text.match(/\{[\s\S]*\}/);
      const parsed = m ? JSON.parse(m[0]) : {};
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      return res.end(JSON.stringify(parsed));
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      return res.end(JSON.stringify({ error: e.message }));
    }
  }

  // ── GET /api/sites ────────────────────────────────────────────────────────
  if (req.method === 'GET' && req.url === '/api/sites') {
    try {
      const outputDir = path.join(ROOT, 'output');
      if (!fs.existsSync(outputDir)) {
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        return res.end(JSON.stringify([]));
      }
      const sites = fs.readdirSync(outputDir)
        .filter(d => fs.statSync(path.join(outputDir, d)).isDirectory())
        .map(slug => {
          const dir = path.join(outputDir, slug);
          const manifestPath = path.join(dir, 'manifest.json');
          if (fs.existsSync(manifestPath)) {
            return JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
          }
          // manifest 없는 구 버전: robots.txt에서 domain 추출
          const robotsPath = path.join(dir, 'robots.txt');
          let domain = slug.replace(/-/g, '.');
          if (fs.existsSync(robotsPath)) {
            const m = fs.readFileSync(robotsPath, 'utf8').match(/Sitemap: https:\/\/([^/]+)/);
            if (m) domain = m[1];
          }
          const stat = fs.statSync(path.join(dir, 'index.html'));
          return {
            slug, domain, brandName: slug, category: 'unknown',
            specialtyLabel: '', scale: '', options: [],
            generatedAt: stat.mtime.toISOString(),
            sizeBytes: stat.size,
            hasBlog: fs.existsSync(path.join(dir, 'blog', 'index.json')),
          };
        })
        .sort((a, b) => new Date(b.generatedAt) - new Date(a.generatedAt));
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      return res.end(JSON.stringify(sites));
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      return res.end(JSON.stringify({ error: e.message }));
    }
  }

  // ── GET static ────────────────────────────────────────────────────────────
  let urlPath = req.url.split('?')[0];
  if (urlPath === '/') urlPath = '/intake/index.html';
  if (urlPath === '/dashboard' || urlPath === '/dashboard/') urlPath = '/dashboard/index.html';

  serveFile(res, path.join(ROOT, urlPath));
});

// 구 버전 output 디렉토리에 manifest.json 백필 (없는 경우만)
function backfillManifests() {
  const outputDir = path.join(ROOT, 'output');
  if (!fs.existsSync(outputDir)) return;
  fs.readdirSync(outputDir).forEach(slug => {
    const dir = path.join(outputDir, slug);
    if (!fs.statSync(dir).isDirectory()) return;
    const manifestPath = path.join(dir, 'manifest.json');
    if (fs.existsSync(manifestPath)) return;
    const htmlPath = path.join(dir, 'index.html');
    if (!fs.existsSync(htmlPath)) return;
    const robotsPath = path.join(dir, 'robots.txt');
    let domain = slug.replace(/-/g, '.');
    if (fs.existsSync(robotsPath)) {
      const m = fs.readFileSync(robotsPath, 'utf8').match(/Sitemap: https:\/\/([^/]+)/);
      if (m) domain = m[1];
    }
    const html = fs.readFileSync(htmlPath, 'utf8');
    const titleM = html.match(/<title>([^—<]+)/);
    const brandName = titleM ? titleM[1].trim() : slug;
    const isClinic = /MedicalClinic/.test(html);
    const stat = fs.statSync(htmlPath);
    const manifest = {
      slug, domain, brandName,
      category: isClinic ? 'clinic' : 'local',
      specialtyLabel: '', scale: 'standard', options: [],
      generatedAt: stat.mtime.toISOString(),
      sizeBytes: stat.size,
      hasBlog: fs.existsSync(path.join(dir, 'blog', 'index.json')),
    };
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    console.log(`  [manifest] 백필 완료: ${slug}`);
  });
}

server.listen(PORT, '0.0.0.0', () => {
  console.log(`\n  VENOM Site Factory 미리보기 서버`);
  console.log(`  → http://localhost:${PORT}\n`);
  backfillManifests();
});
