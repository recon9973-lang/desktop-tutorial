const https = require('https');
const { URL } = require('url');

const APPS_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycby8DngUbdYtGWz52yWVciUgo9I9B75mUQcgKcxo_q2ai0CBehLh-TUGzZ5d1BeY1S1wjg/exec';

function sendToAppsScript(data) {
  return new Promise(function(resolve, reject) {
    // GET 파라미터로 전송 (Apps Script에서 가장 안정적)
    var params = Object.keys(data)
      .map(function(k) { return encodeURIComponent(k) + '=' + encodeURIComponent(data[k] || ''); })
      .join('&');

    function doGet(urlStr, redirects) {
      if (redirects > 5) { resolve({ result: 'ok' }); return; }
      var parsed;
      try { parsed = new URL(urlStr); } catch(e) { reject(e); return; }
      var options = {
        hostname: parsed.hostname,
        path: parsed.pathname + parsed.search,
        method: 'GET',
        headers: { 'User-Agent': 'VenomBot/1.0' },
        timeout: 15000
      };
      var req = https.request(options, function(res) {
        var body = '';
        res.on('data', function(c) { body += c; });
        res.on('end', function() {
          if ([301,302,303,307,308].includes(res.statusCode) && res.headers.location) {
            var next = res.headers.location;
            if (!next.startsWith('http')) {
              next = parsed.protocol + '//' + parsed.host + next;
            }
            doGet(next, redirects + 1);
            return;
          }
          try {
            var json = JSON.parse(body);
            resolve(json);
          } catch(e) {
            // Apps Script가 HTML 등 비-JSON 반환해도 성공 처리
            resolve({ result: 'ok' });
          }
        });
      });
      req.on('error', reject);
      req.on('timeout', function() { req.destroy(); reject(new Error('Timeout')); });
      req.end();
    }

    doGet(APPS_SCRIPT_URL + '?' + params, 0);
  });
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }

  try {
    var body = req.body;
    if (typeof body === 'string') { try { body = JSON.parse(body); } catch(e) {} }
    if (!body || typeof body !== 'object') {
      res.status(400).json({ error: 'Invalid body' }); return;
    }
    var result = await sendToAppsScript(body);
    res.status(200).json(result.result ? result : { result: 'ok' });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
};
