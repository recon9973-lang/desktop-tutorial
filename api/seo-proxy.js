'use strict';

// SEO 도구용 프록시 4종 통합 (Vercel Hobby 12-함수 한도 절감: geo/geo-url/kw/psi → 1개)
//   GET /api/seo-proxy?type=entity&query=...   → Google Knowledge Graph 엔티티 검색
//   GET /api/seo-proxy?type=psi&url=...         → Google PageSpeed Insights
//   GET /api/seo-proxy?type=fetch&url=...       → 페이지 HTML + robots.txt 수집 (GEO 분석)
//   GET /api/seo-proxy?type=keyword&keyword=... → 네이버 검색광고 키워드 도구

const https = require('https');
const http = require('http');
const crypto = require('crypto');
const { URL } = require('url');

// 단순 GET → JSON 패스스루 (entity, psi 공용)
function getJson(fullUrl, res, withRaw) {
  https.get(fullUrl, function(r) {
    var body = '';
    r.on('data', function(c) { body += c; });
    r.on('end', function() {
      try { res.status(r.statusCode).json(JSON.parse(body)); }
      catch (e) {
        res.status(500).json(withRaw ? { error: 'Parse error', raw: body.slice(0, 300) } : { error: 'Parse error' });
      }
    });
  }).on('error', function(e) { res.status(500).json({ error: e.message }); });
}

// 리다이렉트 추적 URL fetch (fetch 타입용)
function fetchUrl(urlStr, redirects) {
  return new Promise(function(resolve, reject) {
    if (redirects > 5) { reject(new Error('Too many redirects')); return; }
    var parsed;
    try { parsed = new URL(urlStr); } catch (e) { reject(e); return; }
    var lib = parsed.protocol === 'https:' ? https : http;
    var options = {
      hostname: parsed.hostname,
      port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
      path: parsed.pathname + parsed.search,
      method: 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; VenomGEOBot/1.0)',
        'Accept': 'text/html,application/xhtml+xml,*/*',
        'Accept-Language': 'ko,en;q=0.9'
      },
      timeout: 10000
    };
    var req = lib.request(options, function(res) {
      if ([301, 302, 303, 307, 308].includes(res.statusCode) && res.headers.location) {
        var next = res.headers.location;
        if (!next.startsWith('http')) next = parsed.protocol + '//' + parsed.host + next;
        resolve(fetchUrl(next, redirects + 1));
        return;
      }
      var chunks = [];
      res.on('data', function(c) { chunks.push(c); });
      res.on('end', function() { resolve({ status: res.statusCode, body: Buffer.concat(chunks).toString('utf8') }); });
    });
    req.on('error', reject);
    req.on('timeout', function() { req.destroy(); reject(new Error('Timeout')); });
    req.end();
  });
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }

  const type = req.query.type;

  // ── 1) Google Knowledge Graph 엔티티 검색 ──
  if (type === 'entity') {
    const query = req.query.query;
    if (!query) { res.status(400).json({ error: 'query parameter required' }); return; }
    const key = process.env.PSI_KEY;
    if (!key) { res.status(500).json({ error: 'PSI_KEY not configured' }); return; }
    const apiPath = '/v1/entities:search?query=' + encodeURIComponent(query)
      + '&key=' + key + '&limit=5&languages=ko&languages=en';
    return getJson('https://kgsearch.googleapis.com' + apiPath, res, false);
  }

  // ── 2) PageSpeed Insights ──
  if (type === 'psi') {
    const url = req.query.url;
    if (!url) { res.status(400).json({ error: 'url parameter required' }); return; }
    const key = process.env.PSI_KEY;
    if (!key) { res.status(500).json({ error: 'PSI_KEY not configured' }); return; }
    const apiPath = '/pagespeedonline/v5/runPagespeed?url=' + encodeURIComponent(url)
      + '&key=' + key
      + '&strategy=mobile&category=seo&category=performance&category=best-practices&category=accessibility';
    return getJson('https://www.googleapis.com' + apiPath, res, true);
  }

  // ── 3) 네이버 검색광고 키워드 도구 ──
  if (type === 'keyword') {
    const keyword = req.query.keyword;
    if (!keyword) { res.status(400).json({ error: 'keyword parameter required' }); return; }
    const customerId = (process.env.NAVER_CUSTOMER_ID || '').trim();
    const accessLicense = (process.env.NAVER_ACCESS_LICENSE || '').trim();
    const secretKey = (process.env.NAVER_SECRET_KEY || '').trim();
    if (!customerId || !accessLicense || !secretKey) {
      res.status(500).json({ error: 'Naver API credentials not configured' }); return;
    }
    const timestamp = Date.now().toString();
    const hmac = crypto.createHmac('sha256', Buffer.from(secretKey, 'base64'));
    hmac.update(timestamp + '.' + accessLicense, 'utf8');
    const signature = hmac.digest('base64');
    const hints = [keyword, keyword + ' 비용', keyword + ' 후기', keyword + ' 잘하는곳', keyword + ' 추천'];
    const apiPath = '/keywordstool?hintKeywords=' + hints.map(encodeURIComponent).join(',') + '&showDetail=1';
    https.get({
      hostname: 'api.searchad.naver.com', path: apiPath, method: 'GET',
      headers: {
        'Content-Type': 'application/json; charset=UTF-8',
        'X-Timestamp': timestamp, 'X-API-KEY': accessLicense,
        'X-Customer': customerId, 'X-Signature': signature
      }
    }, function(r) {
      var body = '';
      r.on('data', function(c) { body += c; });
      r.on('end', function() {
        try { res.status(r.statusCode).json(JSON.parse(body)); }
        catch (e) { res.status(500).json({ error: 'Parse error', raw: body.slice(0, 500) }); }
      });
    }).on('error', function(e) { res.status(500).json({ error: e.message }); });
    return;
  }

  // ── 4) 페이지 HTML + robots.txt 수집 (GEO 분석) ──
  if (type === 'fetch') {
    var url = req.query.url;
    if (!url) { res.status(400).json({ error: 'url parameter required' }); return; }
    try {
      var full = url.startsWith('http') ? url : 'https://' + url;
      var parsed = new URL(full);
      var origin = parsed.protocol + '//' + parsed.host;
      var results = await Promise.allSettled([fetchUrl(full, 0), fetchUrl(origin + '/robots.txt', 0)]);
      var pageResult = results[0], robotsResult = results[1];
      res.status(200).json({
        html: pageResult.status === 'fulfilled' ? pageResult.value.body : '',
        robots: robotsResult.status === 'fulfilled' ? robotsResult.value.body : '',
        pageStatus: pageResult.status === 'fulfilled' ? pageResult.value.status : 0,
        isHttps: parsed.protocol === 'https:'
      });
    } catch (e) { res.status(500).json({ error: e.message }); }
    return;
  }

  res.status(400).json({ error: 'unknown type (entity|psi|fetch|keyword)' });
};
