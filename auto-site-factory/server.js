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

  // ── GET static ────────────────────────────────────────────────────────────
  let urlPath = req.url.split('?')[0];
  if (urlPath === '/') urlPath = '/intake/index.html';

  serveFile(res, path.join(ROOT, urlPath));
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`\n  VENOM Site Factory 미리보기 서버`);
  console.log(`  → http://localhost:${PORT}\n`);
});
