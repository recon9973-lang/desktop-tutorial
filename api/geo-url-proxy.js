const https = require('https');
const http = require('http');
const { URL } = require('url');

function fetchUrl(urlStr, redirects) {
  return new Promise(function(resolve, reject) {
    if (redirects > 5) { reject(new Error('Too many redirects')); return; }
    var parsed;
    try { parsed = new URL(urlStr); } catch(e) { reject(e); return; }
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
      if ([301,302,303,307,308].includes(res.statusCode) && res.headers.location) {
        var next = res.headers.location;
        if (!next.startsWith('http')) {
          next = parsed.protocol + '//' + parsed.host + next;
        }
        resolve(fetchUrl(next, redirects + 1));
        return;
      }
      var chunks = [];
      res.on('data', function(c) { chunks.push(c); });
      res.on('end', function() {
        resolve({ status: res.statusCode, body: Buffer.concat(chunks).toString('utf8') });
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

  var url = req.query.url;
  if (!url) { res.status(400).json({ error: 'url parameter required' }); return; }

  try {
    var parsed = new URL(url.startsWith('http') ? url : 'https://' + url);
    var origin = parsed.protocol + '//' + parsed.host;

    var [pageResult, robotsResult] = await Promise.allSettled([
      fetchUrl(url.startsWith('http') ? url : 'https://' + url, 0),
      fetchUrl(origin + '/robots.txt', 0)
    ]);

    res.status(200).json({
      html: pageResult.status === 'fulfilled' ? pageResult.value.body : '',
      robots: robotsResult.status === 'fulfilled' ? robotsResult.value.body : '',
      pageStatus: pageResult.status === 'fulfilled' ? pageResult.value.status : 0,
      isHttps: parsed.protocol === 'https:'
    });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
};
