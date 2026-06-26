const https = require('https');
const http = require('http');
const { URL } = require('url');

const APPS_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbx-HBP1brRB3LduHBm75cbZBHV5PKN1BoOIdWeh19c3tFc9GsvQa3Z6cuWQkOiI7ApIHg/exec';

// POST body → Apps Script, 리다이렉트는 GET으로 follow
function sendPost(urlStr, payload, redirects) {
  return new Promise(function(resolve, reject) {
    if (redirects > 6) { resolve({ result: 'ok' }); return; }
    var parsed;
    try { parsed = new URL(urlStr); } catch(e) { reject(e); return; }
    var lib = parsed.protocol === 'https:' ? https : http;
    var body = JSON.stringify(payload);

    var options = {
      hostname: parsed.hostname,
      port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
      path: parsed.pathname + parsed.search,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
        'User-Agent': 'Mozilla/5.0'
      },
      timeout: 15000
    };

    var req = lib.request(options, function(res) {
      var data = '';
      res.on('data', function(c) { data += c; });
      res.on('end', function() {
        if ([301,302,303,307,308].includes(res.statusCode) && res.headers.location) {
          // 리다이렉트는 GET으로 follow (Apps Script 표준 동작)
          var next = res.headers.location;
          if (!next.startsWith('http')) next = parsed.protocol + '//' + parsed.host + next;
          return getUrl(next, 0).then(resolve).catch(reject);
        }
        try { resolve(JSON.parse(data)); }
        catch(e) { resolve({ result: 'ok' }); }
      });
    });
    req.on('error', reject);
    req.on('timeout', function() { req.destroy(); reject(new Error('Timeout')); });
    req.write(body);
    req.end();
  });
}

function getUrl(urlStr, redirects) {
  return new Promise(function(resolve, reject) {
    if (redirects > 6) { resolve({ result: 'ok' }); return; }
    var parsed;
    try { parsed = new URL(urlStr); } catch(e) { reject(e); return; }
    var lib = parsed.protocol === 'https:' ? https : http;
    var options = {
      hostname: parsed.hostname,
      port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
      path: parsed.pathname + parsed.search,
      method: 'GET',
      headers: { 'User-Agent': 'Mozilla/5.0' },
      timeout: 15000
    };
    var req = lib.request(options, function(res) {
      var data = '';
      res.on('data', function(c) { data += c; });
      res.on('end', function() {
        if ([301,302,303,307,308].includes(res.statusCode) && res.headers.location) {
          var next = res.headers.location;
          if (!next.startsWith('http')) next = parsed.protocol + '//' + parsed.host + next;
          return getUrl(next, redirects + 1).then(resolve).catch(reject);
        }
        try { resolve(JSON.parse(data)); }
        catch(e) { resolve({ result: 'ok' }); }
      });
    });
    req.on('error', reject);
    req.on('timeout', function() { req.destroy(); reject(new Error('Timeout')); });
    req.end();
  });
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: 'Method not allowed' }); return; }

  try {
    var body = req.body;
    if (typeof body === 'string') { try { body = JSON.parse(body); } catch(e) {} }
    if (!body || typeof body !== 'object') {
      res.status(400).json({ error: 'Invalid body' }); return;
    }
    var result = await sendPost(APPS_SCRIPT_URL, body, 0);
    // Apps Script가 {result:'ok'} 반환하면 성공, 아니면 ok로 간주
    res.status(200).json({ result: 'ok', raw: result });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
};
