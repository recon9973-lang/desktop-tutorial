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

const { prepare, render } = require('./engine/generate');

const PORT = 3737;
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
      const prompt = [
        '한국 소상공인·병원 홈페이지 카피라이터입니다.',
        '아래 정보로 홈페이지 문구를 JSON만 반환하세요 (다른 텍스트 없이).',
        '',
        `업체명: ${name}`,
        `카테고리: ${catLabel}`,
        `${subField}: ${subLabel}`,
        `지역: ${region}`,
        '',
        '반환 형식:',
        '{',
        '  "tagline": "20자 이내 슬로건",',
        '  "metaDesc": "70자 이내 SEO 메타 설명",',
        '  "faq": [',
        '    {"q": "자주 묻는 질문 1", "a": "답변 1"},',
        '    {"q": "자주 묻는 질문 2", "a": "답변 2"},',
        '    {"q": "자주 묻는 질문 3", "a": "답변 3"}',
        '  ]',
        '}',
      ].join('\n');
      const payload = JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 512,
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

  // ── GET static ────────────────────────────────────────────────────────────
  let urlPath = req.url.split('?')[0];
  if (urlPath === '/') urlPath = '/intake/index.html';

  serveFile(res, path.join(ROOT, urlPath));
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`\n  VENOM Site Factory 미리보기 서버`);
  console.log(`  → http://localhost:${PORT}\n`);
});
