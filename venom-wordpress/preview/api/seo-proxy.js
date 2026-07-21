'use strict';

// SEO 도구용 프록시 4종 통합 (Vercel Hobby 12-함수 한도 절감: geo/geo-url/kw/psi → 1개)
//   GET /api/seo-proxy?type=entity&query=...   → Google Knowledge Graph 엔티티 검색
//   GET /api/seo-proxy?type=psi&url=...         → Google PageSpeed Insights
//   GET /api/seo-proxy?type=fetch&url=...       → 페이지 HTML + robots.txt 수집 (GEO 분석)
//   GET /api/seo-proxy?type=keyword&keyword=... → 네이버 검색광고 키워드 도구

const https = require('https');
const http = require('http');
const zlib = require('zlib');
const crypto = require('crypto');
const { URL } = require('url');
const sa = require('../lib/naver-searchad'); // 검색광고 키워드도구 단일 소스

// 단순 GET → JSON 패스스루 (entity, psi 공용)
// 상류(구글 PSI 등)가 느릴 때 함수가 무한 대기하지 않도록 20초 타임아웃을 건다
// → 초과 시 504로 즉시 응답, 클라이언트의 '정밀분석 생략'이 곧바로 동작한다.
function getJson(fullUrl, res, withRaw) {
  var done = false;
  var reqObj = https.get(fullUrl, function(r) {
    var chunks = [];
    r.on('data', function(c) { chunks.push(c); });
    r.on('end', function() {
      if (done) return; done = true;
      var body = Buffer.concat(chunks).toString('utf8');
      try { res.status(r.statusCode).json(JSON.parse(body)); }
      catch (e) {
        res.status(500).json(withRaw ? { error: 'Parse error', raw: body.slice(0, 300) } : { error: 'Parse error' });
      }
    });
  });
  reqObj.on('error', function(e) { if (done) return; done = true; res.status(500).json({ error: e.message }); });
  reqObj.setTimeout(20000, function() {
    if (done) return; done = true;
    reqObj.destroy();
    res.status(504).json({ error: '상류 응답 지연(20초 초과) — 정밀분석 생략' });
  });
}

// SSRF 방지: 내부/사설/링크로컬 호스트 차단
function isBlockedHost(hostname) {
  var h = (hostname || '').toLowerCase();
  if (h === 'localhost' || h === '0.0.0.0' || h === '::1' || h.endsWith('.local') || h.endsWith('.internal')) return true;
  var m = h.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (m) {
    var a = +m[1], b = +m[2];
    if (a === 10 || a === 127 || a === 0) return true;
    if (a === 169 && b === 254) return true;          // link-local / metadata
    if (a === 172 && b >= 16 && b <= 31) return true; // private
    if (a === 192 && b === 168) return true;          // private
  }
  return false;
}

// 리다이렉트 추적 URL fetch (fetch 타입용)
var _BROWSER_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
var _GOOGLEBOT_UA = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)';
// ua: 미지정 시 브라우저 UA. 봇차단(401/403/429/503) 응답이면 Googlebot UA로 1회 자동 재시도.
function fetchUrl(urlStr, redirects, ua) {
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
        // 실제 크롬 UA로 위장: 일부 호스팅/CMS가 미상 봇에 빈/축약 페이지를 주는 문제 방지
        'User-Agent': ua || _BROWSER_UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        // 압축 허용 → content-encoding으로 gzip/br 사용 여부(속도 신호) 감지. 본문은 아래서 해제.
        'Accept-Encoding': 'gzip, deflate, br'
      },
      timeout: 12000
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
      res.on('end', function() {
        var buf = Buffer.concat(chunks);
        var enc = (res.headers['content-encoding'] || '').toLowerCase();
        try {
          if (enc.indexOf('br') >= 0) buf = zlib.brotliDecompressSync(buf);
          else if (enc.indexOf('gzip') >= 0) buf = zlib.gunzipSync(buf);
          else if (enc.indexOf('deflate') >= 0) buf = zlib.inflateSync(buf);
        } catch (e) { /* 해제 실패 시 원본 유지(파싱은 실패해도 헤더 신호는 유효) */ }
        var body = buf.toString('utf8');
        // 봇차단(401/403/429/503)이고 아직 브라우저 UA면 → Googlebot UA로 1회 재시도(SEO 친화 사이트 회복)
        if ([401, 403, 429, 503].indexOf(res.statusCode) >= 0 && !ua) {
          resolve(fetchUrl(urlStr, redirects, _GOOGLEBOT_UA));
          return;
        }
        resolve({ status: res.statusCode, body: body, headers: res.headers });
      });
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
    // 속도 개선: 4개 카테고리(20~40s) → 필요한 2개(performance·seo)만 요청.
    // 항목 판정(psiByName)에 쓰는 audit은 seo 카테고리에 포함되고, 접근성·모범사례
    // 게이지는 부가 정보라 생략 → PSI 응답 시간을 대폭 단축한다.
    const apiPath = '/pagespeedonline/v5/runPagespeed?url=' + encodeURIComponent(url)
      + '&key=' + key
      + '&strategy=mobile&category=performance&category=seo';
    return getJson('https://www.googleapis.com' + apiPath, res, true);
  }

  // ── 3) 네이버 검색광고 키워드 도구 (인증·호출은 lib/naver-searchad 단일 소스) ──
  if (type === 'keyword') {
    const keyword = req.query.keyword;
    if (!keyword) { res.status(400).json({ error: 'keyword parameter required' }); return; }
    // hintKeywords는 공백 불허(네이버 11001 오류) — 공백 제거형 변형 키워드로 확장
    const base = String(keyword).replace(/\s+/g, '');
    const hints = [base, base + '비용', base + '후기', base + '잘하는곳', base + '추천'];
    const r = await sa.fetchKeywordTool(hints);
    if (r.configured === false) { res.status(500).json({ error: 'Naver API credentials not configured' }); return; }
    if (r.json) { res.status(r.status).json(r.json); return; } // 기존과 동일: 네이버 원시 응답 그대로 전달
    res.status(r.status || 500).json({ error: r.error || 'Naver searchad error' }); return;
  }

  // ── 4) 페이지 HTML + robots.txt 수집 (GEO 분석) ──
  if (type === 'fetch') {
    var url = req.query.url;
    if (!url) { res.status(400).json({ error: 'url parameter required' }); return; }
    try {
      var full = url.startsWith('http') ? url : 'https://' + url;
      var parsed = new URL(full);
      if (!/^https?:$/.test(parsed.protocol) || isBlockedHost(parsed.hostname)) {
        return res.status(400).json({ error: '허용되지 않는 주소입니다.' });
      }
      var origin = parsed.protocol + '//' + parsed.host;
      var results = await Promise.allSettled([fetchUrl(full, 0), fetchUrl(origin + '/robots.txt', 0)]);
      var pageResult = results[0], robotsResult = results[1];
      // 보안·속도 신호에 필요한 응답 헤더만 선별 반환(전체 헤더 노출 방지).
      var rawH = (pageResult.status === 'fulfilled' && pageResult.value.headers) ? pageResult.value.headers : {};
      var pickH = {};
      ['strict-transport-security','x-content-type-options','x-frame-options','referrer-policy',
       'content-security-policy','content-encoding','x-xss-protection','permissions-policy']
        .forEach(function(k){ if (rawH[k] != null) pickH[k] = String(rawH[k]); });
      res.status(200).json({
        html: pageResult.status === 'fulfilled' ? pageResult.value.body : '',
        robots: robotsResult.status === 'fulfilled' ? robotsResult.value.body : '',
        pageStatus: pageResult.status === 'fulfilled' ? pageResult.value.status : 0,
        isHttps: parsed.protocol === 'https:',
        headers: pickH
      });
    } catch (e) { res.status(500).json({ error: e.message }); }
    return;
  }

  res.status(400).json({ error: 'unknown type (entity|psi|fetch|keyword)' });
};
