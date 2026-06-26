module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(200).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: 'Method not allowed' }); return; }

  var APPS_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbzZYLKxO6hMOvy0UBQf-rj1mBukpY3d0BETght9KdXn1cbpCvxNAO39_4mBwaQ4wIEzgA/exec';

  try {
    // Vercel auto-parses JSON body; fallback to raw read
    var body = req.body;
    if (!body || typeof body !== 'object' || Array.isArray(body)) {
      var raw = '';
      await new Promise(function(resolve, reject) {
        req.on('data', function(c) { raw += c; });
        req.on('end', resolve);
        req.on('error', reject);
      });
      try { body = JSON.parse(raw); } catch(e) { body = {}; }
    }

    if (!body || !body.hospital) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Build GET query string
    var qs = Object.keys(body)
      .map(function(k) { return encodeURIComponent(k) + '=' + encodeURIComponent(body[k] || ''); })
      .join('&');
    var url = APPS_SCRIPT_URL + '?' + qs;

    // fetch() is available in Node 18+ (Vercel runtime)
    // follow redirects automatically (default)
    var response = await fetch(url, {
      method: 'GET',
      headers: { 'User-Agent': 'Mozilla/5.0' },
      redirect: 'follow',
      signal: AbortSignal.timeout(30000)
    });

    var text = await response.text();
    var data;
    try { data = JSON.parse(text); } catch(e) { data = { result: 'ok' }; }

    return res.status(200).json({ result: 'ok', raw: data });
  } catch (e) {
    console.error('contact handler error:', e.message);
    return res.status(500).json({ error: e.message });
  }
};
