const https = require('https');
const { URL } = require('url');

const WEBHOOK_URL = 'https://script.google.com/macros/s/AKfycby8DngUbdYtGWz52yWVciUgo9I9B75mUQcgKcxo_q2ai0CBehLh-TUGzZ5d1BeY1S1wjg/exec';

function postJson(urlStr, body) {
  return new Promise(function(resolve, reject) {
    var parsed = new URL(urlStr);
    var payload = JSON.stringify(body);
    var options = {
      hostname: parsed.hostname,
      path: parsed.pathname + parsed.search,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
      }
    };
    var req = https.request(options, function(res) {
      var data = '';
      res.on('data', function(c) { data += c; });
      res.on('end', function() {
        // Apps Script redirects to a new URL on success — follow it
        if ([301,302,303,307,308].includes(res.statusCode) && res.headers.location) {
          return postJson(res.headers.location, body).then(resolve).catch(reject);
        }
        try { resolve(JSON.parse(data)); } catch(e) { resolve({ result: 'ok' }); }
      });
    });
    req.on('error', reject);
    req.write(payload);
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
    var result = await postJson(WEBHOOK_URL, body);
    res.status(200).json(result);
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
};
